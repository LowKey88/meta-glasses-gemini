#!/usr/bin/env python3
"""
Redis Key Migration Script

Migrates Redis keys from old naming convention:
  josancamon:rayban-meta-glasses-api:{type}:{id}

To new naming convention:
  meta-glasses:{category}:{subcategory}:{id}

This script:
1. Scans all keys with the old prefix
2. Identifies key types and purposes
3. Converts to new format using RedisKeyBuilder
4. Copies data preserving TTL
5. Logs all operations for audit
6. Does NOT delete old keys (for safety)
"""

import sys
import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import base64

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_utils import r
from utils.redis_key_builder import RedisKeyBuilder
from utils.redis_monitor import redis_monitor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'redis_migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RedisMigrator:
    """Handles migration of Redis keys from old to new naming convention."""
    
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
        Identify the type and extract components from an old key.
        
        Returns:
            Tuple of (key_type, components_dict)
        """
        # Remove the prefix to get the key suffix
        if not key.startswith(self.old_prefix):
            return "unknown", {}
            
        suffix = key[len(self.old_prefix):].lstrip(":")
        parts = suffix.split(":")
        
        if not parts:
            return "unknown", {}
            
        # Generic cache keys (base64 encoded paths)
        if len(parts) == 1:
            try:
                # Try to decode as base64 to confirm it's a cache key
                decoded = base64.b64decode(parts[0]).decode('utf-8')
                return "cache", {"encoded_path": parts[0], "original_path": decoded}
            except:
                return "unknown", {"suffix": suffix}
        
        # Reminder keys: reminder:{event_id}
        elif len(parts) == 2 and parts[0] == "reminder":
            return "reminder", {"event_id": parts[1]}
        
        # User data keys: {type}:{user_id}
        elif len(parts) == 2:
            key_type = parts[0]
            user_id = parts[1]
            
            if key_type == "conversation_history":
                return "user_history", {"user_id": user_id}
            elif key_type == "user_profile":
                return "user_profile", {"user_id": user_id}
            else:
                return "unknown", {"type": key_type, "user_id": user_id}
        
        # Cancellation state keys: cancellation:wa:{user_id}
        elif len(parts) == 3 and parts[0] == "cancellation":
            return "cancellation", {"platform": parts[1], "user_id": parts[2]}
        
        else:
            return "unknown", {"suffix": suffix, "parts": parts}
    
    def generate_new_key(self, key_type: str, components: Dict[str, str]) -> Optional[str]:
        """Generate new key using RedisKeyBuilder based on old key type."""
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
            
            else:
                logger.warning(f"Unknown key type for new key generation: {key_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating new key for type {key_type}: {e}")
            return None
    
    def migrate_key(self, old_key: str) -> bool:
        """
        Migrate a single key from old to new format.
        
        Returns:
            True if migration successful, False otherwise
        """
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
        """Scan all keys with old prefix and migrate them."""
        logger.info(f"Starting Redis key migration (dry_run={self.dry_run})")
        logger.info(f"Scanning for keys with prefix: {self.old_prefix}")
        
        # Scan for all old keys
        pattern = f"{self.old_prefix}:*"
        old_keys = []
        
        try:
            for key in r.scan_iter(match=pattern):
                key_str = key.decode() if isinstance(key, bytes) else key
                old_keys.append(key_str)
                
            self.migration_stats['total_keys_found'] = len(old_keys)
            logger.info(f"Found {len(old_keys)} keys to migrate")
            
            if len(old_keys) == 0:
                logger.info("No keys found with old prefix. Migration complete.")
                return
            
            # Migrate each key
            for i, old_key in enumerate(old_keys, 1):
                logger.info(f"Processing key {i}/{len(old_keys)}: {old_key}")
                self.migrate_key(old_key)
                
                # Small delay to prevent overwhelming Redis
                if i % 100 == 0:
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"Error during migration scan: {e}")
            raise
    
    def validate_migration(self) -> bool:
        """Validate that migration was successful."""
        logger.info("Validating migration...")
        
        validation_errors = []
        
        # Check each migrated key
        for migration in self.migrated_keys:
            old_key = migration["old_key"]
            new_key = migration["new_key"]
            
            try:
                # Check if old key still exists
                if not r.exists(old_key):
                    validation_errors.append(f"Old key missing: {old_key}")
                    continue
                
                # Check if new key exists (only for non-dry-run)
                if not self.dry_run and not r.exists(new_key):
                    validation_errors.append(f"New key missing: {new_key}")
                    continue
                
                # Compare data if not dry run
                if not self.dry_run:
                    old_data = r.get(old_key)
                    new_data = r.get(new_key)
                    
                    if old_data != new_data:
                        validation_errors.append(f"Data mismatch for {old_key} -> {new_key}")
                        
            except Exception as e:
                validation_errors.append(f"Validation error for {old_key}: {e}")
        
        if validation_errors:
            logger.error(f"Validation failed with {len(validation_errors)} errors:")
            for error in validation_errors[:10]:  # Show first 10 errors
                logger.error(f"  - {error}")
            return False
        else:
            logger.info("✅ Migration validation successful!")
            return True
    
    def generate_report(self) -> None:
        """Generate detailed migration report."""
        logger.info("=" * 80)
        logger.info("REDIS KEY MIGRATION REPORT")
        logger.info("=" * 80)
        
        # Summary statistics
        logger.info("MIGRATION SUMMARY:")
        for key, value in self.migration_stats.items():
            logger.info(f"  {key.replace('_', ' ').title()}: {value}")
        
        logger.info("")
        logger.info(f"Migration Mode: {'DRY RUN' if self.dry_run else 'LIVE MIGRATION'}")
        logger.info(f"Total Processing Time: {datetime.now()}")
        
        # Key type breakdown
        logger.info("")
        logger.info("KEY TYPE BREAKDOWN:")
        key_types = ['cache_keys', 'reminder_keys', 'user_history_keys', 'user_profile_keys', 'cancellation_keys', 'unknown_keys']
        for key_type in key_types:
            count = self.migration_stats.get(key_type, 0)
            if count > 0:
                logger.info(f"  {key_type.replace('_', ' ').title()}: {count}")
        
        # Sample migrations
        if self.migrated_keys:
            logger.info("")
            logger.info("SAMPLE MIGRATIONS (first 5):")
            for migration in self.migrated_keys[:5]:
                logger.info(f"  {migration['old_key']} -> {migration['new_key']}")
        
        # Errors
        if self.error_keys:
            logger.info("")
            logger.info(f"MIGRATION ERRORS ({len(self.error_keys)}):")
            for error in self.error_keys[:10]:  # Show first 10 errors
                logger.info(f"  {error['key']}: {error['error']}")
        
        # Save detailed report to file
        report_file = f'migration_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
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
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate Redis keys to new naming convention')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Run in dry-run mode (default: True)')
    parser.add_argument('--live', action='store_true', default=False,
                        help='Run live migration (WARNING: modifies Redis data)')
    parser.add_argument('--validate', action='store_true', default=True,
                        help='Validate migration results (default: True)')
    
    args = parser.parse_args()
    
    # Determine run mode
    dry_run = not args.live  # Default to dry run unless --live specified
    
    if not dry_run:
        print("⚠️  WARNING: You are about to run a LIVE migration that will modify Redis data!")
        print("⚠️  Make sure you have a backup and understand the consequences.")
        response = input("Type 'YES' to confirm live migration: ")
        if response != 'YES':
            print("Migration cancelled.")
            return
    
    try:
        # Initialize migrator
        migrator = RedisMigrator(dry_run=dry_run)
        
        # Run migration
        migrator.scan_and_migrate()
        
        # Validate if requested
        if args.validate:
            migrator.validate_migration()
        
        # Generate report
        migrator.generate_report()
        
        # Final summary
        success_rate = (migrator.migration_stats['migrated_successfully'] / 
                       max(migrator.migration_stats['total_keys_found'], 1)) * 100
        
        print(f"\n🎉 Migration completed!")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Keys processed: {migrator.migration_stats['migrated_successfully']}/{migrator.migration_stats['total_keys_found']}")
        
        if dry_run:
            print("\n💡 This was a DRY RUN. No changes were made to Redis.")
            print("   Run with --live flag to perform actual migration.")
        
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    main()