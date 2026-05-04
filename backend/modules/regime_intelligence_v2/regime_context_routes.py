"""
Regime Context — Routes

API endpoints for unified regime context.

Endpoints:
- GET /api/v1/regime/context
- GET /api/v1/regime/context/summary
- GET /api/v1/regime/context/strategies
- POST /api/v1/regime/context/recompute
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from datetime import datetime, timezone

from .regime_context_engine import (
    RegimeContextEngine,
    get_regime_context_engine,
)


router = APIRouter(prefix="/api/v1/regime/context", tags=["regime-context"])


@router.get("", response_model=Dict[str, Any])
async def get_regime_context(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
):
    """
    Get unified regime context.
    
    Combines:
    - Current market regime
    - Strategy suitability mapping
    - Transition risk assessment
    
    Returns single RegimeContext for execution decisions.
    """
    engine = get_regime_context_engine()
    
    # Compute full context
    context = await engine.compute_context(symbol, timeframe)
    
    return {
        "current_regime": context.current_regime,
        "regime_confidence": context.regime_confidence,
        "dominant_driver": context.dominant_driver,
        
        "next_regime_candidate": context.next_regime_candidate,
        "transition_probability": context.transition_probability,
        "transition_state": context.transition_state,
        
        "favored_strategies": context.favored_strategies,
        "neutral_strategies": context.neutral_strategies,
        "disfavored_strategies": context.disfavored_strategies,
        
        "confidence_modifier": context.confidence_modifier,
        "capital_modifier": context.capital_modifier,
        
        "context_state": context.context_state,
        "reason": context.reason,
        
        "symbol": context.symbol,
        "timeframe": context.timeframe,
        "computed_at": context.computed_at.isoformat(),
    }


@router.get("/summary", response_model=Dict[str, Any])
async def get_context_summary(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
):
    """
    Get regime context summary.
    
    Returns condensed view of current context state.
    """
    engine = get_regime_context_engine()
    
    # Ensure context is computed
    if not engine.current_context:
        await engine.compute_context(symbol, timeframe)
    
    summary = engine.get_summary()
    
    if not summary:
        return {
            "error": "No context computed",
            "symbol": symbol,
            "timeframe": timeframe,
        }
    
    return {
        "current_regime": summary.current_regime,
        "regime_confidence": summary.regime_confidence,
        "transition_state": summary.transition_state,
        "transition_probability": summary.transition_probability,
        "context_state": summary.context_state,
        "total_favored": summary.total_favored,
        "total_neutral": summary.total_neutral,
        "total_disfavored": summary.total_disfavored,
        "confidence_modifier": summary.confidence_modifier,
        "capital_modifier": summary.capital_modifier,
        "symbol": symbol,
        "timeframe": timeframe,
    }


@router.get("/strategies", response_model=Dict[str, Any])
async def get_context_strategies(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
):
    """
    Get strategy suitability from current context.
    
    Returns grouped strategies with modifiers.
    """
    engine = get_regime_context_engine()
    
    # Ensure context is computed
    context = await engine.compute_context(symbol, timeframe)
    
    return {
        "current_regime": context.current_regime,
        "context_state": context.context_state,
        "favored_strategies": context.favored_strategies,
        "neutral_strategies": context.neutral_strategies,
        "disfavored_strategies": context.disfavored_strategies,
        "confidence_modifier": context.confidence_modifier,
        "capital_modifier": context.capital_modifier,
        "recommendation": _get_strategy_recommendation(context.context_state),
        "symbol": symbol,
        "timeframe": timeframe,
    }


def _get_strategy_recommendation(context_state: str) -> str:
    """Generate strategy recommendation based on context state."""
    if context_state == "SUPPORTIVE":
        return "Full allocation to favored strategies recommended"
    elif context_state == "NEUTRAL":
        return "Balanced allocation across favored and neutral strategies"
    else:  # CONFLICTED
        return "Reduce exposure and shift toward neutral strategies until regime stabilizes"


@router.post("/recompute", response_model=Dict[str, Any])
async def recompute_context(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
):
    """
    Force recompute of regime context.
    
    Refreshes all components and rebuilds unified context.
    """
    try:
        engine = get_regime_context_engine()
        
        # Recompute
        context = await engine.compute_context(symbol, timeframe)
        
        return {
            "status": "ok",
            "current_regime": context.current_regime,
            "regime_confidence": context.regime_confidence,
            "dominant_driver": context.dominant_driver,
            
            "next_regime_candidate": context.next_regime_candidate,
            "transition_probability": context.transition_probability,
            "transition_state": context.transition_state,
            
            "favored_strategies": context.favored_strategies,
            "neutral_strategies": context.neutral_strategies,
            "disfavored_strategies": context.disfavored_strategies,
            
            "confidence_modifier": context.confidence_modifier,
            "capital_modifier": context.capital_modifier,
            
            "context_state": context.context_state,
            "reason": context.reason,
            
            "symbol": symbol,
            "timeframe": timeframe,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recompute failed: {str(e)}"
        )
