"""Metrics tracking for dashboard analytics"""
import json
from datetime import datetime, timedelta
from typing import Dict, List
from utils.redis_utils import r
import logging

logger = logging.getLogger("uvicorn")

class MetricsTracker:
    @staticmethod
    def track_ai_request(model_type: str = "chat", response_time: float = 0.0):
        """Track AI API request"""
        try:
            # Track daily count
            today_key = f"metrics:ai_requests:{datetime.now().strftime('%Y-%m-%d')}"
            r.hincrby(today_key, model_type, 1)
            r.expire(today_key, 86400 * 7)  # Keep for 7 days
            
            # Track response time
            if response_time > 0:
                rt_key = f"metrics:response_times:{datetime.now().strftime('%Y-%m-%d')}"
                existing = r.hget(rt_key, model_type)
                if existing:
                    times = json.loads(existing)
                    times.append(response_time)
                else:
                    times = [response_time]
                r.hset(rt_key, model_type, json.dumps(times[-100:]))  # Keep last 100
                r.expire(rt_key, 86400 * 7)
        except Exception as e:
            logger.error(f"Error tracking AI request: {e}")
    
    @staticmethod
    def track_message(user_id: str, message_type: str = "text"):
        """Track WhatsApp message"""
        try:
            # Track hourly count
            hour_key = f"metrics:messages:{datetime.now().strftime('%Y-%m-%d-%H')}"
            r.hincrby(hour_key, message_type, 1)
            r.expire(hour_key, 86400 * 2)  # Keep for 2 days
            
            # Track user activity
            user_key = f"metrics:user_activity:{datetime.now().strftime('%Y-%m-%d')}"
            r.hincrby(user_key, user_id, 1)
            r.expire(user_key, 86400 * 7)
        except Exception as e:
            logger.error(f"Error tracking message: {e}")
    
    @staticmethod
    def get_ai_requests_today() -> int:
        """Get total AI requests for today"""
        try:
            today_key = f"metrics:ai_requests:{datetime.now().strftime('%Y-%m-%d')}"
            total = 0
            for model_type in r.hkeys(today_key):
                count = r.hget(today_key, model_type)
                if count:
                    total += int(count)
            return total
        except Exception as e:
            logger.error(f"Error getting AI requests: {e}")
            return 0
    
    @staticmethod
    def get_message_activity(hours: int = 24) -> Dict[str, int]:
        """Get message activity for the last N hours - returns hourly counts for charting"""
        try:
            activity = {}
            now = datetime.now()
            
            # Iterate through each hour in the window (from oldest to newest)
            for i in range(hours - 1, -1, -1):
                hour_time = now - timedelta(hours=i)
                hour_key = f"metrics:messages:{hour_time.strftime('%Y-%m-%d-%H')}"
                
                # Create hour label - for a 24-hour window, each hour is unique
                # Format: "HH:00" for current day, "Day HH:00" for previous days
                if hour_time.date() == now.date():
                    hour_label = hour_time.strftime('%H:00')
                else:
                    # Include day abbreviation for hours from previous day
                    hour_label = hour_time.strftime('%a %H:00')
                
                hour_total = 0
                # Check if the key exists and sum all message types
                if r.exists(hour_key):
                    for msg_type in r.hkeys(hour_key):
                        count = r.hget(hour_key, msg_type)
                        if count:
                            hour_total += int(count)
                
                # Store the count for this hour
                activity[hour_label] = hour_total
            
            return activity
        except Exception as e:
            logger.error(f"Error getting message activity: {e}")
            return {}
    
    @staticmethod
    def get_24h_message_count() -> int:
        """Get total message count for the last 24 hours"""
        try:
            total = 0
            now = datetime.now()
            
            # Sum messages from the last 24 hours
            for i in range(24):
                hour_time = now - timedelta(hours=i)
                hour_key = f"metrics:messages:{hour_time.strftime('%Y-%m-%d-%H')}"
                
                if r.exists(hour_key):
                    for msg_type in r.hkeys(hour_key):
                        count = r.hget(hour_key, msg_type)
                        if count:
                            total += int(count)
            
            return total
        except Exception as e:
            logger.error(f"Error getting 24h message count: {e}")
            return 0
    
    @staticmethod
    def get_messages_today() -> int:
        """Get total message count for today (since midnight)"""
        try:
            total = 0
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Calculate hours since midnight
            hours_since_midnight = now.hour + 1  # +1 to include current hour
            
            # Sum messages from midnight to now
            for i in range(hours_since_midnight):
                hour_time = today_start + timedelta(hours=i)
                hour_key = f"metrics:messages:{hour_time.strftime('%Y-%m-%d-%H')}"
                
                if r.exists(hour_key):
                    for msg_type in r.hkeys(hour_key):
                        count = r.hget(hour_key, msg_type)
                        if count:
                            total += int(count)
            
            return total
        except Exception as e:
            logger.error(f"Error getting today's message count: {e}")
            return 0
    
    @staticmethod
    def get_command_distribution() -> Dict[str, int]:
        """Get distribution of command types"""
        try:
            # This would need to be tracked when commands are processed
            # For now, return sample data
            return {
                "calendar": 0,
                "tasks": 0,
                "automation": 0,
                "search": 0,
                "memory": 0,
                "other": 0
            }
        except Exception as e:
            logger.error(f"Error getting command distribution: {e}")
            return {}