#!/usr/bin/env python3
"""
Enhanced repair script for Limitless speakers in cached data.
This version uses the improved speaker extraction that properly handles:
- Multiple speakers with the same name (e.g., "Unknown")
- Empty speaker names
- Proper Speaker N numbering
"""

import json
import logging
from datetime import datetime
from utils.redis_utils import r as redis_client
from utils.redis_key_builder import RedisKeyBuilder
from functionality.limitless import extract_speakers_from_contents, standardize_cached_speakers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def repair_all_cached_recordings():
    """
    Repair all cached Limitless recordings to use proper speaker names.
    Uses the enhanced extract_speakers_from_contents function.
    """
    pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
    
    fixed_count = 0
    total_count = 0
    recordings_with_unknown = []
    
    logger.info("🔧 Starting enhanced speaker repair for all cached recordings...")
    
    for key in redis_client.scan_iter(match=pattern):
        total_count += 1
        
        try:
            # Get cached data
            data = redis_client.get(key)
            if not data:
                continue
            
            log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
            log_id = log_data.get('id', 'unknown')
            
            # Check if we have contents to reprocess
            if 'contents' not in log_data:
                logger.debug(f"No contents found for {log_id[:8]}..., loading from API would be needed")
                continue
            
            # Re-extract speakers using the fixed function
            old_extracted = log_data.get('extracted', {})
            old_people = old_extracted.get('people', [])
            
            # Check if any Unknown speakers exist
            has_unknown = any(
                'unknown' in person.get('name', '').lower() 
                for person in old_people 
                if person.get('is_speaker', False)
            )
            
            if has_unknown:
                recordings_with_unknown.append(log_id)
                
                # Create a minimal log object with contents for speaker extraction
                temp_log = {
                    'id': log_id,
                    'contents': log_data.get('contents', [])
                }
                
                # Re-extract speakers with the fixed function
                new_speakers = extract_speakers_from_contents(temp_log)
                
                logger.info(f"Recording {log_id[:8]}... - Old speakers: {[p['name'] for p in old_people if p.get('is_speaker')]}")
                logger.info(f"Recording {log_id[:8]}... - New speakers: {[s['name'] for s in new_speakers]}")
                
                # Update the people list
                # First, remove all old speakers
                non_speaker_people = [p for p in old_people if not p.get('is_speaker', False)]
                
                # Add the new speakers
                new_people = []
                for speaker in new_speakers:
                    new_people.append({
                        'name': speaker['name'],
                        'context': speaker['context'],
                        'is_speaker': True,
                        'role': speaker.get('role', 'participant')
                    })
                
                # Add back non-speaker people
                new_people.extend(non_speaker_people)
                
                # Update extracted data
                old_extracted['people'] = new_people
                
                # Also update speaker mapping if available
                if '_speaker_mapping' in temp_log:
                    log_data['speaker_mapping'] = temp_log['_speaker_mapping']
                
                # Save updated data back to Redis
                redis_client.setex(
                    key,
                    86400 * 7,  # Keep same TTL (7 days)
                    json.dumps(log_data)
                )
                
                fixed_count += 1
                logger.info(f"✅ Fixed recording {log_id[:8]}...")
            
        except Exception as e:
            logger.error(f"Error processing {key}: {str(e)}")
            continue
    
    logger.info(f"\n📊 Repair Summary:")
    logger.info(f"   Total recordings scanned: {total_count}")
    logger.info(f"   Recordings with Unknown speakers: {len(recordings_with_unknown)}")
    logger.info(f"   Recordings fixed: {fixed_count}")
    
    if recordings_with_unknown:
        logger.info(f"\n📝 Fixed recording IDs:")
        for log_id in recordings_with_unknown[:10]:
            logger.info(f"   - {log_id}")
        if len(recordings_with_unknown) > 10:
            logger.info(f"   ... and {len(recordings_with_unknown) - 10} more")

if __name__ == "__main__":
    repair_all_cached_recordings()