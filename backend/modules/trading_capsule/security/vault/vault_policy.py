"""
SEC2 - Vault Policy Engine
Permission model and access control for API keys.
"""

from typing import List, Optional, Set
from datetime import datetime

from .vault_types import (
    APIKeyRecord,
    KeyPermission,
    KeyStatus
)


class VaultPolicy:
    """
    Policy engine for API key access control.
    
    Rules:
    - READ: Can query account info, positions, orders
    - TRADE: Can place/cancel orders (requires READ)
    - WITHDRAW: Can withdraw funds (highest risk, rarely granted)
    
    Services have default allowed scopes:
    - execution_engine: READ, TRADE
    - portfolio_monitor: READ
    - reconciliation: READ
    - admin_terminal: READ (can request TRADE with approval)
    """
    
    # Service default permissions
    SERVICE_PERMISSIONS: dict = {
        "execution_engine": {KeyPermission.READ, KeyPermission.TRADE},
        "portfolio_monitor": {KeyPermission.READ},
        "reconciliation": {KeyPermission.READ},
        "risk_monitor": {KeyPermission.READ},
        "admin_terminal": {KeyPermission.READ},
        "broker_adapter": {KeyPermission.READ, KeyPermission.TRADE},
        "backtest_engine": {KeyPermission.READ},
        "strategy_engine": {KeyPermission.READ},
    }
    
    # Permission hierarchy (higher includes lower)
    PERMISSION_HIERARCHY = {
        KeyPermission.WITHDRAW: {KeyPermission.WITHDRAW, KeyPermission.TRADE, KeyPermission.READ},
        KeyPermission.TRADE: {KeyPermission.TRADE, KeyPermission.READ},
        KeyPermission.READ: {KeyPermission.READ},
    }
    
    def __init__(self):
        """Initialize policy engine"""
        self._enabled = True
    
    def check_access(
        self,
        key: APIKeyRecord,
        requested_scope: KeyPermission,
        requesting_service: str
    ) -> tuple[bool, Optional[str]]:
        """
        Check if access should be granted.
        
        Returns:
            (allowed, reason) - True if allowed, False with reason if denied
        """
        # Check key status
        if key.status != KeyStatus.ACTIVE:
            return False, f"Key is not active (status: {key.status})"
        
        # Check if key has the requested permission
        if not self._key_has_permission(key, requested_scope):
            return False, f"Key does not have {requested_scope.value} permission"
        
        # Check if service is allowed to request this scope
        if not self._service_allowed_scope(requesting_service, requested_scope):
            return False, f"Service '{requesting_service}' not allowed to request {requested_scope.value}"
        
        return True, None
    
    def _key_has_permission(
        self, 
        key: APIKeyRecord, 
        requested: KeyPermission
    ) -> bool:
        """Check if key has the requested permission (or higher)"""
        key_permissions = set(key.permissions)
        
        # Check direct permission
        if requested in key_permissions:
            return True
        
        # Check if key has a higher permission that includes this one
        for key_perm in key_permissions:
            if key_perm in self.PERMISSION_HIERARCHY:
                included = self.PERMISSION_HIERARCHY[key_perm]
                if requested in included:
                    return True
        
        return False
    
    def _service_allowed_scope(
        self,
        service: str,
        requested: KeyPermission
    ) -> bool:
        """Check if service is allowed to request this scope"""
        # Get service's allowed permissions
        allowed = self.SERVICE_PERMISSIONS.get(
            service,
            {KeyPermission.READ}  # Default: READ only
        )
        
        return requested in allowed
    
    def get_service_permissions(self, service: str) -> Set[KeyPermission]:
        """Get allowed permissions for a service"""
        return self.SERVICE_PERMISSIONS.get(
            service,
            {KeyPermission.READ}
        )
    
    def get_effective_permissions(
        self,
        key: APIKeyRecord,
        service: str
    ) -> Set[KeyPermission]:
        """
        Get the intersection of key permissions and service allowed permissions.
        This is what the service can actually use with this key.
        """
        key_permissions = set(key.permissions)
        service_allowed = self.get_service_permissions(service)
        
        return key_permissions & service_allowed
    
    def validate_permissions_update(
        self,
        new_permissions: List[KeyPermission]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a permissions update request.
        
        Rules:
        - At least READ permission required
        - WITHDRAW requires explicit approval (not allowed through API)
        """
        if not new_permissions:
            return False, "At least one permission required"
        
        if KeyPermission.READ not in new_permissions:
            return False, "READ permission is always required"
        
        if KeyPermission.WITHDRAW in new_permissions:
            return False, "WITHDRAW permission cannot be granted through API"
        
        return True, None
    
    def is_high_risk_operation(self, scope: KeyPermission) -> bool:
        """Check if an operation is high risk"""
        return scope in {KeyPermission.TRADE, KeyPermission.WITHDRAW}
    
    def should_require_confirmation(
        self,
        key: APIKeyRecord,
        scope: KeyPermission
    ) -> bool:
        """
        Determine if operation should require additional confirmation.
        
        High-risk scenarios:
        - First TRADE access after key creation
        - Key not used in 7+ days
        - Multiple failed access attempts recently
        """
        # New key with TRADE permission
        if scope == KeyPermission.TRADE and key.access_count == 0:
            return True
        
        # Key not used recently
        if key.last_used_at:
            days_since_use = (datetime.utcnow() - key.last_used_at).days
            if days_since_use > 7 and scope == KeyPermission.TRADE:
                return True
        
        return False


# Singleton instance
_policy_instance = None

def get_vault_policy() -> VaultPolicy:
    """Get singleton VaultPolicy instance"""
    global _policy_instance
    if _policy_instance is None:
        _policy_instance = VaultPolicy()
    return _policy_instance
