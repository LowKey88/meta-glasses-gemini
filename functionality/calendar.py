import base64
import os
import zoneinfo
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from utils.google_api import get_calendar_service

logger = logging.getLogger("uvicorn")

# Google Calendar colorId mapping:
# 4 - Flamingo (Pink)
# 5 - Banana (Yellow)
# 8 - Graphite (Dark Gray)
# 9 - Blueberry (Blue)
# 10 - Basil (Green)
# 11 - Tomato (Red)

SCOPES = ['https://www.googleapis.com/auth/calendar']
TIME_ZONE = 'Asia/Kuala_Lumpur'

def verify_calendar_colors() -> bool:
    """Verify if calendar colors API is accessible and working."""
    try:
        service = get_calendar_service()
        if not service:
            return False
            
        colors = service.colors().get().execute()
        return 'calendar' in colors and len(colors['calendar']) > 0
    except Exception as e:
        print(f"Error verifying calendar colors: {str(e)}")
        return False

def get_event_color(title: str, description: str) -> int:
    """Determine event color based on title and description."""
    # Ensure inputs are strings
    title = str(title).lower()
    description = str(description).lower()
    
    # Default color for regular meetings (Blueberry)
    color_id = 9
    
    # Check for important meetings/deadlines (Graphite)
    important_keywords = ['important', 'deadline', 'critical', 'priority']
    if any(word in title or word in description for word in important_keywords):
        return 8
    
    # Check for personal appointments (Basil)
    personal_keywords = ['personal', 'break', 'lunch', 'doctor', 'appointment']
    if any(word in title or word in description for word in personal_keywords):
        return 10
    
    # Check for social events (Flamingo)
    social_keywords = ['party', 'celebration', 'dinner', 'social', 'event']
    if any(word in title or word in description for word in social_keywords):
        return 4
    
    # Check for urgent meetings (Tomato)
    urgent_keywords = ['urgent', 'emergency', 'asap', 'immediate']
    if any(word in title or word in description for word in urgent_keywords):
        return 11
    
    # Check for reminders/tasks (Banana)
    task_keywords = ['reminder', 'task', 'todo', 'follow up']
    if any(word in title or word in description for word in task_keywords):
        return 5
    
    return color_id

def create_google_calendar_event(title: str, description: str, date: str, time: str, duration: int = 1, color_id: Optional[int] = None) -> tuple[str, str]:
    """Create a new Google Calendar event."""
    service = get_calendar_service()
    if not service:
        raise Exception("Failed to get calendar service - check credentials")

    # If no description provided, use empty string to prevent None
    description = description or ""
    
    # Ensure duration is not None
    if duration is None:
        duration = 1
    
    # Get color based on title and description if not explicitly provided
    if color_id is None:
        color_id = get_event_color(title, description)

    # Parse the requested datetime
    start_datetime = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H:%M')
    kl_tz = zoneinfo.ZoneInfo(TIME_ZONE)
    start_datetime = start_datetime.replace(tzinfo=kl_tz)
    
    # Check for duplicate events (including recurring ones)
    try:
        # For anniversary/birthday events, check for any existing recurring events with similar title
        if 'anniversary' in title.lower() or 'birthday' in title.lower():
            # Search for events without date restriction to find recurring ones
            search_query = title.split()[0]  # First word of title
            events_result = service.events().list(
                calendarId='primary',
                q=search_query,
                singleEvents=False  # Include recurring events (no orderBy allowed with singleEvents=false)
            ).execute()
        else:
            # For regular events, check only on the specific date
            start_of_day = datetime.combine(start_datetime.date(), datetime.min.time()).replace(tzinfo=kl_tz)
            end_of_day = datetime.combine(start_datetime.date(), datetime.max.time()).replace(tzinfo=kl_tz)
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_of_day.isoformat(),
                timeMax=end_of_day.isoformat(),
                q=title.split()[0],  # Search by first word of title
                singleEvents=True,
                orderBy='startTime'
            ).execute()
        
        existing_events = events_result.get('items', [])
        
        # Check if an event with similar title already exists
        title_lower = title.lower()
        for event in existing_events:
            event_title = event.get('summary', '').lower()
            # Check for exact match or very similar titles
            if (event_title == title_lower or 
                (len(title_lower) > 5 and title_lower in event_title) or 
                (len(event_title) > 5 and event_title in title_lower)):
                logger.info(f"Found existing calendar event: {event.get('summary')}")
                
                # Check if it's a recurring event
                if event.get('recurrence'):
                    return event.get('htmlLink'), f"You already have a recurring '{event.get('summary')}' event!"
                else:
                    event_start = event['start'].get('dateTime', event['start'].get('date'))
                    if 'T' in event_start:
                        event_time = datetime.fromisoformat(event_start.replace('Z', '+00:00')).strftime('%I:%M %p')
                    else:
                        event_time = "all day"
                    
                    return event.get('htmlLink'), f"You already have '{event.get('summary')}' scheduled for {event_time} on this date!"
                
    except Exception as e:
        logger.warning(f"Error checking for duplicate events: {e}")
        # Continue with event creation if duplicate check fails
    
    # Check if requested time is in the past
    current_time = datetime.now(kl_tz)
    original_date = start_datetime.date()
    days_to_add = 0
    
    # If time is in the past, move to next day
    if start_datetime <= current_time:
        days_to_add = 1
        start_datetime = start_datetime + timedelta(days=days_to_add)
    
    end_datetime = start_datetime + timedelta(hours=duration)

    # Create the event
    event = {
        'summary': title,
        'description': description,
        'start': {
            'dateTime': start_datetime.isoformat(),
            'timeZone': TIME_ZONE
        },
        'end': {
            'dateTime': end_datetime.isoformat(),
            'timeZone': TIME_ZONE
        },
        'colorId': color_id,  # Google Calendar API expects colorId as an integer
    }
    
    # Add yearly recurrence for anniversary/birthday events
    if 'anniversary' in title.lower() or 'birthday' in title.lower():
        event['recurrence'] = [
            'RRULE:FREQ=YEARLY'
        ]
    
    try:
        result = service.events().insert(calendarId='primary', body=event).execute()
        logger.info(f"Created calendar event: {title}")
        
        # Schedule WhatsApp reminders for the event
        try:
            from utils.reminder import ReminderManager
            if not ReminderManager.schedule_meeting_reminders(
                event_id=result['id'],
                title=title,
                start_time=start_datetime
            ):
                logger.warning(f"Failed to schedule reminders for event: {title}")
        except Exception as e:
            logger.error(f"Failed to schedule reminders: {str(e)}")
            # Continue to return the calendar link even if reminder scheduling fails
            
        # Prepare response message
        message = f"I've scheduled \"{title}\" for {start_datetime.strftime('%I:%M %p')}"
        if start_datetime.date() != original_date:
            message += f" tomorrow" if days_to_add == 1 else f" on {start_datetime.strftime('%A, %B %d')}"
        message += "!"
        
        return result.get("htmlLink"), message
    except Exception as e:
        logger.error(f"Failed to create calendar event: {str(e)}")
        raise Exception(f"Failed to create calendar event: {str(e)}")

def get_schedule_for_date_range(start_date: datetime, end_date: datetime) -> List[Dict]:
    """Get schedule for a date range."""
    service = get_calendar_service()
    if not service:
        logger.error("Failed to get calendar service during schedule fetch")
        return []
    
    # Get the start and end of the date range
    start = datetime.combine(start_date.date(), datetime.min.time())
    end = datetime.combine(end_date.date(), datetime.max.time())
    
    try:
        result = service.events().list(
            calendarId='primary',
            timeMin=start.isoformat() + 'Z',
            timeMax=end.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        logger.info(f"Retrieved {len(result.get('items', []))} events for date range")
    except Exception as e:
        logger.error(f"Failed to fetch calendar events: {str(e)}")
        return []
    
    # Filter events to ensure they fall within the specified date range and haven't ended
    filtered_items = []
    current_time = datetime.now().astimezone()  # Get current time in local timezone
    
    # Track parsing errors for logging
    parsing_errors = 0
    
    for item in result.get('items', []):
        event_start = item['start'].get('dateTime', item['start'].get('date'))
        event_end = item['end'].get('dateTime', item['end'].get('date'))
        
        try:
            event_start_dt = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
            event_end_dt = datetime.fromisoformat(event_end.replace('Z', '+00:00'))
            
            # Convert to local timezone
            event_start_dt = event_start_dt.astimezone()
            event_end_dt = event_end_dt.astimezone()
            
            # Only include events that:
            # 1. Start on the specified date(s)
            # 2. Haven't ended yet (end time is in the future)
            if (start_date.date() <= event_start_dt.date() <= end_date.date() and
                event_end_dt > current_time):
                filtered_items.append(item)
                
        except (ValueError, TypeError) as e:
            parsing_errors += 1
            logger.error(f"Error parsing dates for event {item.get('id', 'unknown')}: {str(e)}")
            continue  # Skip events with invalid dates
    
    if parsing_errors > 0:
        logger.warning(f"Skipped {parsing_errors} events due to date parsing errors")
    
    logger.info(f"Filtered to {len(filtered_items)} relevant events")
    
    return filtered_items

def get_schedule_for_date(target_date: datetime) -> List[Dict]:
    """Get schedule for a specific date."""
    return get_schedule_for_date_range(target_date, target_date)

def get_this_week_schedule() -> List[Dict]:
    """Get schedule for this week."""
    now = datetime.now()
    # Get the start of this week (Monday)
    start = now - timedelta(days=now.weekday())
    # Get the end of this week (Sunday)
    end = start + timedelta(days=6)
    return get_schedule_for_date_range(start, end)

def get_next_week_schedule() -> List[Dict]:
    """Get schedule for next week."""
    now = datetime.now()
    # Get the start of next week (next Monday)
    start = now - timedelta(days=now.weekday()) + timedelta(weeks=1)
    # Get the end of next week (next Sunday)
    end = start + timedelta(days=6)
    return get_schedule_for_date_range(start, end)

def get_todays_schedule() -> List[Dict]:
    """Get all scheduled items for today."""
    return get_schedule_for_date(datetime.now())

def get_tomorrows_schedule() -> List[Dict]:
    """Get all scheduled items for tomorrow."""
    tomorrow = datetime.now() + timedelta(days=1)
    return get_schedule_for_date(tomorrow)

def cancel_specific_meeting(event_id: str) -> bool:
    """
    Cancel a specific meeting by its event ID.
    
    Args:
        event_id (str): The Google Calendar event ID
        
    Returns:
        bool: True if successfully cancelled, False otherwise
    """
    try:
        service = get_calendar_service()
        if not service:
            logger.error("Failed to get calendar service for cancellation")
            return False
        
        # Delete the event from Google Calendar
        service.events().delete(
            calendarId='primary',
            eventId=event_id
        ).execute()
        
        try:
            # Delete the associated reminder from Redis
            from utils.redis_utils import delete_reminder
            delete_reminder(event_id)
            logger.info(f"Successfully cancelled event {event_id}")
        except Exception as e:
            # Log but don't fail if reminder deletion fails
            logger.error(f"Failed to delete reminder for event {event_id}: {str(e)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error cancelling meeting: {str(e)}")
        return False

def get_upcoming_events(include_all_day: bool = False, include_recurring: bool = False) -> List[Dict]:
    """
    Get all upcoming events sorted by start time.
    Returns a list of event dictionaries.
    """
    service = get_calendar_service()
    if not service:
        raise Exception("No valid credentials")
    
    # Get current time
    now = datetime.now().astimezone()
    # Set end time to 30 days from now to limit range
    end = now + timedelta(days=30)
    
    # Get events from now onwards
    events_result = service.events().list(
        calendarId='primary',
        timeMin=now.isoformat(),
        timeMax=end.isoformat(),
        orderBy='startTime',
        singleEvents=True,  # Expand recurring events
        maxResults=5  # Limit to 5 upcoming events
    ).execute()
    
    # Filter events
    filtered_events = []
    for event in events_result.get('items', []):
        try:
            # Skip cancelled events
            if event.get('status') == 'cancelled':
                continue
                
            # Check if it's an all-day event
            is_all_day = 'date' in event.get('start', {})
            if is_all_day and not include_all_day:
                continue
            
            # Get event times
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            # Convert to datetime objects
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone()
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00')).astimezone()
            
            # Only include events that haven't ended
            if end_dt > now:
                filtered_events.append(event)
                
        except Exception as e:
            print(f"Error processing event: {e}")
    
    return filtered_events[:5]  # Ensure we return at most 5 events

def format_events_for_cancellation(events: List[Dict]) -> str:
    """
    Format a list of events into a numbered list for cancellation selection.
    """
    if not events:
        return "You have no upcoming regular events to cancel.\nNote: All-day events like birthdays cannot be cancelled through this system."
    
    formatted_events = ["Select event to cancel:"]
    for i, event in enumerate(events, 1):
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone()
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00')).astimezone()
        
        # Format date differently if event is today
        if start_dt.date() == datetime.now().date():
            date_str = "Today"
        elif start_dt.date() == (datetime.now().date() + timedelta(days=1)):
            date_str = "Tomorrow"
        else:
            date_str = start_dt.strftime("%A, %B %d")
        
        event_str = f"{i}. {event.get('summary', 'Untitled event')} ({date_str} {start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')})"
        formatted_events.append(event_str)
    
    formatted_events.append("\nWhich event would you like to cancel?")
    return "\n".join(formatted_events)

def parse_cancel_command(message: str) -> Optional[int]:
    """
    Parse a cancellation command to extract the event index.
    Handles formats like "cancel meeting 3" or "cancel event 3"
    
    Args:
        message (str): The cancellation command message
        
    Returns:
        Optional[int]: The event index if valid command, None otherwise
    """
    try:
        # Convert message to lowercase for consistent matching
        message = message.lower().strip()
        
        # Match patterns like "cancel meeting X" or "cancel event X"
        if any(message.startswith(prefix) for prefix in ['cancel meeting', 'cancel event']):
            # Extract the number from the end of the message
            parts = message.split()
            if len(parts) >= 3 and parts[-1].isdigit():
                index = int(parts[-1])
                return index if index > 0 else None
                
        return None
        
    except Exception as e:
        print(f"Error parsing cancel command: {e}")
        return None


def cancel_event_by_index(index: int) -> Optional[str]:
    """
    Cancel an event by its index in the upcoming events list.
    Returns the cancelled event title if successful, None if failed.
    
    Args:
        index (int): The 1-based index of the event to cancel
        
    Returns:
        Optional[str]: The title of the cancelled event, or None if cancellation failed
    """
    try:
        events = get_upcoming_events()
        if not events or index < 1 or index > len(events):
            return None
        
        event = events[index - 1]  # Convert to 0-based index
        event_title = event.get('summary', 'Untitled event')
        
        if cancel_specific_meeting(event['id']):
            return event_title
        return None
    except Exception as e:
        print(f"Error cancelling event by index: {e}")
        return None

def cancel_last_meeting() -> Optional[str]:
    """
    Cancel the last created meeting.
    Returns the cancelled meeting title if successful, None if no meeting found.
    
    Note: This function is kept for backward compatibility.
    For better control, use cancel_event_by_index with event selection.
    """
    events = get_upcoming_events()
    if not events:
        return None
    
    last_event = events[0]  # First event is the next upcoming one
    event_title = last_event.get('summary', 'Untitled event')
    
    if cancel_specific_meeting(last_event['id']):
        return event_title
    return None

def format_time(start_time: str, end_time: str, all_day: bool = False) -> str:
    """Format time into friendly, conversational string."""
    if all_day:
        return "for the whole day"
    
    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    
    # Convert to local timezone
    start_dt = start_dt.astimezone()
    end_dt = end_dt.astimezone()
    
    if start_dt.date() == end_dt.date():
        return f"starting at {start_dt.strftime('%I:%M %p')} until {end_dt.strftime('%I:%M %p')}"
    return f"starting {start_dt.strftime('%B %d at %I:%M %p')} until {end_dt.strftime('%B %d at %I:%M %p')}"

def format_item_for_speech(item: Dict) -> str:
    """Format a calendar item into a friendly, conversational message."""
    start = item['start'].get('dateTime', item['start'].get('date'))
    end = item['end'].get('dateTime', item['end'].get('date'))
    is_all_day = 'date' in item['start']
    
    time_str = format_time(start, end, is_all_day)
    title = item.get('summary', 'something untitled')
    location = f" at {item['location']}" if 'location' in item else ""
    
    return f"You have {title}{location} {time_str}"

def format_schedule_response(items: List[Dict], target_date: Optional[datetime] = None, show_both_days: bool = False, show_weekly: bool = False) -> str:
    """Format schedule items into a friendly, conversational message."""
    # Filter out past events
    current_time = datetime.now().astimezone()
    active_items = []
    for item in items:
        end = item['end'].get('dateTime', item['end'].get('date'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00')).astimezone()
        if end_dt > current_time:
            active_items.append(item)
    
    if show_weekly:
        # Group items by date
        schedule_by_date = {}
        for item in active_items:
            start = item['start'].get('dateTime', item['start'].get('date'))
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            date_key = start_dt.date()
            if date_key not in schedule_by_date:
                schedule_by_date[date_key] = []
            schedule_by_date[date_key].append(item)
        
        # Format each day's schedule
        messages = []
        for date in sorted(schedule_by_date.keys()):
            day_items = schedule_by_date[date]
            day_str = date.strftime("%A, %B %d")
            if day_items:
                formatted_items = [format_item_for_speech(item) for item in day_items]
                messages.append(f"On {day_str}, " + ". Then, ".join(formatted_items))
        
        if not messages:
            week_type = "this week" if target_date and target_date.date() <= datetime.now().date() + timedelta(days=7) else "next week"
            return f"You've no meeting for {week_type}."
        
        return '. '.join(messages)
    
    if show_both_days:
        # Get both today's and tomorrow's schedules
        today_items = get_todays_schedule()
        tomorrow_items = get_tomorrows_schedule()
        
        # Filter today's items
        current_time = datetime.now().astimezone()
        active_today_items = []
        for item in today_items:
            end = item['end'].get('dateTime', item['end'].get('date'))
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00')).astimezone()
            if end_dt > current_time:
                active_today_items.append(item)
        
        today_msg = ""
        if not active_today_items:
            today_msg = "You've no active meetings for today"
        else:
            formatted_items = [format_item_for_speech(item) for item in active_today_items]
            today_msg = "Today: " + ". Then, ".join(formatted_items)
        
        tomorrow_msg = ""
        if not tomorrow_items:
            tomorrow_msg = "You've no meetings for tomorrow"
        else:
            formatted_items = [format_item_for_speech(item) for item in tomorrow_items]
            tomorrow_msg = "Tomorrow: " + ". Then, ".join(formatted_items)
        
        return f"{today_msg}. {tomorrow_msg}"
    
    # Single day response
    date_str = "today"
    if target_date:
        if target_date.date() == datetime.now().date():
            date_str = "today"
        elif target_date.date() == (datetime.now() + timedelta(days=1)).date():
            date_str = "tomorrow"
        else:
            date_str = target_date.strftime("on %A, %B %d")
    
    if not active_items:
        return f"You've no active meetings for {date_str}."
    
    if len(active_items) == 1:
        return f"Your schedule {date_str}: " + format_item_for_speech(active_items[0])
    
    formatted_items = [format_item_for_speech(item) for item in active_items]
    items_text = ". Then, ".join(formatted_items)
    
    return f"Your schedule {date_str}: {items_text}"
