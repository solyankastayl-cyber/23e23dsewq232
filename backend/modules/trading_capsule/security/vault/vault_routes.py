"""
SEC2 - Vault API Routes
REST API for API Key Vault operations.
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Request

from .vault_types import (
    KeyPermission,
    KeyStatus,
    AuditAction,
    CreateKeyRequest,
    KeyResponse,
    AccessTokenRequest,
    AccessTokenResponse,
    RotateKeyRequest,
    UpdatePermissionsRequest,
    VaultHealthResponse
)
from .vault_service import get_vault_service
from .vault_audit import get_vault_audit


router = APIRouter(prefix="/api/vault", tags=["SEC2 - API Key Vault"])


# ===========================================
# Health & Status
# ===========================================

@router.get("/health")
async def vault_health():
    """Get vault health status"""
    service = get_vault_service()
    return service.get_health()


@router.get("/stats")
async def vault_stats():
    """Get vault statistics"""
    service = get_vault_service()
    return service.get_stats()


# ===========================================
# Key Management
# ===========================================

@router.post("/keys", response_model=KeyResponse)
async def create_key(request: CreateKeyRequest):
    """
    Create a new API key.
    
    The API key and secret are encrypted before storage.
    Secret is NEVER returned via API.
    """
    try:
        service = get_vault_service()
        return service.create_key(request, requesting_service="api")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create key: {str(e)}")


@router.get("/keys", response_model=List[KeyResponse])
async def list_keys(
    status: Optional[str] = Query(None, description="Filter by status"),
    exchange: Optional[str] = Query(None, description="Filter by exchange")
):
    """
    List all API keys.
    
    Returns masked key info (secrets never returned).
    """
    service = get_vault_service()
    
    key_status = None
    if status:
        try:
            key_status = KeyStatus(status.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    return service.get_all_keys(status=key_status, exchange=exchange)


@router.get("/keys/{key_id}", response_model=KeyResponse)
async def get_key(key_id: str):
    """Get a specific API key by ID"""
    service = get_vault_service()
    key = service.get_key(key_id)
    
    if not key:
        raise HTTPException(status_code=404, detail=f"Key {key_id} not found")
    
    return key


@router.delete("/keys/{key_id}")
async def delete_key(
    key_id: str,
    reason: Optional[str] = Query(None, description="Reason for deletion")
):
    """Delete an API key"""
    service = get_vault_service()
    result = service.delete_key(key_id, reason=reason, requesting_service="api")
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Key {key_id} not found")
    
    return {"success": True, "message": f"Key {key_id} deleted"}


# ===========================================
# Key Lifecycle
# ===========================================

@router.post("/keys/{key_id}/rotate", response_model=KeyResponse)
async def rotate_key(key_id: str, request: RotateKeyRequest):
    """
    Rotate an API key with new credentials.
    
    The old key is marked as ROTATED and a new key is created.
    """
    try:
        service = get_vault_service()
        return service.rotate_key(key_id, request, requesting_service="api")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rotate key: {str(e)}")


@router.post("/keys/{key_id}/disable")
async def disable_key(
    key_id: str,
    reason: Optional[str] = Query(None, description="Reason for disabling")
):
    """Disable an API key"""
    service = get_vault_service()
    result = service.disable_key(key_id, reason=reason, requesting_service="api")
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Key {key_id} not found")
    
    return {"success": True, "message": f"Key {key_id} disabled"}


@router.post("/keys/{key_id}/enable")
async def enable_key(key_id: str):
    """Enable a disabled API key"""
    service = get_vault_service()
    result = service.enable_key(key_id, requesting_service="api")
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Key {key_id} not found or not disabled")
    
    return {"success": True, "message": f"Key {key_id} enabled"}


# ===========================================
# Permissions
# ===========================================

@router.put("/keys/{key_id}/permissions", response_model=KeyResponse)
async def update_permissions(key_id: str, request: UpdatePermissionsRequest):
    """Update permissions for an API key"""
    try:
        service = get_vault_service()
        result = service.update_permissions(key_id, request, requesting_service="api")
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Key {key_id} not found")
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===========================================
# Access Tokens
# ===========================================

@router.post("/access-token", response_model=AccessTokenResponse)
async def request_access_token(request: AccessTokenRequest, req: Request):
    """
    Request an access token for an API key.
    
    The token provides temporary access to the decrypted credentials.
    Tokens are short-lived (default 5 minutes, max 1 hour).
    
    Note: This endpoint is primarily for internal service use.
    The actual credentials are delivered through the token, not via API response.
    """
    service = get_vault_service()
    
    # Get client IP for audit
    ip_address = req.client.host if req.client else None
    
    token, error = service.get_access_token(request, ip_address=ip_address)
    
    if error:
        raise HTTPException(status_code=403, detail=error)
    
    # Return token metadata (not the actual credentials)
    return AccessTokenResponse(
        token_id=token.token_id,
        key_id=token.key_id,
        scope=token.scope,
        expires_at=token.expires_at
    )


@router.delete("/access-token/{token_id}")
async def revoke_access_token(token_id: str):
    """Revoke an access token"""
    service = get_vault_service()
    result = service.revoke_token(token_id)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Token {token_id} not found or expired")
    
    return {"success": True, "message": f"Token {token_id} revoked"}


@router.post("/cleanup-tokens")
async def cleanup_expired_tokens():
    """Clean up expired access tokens"""
    service = get_vault_service()
    count = service.cleanup_expired_tokens()
    
    return {"success": True, "cleaned_up": count}


# ===========================================
# Internal Token Retrieval (for services)
# ===========================================

@router.get("/internal/token/{token_id}")
async def get_token_credentials(token_id: str, req: Request):
    """
    Get credentials from an access token.
    
    INTERNAL USE ONLY - should be called by broker adapters and execution engine.
    
    Security:
    - Only valid, non-expired tokens return credentials
    - Credentials are only in memory, never persisted
    """
    service = get_vault_service()
    token = service.validate_token(token_id)
    
    if not token:
        raise HTTPException(status_code=404, detail="Token not found, expired, or revoked")
    
    return {
        "key_id": token.key_id,
        "api_key": token.api_key,
        "secret_key": token.secret_key,
        "passphrase": token.passphrase,
        "scope": token.scope,
        "expires_at": token.expires_at.isoformat()
    }


# ===========================================
# Audit
# ===========================================

@router.get("/audit")
async def get_audit_events(
    key_id: Optional[str] = Query(None, description="Filter by key ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    limit: int = Query(100, ge=1, le=500, description="Max events to return")
):
    """Get audit events"""
    audit = get_vault_audit()
    
    audit_action = None
    if action:
        try:
            audit_action = AuditAction(action.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
    
    events = audit.get_recent_events(action=audit_action, limit=limit)
    
    if key_id:
        events = [e for e in events if e.key_id == key_id]
    
    return {
        "events": [e.dict() for e in events],
        "count": len(events)
    }


@router.get("/audit/failed-access")
async def get_failed_access_attempts(
    limit: int = Query(20, ge=1, le=100)
):
    """Get recent failed access attempts (security monitoring)"""
    audit = get_vault_audit()
    events = audit.get_failed_access_attempts(limit=limit)
    
    return {
        "events": [e.dict() for e in events],
        "count": len(events)
    }


@router.get("/audit/summary")
async def get_audit_summary():
    """Get audit summary statistics"""
    audit = get_vault_audit()
    return audit.get_audit_summary()


@router.get("/audit/{key_id}")
async def get_key_audit_history(
    key_id: str,
    limit: int = Query(50, ge=1, le=200)
):
    """Get audit history for a specific key"""
    audit = get_vault_audit()
    events = audit.get_key_history(key_id, limit=limit)
    
    return {
        "key_id": key_id,
        "events": [e.dict() for e in events],
        "count": len(events)
    }
