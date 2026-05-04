"""
PHASE 25.2 — Asset Fractal Routes

API endpoints for unified asset fractal contexts.
"""

from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime, timezone

from .asset_fractal_service import get_asset_fractal_service
from .asset_fractal_types import MultiAssetFractalContext


router = APIRouter(prefix="/api/v1/fractal-assets", tags=["fractal-assets"])


@router.get("/context", response_model=Dict[str, Any])
async def get_all_asset_contexts():
    """
    Get unified fractal context for all assets (BTC, SPX, DXY).
    
    Returns AssetFractalContext for each asset in a unified format.
    """
    service = get_asset_fractal_service()
    
    contexts = await service.get_all_contexts()
    
    return {
        "status": "ok",
        "btc": contexts.btc.model_dump(),
        "spx": contexts.spx.model_dump(),
        "dxy": contexts.dxy.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/btc", response_model=Dict[str, Any])
async def get_btc_context():
    """Get BTC fractal context."""
    service = get_asset_fractal_service()
    ctx = await service.get_btc_context()
    
    return {
        "status": "ok",
        "data": ctx.model_dump(),
    }


@router.get("/spx", response_model=Dict[str, Any])
async def get_spx_context():
    """Get SPX fractal context."""
    service = get_asset_fractal_service()
    ctx = await service.get_spx_context()
    
    return {
        "status": "ok",
        "data": ctx.model_dump(),
    }


@router.get("/dxy", response_model=Dict[str, Any])
async def get_dxy_context():
    """Get DXY fractal context."""
    service = get_asset_fractal_service()
    ctx = await service.get_dxy_context()
    
    return {
        "status": "ok",
        "data": ctx.model_dump(),
    }


@router.get("/health", response_model=Dict[str, Any])
async def get_asset_fractal_health():
    """Get health status of asset fractal service."""
    service = get_asset_fractal_service()
    
    # Fetch all to update health
    await service.get_all_contexts()
    
    health = service.get_health()
    
    return {
        "status": health.status,
        "btc_available": health.btc_available,
        "spx_available": health.spx_available,
        "dxy_available": health.dxy_available,
        "last_update": health.last_update.isoformat() if health.last_update else None,
    }


@router.get("/summary", response_model=Dict[str, Any])
async def get_summary():
    """Get compact summary of all asset fractal contexts."""
    service = get_asset_fractal_service()
    contexts = await service.get_all_contexts()
    
    def summarize(ctx):
        return {
            "direction": ctx.direction,
            "confidence": ctx.confidence,
            "strength": ctx.strength,
            "context_state": ctx.context_state,
        }
    
    return {
        "btc": summarize(contexts.btc),
        "spx": summarize(contexts.spx),
        "dxy": summarize(contexts.dxy),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
