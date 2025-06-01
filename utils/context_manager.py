import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from utils.redis_utils import r, try_catch_decorator

logger = logging.getLogger("uvicorn")

# Constants
CONVERSATION_HISTORY_KEY = "conversation_history"
USER_PROFILE_KEY = "user_profile"
HISTORY_LIMIT = 20  # Keep last 20 messages
HISTORY_TTL = 86400 * 7  # 7 days TTL for conversation history


class ContextManager:
    """Manages conversation context and user profiles for personalized interactions."""
    
    @staticmethod
    @try_catch_decorator
    def get_user_key(user_id: str, key_type: str) -> str:
        """Generate Redis key for user data."""
        return f"josancamon:rayban-meta-glasses-api:{key_type}:{user_id}"
    
    @staticmethod
    @try_catch_decorator
    def add_to_conversation_history(user_id: str, message: str, response: str, message_type: str = "other"):
        """Add a message-response pair to conversation history."""
        key = ContextManager.get_user_key(user_id, CONVERSATION_HISTORY_KEY)
        
        # Create conversation entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "response": response,
            "type": message_type
        }
        
        # Get existing history
        history_data = r.get(key)
        if history_data:
            history = json.loads(history_data)
        else:
            history = []
        
        # Add new entry and maintain limit
        history.append(entry)
        if len(history) > HISTORY_LIMIT:
            history = history[-HISTORY_LIMIT:]
        
        # Save back to Redis with TTL
        r.set(key, json.dumps(history), ex=HISTORY_TTL)
        logger.debug(f"Added conversation history for user {user_id}")
    
    @staticmethod
    @try_catch_decorator
    def get_conversation_history(user_id: str, limit: int = 5) -> List[Dict]:
        """Get recent conversation history for a user."""
        key = ContextManager.get_user_key(user_id, CONVERSATION_HISTORY_KEY)
        
        history_data = r.get(key)
        if not history_data:
            return []
        
        history = json.loads(history_data)
        return history[-limit:] if len(history) > limit else history
    
    @staticmethod
    @try_catch_decorator
    def update_user_profile(user_id: str, profile_data: Dict):
        """Update user profile with preferences and learned information."""
        key = ContextManager.get_user_key(user_id, USER_PROFILE_KEY)
        
        # Get existing profile
        existing_data = r.get(key)
        if existing_data:
            profile = json.loads(existing_data)
        else:
            profile = {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "preferences": {},
                "context": {},
                "stats": {
                    "total_messages": 0,
                    "frequent_commands": {}
                }
            }
        
        # Update profile with new data
        for key, value in profile_data.items():
            if key in ["preferences", "context"]:
                profile[key].update(value)
            else:
                profile[key] = value
        
        # Update stats
        profile["last_interaction"] = datetime.now().isoformat()
        profile["stats"]["total_messages"] = profile["stats"].get("total_messages", 0) + 1
        
        # Save profile (no expiry for user profiles)
        r.set(ContextManager.get_user_key(user_id, USER_PROFILE_KEY), json.dumps(profile))
        logger.debug(f"Updated user profile for {user_id}")
    
    @staticmethod
    @try_catch_decorator
    def get_user_profile(user_id: str) -> Optional[Dict]:
        """Get user profile data."""
        key = ContextManager.get_user_key(user_id, USER_PROFILE_KEY)
        
        profile_data = r.get(key)
        if not profile_data:
            return None
        
        return json.loads(profile_data)
    
    @staticmethod
    @try_catch_decorator
    def extract_user_name(message: str, user_id: str) -> Optional[str]:
        """Extract user name from messages like 'I am John' or 'My name is Sarah'."""
        import re
        
        # Patterns to extract names
        patterns = [
            r"(?:i am|i'm|my name is|this is|call me)\s+([A-Z][a-z]+)",
            r"^([A-Z][a-z]+)\s+here",
            r"(?:friends call me|people call me|just call me)\s+([A-Z][a-z]+)",
            r"(?:actually|it's actually)\s+([A-Z][a-z]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                name = match.group(1).capitalize()
                # Update user profile with name
                ContextManager.update_user_profile(user_id, {"name": name})
                logger.info(f"Extracted user name: {name} for user {user_id}")
                return name
        
        return None
    
    @staticmethod
    @try_catch_decorator
    def extract_preferences(message: str, user_id: str) -> Dict:
        """Extract user preferences from natural language."""
        import re
        
        preferences = {}
        message_lower = message.lower()
        
        # Meeting duration preferences
        duration_match = re.search(r'(\d+)[\s-]?(?:minute|min|hour|hr)', message_lower)
        if duration_match and any(word in message_lower for word in ['meeting', 'appointment', 'usually', 'prefer']):
            duration = int(duration_match.group(1))
            if 'hour' in message_lower or 'hr' in message_lower:
                duration *= 60
            preferences['default_meeting_duration'] = duration
            logger.info(f"Extracted meeting duration preference: {duration} minutes")
        
        # Time preferences
        if any(word in message_lower for word in ['morning', 'afternoon', 'evening', 'night']):
            if 'morning' in message_lower:
                preferences['preferred_time'] = 'morning'
            elif 'afternoon' in message_lower:
                preferences['preferred_time'] = 'afternoon'
            elif 'evening' in message_lower:
                preferences['preferred_time'] = 'evening'
            elif 'night' in message_lower:
                preferences['preferred_time'] = 'night'
        
        # Work/Personal info
        work_match = re.search(r'(?:work as|job is|i am a|i\'m a)\s+(.+?)(?:\.|,|$)', message_lower)
        if work_match:
            job_raw = work_match.group(1).strip()
            # Use AI to properly format the job title and company
            try:
                from utils.gemini import simple_prompt_request
                formatted_job = simple_prompt_request(
                    f"Format this job description with proper capitalization: '{job_raw}'. "
                    f"Return only the formatted text, no explanation. Keep the structure same."
                )
                job = formatted_job.strip() if formatted_job else job_raw.title()
            except:
                # Fallback to simple title case
                job = job_raw.title()
            
            ContextManager.update_user_profile(user_id, {"context": {"job": job}})
            logger.info(f"Extracted job: {job}")
        
        # Interests
        interest_match = re.search(r'(?:interested in|love|enjoy|like)\s+(.+?)(?:\.|,|and|$)', message_lower)
        if interest_match:
            interest_raw = interest_match.group(1).strip()
            # Use AI to properly format the interest
            try:
                from utils.gemini import simple_prompt_request
                formatted_interest = simple_prompt_request(
                    f"Format this interest/topic with proper capitalization: '{interest_raw}'. "
                    f"Return only the formatted text, no explanation."
                )
                interest = formatted_interest.strip() if formatted_interest else interest_raw.title()
            except:
                # Fallback to simple title case
                interest = interest_raw.title()
            
            profile = ContextManager.get_user_profile(user_id) or {"context": {"interests": []}}
            interests = profile.get("context", {}).get("interests", [])
            if interest not in interests:
                interests.append(interest)
            ContextManager.update_user_profile(user_id, {"context": {"interests": interests}})
            logger.info(f"Extracted interest: {interest}")
        
        # Timezone
        tz_match = re.search(r'timezone is\s+([a-z/]+)', message_lower)
        if tz_match:
            preferences['timezone'] = tz_match.group(1)
        
        if preferences:
            ContextManager.update_user_profile(user_id, {"preferences": preferences})
        
        return preferences
    
    @staticmethod
    @try_catch_decorator
    def get_context_summary(user_id: str) -> str:
        """Get a summary of user context for prompt injection."""
        profile = ContextManager.get_user_profile(user_id)
        history = ContextManager.get_conversation_history(user_id, limit=5)
        
        context_parts = []
        
        # Add user name if known
        if profile and profile.get("name"):
            context_parts.append(f"User's name is {profile['name']}")
        
        # Add recent conversation summary
        if history:
            recent_topics = []
            for entry in history[-3:]:  # Last 3 conversations
                if entry.get("type") != "other":
                    recent_topics.append(entry["type"])
            
            if recent_topics:
                context_parts.append(f"Recent topics: {', '.join(set(recent_topics))}")
            
            # Add last interaction time
            last_msg = history[-1]
            last_time = datetime.fromisoformat(last_msg["timestamp"])
            time_diff = datetime.now() - last_time
            
            if time_diff < timedelta(minutes=30):
                context_parts.append("Currently in an active conversation")
            elif time_diff < timedelta(hours=24):
                context_parts.append(f"Last interaction was {int(time_diff.total_seconds() / 3600)} hours ago")
        
        # Add preferences if any
        if profile and profile.get("preferences"):
            prefs = profile["preferences"]
            if prefs:
                context_parts.append(f"User preferences: {json.dumps(prefs)}")
        
        return ". ".join(context_parts) if context_parts else ""
    
    @staticmethod
    @try_catch_decorator
    def track_command_frequency(user_id: str, command_type: str):
        """Track frequency of different command types."""
        profile = ContextManager.get_user_profile(user_id) or {"stats": {"frequent_commands": {}}}
        
        freq = profile["stats"].get("frequent_commands", {})
        freq[command_type] = freq.get(command_type, 0) + 1
        
        ContextManager.update_user_profile(user_id, {
            "stats": {
                "frequent_commands": freq
            }
        })
    
    @staticmethod
    @try_catch_decorator
    def get_personalized_greeting(user_id: str) -> str:
        """Generate a personalized greeting based on user context."""
        profile = ContextManager.get_user_profile(user_id)
        
        if not profile:
            return "Hello! How can I help you today?"
        
        name = profile.get("name", "")
        name_part = f"Hello {name}!" if name else "Hello!"
        
        # Check last interaction
        history = ContextManager.get_conversation_history(user_id, limit=1)
        if history:
            last_msg = history[-1]
            last_time = datetime.fromisoformat(last_msg["timestamp"])
            time_diff = datetime.now() - last_time
            
            if time_diff < timedelta(minutes=30):
                return f"{name_part} What else can I help you with?"
            elif time_diff < timedelta(hours=4):
                return f"Welcome back{', ' + name if name else ''}! How can I assist you?"
            elif time_diff < timedelta(days=1):
                return f"{name_part} Good to see you again. What can I do for you?"
            else:
                return f"{name_part} It's been a while! How can I help you today?"
        
        return f"{name_part} Nice to meet you! How can I assist you?"
    
    @staticmethod
    @try_catch_decorator
    def get_conversation_summary(user_id: str) -> str:
        """Get a summary of recent conversations."""
        history = ContextManager.get_conversation_history(user_id, limit=10)
        
        if not history:
            return "We haven't talked about anything yet."
        
        # Group by topics
        topics = {}
        for entry in history:
            msg_type = entry.get('type', 'other')
            if msg_type not in topics:
                topics[msg_type] = []
            topics[msg_type].append(entry['message'])
        
        # Create summary
        summary_parts = []
        for topic, messages in topics.items():
            if topic != 'other':
                summary_parts.append(f"{topic} ({len(messages)} times)")
        
        if summary_parts:
            return f"We've been discussing: {', '.join(summary_parts)}"
        else:
            return "We've been having a general conversation."
    
    @staticmethod
    @try_catch_decorator
    def understand_context_reference(message: str, user_id: str) -> Optional[str]:
        """Understand contextual references like 'it', 'that', 'the same'."""
        message_lower = message.lower()
        history = ContextManager.get_conversation_history(user_id, limit=3)
        
        if not history:
            return None
        
        # Check for time modifications
        if any(word in message_lower for word in ['actually', 'make it', 'change to', 'instead']):
            # Look for time references in recent messages
            for entry in reversed(history):
                if 'meeting' in entry['message'].lower() or 'appointment' in entry['message'].lower():
                    return f"modify_previous_meeting"
        
        # Check for additions
        if any(word in message_lower for word in ['also', 'add', 'include', 'and']):
            for entry in reversed(history):
                if entry['type'] in ['calendar', 'task']:
                    return f"add_to_previous_{entry['type']}"
        
        # Check for "the usual" or shortcuts
        if any(phrase in message_lower for phrase in ['the usual', 'you know', 'same thing', 'like always']):
            profile = ContextManager.get_user_profile(user_id)
            if profile:
                freq_commands = profile.get('stats', {}).get('frequent_commands', {})
                if freq_commands:
                    # Get most frequent command
                    most_frequent = max(freq_commands, key=freq_commands.get)
                    return f"repeat_{most_frequent}"
        
        return None
    
    @staticmethod
    @try_catch_decorator
    def get_smart_suggestions(user_id: str) -> List[str]:
        """Get smart suggestions based on user patterns."""
        profile = ContextManager.get_user_profile(user_id)
        suggestions = []
        
        if not profile:
            return suggestions
        
        # Time-based suggestions
        current_hour = datetime.now().hour
        freq_commands = profile.get('stats', {}).get('frequent_commands', {})
        
        # Morning suggestions
        if 8 <= current_hour < 12:
            if freq_commands.get('calendar', 0) > 2:
                suggestions.append("Check today's schedule")
            if freq_commands.get('task', 0) > 2:
                suggestions.append("Review today's tasks")
        
        # Evening suggestions
        elif 17 <= current_hour < 22:
            if freq_commands.get('calendar', 0) > 2:
                suggestions.append("Check tomorrow's schedule")
            if freq_commands.get('task', 0) > 2:
                suggestions.append("Plan tomorrow's tasks")
        
        # Based on preferences
        prefs = profile.get('preferences', {})
        if prefs.get('preferred_time') == 'morning' and current_hour >= 18:
            suggestions.append("Set a morning meeting for tomorrow")
        
        return suggestions