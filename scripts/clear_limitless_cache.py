#!/usr/bin/env python3
"""
Clear Limitless-related data from Redis to force fresh processing.
This will clear:
- All cached Limitless recordings
- All memories created from Limitless
- All Limitless-related task markers
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.redis_utils import r as redis_client
from utils.redis_key_builder import RedisKeyBuilder
from utils.memory_manager import MemoryManager
import json

PHONE_NUMBER = "60122873632"

def clear_limitless_cache():
    """Clear all Limitless cached recordings."""
    print("\n🗑️  Clearing Limitless cached recordings...")
    
    # Pattern for Limitless recordings
    pattern = RedisKeyBuilder.build_limitless_lifelog_key("*")
    keys = list(redis_client.scan_iter(match=pattern))
    
    if keys:
        redis_client.delete(*keys)
        print(f"✅ Deleted {len(keys)} cached recordings")
    else:
        print("ℹ️  No cached recordings found")
    
    # Clear task processing markers
    task_pattern = "meta-glasses:limitless:*_tasks_processed:*"
    task_keys = list(redis_client.scan_iter(match=task_pattern))
    
    if task_keys:
        redis_client.delete(*task_keys)
        print(f"✅ Deleted {len(task_keys)} task processing markers")

def clear_limitless_memories():
    """Clear all memories created from Limitless."""
    print("\n🗑️  Clearing Limitless memories...")
    
    # Get all memories
    memories = MemoryManager.get_all_memories(PHONE_NUMBER)
    
    limitless_memory_ids = []
    for memory in memories:
        metadata = memory.get('metadata', {})
        if metadata.get('source') == 'limitless' or memory.get('extracted_from') == 'limitless':
            limitless_memory_ids.append(memory['id'])
    
    if limitless_memory_ids:
        # Remove from index
        index_key = MemoryManager.get_index_key(PHONE_NUMBER)
        for memory_id in limitless_memory_ids:
            redis_client.srem(index_key, memory_id)
            
            # Delete memory data
            memory_key = MemoryManager.get_memory_key(PHONE_NUMBER, memory_id)
            redis_client.delete(memory_key)
        
        print(f"✅ Deleted {len(limitless_memory_ids)} Limitless memories")
    else:
        print("ℹ️  No Limitless memories found")

def show_stats():
    """Show current stats after clearing."""
    print("\n📊 Current Statistics:")
    
    # Count remaining memories
    memories = MemoryManager.get_all_memories(PHONE_NUMBER)
    print(f"Total memories remaining: {len(memories)}")
    
    # Count by source
    source_counts = {}
    for memory in memories:
        source = memory.get('extracted_from', 'unknown')
        source_counts[source] = source_counts.get(source, 0) + 1
    
    if source_counts:
        print("\nMemories by source:")
        for source, count in source_counts.items():
            print(f"  {source}: {count}")

if __name__ == "__main__":
    print("🧹 Clearing Limitless Cache and Memories")
    print("=" * 50)
    
    response = input("\n⚠️  This will delete all Limitless recordings and memories. Continue? (y/N): ")
    
    if response.lower() == 'y':
        clear_limitless_cache()
        clear_limitless_memories()
        show_stats()
        print("\n✅ Cleanup complete!")
        print("\n📱 Next steps:")
        print("1. Open the dashboard at http://localhost:3000")
        print("2. Navigate to Limitless sync section")
        print("3. Perform a fresh sync to test the new memory optimization")
    else:
        print("\n❌ Cleanup cancelled")