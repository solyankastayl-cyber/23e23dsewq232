"""
PHASE 25.4 — Macro-Fractal Brain Routes

API endpoints for unified macro-fractal intelligence.
"""

from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime, timezone

from .macro_fractal_engine import get_macro_fractal_engine
from .macro_fractal_types import MacroFractalContext

from modules.macro_context.macro_context_engine import get_macro_context_engine
from modules.macro_context.macro_context_adapter import get_macro_adapter
from modules.fractal_intelligence.asset_fractal_service import get_asset_fractal_service
from modules.cross_asset_intelligence.cross_asset_engine import get_cross_asset_engine


router = APIRouter(prefix="/api/v1/macro-fractal", tags=["macro-fractal"])


async def _get_all_inputs():
    """Get all inputs for macro-fractal brain."""
    # Macro context
    macro_engine = get_macro_context_engine()
    macro_adapter = get_macro_adapter()
    
    # Use some default inputs
    macro_input = macro_adapter.create_manual_input(
        inflation=0.3,
        rates=0.4,
        labor=0.3,
        growth=0.2,
        liquidity=0.2,
    )
    macro = macro_engine.build_context(macro_input)
    
    # Asset fractals
    fractal_service = get_asset_fractal_service()
    fractals = await fractal_service.get_all_contexts_with_macro_fallback(
        macro_usd_bias=macro.usd_bias,
        macro_confidence=macro.confidence,
    )
    
    # Cross-asset alignment
    cross_asset_engine = get_cross_asset_engine()
    cross_asset = cross_asset_engine.compute_alignment(
        macro=macro,
        dxy=fractals.dxy,
        spx=fractals.spx,
        btc=fractals.btc,
    )
    
    return macro, fractals, cross_asset


@router.get("/context", response_model=Dict[str, Any])
async def get_context():
    """
    Get full MacroFractalContext.
    
    Returns unified assessment of macro + fractal + cross-asset chain.
    """
    engine = get_macro_fractal_engine()
    macro, fractals, cross_asset = await _get_all_inputs()
    
    context = engine.compute(
        macro=macro,
        btc=fractals.btc,
        spx=fractals.spx,
        dxy=fractals.dxy,
        cross_asset=cross_asset,
    )
    
    return {
        "status": "ok",
        "data": context.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/summary", response_model=Dict[str, Any])
async def get_summary():
    """Get compact summary of macro-fractal context."""
    engine = get_macro_fractal_engine()
    macro, fractals, cross_asset = await _get_all_inputs()
    
    context = engine.compute(
        macro=macro,
        btc=fractals.btc,
        spx=fractals.spx,
        dxy=fractals.dxy,
        cross_asset=cross_asset,
    )
    
    summary = engine.get_summary(context)
    
    return summary.model_dump()


@router.get("/health", response_model=Dict[str, Any])
async def get_health():
    """Get health status of macro-fractal brain."""
    engine = get_macro_fractal_engine()
    
    try:
        macro, fractals, cross_asset = await _get_all_inputs()
        engine.compute(
            macro=macro,
            btc=fractals.btc,
            spx=fractals.spx,
            dxy=fractals.dxy,
            cross_asset=cross_asset,
        )
    except Exception:
        pass
    
    health = engine.get_health()
    
    return {
        "status": health.status,
        "has_macro": health.has_macro,
        "has_btc": health.has_btc,
        "has_spx": health.has_spx,
        "has_dxy": health.has_dxy,
        "has_cross_asset": health.has_cross_asset,
        "context_state": health.context_state,
        "last_update": health.last_update.isoformat() if health.last_update else None,
    }


@router.get("/drivers", response_model=Dict[str, Any])
async def get_drivers():
    """Get driver strength analysis."""
    engine = get_macro_fractal_engine()
    macro, fractals, cross_asset = await _get_all_inputs()
    
    drivers = engine.get_drivers(
        macro=macro,
        btc=fractals.btc,
        spx=fractals.spx,
        dxy=fractals.dxy,
        cross_asset_strength=cross_asset.alignment_score,
    )
    
    return {
        "drivers": drivers.drivers,
        "dominant_driver": drivers.dominant_driver,
        "weakest_driver": drivers.weakest_driver,
    }
