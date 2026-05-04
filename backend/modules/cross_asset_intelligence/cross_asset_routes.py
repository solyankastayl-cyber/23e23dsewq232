"""
PHASE 25.3 — Cross-Asset Routes

API endpoints for cross-asset intelligence.
"""

from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime, timezone

from .cross_asset_engine import get_cross_asset_engine
from .cross_asset_types import CrossAssetAlignment, CrossAssetSummary

from modules.macro_context.macro_context_engine import get_macro_context_engine
from modules.macro_context.macro_context_adapter import get_macro_adapter
from modules.fractal_intelligence.asset_fractal_service import get_asset_fractal_service


router = APIRouter(prefix="/api/v1/cross-asset", tags=["cross-asset"])


async def _get_current_contexts():
    """Get current macro and fractal contexts."""
    macro_engine = get_macro_context_engine()
    macro_adapter = get_macro_adapter()
    fractal_service = get_asset_fractal_service()
    
    # Build macro context with some default inputs if not set
    # In production, these would come from real data
    macro_input = macro_adapter.create_manual_input(
        inflation=0.3,
        rates=0.4,
        labor=0.3,
        growth=0.2,
        liquidity=0.2,
    )
    macro = macro_engine.build_context(macro_input)
    
    # Get fractal contexts
    fractals = await fractal_service.get_all_contexts_with_macro_fallback(
        macro_usd_bias=macro.usd_bias,
        macro_confidence=macro.confidence,
    )
    
    return macro, fractals


@router.get("/alignment", response_model=Dict[str, Any])
async def get_alignment():
    """
    Get full cross-asset alignment.
    
    Returns complete CrossAssetAlignment with all bridges.
    """
    engine = get_cross_asset_engine()
    macro, fractals = await _get_current_contexts()
    
    alignment = engine.compute_alignment(
        macro=macro,
        dxy=fractals.dxy,
        spx=fractals.spx,
        btc=fractals.btc,
    )
    
    return {
        "status": "ok",
        "data": alignment.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/summary", response_model=Dict[str, Any])
async def get_summary():
    """Get compact summary of cross-asset alignment."""
    engine = get_cross_asset_engine()
    macro, fractals = await _get_current_contexts()
    
    alignment = engine.compute_alignment(
        macro=macro,
        dxy=fractals.dxy,
        spx=fractals.spx,
        btc=fractals.btc,
    )
    
    summary = engine.get_summary(alignment)
    
    return summary.model_dump()


@router.get("/bridges", response_model=Dict[str, Any])
async def get_all_bridges():
    """Get all three bridges."""
    engine = get_cross_asset_engine()
    macro, fractals = await _get_current_contexts()
    
    alignment = engine.compute_alignment(
        macro=macro,
        dxy=fractals.dxy,
        spx=fractals.spx,
        btc=fractals.btc,
    )
    
    return {
        "macro_dxy": alignment.macro_dxy.model_dump(),
        "dxy_spx": alignment.dxy_spx.model_dump(),
        "spx_btc": alignment.spx_btc.model_dump(),
    }


@router.get("/bridges/macro-dxy", response_model=Dict[str, Any])
async def get_macro_dxy_bridge():
    """Get Macro → DXY bridge."""
    engine = get_cross_asset_engine()
    macro, fractals = await _get_current_contexts()
    
    alignment = engine.compute_alignment(
        macro=macro,
        dxy=fractals.dxy,
        spx=fractals.spx,
        btc=fractals.btc,
    )
    
    return {
        "status": "ok",
        "data": alignment.macro_dxy.model_dump(),
    }


@router.get("/bridges/dxy-spx", response_model=Dict[str, Any])
async def get_dxy_spx_bridge():
    """Get DXY → SPX bridge."""
    engine = get_cross_asset_engine()
    macro, fractals = await _get_current_contexts()
    
    alignment = engine.compute_alignment(
        macro=macro,
        dxy=fractals.dxy,
        spx=fractals.spx,
        btc=fractals.btc,
    )
    
    return {
        "status": "ok",
        "data": alignment.dxy_spx.model_dump(),
    }


@router.get("/bridges/spx-btc", response_model=Dict[str, Any])
async def get_spx_btc_bridge():
    """Get SPX → BTC bridge."""
    engine = get_cross_asset_engine()
    macro, fractals = await _get_current_contexts()
    
    alignment = engine.compute_alignment(
        macro=macro,
        dxy=fractals.dxy,
        spx=fractals.spx,
        btc=fractals.btc,
    )
    
    return {
        "status": "ok",
        "data": alignment.spx_btc.model_dump(),
    }


@router.get("/health", response_model=Dict[str, Any])
async def get_health():
    """Get health status of cross-asset module."""
    engine = get_cross_asset_engine()
    
    # Compute alignment to update state
    try:
        macro, fractals = await _get_current_contexts()
        engine.compute_alignment(
            macro=macro,
            dxy=fractals.dxy,
            spx=fractals.spx,
            btc=fractals.btc,
        )
    except Exception:
        pass
    
    health = engine.get_health()
    
    return {
        "status": health.status,
        "macro_available": health.macro_available,
        "dxy_available": health.dxy_available,
        "spx_available": health.spx_available,
        "btc_available": health.btc_available,
        "bridges_computed": health.bridges_computed,
        "last_update": health.last_update.isoformat() if health.last_update else None,
    }
