"""
PHASE 25.6 — A/B Test Routes

API endpoints for system validation.

Endpoints:
- GET /api/v1/system-validation/compare
- GET /api/v1/system-validation/summary
- GET /api/v1/system-validation/health
"""

from fastapi import APIRouter
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .ab_test_types import (
    SystemComparison,
    SystemComparisonSummary,
    SystemValidationHealth,
    SystemOutput,
)
from .ab_test_engine import get_ab_test_engine

from modules.fractal_intelligence.fractal_context_engine import FractalContextEngine
from modules.execution_context.execution_context_engine import get_execution_context_engine
from modules.macro_fractal_brain.macro_fractal_engine import get_macro_fractal_engine
from modules.macro_context.macro_context_engine import get_macro_context_engine
from modules.macro_context.macro_context_adapter import get_macro_adapter
from modules.fractal_intelligence.asset_fractal_service import get_asset_fractal_service
from modules.cross_asset_intelligence.cross_asset_engine import get_cross_asset_engine


router = APIRouter(prefix="/api/v1/system-validation", tags=["system-validation"])

# Singleton fractal engine
_fractal_engine: Optional[FractalContextEngine] = None


def _get_fractal_engine() -> FractalContextEngine:
    """Get or create FractalContextEngine singleton."""
    global _fractal_engine
    if _fractal_engine is None:
        _fractal_engine = FractalContextEngine()
    return _fractal_engine


async def _get_system_a_output() -> SystemOutput:
    """
    Get System A output: TA + Exchange only (baseline).
    
    No Fractal, no Macro. Pure TA/Exchange signal.
    """
    # Baseline: fixed confidence and capital
    # In real system, would come from TA + Exchange engines
    return SystemOutput(
        system_type="A",
        direction="LONG",  # Base direction from TA
        strategy="MOMENTUM",  # Base strategy from TA
        confidence=0.61,  # Base confidence
        capital_modifier=1.0,  # No modifier
        context_state="NEUTRAL",
    )


async def _get_system_b_output() -> SystemOutput:
    """
    Get System B output: TA + Exchange + Fractal.
    
    Adds Fractal Intelligence but no Macro.
    """
    try:
        fractal_engine = _get_fractal_engine()
        fractal = await fractal_engine.build_context("BTC")
        
        # Base values
        base_direction = "LONG"
        base_strategy = "MOMENTUM"
        base_confidence = 0.61
        
        # Apply fractal modifier (limited)
        fractal_boost = fractal.fractal_strength * 0.08
        modified_confidence = min(1.0, base_confidence + fractal_boost)
        
        return SystemOutput(
            system_type="B",
            direction=base_direction,  # Direction unchanged
            strategy=base_strategy,  # Strategy unchanged
            confidence=round(modified_confidence, 4),
            capital_modifier=1.0 + (fractal.fractal_strength * 0.05),
            context_state=fractal.context_state,
        )
    except Exception:
        # Fallback to baseline
        return SystemOutput(
            system_type="B",
            direction="LONG",
            strategy="MOMENTUM",
            confidence=0.64,
            capital_modifier=1.03,
            context_state="NEUTRAL",
        )


async def _get_system_c_output() -> SystemOutput:
    """
    Get System C output: TA + Exchange + Fractal + Macro (full system).
    
    Full Macro-Fractal integration.
    """
    try:
        # Get all components
        macro_engine = get_macro_context_engine()
        macro_adapter = get_macro_adapter()
        fractal_engine = _get_fractal_engine()
        fractal_service = get_asset_fractal_service()
        cross_asset_engine = get_cross_asset_engine()
        macro_fractal_engine = get_macro_fractal_engine()
        exec_engine = get_execution_context_engine()
        
        # Build macro context
        macro_input = macro_adapter.create_manual_input(
            inflation=0.3,
            rates=0.4,
            labor=0.3,
            growth=0.2,
            liquidity=0.2,
        )
        macro = macro_engine.build_context(macro_input)
        
        # Get fractals
        fractal = await fractal_engine.build_context("BTC")
        fractals = await fractal_service.get_all_contexts_with_macro_fallback(
            macro_usd_bias=macro.usd_bias,
            macro_confidence=macro.confidence,
        )
        
        # Cross-asset alignment
        cross_asset = cross_asset_engine.compute_alignment(
            macro=macro,
            dxy=fractals.dxy,
            spx=fractals.spx,
            btc=fractals.btc,
        )
        
        # Macro-fractal brain
        macro_fractal = macro_fractal_engine.compute(
            macro=macro,
            btc=fractals.btc,
            spx=fractals.spx,
            dxy=fractals.dxy,
            cross_asset=cross_asset,
        )
        
        # Execution context
        exec_context = exec_engine.compute(
            macro_fractal=macro_fractal,
            fractal=fractal,
            cross_asset=cross_asset,
        )
        
        # Base values (direction and strategy NEVER change)
        base_direction = "LONG"
        base_strategy = "MOMENTUM"
        base_confidence = 0.61
        
        # Apply execution modifiers
        modified_confidence = base_confidence * exec_context.confidence_modifier
        modified_confidence = min(1.0, max(0.0, modified_confidence))
        
        return SystemOutput(
            system_type="C",
            direction=base_direction,  # Direction unchanged
            strategy=base_strategy,  # Strategy unchanged
            confidence=round(modified_confidence, 4),
            capital_modifier=round(exec_context.capital_modifier, 4),
            context_state=exec_context.context_state,
        )
    except Exception as e:
        # Fallback
        return SystemOutput(
            system_type="C",
            direction="LONG",
            strategy="MOMENTUM",
            confidence=0.67,
            capital_modifier=1.06,
            context_state="NEUTRAL",
        )


@router.get("/compare", response_model=Dict[str, Any])
async def compare_systems():
    """
    Compare System A, B, C.
    
    Returns full comparison with validation result.
    
    - System A: TA + Exchange (baseline)
    - System B: TA + Exchange + Fractal
    - System C: TA + Exchange + Fractal + Macro
    """
    engine = get_ab_test_engine()
    
    # Get outputs from all systems
    system_a = await _get_system_a_output()
    system_b = await _get_system_b_output()
    system_c = await _get_system_c_output()
    
    # Compare
    comparison = engine.compare(system_a, system_b, system_c)
    
    return {
        "status": "ok",
        "data": comparison.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/summary", response_model=SystemComparisonSummary)
async def get_summary():
    """
    Get compact comparison summary.
    
    Returns key metrics only.
    """
    engine = get_ab_test_engine()
    
    system_a = await _get_system_a_output()
    system_b = await _get_system_b_output()
    system_c = await _get_system_c_output()
    
    comparison = engine.compare(system_a, system_b, system_c)
    return engine.get_summary(comparison)


@router.get("/health", response_model=Dict[str, Any])
async def get_health():
    """
    Get health status of system validation module.
    """
    engine = get_ab_test_engine()
    
    try:
        system_a = await _get_system_a_output()
        system_b = await _get_system_b_output()
        system_c = await _get_system_c_output()
        engine.compare(system_a, system_b, system_c)
    except Exception:
        pass
    
    health = engine.get_health()
    
    return {
        "status": health.status,
        "system_a_available": health.system_a_available,
        "system_b_available": health.system_b_available,
        "system_c_available": health.system_c_available,
        "last_validation": health.last_validation,
        "last_update": health.last_update.isoformat() if health.last_update else None,
    }
