import os
import logging
from datetime import datetime, timedelta
import json
from typing import Dict, Optional

from utils.redis_utils import r, try_catch_decorator
from utils.whatsapp import send_whatsapp_message

logger = logging.getLogger("uvicorn")

REMINDER_KEY_PREFIX = "josancamon:rayban-meta-glasses-api:reminder:"
MORNING_REMINDER_HOUR = 8  # Send morning reminders at 8 AM

class ReminderManager:
    @staticmethod
    @try_catch_decorator
    def schedule_meeting_reminders(event_id: str, title: str, start_time: datetime) -> bool:
        """
        Schedule reminders for a meeting.
        
        Args:
            event_id: The Google Calendar event ID
            title: The meeting title
            start_time: The meeting start time
            
        Returns:
            bool: True if reminders were scheduled successfully
        """
        reminder_data = {
            "title": title,
            "start_time": start_time.isoformat(),
            "morning_reminder_sent": False,
            "hour_before_reminder_sent": False,
            "start_reminder_sent": False
        }
        
        # Store reminder data in Redis
        key = f"{REMINDER_KEY_PREFIX}{event_id}"
        r.set(key, json.dumps(reminder_data))
        
        # Set expiration for 1 day after the meeting
        expiration = start_time + timedelta(days=1)
        r.expireat(key, expiration)
        
        logger.info(f"Scheduled reminders for meeting '{title}' at {start_time.strftime('%I:%M %p')}.")
        return True

    @staticmethod
    @try_catch_decorator
    def get_reminder(event_id: str) -> Optional[Dict]:
        """Get reminder data for an event."""
        key = f"{REMINDER_KEY_PREFIX}{event_id}"
        data = r.get(key)
        return json.loads(data) if data else None

    @staticmethod
    @try_catch_decorator
    def mark_reminder_sent(event_id: str, reminder_type: str) -> bool:
        """Mark a specific reminder as sent."""
        key = f"{REMINDER_KEY_PREFIX}{event_id}"
        data = r.get(key)
        if not data:
            return False
            
        reminder_data = json.loads(data)
        # Ensure all fields exist with default False
        reminder_data.setdefault("morning_reminder_sent", False)
        reminder_data.setdefault("hour_before_reminder_sent", False)
        reminder_data.setdefault("start_reminder_sent", False)

        if reminder_type == "morning":
            reminder_data["morning_reminder_sent"] = True
        elif reminder_type == "hour_before":
            reminder_data["hour_before_reminder_sent"] = True
        elif reminder_type == "start":
            reminder_data["start_reminder_sent"] = True
            
        r.set(key, json.dumps(reminder_data))
        return True

    @staticmethod
    def _format_time(dt: datetime) -> str:
        """Format time in 12-hour format."""
        return dt.strftime("%I:%M %p")

    @staticmethod
    @try_catch_decorator
    def check_and_send_pending_reminders():
        """Check for and send any pending reminders."""
        now = datetime.now()
        
        # Scan all reminder keys
        for key in r.scan_iter(f"{REMINDER_KEY_PREFIX}*"):
            data = r.get(key)
            if not data:
                continue
                
            reminder_data = json.loads(data)
            event_id = key.decode().replace(REMINDER_KEY_PREFIX, "")
            start_time = datetime.fromisoformat(reminder_data["start_time"])
            
            # Skip if meeting is in the past
            if start_time < now:
                continue
            
            # Check morning reminder
            if not reminder_data["morning_reminder_sent"]:
                if now.hour == MORNING_REMINDER_HOUR and start_time.date() == now.date():
                    message = (
                        f"Good morning! '{reminder_data['title']}' is "
                        f"scheduled for {ReminderManager._format_time(start_time)} today"
                    )
                    send_whatsapp_message(message)
                    ReminderManager.mark_reminder_sent(event_id, "morning")
            
            # Check hour before reminder
            if not reminder_data["hour_before_reminder_sent"]:
                time_until_start = start_time - now
                if timedelta(minutes=55) <= time_until_start <= timedelta(minutes=65):
                    message = (
                        f"Reminder: '{reminder_data['title']}' starts in 1 hour "
                        f"at {ReminderManager._format_time(start_time)}"
                    )
                    send_whatsapp_message(message)
                    ReminderManager.mark_reminder_sent(event_id, "hour_before")
            
            # Check meeting start reminder
            if not reminder_data.get("start_reminder_sent", False):  # Use .get() with default False for backward compatibility
                time_until_start = start_time - now
                if timedelta(minutes=-1) <= time_until_start <= timedelta(minutes=1):
                    message = f"'{reminder_data['title']}' is starting now!"
                    send_whatsapp_message(message)
                    ReminderManager.mark_reminder_sent(event_id, "start")

# Function to be called by scheduler/cron job
def check_reminders():
    """Check and send pending reminders. This should be called every minute."""
    ReminderManager.check_and_send_pending_reminders()