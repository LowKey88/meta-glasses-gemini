#!/usr/bin/env python3
"""
Debug script to check the most recent Limitless recordings and their speaker data.
Focus on recordings from around 07:10 PM to understand the Unknown speaker issue.
"""

import json
import asyncio
from datetime import datetime, timedelta
from utils.limitless_api import LimitlessAPIClient
from utils.redis_utils import r as redis_client
from utils.redis_key_builder import RedisKeyBuilder

async def debug_recent_recordings():
    """Debug the most recent recordings to find Unknown speaker issues."""
    
    client = LimitlessAPIClient()
    
    # Get recordings from the last 6 hours
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=6)
    
    print(f"🔍 Fetching recordings from {start_time} to {end_time}")
    
    lifelogs = await client.get_all_lifelogs(
        start_time=start_time,
        end_time=end_time,
        timezone_str="Asia/Kuala_Lumpur",
        max_entries=10,  # Just recent ones
        include_markdown=True,
        include_headings=True
    )
    
    print(f"\n📊 Found {len(lifelogs)} recent recordings")
    
    # Look for recordings around 07:10 PM
    target_time = datetime.strptime("19:10", "%H:%M").time()
    
    for log in lifelogs:
        log_id = log.get('id', 'unknown')
        title = log.get('title', 'Untitled')
        start_time_str = log.get('start_time') or log.get('startTime') or log.get('createdAt')
        
        # Parse time
        recording_time = None
        if start_time_str:
            try:
                recording_dt = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                recording_time = recording_dt.time()
            except:
                pass
        
        print(f"\n{'='*80}")
        print(f"📼 Recording: {title}")
        print(f"   ID: {log_id}")
        print(f"   Time: {start_time_str}")
        
        # Check contents for speaker data
        contents = log.get('contents', [])
        print(f"   Contents count: {len(contents)}")
        
        # Analyze speaker data from API
        speaker_stats = {
            'with_name': 0,
            'without_name': 0,
            'empty_name': 0,
            'user': 0,
            'unknown_ids': []
        }
        
        for i, content in enumerate(contents[:5]):  # First 5 contents
            speaker_name = content.get('speakerName', '')
            speaker_id = content.get('speakerIdentifier', '')
            
            print(f"\n   Content {i+1}:")
            print(f"     speakerName: '{speaker_name}' (empty: {not speaker_name})")
            print(f"     speakerIdentifier: '{speaker_id}'")
            
            # Categorize
            if speaker_id == 'user':
                speaker_stats['user'] += 1
            elif speaker_name:
                speaker_stats['with_name'] += 1
            elif not speaker_name and speaker_id:
                speaker_stats['without_name'] += 1
                if speaker_id not in speaker_stats['unknown_ids']:
                    speaker_stats['unknown_ids'].append(speaker_id)
            elif not speaker_name:
                speaker_stats['empty_name'] += 1
        
        print(f"\n   Speaker Statistics:")
        print(f"     With names: {speaker_stats['with_name']}")
        print(f"     Without names (but with ID): {speaker_stats['without_name']}")
        print(f"     Empty names (no ID): {speaker_stats['empty_name']}")
        print(f"     User speakers: {speaker_stats['user']}")
        print(f"     Unknown IDs: {speaker_stats['unknown_ids']}")
        
        # Check cached data
        cache_key = RedisKeyBuilder.build_limitless_lifelog_key(log_id)
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            try:
                cached_log = json.loads(cached_data.decode() if isinstance(cached_data, bytes) else cached_data)
                extracted = cached_log.get('extracted', {})
                people = extracted.get('people', [])
                
                print(f"\n   Cached Data:")
                print(f"     People count: {len(people)}")
                for person in people:
                    print(f"     - {person.get('name')} (is_speaker: {person.get('is_speaker', False)})")
                    
                # Check for Unknown speakers
                unknown_count = sum(1 for p in people if 'unknown' in p.get('name', '').lower())
                if unknown_count > 0:
                    print(f"\n   ⚠️  WARNING: Found {unknown_count} Unknown speakers in cache!")
                    
            except Exception as e:
                print(f"   Error parsing cached data: {e}")
        else:
            print(f"\n   No cached data found")
            
        # Check if this is around 07:10 PM
        if recording_time and abs((datetime.combine(datetime.today(), recording_time) - 
                                   datetime.combine(datetime.today(), target_time)).total_seconds()) < 1800:  # Within 30 mins
            print(f"\n   🎯 This recording is near 07:10 PM!")

if __name__ == "__main__":
    asyncio.run(debug_recent_recordings())