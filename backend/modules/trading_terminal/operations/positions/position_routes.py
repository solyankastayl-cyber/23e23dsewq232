"""
OPS1 Position Routes
====================

API endpoints for deep position monitoring.
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .position_service import position_service
from .position_types import PositionStatus


router = APIRouter(prefix="/api/ops/positions", tags=["ops-positions"])


# ===========================================
# Request Models
# ===========================================

class RegisterPositionRequest(BaseModel):
    """Request to register a position"""
    positionId: Optional[str] = None
    exchange: str = Field(..., description="Exchange name")
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="LONG or SHORT")
    quantity: float = Field(..., description="Position size")
    entryPrice: float = Field(..., description="Entry price")
    markPrice: Optional[float] = None
    leverage: Optional[float] = None
    marginMode: Optional[str] = None
    stopLoss: Optional[float] = None
    takeProfit: Optional[float] = None
    strategyId: Optional[str] = None
    profileId: Optional[str] = None
    configId: Optional[str] = None


class UpdatePositionRequest(BaseModel):
    """Request to update a position"""
    markPrice: Optional[float] = None
    quantity: Optional[float] = None
    stopLoss: Optional[float] = None
    takeProfit: Optional[float] = None
    realizedPnl: Optional[float] = None


class ClosePositionRequest(BaseModel):
    """Request to close a position"""
    exitPrice: float = Field(..., description="Exit price")
    realizedPnl: float = Field(..., description="Realized PnL")


# ===========================================
# Health
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for OPS1"""
    return position_service.get_health()


# ===========================================
# Position Management
# ===========================================

@router.post("")
async def register_position(request: RegisterPositionRequest):
    """
    Register a new position.
    
    Enriches with ownership, risk, and event data.
    """
    raw = {
        "position_id": request.positionId or f"pos_{int(time.time()*1000)}",
        "exchange": request.exchange,
        "symbol": request.symbol.upper(),
        "side": request.side.upper(),
        "quantity": request.quantity,
        "entry_price": request.entryPrice,
        "mark_price": request.markPrice or request.entryPrice,
        "leverage": request.leverage,
        "margin_mode": request.marginMode,
        "stop_loss": request.stopLoss,
        "take_profit": request.takeProfit,
        "strategy_id": request.strategyId,
        "profile_id": request.profileId,
        "config_id": request.configId,
        "opened_at": int(time.time() * 1000)
    }
    
    position = position_service.register_position(raw)
    
    return {
        "success": True,
        "position": position.to_dict()
    }


@router.put("/{position_id}")
async def update_position(position_id: str, request: UpdatePositionRequest):
    """Update an existing position"""
    
    updates = {}
    if request.markPrice is not None:
        updates["mark_price"] = request.markPrice
    if request.quantity is not None:
        updates["quantity"] = request.quantity
    if request.stopLoss is not None:
        updates["stop_loss"] = request.stopLoss
    if request.takeProfit is not None:
        updates["take_profit"] = request.takeProfit
    if request.realizedPnl is not None:
        updates["realized_pnl"] = request.realizedPnl
    
    position = position_service.update_position(position_id, updates)
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    return {
        "success": True,
        "position": position.to_dict()
    }


@router.post("/{position_id}/close")
async def close_position(position_id: str, request: ClosePositionRequest):
    """Close a position"""
    
    position = position_service.close_position(
        position_id,
        request.exitPrice,
        request.realizedPnl
    )
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    return {
        "success": True,
        "position": position.to_dict()
    }


# ===========================================
# Query Endpoints
# ===========================================

@router.get("")
async def get_all_positions(include_closed: bool = Query(False)):
    """Get all positions"""
    positions = position_service.get_all_positions(include_closed)
    return {
        "positions": [p.to_dict() for p in positions],
        "count": len(positions)
    }


@router.get("/summary")
async def get_summary():
    """Get aggregated position summary"""
    summary = position_service.get_summary()
    return summary.to_dict()


@router.get("/{position_id}")
async def get_position(position_id: str):
    """Get position by ID"""
    position = position_service.get_position(position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    return position.to_dict()


@router.get("/{position_id}/risk")
async def get_position_risk(position_id: str):
    """Get risk view for position"""
    risk = position_service.get_position_risk(position_id)
    if not risk:
        raise HTTPException(status_code=404, detail="Position not found")
    return risk.to_dict()


@router.get("/{position_id}/owner")
async def get_position_ownership(position_id: str):
    """Get ownership info for position"""
    ownership = position_service.get_position_ownership(position_id)
    if not ownership:
        raise HTTPException(status_code=404, detail="Position not found or no ownership data")
    return ownership.to_dict()


# ===========================================
# Filter Endpoints
# ===========================================

@router.get("/symbol/{symbol}")
async def get_by_symbol(symbol: str, include_closed: bool = Query(False)):
    """Get positions by symbol"""
    positions = position_service.get_by_symbol(symbol, include_closed)
    return {
        "symbol": symbol.upper(),
        "positions": [p.to_dict() for p in positions],
        "count": len(positions)
    }


@router.get("/exchange/{exchange}")
async def get_by_exchange(exchange: str, include_closed: bool = Query(False)):
    """Get positions by exchange"""
    positions = position_service.get_by_exchange(exchange, include_closed)
    return {
        "exchange": exchange.upper(),
        "positions": [p.to_dict() for p in positions],
        "count": len(positions)
    }


@router.get("/strategy/{strategy_id}")
async def get_by_strategy(strategy_id: str, include_closed: bool = Query(False)):
    """Get positions by strategy"""
    positions = position_service.get_by_strategy(strategy_id, include_closed)
    return {
        "strategyId": strategy_id,
        "positions": [p.to_dict() for p in positions],
        "count": len(positions)
    }


@router.get("/profile/{profile_id}")
async def get_by_profile(profile_id: str, include_closed: bool = Query(False)):
    """Get positions by profile"""
    positions = position_service.get_by_profile(profile_id, include_closed)
    return {
        "profileId": profile_id,
        "positions": [p.to_dict() for p in positions],
        "count": len(positions)
    }


@router.get("/status/{status}")
async def get_by_status(status: str):
    """Get positions by status"""
    positions = position_service.get_by_status(status.upper())
    return {
        "status": status.upper(),
        "positions": [p.to_dict() for p in positions],
        "count": len(positions)
    }


# ===========================================
# Risk Endpoints
# ===========================================

@router.get("/risk/high")
async def get_high_risk_positions(min_level: str = Query("HIGH")):
    """Get positions with high risk"""
    positions = position_service.get_high_risk_positions(min_level.upper())
    return {
        "minLevel": min_level.upper(),
        "positions": [p.to_dict() for p in positions],
        "count": len(positions)
    }
