#!/usr/bin/env python3
"""Fix memory display issues - analyze and repair corrupted memory content"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
import logging
from datetime import datetime
from utils.redis_utils import r
from utils.memory_manager import MemoryManager
from utils.redis_key_builder import redis_keys
from utils.gemini import simple_prompt_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_memory_content(memory):
    """Analyze a memory for content issues"""
    issues = []
    content = memory.get('content', '')
    
    # Check for AI extraction artifacts
    if content.startswith('From ') and ':' in content:
        issues.append('ai_extraction_artifact')
    
    # Check for truncated content
    if content.endswith('...') and len(content) > 50:
        issues.append('possibly_truncated')
    
    # Check for test data
    test_patterns = ['TEST', 'FINAL TEST', 'VERIFICATION', 'test memory']
    if any(pattern in content.upper() for pattern in test_patterns):
        issues.append('test_data')
    
    # Check for malformed JSON in content
    if '{' in content and '}' in content:
        try:
            # Try to extract and parse JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json.loads(json_match.group())
        except:
            issues.append('malformed_json')
    
    # Check for encoding issues
    if '\\u' in content or '\\x' in content:
        issues.append('encoding_issue')
    
    return issues

def clean_ai_extraction_artifact(content):
    """Clean up AI extraction artifacts from content"""
    # Pattern: "From [context]: [actual content]"
    match = re.match(r'^From (.+?):\s*(.+)$', content, re.DOTALL)
    if match:
        context, actual_content = match.groups()
        # Return just the actual content
        return actual_content.strip()
    return content

def fix_memory_issues():
    """Fix memory display issues"""
    
    print("\n=== FIXING MEMORY DISPLAY ISSUES ===\n")
    
    user_id = "60122873632"
    
    # Get all memories
    print("1. Fetching all memories...")
    memories = MemoryManager.get_all_memories(user_id)
    print(f"   Total memories found: {len(memories)}")
    
    # Analyze memories for issues
    print("\n2. Analyzing memories for issues...")
    issues_found = {
        'ai_extraction_artifact': [],
        'possibly_truncated': [],
        'test_data': [],
        'malformed_json': [],
        'encoding_issue': [],
        'no_issues': []
    }
    
    for memory in memories:
        memory_issues = analyze_memory_content(memory)
        if not memory_issues:
            issues_found['no_issues'].append(memory)
        else:
            for issue in memory_issues:
                if issue in issues_found:
                    issues_found[issue].append(memory)
    
    # Print summary
    print("\n   Issue Summary:")
    for issue_type, memories_with_issue in issues_found.items():
        if issue_type != 'no_issues' and memories_with_issue:
            print(f"   - {issue_type}: {len(memories_with_issue)} memories")
    
    print(f"   - no_issues: {len(issues_found['no_issues'])} memories")
    
    # Fix AI extraction artifacts
    if issues_found['ai_extraction_artifact']:
        print("\n3. Fixing AI extraction artifacts...")
        fixed_count = 0
        
        for memory in issues_found['ai_extraction_artifact'][:10]:  # Fix first 10 as example
            original_content = memory['content']
            cleaned_content = clean_ai_extraction_artifact(original_content)
            
            if cleaned_content != original_content:
                print(f"\n   Memory ID: {memory['id']}")
                print(f"   Original: {original_content[:100]}...")
                print(f"   Cleaned:  {cleaned_content[:100]}...")
                
                # Update the memory
                success = MemoryManager.update_memory(
                    user_id,
                    memory['id'],
                    {'content': cleaned_content}
                )
                
                if success:
                    fixed_count += 1
                    print("   ✓ Fixed")
                else:
                    print("   ✗ Failed to update")
        
        print(f"\n   Fixed {fixed_count} memories with AI extraction artifacts")
    
    # Remove test data
    if issues_found['test_data']:
        print("\n4. Handling test data...")
        print(f"   Found {len(issues_found['test_data'])} test memories")
        
        # Show samples
        for memory in issues_found['test_data'][:5]:
            print(f"   - {memory['id']}: {memory['content'][:50]}...")
        
        # Optional: Delete test memories
        # for memory in issues_found['test_data']:
        #     MemoryManager.delete_memory(user_id, memory['id'])
    
    # Check for duplicate memories
    print("\n5. Checking for duplicate memories...")
    content_map = {}
    duplicates = []
    
    for memory in memories:
        content_key = memory['content'].lower().strip()
        if content_key in content_map:
            duplicates.append((content_map[content_key], memory))
        else:
            content_map[content_key] = memory
    
    if duplicates:
        print(f"   Found {len(duplicates)} duplicate memories")
        for original, duplicate in duplicates[:5]:
            print(f"   - Original: {original['id']} ({original['created_at']})")
            print(f"     Duplicate: {duplicate['id']} ({duplicate['created_at']})")
            print(f"     Content: {original['content'][:50]}...")
    
    # Verify memory retrieval matches what's in Redis
    print("\n6. Verifying memory consistency...")
    
    # Get memories directly from Redis
    memory_pattern = redis_keys.get_user_memory_key(user_id, "*")
    redis_memory_keys = r.keys(memory_pattern)
    redis_count = len(redis_memory_keys)
    
    # Get memories via MemoryManager
    manager_memories = MemoryManager.get_all_memories(user_id)
    manager_count = len(manager_memories)
    
    print(f"   Memories in Redis: {redis_count}")
    print(f"   Memories via MemoryManager: {manager_count}")
    
    if redis_count != manager_count:
        print(f"   ⚠️  Mismatch detected! Difference: {redis_count - manager_count}")
        
        # Find missing memories
        manager_ids = {m['id'] for m in manager_memories}
        
        missing_count = 0
        for key in redis_memory_keys[:10]:  # Check first 10
            key_str = key.decode() if isinstance(key, bytes) else key
            memory_id = key_str.split(':')[-1]
            
            if memory_id not in manager_ids:
                # Check why it's missing
                memory_data = r.get(key_str)
                if memory_data:
                    try:
                        memory = json.loads(memory_data)
                        status = memory.get('status', 'unknown')
                        print(f"   Missing memory {memory_id}: status={status}")
                        missing_count += 1
                    except:
                        print(f"   Failed to parse memory {memory_id}")
        
        if missing_count > 0:
            print(f"   Found {missing_count} memories not returned by MemoryManager")
    else:
        print("   ✓ Memory counts match")
    
    print("\n7. Recommendations:")
    print("   - Clear browser cache and reload dashboard")
    print("   - Check if dashboard is using correct API endpoint")
    print("   - Verify authentication is working properly")
    print("   - Consider implementing pagination if too many memories")

if __name__ == "__main__":
    fix_memory_issues()