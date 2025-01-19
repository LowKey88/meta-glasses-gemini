import os
import json
import base64
from google_auth_oauthlib.flow import InstalledAppFlow
from fastapi import HTTPException

class GoogleAuth:
    _instance = None
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/tasks'
    ]

    def __init__(self):
        if not GoogleAuth._instance:
            self.app_url = os.getenv('APP_URL')
            self.api_secret = os.getenv('API_SECRET_KEY')
            GoogleAuth._instance = self

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = GoogleAuth()
        return cls._instance

    def verify_api_key(self, x_api_key: str):
        if not x_api_key or x_api_key != self.api_secret:
            raise HTTPException(status_code=403, detail="Unauthorized")

    def initialize_oauth_flow(self):
        credentials_data_base64 = os.getenv('OAUTH_CREDENTIALS_ENCODED')
        credentials_data = base64.b64decode(credentials_data_base64).decode('utf-8')
        
        os.makedirs('creds', exist_ok=True)
        with open('creds/credentials.json', 'w') as f:
            f.write(credentials_data)
            
        flow = InstalledAppFlow.from_client_secrets_file(
            'creds/credentials.json',
            self.SCOPES,
            redirect_uri=f'{self.app_url}/auth/callback'
        )
        return flow

    async def get_auth_url(self, x_api_key: str):
        self.verify_api_key(x_api_key)
        flow = self.initialize_oauth_flow()
        auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')
        return {"auth_url": auth_url}

    async def handle_callback(self, code: str, state: str, x_api_key: str):
        self.verify_api_key(x_api_key)
        flow = self.initialize_oauth_flow()
        flow.fetch_token(code=code)
        
        token_data = {
            'token': flow.credentials.token,
            'refresh_token': flow.credentials.refresh_token,
            'token_uri': flow.credentials.token_uri,
            'client_id': flow.credentials.client_id,
            'client_secret': flow.credentials.client_secret,
            'scopes': flow.credentials.scopes,
            'expiry': flow.credentials.expiry.isoformat()
        }
        
        with open('creds/token.json', 'w') as f:
            json.dump(token_data, f)
            
        return {"message": "Authentication successful!"}