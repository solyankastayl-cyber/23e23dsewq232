"""
Regime Transition Detector — Routes

API endpoints for transition detection.

Endpoints:
- GET /api/v1/regime/transition/current
- GET /api/v1/regime/transition/history
- GET /api/v1/regime/transition/summary
- POST /api/v1/regime/transition/recompute
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from datetime import datetime, timezone

from .regime_transition_engine import (
    RegimeTransitionEngine,
    get_regime_transition_engine,
)
from .regime_transition_registry import (
    RegimeTransitionRegistry,
    get_regime_transition_registry,
)


router = APIRouter(prefix="/api/v1/regime/transition", tags=["regime-transition"])


@router.get("/current", response_model=Dict[str, Any])
async def get_current_transition(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
):
    """
    Get current regime transition state.
    
    Returns transition probability, next regime candidate, and triggers.
    """
    engine = get_regime_transition_engine()
    registry = get_regime_transition_registry()
    
    # Detect current transition
    transition = await engine.detect_transition_from_history(symbol, timeframe)
    
    # Store in history
    await registry.store_transition(transition)
    
    return {
        "current_regime": transition.current_regime,
        "next_regime_candidate": transition.next_regime_candidate,
        "transition_probability": transition.transition_probability,
        "transition_score": transition.transition_score,
        "transition_state": transition.transition_state,
        "trigger_factors": transition.trigger_factors,
        "confidence_modifier": transition.confidence_modifier,
        "capital_modifier": transition.capital_modifier,
        "reason": transition.reason,
        "symbol": symbol,
        "timeframe": timeframe,
        "computed_at": transition.computed_at.isoformat(),
    }


@router.get("/history", response_model=Dict[str, Any])
async def get_transition_history(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
    limit: int = Query(50, ge=1, le=500, description="Max records"),
):
    """
    Get transition history for symbol/timeframe.
    """
    registry = get_regime_transition_registry()
    history = await registry.get_history(symbol, timeframe, limit)
    
    return {
        "history": [
            {
                "current_regime": r.current_regime,
                "next_regime_candidate": r.next_regime_candidate,
                "transition_probability": r.transition_probability,
                "transition_state": r.transition_state,
                "trigger_factors": r.trigger_factors,
                "recorded_at": r.recorded_at.isoformat(),
            }
            for r in history
        ],
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(history),
    }


@router.get("/summary", response_model=Dict[str, Any])
async def get_transition_summary(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
):
    """
    Get transition summary statistics.
    
    Returns counts by state, frequency, and common triggers.
    """
    registry = get_regime_transition_registry()
    summary = await registry.get_summary(symbol, timeframe)
    
    return {
        "total_records": summary.total_records,
        "stable_count": summary.stable_count,
        "early_shift_count": summary.early_shift_count,
        "active_transition_count": summary.active_transition_count,
        "unstable_count": summary.unstable_count,
        "current_state": summary.current_state,
        "average_probability": summary.average_probability,
        "most_common_trigger": summary.most_common_trigger,
        "transition_frequency": summary.transition_frequency,
        "symbol": symbol,
        "timeframe": timeframe,
    }


@router.post("/recompute", response_model=Dict[str, Any])
async def recompute_transition(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
):
    """
    Force recompute of current transition state.
    
    Stores result in history.
    """
    try:
        engine = get_regime_transition_engine()
        registry = get_regime_transition_registry()
        
        # Recompute
        transition = await engine.detect_transition_from_history(symbol, timeframe)
        
        # Store in history
        await registry.store_transition(transition)
        
        return {
            "status": "ok",
            "current_regime": transition.current_regime,
            "next_regime_candidate": transition.next_regime_candidate,
            "transition_probability": transition.transition_probability,
            "transition_state": transition.transition_state,
            "trigger_factors": transition.trigger_factors,
            "confidence_modifier": transition.confidence_modifier,
            "capital_modifier": transition.capital_modifier,
            "reason": transition.reason,
            "symbol": symbol,
            "timeframe": timeframe,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recompute failed: {str(e)}"
        )
