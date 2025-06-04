# Redis Key Migration Guide

This directory contains scripts for migrating Redis keys from the old naming convention to the new clean hierarchical structure.

## Migration Overview

### Old Pattern
```
josancamon:rayban-meta-glasses-api:{type}:{id}
```

### New Pattern
```
meta-glasses:{category}:{subcategory}:{identifier}
```

## Scripts

### 1. `analyze_redis_keys.py` - Pre-Migration Analysis
**Purpose**: Analyze current Redis keys to understand data patterns before migration.

```bash
# Analyze current Redis state
python scripts/analyze_redis_keys.py
```

**Output**:
- Key count and distribution
- Size statistics
- TTL patterns
- Sample keys for review
- Migration impact assessment

### 2. `test_migration_logic.py` - Logic Validation
**Purpose**: Test migration logic without connecting to Redis.

```bash
# Test migration logic
python scripts/test_migration_logic.py
```

**Features**:
- Tests key identification patterns
- Validates new key generation
- Checks for key collisions
- Tests edge cases and base64 encoding

### 3. `migrate_redis_keys.py` - Main Migration Script
**Purpose**: Perform the actual Redis key migration.

```bash
# DRY RUN (recommended first)
python scripts/migrate_redis_keys.py --dry-run

# LIVE MIGRATION (after testing)
python scripts/migrate_redis_keys.py --live --validate
```

**Features**:
- Scans all keys with old prefix
- Identifies key types automatically
- Migrates data preserving TTL
- Comprehensive logging and reporting
- Validation of migration results
- Safety checks and confirmations

## Migration Process

### Step 1: Pre-Migration Analysis
```bash
# 1. Analyze current Redis state
python scripts/analyze_redis_keys.py

# 2. Review the analysis report
# Check key counts, patterns, and data sizes
```

### Step 2: Test Migration Logic
```bash
# 3. Test migration logic
python scripts/test_migration_logic.py

# 4. Verify all expected patterns work correctly
```

### Step 3: Dry Run Migration
```bash
# 5. Perform dry run migration
python scripts/migrate_redis_keys.py --dry-run

# 6. Review migration logs and reports
# Check migration_report_*.json for details
```

### Step 4: Live Migration
```bash
# 7. Create Redis backup (recommended)
# Use your Redis backup strategy

# 8. Run live migration
python scripts/migrate_redis_keys.py --live --validate

# 9. Monitor logs and validate results
```

### Step 5: Post-Migration Validation
```bash
# 10. Run analysis again to verify new state
python scripts/analyze_redis_keys.py

# 11. Test application functionality
# 12. Monitor for any issues
```

## Key Type Mappings

| Old Pattern | New Pattern | Description |
|-------------|-------------|-------------|
| `josancamon:rayban-meta-glasses-api:{base64}` | `meta-glasses:cache:generic:{base64}` | Generic cache data |
| `josancamon:rayban-meta-glasses-api:reminder:{event_id}` | `meta-glasses:reminder:event:{event_id}` | Calendar reminders |
| `josancamon:rayban-meta-glasses-api:conversation_history:{user_id}` | `meta-glasses:user:history:{user_id}` | User chat history |
| `josancamon:rayban-meta-glasses-api:user_profile:{user_id}` | `meta-glasses:user:profile:{user_id}` | User profiles |
| `josancamon:rayban-meta-glasses-api:cancellation:wa:{user_id}` | `meta-glasses:state:cancellation:wa:{user_id}` | Cancellation state |

## Safety Features

### Migration Script Safety
- **Dry run mode by default** - No changes made without explicit confirmation
- **Data preservation** - Uses DUMP/RESTORE to maintain exact TTL
- **Duplicate key detection** - Skips if new key already exists
- **Comprehensive logging** - All operations logged with timestamps
- **Error handling** - Continues migration even if individual keys fail
- **Validation** - Compares old vs new data after migration

### Rollback Strategy
- **Old keys are preserved** - Original keys not deleted during migration
- **Incremental approach** - Can migrate in batches if needed
- **Application compatibility** - New code uses new keys, falls back to old if needed

## File Outputs

### Log Files
- `redis_migration_YYYYMMDD_HHMMSS.log` - Detailed migration log
- `migration_report_YYYYMMDD_HHMMSS.json` - Structured migration report
- `redis_analysis_YYYYMMDD_HHMMSS.json` - Analysis results

### Report Contents
```json
{
  "migration_stats": {
    "total_keys_found": 150,
    "migrated_successfully": 145,
    "migration_errors": 5,
    "cache_keys": 80,
    "reminder_keys": 25,
    "user_history_keys": 20,
    "user_profile_keys": 15,
    "cancellation_keys": 5
  },
  "migrated_keys": [...],
  "error_keys": [...],
  "dry_run": true,
  "timestamp": "2024-01-15T10:30:00"
}
```

## Troubleshooting

### Common Issues

**Connection Refused**
```bash
# Check Redis connection settings in utils/redis_utils.py
# Ensure Redis server is running and accessible
```

**Permission Denied**
```bash
# Make scripts executable
chmod +x scripts/*.py
```

**Import Errors**
```bash
# Ensure you're running from project root
cd /path/to/meta-glasses-gemini
python scripts/migrate_redis_keys.py
```

**Large Dataset Migration**
```bash
# For large datasets, consider migrating in batches
# Monitor Redis memory usage during migration
# Use --dry-run first to estimate impact
```

### Recovery Procedures

**If Migration Fails**
1. Review error logs for specific failures
2. Old keys are still intact - no data loss
3. Fix issues and re-run migration for failed keys
4. Application will continue using old keys until migration completes

**If Application Issues Occur**
1. Application code supports both old and new keys
2. Check logs for key lookup failures
3. Verify new keys exist and have correct data
4. Rollback by stopping migration and using old keys

## Best Practices

1. **Always start with analysis** - Understand your data first
2. **Test logic separately** - Validate migration patterns
3. **Use dry run mode** - Never skip the dry run
4. **Monitor during migration** - Watch for errors and memory usage
5. **Validate results** - Compare old vs new key data
6. **Keep backups** - Have a recovery plan
7. **Migrate during low traffic** - Minimize impact on users

## Support

For issues with migration scripts:
1. Check the log files for detailed error information
2. Review this documentation for troubleshooting steps
3. Test with smaller datasets first
4. Verify Redis connection and permissions