from googleapiclient.discovery_cache.base import Cache
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import os
import warnings

# Disable oauth2client cache warning
warnings.filterwarnings('ignore', message='file_cache is unavailable when using oauth2client >= 4.0.0')

class MemoryCache(Cache):
    _CACHE = {}

    def get(self, url):
        return MemoryCache._CACHE.get(url)

    def set(self, url, content):
        MemoryCache._CACHE[url] = content

def get_calendar_service():
    """Get authenticated Google Calendar service."""
    if not os.path.exists('creds/token.json'):
        return None
    creds = Credentials.from_authorized_user_file('creds/token.json', ['https://www.googleapis.com/auth/calendar'])
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            return None
    return build('calendar', 'v3', credentials=creds, cache=MemoryCache())