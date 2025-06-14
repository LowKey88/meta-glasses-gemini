#!/usr/bin/env python3
"""
Check current memory statistics and analyze memory creation patterns.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_utils import r as redis_client
from utils.redis_key_builder import RedisKeyBuilder
from utils.memory_manager import MemoryManager
import json
from collections import defaultdict

PHONE_NUMBER = "60122873632"  # Update with your phone number

def analyze_limitless_memories():
    """Analyze memories created from Limitless recordings."""
    print("\n📊 Analyzing Limitless Memories")
    print("=" * 50)
    
    # Get all memories
    memories = MemoryManager.get_all_memories(PHONE_NUMBER)
    
    # Filter Limitless memories
    limitless_memories = []
    recordings = defaultdict(list)
    
    for memory in memories:
        metadata = memory.get('metadata', {})
        if metadata.get('source') == 'limitless':
            limitless_memories.append(memory)
            log_id = metadata.get('log_id')
            if log_id:
                recordings[log_id].append(memory)
    
    print(f"\nTotal memories: {len(memories)}")
    print(f"Limitless memories: {len(limitless_memories)}")
    print(f"Unique recordings: {len(recordings)}")
    
    if recordings:
        # Calculate memories per recording
        memory_counts = defaultdict(int)
        for log_id, mems in recordings.items():
            count = len(mems)
            memory_counts[count] += 1
        
        print("\n📈 Memories per recording distribution:")
        for count in sorted(memory_counts.keys()):
            print(f"  {count} memory/recording: {memory_counts[count]} recordings")
        
        # Calculate average
        total_recording_memories = sum(len(mems) for mems in recordings.values())
        avg = total_recording_memories / len(recordings)
        print(f"\n📊 Average memories per recording: {avg:.2f}")
        
        # Show sample consolidated memories
        print("\n🔍 Sample memories (newest first):")
        for i, memory in enumerate(limitless_memories[:5], 1):
            print(f"\n{i}. Type: {memory.get('type')}")
            print(f"   Created: {memory.get('created_at', '')[:19]}")
            content = memory.get('content', '')
            print(f"   Content preview: {content[:150]}...")
            
            metadata = memory.get('metadata', {})
            if metadata.get('is_consolidated'):
                print(f"   ✅ Consolidated memory")
                print(f"   Facts: {metadata.get('facts_count', 0)}, People: {metadata.get('people_count', 0)}")
            
            # Count memory types for this recording
            log_id = metadata.get('log_id')
            if log_id:
                recording_memories = recordings[log_id]
                types = [m.get('type') for m in recording_memories]
                print(f"   Recording has {len(recording_memories)} memories: {', '.join(types)}")

def check_cached_recordings():
    """Check cached Limitless recordings."""
    print("\n\n📼 Checking Cached Recordings")
    print("=" * 50)
    
    # Get all cached recordings
    pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
    keys = list(redis_client.scan_iter(match=pattern))
    
    print(f"\nCached recordings: {len(keys)}")
    
    if keys:
        # Sample a few recordings
        print("\n🔍 Sample recordings:")
        for i, key in enumerate(keys[:3], 1):
            data = redis_client.get(key)
            if data:
                log_data = json.loads(data.decode() if isinstance(data, bytes) else data)
                print(f"\n{i}. Title: {log_data.get('title', 'Untitled')}")
                print(f"   ID: {log_data.get('id', '')[:8]}...")
                print(f"   Processed: {log_data.get('processed_at', '')[:19]}")
                
                extracted = log_data.get('extracted', {})
                print(f"   Extracted: {len(extracted.get('facts', []))} facts, "
                      f"{len(extracted.get('people', []))} people, "
                      f"{len(extracted.get('tasks', []))} tasks")

def memory_type_breakdown():
    """Show breakdown by memory type."""
    print("\n\n📊 Memory Type Breakdown")
    print("=" * 50)
    
    memories = MemoryManager.get_all_memories(PHONE_NUMBER)
    
    type_counts = defaultdict(int)
    source_counts = defaultdict(int)
    
    for memory in memories:
        type_counts[memory.get('type', 'unknown')] += 1
        source = memory.get('extracted_from', 'unknown')
        source_counts[source] += 1
    
    print("\nBy Type:")
    for mem_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {mem_type}: {count}")
    
    print("\nBy Source:")
    for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {source}: {count}")

if __name__ == "__main__":
    print("🧪 Memory Statistics Analysis")
    
    analyze_limitless_memories()
    check_cached_recordings()
    memory_type_breakdown()
    
    print("\n\n✅ Analysis complete!")