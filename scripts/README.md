# Scripts Directory

This directory contains various utility and maintenance scripts for the Meta Glasses Gemini project.

## Directory Structure

```
scripts/
├── README.md                           # This file
├── cleanup_fix_scripts.py             # Script to organize temporary fix scripts
├── LIMITLESS_SPEAKER_FIX_SUMMARY.md   # Documentation of speaker identification fixes
├── fixes/                             # Temporary fix scripts (archived)
├── MIGRATION_README.md                # Redis migration documentation
├── analyze_redis_keys.py              # Redis key analysis utility
├── cleanup_old_redis_keys.py          # Redis cleanup utility
├── migrate_redis_keys.py              # Redis migration script
├── migrate_redis_keys_enhanced.py     # Enhanced Redis migration
└── test_migration_logic.py            # Migration testing script
```

## Script Categories

### 📋 Documentation
- `LIMITLESS_SPEAKER_FIX_SUMMARY.md` - Complete documentation of the speaker identification bug fixes
- `MIGRATION_README.md` - Redis key migration documentation and procedures

### 🔧 Maintenance Scripts
- `cleanup_fix_scripts.py` - Organizes temporary fix scripts into the fixes/ folder
- `cleanup_old_redis_keys.py` - Removes outdated Redis keys to free up memory

### 🔄 Migration Scripts
- `migrate_redis_keys.py` - Basic Redis key migration utility
- `migrate_redis_keys_enhanced.py` - Enhanced version with better error handling
- `test_migration_logic.py` - Tests migration logic before applying changes

### 📊 Analysis Tools
- `analyze_redis_keys.py` - Analyzes Redis key patterns and usage statistics

### 🩹 Historical Fixes (`fixes/` folder)
The `fixes/` directory contains archived scripts that were used to resolve specific issues:

#### Speaker Identification Fixes
- `fix_limitless_speakers.py` - Initial fix for Unknown speakers
- `fix_limitless_speakers_v2.py` - Enhanced version with better detection
- `fix_false_speakers.py` - Fixed speakers with `is_speaker=False`
- `fix_speaker_naming_bug.py` - Fixed generic "Speaker" labels
- `repair_limitless_speakers_v2.py` - Comprehensive speaker repair utility
- `emergency_speaker_fix.py` - Emergency fix for critical speaker issues

#### Debug Scripts
- `debug_limitless_speakers.py` - Debug speaker identification issues
- `debug_new_recordings.py` - Debug new recording processing
- `debug_speaker_naming.py` - Debug specific speaker naming problems
- `diagnose_unknown_speaker.py` - Diagnose Unknown speaker occurrences
- `check_all_limitless_data.py` - Comprehensive data validation

## Usage Guidelines

### Running Scripts
Most scripts should be run from the project root directory:

```bash
# From project root
python3 scripts/script_name.py
```

### Safety Notes
- **Test scripts** in a development environment before production use
- **Backup data** before running migration or cleanup scripts
- **Review logs** carefully after running maintenance scripts

### Adding New Scripts
When adding new scripts to this directory:

1. **Include documentation** in the script header explaining its purpose
2. **Add logging** for important operations and errors
3. **Use appropriate subdirectories** (`fixes/` for temporary fixes, etc.)
4. **Update this README** to include the new script

## Historical Context

The `fixes/` directory preserves scripts that were created to resolve the Limitless speaker identification system issues in June 2025. These scripts successfully:

- Converted "Unknown" speakers to proper "Speaker N" naming
- Fixed speakers with incorrect `is_speaker` flags
- Resolved generic "Speaker" labels without numbers
- Standardized speaker naming across all recordings

These scripts are preserved for reference and potential future use, but the core issues have been resolved in the main codebase.