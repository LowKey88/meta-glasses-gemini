#!/usr/bin/env python3
"""
Debug script to investigate memory creation and display issues on VPS.
"""

import json
import sys
from utils.memory_manager import MemoryManager
from utils.redis_utils import r

def debug_memories():
    """Debug memory issues by checking Redis directly."""
    user_id = "60122873632"
    
    print("🔍 Debugging Memory Issues")
    print("=" * 50)
    
    # 1. Check memory index
    index_key = MemoryManager.get_index_key(user_id)
    print(f"📋 Memory index key: {index_key}")
    
    memory_ids = r.smembers(index_key)
    print(f"📊 Found {len(memory_ids)} memory IDs in index")
    
    # 2. Check each memory
    memories_data = []
    for i, memory_id in enumerate(memory_ids, 1):
        memory_id_str = memory_id.decode() if isinstance(memory_id, bytes) else memory_id
        print(f"\n📝 Memory {i}: {memory_id_str}")
        
        memory_key = MemoryManager.get_memory_key(user_id, memory_id_str)
        raw_data = r.get(memory_key)
        
        if raw_data:
            try:
                memory_data = json.loads(raw_data)
                memories_data.append(memory_data)
                
                print(f"   Status: {memory_data.get('status', 'MISSING')}")
                print(f"   Type: {memory_data.get('type', 'MISSING')}")
                print(f"   Source: {memory_data.get('extracted_from', 'MISSING')}")
                print(f"   Created: {memory_data.get('created_at', 'MISSING')}")
                print(f"   Content preview: {memory_data.get('content', 'MISSING')[:100]}...")
                
                # Check for corrupted content
                content = memory_data.get('content', '')
                if 'From ' in content and ': ' in content:
                    print(f"   ⚠️  POTENTIAL CORRUPTION: Content has 'From X:' prefix")
                
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON decode error: {e}")
        else:
            print(f"   ❌ No data found for key: {memory_key}")
    
    # 3. Test get_all_memories function
    print(f"\n🔍 Testing get_all_memories function...")
    api_memories = MemoryManager.get_all_memories(user_id)
    print(f"📊 get_all_memories returned {len(api_memories)} memories")
    
    # 4. Check for filtering issues
    active_memories = [m for m in memories_data if m.get('status') == 'active']
    inactive_memories = [m for m in memories_data if m.get('status') != 'active']
    
    print(f"✅ Active memories: {len(active_memories)}")
    print(f"❌ Inactive/missing status: {len(inactive_memories)}")
    
    if inactive_memories:
        print("\n🔍 Inactive memories:")
        for mem in inactive_memories:
            print(f"   - {mem.get('id', 'no-id')}: status='{mem.get('status', 'MISSING')}'")
    
    # 5. Check for recent creation issues
    print(f"\n🕐 Checking recent memories (last 24 hours)...")
    from datetime import datetime, timedelta
    now = datetime.now()
    recent_cutoff = now - timedelta(hours=24)
    
    recent_memories = []
    for mem in memories_data:
        created_str = mem.get('created_at', '')
        if created_str:
            try:
                created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                # Remove timezone info for comparison
                created_dt = created_dt.replace(tzinfo=None)
                if created_dt > recent_cutoff:
                    recent_memories.append(mem)
            except:
                pass
    
    print(f"📅 Recent memories found: {len(recent_memories)}")
    for mem in recent_memories:
        print(f"   - {mem.get('created_at')}: {mem.get('content', '')[:50]}...")
    
    # 6. Check for content corruption patterns
    print(f"\n🔍 Checking for content corruption patterns...")
    corrupted_count = 0
    for mem in memories_data:
        content = mem.get('content', '')
        # Look for common corruption patterns
        if any(pattern in content for pattern in ['From ', ': ']):
            corrupted_count += 1
            print(f"   ⚠️  Corrupted: {mem.get('id')}: {content[:100]}...")
    
    print(f"❌ Total corrupted memories: {corrupted_count}")
    
    return {
        'total_in_redis': len(memories_data),
        'total_in_api': len(api_memories),
        'active_memories': len(active_memories),
        'recent_memories': len(recent_memories),
        'corrupted_memories': corrupted_count
    }

def fix_memory_status():
    """Fix memories that might be missing the status field."""
    user_id = "60122873632"
    
    print("\n🔧 Fixing memory status fields...")
    
    index_key = MemoryManager.get_index_key(user_id)
    memory_ids = r.smembers(index_key)
    
    fixed_count = 0
    for memory_id in memory_ids:
        memory_id_str = memory_id.decode() if isinstance(memory_id, bytes) else memory_id
        memory_key = MemoryManager.get_memory_key(user_id, memory_id_str)
        raw_data = r.get(memory_key)
        
        if raw_data:
            try:
                memory_data = json.loads(raw_data)
                
                # Fix missing status
                if 'status' not in memory_data or not memory_data['status']:
                    memory_data['status'] = 'active'
                    r.set(memory_key, json.dumps(memory_data))
                    fixed_count += 1
                    print(f"   ✅ Fixed status for memory: {memory_id_str}")
                    
            except json.JSONDecodeError:
                print(f"   ❌ Could not parse memory: {memory_id_str}")
    
    print(f"🔧 Fixed {fixed_count} memories")

def clean_corrupted_content():
    """Clean up corrupted memory content."""
    user_id = "60122873632"
    
    print("\n🧹 Cleaning corrupted memory content...")
    
    index_key = MemoryManager.get_index_key(user_id)
    memory_ids = r.smembers(index_key)
    
    cleaned_count = 0
    for memory_id in memory_ids:
        memory_id_str = memory_id.decode() if isinstance(memory_id, bytes) else memory_id
        memory_key = MemoryManager.get_memory_key(user_id, memory_id_str)
        raw_data = r.get(memory_key)
        
        if raw_data:
            try:
                memory_data = json.loads(raw_data)
                content = memory_data.get('content', '')
                
                # Clean content that starts with "From X: "
                if content.startswith('From ') and ': ' in content:
                    # Extract the actual content after "From X: "
                    colon_index = content.find(': ')
                    if colon_index > 0:
                        clean_content = content[colon_index + 2:].strip()
                        if clean_content:
                            memory_data['content'] = clean_content
                            r.set(memory_key, json.dumps(memory_data))
                            cleaned_count += 1
                            print(f"   🧹 Cleaned: {memory_id_str}")
                            print(f"      Before: {content[:100]}...")
                            print(f"      After:  {clean_content[:100]}...")
                    
            except json.JSONDecodeError:
                print(f"   ❌ Could not parse memory: {memory_id_str}")
    
    print(f"🧹 Cleaned {cleaned_count} corrupted memories")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fix":
        fix_memory_status()
        clean_corrupted_content()
    else:
        result = debug_memories()
        print(f"\n📊 Summary:")
        for key, value in result.items():
            print(f"   {key}: {value}")
        
        print(f"\n💡 To fix issues, run: python debug_memory_issues.py fix")