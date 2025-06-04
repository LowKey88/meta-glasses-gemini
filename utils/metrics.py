"""Metrics tracking for dashboard analytics"""
import json
from datetime import datetime, timedelta
from typing import Dict, List
from utils.redis_utils import r
from utils.redis_monitor import (
    monitored_hincrby, monitored_expire, monitored_hget, monitored_hset,
    monitored_hkeys, monitored_exists
)
from utils.redis_key_builder import redis_keys
import logging

logger = logging.getLogger("uvicorn")

class MetricsTracker:
    @staticmethod
    def track_ai_request(model_type: str = "chat", response_time: float = 0.0):
        """Track AI API request"""
        try:
            # Track daily count
            today_key = redis_keys.get_ai_requests_key(datetime.now().strftime('%Y-%m-%d'))
            monitored_hincrby(today_key, model_type, 1)
            monitored_expire(today_key, 86400 * 7)  # Keep for 7 days
            
            # Track response time
            if response_time > 0:
                rt_key = redis_keys.get_response_times_key(datetime.now().strftime('%Y-%m-%d'))
                existing = monitored_hget(rt_key, model_type)
                if existing:
                    times = json.loads(existing)
                    times.append(response_time)
                else:
                    times = [response_time]
                monitored_hset(rt_key, model_type, json.dumps(times[-100:]))  # Keep last 100
                monitored_expire(rt_key, 86400 * 7)
        except Exception as e:
            logger.error(f"Error tracking AI request: {e}")
    
    @staticmethod
    def track_message(user_id: str, message_type: str = "text"):
        """Track WhatsApp message"""
        try:
            # Track hourly count
            now = datetime.now()
            hour_key = redis_keys.get_messages_key(now.strftime('%Y-%m-%d'), now.strftime('%H'))
            monitored_hincrby(hour_key, message_type, 1)
            monitored_expire(hour_key, 86400 * 2)  # Keep for 2 days
            
            # Track user activity
            user_key = redis_keys.get_user_activity_key(now.strftime('%Y-%m-%d'))
            monitored_hincrby(user_key, user_id, 1)
            monitored_expire(user_key, 86400 * 7)
        except Exception as e:
            logger.error(f"Error tracking message: {e}")
    
    @staticmethod
    def get_ai_requests_today() -> int:
        """Get total AI requests for today"""
        try:
            today_key = redis_keys.get_ai_requests_key(datetime.now().strftime('%Y-%m-%d'))
            total = 0
            for model_type in monitored_hkeys(today_key):
                count = monitored_hget(today_key, model_type)
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
                hour_key = redis_keys.get_messages_key(hour_time.strftime('%Y-%m-%d'), hour_time.strftime('%H'))
                
                # Create hour label with visual separation for different days
                if hour_time.date() == now.date():
                    # Today: just show hour
                    hour_label = hour_time.strftime('%H:00')
                elif hour_time.date() == (now - timedelta(days=1)).date():
                    # Yesterday: prefix with "Y-"
                    hour_label = f"Y-{hour_time.strftime('%H:00')}"
                else:
                    # Other days: show day abbreviation
                    hour_label = hour_time.strftime('%a %H:00')
                
                hour_total = 0
                # Check if the key exists and sum all message types
                if monitored_exists(hour_key):
                    for msg_type in monitored_hkeys(hour_key):
                        count = monitored_hget(hour_key, msg_type)
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
                hour_key = redis_keys.get_messages_key(hour_time.strftime('%Y-%m-%d'), hour_time.strftime('%H'))
                
                if monitored_exists(hour_key):
                    for msg_type in monitored_hkeys(hour_key):
                        count = monitored_hget(hour_key, msg_type)
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
                hour_key = redis_keys.get_messages_key(hour_time.strftime('%Y-%m-%d'), hour_time.strftime('%H'))
                
                if monitored_exists(hour_key):
                    for msg_type in monitored_hkeys(hour_key):
                        count = monitored_hget(hour_key, msg_type)
                        if count:
                            total += int(count)
            
            return total
        except Exception as e:
            logger.error(f"Error getting today's message count: {e}")
            return 0
    
    @staticmethod
    def get_weekly_message_activity() -> Dict[str, int]:
        """Get daily message totals for the last 7 days"""
        try:
            activity = {}
            now = datetime.now()
            
            # Get data for the last 7 days
            for days_ago in range(6, -1, -1):  # Start from 6 days ago to today
                day = now - timedelta(days=days_ago)
                day_total = 0
                
                # Sum all hours for this day
                for hour in range(24):
                    # Only count up to current hour for today
                    if days_ago == 0 and hour > now.hour:
                        break
                        
                    hour_time = day.replace(hour=hour, minute=0, second=0, microsecond=0)
                    hour_key = redis_keys.get_messages_key(hour_time.strftime('%Y-%m-%d'), hour_time.strftime('%H'))
                    
                    if monitored_exists(hour_key):
                        for msg_type in monitored_hkeys(hour_key):
                            count = monitored_hget(hour_key, msg_type)
                            if count:
                                day_total += int(count)
                
                # Format day label
                if days_ago == 0:
                    day_label = "Today"
                elif days_ago == 1:
                    day_label = "Yesterday"
                else:
                    day_label = day.strftime('%a')  # Mon, Tue, etc.
                
                activity[day_label] = day_total
            
            return activity
        except Exception as e:
            logger.error(f"Error getting weekly message activity: {e}")
            return {}
    
    @staticmethod
    def get_today_vs_yesterday_hourly() -> Dict[str, Dict[str, int]]:
        """Get hourly comparison between today and yesterday"""
        try:
            today = datetime.now()
            yesterday = today - timedelta(days=1)
            
            today_data = {}
            yesterday_data = {}
            
            # Get hourly data for both days
            for hour in range(24):
                hour_label = f"{hour:02d}:00"
                
                # Today's data (only up to current hour)
                if hour <= today.hour:
                    today_key = redis_keys.get_messages_key(today.strftime('%Y-%m-%d'), f"{hour:02d}")
                    today_total = 0
                    if monitored_exists(today_key):
                        for msg_type in monitored_hkeys(today_key):
                            count = monitored_hget(today_key, msg_type)
                            if count:
                                today_total += int(count)
                    today_data[hour_label] = today_total
                else:
                    today_data[hour_label] = 0
                
                # Yesterday's data (all 24 hours)
                yesterday_key = redis_keys.get_messages_key(yesterday.strftime('%Y-%m-%d'), f"{hour:02d}")
                yesterday_total = 0
                if monitored_exists(yesterday_key):
                    for msg_type in monitored_hkeys(yesterday_key):
                        count = monitored_hget(yesterday_key, msg_type)
                        if count:
                            yesterday_total += int(count)
                yesterday_data[hour_label] = yesterday_total
            
            return {
                "today": today_data,
                "yesterday": yesterday_data
            }
        except Exception as e:
            logger.error(f"Error getting today vs yesterday comparison: {e}")
            return {"today": {}, "yesterday": {}}
    
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