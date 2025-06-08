#!/usr/bin/env python3
"""
Fix Unknown speakers where is_speaker=False (missed by previous fix).
"""

import json
import logging
from utils.redis_utils import r as redis_client
from utils.redis_key_builder import RedisKeyBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_false_speakers():
    """Fix Unknown speakers that have is_speaker=False."""
    
    pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
    fixed_count = 0
    total_count = 0
    
    logger.info("🔍 Scanning for Unknown speakers with is_speaker=False...")
    
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
            
            # Check for Unknown speakers regardless of is_speaker value
            has_unknown = False
            for person in people:
                person_name = person.get('name', '')
                if person_name.lower() in ['unknown', 'unknown speaker', 'unidentified', 'unidentified speaker']:
                    has_unknown = True
                    logger.warning(f"Found Unknown speaker in {log_id}: {person}")
                    break
            
            if has_unknown:
                logger.info(f"🔧 Fixing recording {log_id[:8]}... with Unknown speakers")
                
                # Fix all Unknown speakers, regardless of is_speaker value
                speaker_counter = 0
                for person in people:
                    person_name = person.get('name', '')
                    if person_name.lower() in ['unknown', 'unknown speaker', 'unidentified', 'unidentified speaker']:
                        new_name = f"Speaker {speaker_counter}"
                        old_name = person_name
                        person['name'] = new_name
                        person['context'] = 'Unrecognized speaker in conversation'
                        
                        # Fix the is_speaker flag if needed
                        if person.get('context') == 'Identified speaker in conversation':
                            person['is_speaker'] = True
                        
                        logger.info(f"  Fixed: '{old_name}' → '{new_name}' (is_speaker: {person.get('is_speaker')})")
                        speaker_counter += 1
                
                # Update the cached data
                log_data['extracted'] = extracted
                
                # Save back to Redis
                redis_client.setex(
                    key,
                    86400 * 7,  # Keep for 7 days
                    json.dumps(log_data)
                )
                
                fixed_count += 1
                logger.info(f"✅ Fixed recording {log_id[:8]}...")
                
        except json.JSONDecodeError:
            logger.error(f"❌ Failed to parse cached data for key: {key}")
            continue
        except Exception as e:
            logger.error(f"❌ Error processing key {key}: {str(e)}")
            continue
    
    logger.info(f"🎉 Completed! Fixed {fixed_count} recordings out of {total_count} total cached recordings")

if __name__ == "__main__":
    fix_false_speakers()