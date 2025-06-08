#!/usr/bin/env python3
"""
Cleanup script to remove temporary fix scripts now that the speaker identification system is fixed.
"""

import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_fix_scripts():
    """Remove temporary fix scripts that are no longer needed."""
    
    # List of temporary fix scripts that can be safely removed
    temp_scripts = [
        'fix_limitless_speakers.py',
        'fix_limitless_speakers_v2.py', 
        'fix_false_speakers.py',
        'fix_speaker_naming_bug.py',
        'repair_limitless_speakers_v2.py',
        'debug_limitless_speakers.py',
        'debug_new_recordings.py',
        'debug_speaker_naming.py',
        'diagnose_unknown_speaker.py',
        'check_all_limitless_data.py',
        'emergency_speaker_fix.py'
    ]
    
    logger.info("🧹 Cleaning up temporary fix scripts...")
    
    removed_count = 0
    for script in temp_scripts:
        if os.path.exists(script):
            try:
                os.remove(script)
                logger.info(f"  ✅ Removed: {script}")
                removed_count += 1
            except Exception as e:
                logger.error(f"  ❌ Failed to remove {script}: {e}")
        else:
            logger.debug(f"  ⏭️  Not found: {script}")
    
    logger.info(f"🎉 Cleanup complete! Removed {removed_count} temporary scripts")
    
    # Keep useful documentation
    keep_files = [
        'LIMITLESS_SPEAKER_FIX_SUMMARY.md'
    ]
    
    logger.info("\n📋 Keeping documentation files:")
    for file in keep_files:
        if os.path.exists(file):
            logger.info(f"  📄 Kept: {file}")

if __name__ == "__main__":
    cleanup_fix_scripts()