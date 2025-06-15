import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from utils.redis_utils import r, try_catch_decorator
from utils.redis_monitor import monitored_set, monitored_sadd, monitored_smembers, monitored_get
from utils.redis_key_builder import redis_keys

logger = logging.getLogger("uvicorn")

# Memory configuration
MEMORY_KEY_PREFIX = "memory:"
MEMORY_INDEX_KEY = "memory_index:"
MEMORY_TTL = None  # Permanent memories

# Memory types
MEMORY_TYPES = {
    'fact': 'Simple facts and information',
    'preference': 'User preferences and likes/dislikes',
    'relationship': 'People and relationships',
    'routine': 'Regular activities and schedules',
    'important_date': 'Birthdays, anniversaries, appointments',
    'personal_info': 'Personal information like phone, email, address',
    'allergy': 'Food allergies and restrictions',
    'note': 'General notes and reminders'
}

# Auto-detection patterns
MEMORY_PATTERNS = {
    'allergy': [
        r"allergic to (.+?)(?:\.|,|$)",
        r"can't eat (.+?)(?:\.|,|$)",
        r"intolerant to (.+?)(?:\.|,|$)"
    ],
    'relationship': [
        r"my (\w+) (?:is|'s|name is) (?:called |named )?(\w+)",
        r"(\w+) is my (\w+)",
        r"married to (\w+)",
        r"my (\w+) (?:called |named )?(\w+) (?:is|she is|he is) (\d+) years old"
    ],
    'preference': [
        r"i (?:prefer|like|love|enjoy) (.+?)(?:\.|,|$)",
        r"i (?:hate|dislike|don't like) (.+?)(?:\.|,|$)",
        r"my favorite (.+?) is (.+?)(?:\.|,|$)"
    ],
    'routine': [
        r"every (\w+) (?:i |we )?(.+?)(?:\.|,|$)",
        r"(?:usually|always) (.+?) (?:at|on) (.+?)(?:\.|,|$)"
    ],
    'important_date': [
        r"(\w+)'s birthday is (.+?)(?:\.|,|$)",
        r"anniversary is (.+?)(?:\.|,|$)",
        r"(.+?) on (\d{1,2}[/-]\d{1,2}[/-]?\d{0,4})"
    ],
    'personal_info': [
        r"my (?:phone|number) is (.+?)(?:\.|,|$)",
        r"my email is (.+?)(?:\.|,|$)",
        r"my (?:car|vehicle) is (?:a )?(.+?)(?:\.|,|$)"
    ]
}


class MemoryManager:
    """Manages long-term memory storage and retrieval for users."""
    
    @staticmethod
    @try_catch_decorator
    def get_memory_key(user_id: str, memory_id: str = None) -> str:
        """Generate Redis key for memory storage."""
        if memory_id:
            return redis_keys.get_user_memory_key(user_id, memory_id)
        # Return pattern for all memories for this user: meta-glasses:user:memory:user_id:*
        return f"{redis_keys.get_user_memory_key(user_id, '*')}"
    
    @staticmethod
    @try_catch_decorator
    def get_index_key(user_id: str) -> str:
        """Generate Redis key for memory index."""
        return redis_keys.get_user_memory_index_key(user_id)
    
    @staticmethod
    @try_catch_decorator
    def create_memory(
        user_id: str,
        content: str,
        memory_type: str = 'note',
        tags: List[str] = None,
        importance: int = 5,
        extracted_from: str = None,
        skip_deduplication: bool = False
    ) -> str:
        """Create a new memory with intelligent deduplication."""
        
        # OPTIMIZATION: Skip expensive AI deduplication for Limitless (they have their own duplicate checking)
        if not skip_deduplication:
            # Check for existing similar memories using optimized approach - only get recent memories of same type
            recent_memories = MemoryManager._get_recent_memories_by_type(user_id, memory_type, limit=10)
            
            # Use AI to check if this memory already exists or conflicts
            if recent_memories:
                try:
                    from utils.gemini import simple_prompt_request
                    
                    existing_content = "; ".join([f"{m['type']}: {m['content']}" for m in recent_memories[:5]])  # Check last 5 memories
                    
                    dedup_prompt = f"""
                    New memory: "{content}" (type: {memory_type})
                    Existing memories: {existing_content}
                    
                    Analyze if this new memory:
                    1. Is duplicate/very similar to existing → return "DUPLICATE"
                    2. Conflicts with existing (better/updated version) → return "CONFLICT: [text_to_replace]"
                    3. Is completely new information → return "CREATE"
                    """
                    
                    dedup_response = simple_prompt_request(dedup_prompt)
                    
                    if dedup_response.startswith('DUPLICATE'):
                        logger.info(f"Skipping duplicate memory: {content}")
                        return "duplicate"
                    
                    elif dedup_response.startswith('CONFLICT'):
                        # Find and update the conflicting memory
                        conflict_text = dedup_response.replace('CONFLICT:', '').strip()
                        for memory in recent_memories:
                            if conflict_text.lower() in memory['content'].lower():
                                # Update existing memory with better version
                                MemoryManager.update_memory(user_id, memory['id'], {
                                    'content': content,
                                    'importance': max(importance, memory.get('importance', 5)),
                                    'updated_at': datetime.now().isoformat()
                                })
                                logger.info(f"Updated conflicting memory {memory['id']}: {content}")
                                return memory['id']
                    
                except Exception as e:
                    logger.error(f"Error in AI deduplication: {e}")
        
        # Create new memory
        memory_id = str(uuid.uuid4())[:8]
        
        memory = {
            'id': memory_id,
            'user_id': user_id,
            'type': memory_type,
            'content': content,
            'tags': tags or [],
            'importance': importance,
            'created_at': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat(),
            'access_count': 0,
            'confidence': 1.0,
            'extracted_from': extracted_from,
            'status': 'active'
        }
        
        # Store memory
        key = MemoryManager.get_memory_key(user_id, memory_id)
        monitored_set(key, json.dumps(memory))
        
        # Update index
        index_key = MemoryManager.get_index_key(user_id)
        monitored_sadd(index_key, memory_id)
        
        # Update memory type counters for instant dashboard performance
        MemoryManager._increment_memory_counter(user_id, memory_type)
        
        logger.info(f"Created memory {memory_id} for user {user_id}: {content[:50]}...")
        return memory_id
    
    @staticmethod
    @try_catch_decorator
    def get_memory(user_id: str, memory_id: str) -> Optional[Dict]:
        """Retrieve a specific memory."""
        key = MemoryManager.get_memory_key(user_id, memory_id)
        data = monitored_get(key)
        
        if data:
            memory = json.loads(data)
            # Update access stats
            memory['last_accessed'] = datetime.now().isoformat()
            memory['access_count'] += 1
            monitored_set(key, json.dumps(memory))
            return memory
        
        return None
    
    @staticmethod
    @try_catch_decorator
    def search_memories(
        user_id: str,
        query: str,
        memory_type: str = None,
        limit: int = 5
    ) -> List[Dict]:
        """Search memories by content or type."""
        memories = MemoryManager.get_all_memories(user_id)
        query_lower = query.lower()
        
        # Filter by type if specified
        if memory_type:
            memories = [m for m in memories if m['type'] == memory_type]
        
        # Score memories by relevance
        scored_memories = []
        for memory in memories:
            score = 0
            content_lower = memory['content'].lower()
            
            # Exact match
            if query_lower in content_lower:
                score += 10
            
            # Word match
            query_words = query_lower.split()
            for word in query_words:
                if word in content_lower:
                    score += 2
            
            # Tag match
            for tag in memory.get('tags', []):
                if query_lower in tag.lower():
                    score += 5
            
            # Consider importance and recency
            score += memory.get('importance', 5) / 10
            
            if score > 0:
                scored_memories.append((score, memory))
        
        # Sort by score and return top results
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in scored_memories[:limit]]
    
    @staticmethod
    @try_catch_decorator
    def get_all_memories(user_id: str) -> List[Dict]:
        """Get all memories for a user, sorted by creation date (newest first)."""
        index_key = MemoryManager.get_index_key(user_id)
        memory_ids = monitored_smembers(index_key)
        
        memories = []
        for memory_id in memory_ids:
            memory_id = memory_id.decode() if isinstance(memory_id, bytes) else memory_id
            memory = MemoryManager.get_memory(user_id, memory_id)
            if memory and memory.get('status') == 'active':
                memories.append(memory)
        
        # Sort by created_at timestamp, newest first
        memories.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return memories
    
    @staticmethod
    @try_catch_decorator
    def get_memory_counts_by_type(user_id: str) -> Dict[str, int]:
        """Get memory counts by type using efficient Redis counters."""
        # Use Redis hash to store memory counts by type
        counters_key = redis_keys.get_user_memory_counters_key(user_id)
        
        # Check if counters exist, if not rebuild them once
        if not r.exists(counters_key):
            logger.info(f"Rebuilding memory counters for user {user_id}")
            MemoryManager._rebuild_memory_counters(user_id)
        
        # Get all counts from Redis hash (single operation!)
        type_counts = {}
        counter_data = r.hgetall(counters_key)
        
        for mem_type, count in counter_data.items():
            type_key = mem_type.decode() if isinstance(mem_type, bytes) else mem_type
            count_val = int(count.decode() if isinstance(count, bytes) else count)
            type_counts[type_key] = count_val
        
        return type_counts
    
    @staticmethod
    @try_catch_decorator
    def _rebuild_memory_counters(user_id: str):
        """Rebuild memory counters from scratch (one-time operation)."""
        index_key = MemoryManager.get_index_key(user_id)
        memory_ids = monitored_smembers(index_key)
        counters_key = redis_keys.get_user_memory_counters_key(user_id)
        
        # Clear existing counters
        r.delete(counters_key)
        
        type_counts = {}
        
        # Only get the type field for each memory (much faster than loading full memory)
        for memory_id in memory_ids:
            memory_id = memory_id.decode() if isinstance(memory_id, bytes) else memory_id
            memory_key = MemoryManager.get_memory_key(user_id, memory_id)
            
            try:
                memory_data = monitored_get(memory_key)
                if memory_data:
                    memory = json.loads(memory_data)
                    # Only count active memories
                    if memory.get('status') == 'active':
                        mem_type = memory.get('type', 'unknown')
                        type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
            except (json.JSONDecodeError, KeyError):
                continue
        
        # Save counters to Redis hash
        if type_counts:
            r.hmset(counters_key, type_counts)
            # Set expiry to 7 days (will be refreshed when memories are modified)
            r.expire(counters_key, 86400 * 7)
        
        logger.info(f"Rebuilt memory counters: {type_counts}")
        return type_counts
    
    @staticmethod
    @try_catch_decorator
    def _increment_memory_counter(user_id: str, memory_type: str):
        """Increment memory counter for a specific type."""
        counters_key = redis_keys.get_user_memory_counters_key(user_id)
        r.hincrby(counters_key, memory_type, 1)
        # Refresh expiry to 7 days
        r.expire(counters_key, 86400 * 7)
    
    @staticmethod
    @try_catch_decorator
    def _decrement_memory_counter(user_id: str, memory_type: str):
        """Decrement memory counter for a specific type."""
        counters_key = redis_keys.get_user_memory_counters_key(user_id)
        current = r.hget(counters_key, memory_type)
        if current and int(current) > 0:
            r.hincrby(counters_key, memory_type, -1)
        # Refresh expiry to 7 days
        r.expire(counters_key, 86400 * 7)
    
    @staticmethod
    @try_catch_decorator
    def _get_recent_memories_by_type(user_id: str, memory_type: str, limit: int = 10) -> List[Dict]:
        """Get recent memories of a specific type efficiently (for deduplication)."""
        index_key = MemoryManager.get_index_key(user_id)
        memory_ids = monitored_smembers(index_key)
        
        # Get memories of the specific type, sorted by creation date
        matching_memories = []
        
        for memory_id in memory_ids:
            memory_id = memory_id.decode() if isinstance(memory_id, bytes) else memory_id
            memory = MemoryManager.get_memory(user_id, memory_id)
            
            if (memory and 
                memory.get('status') == 'active' and 
                memory.get('type') == memory_type):
                matching_memories.append(memory)
            
            # Stop early if we have enough memories
            if len(matching_memories) >= limit * 2:  # Get extra to sort properly
                break
        
        # Sort by creation date (newest first) and return limited results
        matching_memories.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return matching_memories[:limit]
    
    @staticmethod
    @try_catch_decorator
    def get_memories_paginated(
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = 'created_at',
        sort_order: str = 'desc',
        memory_type: str = None,
        search_query: str = None
    ) -> Tuple[List[Dict], int]:
        """Get paginated memories with filtering and sorting - much more efficient for large datasets."""
        try:
            # Get all memory IDs first
            index_key = MemoryManager.get_index_key(user_id)
            memory_ids = monitored_smembers(index_key)
            
            # Load and filter memories
            valid_memories = []
            for memory_id in memory_ids:
                memory_id = memory_id.decode() if isinstance(memory_id, bytes) else memory_id
                memory_key = MemoryManager.get_memory_key(user_id, memory_id)
                
                try:
                    memory_data = monitored_get(memory_key)
                    if not memory_data:
                        continue
                        
                    memory = json.loads(memory_data)
                    
                    # Skip inactive memories
                    if memory.get('status') != 'active':
                        continue
                    
                    # Apply type filter
                    if memory_type and memory.get('type') != memory_type:
                        continue
                    
                    # Apply search filter
                    if search_query:
                        search_lower = search_query.lower()
                        content_lower = memory.get('content', '').lower()
                        user_id_lower = memory.get('user_id', '').lower()
                        
                        if not (search_lower in content_lower or search_lower in user_id_lower):
                            continue
                    
                    valid_memories.append(memory)
                    
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
            
            # Sort memories
            def get_sort_value(memory):
                if sort_by == 'created_at':
                    return memory.get('created_at', '')
                elif sort_by == 'type':
                    return memory.get('type', '')
                elif sort_by == 'content':
                    return memory.get('content', '').lower()
                else:
                    return memory.get('created_at', '')
            
            reverse_sort = sort_order == 'desc'
            valid_memories.sort(key=get_sort_value, reverse=reverse_sort)
            
            # Calculate pagination
            total_count = len(valid_memories)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            # Get current page memories
            page_memories = valid_memories[start_idx:end_idx]
            
            # Update access stats for retrieved memories
            for memory in page_memories:
                memory['last_accessed'] = datetime.now().isoformat()
                memory['access_count'] = memory.get('access_count', 0) + 1
                # Note: We're not updating Redis here for performance reasons
                # Consider updating only when memories are actually viewed/edited
            
            logger.debug(f"Retrieved page {page} ({len(page_memories)} memories) from {total_count} total for user {user_id}")
            return page_memories, total_count
            
        except Exception as e:
            logger.error(f"Error in get_memories_paginated: {e}")
            return [], 0
    
    @staticmethod
    @try_catch_decorator
    def update_memory(user_id: str, memory_id: str, updates: Dict) -> bool:
        """Update an existing memory."""
        memory = MemoryManager.get_memory(user_id, memory_id)
        if not memory:
            return False
        
        # Track type changes for counter updates
        old_type = memory.get('type')
        old_status = memory.get('status')
        
        # Update fields
        for key, value in updates.items():
            if key not in ['id', 'user_id', 'created_at']:
                memory[key] = value
        
        memory['updated_at'] = datetime.now().isoformat()
        
        # Save updated memory
        key = MemoryManager.get_memory_key(user_id, memory_id)
        monitored_set(key, json.dumps(memory))
        
        # Update counters if type changed or status changed
        new_type = memory.get('type')
        new_status = memory.get('status')
        
        if old_status == 'active' and new_status == 'archived':
            # Memory was archived (soft deleted)
            MemoryManager._decrement_memory_counter(user_id, old_type)
        elif old_status == 'archived' and new_status == 'active':
            # Memory was restored
            MemoryManager._increment_memory_counter(user_id, new_type)
        elif old_status == 'active' and new_status == 'active' and old_type != new_type:
            # Type changed for active memory
            MemoryManager._decrement_memory_counter(user_id, old_type)
            MemoryManager._increment_memory_counter(user_id, new_type)
        
        logger.info(f"Updated memory {memory_id} for user {user_id}")
        return True
    
    @staticmethod
    @try_catch_decorator
    def delete_memory(user_id: str, memory_id: str) -> bool:
        """Delete a memory (soft delete by marking as archived)."""
        return MemoryManager.update_memory(
            user_id, 
            memory_id, 
            {'status': 'archived', 'archived_at': datetime.now().isoformat()}
        )
    
    @staticmethod
    @try_catch_decorator
    def cleanup_question_memories(user_id: str) -> int:
        """Clean up memories that were incorrectly extracted from questions."""
        cleaned_count = 0
        all_memories = MemoryManager.get_all_memories(user_id)
        
        question_indicators = [
            'who is', 'what is', 'where is', 'when is', 'how is', 'why is'
        ]
        
        for memory in all_memories:
            content_lower = memory['content'].lower()
            if any(indicator in content_lower for indicator in question_indicators):
                MemoryManager.delete_memory(user_id, memory['id'])
                cleaned_count += 1
                logger.info(f"Cleaned up question memory: {memory['content']}")
        
        return cleaned_count
    
    @staticmethod
    @try_catch_decorator
    def extract_memories_from_text(text: str, user_id: str) -> List[Tuple[str, str, str]]:
        """Extract potential memories from text using AI-powered analysis."""
        text_stripped = text.strip()
        
        # Skip very short messages or common greetings
        if len(text_stripped) < 10 or text_stripped.lower() in ['hi', 'hello', 'hey', 'thanks', 'ok', 'okay']:
            return []
        
        # Use AI to analyze if this contains memorable information
        try:
            from utils.gemini import simple_prompt_request
            
            analysis_prompt = f"""
            Analyze this message for memorable personal information: "{text}"
            
            Classification guidelines:
            - relationship: family members, friends, colleagues (include their names!)
            - important_date: birthdays, anniversaries, special dates
            - allergy: food allergies, medical restrictions
            - preference: likes, dislikes, favorites
            - personal_info: contact details, addresses, job titles
            - note: general information worth remembering
            
            Task:
            1. If this is a question, return "QUESTION"
            2. Extract and rephrase as natural statements
            3. IMPORTANT: For relationships, keep the specific names (e.g., "My [relation] is [name]" not just "has [relation]")
            4. Pay special attention: birthdays/birth dates = important_date (not personal_info)
            
            Return format:
            TYPE: relationship|preference|allergy|important_date|personal_info|note|QUESTION
            CONTENT: [natural statement with names preserved] or QUESTION
            """
            
            response = simple_prompt_request(analysis_prompt)
            
            # Parse AI response
            lines = response.strip().split('\n')
            memory_type = None
            content = None
            
            for line in lines:
                if line.startswith('TYPE:'):
                    memory_type = line.replace('TYPE:', '').strip()
                elif line.startswith('CONTENT:'):
                    content = line.replace('CONTENT:', '').strip()
            
            # Check if it's a question or has no memorable content
            if memory_type == 'QUESTION' or content == 'QUESTION' or not memory_type or not content:
                logger.debug(f"AI determined no memorable content in: {text}")
                return []
            
            # Handle explicit "remember" commands differently
            if text.lower().startswith('remember'):
                memory_type = 'note'
                content = text.replace('remember that', '').replace('remember', '').strip()
            
            # Clean up AI extraction artifacts if present
            if content.startswith('From ') and ':' in content:
                # Extract just the actual content after the colon
                parts = content.split(':', 1)
                if len(parts) == 2:
                    content = parts[1].strip()
            
            logger.info(f"AI extracted memory - Type: {memory_type}, Content: {content}")
            return [(memory_type, content, text)]
            
        except Exception as e:
            logger.error(f"Error in AI memory extraction: {e}")
            # Fallback to simple explicit remember detection
            if text.lower().startswith('remember'):
                content = text.replace('remember that', '').replace('remember', '').strip()
                return [('note', content, text)]
            return []
    
    @staticmethod
    @try_catch_decorator
    def get_memories_by_type(user_id: str, memory_type: str) -> List[Dict]:
        """Get all memories of a specific type."""
        all_memories = MemoryManager.get_all_memories(user_id)
        return [m for m in all_memories if m['type'] == memory_type]
    
    @staticmethod
    @try_catch_decorator
    def get_memories_by_tags(user_id: str, tags: List[str]) -> List[Dict]:
        """Get memories that have any of the specified tags."""
        all_memories = MemoryManager.get_all_memories(user_id)
        matching = []
        
        for memory in all_memories:
            memory_tags = memory.get('tags', [])
            if any(tag in memory_tags for tag in tags):
                matching.append(memory)
        
        return matching
    
    @staticmethod
    @try_catch_decorator
    def get_relevant_memories_for_context(user_id: str, message: str, limit: int = 3) -> List[Dict]:
        """Get memories relevant to the current message context."""
        relevant = []
        message_lower = message.lower()
        
        # Time-based relevance
        if any(word in message_lower for word in ['tomorrow', 'today', 'week', 'monday', 'tuesday']):
            routines = MemoryManager.get_memories_by_type(user_id, 'routine')
            relevant.extend(routines[:2])
        
        # Food/restaurant context
        if any(word in message_lower for word in ['eat', 'food', 'restaurant', 'lunch', 'dinner']):
            allergies = MemoryManager.get_memories_by_type(user_id, 'allergy')
            preferences = MemoryManager.search_memories(user_id, 'food', 'preference')
            relevant.extend(allergies)
            relevant.extend(preferences[:2])
        
        # People context - extract names
        import re
        name_pattern = r'\b[A-Z][a-z]+\b'
        names = re.findall(name_pattern, message)
        for name in names:
            people_memories = MemoryManager.search_memories(user_id, name, 'relationship')
            relevant.extend(people_memories[:1])
        
        # Remove duplicates and limit
        seen = set()
        unique = []
        for memory in relevant:
            if memory['id'] not in seen:
                seen.add(memory['id'])
                unique.append(memory)
        
        return unique[:limit]
    
    @staticmethod
    @try_catch_decorator
    def format_memories_for_prompt(memories: List[Dict]) -> str:
        """Format memories for inclusion in AI prompts."""
        if not memories:
            return ""
        
        formatted = []
        for memory in memories:
            formatted.append(f"[{memory['type']}] {memory['content']}")
        
        return "Relevant memories: " + "; ".join(formatted)
    
    @staticmethod
    @try_catch_decorator
    def check_memory_triggers(user_id: str) -> List[str]:
        """Check for proactive memory-based reminders."""
        triggers = []
        memories = MemoryManager.get_all_memories(user_id)
        now = datetime.now()
        
        for memory in memories:
            # Birthday reminders (3 days before)
            if memory['type'] == 'important_date' and 'birthday' in memory['content'].lower():
                # Extract date from content
                date_match = re.search(r'(\d{1,2})[/-](\d{1,2})', memory['content'])
                if date_match:
                    month, day = int(date_match.group(1)), int(date_match.group(2))
                    birthday_this_year = datetime(now.year, month, day)
                    
                    # If birthday passed this year, check next year
                    if birthday_this_year < now:
                        birthday_this_year = datetime(now.year + 1, month, day)
                    
                    days_until = (birthday_this_year - now).days
                    if 0 <= days_until <= 3:
                        triggers.append(f"Reminder: {memory['content']} in {days_until} days!")
            
            # Routine reminders
            if memory['type'] == 'routine':
                # Check if it's time for the routine
                day_match = re.search(r'every (\w+)', memory['content'].lower())
                if day_match:
                    routine_day = day_match.group(1)
                    current_day = now.strftime('%A').lower()
                    if routine_day == current_day or routine_day == 'day':
                        triggers.append(f"Daily routine: {memory['content']}")
        
        return triggers