import os
import requests
import logging

# Use uvicorn logger
logger = logging.getLogger("uvicorn")

WHATSAPP_API_VERSION = "v21.0"
GRAPH_API_BASE = "https://graph.facebook.com"

headers = {
   'Authorization': f'Bearer {os.getenv("WHATSAPP_AUTH_TOKEN")}',
   'Content-Type': 'application/json',
}

def get_whatsapp_url():
   return f"{GRAPH_API_BASE}/{WHATSAPP_API_VERSION}/{os.getenv('WHATSAPP_PHONE_ID')}/messages"

def send_whatsapp_message(text: str):
    logger.info(f"send_whatsapp_message: {text}")
    json_data = {
        'messaging_product': 'whatsapp',
        'to': os.getenv('WHATSAPP_PHONE_NUMBER'),
        'type': 'text',
        'text': {'body': text}
    }
    try:
        response = requests.post(get_whatsapp_url(), headers=headers, json=json_data)
        response_data = response.json()
        
        # Check for authentication errors
        if response.status_code == 401 or (response_data.get('error', {}).get('code') == 190):
            logger.error(f"WhatsApp token expired or invalid: {response_data}")
            # Token has expired - log error details
            error_msg = response_data.get('error', {}).get('message', 'Token authentication failed')
            logger.error(f"Token error details: {error_msg}")
            return
            
        logger.info(f"send_whatsapp_message response: {response_data}")
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {e}")

def send_whatsapp_image(content):
    logger.info(f"send_whatsapp_image: sending image with content {content}")
    json_data = {
        'messaging_product': 'whatsapp',
        'to': os.getenv('WHATSAPP_PHONE_NUMBER'),
        'type': 'image',
        'image': {'link': content}
    }
    response = requests.post(get_whatsapp_url(), headers=headers, json=json_data)
    logger.info(f"send_whatsapp_image response: {response.json()}")

def download_file(file_data):
    logger.info(f"download_file: processing file data {file_data}")
    res = requests.get(f'{GRAPH_API_BASE}/{WHATSAPP_API_VERSION}/{file_data["id"]}/', headers=headers)
    logger.info(f"download_file metadata response: {res.json()}")
    url = res.json()['url']
    response = requests.get(url, headers=headers)
    if not os.path.exists('media/'):
        os.makedirs('media/')
        logger.info("Created media directory")

    file_format = 'ogg' if 'audio' in file_data['mime_type'] else 'jpg'
    if response.status_code == 200:
        with open(f'media/{file_data["id"]}.{file_format}', "wb") as f:
            f.write(response.content)
        logger.info(f"Media file successfully downloaded to media/{file_data['id']}.{file_format}")
        return f'media/{file_data["id"]}.{file_format}'
    else:
        logger.info(f"Download failed. Status code: {response.status_code}")

def send_whatsapp_threaded(message: str):
   send_whatsapp_message(message)