"""
SEC2 - Vault Cryptography
AES-256-GCM encryption for secure key storage.

Security notes:
- Uses AES-256-GCM (authenticated encryption)
- Each encryption uses a unique nonce/IV
- Master key should be loaded from secure environment
- In production, consider using HSM or KMS
"""

import os
import base64
import secrets
import hashlib
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class VaultCrypto:
    """
    AES-256-GCM encryption service for vault secrets.
    
    Security features:
    - 256-bit key (derived from master secret)
    - 96-bit nonce (unique per encryption)
    - GCM mode provides authenticated encryption
    """
    
    # Nonce size for GCM (96 bits = 12 bytes)
    NONCE_SIZE = 12
    
    # Key size for AES-256
    KEY_SIZE = 32
    
    def __init__(self):
        """Initialize crypto with master key from environment"""
        self._master_key = self._load_master_key()
        self._aesgcm = AESGCM(self._master_key)
    
    def _load_master_key(self) -> bytes:
        """
        Load or derive master encryption key.
        
        In production, this should come from:
        - Environment variable
        - HashiCorp Vault
        - AWS KMS
        - GCP Secret Manager
        
        For now, we derive from VAULT_MASTER_SECRET env var,
        or generate a development key if not set.
        """
        master_secret = os.environ.get("VAULT_MASTER_SECRET")
        
        if master_secret:
            # Derive 256-bit key from secret using SHA-256
            return hashlib.sha256(master_secret.encode()).digest()
        else:
            # Development mode: generate ephemeral key
            # WARNING: Keys encrypted with this won't survive restart
            print("[VaultCrypto] WARNING: No VAULT_MASTER_SECRET set, using ephemeral key")
            return secrets.token_bytes(self.KEY_SIZE)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext using AES-256-GCM.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded string: nonce + ciphertext + tag
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")
        
        # Generate unique nonce for this encryption
        nonce = secrets.token_bytes(self.NONCE_SIZE)
        
        # Encrypt (GCM automatically appends auth tag)
        ciphertext = self._aesgcm.encrypt(
            nonce,
            plaintext.encode('utf-8'),
            associated_data=None
        )
        
        # Combine nonce + ciphertext for storage
        encrypted_data = nonce + ciphertext
        
        # Return as base64 string
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt AES-256-GCM encrypted string.
        
        Args:
            encrypted: Base64-encoded encrypted data (nonce + ciphertext + tag)
            
        Returns:
            Decrypted plaintext string
        """
        if not encrypted:
            raise ValueError("Cannot decrypt empty string")
        
        # Decode from base64
        encrypted_data = base64.b64decode(encrypted)
        
        # Extract nonce and ciphertext
        nonce = encrypted_data[:self.NONCE_SIZE]
        ciphertext = encrypted_data[self.NONCE_SIZE:]
        
        # Decrypt and verify
        plaintext = self._aesgcm.decrypt(
            nonce,
            ciphertext,
            associated_data=None
        )
        
        return plaintext.decode('utf-8')
    
    def rotate_key(self, old_encrypted: str, new_crypto: 'VaultCrypto') -> str:
        """
        Re-encrypt data with a new key (for key rotation).
        
        Args:
            old_encrypted: Data encrypted with current key
            new_crypto: VaultCrypto instance with new master key
            
        Returns:
            Data encrypted with new key
        """
        # Decrypt with old key
        plaintext = self.decrypt(old_encrypted)
        
        # Encrypt with new key
        return new_crypto.encrypt(plaintext)
    
    @staticmethod
    def generate_key_id() -> str:
        """Generate a unique key ID"""
        return f"key_{secrets.token_hex(8)}"
    
    @staticmethod
    def generate_token_id() -> str:
        """Generate a unique token ID"""
        return f"tok_{secrets.token_hex(12)}"
    
    @staticmethod
    def generate_event_id() -> str:
        """Generate a unique audit event ID"""
        return f"evt_{secrets.token_hex(8)}"
    
    @staticmethod
    def mask_key(api_key: str, visible_chars: int = 4) -> str:
        """
        Mask an API key for display.
        Shows first and last N characters, rest as asterisks.
        
        Example: "ABCDEFGHIJKLMNOP" -> "ABCD********MNOP"
        """
        if not api_key:
            return "****"
        
        if len(api_key) <= visible_chars * 2:
            return "*" * len(api_key)
        
        start = api_key[:visible_chars]
        end = api_key[-visible_chars:]
        middle_len = len(api_key) - (visible_chars * 2)
        
        return f"{start}{'*' * middle_len}{end}"


# Singleton instance
_crypto_instance = None

def get_vault_crypto() -> VaultCrypto:
    """Get singleton VaultCrypto instance"""
    global _crypto_instance
    if _crypto_instance is None:
        _crypto_instance = VaultCrypto()
    return _crypto_instance
