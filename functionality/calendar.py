import base64
import os
from datetime import datetime, timedelta
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

def get_credentials():
   creds = None
   if os.path.exists('creds/token.json'):
       creds = Credentials.from_authorized_user_file('creds/token.json', SCOPES)
   if not creds or not creds.valid:
       if creds and creds.expired and creds.refresh_token:
           creds.refresh(Request())
   return creds

def create_google_calendar_event(title, description, date, time, duration=1, color_id=0 | 9):
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
           'timeZone': 'Asia/Kuala_Lumpur'
       },
       'end': {
           'dateTime': end_datetime.isoformat(),
           'timeZone': 'Asia/Kuala_Lumpur'
       },
       'colorId': color_id,
   }
   event = service.events().insert(calendarId='primary', body=event).execute()
   return event.get("htmlLink")

# create_google_calendar_event(
#     title="Project Review",
#     description="Discuss progress and next steps for Q2 launch",
#     date="2024-04-10",
#     time="14:00",
#     duration=1
# )

# TODO: be able to retrieve events
#   - Your next event
#   - Next "time" events about x thing
#   - Modify your next eent.