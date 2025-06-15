import os
import requests
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Use uvicorn logger
logger = logging.getLogger("uvicorn")

WHATSAPP_API_VERSION = "v21.0"
GRAPH_API_BASE = "https://graph.facebook.com"

headers = {
   'Authorization': f'Bearer {os.getenv("WHATSAPP_AUTH_TOKEN")}',
   'Content-Type': 'application/json',
}

# Conversation window tracking
CONVERSATION_WINDOW_HOURS = 24
_last_user_message_time = None

def get_whatsapp_url():
   phone_id = os.getenv('WHATSAPP_PHONE_ID')
   if not phone_id:
       logger.error("❌ WHATSAPP_PHONE_ID environment variable is not set!")
       logger.error("💡 Get your Phone Number ID from WhatsApp Business Manager → API Setup")
       logger.error("💡 It's different from your phone number - it's a long ID like 1234567890123456")
       raise ValueError("WHATSAPP_PHONE_ID is required but not set")
   return f"{GRAPH_API_BASE}/{WHATSAPP_API_VERSION}/{phone_id}/messages"

def update_conversation_window():
   """Update the last user message time to current time."""
   global _last_user_message_time
   _last_user_message_time = datetime.now()
   logger.info(f"Conversation window updated: {_last_user_message_time}")

def get_template_config(template_name: str) -> dict:
    """Get template configuration from settings, fallback to hardcoded defaults"""
    try:
        from utils.redis_utils import r
        from utils.encryption import secure_retrieve
        
        # Try to get from Redis settings first
        setting_key = f"whatsapp_template_{template_name}"
        redis_key = f"meta-glasses:settings:global:{setting_key}"
        
        redis_value = r.get(redis_key)
        if redis_value:
            encrypted_value = redis_value.decode('utf-8')
            config_str = secure_retrieve(encrypted_value)
            if config_str:
                config = json.loads(config_str)
                # Extract template_config if it exists
                if isinstance(config, dict) and 'template_config' in config:
                    return config['template_config']
                return config
    except Exception as e:
        logger.warning(f"Failed to get template config from settings for {template_name}: {e}")
    
    # Fallback to hardcoded configurations
    return get_default_template_config(template_name)

def get_default_template_config(template_name: str) -> dict:
    """Get default hardcoded template configuration"""
    default_configs = {
        "ha_notification": {
            "enabled": True,
            "template_name": "ha_notification",
            "variables": [
                {"position": 0, "parameter_name": "ha_message", "description": "Home Assistant message"}
            ]
        },
        "meeting_reminder": {
            "enabled": True,
            "template_name": "meeting_reminder", 
            "variables": [
                {"position": 0, "parameter_name": "meeting_title", "description": "Meeting name"},
                {"position": 1, "parameter_name": "meeting_time", "description": "Meeting time"}
            ]
        },
        "meeting_start": {
            "enabled": True,
            "template_name": "meeting_start",
            "variables": [
                {"position": 0, "parameter_name": "meeting_title", "description": "Meeting name"}
            ]
        },
        "daily_schedule": {
            "enabled": True,
            "template_name": "daily_schedule",
            "variables": [
                {"position": 0, "parameter_name": "schedule_details", "description": "Schedule information"}
            ]
        }
    }
    
    return default_configs.get(template_name, {
        "enabled": False,
        "template_name": template_name,
        "variables": []
    })

def is_within_conversation_window() -> bool:
   """Check if we're within the 24-hour conversation window."""
   if _last_user_message_time is None:
       logger.info("No previous user message recorded - outside conversation window")
       return False
   
   time_since_last_message = datetime.now() - _last_user_message_time
   is_within = time_since_last_message < timedelta(hours=CONVERSATION_WINDOW_HOURS)
   
   logger.info(f"Time since last user message: {time_since_last_message}, within window: {is_within}")
   return is_within

def send_whatsapp_template(template_name: str, parameters: Optional[Dict[str, Any]] = None):
   """Send a WhatsApp message template (for use outside 24-hour window)."""
   logger.info(f"Sending WhatsApp template: {template_name} with parameters: {parameters}")
   
   # Get template configuration from settings
   config = get_template_config(template_name)
   
   # Check if template is enabled
   if not config.get("enabled", False):
       logger.warning(f"Template {template_name} is disabled")
       return False
   
   template_data = {
       "name": template_name,
       "language": {"code": "en"}
   }
   
   # Build template components dynamically from configuration
   variables = config.get("variables", [])
   if variables and parameters and 'body' in parameters:
       # Sort variables by position
       sorted_variables = sorted(variables, key=lambda x: x.get("position", 0))
       
       # Build parameters array
       body_params = []
       for i, variable in enumerate(sorted_variables):
           if i < len(parameters['body']):
               param_name = variable.get("parameter_name", f"param_{i}")
               body_params.append({
                   "type": "text",
                   "parameter_name": param_name,
                   "text": str(parameters['body'][i])
               })
           else:
               # Not enough parameters provided
               logger.warning(f"Not enough parameters for template {template_name}. Expected {len(sorted_variables)}, got {len(parameters['body'])}")
               break
       
       if body_params:
           template_data["components"] = [
               {
                   "type": "body",
                   "parameters": body_params
               }
           ]
   else:
       # No variables or no parameters - send template without parameters
       logger.info(f"🧪 Testing {template_name} template without parameters")
   
   json_data = {
       'messaging_product': 'whatsapp',
       'to': os.getenv('WHATSAPP_PHONE_NUMBER'),
       'type': 'template',
       'template': template_data
   }
   
   # Debug logging
   logger.info(f"Template JSON being sent: {json_data}")
   
   try:
       response = requests.post(get_whatsapp_url(), headers=headers, json=json_data)
       response_data = response.json()
       
       if response.status_code == 401 or (response_data.get('error', {}).get('code') == 190):
           logger.error(f"WhatsApp token expired or invalid: {response_data}")
           return False
       
       if response.status_code != 200:
           logger.error(f"Template message failed: {response_data}")
           # Check for specific error types
           error_message = response_data.get('error', {}).get('message', '')
           error_code = response_data.get('error', {}).get('code', 0)
           
           if 'Invalid parameter' in error_message:
               logger.error("❌ Template issue: Either template not approved yet or parameter structure incorrect")
               logger.error("💡 Check WhatsApp Business Manager: Templates must be 'APPROVED' status")
           elif error_code == 131000:
               logger.error("❌ Template not found or not approved")
           
           return False
           
       logger.info(f"Template message sent successfully: {response_data}")
       return True
       
   except Exception as e:
       logger.error(f"Failed to send WhatsApp template: {e}")
       return False

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

def send_smart_whatsapp_message(text: str, template_fallback: str = "ha_notification", template_params: Optional[Dict[str, Any]] = None) -> bool:
   """
   Smart WhatsApp message sender that automatically chooses between regular messages and templates.
   
   Args:
       text: The message text to send
       template_fallback: Template name to use if outside conversation window
       template_params: Parameters for the template
       
   Returns:
       bool: True if message sent successfully, False otherwise
   """
   if is_within_conversation_window():
       logger.info("Within conversation window - sending regular message")
       try:
           send_whatsapp_message(text)
           return True
       except Exception as e:
           logger.error(f"Regular message failed: {e}")
           return False
   else:
       logger.info("Outside conversation window - using template message")
       # If no template params provided, use the correct variable name for ha_notification template
       if not template_params:
           if template_fallback == "ha_notification":
               template_params = {"body": [text]}
           else:
               template_params = {"body": [text]}
       return send_whatsapp_template(template_fallback, template_params)

def send_whatsapp_threaded(message: str):
   send_whatsapp_message(message)