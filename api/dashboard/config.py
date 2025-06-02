"""Dashboard configuration and constants"""
import os
from typing import List

# Authentication
JWT_SECRET = os.getenv("DASHBOARD_JWT_SECRET", "your-dashboard-secret-key")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "meta-admin-2024")
TOKEN_EXPIRY_HOURS = 24

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