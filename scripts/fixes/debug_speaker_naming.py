#!/usr/bin/env python3
"""
Debug the specific recording from Jun 8, 07:58 PM to see why it shows "Speaker" instead of "Speaker 1".
"""

import json
import logging
from datetime import datetime
from utils.redis_utils import r as redis_client
from utils.redis_key_builder import RedisKeyBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_speaker_naming():
    """Debug the specific recording with improper Speaker naming."""
    
    pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
    target_time = "07:58 PM"
    target_date = "Jun 8, 2025"
    
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
            
            for field in time_fields:
                if log_data.get(field):
                    try:
                        time_str = log_data.get(field)
                        if 'T' in time_str:
                            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                            # Check if it's around 07:58 PM (19:58)
                            if dt.hour == 19 and 55 <= dt.minute <= 59 and dt.day == 8:
                                recording_time = dt.strftime('%I:%M %p')
                                logger.info(f"📍 Found target recording: {log_id}")
                                logger.info(f"  Time: {recording_time}")
                                logger.info(f"  Title: {log_data.get('title', 'No title')}")
                                
                                # Examine the extracted speakers
                                extracted = log_data.get('extracted', {})
                                people = extracted.get('people', [])
                                
                                logger.info(f"\n👥 EXTRACTED SPEAKERS ({len(people)}):")
                                for i, person in enumerate(people):
                                    name = person.get('name', 'NO NAME')
                                    is_speaker = person.get('is_speaker', 'NOT SET')
                                    context = person.get('context', 'No context')
                                    role = person.get('role', 'No role')
                                    speaker_id = person.get('speaker_id', 'No ID')
                                    
                                    logger.info(f"  [{i}] name='{name}', is_speaker={is_speaker}")
                                    logger.info(f"      context='{context}', role='{role}', speaker_id='{speaker_id}'")
                                    
                                    if name == "Speaker":
                                        logger.warning(f"      ⚠️  FOUND PROBLEMATIC 'Speaker' (should be 'Speaker N')")
                                
                                # Examine the raw contents from Limitless API
                                contents = log_data.get('contents', [])
                                logger.info(f"\n📝 RAW LIMITLESS API CONTENTS ({len(contents)}):")
                                
                                unique_speakers = {}
                                for i, content in enumerate(contents[:10]):  # First 10 contents
                                    speaker_name = content.get('speakerName', 'NO NAME')
                                    speaker_id = content.get('speakerIdentifier', 'NO ID')
                                    text = content.get('content', '')[:50]
                                    
                                    # Track unique speakers
                                    if speaker_id not in unique_speakers:
                                        unique_speakers[speaker_id] = speaker_name
                                    
                                    logger.info(f"  [{i}] speakerName='{speaker_name}', speakerId='{speaker_id}'")
                                    logger.info(f"      content='{text}...'")
                                
                                logger.info(f"\n🆔 UNIQUE SPEAKER IDS FROM API:")
                                for speaker_id, speaker_name in unique_speakers.items():
                                    logger.info(f"  {speaker_id} → '{speaker_name}'")
                                
                                # Check speaker mapping if it exists
                                speaker_mapping = log_data.get('speaker_mapping', {})
                                if speaker_mapping:
                                    logger.info(f"\n🗺️  SPEAKER MAPPING:")
                                    for speaker_id, mapped_name in speaker_mapping.items():
                                        logger.info(f"  {speaker_id} → '{mapped_name}'")
                                else:
                                    logger.info(f"\n🗺️  NO SPEAKER MAPPING FOUND")
                                
                                return log_data
                                
                    except Exception as e:
                        logger.debug(f"Error parsing time for {log_id}: {e}")
                        
        except json.JSONDecodeError:
            continue
    
    logger.warning("❌ Target recording not found")
    return None

if __name__ == "__main__":
    debug_speaker_naming()