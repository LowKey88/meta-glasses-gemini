import os
import json
import base64
import redis
import zoneinfo
from datetime import datetime, timedelta, timezone

r = redis.Redis(
    host=os.getenv('REDIS_DB_HOST', 'localhost'),
    port=int(os.getenv('REDIS_DB_PORT', '6378')),
    username='default',
    password=os.getenv('REDIS_DB_PASSWORD', ''),
    health_check_interval=30
)

TIME_ZONE = 'Asia/Kuala_Lumpur'


def try_catch_decorator(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f'Error calling {func.__name__}', e)
            return None

    return wrapper


# ------------ Place ID Caching ------------
@try_catch_decorator
def get_generic_cache(path: str):
    key = base64.b64encode(f'{path}'.encode('utf-8'))
    key = key.decode('utf-8')

    data = r.get(f'josancamon:rayban-meta-glasses-api:{key}')
    return json.loads(data) if data else None


@try_catch_decorator
def set_generic_cache(path: str, data: dict, ttl: int = 3600):  # Default 1 hour TTL
    key = base64.b64encode(f'{path}'.encode('utf-8'))
    key = key.decode('utf-8')

    r.set(f'josancamon:rayban-meta-glasses-api:{key}', json.dumps(data, default=str))
    r.expire(f'josancamon:rayban-meta-glasses-api:{key}', ttl)


@try_catch_decorator
def delete_generic_cache(path: str):
    key = base64.b64encode(f'{path}'.encode('utf-8'))
    key = key.decode('utf-8')
    r.delete(f'josancamon:rayban-meta-glasses-api:{key}')

# ------------ Reminder Management ------------
@try_catch_decorator
def get_reminder_keys():
    """Get all reminder keys."""
    return r.keys('josancamon:rayban-meta-glasses-api:reminder:*')

@try_catch_decorator
def delete_reminder(event_id: str):
    """Delete a reminder by event ID."""
    key = f'josancamon:rayban-meta-glasses-api:reminder:{event_id}'
    r.delete(key)

@try_catch_decorator
def cleanup_expired_reminders():
    """Clean up expired reminders and old data."""
    pattern = 'josancamon:rayban-meta-glasses-api:reminder:*'
    for key in r.scan_iter(pattern):
        try:
            data = r.get(key)
            if data:
                reminder_data = json.loads(data)
                start_time = reminder_data.get('start_time')
                if start_time:
                    # Delete reminder if event has ended
                    kl_tz = zoneinfo.ZoneInfo(TIME_ZONE)
                    event_time = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(kl_tz)
                    current_time = datetime.now(kl_tz)
                    if current_time > event_time:
                        r.delete(key)
        except Exception as e:
            print(f"Error cleaning up reminder {key}: {e}")
            # If we can't parse the data, it's probably corrupted - delete it
            r.delete(key)

# ------------ Calendar Event Cancellation State ------------
@try_catch_decorator
def set_cancellation_state(user_id: str):
    """Set cancellation state with 30-second expiry."""
    key = f'josancamon:rayban-meta-glasses-api:cancellation:wa:{user_id}'
    r.set(key, 'active')
    r.expire(key, 30)  # 30 second timeout

@try_catch_decorator
def get_cancellation_state(user_id: str) -> bool:
    """Check if user is in cancellation state."""
    key = f'josancamon:rayban-meta-glasses-api:cancellation:wa:{user_id}'
    return bool(r.get(key))

@try_catch_decorator
def clear_cancellation_state(user_id: str):
    """Clear cancellation state."""
    key = f'josancamon:rayban-meta-glasses-api:cancellation:wa:{user_id}'
    r.delete(key)

# Code to connect to Redis from local machine from GCP
# gcloud compute ssh redis-proxy --project=$project-id --zone us-central1-a -- -N -L 6379:$redis-private-ip:6379