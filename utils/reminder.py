import os
import logging
from datetime import datetime, timedelta
import json
from typing import Dict, Optional

from utils.redis_utils import r, try_catch_decorator, delete_reminder
from utils.whatsapp import send_whatsapp_message
from utils.google_api import get_calendar_service

logger = logging.getLogger("uvicorn")

REMINDER_KEY_PREFIX = "josancamon:rayban-meta-glasses-api:reminder:"
MORNING_REMINDER_HOUR = 8  # Send morning reminders at 8 AM
TIME_ZONE = 'Asia/Kuala_Lumpur'

def verify_event_exists(event_id: str) -> bool:
    """
    Verify if an event still exists in Google Calendar.
    If not, clean up the Redis reminder.
    
    Args:
        event_id: The Google Calendar event ID
        
    Returns:
        bool: True if event exists, False if not
    """
    try:
        service = get_calendar_service()
        if not service:
            return False
            
        try:
            # Try to get the event
            service.events().get(calendarId='primary', eventId=event_id).execute()
            return True
        except Exception:
            # If event doesn't exist, clean up Redis
            logger.info(f"Event {event_id} no longer exists in Google Calendar, cleaning up Redis reminder")
            delete_reminder(event_id)
            return False
            
    except Exception as e:
        logger.error(f"Error verifying event existence: {e}")
        return False

class ReminderManager:
    @staticmethod
    @try_catch_decorator
    def sync_with_calendar():
        """
        Sync Redis reminders with Google Calendar events.
        Removes reminders for deleted events and adds reminders for new events.
        """
        service = get_calendar_service()
        if not service:
            logger.error("Failed to get calendar service during sync")
            return

        # Get all existing reminders from Redis
        existing_reminders = {}
        for key in r.scan_iter(f"{REMINDER_KEY_PREFIX}*"):
            event_id = key.decode().replace(REMINDER_KEY_PREFIX, "")
            data = r.get(key)
            if data:
                existing_reminders[event_id] = json.loads(data)

        # Get upcoming events from Google Calendar
        now = datetime.now().astimezone()
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat(),
            maxResults=100,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        calendar_events = {event['id']: event for event in events_result.get('items', [])}

        # Remove reminders for deleted events
        for event_id in existing_reminders:
            if event_id not in calendar_events:
                logger.info(f"Removing reminder for deleted event: {event_id}")
                delete_reminder(event_id)

        # Add reminders for new events
        for event_id, event in calendar_events.items():
            if event_id not in existing_reminders:
                start = event['start'].get('dateTime', event['start'].get('date'))
                start_time = datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone()
                
                # Convert to timezone-aware datetime for comparison
                now = datetime.now().astimezone()
                
                # Only add reminder if event is in the future
                if start_time > now:
                    logger.info(f"Adding reminder for new event: {event.get('summary', 'Untitled')}")
                    ReminderManager.schedule_meeting_reminders(
                        event_id=event_id,
                        title=event.get('summary', 'Untitled'),
                        start_time=start_time
                    )
                    
        logger.info("Calendar sync completed")

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
        
        logger.info(f"Scheduled reminders for '{title}' at {start_time.strftime('%I:%M %p')}.")
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
    def _collect_todays_events(now: datetime):
        """Collect all events scheduled for today."""
        todays_events = []
        for key in r.scan_iter(f"{REMINDER_KEY_PREFIX}*"):
            data = r.get(key)
            if not data:
                continue
                
            reminder_data = json.loads(data)
            event_id = key.decode().replace(REMINDER_KEY_PREFIX, "")
            start_time = datetime.fromisoformat(reminder_data["start_time"]).astimezone()
            
            # Skip if event is in the past
            if start_time < now:
                continue
                
            if start_time.date() == now.date():
                todays_events.append({
                    "event_id": event_id,
                    "title": reminder_data["title"],
                    "start_time": start_time,
                    "morning_reminder_sent": reminder_data["morning_reminder_sent"],
                    "hour_before_reminder_sent": reminder_data["hour_before_reminder_sent"],
                    "start_reminder_sent": reminder_data.get("start_reminder_sent", False)
                })
        
        return sorted(todays_events, key=lambda x: x["start_time"])

    @staticmethod
    @try_catch_decorator
    def check_and_send_pending_reminders():
        """Check for and send any pending reminders."""
        now = datetime.now().astimezone()
        
        # Handle morning reminders - collect all events for today
        if now.hour == MORNING_REMINDER_HOUR:
            todays_events = ReminderManager._collect_todays_events(now)
            unsent_morning_reminders = [
                event for event in todays_events
                if not event["morning_reminder_sent"]
            ]
            
            if unsent_morning_reminders:
                # Filter out events that no longer exist in Google Calendar
                valid_reminders = [
                    event for event in unsent_morning_reminders
                    if verify_event_exists(event["event_id"])
                ]
                
                if valid_reminders:
                    # Create a single morning message for all valid events
                    events_text = "\n".join(
                        f"• '{event['title']}' at {ReminderManager._format_time(event['start_time'])}"
                        for event in valid_reminders
                    )
                    message = f"Good morning! Here's your schedule for today:\n{events_text}"
                    send_whatsapp_message(message)
                    
                    # Mark all morning reminders as sent
                    for event in valid_reminders:
                        ReminderManager.mark_reminder_sent(event["event_id"], "morning")
        
        # Handle individual reminders (hour before and start time)
        for key in r.scan_iter(f"{REMINDER_KEY_PREFIX}*"):
            data = r.get(key)
            if not data:
                continue
                
            reminder_data = json.loads(data)
            event_id = key.decode().replace(REMINDER_KEY_PREFIX, "")
            
            # Verify event still exists in Google Calendar
            if not verify_event_exists(event_id):
                continue
                
            start_time = datetime.fromisoformat(reminder_data["start_time"]).astimezone()
            
            # Skip if event is in the past
            if start_time < now:
                continue
            
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