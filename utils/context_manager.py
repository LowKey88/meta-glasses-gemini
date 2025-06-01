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