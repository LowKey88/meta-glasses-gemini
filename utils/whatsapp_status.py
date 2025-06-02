"""WhatsApp API status and token validation utilities"""
import os
import requests
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger("uvicorn")

def check_whatsapp_token_status() -> Dict[str, any]:
    """
    Check WhatsApp token status and get token information
    Returns dict with status, expiry, and other token details
    """
    try:
        # WhatsApp tokens are typically long-lived (60+ days)
        # We'll check the token by making a test API call
        token = os.getenv("WHATSAPP_AUTH_TOKEN")
        phone_id = os.getenv("WHATSAPP_PHONE_ID")
        
        if not token or not phone_id:
            return {
                "status": "error",
                "message": "Missing WhatsApp credentials",
                "is_valid": False,
                "token_present": bool(token),
                "phone_id_present": bool(phone_id)
            }
        
        # Make a test API call to check token validity
        # Using the /phone_numbers endpoint which doesn't send messages
        test_url = f"https://graph.facebook.com/v21.0/{phone_id}"
        headers = {
            'Authorization': f'Bearer {token}',
        }
        
        response = requests.get(test_url, headers=headers)
        
        if response.status_code == 200:
            # Token is valid
            # WhatsApp tokens don't return expiry info directly
            # They typically last 60 days from creation
            return {
                "status": "active",
                "is_valid": True,
                "message": "Token is valid and active",
                "api_version": "v21.0",
                "phone_id": phone_id,
                # WhatsApp tokens are typically valid for 60 days
                # We can't get exact expiry without storing creation date
                "token_type": "Long-lived token (60+ days typical validity)",
                "last_checked": datetime.now().isoformat()
            }
        elif response.status_code == 401:
            return {
                "status": "expired",
                "is_valid": False,
                "message": "Token is expired or invalid",
                "error": response.json().get('error', {}).get('message', 'Unknown error'),
                "last_checked": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "is_valid": False,
                "message": f"API returned status {response.status_code}",
                "error": response.text,
                "last_checked": datetime.now().isoformat()
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking WhatsApp token: {e}")
        return {
            "status": "error",
            "is_valid": False,
            "message": "Network error checking token",
            "error": str(e),
            "last_checked": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Unexpected error checking WhatsApp token: {e}")
        return {
            "status": "error",
            "is_valid": False,
            "message": "Unexpected error",
            "error": str(e),
            "last_checked": datetime.now().isoformat()
        }