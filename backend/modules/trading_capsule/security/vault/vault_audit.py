"""
SEC2 - Vault Audit Service
Comprehensive audit trail for all vault operations.
"""

from typing import Optional, List
from datetime import datetime

from .vault_types import (
    VaultAuditEvent,
    KeyPermission,
    AuditAction
)
from .vault_crypto import get_vault_crypto
from .vault_repository import get_vault_repository


class VaultAudit:
    """
    Audit service for tracking all vault operations.
    
    Every operation is logged:
    - Key creation
    - Key access (successful and failed)
    - Key rotation
    - Key enable/disable
    - Permission changes
    """
    
    def __init__(self):
        """Initialize audit service"""
        self._repo = get_vault_repository()
        self._crypto = get_vault_crypto()
        self._enabled = True
    
    def log_create(
        self,
        key_id: str,
        service: str,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> VaultAuditEvent:
        """Log key creation"""
        event = VaultAuditEvent(
            event_id=self._crypto.generate_event_id(),
            key_id=key_id,
            action=AuditAction.CREATE,
            service=service,
            user_id=user_id,
            success=True,
            metadata=metadata
        )
        return self._repo.log_audit_event(event)
    
    def log_access(
        self,
        key_id: str,
        service: str,
        scope_requested: KeyPermission,
        scope_granted: Optional[KeyPermission] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> VaultAuditEvent:
        """Log key access attempt"""
        event = VaultAuditEvent(
            event_id=self._crypto.generate_event_id(),
            key_id=key_id,
            action=AuditAction.ACCESS if success else AuditAction.FAILED_ACCESS,
            service=service,
            user_id=user_id,
            scope_requested=scope_requested,
            scope_granted=scope_granted if success else None,
            success=success,
            error_message=error_message,
            ip_address=ip_address
        )
        return self._repo.log_audit_event(event)
    
    def log_rotate(
        self,
        key_id: str,
        service: str,
        old_key_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> VaultAuditEvent:
        """Log key rotation"""
        event = VaultAuditEvent(
            event_id=self._crypto.generate_event_id(),
            key_id=key_id,
            action=AuditAction.ROTATE,
            service=service,
            user_id=user_id,
            success=True,
            metadata={"old_key_id": old_key_id, **(metadata or {})}
        )
        return self._repo.log_audit_event(event)
    
    def log_disable(
        self,
        key_id: str,
        service: str,
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> VaultAuditEvent:
        """Log key disable"""
        event = VaultAuditEvent(
            event_id=self._crypto.generate_event_id(),
            key_id=key_id,
            action=AuditAction.DISABLE,
            service=service,
            user_id=user_id,
            success=True,
            metadata={"reason": reason} if reason else None
        )
        return self._repo.log_audit_event(event)
    
    def log_enable(
        self,
        key_id: str,
        service: str,
        user_id: Optional[str] = None
    ) -> VaultAuditEvent:
        """Log key enable"""
        event = VaultAuditEvent(
            event_id=self._crypto.generate_event_id(),
            key_id=key_id,
            action=AuditAction.ENABLE,
            service=service,
            user_id=user_id,
            success=True
        )
        return self._repo.log_audit_event(event)
    
    def log_delete(
        self,
        key_id: str,
        service: str,
        user_id: Optional[str] = None,
        reason: Optional[str] = None
    ) -> VaultAuditEvent:
        """Log key deletion"""
        event = VaultAuditEvent(
            event_id=self._crypto.generate_event_id(),
            key_id=key_id,
            action=AuditAction.DELETE,
            service=service,
            user_id=user_id,
            success=True,
            metadata={"reason": reason} if reason else None
        )
        return self._repo.log_audit_event(event)
    
    def log_permission_change(
        self,
        key_id: str,
        service: str,
        old_permissions: List[KeyPermission],
        new_permissions: List[KeyPermission],
        user_id: Optional[str] = None
    ) -> VaultAuditEvent:
        """Log permission change"""
        event = VaultAuditEvent(
            event_id=self._crypto.generate_event_id(),
            key_id=key_id,
            action=AuditAction.PERMISSION_CHANGE,
            service=service,
            user_id=user_id,
            success=True,
            metadata={
                "old_permissions": [p.value if isinstance(p, KeyPermission) else p for p in old_permissions],
                "new_permissions": [p.value if isinstance(p, KeyPermission) else p for p in new_permissions]
            }
        )
        return self._repo.log_audit_event(event)
    
    def get_key_history(
        self,
        key_id: str,
        limit: int = 50
    ) -> List[VaultAuditEvent]:
        """Get audit history for a specific key"""
        return self._repo.get_key_audit_history(key_id, limit)
    
    def get_recent_events(
        self,
        action: Optional[AuditAction] = None,
        limit: int = 100
    ) -> List[VaultAuditEvent]:
        """Get recent audit events"""
        return self._repo.get_audit_events(action=action, limit=limit)
    
    def get_failed_access_attempts(
        self,
        limit: int = 20
    ) -> List[VaultAuditEvent]:
        """Get recent failed access attempts (security monitoring)"""
        return self._repo.get_recent_failed_access(limit)
    
    def get_audit_summary(self) -> dict:
        """Get summary of audit events"""
        return {
            "total_events": self._repo.count_audit_events(),
            "total_access": self._repo.count_audit_events(action=AuditAction.ACCESS),
            "failed_access": self._repo.count_audit_events(action=AuditAction.FAILED_ACCESS),
            "key_creates": self._repo.count_audit_events(action=AuditAction.CREATE),
            "key_rotations": self._repo.count_audit_events(action=AuditAction.ROTATE),
            "key_disables": self._repo.count_audit_events(action=AuditAction.DISABLE),
        }


# Singleton instance
_audit_instance = None

def get_vault_audit() -> VaultAudit:
    """Get singleton VaultAudit instance"""
    global _audit_instance
    if _audit_instance is None:
        _audit_instance = VaultAudit()
    return _audit_instance
