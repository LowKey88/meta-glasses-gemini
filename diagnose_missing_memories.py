#!/usr/bin/env python3
"""
Diagnose why manual and WhatsApp memories are missing from dashboard
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.memory_manager import MemoryManager
from utils.redis_utils import r
from utils.redis_key_builder import redis_keys

def diagnose_missing_memories():
    """Diagnose why manual and WhatsApp memories are not showing"""
    
    print("\n=== DIAGNOSING MISSING MEMORIES ===\n")
    
    user_id = "60122873632"
    
    # 1. Get memories from index
    print("1. Checking memory index:")
    index_key = MemoryManager.get_index_key(user_id)
    memory_ids = r.smembers(index_key)
    print(f"   Total IDs in index: {len(memory_ids)}")
    
    # 2. Check each memory and categorize by source
    print("\n2. Analyzing all memories by source:")
    
    sources = {
        'manual': [],
        'whatsapp': [],
        'limitless': [],
        'none': [],
        'missing': []
    }
    
    status_counts = {
        'active': 0,
        'archived': 0,
        'missing_status': 0,
        'key_not_found': 0
    }
    
    for memory_id in memory_ids:
        memory_id_str = memory_id.decode() if isinstance(memory_id, bytes) else memory_id
        memory_key = MemoryManager.get_memory_key(user_id, memory_id_str)
        raw_data = r.get(memory_key)
        
        if raw_data:
            try:
                memory_data = json.loads(raw_data)
                
                # Check status
                status = memory_data.get('status', 'missing_status')
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    status_counts['missing_status'] += 1
                
                # Only analyze active memories
                if status == 'active':
                    # Check source
                    extracted_from = memory_data.get('extracted_from')
                    metadata_source = memory_data.get('metadata', {}).get('source')
                    
                    if extracted_from == 'manual' or metadata_source == 'manual':
                        sources['manual'].append(memory_data)
                    elif extracted_from == 'whatsapp' or metadata_source == 'whatsapp':
                        sources['whatsapp'].append(memory_data)
                    elif extracted_from == 'limitless' or metadata_source == 'limitless':
                        sources['limitless'].append(memory_data)
                    elif extracted_from is None and metadata_source is None:
                        sources['none'].append(memory_data)
                    else:
                        print(f"   Unknown source: extracted_from='{extracted_from}', metadata_source='{metadata_source}'")
                        
            except json.JSONDecodeError:
                print(f"   Failed to parse memory: {memory_id_str}")
        else:
            sources['missing'].append(memory_id_str)
            status_counts['key_not_found'] += 1
    
    # Print results
    print(f"\n   Status breakdown:")
    for status, count in status_counts.items():
        print(f"   - {status}: {count}")
    
    print(f"\n   Source breakdown (active memories only):")
    for source, memories in sources.items():
        print(f"   - {source}: {len(memories)}")
    
    # 3. Test MemoryManager.get_all_memories()
    print("\n3. Testing MemoryManager.get_all_memories():")
    api_memories = MemoryManager.get_all_memories(user_id)
    print(f"   Returned by API: {len(api_memories)}")
    
    # Check sources in API result
    api_sources = {
        'manual': 0,
        'whatsapp': 0,
        'limitless': 0,
        'none': 0
    }
    
    for memory in api_memories:
        extracted_from = memory.get('extracted_from')
        metadata_source = memory.get('metadata', {}).get('source')
        
        if extracted_from == 'manual' or metadata_source == 'manual':
            api_sources['manual'] += 1
        elif extracted_from == 'whatsapp' or metadata_source == 'whatsapp':
            api_sources['whatsapp'] += 1
        elif extracted_from == 'limitless' or metadata_source == 'limitless':
            api_sources['limitless'] += 1
        else:
            api_sources['none'] += 1
    
    print(f"   API source breakdown:")
    for source, count in api_sources.items():
        print(f"   - {source}: {count}")
    
    # 4. Show sample memories by source
    print("\n4. Sample memories by source:")
    
    for source_name, memories in sources.items():
        if memories and source_name != 'missing':
            print(f"\n   {source_name.upper()} samples:")
            for i, memory in enumerate(memories[:3]):
                if isinstance(memory, dict):
                    print(f"   - {memory.get('id')}: {memory.get('content', '')[:60]}...")
                    print(f"     extracted_from: {memory.get('extracted_from')}")
                    print(f"     metadata.source: {memory.get('metadata', {}).get('source')}")
                    print(f"     created_at: {memory.get('created_at')}")
                else:
                    print(f"   - Missing key: {memory}")
    
    # 5. Check for recent manual memories
    print("\n5. Looking for recent manual memories:")
    
    manual_memories = sources['manual']
    if manual_memories:
        # Sort by creation date
        manual_memories.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        print(f"   Found {len(manual_memories)} manual memories")
        print("   Most recent:")
        for memory in manual_memories[:5]:
            print(f"   - {memory.get('created_at')}: {memory.get('content', '')[:50]}...")
    else:
        print("   No manual memories found!")
        
        # Check if there are any memories with source=None that might be manual
        none_memories = sources['none']
        print(f"\n   Checking {len(none_memories)} memories with no source:")
        for memory in none_memories[:10]:
            print(f"   - {memory.get('id')}: {memory.get('content', '')[:50]}...")
            print(f"     type: {memory.get('type')}")
            print(f"     created_at: {memory.get('created_at')}")

if __name__ == "__main__":
    diagnose_missing_memories()