"""
Account Routes (TR1)
====================

API endpoints for Account/Key Manager.

Endpoints:
- GET    /api/accounts              - List all connections
- POST   /api/accounts              - Create connection
- GET    /api/accounts/{id}         - Get connection
- DELETE /api/accounts/{id}         - Delete connection
- POST   /api/accounts/{id}/validate - Validate keys
- GET    /api/accounts/{id}/state   - Get account state
- GET    /api/accounts/{id}/health  - Health check
- POST   /api/accounts/{id}/enable  - Enable connection
- POST   /api/accounts/{id}/disable - Disable connection
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from .account_service import account_service
from .account_health_service import account_health_service


# ===========================================
# Router
# ===========================================

router = APIRouter(prefix="/api/accounts", tags=["TR1 - Account Manager"])


# ===========================================
# Request Models
# ===========================================

class CreateConnectionRequest(BaseModel):
    exchange: str = Field(..., description="Exchange: BINANCE, BYBIT, HYPERLIQUID, COINBASE, OKX, MOCK")
    label: str = Field(..., description="Connection label")
    api_key: str = Field(..., description="API key")
    api_secret: str = Field(..., description="API secret")
    passphrase: str = Field(default="", description="Passphrase (for some exchanges)")
    is_testnet: bool = Field(default=False, description="Use testnet")
    description: str = Field(default="", description="Description")


# ===========================================
# Health
# ===========================================

@router.get("/health")
async def get_service_health():
    """Get TR1 module health"""
    return {
        "module": "Account Manager",
        "phase": "TR1",
        "services": {
            "account_service": account_service.get_health(),
            "health_service": account_health_service.get_service_health()
        }
    }


# ===========================================
# Connections CRUD
# ===========================================

@router.get("")
async def list_connections():
    """List all exchange connections"""
    connections = account_service.get_all_connections()
    summary = account_service.get_accounts_summary()
    
    return {
        "connections": [c.to_dict() for c in connections],
        "count": len(connections),
        "summary": summary
    }


@router.post("")
async def create_connection(request: CreateConnectionRequest):
    """Create a new exchange connection"""
    result = account_service.create_connection(
        exchange=request.exchange,
        label=request.label,
        api_key=request.api_key,
        api_secret=request.api_secret,
        passphrase=request.passphrase,
        is_testnet=request.is_testnet,
        description=request.description
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/{connection_id}")
async def get_connection(connection_id: str):
    """Get specific connection"""
    conn = account_service.get_connection(connection_id)
    
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    return conn.to_dict()


@router.delete("/{connection_id}")
async def delete_connection(connection_id: str):
    """Delete a connection"""
    result = account_service.delete_connection(connection_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    
    return result


# ===========================================
# Validation
# ===========================================

@router.post("/{connection_id}/validate")
async def validate_connection(connection_id: str):
    """Validate connection API keys"""
    result = account_service.validate_connection(connection_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    
    return result


# ===========================================
# Account State
# ===========================================

@router.get("/{connection_id}/state")
async def get_account_state(connection_id: str, refresh: bool = False):
    """Get account state (balances, positions)"""
    state = account_service.get_account_state(connection_id, force_refresh=refresh)
    
    if not state:
        raise HTTPException(status_code=404, detail="Unable to fetch account state")
    
    return state.to_dict()


# ===========================================
# Health Check
# ===========================================

@router.get("/{connection_id}/health")
async def get_connection_health(connection_id: str):
    """Get connection health status"""
    health = account_health_service.check_health(connection_id)
    return health.to_dict()


@router.get("/health/all")
async def get_all_connections_health():
    """Get health of all connections"""
    results = account_health_service.check_all_health()
    summary = account_health_service.get_health_summary()
    
    return {
        "health_checks": [h.to_dict() for h in results],
        "summary": summary
    }


# ===========================================
# Enable / Disable
# ===========================================

@router.post("/{connection_id}/enable")
async def enable_connection(connection_id: str):
    """Enable a connection"""
    result = account_service.enable_connection(connection_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    
    return result


@router.post("/{connection_id}/disable")
async def disable_connection(connection_id: str):
    """Disable a connection"""
    result = account_service.disable_connection(connection_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    
    return result


# ===========================================
# Summary
# ===========================================

@router.get("/summary/all")
async def get_accounts_summary():
    """Get accounts summary"""
    return account_service.get_accounts_summary()
