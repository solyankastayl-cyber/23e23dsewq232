"""
SEC2 - API Key Vault
Secure storage for exchange API keys with encryption, masking, and access control.

Components:
- vault_types.py: Data models (APIKey, VaultAccessToken, VaultAuditEvent)
- vault_crypto.py: AES-256-GCM encryption
- vault_service.py: Core vault operations
- vault_repository.py: MongoDB persistence
- vault_policy.py: Permission model (READ, TRADE, WITHDRAW)
- vault_audit.py: Audit trail logging
- vault_routes.py: API endpoints

Security Features:
- Encrypted storage (keys never stored in plaintext)
- Secret masking (secrets never returned via API)
- Scope-based permissions
- Audit trail for all access
- Key rotation support
- Kill switch integration
"""

from .vault_types import (
    APIKeyRecord,
    VaultAccessToken,
    VaultAuditEvent,
    KeyPermission,
    KeyStatus,
    AuditAction
)
from .vault_service import VaultService
from .vault_routes import router as vault_router

__all__ = [
    "APIKeyRecord",
    "VaultAccessToken",
    "VaultAuditEvent",
    "KeyPermission",
    "KeyStatus",
    "AuditAction",
    "VaultService",
    "vault_router"
]
