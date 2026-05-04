"""
SEC2 - Vault Service
Core service for API key management with encryption and access control.
"""

from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from .vault_types import (
    APIKeyRecord,
    VaultAccessToken,
    KeyPermission,
    KeyStatus,
    CreateKeyRequest,
    KeyResponse,
    AccessTokenRequest,
    AccessTokenResponse,
    RotateKeyRequest,
    UpdatePermissionsRequest
)
from .vault_crypto import get_vault_crypto, VaultCrypto
from .vault_repository import get_vault_repository, VaultRepository
from .vault_policy import get_vault_policy, VaultPolicy
from .vault_audit import get_vault_audit, VaultAudit


class VaultService:
    """
    Core API Key Vault service.
    
    Provides:
    - Encrypted key storage
    - Access token generation
    - Permission-based access control
    - Key rotation
    - Audit trail
    
    Security:
    - Keys are always stored encrypted
    - Secrets are never returned via API
    - All access is logged
    - Scope-based permissions
    """
    
    def __init__(self):
        """Initialize vault service"""
        self._crypto: VaultCrypto = get_vault_crypto()
        self._repo: VaultRepository = get_vault_repository()
        self._policy: VaultPolicy = get_vault_policy()
        self._audit: VaultAudit = get_vault_audit()
        
        # In-memory token store (short-lived tokens)
        self._active_tokens: dict[str, VaultAccessToken] = {}
    
    # ===========================================
    # Key Management
    # ===========================================
    
    def create_key(
        self,
        request: CreateKeyRequest,
        requesting_service: str = "admin",
        user_id: Optional[str] = None
    ) -> KeyResponse:
        """
        Create a new API key record.
        
        The API key and secret are encrypted before storage.
        """
        # Generate unique key ID
        key_id = self._crypto.generate_key_id()
        
        # Encrypt credentials
        encrypted_api = self._crypto.encrypt(request.api_key)
        encrypted_secret = self._crypto.encrypt(request.secret_key)
        encrypted_passphrase = None
        if request.passphrase:
            encrypted_passphrase = self._crypto.encrypt(request.passphrase)
        
        # Validate permissions
        valid, error = self._policy.validate_permissions_update(request.permissions)
        if not valid:
            raise ValueError(error)
        
        # Create record
        key_record = APIKeyRecord(
            key_id=key_id,
            exchange=request.exchange.upper(),
            account_name=request.account_name,
            encrypted_api_key=encrypted_api,
            encrypted_secret_key=encrypted_secret,
            encrypted_passphrase=encrypted_passphrase,
            permissions=request.permissions,
            status=KeyStatus.ACTIVE,
            notes=request.notes
        )
        
        # Store
        self._repo.create_key(key_record)
        
        # Audit
        self._audit.log_create(
            key_id=key_id,
            service=requesting_service,
            user_id=user_id,
            metadata={
                "exchange": request.exchange,
                "account_name": request.account_name,
                "permissions": [p.value for p in request.permissions]
            }
        )
        
        return self._to_key_response(key_record, request.api_key)
    
    def get_key(self, key_id: str) -> Optional[KeyResponse]:
        """Get a key by ID (returns masked response)"""
        key_record = self._repo.get_key(key_id)
        if not key_record:
            return None
        
        # Decrypt API key for masking
        api_key = self._crypto.decrypt(key_record.encrypted_api_key)
        return self._to_key_response(key_record, api_key)
    
    def get_all_keys(
        self,
        status: Optional[KeyStatus] = None,
        exchange: Optional[str] = None
    ) -> List[KeyResponse]:
        """Get all keys (returns masked responses)"""
        key_records = self._repo.get_all_keys(status=status, exchange=exchange)
        
        responses = []
        for record in key_records:
            api_key = self._crypto.decrypt(record.encrypted_api_key)
            responses.append(self._to_key_response(record, api_key))
        
        return responses
    
    def get_active_keys(self) -> List[KeyResponse]:
        """Get all active keys"""
        return self.get_all_keys(status=KeyStatus.ACTIVE)
    
    def _to_key_response(
        self, 
        record: APIKeyRecord, 
        api_key: str
    ) -> KeyResponse:
        """Convert record to masked response"""
        return KeyResponse(
            key_id=record.key_id,
            exchange=record.exchange,
            account_name=record.account_name,
            api_key_masked=self._crypto.mask_key(api_key),
            permissions=record.permissions,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            last_used_at=record.last_used_at,
            access_count=record.access_count,
            notes=record.notes
        )
    
    # ===========================================
    # Access Token Management
    # ===========================================
    
    def get_access_token(
        self,
        request: AccessTokenRequest,
        ip_address: Optional[str] = None
    ) -> Tuple[Optional[VaultAccessToken], Optional[str]]:
        """
        Request an access token for a key.
        
        Returns:
            (token, error) - Token if successful, error message if not
        """
        # Get key record
        key_record = self._repo.get_key(request.key_id)
        if not key_record:
            self._audit.log_access(
                key_id=request.key_id,
                service=request.requesting_service,
                scope_requested=request.scope,
                success=False,
                error_message="Key not found",
                ip_address=ip_address
            )
            return None, "Key not found"
        
        # Check access policy
        allowed, reason = self._policy.check_access(
            key_record,
            request.scope,
            request.requesting_service
        )
        
        if not allowed:
            self._audit.log_access(
                key_id=request.key_id,
                service=request.requesting_service,
                scope_requested=request.scope,
                success=False,
                error_message=reason,
                ip_address=ip_address
            )
            return None, reason
        
        # Decrypt credentials
        api_key = self._crypto.decrypt(key_record.encrypted_api_key)
        secret_key = self._crypto.decrypt(key_record.encrypted_secret_key)
        passphrase = None
        if key_record.encrypted_passphrase:
            passphrase = self._crypto.decrypt(key_record.encrypted_passphrase)
        
        # Create token
        token = VaultAccessToken(
            token_id=self._crypto.generate_token_id(),
            key_id=request.key_id,
            scope=request.scope,
            api_key=api_key,
            secret_key=secret_key,
            passphrase=passphrase,
            expires_at=datetime.utcnow() + timedelta(seconds=request.ttl_seconds),
            requesting_service=request.requesting_service
        )
        
        # Store in memory
        self._active_tokens[token.token_id] = token
        
        # Update last used
        self._repo.update_last_used(request.key_id)
        
        # Audit
        self._audit.log_access(
            key_id=request.key_id,
            service=request.requesting_service,
            scope_requested=request.scope,
            scope_granted=request.scope,
            success=True,
            ip_address=ip_address
        )
        
        return token, None
    
    def validate_token(self, token_id: str) -> Optional[VaultAccessToken]:
        """Validate and return an active token"""
        token = self._active_tokens.get(token_id)
        
        if not token:
            return None
        
        # Check expiration
        if datetime.utcnow() > token.expires_at:
            del self._active_tokens[token_id]
            return None
        
        return token
    
    def revoke_token(self, token_id: str) -> bool:
        """Revoke an access token"""
        if token_id in self._active_tokens:
            del self._active_tokens[token_id]
            return True
        return False
    
    def cleanup_expired_tokens(self) -> int:
        """Clean up expired tokens"""
        now = datetime.utcnow()
        expired = [
            tid for tid, token in self._active_tokens.items()
            if now > token.expires_at
        ]
        for tid in expired:
            del self._active_tokens[tid]
        return len(expired)
    
    # ===========================================
    # Key Lifecycle
    # ===========================================
    
    def rotate_key(
        self,
        key_id: str,
        request: RotateKeyRequest,
        requesting_service: str = "admin",
        user_id: Optional[str] = None
    ) -> KeyResponse:
        """
        Rotate an API key with new credentials.
        
        Process:
        1. Mark old key as ROTATED
        2. Create new key with same settings
        3. Link new key to old
        """
        # Get existing key
        old_key = self._repo.get_key(key_id)
        if not old_key:
            raise ValueError(f"Key {key_id} not found")
        
        # Generate new key ID
        new_key_id = self._crypto.generate_key_id()
        
        # Encrypt new credentials
        encrypted_api = self._crypto.encrypt(request.new_api_key)
        encrypted_secret = self._crypto.encrypt(request.new_secret_key)
        encrypted_passphrase = None
        if request.new_passphrase:
            encrypted_passphrase = self._crypto.encrypt(request.new_passphrase)
        
        # Create new key record
        new_key = APIKeyRecord(
            key_id=new_key_id,
            exchange=old_key.exchange,
            account_name=old_key.account_name,
            encrypted_api_key=encrypted_api,
            encrypted_secret_key=encrypted_secret,
            encrypted_passphrase=encrypted_passphrase,
            permissions=old_key.permissions,
            status=KeyStatus.ACTIVE,
            rotated_from=key_id,
            notes=old_key.notes
        )
        
        # Mark old key as rotated
        self._repo.update_key_status(key_id, KeyStatus.ROTATED)
        
        # Store new key
        self._repo.create_key(new_key)
        
        # Audit
        self._audit.log_rotate(
            key_id=new_key_id,
            service=requesting_service,
            old_key_id=key_id,
            user_id=user_id
        )
        
        return self._to_key_response(new_key, request.new_api_key)
    
    def disable_key(
        self,
        key_id: str,
        reason: Optional[str] = None,
        requesting_service: str = "admin",
        user_id: Optional[str] = None
    ) -> bool:
        """Disable an API key"""
        key = self._repo.get_key(key_id)
        if not key:
            return False
        
        self._repo.update_key_status(key_id, KeyStatus.DISABLED)
        
        # Revoke any active tokens for this key
        self._revoke_tokens_for_key(key_id)
        
        # Audit
        self._audit.log_disable(
            key_id=key_id,
            service=requesting_service,
            reason=reason,
            user_id=user_id
        )
        
        return True
    
    def enable_key(
        self,
        key_id: str,
        requesting_service: str = "admin",
        user_id: Optional[str] = None
    ) -> bool:
        """Enable a disabled API key"""
        key = self._repo.get_key(key_id)
        if not key:
            return False
        
        if key.status not in [KeyStatus.DISABLED]:
            return False
        
        self._repo.update_key_status(key_id, KeyStatus.ACTIVE)
        
        # Audit
        self._audit.log_enable(
            key_id=key_id,
            service=requesting_service,
            user_id=user_id
        )
        
        return True
    
    def delete_key(
        self,
        key_id: str,
        reason: Optional[str] = None,
        requesting_service: str = "admin",
        user_id: Optional[str] = None
    ) -> bool:
        """Delete an API key (use with caution)"""
        key = self._repo.get_key(key_id)
        if not key:
            return False
        
        # Revoke any active tokens
        self._revoke_tokens_for_key(key_id)
        
        # Delete from storage
        result = self._repo.delete_key(key_id)
        
        if result:
            # Audit
            self._audit.log_delete(
                key_id=key_id,
                service=requesting_service,
                user_id=user_id,
                reason=reason
            )
        
        return result
    
    def _revoke_tokens_for_key(self, key_id: str):
        """Revoke all active tokens for a key"""
        to_revoke = [
            tid for tid, token in self._active_tokens.items()
            if token.key_id == key_id
        ]
        for tid in to_revoke:
            del self._active_tokens[tid]
    
    # ===========================================
    # Permission Management
    # ===========================================
    
    def update_permissions(
        self,
        key_id: str,
        request: UpdatePermissionsRequest,
        requesting_service: str = "admin",
        user_id: Optional[str] = None
    ) -> Optional[KeyResponse]:
        """Update permissions for a key"""
        key = self._repo.get_key(key_id)
        if not key:
            return None
        
        # Validate new permissions
        valid, error = self._policy.validate_permissions_update(request.permissions)
        if not valid:
            raise ValueError(error)
        
        old_permissions = key.permissions
        
        # Update
        updated = self._repo.update_key(
            key_id,
            {"permissions": [p.value for p in request.permissions]}
        )
        
        if updated:
            # Audit
            self._audit.log_permission_change(
                key_id=key_id,
                service=requesting_service,
                old_permissions=old_permissions,
                new_permissions=request.permissions,
                user_id=user_id
            )
            
            api_key = self._crypto.decrypt(updated.encrypted_api_key)
            return self._to_key_response(updated, api_key)
        
        return None
    
    # ===========================================
    # Health & Stats
    # ===========================================
    
    def get_health(self) -> dict:
        """Get vault health status"""
        total = self._repo.count_keys()
        active = self._repo.count_keys(status=KeyStatus.ACTIVE)
        
        return {
            "status": "healthy",
            "version": "sec2_v1",
            "total_keys": total,
            "active_keys": active,
            "active_tokens": len(self._active_tokens),
            "encryption_enabled": True,
            "audit_enabled": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_stats(self) -> dict:
        """Get vault statistics"""
        return {
            "keys": {
                "total": self._repo.count_keys(),
                "active": self._repo.count_keys(status=KeyStatus.ACTIVE),
                "disabled": self._repo.count_keys(status=KeyStatus.DISABLED),
                "rotated": self._repo.count_keys(status=KeyStatus.ROTATED)
            },
            "tokens": {
                "active": len(self._active_tokens)
            },
            "audit": self._audit.get_audit_summary()
        }


# Singleton instance
_service_instance = None

def get_vault_service() -> VaultService:
    """Get singleton VaultService instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = VaultService()
    return _service_instance
