#!/usr/bin/env python3
"""
Enhanced Redis Key Migration Script

This script handles ALL Redis key patterns, including memory and metrics keys
that were missed by the original migration script.

Handles these additional patterns:
- memory:{user_id}:{memory_id} -> meta-glasses:user:memory:{user_id}:{memory_id}
- memory_index:{user_id} -> meta-glasses:user:memory_index:{user_id}
- metrics:{type}:{date} -> meta-glasses:metrics:{type}:{date}
- redis_monitor:{type} -> meta-glasses:monitor:redis:{type}
"""

import sys
import os
import json
import logging
import time
import base64
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_utils import r
from utils.redis_key_builder import RedisKeyBuilder

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'redis_migration_enhanced_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedRedisMigrator:
    """Enhanced migrator that handles ALL key patterns."""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.old_prefix = "josancamon:rayban-meta-glasses-api"
        self.migration_stats = {
            'total_keys_found': 0,
            'cache_keys': 0,
            'reminder_keys': 0,
            'user_history_keys': 0,
            'user_profile_keys': 0,
            'cancellation_keys': 0,
            'memory_keys': 0,
            'memory_index_keys': 0,
            'metrics_keys': 0,
            'monitor_keys': 0,
            'unknown_keys': 0,
            'migrated_successfully': 0,
            'migration_errors': 0,
            'keys_with_ttl': 0,
            'keys_without_ttl': 0
        }
        self.migrated_keys = []
        self.error_keys = []
    
    def identify_key_type(self, key: str) -> Tuple[str, Dict[str, str]]:
        """
        Enhanced key identification that handles ALL key patterns.
        """
        # Handle keys with the old josancamon prefix
        if key.startswith(self.old_prefix):
            suffix = key[len(self.old_prefix):].lstrip(":")
            parts = suffix.split(":")
            
            if not parts:
                return "unknown", {}
            
            # Generic cache keys (base64 encoded paths)
            if len(parts) == 1:
                try:
                    decoded = base64.b64decode(parts[0]).decode('utf-8')
                    return "cache", {"encoded_path": parts[0], "original_path": decoded}
                except:
                    return "unknown", {"suffix": suffix}
            
            # Two-part keys
            elif len(parts) == 2:
                key_type, identifier = parts[0], parts[1]
                
                if key_type == "reminder":
                    return "reminder", {"event_id": identifier}
                elif key_type == "conversation_history":
                    return "user_history", {"user_id": identifier}
                elif key_type == "user_profile":
                    return "user_profile", {"user_id": identifier}
                else:
                    return "unknown", {"type": key_type, "user_id": identifier}
            
            # Three-part keys
            elif len(parts) == 3:
                if parts[0] == "cancellation":
                    return "cancellation", {"platform": parts[1], "user_id": parts[2]}
                else:
                    return "unknown", {"suffix": suffix, "parts": parts}
            
            else:
                return "unknown", {"suffix": suffix, "parts": parts}
        
        # Handle standalone patterns (without josancamon prefix)
        elif key.startswith("memory:"):
            # memory:{user_id}:{memory_id} or memory_index:{user_id}
            parts = key.split(":")
            if len(parts) == 3 and parts[0] == "memory":
                return "memory", {"user_id": parts[1], "memory_id": parts[2]}
            else:
                return "unknown", {"key": key}
        
        elif key.startswith("memory_index:"):
            # memory_index:{user_id}
            parts = key.split(":")
            if len(parts) == 2:
                return "memory_index", {"user_id": parts[1]}
            else:
                return "unknown", {"key": key}
        
        elif key.startswith("metrics:"):
            # metrics:{type}:{date} or similar patterns
            parts = key.split(":")
            if len(parts) >= 3:
                return "metrics", {"type": parts[1], "identifier": ":".join(parts[2:])}
            else:
                return "unknown", {"key": key}
        
        elif key.startswith("redis_monitor:"):
            # redis_monitor:{type}
            parts = key.split(":")
            if len(parts) >= 2:
                return "monitor", {"type": ":".join(parts[1:])}
            else:
                return "unknown", {"key": key}
        
        else:
            return "unknown", {"key": key}
    
    def generate_new_key(self, key_type: str, components: Dict[str, str]) -> Optional[str]:
        """Generate new key using RedisKeyBuilder."""
        try:
            if key_type == "cache":
                return RedisKeyBuilder.get_generic_cache_key(components["original_path"])
            
            elif key_type == "reminder":
                return RedisKeyBuilder.get_reminder_event_key(components["event_id"])
            
            elif key_type == "user_history":
                return RedisKeyBuilder.get_user_history_key(components["user_id"])
            
            elif key_type == "user_profile":
                return RedisKeyBuilder.get_user_profile_key(components["user_id"])
            
            elif key_type == "cancellation":
                return RedisKeyBuilder.get_cancellation_state_key(
                    components["user_id"], 
                    components["platform"]
                )
            
            elif key_type == "memory":
                return RedisKeyBuilder.get_user_memory_key(
                    components["user_id"],
                    components["memory_id"]
                )
            
            elif key_type == "memory_index":
                return RedisKeyBuilder.get_user_memory_index_key(components["user_id"])
            
            elif key_type == "metrics":
                # Handle different metrics patterns
                metric_type = components["type"]
                identifier = components["identifier"]
                
                if metric_type == "ai_requests":
                    return RedisKeyBuilder.get_ai_requests_key(identifier)
                elif metric_type == "messages":
                    # Handle messages:YYYY-MM-DD-HH pattern
                    if "-" in identifier:
                        date_hour = identifier.split("-")
                        if len(date_hour) >= 4:  # YYYY-MM-DD-HH
                            date = "-".join(date_hour[:3])
                            hour = date_hour[3]
                            return RedisKeyBuilder.get_messages_key(date, hour)
                        else:  # YYYY-MM-DD
                            return RedisKeyBuilder.get_messages_key(identifier)
                    else:
                        return RedisKeyBuilder.get_messages_key(identifier)
                elif metric_type == "response_times":
                    return RedisKeyBuilder.get_response_times_key(identifier)
                elif metric_type == "user_activity":
                    return RedisKeyBuilder.get_user_activity_key(identifier)
                else:
                    logger.warning(f"Unknown metrics type: {metric_type}")
                    return None
            
            elif key_type == "monitor":
                monitor_type = components["type"]
                if monitor_type == "commands":
                    return RedisKeyBuilder.get_redis_commands_key()
                elif monitor_type == "latency":
                    return RedisKeyBuilder.get_redis_latency_key()
                else:
                    # Generic health check or other monitor key
                    return RedisKeyBuilder.get_health_check_key(monitor_type)
            
            else:
                logger.warning(f"Unknown key type for new key generation: {key_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating new key for type {key_type}: {e}")
            return None
    
    def migrate_key(self, old_key: str) -> bool:
        """Migrate a single key from old to new format."""
        try:
            # Identify key type and components
            key_type, components = self.identify_key_type(old_key)
            
            if key_type == "unknown":
                logger.warning(f"Unknown key pattern, skipping: {old_key}")
                self.migration_stats['unknown_keys'] += 1
                return False
            
            # Generate new key
            new_key = self.generate_new_key(key_type, components)
            if not new_key:
                logger.error(f"Failed to generate new key for: {old_key}")
                return False
            
            # Check if new key already exists
            if r.exists(new_key):
                logger.warning(f"New key already exists, skipping: {new_key}")
                return False
            
            # Get the data and TTL from old key
            data = r.get(old_key)
            if data is None:
                logger.warning(f"No data found for key: {old_key}")
                return False
            
            ttl = r.ttl(old_key)
            has_ttl = ttl > 0
            
            if has_ttl:
                self.migration_stats['keys_with_ttl'] += 1
            else:
                self.migration_stats['keys_without_ttl'] += 1
            
            # Perform migration
            if not self.dry_run:
                if has_ttl:
                    # Use DUMP/RESTORE to preserve exact TTL
                    dumped_data = r.dump(old_key)
                    r.restore(new_key, ttl * 1000, dumped_data)  # TTL in milliseconds
                    logger.info(f"Migrated with TTL {ttl}s: {old_key} -> {new_key}")
                else:
                    # Simple copy for keys without TTL
                    r.set(new_key, data)
                    logger.info(f"Migrated: {old_key} -> {new_key}")
            else:
                logger.info(f"[DRY RUN] Would migrate: {old_key} -> {new_key} (TTL: {ttl if has_ttl else 'none'})")
            
            # Track migration
            self.migrated_keys.append({
                "old_key": old_key,
                "new_key": new_key,
                "key_type": key_type,
                "components": components,
                "ttl": ttl if has_ttl else None,
                "data_size": len(data) if isinstance(data, bytes) else len(str(data))
            })
            
            # Update stats
            self.migration_stats[f'{key_type}_keys'] += 1
            self.migration_stats['migrated_successfully'] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error migrating key {old_key}: {e}")
            self.error_keys.append({"key": old_key, "error": str(e)})
            self.migration_stats['migration_errors'] += 1
            return False
    
    def scan_and_migrate(self) -> None:
        """Scan ALL keys that need migration and migrate them."""
        logger.info(f"Starting enhanced Redis key migration (dry_run={self.dry_run})")
        
        # Patterns to scan for
        patterns = [
            f"{self.old_prefix}:*",  # Original josancamon keys
            "memory:*",              # Memory keys
            "memory_index:*",        # Memory index keys
            "metrics:*",             # Metrics keys
            "redis_monitor:*"        # Monitor keys
        ]
        
        all_keys = []
        
        try:
            for pattern in patterns:
                logger.info(f"Scanning for pattern: {pattern}")
                for key in r.scan_iter(match=pattern):
                    key_str = key.decode() if isinstance(key, bytes) else key
                    all_keys.append(key_str)
            
            # Remove duplicates
            all_keys = list(set(all_keys))
            
            self.migration_stats['total_keys_found'] = len(all_keys)
            logger.info(f"Found {len(all_keys)} total keys to migrate")
            
            if len(all_keys) == 0:
                logger.info("No keys found that need migration.")
                return
            
            # Migrate each key
            for i, old_key in enumerate(all_keys, 1):
                logger.info(f"Processing key {i}/{len(all_keys)}: {old_key}")
                self.migrate_key(old_key)
                
                # Small delay to prevent overwhelming Redis
                if i % 100 == 0:
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"Error during enhanced migration scan: {e}")
            raise
    
    def generate_report(self) -> None:
        """Generate detailed migration report."""
        logger.info("=" * 80)
        logger.info("ENHANCED REDIS KEY MIGRATION REPORT")
        logger.info("=" * 80)
        
        # Summary statistics
        logger.info("MIGRATION SUMMARY:")
        for key, value in self.migration_stats.items():
            logger.info(f"  {key.replace('_', ' ').title()}: {value}")
        
        logger.info("")
        logger.info(f"Migration Mode: {'DRY RUN' if self.dry_run else 'LIVE MIGRATION'}")
        
        # Key type breakdown
        logger.info("")
        logger.info("KEY TYPE BREAKDOWN:")
        key_types = [
            'cache_keys', 'reminder_keys', 'user_history_keys', 'user_profile_keys', 
            'cancellation_keys', 'memory_keys', 'memory_index_keys', 'metrics_keys',
            'monitor_keys', 'unknown_keys'
        ]
        for key_type in key_types:
            count = self.migration_stats.get(key_type, 0)
            if count > 0:
                logger.info(f"  {key_type.replace('_', ' ').title()}: {count}")
        
        # Sample migrations
        if self.migrated_keys:
            logger.info("")
            logger.info("SAMPLE MIGRATIONS (first 10):")
            for migration in self.migrated_keys[:10]:
                logger.info(f"  {migration['old_key']} -> {migration['new_key']}")
        
        # Errors
        if self.error_keys:
            logger.info("")
            logger.info(f"MIGRATION ERRORS ({len(self.error_keys)}):")
            for error in self.error_keys[:10]:
                logger.info(f"  {error['key']}: {error['error']}")
        
        # Save detailed report
        report_file = f'enhanced_migration_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        report_data = {
            'migration_stats': self.migration_stats,
            'migrated_keys': self.migrated_keys,
            'error_keys': self.error_keys,
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
    """Main enhanced migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Redis key migration for ALL patterns')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Run in dry-run mode (default: True)')
    parser.add_argument('--live', action='store_true', default=False,
                        help='Run live migration (WARNING: modifies Redis data)')
    
    args = parser.parse_args()
    
    # Determine run mode
    dry_run = not args.live
    
    if not dry_run:
        print("⚠️  WARNING: Enhanced migration will modify Redis data!")
        print("⚠️  This includes memory, metrics, and monitoring keys.")
        response = input("Type 'YES' to confirm live migration: ")
        if response != 'YES':
            print("Migration cancelled.")
            return
    
    try:
        # Initialize enhanced migrator
        migrator = EnhancedRedisMigrator(dry_run=dry_run)
        
        # Run migration
        migrator.scan_and_migrate()
        
        # Generate report
        migrator.generate_report()
        
        # Final summary
        success_rate = (migrator.migration_stats['migrated_successfully'] / 
                       max(migrator.migration_stats['total_keys_found'], 1)) * 100
        
        print(f"\n🎉 Enhanced migration completed!")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Keys processed: {migrator.migration_stats['migrated_successfully']}/{migrator.migration_stats['total_keys_found']}")
        
        if dry_run:
            print("\n💡 This was a DRY RUN. No changes were made to Redis.")
            print("   Run with --live flag to perform actual migration.")
        
    except KeyboardInterrupt:
        logger.info("Enhanced migration interrupted by user")
    except Exception as e:
        logger.error(f"Enhanced migration failed: {e}")
        raise


if __name__ == "__main__":
    main()