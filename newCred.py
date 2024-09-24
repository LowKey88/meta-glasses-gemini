import base64
import os
import json
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
        try:
            creds.refresh(Request())
        except:
            print('Token expired! Delete it!')
    else:
        credentials_data_base64 = os.getenv('OAUTH_CREDENTIALS_ENCODED')  # base64 encoded credentials.json
        credentials_data = base64.b64decode(credentials_data_base64).decode('utf-8')
        with open('creds/credentials.json', 'w') as credentials:
            credentials.write(credentials_data)

        flow = InstalledAppFlow.from_client_secrets_file(
            'creds/credentials.json', SCOPES, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
        # creds = flow.run_local_server(port=0)
        auth_url, _ = flow.authorization_url(prompt='consent')
        print('Please go to this URL: {}'.format(auth_url))
        code = input('Enter the authorization code: ')        
        creds = flow.fetch_token(code=code)
        
        
        # creds = flow.run_local_server(open_browser=False, bind_addr="0.0.0.0", port=0)
    with open('creds/token.json', 'w') as token:
        json.dump(creds, token)