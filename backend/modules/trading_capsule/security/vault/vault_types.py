"""
SEC2 - Vault Data Types
Defines core data models for API Key Vault.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class KeyPermission(str, Enum):
    """Permission scopes for API keys"""
    READ = "READ"           # Can read account data, positions, orders
    TRADE = "TRADE"         # Can place/cancel orders
    WITHDRAW = "WITHDRAW"   # Can withdraw funds (highest risk)


class KeyStatus(str, Enum):
    """API key lifecycle status"""
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    ROTATED = "ROTATED"
    EXPIRED = "EXPIRED"


class AuditAction(str, Enum):
    """Audit event actions"""
    CREATE = "CREATE"
    ACCESS = "ACCESS"
    ROTATE = "ROTATE"
    DISABLE = "DISABLE"
    ENABLE = "ENABLE"
    DELETE = "DELETE"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    FAILED_ACCESS = "FAILED_ACCESS"


# ===========================================
# Core Data Models
# ===========================================

class APIKeyRecord(BaseModel):
    """
    Stored API key record.
    API key and secret are always stored encrypted.
    """
    key_id: str = Field(..., description="Unique identifier for this key")
    
    # Exchange info
    exchange: str = Field(..., description="Exchange name (BINANCE, BYBIT, etc.)")
    account_name: str = Field(..., description="Human-readable account name")
    
    # Encrypted credentials (NEVER store plaintext)
    encrypted_api_key: str = Field(..., description="AES-256-GCM encrypted API key")
    encrypted_secret_key: str = Field(..., description="AES-256-GCM encrypted secret")
    
    # Optional passphrase for some exchanges (e.g., OKX)
    encrypted_passphrase: Optional[str] = Field(None, description="Encrypted passphrase if required")
    
    # Permissions
    permissions: List[KeyPermission] = Field(
        default=[KeyPermission.READ],
        description="Allowed permission scopes"
    )
    
    # Status
    status: KeyStatus = Field(default=KeyStatus.ACTIVE)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    rotated_from: Optional[str] = Field(None, description="Previous key_id if rotated")
    
    # Usage tracking
    access_count: int = Field(default=0)
    
    # Notes
    notes: Optional[str] = None

    class Config:
        use_enum_values = True


class VaultAccessToken(BaseModel):
    """
    Temporary access token for using a key.
    Modules request tokens instead of raw keys.
    """
    token_id: str = Field(..., description="Unique token identifier")
    
    key_id: str = Field(..., description="Reference to the API key")
    
    scope: KeyPermission = Field(..., description="Requested permission scope")
    
    # The decrypted credentials (only in memory, never stored)
    api_key: Optional[str] = Field(None, description="Decrypted API key")
    secret_key: Optional[str] = Field(None, description="Decrypted secret")
    passphrase: Optional[str] = Field(None, description="Decrypted passphrase")
    
    # Token lifecycle
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(..., description="Token expiration time")
    
    # Context
    requesting_service: str = Field(..., description="Service that requested the token")
    
    class Config:
        use_enum_values = True


class VaultAuditEvent(BaseModel):
    """
    Audit log entry for all vault operations.
    Every access is recorded.
    """
    event_id: str = Field(..., description="Unique event identifier")
    
    key_id: str = Field(..., description="Reference to the API key")
    
    action: AuditAction = Field(..., description="Type of action performed")
    
    # Who performed the action
    service: str = Field(..., description="Service/module that performed action")
    user_id: Optional[str] = Field(None, description="User ID if applicable")
    
    # Request context
    scope_requested: Optional[KeyPermission] = None
    scope_granted: Optional[KeyPermission] = None
    
    # Result
    success: bool = Field(default=True)
    error_message: Optional[str] = None
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional context
    ip_address: Optional[str] = None
    metadata: Optional[dict] = None

    class Config:
        use_enum_values = True


# ===========================================
# Request/Response Models
# ===========================================

class CreateKeyRequest(BaseModel):
    """Request to create a new API key"""
    exchange: str
    account_name: str
    api_key: str
    secret_key: str
    passphrase: Optional[str] = None
    permissions: List[KeyPermission] = [KeyPermission.READ]
    notes: Optional[str] = None


class KeyResponse(BaseModel):
    """Response with masked key info (never returns secret)"""
    key_id: str
    exchange: str
    account_name: str
    api_key_masked: str  # e.g., "ABCD****WXYZ"
    permissions: List[KeyPermission]
    status: KeyStatus
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime]
    access_count: int
    notes: Optional[str] = None

    class Config:
        use_enum_values = True


class AccessTokenRequest(BaseModel):
    """Request for a vault access token"""
    key_id: str
    scope: KeyPermission
    requesting_service: str
    ttl_seconds: int = Field(default=300, ge=30, le=3600)  # 5 min default, max 1 hour


class AccessTokenResponse(BaseModel):
    """Response with access token (credentials only in memory)"""
    token_id: str
    key_id: str
    scope: KeyPermission
    expires_at: datetime
    # Note: actual credentials are delivered separately through secure channel
    
    class Config:
        use_enum_values = True


class RotateKeyRequest(BaseModel):
    """Request to rotate an API key"""
    new_api_key: str
    new_secret_key: str
    new_passphrase: Optional[str] = None


class UpdatePermissionsRequest(BaseModel):
    """Request to update key permissions"""
    permissions: List[KeyPermission]


class VaultHealthResponse(BaseModel):
    """Vault health status"""
    status: str
    version: str
    total_keys: int
    active_keys: int
    encryption_enabled: bool
    audit_enabled: bool
    timestamp: datetime
