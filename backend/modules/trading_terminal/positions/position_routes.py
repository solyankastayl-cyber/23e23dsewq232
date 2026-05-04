"""
Position Routes for Trading Terminal
=====================================

FastAPI routes for position management.

Endpoints:
- GET /api/terminal/positions - List all positions
- GET /api/terminal/positions/open - Open positions only
- GET /api/terminal/positions/history - Closed positions
- GET /api/terminal/positions/{position_id} - Get specific position
- GET /api/terminal/positions/summary/{symbol} - Position summary

Simulation endpoints (dev/testing):
- POST /api/terminal/positions/simulate-open-from-order - Create from order
- POST /api/terminal/positions/{id}/simulate-mark - Update mark price
- POST /api/terminal/positions/{id}/simulate-close - Close position
- POST /api/terminal/positions/{id}/simulate-reduce - Reduce position
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from .position_engine import get_position_engine
from .position_repository import get_position_repository

router = APIRouter(prefix="/api/terminal/positions", tags=["Positions"])


# ---- Pydantic Models ----

class SimulateOpenRequest(BaseModel):
    order: dict
    intent: dict
    market_price: Optional[float] = None


class SimulateMarkRequest(BaseModel):
    mark_price: float


class SimulateCloseRequest(BaseModel):
    close_price: float
    reason: str = "manual_close"


class SimulateReduceRequest(BaseModel):
    reduce_size: float
    reduce_price: float


# ---- Read Endpoints ----

@router.get("/health")
async def positions_health():
    """Health check for positions module"""
    return {
        "ok": True,
        "module": "position_manager",
        "version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("")
async def list_positions(
    symbol: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200)
):
    """List all positions"""
    repo = get_position_repository()
    positions = repo.list_all(symbol=symbol.upper() if symbol else None, limit=limit)
    return {
        "ok": True,
        "count": len(positions),
        "positions": [p.to_dict() for p in positions]
    }


@router.get("/open")
async def list_open_positions(symbol: Optional[str] = None):
    """List only open positions"""
    repo = get_position_repository()
    positions = repo.list_open(symbol=symbol.upper() if symbol else None)
    return {
        "ok": True,
        "count": len(positions),
        "positions": [p.to_dict() for p in positions]
    }


@router.get("/history")
async def list_position_history(
    symbol: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500)
):
    """Get position history (closed positions)"""
    repo = get_position_repository()
    positions = repo.list_history(symbol=symbol.upper() if symbol else None, limit=limit)
    return {
        "ok": True,
        "count": len(positions),
        "positions": [p.to_dict() for p in positions]
    }


@router.get("/summary/{symbol}")
async def get_position_summary(
    symbol: str,
    timeframe: str = Query(default="4H", description="Timeframe: 1H, 4H, or 1D")
):
    """Get position summary for symbol"""
    engine = get_position_engine()
    summary = engine.build_position_summary(symbol.upper(), timeframe.upper())
    return {
        "ok": True,
        **summary
    }


@router.get("/{position_id}")
async def get_position(position_id: str):
    """Get specific position by ID"""
    repo = get_position_repository()
    position = repo.get(position_id)
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    return {
        "ok": True,
        "position": position.to_dict()
    }


# ---- Simulation Endpoints (Dev/Testing) ----

@router.post("/simulate-open-from-order")
async def simulate_open_from_order(request: SimulateOpenRequest):
    """
    Create position from filled order.
    For development and testing.
    """
    engine = get_position_engine()
    
    try:
        position = engine.sync_from_filled_order(
            order=request.order,
            intent=request.intent,
            market_price=request.market_price
        )
        return {
            "ok": True,
            "position": position.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{position_id}/simulate-mark")
async def simulate_mark_update(position_id: str, request: SimulateMarkRequest):
    """
    Update mark price for position.
    For development and testing.
    """
    repo = get_position_repository()
    position = repo.get(position_id)
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    engine = get_position_engine()
    updated = engine.update_mark_price(
        symbol=position.symbol,
        timeframe=position.timeframe,
        mark_price=request.mark_price
    )
    
    if not updated:
        raise HTTPException(status_code=400, detail="Update failed")
    
    return {
        "ok": True,
        "position": updated.to_dict()
    }


@router.post("/{position_id}/simulate-close")
async def simulate_close_position(position_id: str, request: SimulateCloseRequest):
    """
    Close position.
    For development and testing.
    """
    engine = get_position_engine()
    
    try:
        position = engine.close_position(
            position_id=position_id,
            close_price=request.close_price,
            reason=request.reason
        )
        return {
            "ok": True,
            "position": position.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{position_id}/simulate-reduce")
async def simulate_reduce_position(position_id: str, request: SimulateReduceRequest):
    """
    Reduce position size.
    For development and testing.
    """
    engine = get_position_engine()
    
    try:
        position = engine.reduce_position(
            position_id=position_id,
            reduce_size=request.reduce_size,
            reduce_price=request.reduce_price
        )
        return {
            "ok": True,
            "position": position.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
