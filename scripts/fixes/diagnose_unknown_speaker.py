#!/usr/bin/env python3
"""
Diagnostic script to find the specific recording with Unknown speaker from Jun 8, 07:10 PM.
"""

import json
import logging
from datetime import datetime
from utils.redis_utils import r as redis_client
from utils.redis_key_builder import RedisKeyBuilder

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def find_specific_recording():
    """Find the recording from Jun 8, 07:10 PM that shows Unknown speaker."""
    
    pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
    target_time = "07:10 PM"
    target_date = "Jun 8, 2025"
    found_count = 0
    
    logger.info(f"🔍 Searching for recording from {target_date} around {target_time}...")
    
    for key in redis_client.scan_iter(match=pattern):
        data = redis_client.get(key)
        if not data:
            continue
            
        try:
            log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
            log_id = log_data.get('id', 'unknown')
            
            # Check various time fields
            time_fields = ['start_time', 'startTime', 'created_at', 'createdAt', 'processed_at']
            recording_time = None
            
            for field in time_fields:
                if log_data.get(field):
                    try:
                        # Parse the time
                        time_str = log_data.get(field)
                        if 'T' in time_str:
                            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                            # Check if it's around 07:10 PM (19:10)
                            if dt.hour == 19 and 5 <= dt.minute <= 15 and dt.day == 8:
                                recording_time = dt.strftime('%I:%M %p')
                                logger.info(f"📍 Found recording from {recording_time}: {log_id}")
                                found_count += 1
                                
                                # Examine the speakers
                                extracted = log_data.get('extracted', {})
                                people = extracted.get('people', [])
                                
                                logger.info(f"  Title: {log_data.get('title', 'No title')}")
                                logger.info(f"  Summary: {log_data.get('summary', 'No summary')[:100]}...")
                                logger.info(f"  People count: {len(people)}")
                                
                                for i, person in enumerate(people):
                                    name = person.get('name', 'NO NAME')
                                    is_speaker = person.get('is_speaker', False)
                                    context = person.get('context', 'No context')
                                    logger.info(f"    Person {i}: name='{name}', is_speaker={is_speaker}, context='{context}'")
                                    
                                    # Check if this is the Unknown speaker
                                    if name.lower() in ['unknown', 'unknown speaker']:
                                        logger.warning(f"    ⚠️  FOUND UNKNOWN SPEAKER!")
                                
                                # Also check the raw contents
                                contents = log_data.get('contents', [])
                                if contents:
                                    logger.info(f"  Raw contents count: {len(contents)}")
                                    for i, content in enumerate(contents[:3]):  # First 3 contents
                                        speaker_name = content.get('speakerName', 'NO NAME')
                                        speaker_id = content.get('speakerIdentifier', 'NO ID')
                                        text = content.get('content', '')[:50]
                                        logger.info(f"    Content {i}: speakerName='{speaker_name}', speakerId='{speaker_id}', text='{text}...'")
                                
                                logger.info("-" * 80)
                                break
                    except Exception as e:
                        logger.debug(f"Error parsing time for {log_id}: {e}")
                        
        except json.JSONDecodeError:
            logger.error(f"Failed to parse data for key: {key}")
            continue
    
    if found_count == 0:
        logger.warning(f"❌ No recordings found from {target_date} around {target_time}")
        logger.info("Searching for recent recordings with Unknown speakers...")
        
        # Search for any recent Unknown speakers
        for key in redis_client.scan_iter(match=pattern):
            data = redis_client.get(key)
            if not data:
                continue
                
            try:
                log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                log_id = log_data.get('id', 'unknown')
                extracted = log_data.get('extracted', {})
                people = extracted.get('people', [])
                
                for person in people:
                    name = person.get('name', '')
                    if name.lower() in ['unknown', 'unknown speaker'] and person.get('is_speaker'):
                        # Found one!
                        logger.warning(f"🚨 Found Unknown speaker in recording {log_id}")
                        logger.info(f"  Title: {log_data.get('title', 'No title')}")
                        logger.info(f"  Time: {log_data.get('start_time') or log_data.get('created_at', 'Unknown time')}")
                        logger.info(f"  Full person data: {person}")
                        found_count += 1
                        break
                        
            except Exception as e:
                continue
    
    logger.info(f"\n📊 Summary: Found {found_count} recordings with issues")

if __name__ == "__main__":
    find_specific_recording()