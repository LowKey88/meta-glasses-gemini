#!/usr/bin/env python3
"""
Script to fix all existing cached Limitless recordings with Unknown speakers.
This will update all cached recordings to use proper Speaker N naming.
"""

import json
import logging
from utils.redis_utils import r as redis_client
from utils.redis_key_builder import RedisKeyBuilder
from functionality.limitless import standardize_cached_speakers, validate_speaker_names

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_all_cached_recordings():
    """Fix all cached Limitless recordings to use proper Speaker N naming."""
    
    pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
    fixed_count = 0
    total_count = 0
    
    logger.info("🔍 Scanning for cached Limitless recordings with Unknown speakers...")
    
    for key in redis_client.scan_iter(match=pattern):
        total_count += 1
        data = redis_client.get(key)
        if not data:
            continue
            
        try:
            log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
            log_id = log_data.get('id', 'unknown')
            extracted = log_data.get('extracted', {})
            people = extracted.get('people', [])
            
            # Check if this recording has Unknown speakers
            has_unknown = False
            for person in people:
                person_name = person.get('name', '')
                if (person_name.lower() in ['unknown', 'unknown speaker', 'unidentified', 'unidentified speaker', ''] or
                    not person_name.strip()) and person.get('is_speaker'):
                    has_unknown = True
                    break
            
            if has_unknown:
                logger.info(f"🔧 Fixing recording {log_id[:8]}... with Unknown speakers")
                
                # Apply comprehensive fixes
                extracted = standardize_cached_speakers(extracted)
                extracted = validate_speaker_names(extracted, log_id)
                
                # Update the cached data
                log_data['extracted'] = extracted
                
                # Save back to Redis
                redis_client.setex(
                    key,
                    86400 * 7,  # Keep for 7 days
                    json.dumps(log_data)
                )
                
                fixed_count += 1
                
                # Log the speakers after fix
                fixed_speakers = [p.get('name') for p in extracted.get('people', []) if p.get('is_speaker')]
                logger.info(f"✅ Fixed {log_id[:8]}... speakers: {fixed_speakers}")
                
        except json.JSONDecodeError:
            logger.error(f"❌ Failed to parse cached data for key: {key}")
            continue
        except Exception as e:
            logger.error(f"❌ Error processing key {key}: {str(e)}")
            continue
    
    logger.info(f"🎉 Completed! Fixed {fixed_count} recordings out of {total_count} total cached recordings")
    
    if fixed_count > 0:
        logger.info("🔄 All Unknown speakers have been converted to proper Speaker N naming")
        logger.info("📱 Dashboard should now show consistent Speaker 0, Speaker 1, Speaker 2, etc.")
    else:
        logger.info("✨ No Unknown speakers found in cached data")

if __name__ == "__main__":
    fix_all_cached_recordings()