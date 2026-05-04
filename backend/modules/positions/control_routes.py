"""
Position Control Routes
Sprint A6: API endpoints for manual position control
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from modules.positions.control_service_locator import get_position_control_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/control", tags=["position-control"])


class ReduceBody(BaseModel):
    percent: float


@router.post("/{symbol}/reduce")
async def reduce_position(symbol: str, body: ReduceBody):
    """
    Reduce position by percentage.
    
    Body:
        {"percent": 25 | 50 | 100}
    
    Returns:
        {"ok": true, "reduced_qty": float, "exchange_order_id": str}
    """
    try:
        service = get_position_control_service()
        result = await service.reduce_position(symbol, body.percent)
        
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"[A6] Reduce position failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{symbol}/reverse")
async def reverse_position(symbol: str):
    """
    Reverse position (close current → open opposite).
    
    CRITICAL: Invalidates current TP/SL protection.
    
    Returns:
        {"ok": true, "closed": dict, "opened": dict}
    """
    try:
        service = get_position_control_service()
        result = await service.reverse_position(symbol)
        
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"[A6] Reverse position failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flatten-all")
async def flatten_all():
    """
    Close all open positions (PANIC BUTTON).
    
    Returns:
        {"ok": true, "count": int, "results": list}
    """
    try:
        service = get_position_control_service()
        result = await service.flatten_all()
        
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"[A6] Flatten all failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
