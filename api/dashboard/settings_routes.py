"""Settings API endpoints for Dashboard Configuration Management"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator
import requests
from utils.redis_utils import r
from utils.redis_key_builder import redis_keys
from utils.encryption import encrypt_value, decrypt_value, is_encrypted_value, secure_store, secure_retrieve
from .config import DEFAULT_USER_ID
from .auth import verify_token, update_admin_password

logger = logging.getLogger("uvicorn")

# Settings API Router
router = APIRouter(prefix="/settings", tags=["settings"])

# Pydantic Models
class SettingValue(BaseModel):
    key: str
    value: str
    category: str
    description: Optional[str] = None
    is_sensitive: bool = False
    requires_restart: bool = False

class SettingUpdate(BaseModel):
    value: str

class SettingTest(BaseModel):
    key: str
    value: str

class SettingsBackup(BaseModel):
    settings: Dict[str, Any]
    timestamp: datetime
    version: str = "1.0"

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

# Settings Schema Definition
SETTINGS_SCHEMA = {
    # System Settings
    "dashboard_password": {
        "category": "system",
        "description": "Dashboard admin password",
        "is_sensitive": True,
        "requires_restart": False,
        "default": "meta-admin-2024"
    },
    "default_user_id": {
        "category": "system", 
        "description": "Default user ID for operations",
        "is_sensitive": False,
        "requires_restart": True,
        "default": "60122873632"
    },
    "limitless_log_level": {
        "category": "system",
        "description": "Limitless integration log level",
        "is_sensitive": False,
        "requires_restart": False,
        "default": "WARNING",
        "options": ["DEBUG", "INFO", "WARNING", "ERROR"]
    },
    
    # API Keys - AI Services
    "gemini_api_key": {
        "category": "ai_services",
        "description": "Google Gemini API key for AI processing",
        "is_sensitive": True,
        "requires_restart": False,
        "validation": lambda x: x.startswith("AIza") if x else False
    },
    "limitless_api_key": {
        "category": "ai_services", 
        "description": "Limitless API key for memory integration",
        "is_sensitive": True,
        "requires_restart": False,
        "validation": lambda x: x.startswith("sk-") if x else False
    },
    
    # API Keys - Communication
    "whatsapp_auth_token": {
        "category": "communication",
        "description": "WhatsApp Business API authentication token",
        "is_sensitive": True,
        "requires_restart": False
    },
    "whatsapp_phone_number": {
        "category": "communication",
        "description": "WhatsApp Business phone number",
        "is_sensitive": False,
        "requires_restart": False
    },
    "whatsapp_webhook_verification_token": {
        "category": "communication",
        "description": "WhatsApp webhook verification token",
        "is_sensitive": True,
        "requires_restart": False
    },
    
    # API Keys - Productivity
    "notion_integration_secret": {
        "category": "productivity",
        "description": "Notion integration token",
        "is_sensitive": True,
        "requires_restart": False,
        "validation": lambda x: x.startswith("ntn_") if x else False
    },
    "notion_database_id": {
        "category": "productivity",
        "description": "Notion database ID for notes",
        "is_sensitive": False,
        "requires_restart": False
    },
    
    # API Keys - Home Automation
    "home_assistant_token": {
        "category": "home_automation",
        "description": "Home Assistant long-lived access token",
        "is_sensitive": True,
        "requires_restart": False
    },
    "home_assistant_url": {
        "category": "home_automation",
        "description": "Home Assistant URL",
        "is_sensitive": False,
        "requires_restart": False
    },
    "home_assistant_agent_id": {
        "category": "home_automation",
        "description": "Home Assistant conversation agent ID",
        "is_sensitive": False,
        "requires_restart": False
    },
    
    # API Keys - External Services
    "serper_dev_api_key": {
        "category": "external_services",
        "description": "Serper.dev API key for search",
        "is_sensitive": True,
        "requires_restart": False
    },
    "crawlbase_api_key": {
        "category": "external_services",
        "description": "Crawlbase API key for web scraping",
        "is_sensitive": True,
        "requires_restart": False
    },
    
    # Cloud Storage
    "cloud_storage_bucket_name": {
        "category": "storage",
        "description": "Google Cloud Storage bucket name",
        "is_sensitive": False,
        "requires_restart": False
    },
    "oauth_credentials_encoded": {
        "category": "storage",
        "description": "Encoded Google OAuth credentials",
        "is_sensitive": True,
        "requires_restart": False
    }
}

def get_setting_redis_key(key: str) -> str:
    """Get Redis key for a setting"""
    return f"meta-glasses:settings:global:{key}"

# Define sensitive settings that should be encrypted
SENSITIVE_SETTINGS = {
    "dashboard_password",
    "gemini_api_key", 
    "limitless_api_key",
    "whatsapp_auth_token",
    "whatsapp_webhook_verification_token",
    "notion_integration_secret",
    "home_assistant_token",
    "serper_dev_api_key",
    "crawlbase_api_key",
    "oauth_credentials_encoded"
}

def mask_sensitive_value(value: str, is_sensitive: bool) -> str:
    """Mask sensitive values for display"""
    if not is_sensitive or not value:
        return value
    
    if len(value) <= 8:
        return "*" * len(value)
    
    # Show first 3 and last 3 characters
    return f"{value[:3]}{'*' * (len(value) - 6)}{value[-3:]}"

def get_current_env_value(key: str) -> Optional[str]:
    """Get current value from environment variables"""
    env_key = key.upper()
    return os.getenv(env_key)

@router.get("/schema")
async def get_settings_schema(user: dict = Depends(verify_token)):
    """Get settings schema with metadata"""
    try:
        return {
            "schema": SETTINGS_SCHEMA,
            "categories": {
                "system": "System Configuration",
                "ai_services": "AI Services",
                "communication": "Communication",
                "productivity": "Productivity Tools", 
                "home_automation": "Home Automation",
                "external_services": "External Services",
                "storage": "Cloud Storage"
            }
        }
    except Exception as e:
        logger.error(f"Error getting settings schema: {e}")
        raise HTTPException(status_code=500, detail="Failed to get settings schema")

@router.get("/")
async def get_all_settings(user: dict = Depends(verify_token)):
    """Get all settings with current values"""
    try:
        settings = {}
        
        for key, schema in SETTINGS_SCHEMA.items():
            # Try Redis first, then environment variables
            redis_key = get_setting_redis_key(key)
            redis_value = r.get(redis_key)
            
            if redis_value:
                encrypted_value = redis_value.decode('utf-8')
                # Decrypt if the value is encrypted
                value = secure_retrieve(encrypted_value)
                source = "redis"
            else:
                value = get_current_env_value(key)
                source = "environment"
            
            # Apply masking for sensitive values
            display_value = mask_sensitive_value(value or "", schema.get("is_sensitive", False))
            
            settings[key] = {
                "value": display_value,
                "source": source,
                "has_value": bool(value),
                "category": schema["category"],
                "description": schema["description"],
                "is_sensitive": schema.get("is_sensitive", False),
                "requires_restart": schema.get("requires_restart", False),
                "options": schema.get("options")
            }
        
        return {"settings": settings}
    
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get settings")

@router.get("/{key}")
async def get_setting(key: str, user: dict = Depends(verify_token)):
    """Get a specific setting"""
    try:
        if key not in SETTINGS_SCHEMA:
            raise HTTPException(status_code=404, detail="Setting not found")
        
        schema = SETTINGS_SCHEMA[key]
        redis_key = get_setting_redis_key(key)
        redis_value = r.get(redis_key)
        
        if redis_value:
            encrypted_value = redis_value.decode('utf-8')
            # Decrypt if the value is encrypted
            value = secure_retrieve(encrypted_value)
            source = "redis"
        else:
            value = get_current_env_value(key)
            source = "environment"
        
        # Apply masking for sensitive values
        display_value = mask_sensitive_value(value or "", schema.get("is_sensitive", False))
        
        return {
            "key": key,
            "value": display_value,
            "source": source,
            "has_value": bool(value),
            **schema
        }
    
    except Exception as e:
        logger.error(f"Error getting setting {key}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get setting {key}")

@router.put("/{key}")
async def update_setting(key: str, setting_update: SettingUpdate, user: dict = Depends(verify_token)):
    """Update a specific setting"""
    try:
        if key not in SETTINGS_SCHEMA:
            raise HTTPException(status_code=404, detail="Setting not found")
        
        schema = SETTINGS_SCHEMA[key]
        value = setting_update.value
        
        # Validate value if validator exists
        if "validation" in schema and schema["validation"]:
            if not schema["validation"](value):
                raise HTTPException(status_code=400, detail=f"Invalid value format for {key}")
        
        # Store in Redis with encryption for sensitive settings
        redis_key = get_setting_redis_key(key)
        stored_value = secure_store(key, value, SENSITIVE_SETTINGS)
        r.set(redis_key, stored_value)
        
        # Log the change
        logger.info(f"Setting {key} updated by user {user.get('user', 'unknown')}")
        
        # Store audit log
        audit_key = f"meta-glasses:settings:audit:{key}:{int(datetime.now().timestamp())}"
        audit_data = {
            "key": key,
            "previous_source": "redis" if r.get(redis_key) else "environment",
            "new_value_set": True,
            "changed_by": user.get('user', 'unknown'),
            "timestamp": datetime.now().isoformat(),
            "requires_restart": schema.get("requires_restart", False)
        }
        r.setex(audit_key, 86400 * 30, json.dumps(audit_data))  # Keep for 30 days
        
        return {
            "success": True,
            "message": f"Setting {key} updated successfully",
            "requires_restart": schema.get("requires_restart", False)
        }
    
    except Exception as e:
        logger.error(f"Error updating setting {key}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update setting {key}")

@router.delete("/{key}")
async def delete_setting(key: str, user: dict = Depends(verify_token)):
    """Delete a setting (revert to environment variable)"""
    try:
        if key not in SETTINGS_SCHEMA:
            raise HTTPException(status_code=404, detail="Setting not found")
        
        redis_key = get_setting_redis_key(key)
        r.delete(redis_key)
        
        # Log the change
        logger.info(f"Setting {key} deleted (reverted to env) by user {user.get('user', 'unknown')}")
        
        return {
            "success": True,
            "message": f"Setting {key} reverted to environment variable"
        }
    
    except Exception as e:
        logger.error(f"Error deleting setting {key}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete setting {key}")

@router.post("/test/{key}")
async def test_setting_connection(key: str, setting_test: SettingTest, user: dict = Depends(verify_token)):
    """Test connection for a specific setting"""
    try:
        if key not in SETTINGS_SCHEMA:
            raise HTTPException(status_code=404, detail="Setting not found")
        
        value = setting_test.value
        test_result = {"success": False, "message": "Test not implemented for this setting"}
        
        # Implement specific tests for different services
        if key == "gemini_api_key":
            test_result = await test_gemini_connection(value)
        elif key == "whatsapp_auth_token":
            test_result = await test_whatsapp_connection(value)
        elif key == "notion_integration_secret":
            test_result = await test_notion_connection(value)
        elif key == "home_assistant_token":
            test_result = await test_home_assistant_connection(value, 
                get_current_env_value("home_assistant_url") or "")
        else:
            test_result = {"success": True, "message": "Setting format is valid"}
        
        return test_result
    
    except Exception as e:
        logger.error(f"Error testing setting {key}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test setting {key}")

# Connection test functions
async def test_gemini_connection(api_key: str) -> Dict[str, Any]:
    """Test Gemini API connection"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Try to list models as a simple test
        models = genai.list_models()
        model_count = len(list(models))
        
        return {
            "success": True,
            "message": f"Successfully connected to Gemini API. {model_count} models available."
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to connect to Gemini API: {str(e)}"
        }

async def test_whatsapp_connection(auth_token: str) -> Dict[str, Any]:
    """Test WhatsApp API connection"""
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            "https://graph.facebook.com/v18.0/me",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "message": f"Successfully connected to WhatsApp API. Account: {data.get('name', 'Unknown')}"
            }
        else:
            return {
                "success": False,
                "message": f"WhatsApp API error: {response.status_code} - {response.text}"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to connect to WhatsApp API: {str(e)}"
        }

async def test_notion_connection(token: str) -> Dict[str, Any]:
    """Test Notion API connection"""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28"
        }
        response = requests.get(
            "https://api.notion.com/v1/users/me",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "message": f"Successfully connected to Notion API. User: {data.get('name', 'Unknown')}"
            }
        else:
            return {
                "success": False,
                "message": f"Notion API error: {response.status_code} - {response.text}"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to connect to Notion API: {str(e)}"
        }

async def test_home_assistant_connection(token: str, url: str) -> Dict[str, Any]:
    """Test Home Assistant connection"""
    try:
        if not url:
            return {
                "success": False,
                "message": "Home Assistant URL not configured"
            }
        
        headers = {"Authorization": f"Bearer {token}"}
        test_url = f"https://{url}/api/config" if not url.startswith('http') else f"{url}/api/config"
        
        response = requests.get(test_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "message": f"Successfully connected to Home Assistant. Version: {data.get('version', 'Unknown')}"
            }
        else:
            return {
                "success": False,
                "message": f"Home Assistant API error: {response.status_code}"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to connect to Home Assistant: {str(e)}"
        }

@router.post("/change-password")
async def change_admin_password(password_change: PasswordChange, user: dict = Depends(verify_token)):
    """Change the admin dashboard password"""
    try:
        from .auth import authenticate_user
        
        # Verify current password
        if not authenticate_user(password_change.current_password, "localhost"):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        
        # Validate new password strength
        if len(password_change.new_password) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters long")
        
        # Update password
        if update_admin_password(password_change.new_password):
            logger.info(f"Admin password changed by user {user.get('user', 'unknown')}")
            return {
                "success": True,
                "message": "Password changed successfully. Please log in again with your new password."
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update password")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")