#!/usr/bin/env python3
"""
Fix manual memories that have content stored in extracted_from field
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.memory_manager import MemoryManager
from utils.redis_utils import r

def fix_manual_memories():
    """Fix memories where content is stored in extracted_from field"""
    
    print("\n=== FIXING MANUAL MEMORIES ===\n")
    
    user_id = "60122873632"
    
    # Get all memory IDs from index
    index_key = MemoryManager.get_index_key(user_id)
    memory_ids = r.smembers(index_key)
    
    print(f"Checking {len(memory_ids)} memories...")
    
    fixed_count = 0
    manual_memories_found = []
    
    for memory_id in memory_ids:
        memory_id_str = memory_id.decode() if isinstance(memory_id, bytes) else memory_id
        memory_key = MemoryManager.get_memory_key(user_id, memory_id_str)
        raw_data = r.get(memory_key)
        
        if raw_data:
            try:
                memory_data = json.loads(raw_data)
                extracted_from = memory_data.get('extracted_from', '')
                content = memory_data.get('content', '')
                
                # Check if this looks like a manual memory with content in extracted_from
                manual_indicators = [
                    'My name is',
                    'My wife',
                    'My daughter',
                    'My anniversary',
                    'birthday is',
                    'was born on',
                    'I\'m married'
                ]
                
                is_manual_memory = any(indicator in extracted_from for indicator in manual_indicators)
                
                if is_manual_memory and extracted_from:
                    print(f"\n🔧 Found manual memory to fix: {memory_id_str}")
                    print(f"   Current content: '{content}'")
                    print(f"   Current extracted_from: '{extracted_from}'")
                    
                    # Fix the memory
                    memory_data['content'] = extracted_from
                    memory_data['extracted_from'] = 'manual'
                    
                    # Set proper metadata
                    if 'metadata' not in memory_data:
                        memory_data['metadata'] = {}
                    memory_data['metadata']['source'] = 'manual'
                    
                    # Save the fixed memory
                    r.set(memory_key, json.dumps(memory_data))
                    fixed_count += 1
                    manual_memories_found.append(memory_data)
                    
                    print(f"   ✅ Fixed: content='{extracted_from[:50]}...', extracted_from='manual'")
                
                # Also check memories with no source that might be manual
                elif (not extracted_from or extracted_from == 'None') and content:
                    # Check if content looks like personal info that should be manual
                    personal_patterns = [
                        'Hisyam like',
                        'Hisyam work',
                        'Hisyam was born',
                        'Hisyam likes to watch'
                    ]
                    
                    is_personal_info = any(pattern in content for pattern in personal_patterns)
                    
                    if is_personal_info:
                        print(f"\n🔧 Found personal info to mark as manual: {memory_id_str}")
                        print(f"   Content: '{content}'")
                        
                        # Mark as manual
                        memory_data['extracted_from'] = 'manual'
                        if 'metadata' not in memory_data:
                            memory_data['metadata'] = {}
                        memory_data['metadata']['source'] = 'manual'
                        
                        r.set(memory_key, json.dumps(memory_data))
                        fixed_count += 1
                        manual_memories_found.append(memory_data)
                        
                        print(f"   ✅ Marked as manual")
                        
            except json.JSONDecodeError:
                print(f"   ❌ Failed to parse memory: {memory_id_str}")
    
    print(f"\n📊 Summary:")
    print(f"   Fixed {fixed_count} manual memories")
    print(f"   Total manual memories found: {len(manual_memories_found)}")
    
    if manual_memories_found:
        print(f"\n📝 Manual memories now available:")
        for memory in manual_memories_found:
            print(f"   - {memory.get('content', '')[:60]}...")
    
    return fixed_count

if __name__ == "__main__":
    fixed_count = fix_manual_memories()
    print(f"\n✅ Fixed {fixed_count} manual memories. They should now appear in your dashboard!")