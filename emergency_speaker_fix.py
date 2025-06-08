#!/usr/bin/env python3
"""
Emergency script to monitor and fix Unknown speakers in real-time.
Run this alongside your main application to catch any Unknown speakers.
"""

import json
import logging
import time
from utils.redis_utils import r as redis_client
from utils.redis_key_builder import RedisKeyBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def monitor_and_fix_unknown_speakers():
    """Monitor for new recordings and fix any Unknown speakers immediately."""
    
    logger.info("🚨 Starting emergency Unknown speaker monitor...")
    logger.info("This will check for new recordings every 30 seconds and fix any Unknown speakers")
    
    processed_recordings = set()
    
    while True:
        try:
            # Get all cached recordings
            pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
            
            for key in redis_client.scan_iter(match=pattern):
                # Skip if we've already processed this recording
                if key in processed_recordings:
                    continue
                
                data = redis_client.get(key)
                if not data:
                    continue
                
                try:
                    log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                    log_id = log_data.get('id', 'unknown')
                    extracted = log_data.get('extracted', {})
                    people = extracted.get('people', [])
                    
                    # Check for Unknown speakers
                    has_unknown = False
                    for person in people:
                        person_name = person.get('name', '')
                        if (person_name.lower() in ['unknown', 'unknown speaker', 'unidentified'] and 
                            person.get('is_speaker')):
                            has_unknown = True
                            break
                    
                    if has_unknown:
                        logger.warning(f"🚨 EMERGENCY FIX: Found Unknown speaker in NEW recording {log_id[:8]}...")
                        
                        # Fix the speakers
                        speaker_counter = 0
                        for person in people:
                            person_name = person.get('name', '')
                            if (person_name.lower() in ['unknown', 'unknown speaker', 'unidentified'] and
                                person.get('is_speaker')):
                                new_name = f"Speaker {speaker_counter}"
                                person['name'] = new_name
                                person['context'] = 'Unrecognized speaker in conversation'
                                logger.info(f"  Fixed: '{person_name}' → '{new_name}'")
                                speaker_counter += 1
                        
                        # Save the fixed data back
                        log_data['extracted'] = extracted
                        redis_client.setex(key, 86400 * 7, json.dumps(log_data))
                        logger.info(f"✅ Saved fixed recording {log_id[:8]}...")
                    
                    # Mark as processed
                    processed_recordings.add(key)
                    
                except Exception as e:
                    logger.error(f"Error processing recording: {str(e)}")
                    continue
            
            # Wait before next check
            time.sleep(30)
            
        except KeyboardInterrupt:
            logger.info("Monitor stopped by user")
            break
        except Exception as e:
            logger.error(f"Monitor error: {str(e)}")
            time.sleep(30)

if __name__ == "__main__":
    monitor_and_fix_unknown_speakers()