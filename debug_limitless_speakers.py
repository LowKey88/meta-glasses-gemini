#!/usr/bin/env python3
"""
Debug script to analyze Limitless speaker data in Redis.
Identifies any remaining "Unknown" speakers in cached recordings.
"""

import sys
import os
import json
from typing import Dict, List
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.redis_utils import r

def analyze_limitless_speakers():
    """Analyze speaker data in all cached Limitless recordings."""
    print("🔍 Analyzing Limitless speaker data...")
    
    # Get all Limitless lifelog keys
    pattern = "meta-glasses:limitless:lifelog:*"
    keys = []
    for key in r.scan_iter(match=pattern):
        keys.append(key.decode() if isinstance(key, bytes) else key)
    
    print(f"Found {len(keys)} Limitless recordings in Redis")
    
    total_recordings = 0
    unknown_speaker_count = 0
    recordings_with_unknown = []
    speaker_name_stats = {}
    
    for key in keys:
        try:
            data = r.get(key)
            if not data:
                continue
                
            log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
            log_id = log_data.get('id', 'unknown')
            title = log_data.get('title', 'Unknown Title')
            extracted = log_data.get('extracted', {})
            people = extracted.get('people', [])
            
            total_recordings += 1
            
            print(f"\nRecording {total_recordings}: {log_id[:8]}... - '{title}'")
            print(f"  People count: {len(people)}")
            
            recording_has_unknown = False
            
            for i, person in enumerate(people):
                name = person.get('name', 'no-name')
                is_speaker = person.get('is_speaker', False)
                context = person.get('context', 'no-context')
                
                # Track speaker name patterns
                if name in speaker_name_stats:
                    speaker_name_stats[name] += 1
                else:
                    speaker_name_stats[name] = 1
                
                print(f"    Person {i+1}: \"{name}\" (speaker: {is_speaker}) - {context}")
                
                # Check for Unknown speakers
                if name.lower() in ['unknown', 'unknown speaker']:
                    unknown_speaker_count += 1
                    recording_has_unknown = True
                    print(f"      ⚠️  FOUND UNKNOWN SPEAKER!")
            
            if recording_has_unknown:
                recordings_with_unknown.append({
                    'id': log_id,
                    'title': title,
                    'key': key,
                    'people': people
                })
                
        except Exception as e:
            print(f"Error analyzing recording: {e}")
    
    print("\n" + "=" * 80)
    print("LIMITLESS SPEAKER ANALYSIS REPORT")
    print("=" * 80)
    
    print(f"📊 SUMMARY:")
    print(f"  Total recordings analyzed: {total_recordings}")
    print(f"  Total 'Unknown' speakers found: {unknown_speaker_count}")
    print(f"  Recordings with unknown speakers: {len(recordings_with_unknown)}")
    
    print(f"\n🏷️  SPEAKER NAME STATISTICS:")
    for name, count in sorted(speaker_name_stats.items(), key=lambda x: x[1], reverse=True):
        if name.lower() in ['unknown', 'unknown speaker']:
            print(f"  ⚠️  {name}: {count} occurrences")
        else:
            print(f"  {name}: {count} occurrences")
    
    if recordings_with_unknown:
        print(f"\n⚠️  RECORDINGS WITH UNKNOWN SPEAKERS:")
        for recording in recordings_with_unknown:
            print(f"  ID: {recording['id']}")
            print(f"  Title: {recording['title']}")
            print(f"  Key: {recording['key']}")
            print(f"  People with issues:")
            for person in recording['people']:
                name = person.get('name', 'no-name')
                if name.lower() in ['unknown', 'unknown speaker']:
                    print(f"    - {person}")
            print()
    else:
        print(f"\n✅ NO UNKNOWN SPEAKERS FOUND - All recordings are properly standardized!")
    
    # Check for any Speaker N numbering issues
    speaker_n_names = [name for name in speaker_name_stats.keys() if name.startswith('Speaker ')]
    if speaker_n_names:
        print(f"\n🔢 SPEAKER N NAMING ANALYSIS:")
        for name in sorted(speaker_n_names):
            print(f"  {name}: {speaker_name_stats[name]} occurrences")
            
        # Check for numbering gaps or inconsistencies
        speaker_numbers = []
        for name in speaker_n_names:
            try:
                number = int(name.split(' ')[1])
                speaker_numbers.append(number)
            except (IndexError, ValueError):
                print(f"  ⚠️  Invalid Speaker N format: {name}")
        
        if speaker_numbers:
            min_num = min(speaker_numbers)
            max_num = max(speaker_numbers)
            print(f"  Number range: {min_num} to {max_num}")
            
            # Check for gaps
            expected_numbers = set(range(min_num, max_num + 1))
            actual_numbers = set(speaker_numbers)
            missing_numbers = expected_numbers - actual_numbers
            
            if missing_numbers:
                print(f"  ⚠️  Missing numbers: {sorted(missing_numbers)}")
            else:
                print(f"  ✅ No gaps in Speaker N numbering")

def main():
    """Main analysis function."""
    try:
        analyze_limitless_speakers()
        print(f"\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()