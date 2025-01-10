import base64
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Calendar colorId
# 0 green default
# 1 purple
# 2 green teal
# 3 pink
# 4 red
# 5 yellow

SCOPES = ['https://www.googleapis.com/auth/calendar']
TIME_ZONE = 'Asia/Kuala_Lumpur'

def get_credentials():
    """Get and refresh Google Calendar credentials."""
    creds = None
    if os.path.exists('creds/token.json'):
        creds = Credentials.from_authorized_user_file('creds/token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    return creds

def create_google_calendar_event(title: str, description: str, date: str, time: str, duration: int = 1, color_id: int = 0) -> str:
    """Create a new Google Calendar event."""
    creds = get_credentials()
    if not creds:
        raise Exception("No valid credentials")

    service = build('calendar', 'v3', credentials=creds)
    start_datetime = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H:%M')
    end_datetime = start_datetime + timedelta(hours=duration)

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
        'colorId': str(color_id),
    }
    result = service.events().insert(calendarId='primary', body=event).execute()
    return result.get("htmlLink")

def get_schedule_for_date_range(start_date: datetime, end_date: datetime) -> List[Dict]:
    """Get schedule for a date range."""
    creds = get_credentials()
    if not creds:
        raise Exception("No valid credentials")

    service = build('calendar', 'v3', credentials=creds)
    
    # Get the start and end of the date range
    start = datetime.combine(start_date.date(), datetime.min.time())
    end = datetime.combine(end_date.date(), datetime.max.time())
    
    result = service.events().list(
        calendarId='primary',
        timeMin=start.isoformat() + 'Z',
        timeMax=end.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    # Filter events to ensure they fall within the specified date range
    filtered_items = []
    for item in result.get('items', []):
        event_start = item['start'].get('dateTime', item['start'].get('date'))
        event_start_dt = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
        event_start_dt = event_start_dt.astimezone()  # Convert to local timezone
        
        # Only include events that start on the specified date(s)
        if start_date.date() <= event_start_dt.date() <= end_date.date():
            filtered_items.append(item)
    
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
    location = f" happening at {item['location']}" if 'location' in item else ""
    description = f". Just to remind you: {item['description']}" if 'description' in item else ""
    
    return f"you have {title}{location} {time_str}{description}"

def format_schedule_response(items: List[Dict], target_date: Optional[datetime] = None, show_both_days: bool = False, show_weekly: bool = False) -> str:
    """Format schedule items into a friendly, conversational message."""
    if show_weekly:
        # Group items by date
        schedule_by_date = {}
        for item in items:
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
            return f"You have no meetings scheduled for {week_type}."
        
        intro = "Here's your schedule:"
        return f"{intro} {'. '.join(messages)}"
    
    if show_both_days:
        # Get both today's and tomorrow's schedules
        today_items = get_todays_schedule()
        tomorrow_items = get_tomorrows_schedule()
        
        today_msg = ""
        if not today_items:
            today_msg = "You have no meetings scheduled today"
        else:
            formatted_items = [format_item_for_speech(item) for item in today_items]
            today_msg = "Today " + ". Then, ".join(formatted_items)
        
        tomorrow_msg = ""
        if not tomorrow_items:
            tomorrow_msg = "You have no meetings scheduled tomorrow"
        else:
            formatted_items = [format_item_for_speech(item) for item in tomorrow_items]
            tomorrow_msg = "Tomorrow " + ". Then, ".join(formatted_items)
        
        return f"Let me tell you about your schedule. {today_msg}. {tomorrow_msg}."
    
    # Single day response
    date_str = "today"
    if target_date:
        if target_date.date() == datetime.now().date():
            date_str = "today"
        elif target_date.date() == (datetime.now() + timedelta(days=1)).date():
            date_str = "tomorrow"
        else:
            date_str = target_date.strftime("on %A, %B %d")
    
    if not items:
        return f"You have no meetings scheduled {date_str}."
    
    if len(items) == 1:
        return f"Let me tell you about your schedule {date_str}. " + format_item_for_speech(items[0])
    
    formatted_items = [format_item_for_speech(item) for item in items]
    items_text = ". Then, ".join(formatted_items)
    
    return f"Let me walk you through your schedule {date_str}. {items_text}"
