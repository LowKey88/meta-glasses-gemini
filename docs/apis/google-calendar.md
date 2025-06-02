# Google Calendar Integration

## Overview
The Google Calendar integration provides bi-directional synchronization of events, with smart time validation and timezone-aware operations centered on Asia/Kuala_Lumpur.

## Prerequisites
- Google Cloud Project
- OAuth 2.0 Configuration
- Calendar API Enabled
- HTTPS Endpoints

## Configuration
```python
# Environment Variables
GOOGLE_CLIENT_ID=      # OAuth Client ID
GOOGLE_CLIENT_SECRET=  # OAuth Client Secret
GOOGLE_REFRESH_TOKEN=  # OAuth Refresh Token
CALENDAR_ID=          # Primary Calendar ID
```

## Calendar Operations

### 1. Event Creation
```python
async def create_event(event_data: dict):
    # Smart time validation
    event_time = parse_time(event_data['time'])
    if event_time < current_time:
        event_time = schedule_for_next_day(event_time)
    
    # Create event with timezone
    event = {
        'summary': event_data['title'],
        'start': {
            'dateTime': event_time.isoformat(),
            'timeZone': 'Asia/Kuala_Lumpur',
        },
        'end': {
            'dateTime': (event_time + duration).isoformat(),
            'timeZone': 'Asia/Kuala_Lumpur',
        },
    }
    
    return await calendar_service.events().insert(
        calendarId=CALENDAR_ID,
        body=event
    ).execute()
```

### 2. Event Cancellation
```python
async def cancel_event(event_index: int):
    # Get recent events
    events = await get_upcoming_events()
    
    # Cancel by index
    if 0 <= event_index < len(events):
        event_id = events[event_index]['id']
        await calendar_service.events().delete(
            calendarId=CALENDAR_ID,
            eventId=event_id
        ).execute()
        return True
    return False
```

### 3. Event Synchronization
```python
async def sync_calendar():
    # Get events from last 7 days
    time_min = (datetime.now() - timedelta(days=7)).isoformat() + 'Z'
    
    # Sync with Redis cache
    events = await calendar_service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=time_min,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    await cache_events(events['items'])
```

## Time Management

### 1. Timezone Handling
```python
from zoneinfo import ZoneInfo

KL_TIMEZONE = ZoneInfo('Asia/Kuala_Lumpur')

def get_local_time():
    return datetime.now(KL_TIMEZONE)

def is_future_time(time: datetime):
    return time > get_local_time()
```

### 2. Smart Validation
```python
def validate_event_time(time: datetime):
    if not is_future_time(time):
        # Reschedule for next day
        tomorrow = get_local_time() + timedelta(days=1)
        return datetime.combine(
            tomorrow.date(),
            time.time(),
            KL_TIMEZONE
        )
    return time
```

## Redis Integration

### 1. Event Caching
```python
async def cache_events(events: list):
    pipeline = redis.pipeline()
    
    for event in events:
        key = f"calendar:event:{event['id']}"
        pipeline.setex(
            key,
            timedelta(days=7),
            json.dumps(event)
        )
    
    await pipeline.execute()
```

### 2. Reminder System
```python
async def set_reminder(event_id: str, time: datetime):
    key = f"calendar:reminder:{event_id}"
    
    # Set reminder with 1-hour post-event expiry
    await redis.setex(
        key,
        timedelta(hours=event_duration + 1),
        json.dumps({
            'event_id': event_id,
            'time': time.isoformat()
        })
    )
```

## Synchronization Worker

### 1. Periodic Sync
```python
async def start_sync_worker():
    while True:
        try:
            await sync_calendar()
            await asyncio.sleep(300)  # 5-minute intervals
        except Exception as e:
            log_error("Calendar sync failed", e)
            await asyncio.sleep(60)  # Retry after 1 minute
```

### 2. Error Recovery
```python
async def recover_sync_state():
    # Clear stale cache
    await redis.delete_pattern("calendar:*")
    
    # Full sync
    await sync_calendar()
    
    # Verify sync
    await verify_calendar_state()
```

## Error Handling

### 1. API Errors
```python
class CalendarError(Exception):
    def __init__(self, message: str, code: int):
        self.message = message
        self.code = code

# Common errors
AUTH_ERROR = CalendarError("Authentication failed", 401)
QUOTA_ERROR = CalendarError("Quota exceeded", 429)
SYNC_ERROR = CalendarError("Sync failed", 500)
```

### 2. Recovery Strategies
- Exponential backoff for API errors
- Cache fallback for read operations
- Manual sync trigger option
- User notification for critical errors

## Performance Optimization

### 1. Caching Strategy
- 7-day event cache window
- TTL-based cleanup
- Batch operations for sync
- Memory usage limits

### 2. API Usage
- Request batching
- Rate limit monitoring
- Connection pooling
- Retry management

## Monitoring

### 1. Metrics
- Sync success rate
- API response times
- Cache hit ratio
- Error frequency

### 2. Health Checks
- API availability
- Cache connectivity
- Sync worker status
- Event consistency

## Testing

### 1. Test Cases
```python
async def test_calendar_operations():
    # Test event creation
    event = await create_test_event()
    assert event['status'] == 'confirmed'
    
    # Test cancellation
    success = await cancel_event(0)
    assert success is True
    
    # Test sync
    await sync_calendar()
    cached = await get_cached_events()
    assert len(cached) > 0
```

### 2. Integration Tests
- Time validation
- Timezone handling
- Sync consistency
- Error scenarios
- Performance benchmarks
