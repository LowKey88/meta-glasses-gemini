#!/usr/bin/env python3
"""
Move temporary fix scripts to scripts/fixes folder for organization.
"""

import os
import shutil
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def organize_fix_scripts():
    """Move temporary fix scripts to scripts/fixes folder."""
    
    # List of temporary fix scripts to organize
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
    
    # Create scripts/fixes directory if it doesn't exist
    fixes_dir = "scripts/fixes"
    os.makedirs(fixes_dir, exist_ok=True)
    logger.info(f"📁 Created directory: {fixes_dir}")
    
    logger.info("📦 Moving temporary fix scripts to scripts/fixes...")
    
    moved_count = 0
    for script in temp_scripts:
        if os.path.exists(script):
            try:
                destination = os.path.join(fixes_dir, script)
                shutil.move(script, destination)
                logger.info(f"  ✅ Moved: {script} → {destination}")
                moved_count += 1
            except Exception as e:
                logger.error(f"  ❌ Failed to move {script}: {e}")
        else:
            logger.debug(f"  ⏭️  Not found: {script}")
    
    logger.info(f"🎉 Organization complete! Moved {moved_count} scripts to scripts/fixes/")
    
    # Keep useful documentation files in root
    keep_files = [
        'LIMITLESS_SPEAKER_FIX_SUMMARY.md'
    ]
    
    logger.info("\n📋 Keeping documentation files in root:")
    for file in keep_files:
        if os.path.exists(file):
            logger.info(f"  📄 Kept: {file}")

if __name__ == "__main__":
    organize_fix_scripts()