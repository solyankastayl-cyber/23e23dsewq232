"""Encryption Helper — Secure API key storage

Uses Fernet (symmetric encryption) для безопасного хранения API keys в MongoDB.

CRITICAL: SECRET_KEY must be kept secure and never committed to git.

Usage:
    encrypted = encrypt_api_key("my_secret_key")
    decrypted = decrypt_api_key(encrypted)
"""

import os
import base64
from cryptography.fernet import Fernet

# Get encryption key from environment
# IMPORTANT: Generate with: Fernet.generate_key()
SECRET_KEY = os.environ.get(
    "ENCRYPTION_SECRET_KEY",
    # Default для development (NEVER use in production)
    "7vK9qZ2xE5fL8pN3wR6tY1uI4oP0aSdFgHjKlMnBvCxZqWeRtYuIoP"
)

# Ensure key is 32 url-safe base64-encoded bytes
if len(SECRET_KEY) < 32:
    # Pad to 32 bytes for Fernet
    SECRET_KEY = (SECRET_KEY + "=" * 32)[:32]

# Encode to base64 for Fernet
SECRET_KEY_BYTES = base64.urlsafe_b64encode(SECRET_KEY.encode()[:32])

cipher = Fernet(SECRET_KEY_BYTES)


def encrypt_api_key(plain_text: str) -> str:
    """Encrypt API key for storage.
    
    Args:
        plain_text: Plain text API key
    
    Returns:
        Encrypted string (base64)
    """
    if not plain_text:
        return ""
    
    encrypted_bytes = cipher.encrypt(plain_text.encode())
    return encrypted_bytes.decode()


def decrypt_api_key(encrypted_text: str) -> str:
    """Decrypt API key from storage.
    
    Args:
        encrypted_text: Encrypted API key
    
    Returns:
        Decrypted plain text
    """
    if not encrypted_text:
        return ""
    
    decrypted_bytes = cipher.decrypt(encrypted_text.encode())
    return decrypted_bytes.decode()


def generate_new_secret_key() -> str:
    """Generate new Fernet secret key.
    
    Run once and save to ENCRYPTION_SECRET_KEY env variable.
    
    Returns:
        New secret key (base64)
    """
    key = Fernet.generate_key()
    return key.decode()


if __name__ == "__main__":
    # Test encryption
    test_key = "my_test_api_key_12345"
    
    encrypted = encrypt_api_key(test_key)
    print(f"Encrypted: {encrypted}")
    
    decrypted = decrypt_api_key(encrypted)
    print(f"Decrypted: {decrypted}")
    
    assert test_key == decrypted, "Encryption/decryption failed"
    print("✅ Encryption working correctly")
    
    # Generate new key
    new_key = generate_new_secret_key()
    print(f"\nNew secret key (save to env): {new_key}")
