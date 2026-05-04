"""
PHASE 25.1 — Macro Context Routes

API endpoints for Macro Context module.

Endpoints:
- GET /api/v1/macro-context/context - Full MacroContext
- GET /api/v1/macro-context/summary - Compact summary
- GET /api/v1/macro-context/health - Health status
- GET /api/v1/macro-context/inputs - Current inputs (debug)
- POST /api/v1/macro-context/compute - Compute from provided data
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime, timezone

from .macro_context_types import (
    MacroInput,
    MacroContext,
    MacroContextSummary,
    MacroHealthStatus,
)
from .macro_context_engine import get_macro_context_engine


router = APIRouter(prefix="/api/v1/macro-context", tags=["macro-context"])


# ══════════════════════════════════════════════════════════════
# In-Memory State (for demo/testing)
# ══════════════════════════════════════════════════════════════

_current_input: MacroInput = MacroInput()


# ══════════════════════════════════════════════════════════════
# Routes
# ══════════════════════════════════════════════════════════════

@router.get("/context", response_model=Dict[str, Any])
async def get_context():
    """
    Get full MacroContext based on current inputs.
    
    Returns complete macro context with all computed fields.
    """
    engine = get_macro_context_engine()
    context = engine.build_context(_current_input)
    
    return {
        "status": "ok",
        "data": context.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/summary", response_model=Dict[str, Any])
async def get_summary():
    """
    Get compact MacroContext summary.
    
    Returns only essential fields for quick access.
    """
    engine = get_macro_context_engine()
    context = engine.build_context(_current_input)
    summary = engine.get_summary(context)
    
    return {
        "macro_state": summary.macro_state,
        "usd_bias": summary.usd_bias,
        "equity_bias": summary.equity_bias,
        "liquidity_state": summary.liquidity_state,
        "confidence": summary.confidence,
        "reliability": summary.reliability,
        "context_state": summary.context_state,
    }


@router.get("/health", response_model=Dict[str, Any])
async def get_health():
    """
    Get health status of macro context module.
    """
    engine = get_macro_context_engine()
    
    # Build context to update internal state
    engine.build_context(_current_input)
    
    health = engine.get_health()
    
    return {
        "status": health.status,
        "has_inputs": health.has_inputs,
        "input_count": health.input_count,
        "context_state": health.context_state,
        "last_update": health.last_update.isoformat() if health.last_update else None,
    }


@router.get("/inputs", response_model=Dict[str, Any])
async def get_inputs():
    """
    Get current normalized macro inputs (for debug/audit).
    """
    return {
        "status": "ok",
        "inputs": _current_input.get_all_signals(),
        "source": _current_input.source,
        "timestamp": _current_input.timestamp.isoformat(),
        "non_zero_count": _current_input.count_non_zero(),
    }


@router.post("/compute", response_model=Dict[str, Any])
async def compute_context(data: Dict[str, Any]):
    """
    Compute MacroContext from provided data.
    
    Accepts either:
    - Raw macro values (inflation: 3.5, fed_rate: 5.0, etc.)
    - Normalized signals (inflation_signal: 0.5, rates_signal: 0.3, etc.)
    
    Returns full MacroContext.
    """
    global _current_input
    
    engine = get_macro_context_engine()
    
    try:
        # Check if data contains normalized signals or raw values
        if any(key.endswith("_signal") for key in data.keys()):
            # Direct normalized input
            _current_input = MacroInput(**data)
        else:
            # Raw values - use adapter
            _current_input = engine.adapter.adapt_from_dict(data)
        
        context = engine.build_context(_current_input)
        
        return {
            "status": "ok",
            "data": context.model_dump(),
            "inputs_used": _current_input.get_all_signals(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to compute macro context: {str(e)}"
        )


@router.post("/set-inputs", response_model=Dict[str, Any])
async def set_inputs(data: Dict[str, Any]):
    """
    Set current macro inputs (normalized values).
    
    All values should be in [-1.0, +1.0].
    """
    global _current_input
    
    engine = get_macro_context_engine()
    
    try:
        _current_input = engine.adapter.create_manual_input(
            inflation=data.get("inflation", 0.0),
            rates=data.get("rates", 0.0),
            labor=data.get("labor", 0.0),
            unemployment=data.get("unemployment", 0.0),
            housing=data.get("housing", 0.0),
            growth=data.get("growth", 0.0),
            liquidity=data.get("liquidity", 0.0),
            credit=data.get("credit", 0.0),
            consumer=data.get("consumer", 0.0),
        )
        
        return {
            "status": "ok",
            "message": "Macro inputs updated",
            "inputs": _current_input.get_all_signals(),
            "non_zero_count": _current_input.count_non_zero(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to set inputs: {str(e)}"
        )


# ══════════════════════════════════════════════════════════════
# Example Scenario Endpoints (for testing)
# ══════════════════════════════════════════════════════════════

@router.post("/scenarios/risk-on", response_model=Dict[str, Any])
async def scenario_risk_on():
    """Load RISK_ON scenario for testing."""
    global _current_input
    
    engine = get_macro_context_engine()
    _current_input = engine.adapter.create_manual_input(
        inflation=-0.3,   # Low inflation
        rates=-0.4,       # Dovish rates
        labor=0.5,        # Strong labor
        unemployment=0.4, # Low unemployment
        housing=0.3,      # Strong housing
        growth=0.6,       # Strong growth
        liquidity=0.5,    # Expanding liquidity
        credit=0.4,       # Easy credit
        consumer=0.5,     # Strong consumer
    )
    
    context = engine.build_context(_current_input)
    return {
        "status": "ok",
        "scenario": "RISK_ON",
        "data": context.model_dump(),
    }


@router.post("/scenarios/risk-off", response_model=Dict[str, Any])
async def scenario_risk_off():
    """Load RISK_OFF scenario for testing."""
    global _current_input
    
    engine = get_macro_context_engine()
    _current_input = engine.adapter.create_manual_input(
        inflation=0.4,    # High inflation
        rates=0.5,        # Hawkish rates
        labor=0.2,        # OK labor
        unemployment=-0.2,# Rising unemployment
        housing=-0.3,     # Weak housing
        growth=-0.4,      # Weak growth
        liquidity=-0.3,   # Contracting liquidity
        credit=-0.4,      # Tight credit
        consumer=-0.3,    # Weak consumer
    )
    
    context = engine.build_context(_current_input)
    return {
        "status": "ok",
        "scenario": "RISK_OFF",
        "data": context.model_dump(),
    }


@router.post("/scenarios/tightening", response_model=Dict[str, Any])
async def scenario_tightening():
    """Load TIGHTENING scenario for testing."""
    global _current_input
    
    engine = get_macro_context_engine()
    _current_input = engine.adapter.create_manual_input(
        inflation=0.6,    # High inflation
        rates=0.6,        # Very hawkish rates
        labor=0.3,        # OK labor
        unemployment=0.2, # OK unemployment
        housing=-0.2,     # Weakening housing
        growth=0.1,       # Slowing growth
        liquidity=-0.4,   # Contracting liquidity
        credit=-0.3,      # Tightening credit
        consumer=-0.1,    # Weakening consumer
    )
    
    context = engine.build_context(_current_input)
    return {
        "status": "ok",
        "scenario": "TIGHTENING",
        "data": context.model_dump(),
    }


@router.post("/scenarios/stagflation", response_model=Dict[str, Any])
async def scenario_stagflation():
    """Load STAGFLATION scenario for testing."""
    global _current_input
    
    engine = get_macro_context_engine()
    _current_input = engine.adapter.create_manual_input(
        inflation=0.7,    # Very high inflation
        rates=0.3,        # Elevated rates
        labor=-0.2,       # Weakening labor
        unemployment=-0.3,# Rising unemployment
        housing=-0.4,     # Weak housing
        growth=-0.4,      # Negative growth
        liquidity=-0.1,   # Stable/slight contraction
        credit=-0.2,      # Tighter credit
        consumer=-0.4,    # Weak consumer
    )
    
    context = engine.build_context(_current_input)
    return {
        "status": "ok",
        "scenario": "STAGFLATION",
        "data": context.model_dump(),
    }
