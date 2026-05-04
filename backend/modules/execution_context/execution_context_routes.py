"""
PHASE 25.5 — Execution Context Routes

API endpoints for Execution Context Layer.

Endpoints:
- GET /api/v1/execution-context/context
- GET /api/v1/execution-context/summary
- GET /api/v1/execution-context/health
"""

from fastapi import APIRouter
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .execution_context_types import (
    ExecutionContext,
    ExecutionContextSummary,
    ExecutionContextHealthStatus,
)
from .execution_context_engine import get_execution_context_engine

from modules.macro_fractal_brain.macro_fractal_engine import get_macro_fractal_engine
from modules.macro_context.macro_context_engine import get_macro_context_engine
from modules.macro_context.macro_context_adapter import get_macro_adapter
from modules.fractal_intelligence.asset_fractal_service import get_asset_fractal_service
from modules.fractal_intelligence.fractal_context_engine import FractalContextEngine
from modules.cross_asset_intelligence.cross_asset_engine import get_cross_asset_engine


router = APIRouter(prefix="/api/v1/execution-context", tags=["execution-context"])

# Singleton fractal engine
_fractal_engine: Optional[FractalContextEngine] = None


def _get_fractal_engine() -> FractalContextEngine:
    """Get or create FractalContextEngine singleton."""
    global _fractal_engine
    if _fractal_engine is None:
        _fractal_engine = FractalContextEngine()
    return _fractal_engine


async def _get_all_inputs():
    """
    Get all inputs required for ExecutionContext computation.
    
    Returns:
        - macro_fractal: MacroFractalContext
        - fractal: FractalContext
        - cross_asset: CrossAssetAlignment
    """
    # Macro context
    macro_engine = get_macro_context_engine()
    macro_adapter = get_macro_adapter()
    
    # Use default inputs
    macro_input = macro_adapter.create_manual_input(
        inflation=0.3,
        rates=0.4,
        labor=0.3,
        growth=0.2,
        liquidity=0.2,
    )
    macro = macro_engine.build_context(macro_input)
    
    # Asset fractals (for cross-asset)
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
    
    # Macro-fractal context
    macro_fractal_engine = get_macro_fractal_engine()
    macro_fractal = macro_fractal_engine.compute(
        macro=macro,
        btc=fractals.btc,
        spx=fractals.spx,
        dxy=fractals.dxy,
        cross_asset=cross_asset,
    )
    
    # BTC fractal context (main fractal)
    fractal_engine = _get_fractal_engine()
    fractal = await fractal_engine.build_context("BTC")
    
    return macro_fractal, fractal, cross_asset


@router.get("/context", response_model=Dict[str, Any])
async def get_context():
    """
    Get full ExecutionContext.
    
    Returns complete execution context with:
    - context_bias
    - fractal_strength
    - macro_strength
    - cross_asset_strength
    - confidence_modifier
    - capital_modifier
    - context_state
    - reason
    """
    engine = get_execution_context_engine()
    macro_fractal, fractal, cross_asset = await _get_all_inputs()
    
    context = engine.compute(
        macro_fractal=macro_fractal,
        fractal=fractal,
        cross_asset=cross_asset,
    )
    
    return {
        "status": "ok",
        "data": context.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/summary", response_model=ExecutionContextSummary)
async def get_summary():
    """
    Get compact ExecutionContext summary.
    
    Returns:
    - context_bias
    - confidence_modifier
    - capital_modifier
    - context_state
    """
    engine = get_execution_context_engine()
    macro_fractal, fractal, cross_asset = await _get_all_inputs()
    
    context = engine.compute(
        macro_fractal=macro_fractal,
        fractal=fractal,
        cross_asset=cross_asset,
    )
    
    return engine.get_summary(context)


@router.get("/health", response_model=Dict[str, Any])
async def get_health():
    """
    Get health status of execution context module.
    
    Returns:
    - status: OK | DEGRADED | ERROR
    - has_macro_fractal
    - has_fractal
    - has_cross_asset
    - context_state
    - last_update
    """
    engine = get_execution_context_engine()
    
    try:
        macro_fractal, fractal, cross_asset = await _get_all_inputs()
        engine.compute(
            macro_fractal=macro_fractal,
            fractal=fractal,
            cross_asset=cross_asset,
        )
    except Exception:
        pass
    
    health = engine.get_health()
    
    return {
        "status": health.status,
        "has_macro_fractal": health.has_macro_fractal,
        "has_fractal": health.has_fractal,
        "has_cross_asset": health.has_cross_asset,
        "context_state": health.context_state,
        "last_update": health.last_update.isoformat() if health.last_update else None,
    }
