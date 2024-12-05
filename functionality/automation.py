import os

import requests

headers = {
    'Authorization': f'Bearer {os.getenv("HOME_ASSISTANT_TOKEN")}',
    'Content-Type': 'application/json',
}


def automation_command(text: str):
    json_data = {
        "text": text,
        "agent_id": "conversation.home_assistant"
    }
    url = f'{os.getenv("HOME_ASSISTANT_URL")}/api/conversation/process'
    response = requests.post(url, headers=headers, json=json_data)
    res = response.json().get('response').get('speech').get('plain').get('speech')
    print('Querying to Home Asssistant:', response.json())
    return res