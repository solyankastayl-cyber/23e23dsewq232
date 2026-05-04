"""
Protection Routes
Sprint A7: TP/SL через app-side watcher
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from modules.positions.protection_repository import ProtectionRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/protection", tags=["protection"])

# DB singleton
_db = None

def init_protection_db(db):
    global _db
    _db = db

def get_protection_repo():
    if _db is None:
        raise RuntimeError("Protection DB not initialized")
    return ProtectionRepository(_db)


class PriceBody(BaseModel):
    price: float


@router.get("/{symbol}")
async def get_protection(symbol: str):
    """
    Get protection rule for symbol.
    
    Returns:
        {tp_price, sl_price, tp_enabled, sl_enabled, status}
    """
    try:
        repo = get_protection_repo()
        rule = await repo.get(symbol)
        
        if not rule:
            return {"ok": True, "protection": None}
        
        return {"ok": True, "protection": rule}
    
    except Exception as e:
        logger.error(f"[ProtectionRoutes] Get protection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{symbol}/tp")
async def set_tp(symbol: str, body: PriceBody):
    """
    Set Take Profit for symbol.
    
    Body:
        {"price": 75000.0}
    
    Returns:
        {"ok": true}
    """
    try:
        repo = get_protection_repo()
        
        # Get existing rule or create new
        existing = await repo.get(symbol)
        
        data = {
            "symbol": symbol,
            "tp_price": body.price,
            "tp_enabled": True,
            "status": "ACTIVE"
        }
        
        # Preserve SL settings if exist
        if existing:
            data["sl_price"] = existing.get("sl_price")
            data["sl_enabled"] = existing.get("sl_enabled", False)
        
        await repo.upsert(symbol, data)
        
        logger.info(f"[ProtectionRoutes] TP set: {symbol} @ {body.price}")
        
        return {"ok": True}
    
    except Exception as e:
        logger.error(f"[ProtectionRoutes] Set TP failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{symbol}/sl")
async def set_sl(symbol: str, body: PriceBody):
    """
    Set Stop Loss for symbol.
    
    Body:
        {"price": 68000.0}
    
    Returns:
        {"ok": true}
    """
    try:
        repo = get_protection_repo()
        
        # Get existing rule or create new
        existing = await repo.get(symbol)
        
        data = {
            "symbol": symbol,
            "sl_price": body.price,
            "sl_enabled": True,
            "status": "ACTIVE"
        }
        
        # Preserve TP settings if exist
        if existing:
            data["tp_price"] = existing.get("tp_price")
            data["tp_enabled"] = existing.get("tp_enabled", False)
        
        await repo.upsert(symbol, data)
        
        logger.info(f"[ProtectionRoutes] SL set: {symbol} @ {body.price}")
        
        return {"ok": True}
    
    except Exception as e:
        logger.error(f"[ProtectionRoutes] Set SL failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{symbol}/cancel")
async def cancel_protection(symbol: str):
    """
    Cancel all TP/SL for symbol.
    
    Returns:
        {"ok": true}
    """
    try:
        repo = get_protection_repo()
        await repo.disable(symbol)
        
        logger.info(f"[ProtectionRoutes] Protection cancelled: {symbol}")
        
        return {"ok": True}
    
    except Exception as e:
        logger.error(f"[ProtectionRoutes] Cancel protection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
