import base64
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


# TODO: handle reminders using google-reminders-cli
# https://github.com/jonahar/google-reminders-cli/tree/master
SCOPES = ['https://www.googleapis.com/auth/calendar']
creds = None
if os.path.exists('creds/token.json'):
    creds = Credentials.from_authorized_user_file('creds/token.json', SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        credentials_data_base64 = os.getenv('OAUTH_CREDENTIALS_ENCODED')  # base64 encoded credentials.json
        credentials_data = base64.b64decode(credentials_data_base64).decode('utf-8')
        with open('creds/credentials.json', 'w') as credentials:
            credentials.write(credentials_data)

        flow = InstalledAppFlow.from_client_secrets_file(
            'creds/credentials.json', SCOPES)
        # creds = flow.run_local_server(port=0)
        creds = flow.run_local_server(open_browser=False, bind_addr="0.0.0.0", port=0)
    with open('creds/token.json', 'w') as token:
        token.write(creds.to_json())