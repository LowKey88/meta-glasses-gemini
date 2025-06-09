"""Enhanced authentication utilities for dashboard API with security improvements"""

import jwt
import bcrypt
import secrets
import logging
from datetime import datetime, timedelta
from fastapi import HTTPException, Header
from .config import JWT_SECRET, get_secure_jwt_secret
from utils.redis_utils import r
from utils.encryption import encrypt_value, decrypt_value, is_encrypted_value

logger = logging.getLogger("uvicorn")

class AuthManager:
    """Manages authentication with enhanced security features."""
    
    def __init__(self):
        self.failed_attempts = {}  # Track failed login attempts
        self.max_attempts = 5
        self.lockout_duration = 300  # 5 minutes in seconds
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt with salt."""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    def is_locked_out(self, client_ip: str) -> bool:
        """Check if a client IP is locked out due to failed attempts."""
        if client_ip not in self.failed_attempts:
            return False
        
        attempts, last_attempt = self.failed_attempts[client_ip]
        if attempts >= self.max_attempts:
            if datetime.now().timestamp() - last_attempt < self.lockout_duration:
                return True
            else:
                # Reset failed attempts after lockout period
                del self.failed_attempts[client_ip]
        return False
    
    def record_failed_attempt(self, client_ip: str):
        """Record a failed login attempt."""
        current_time = datetime.now().timestamp()
        if client_ip in self.failed_attempts:
            attempts, _ = self.failed_attempts[client_ip]
            self.failed_attempts[client_ip] = (attempts + 1, current_time)
        else:
            self.failed_attempts[client_ip] = (1, current_time)
    
    def reset_failed_attempts(self, client_ip: str):
        """Reset failed attempts for successful login."""
        if client_ip in self.failed_attempts:
            del self.failed_attempts[client_ip]
    
    def get_stored_password_hash(self) -> str:
        """Get the stored password hash from Redis or return default."""
        try:
            # Try to get hashed password from Redis
            stored_hash = r.get('meta-glasses:auth:password_hash')
            if stored_hash:
                decrypted_hash = decrypt_value(stored_hash.decode('utf-8'))
                return decrypted_hash
            
            # If no stored hash, create one from default password and store it
            default_password = "meta-admin-2024"  # This will be migrated
            hashed_password = self.hash_password(default_password)
            
            # Store the hashed password (encrypted)
            encrypted_hash = encrypt_value(hashed_password)
            r.set('meta-glasses:auth:password_hash', encrypted_hash)
            
            logger.info("Created initial password hash from default password")
            return hashed_password
            
        except Exception as e:
            logger.error(f"Error getting stored password hash: {e}")
            # Fallback to hashing the default password
            return self.hash_password("meta-admin-2024")
    
    def update_password(self, new_password: str) -> bool:
        """Update the stored password hash."""
        try:
            hashed_password = self.hash_password(new_password)
            encrypted_hash = encrypt_value(hashed_password)
            r.set('meta-glasses:auth:password_hash', encrypted_hash)
            logger.info("Password updated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to update password: {e}")
            return False
    
    def authenticate_user(self, password: str, client_ip: str = "unknown") -> bool:
        """Authenticate a user with rate limiting."""
        # Check for lockout
        if self.is_locked_out(client_ip):
            raise HTTPException(
                status_code=429, 
                detail="Too many failed attempts. Please try again later."
            )
        
        # Get stored password hash
        stored_hash = self.get_stored_password_hash()
        
        # Verify password
        if self.verify_password(password, stored_hash):
            self.reset_failed_attempts(client_ip)
            return True
        else:
            self.record_failed_attempt(client_ip)
            return False
    
    def create_access_token(self, user_data: dict, expires_delta: timedelta = None) -> str:
        """Create a JWT access token with secure settings."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        
        to_encode = user_data.copy()
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        # Use secure JWT secret
        secret = get_secure_jwt_secret()
        encoded_jwt = jwt.encode(to_encode, secret, algorithm="HS256")
        return encoded_jwt

# Global auth manager instance
auth_manager = AuthManager()

def verify_token(authorization: str = Header(None)):
    """Verify JWT token from Authorization header with enhanced security."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(" ")[1]
    try:
        # Use secure JWT secret for verification
        secret = get_secure_jwt_secret()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def hash_password(password: str) -> str:
    """Convenience function to hash a password."""
    return auth_manager.hash_password(password)

def verify_password(password: str, hashed: str) -> bool:
    """Convenience function to verify a password."""
    return auth_manager.verify_password(password, hashed)

def authenticate_user(password: str, client_ip: str = "unknown") -> bool:
    """Convenience function to authenticate a user."""
    return auth_manager.authenticate_user(password, client_ip)

def create_access_token(user_data: dict, expires_delta: timedelta = None) -> str:
    """Convenience function to create an access token."""
    return auth_manager.create_access_token(user_data, expires_delta)

def update_admin_password(new_password: str) -> bool:
    """Convenience function to update admin password."""
    return auth_manager.update_password(new_password)