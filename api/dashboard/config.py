"""Dashboard configuration and constants"""
import os
import secrets
from typing import List

# Authentication
JWT_SECRET = os.getenv("DASHBOARD_JWT_SECRET", "your-dashboard-secret-key")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "meta-admin-2024")
TOKEN_EXPIRY_HOURS = 24

def get_secure_jwt_secret() -> str:
    """Get a secure JWT secret, either from environment or use consistent fallback."""
    env_secret = os.getenv("DASHBOARD_JWT_SECRET")
    if env_secret and len(env_secret) >= 32:
        return env_secret
    
    # Use a consistent fallback for development (instead of random generation)
    development_secret = "meta-glasses-development-jwt-secret-key-12345678"
    return development_secret

# API Settings
API_PREFIX = "/api/dashboard"
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "60122873632")

# Pagination
DEFAULT_LIMIT = 50
MAX_LIMIT = 200

# CORS Origins
DASHBOARD_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://localhost:8111",
    "https://rayban.gbhome.my"
]

# Redis Patterns
MEMORY_KEY_PATTERN = "memory:*"
REMINDER_KEY_PATTERN = "reminder:*"
CONTEXT_KEY_PATTERN = "context:*"

# Memory Types
VALID_MEMORY_TYPES = [
    "relationship",
    "important_date", 
    "allergy",
    "preference",
    "personal_info",
    "note"
]