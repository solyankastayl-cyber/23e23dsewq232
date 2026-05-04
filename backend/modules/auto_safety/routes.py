"""
Auto Safety Routes
==================
Sprint A4: Operator control panel API
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .service_locator import get_auto_safety_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auto-safety", tags=["auto_safety"])


class ConfigUpdateRequest(BaseModel):
    """Request to update auto safety config"""
    enabled: bool | None = None
    auto_mode_enabled: bool | None = None
    max_trades_per_hour: int | None = None
    max_concurrent_positions: int | None = None
    max_capital_deployed_pct: float | None = None
    max_single_trade_notional_pct: float | None = None
    daily_loss_limit_usd: float | None = None
    max_consecutive_losses: int | None = None
    allowed_symbols: list[str] | None = None


@router.get("/config")
async def get_config():
    """
    Get current auto safety config
    
    Returns:
        {"ok": true, "config": {...}}
    """
    try:
        service = get_auto_safety_service()
        config = await service.get_config()
        return {"ok": True, "config": config}
    except Exception as e:
        logger.error(f"[AutoSafety] Get config failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def update_config(request: ConfigUpdateRequest):
    """
    Update auto safety config (operator override)
    
    Body:
        {"auto_mode_enabled": true, "allowed_symbols": ["BTCUSDT"]}
    
    Returns:
        {"ok": true, "config": {...}}
    """
    try:
        service = get_auto_safety_service()
        
        # Build patch dict (only include non-None fields)
        patch = {}
        if request.enabled is not None:
            patch["enabled"] = request.enabled
        if request.auto_mode_enabled is not None:
            patch["auto_mode_enabled"] = request.auto_mode_enabled
        if request.max_trades_per_hour is not None:
            patch["max_trades_per_hour"] = request.max_trades_per_hour
        if request.max_concurrent_positions is not None:
            patch["max_concurrent_positions"] = request.max_concurrent_positions
        if request.max_capital_deployed_pct is not None:
            patch["max_capital_deployed_pct"] = request.max_capital_deployed_pct
        if request.max_single_trade_notional_pct is not None:
            patch["max_single_trade_notional_pct"] = request.max_single_trade_notional_pct
        if request.daily_loss_limit_usd is not None:
            patch["daily_loss_limit_usd"] = request.daily_loss_limit_usd
        if request.max_consecutive_losses is not None:
            patch["max_consecutive_losses"] = request.max_consecutive_losses
        if request.allowed_symbols is not None:
            patch["allowed_symbols"] = request.allowed_symbols
        
        config = await service.update_config(patch)
        
        logger.info(f"[AutoSafety] Config updated: {patch}")
        
        return {"ok": True, "config": config}
    except Exception as e:
        logger.error(f"[AutoSafety] Update config failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state")
async def get_state():
    """
    Get current auto safety state
    
    Returns:
        {"ok": true, "state": {...}}
    """
    try:
        service = get_auto_safety_service()
        state = await service.get_state()
        return {"ok": True, "state": state}
    except Exception as e:
        logger.error(f"[AutoSafety] Get state failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-hourly-counters")
async def reset_hourly_counters():
    """
    Manually reset hourly counters (for testing)
    
    Returns:
        {"ok": true}
    """
    try:
        service = get_auto_safety_service()
        await service.reset_hourly_counters()
        return {"ok": True}
    except Exception as e:
        logger.error(f"[AutoSafety] Reset hourly counters failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
