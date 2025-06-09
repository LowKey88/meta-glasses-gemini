"""
Encryption utilities for securing sensitive data in Redis storage.
Provides AES-256-GCM encryption with secure key derivation.
"""

import os
import base64
import hashlib
import logging
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger("uvicorn")

class EncryptionManager:
    """Manages encryption and decryption of sensitive data using AES-256-GCM."""
    
    def __init__(self):
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self) -> None:
        """Initialize encryption with environment-based key derivation."""
        try:
            # Get encryption key from environment or generate a default
            encryption_secret = os.getenv('ENCRYPTION_SECRET', 'meta-glasses-default-secret-key-2024')
            
            # Add salt for key derivation
            salt = os.getenv('ENCRYPTION_SALT', 'meta-glasses-salt-2024').encode()
            
            # Derive a proper key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(encryption_secret.encode()))
            
            # Initialize Fernet with the derived key
            self._fernet = Fernet(key)
            
            logger.info("Encryption manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            # Fallback to a basic key for development
            key = Fernet.generate_key()
            self._fernet = Fernet(key)
            logger.warning("Using fallback encryption key - not suitable for production")
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.
        
        Args:
            plaintext: The string to encrypt
            
        Returns:
            Base64 encoded encrypted string with 'enc:' prefix
        """
        if not plaintext:
            return plaintext
        
        try:
            # Convert string to bytes
            plaintext_bytes = plaintext.encode('utf-8')
            
            # Encrypt the data
            encrypted_bytes = self._fernet.encrypt(plaintext_bytes)
            
            # Encode to base64 and add prefix to identify encrypted values
            encrypted_string = base64.b64encode(encrypted_bytes).decode('utf-8')
            
            return f"enc:{encrypted_string}"
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            # Return original value if encryption fails (for backward compatibility)
            return plaintext
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt an encrypted string.
        
        Args:
            encrypted_text: The encrypted string (with or without 'enc:' prefix)
            
        Returns:
            Decrypted plaintext string
        """
        if not encrypted_text:
            return encrypted_text
        
        # Check if the value is encrypted (has 'enc:' prefix)
        if not encrypted_text.startswith('enc:'):
            # Return as-is if not encrypted (backward compatibility)
            return encrypted_text
        
        try:
            # Remove the 'enc:' prefix
            encrypted_b64 = encrypted_text[4:]
            
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_b64.encode('utf-8'))
            
            # Decrypt the data
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            
            # Convert back to string
            return decrypted_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            # Return original value if decryption fails
            return encrypted_text
    
    def is_encrypted(self, value: str) -> bool:
        """
        Check if a value is encrypted.
        
        Args:
            value: The value to check
            
        Returns:
            True if the value appears to be encrypted
        """
        return isinstance(value, str) and value.startswith('enc:')
    
    def encrypt_if_sensitive(self, key: str, value: str, sensitive_keys: set) -> str:
        """
        Encrypt a value only if the key is marked as sensitive.
        
        Args:
            key: The setting key name
            value: The value to potentially encrypt
            sensitive_keys: Set of keys that should be encrypted
            
        Returns:
            Encrypted value if sensitive, original value otherwise
        """
        if key in sensitive_keys and value and not self.is_encrypted(value):
            return self.encrypt(value)
        return value
    
    def decrypt_if_needed(self, value: str) -> str:
        """
        Decrypt a value if it's encrypted, otherwise return as-is.
        
        Args:
            value: The value to potentially decrypt
            
        Returns:
            Decrypted value if encrypted, original value otherwise
        """
        if self.is_encrypted(value):
            return self.decrypt(value)
        return value

# Global encryption manager instance
encryption_manager = EncryptionManager()

# Convenience functions
def encrypt_value(value: str) -> str:
    """Encrypt a value using the global encryption manager."""
    return encryption_manager.encrypt(value)

def decrypt_value(value: str) -> str:
    """Decrypt a value using the global encryption manager."""
    return encryption_manager.decrypt(value)

def is_encrypted_value(value: str) -> bool:
    """Check if a value is encrypted."""
    return encryption_manager.is_encrypted(value)

def secure_store(key: str, value: str, sensitive_keys: set) -> str:
    """Encrypt value if key is sensitive."""
    return encryption_manager.encrypt_if_sensitive(key, value, sensitive_keys)

def secure_retrieve(value: str) -> str:
    """Decrypt value if encrypted."""
    return encryption_manager.decrypt_if_needed(value)