"""
Fractal Market Intelligence Routes

PHASE 32.1 — API endpoints for Fractal Market Intelligence Engine.

Endpoints:
- GET  /api/v1/fractal/state/{symbol}
- GET  /api/v1/fractal/summary/{symbol}
- GET  /api/v1/fractal/history/{symbol}
- POST /api/v1/fractal/recompute/{symbol}
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .fractal_engine import (
    FractalEngine,
    get_fractal_engine,
)
from .fractal_registry import get_fractal_registry
from .fractal_types import FRACTAL_ALIGNED_MODIFIER, FRACTAL_CONFLICT_MODIFIER


router = APIRouter(prefix="/api/v1/fractal", tags=["fractal-intelligence"])


@router.get("/state/{symbol}", response_model=Dict[str, Any])
async def get_fractal_state(symbol: str):
    """
    Get current fractal market state for symbol.
    
    Returns multi-timeframe state analysis with alignment and bias.
    """
    engine = get_fractal_engine()
    
    # Generate state
    state = engine.generate_fractal_state(symbol.upper())
    
    # Save to MongoDB
    registry = get_fractal_registry()
    registry.save_state(state)
    
    return {
        "symbol": state.symbol,
        "timeframe_states": {
            "5m": state.tf_5m_state,
            "15m": state.tf_15m_state,
            "1h": state.tf_1h_state,
            "4h": state.tf_4h_state,
            "1d": state.tf_1d_state,
        },
        "fractal_metrics": {
            "alignment": state.fractal_alignment,
            "bias": state.fractal_bias,
            "confidence": state.fractal_confidence,
            "volatility_consistency": state.volatility_consistency,
        },
        "modifiers": {
            "aligned_modifier": FRACTAL_ALIGNED_MODIFIER,
            "conflict_modifier": FRACTAL_CONFLICT_MODIFIER,
        },
        "generated_at": state.created_at.isoformat(),
    }


@router.get("/summary/{symbol}", response_model=Dict[str, Any])
async def get_fractal_summary(symbol: str):
    """
    Get fractal intelligence summary for symbol.
    
    Returns state distribution, averages, and streaks.
    """
    engine = get_fractal_engine()
    
    # Ensure state exists
    if not engine.get_current_state(symbol.upper()):
        engine.generate_fractal_state(symbol.upper())
    
    summary = engine.get_summary(symbol.upper())
    
    return {
        "symbol": summary.symbol,
        "current": {
            "alignment": summary.current_alignment,
            "bias": summary.current_bias,
            "confidence": summary.current_confidence,
        },
        "state_distribution": {
            "trend_up": summary.trend_up_count,
            "trend_down": summary.trend_down_count,
            "range": summary.range_count,
            "volatile": summary.volatile_count,
        },
        "historical": {
            "avg_alignment": summary.avg_alignment,
            "avg_confidence": summary.avg_confidence,
            "alignment_streak": summary.alignment_streak,
            "highest_alignment": summary.highest_alignment,
        },
        "total_snapshots": summary.total_snapshots,
        "last_updated": summary.last_updated.isoformat() if summary.last_updated else None,
    }


@router.get("/history/{symbol}", response_model=Dict[str, Any])
async def get_fractal_history(
    symbol: str,
    limit: int = Query(default=50, ge=1, le=500),
):
    """
    Get fractal state history for symbol.
    """
    # Try MongoDB first
    registry = get_fractal_registry()
    history = registry.get_history(symbol.upper(), limit=limit)
    
    # Fallback to in-memory
    if not history:
        engine = get_fractal_engine()
        in_memory = engine.get_history(symbol.upper(), limit=limit)
        history = [
            {
                "fractal_alignment": s.fractal_alignment,
                "fractal_bias": s.fractal_bias,
                "fractal_confidence": s.fractal_confidence,
                "tf_states": s.tf_states,
                "created_at": s.created_at.isoformat(),
            }
            for s in in_memory
        ]
    
    return {
        "symbol": symbol.upper(),
        "total": len(history),
        "history": history,
    }


@router.post("/recompute/{symbol}", response_model=Dict[str, Any])
async def recompute_fractal_state(symbol: str):
    """
    Force recompute of fractal market state.
    """
    try:
        engine = get_fractal_engine()
        
        # Recompute
        state = engine.generate_fractal_state(symbol.upper())
        
        # Save to MongoDB
        registry = get_fractal_registry()
        registry.save_state(state)
        
        return {
            "status": "ok",
            "symbol": state.symbol,
            "fractal_state": {
                "alignment": state.fractal_alignment,
                "bias": state.fractal_bias,
                "confidence": state.fractal_confidence,
            },
            "timeframe_states": state.get_all_states(),
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fractal state recompute failed: {str(e)}",
        )


@router.get("/modifier/{symbol}", response_model=Dict[str, Any])
async def get_fractal_modifier(
    symbol: str,
    hypothesis_bias: str = "LONG",
):
    """
    Get fractal modifier for hypothesis scoring.
    
    Returns alignment status and modifier value.
    """
    engine = get_fractal_engine()
    
    modifier = engine.get_fractal_modifier(symbol.upper(), hypothesis_bias)
    
    return {
        "symbol": symbol.upper(),
        "hypothesis_bias": modifier.hypothesis_bias,
        "fractal_bias": modifier.fractal_bias,
        "alignment": modifier.alignment,
        "is_aligned": modifier.is_aligned,
        "modifier": modifier.modifier,
        "reason": modifier.reason,
    }
