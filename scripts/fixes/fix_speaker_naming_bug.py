#!/usr/bin/env python3
"""
Fix recordings that have "Speaker" instead of "Speaker N" naming.
"""

import json
import logging
from utils.redis_utils import r as redis_client
from utils.redis_key_builder import RedisKeyBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_speaker_naming_bug():
    """Fix recordings that have 'Speaker' instead of proper 'Speaker N' naming."""
    
    pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
    fixed_count = 0
    total_count = 0
    
    logger.info("🔍 Scanning for recordings with 'Speaker' naming bug...")
    
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
            
            # Check for "Speaker" without number
            has_speaker_bug = False
            for person in people:
                person_name = person.get('name', '')
                if person_name == 'Speaker' and person.get('is_speaker'):
                    has_speaker_bug = True
                    logger.warning(f"Found 'Speaker' bug in {log_id}: {person}")
                    break
            
            if has_speaker_bug:
                logger.info(f"🔧 Fixing recording {log_id[:8]}... with Speaker naming bug")
                
                # Find the highest existing Speaker N number
                max_speaker_num = -1
                for person in people:
                    person_name = person.get('name', '')
                    if person_name.startswith('Speaker ') and person.get('is_speaker'):
                        try:
                            num = int(person_name.split(' ')[1])
                            max_speaker_num = max(max_speaker_num, num)
                        except (IndexError, ValueError):
                            pass
                
                # Fix all "Speaker" entries
                next_speaker_num = max_speaker_num + 1
                for person in people:
                    person_name = person.get('name', '')
                    if person_name == 'Speaker' and person.get('is_speaker'):
                        new_name = f"Speaker {next_speaker_num}"
                        person['name'] = new_name
                        person['context'] = 'Unrecognized speaker in conversation'
                        logger.info(f"  Fixed: 'Speaker' → '{new_name}'")
                        next_speaker_num += 1
                
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
    fix_speaker_naming_bug()