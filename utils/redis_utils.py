import os
import json
import base64
import redis
import zoneinfo
from datetime import datetime, timedelta, timezone
from .redis_key_builder import redis_keys

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


# ------------ Generic Caching ------------
@try_catch_decorator
def get_generic_cache(path: str):
    key = redis_keys.get_generic_cache_key(path)
    data = r.get(key)
    return json.loads(data) if data else None


@try_catch_decorator
def set_generic_cache(path: str, data: dict, ttl: int = 3600):  # Default 1 hour TTL
    key = redis_keys.get_generic_cache_key(path)
    r.set(key, json.dumps(data, default=str))
    r.expire(key, ttl)


@try_catch_decorator
def delete_generic_cache(path: str):
    key = redis_keys.get_generic_cache_key(path)
    r.delete(key)

# ------------ Reminder Management ------------
@try_catch_decorator
def get_reminder_keys():
    """Get all reminder keys."""
    pattern = redis_keys.get_all_reminder_keys_pattern()
    return r.keys(pattern)

@try_catch_decorator
def delete_reminder(event_id: str):
    """Delete a reminder by event ID."""
    key = redis_keys.get_reminder_event_key(event_id)
    r.delete(key)

@try_catch_decorator
def cleanup_expired_reminders():
    """Clean up expired reminders and old data."""
    pattern = redis_keys.get_all_reminder_keys_pattern()
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
    key = redis_keys.get_cancellation_state_key(user_id, "wa")
    r.set(key, 'active')
    r.expire(key, 30)  # 30 second timeout

@try_catch_decorator
def get_cancellation_state(user_id: str) -> bool:
    """Check if user is in cancellation state."""
    key = redis_keys.get_cancellation_state_key(user_id, "wa")
    return bool(r.get(key))

@try_catch_decorator
def clear_cancellation_state(user_id: str):
    """Clear cancellation state."""
    key = redis_keys.get_cancellation_state_key(user_id, "wa")
    r.delete(key)

# Code to connect to Redis from local machine from GCP
# gcloud compute ssh redis-proxy --project=$project-id --zone us-central1-a -- -N -L 6379:$redis-private-ip:6379