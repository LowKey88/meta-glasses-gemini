#!/usr/bin/env python3
"""
Redis Old Key Cleanup Script

Safely removes old Redis keys after verifying the new keys exist.
This script cleans up keys that were successfully migrated to the new naming convention.

Safety Features:
- Dry run mode by default
- Verifies new key exists before deleting old key
- Comprehensive logging
- Batch processing with delays
- Rollback-friendly (doesn't delete if verification fails)
"""

import sys
import os
import json
import logging
import time
import base64
from datetime import datetime
from typing import Dict, List, Tuple, Set

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_utils import r
from utils.redis_key_builder import RedisKeyBuilder

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'redis_cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RedisKeyCleanup:
    """Safely cleans up old Redis keys after migration."""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.old_prefix = "josancamon:rayban-meta-glasses-api"
        self.old_standalone_patterns = ["memory:", "memory_index:", "metrics:", "redis_monitor:"]
        
        self.cleanup_stats = {
            'total_old_keys_found': 0,
            'verified_for_deletion': 0,
            'successfully_deleted': 0,
            'deletion_errors': 0,
            'verification_failed': 0,
            'skipped_no_new_key': 0
        }
        
        self.deleted_keys = []
        self.error_keys = []
        self.skipped_keys = []
    
    def identify_migration_mapping(self, old_key: str) -> str:
        """
        Identify what the new key should be for a given old key.
        Returns the new key path or empty string if no mapping.
        """
        # Handle josancamon prefixed keys
        if old_key.startswith(self.old_prefix):
            suffix = old_key[len(self.old_prefix):].lstrip(":")
            parts = suffix.split(":")
            
            if not parts:
                return ""
            
            # Cache keys (base64 encoded)
            if len(parts) == 1:
                try:
                    decoded = base64.b64decode(parts[0]).decode('utf-8')
                    return RedisKeyBuilder.get_generic_cache_key(decoded)
                except:
                    return ""
            
            # Reminder keys
            elif len(parts) == 2 and parts[0] == "reminder":
                return RedisKeyBuilder.get_reminder_event_key(parts[1])
            
            # User data keys
            elif len(parts) == 2:
                key_type, user_id = parts[0], parts[1]
                if key_type == "conversation_history":
                    return RedisKeyBuilder.get_user_history_key(user_id)
                elif key_type == "user_profile":
                    return RedisKeyBuilder.get_user_profile_key(user_id)
            
            # Cancellation keys
            elif len(parts) == 3 and parts[0] == "cancellation":
                return RedisKeyBuilder.get_cancellation_state_key(parts[2], parts[1])
        
        # Handle standalone pattern keys
        elif old_key.startswith("memory:"):
            parts = old_key.split(":")
            if len(parts) == 3:  # memory:user_id:memory_id
                return RedisKeyBuilder.get_user_memory_key(parts[1], parts[2])
        
        elif old_key.startswith("memory_index:"):
            parts = old_key.split(":")
            if len(parts) == 2:  # memory_index:user_id
                return RedisKeyBuilder.get_user_memory_index_key(parts[1])
        
        elif old_key.startswith("metrics:"):
            parts = old_key.split(":")
            if len(parts) >= 3:
                metric_type = parts[1]
                identifier = ":".join(parts[2:])
                
                if metric_type == "messages":
                    # Handle messages:YYYY-MM-DD-HH pattern
                    if "-" in identifier and len(identifier.split("-")) >= 4:
                        date_hour = identifier.split("-")
                        date = "-".join(date_hour[:3])
                        hour = date_hour[3]
                        return RedisKeyBuilder.get_messages_key(date, hour)
                    else:
                        return RedisKeyBuilder.get_messages_key(identifier)
                elif metric_type == "ai_requests":
                    return RedisKeyBuilder.get_ai_requests_key(identifier)
                elif metric_type == "response_times":
                    return RedisKeyBuilder.get_response_times_key(identifier)
                elif metric_type == "user_activity":
                    return RedisKeyBuilder.get_user_activity_key(identifier)
        
        elif old_key.startswith("redis_monitor:"):
            parts = old_key.split(":")
            if len(parts) >= 2:
                monitor_type = ":".join(parts[1:])
                if monitor_type == "commands":
                    return RedisKeyBuilder.get_redis_commands_key()
                elif monitor_type == "latency":
                    return RedisKeyBuilder.get_redis_latency_key()
                else:
                    return RedisKeyBuilder.get_health_check_key(monitor_type)
        
        return ""
    
    def verify_migration_complete(self, old_key: str, new_key: str) -> bool:
        """
        Verify that migration was successful by checking:
        1. New key exists
        2. Data integrity (basic check)
        """
        try:
            # Check if old key exists
            if not r.exists(old_key):
                logger.warning(f"Old key doesn't exist: {old_key}")
                return False
            
            # Check if new key exists
            if not r.exists(new_key):
                logger.warning(f"New key doesn't exist: {new_key}")
                return False
            
            # Basic data integrity check - compare data types
            old_type = r.type(old_key)
            new_type = r.type(new_key)
            
            if isinstance(old_type, bytes):
                old_type = old_type.decode()
            if isinstance(new_type, bytes):
                new_type = new_type.decode()
            
            if old_type != new_type:
                logger.warning(f"Data type mismatch: {old_key} ({old_type}) vs {new_key} ({new_type})")
                return False
            
            # For simple verification, we'll trust that if both keys exist and have same type,
            # the migration was successful (since our migration script was comprehensive)
            return True
            
        except Exception as e:
            logger.error(f"Error verifying migration for {old_key}: {e}")
            return False
    
    def cleanup_key(self, old_key: str) -> bool:
        """
        Safely clean up a single old key after verification.
        Returns True if successfully cleaned up, False otherwise.
        """
        try:
            # Determine the new key that should exist
            new_key = self.identify_migration_mapping(old_key)
            
            if not new_key:
                logger.info(f"No migration mapping found for {old_key}, skipping")
                self.cleanup_stats['skipped_no_new_key'] += 1
                self.skipped_keys.append({"key": old_key, "reason": "No migration mapping"})
                return False
            
            # Verify migration was successful
            if not self.verify_migration_complete(old_key, new_key):
                logger.warning(f"Migration verification failed for {old_key} -> {new_key}")
                self.cleanup_stats['verification_failed'] += 1
                self.skipped_keys.append({"key": old_key, "reason": "Verification failed", "new_key": new_key})
                return False
            
            self.cleanup_stats['verified_for_deletion'] += 1
            
            # Perform cleanup
            if not self.dry_run:
                result = r.delete(old_key)
                if result:
                    logger.info(f"Deleted old key: {old_key} (migrated to {new_key})")
                    self.cleanup_stats['successfully_deleted'] += 1
                    self.deleted_keys.append({
                        "old_key": old_key,
                        "new_key": new_key,
                        "deleted_at": datetime.now().isoformat()
                    })
                    return True
                else:
                    logger.error(f"Failed to delete {old_key}")
                    self.cleanup_stats['deletion_errors'] += 1
                    return False
            else:
                logger.info(f"[DRY RUN] Would delete: {old_key} (migrated to {new_key})")
                self.deleted_keys.append({
                    "old_key": old_key,
                    "new_key": new_key,
                    "would_delete": True
                })
                return True
                
        except Exception as e:
            logger.error(f"Error cleaning up key {old_key}: {e}")
            self.error_keys.append({"key": old_key, "error": str(e)})
            self.cleanup_stats['deletion_errors'] += 1
            return False
    
    def scan_and_cleanup(self) -> None:
        """Scan for old keys and clean them up safely."""
        logger.info(f"Starting Redis key cleanup (dry_run={self.dry_run})")
        
        # Patterns to scan for old keys
        patterns = [
            f"{self.old_prefix}:*",  # Original josancamon keys
            "memory:*",              # Old memory keys
            "memory_index:*",        # Old memory index keys
            "metrics:*",             # Old metrics keys
            "redis_monitor:*"        # Old monitor keys
        ]
        
        all_old_keys = []
        
        try:
            for pattern in patterns:
                logger.info(f"Scanning for old keys with pattern: {pattern}")
                for key in r.scan_iter(match=pattern):
                    key_str = key.decode() if isinstance(key, bytes) else key
                    all_old_keys.append(key_str)
            
            # Remove duplicates and filter out new keys
            all_old_keys = list(set(all_old_keys))
            
            # Filter out keys that are already in new format
            old_keys_to_cleanup = []
            for key in all_old_keys:
                # Skip if it's already a new key
                if key.startswith("meta-glasses:"):
                    continue
                old_keys_to_cleanup.append(key)
            
            self.cleanup_stats['total_old_keys_found'] = len(old_keys_to_cleanup)
            logger.info(f"Found {len(old_keys_to_cleanup)} old keys to potentially clean up")
            
            if len(old_keys_to_cleanup) == 0:
                logger.info("No old keys found that need cleanup.")
                return
            
            # Clean up each key
            for i, old_key in enumerate(old_keys_to_cleanup, 1):
                logger.info(f"Processing key {i}/{len(old_keys_to_cleanup)}: {old_key}")
                self.cleanup_key(old_key)
                
                # Small delay to prevent overwhelming Redis
                if i % 50 == 0:
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"Error during cleanup scan: {e}")
            raise
    
    def generate_report(self) -> None:
        """Generate detailed cleanup report."""
        logger.info("=" * 80)
        logger.info("REDIS KEY CLEANUP REPORT")
        logger.info("=" * 80)
        
        # Summary statistics
        logger.info("CLEANUP SUMMARY:")
        for key, value in self.cleanup_stats.items():
            logger.info(f"  {key.replace('_', ' ').title()}: {value}")
        
        logger.info("")
        logger.info(f"Cleanup Mode: {'DRY RUN' if self.dry_run else 'LIVE CLEANUP'}")
        
        # Sample deletions
        if self.deleted_keys:
            logger.info("")
            logger.info("SAMPLE DELETIONS (first 10):")
            for deletion in self.deleted_keys[:10]:
                if self.dry_run:
                    logger.info(f"  Would delete: {deletion['old_key']} -> {deletion['new_key']}")
                else:
                    logger.info(f"  Deleted: {deletion['old_key']} -> {deletion['new_key']}")
        
        # Errors and skipped keys
        if self.error_keys:
            logger.info("")
            logger.info(f"CLEANUP ERRORS ({len(self.error_keys)}):")
            for error in self.error_keys[:5]:
                logger.info(f"  {error['key']}: {error['error']}")
        
        if self.skipped_keys:
            logger.info("")
            logger.info(f"SKIPPED KEYS ({len(self.skipped_keys)}):")
            for skip in self.skipped_keys[:5]:
                logger.info(f"  {skip['key']}: {skip['reason']}")
        
        # Save detailed report
        report_file = f'cleanup_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        report_data = {
            'cleanup_stats': self.cleanup_stats,
            'deleted_keys': self.deleted_keys,
            'error_keys': self.error_keys,
            'skipped_keys': self.skipped_keys,
            'dry_run': self.dry_run,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            logger.info(f"Detailed report saved to: {report_file}")
        except Exception as e:
            logger.error(f"Failed to save report file: {e}")
        
        logger.info("=" * 80)


def main():
    """Main cleanup function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up old Redis keys after migration')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Run in dry-run mode (default: True)')
    parser.add_argument('--live', action='store_true', default=False,
                        help='Run live cleanup (WARNING: deletes Redis keys)')
    
    args = parser.parse_args()
    
    # Determine run mode
    dry_run = not args.live
    
    if not dry_run:
        print("⚠️  WARNING: You are about to DELETE old Redis keys!")
        print("⚠️  Make sure the migration was successful and you have backups.")
        print("⚠️  This operation cannot be undone.")
        response = input("Type 'DELETE' to confirm live cleanup: ")
        if response != 'DELETE':
            print("Cleanup cancelled.")
            return
    
    try:
        # Initialize cleanup
        cleanup = RedisKeyCleanup(dry_run=dry_run)
        
        # Run cleanup
        cleanup.scan_and_cleanup()
        
        # Generate report
        cleanup.generate_report()
        
        # Final summary
        if cleanup.cleanup_stats['total_old_keys_found'] > 0:
            success_rate = (cleanup.cleanup_stats['verified_for_deletion'] / 
                           cleanup.cleanup_stats['total_old_keys_found']) * 100
            
            print(f"\n🧹 Cleanup completed!")
            print(f"Keys processed: {cleanup.cleanup_stats['verified_for_deletion']}/{cleanup.cleanup_stats['total_old_keys_found']}")
            print(f"Success rate: {success_rate:.1f}%")
            
            if dry_run:
                print("\n💡 This was a DRY RUN. No keys were deleted.")
                print("   Run with --live flag to perform actual cleanup.")
            else:
                print(f"\n✅ Successfully deleted {cleanup.cleanup_stats['successfully_deleted']} old keys!")
                print("   Your Redis is now clean and optimized.")
        else:
            print("\n✨ No old keys found - your Redis is already clean!")
        
    except KeyboardInterrupt:
        logger.info("Cleanup interrupted by user")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise


if __name__ == "__main__":
    main()