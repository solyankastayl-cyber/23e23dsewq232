"""
Strategy Brain — Routes

PHASE 29.5 — API endpoints for Strategy Brain.

Endpoints:
- GET  /api/v1/strategy/decision/{symbol}
- GET  /api/v1/strategy/summary/{symbol}
- GET  /api/v1/strategy/history/{symbol}
- POST /api/v1/strategy/recompute/{symbol}
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime, timezone

from .strategy_brain_engine import (
    StrategyBrainEngine,
    get_strategy_brain,
)


router = APIRouter(prefix="/api/v1/strategy", tags=["strategy"])


@router.get("/decision/{symbol}", response_model=Dict[str, Any])
async def get_strategy_decision(symbol: str):
    """
    Get current strategy decision for symbol.
    
    Uses Hypothesis Engine to determine optimal strategy.
    
    Returns:
    - selected_strategy: The chosen strategy or "none"
    - suitability_score: How suitable the strategy is (0-1)
    - hypothesis_type: Market hypothesis driving the decision
    - execution_state: Current execution conditions
    """
    brain = get_strategy_brain()
    
    # Generate decision from live hypothesis
    decision = brain.select_strategy_from_hypothesis(symbol.upper())
    
    return {
        "symbol": decision.symbol,
        "hypothesis_type": decision.hypothesis_type,
        "directional_bias": decision.directional_bias,
        "selected_strategy": decision.selected_strategy,
        "alternative_strategies": decision.alternative_strategies,
        "suitability_score": decision.suitability_score,
        "execution_state": decision.execution_state,
        "confidence": decision.confidence,
        "reliability": decision.reliability,
        "reason": decision.reason,
        "created_at": decision.created_at.isoformat(),
    }


@router.get("/summary/{symbol}", response_model=Dict[str, Any])
async def get_strategy_summary(symbol: str):
    """
    Get strategy summary statistics for symbol.
    
    Returns distribution of strategy selections and averages.
    """
    brain = get_strategy_brain()
    
    # Ensure at least one decision exists
    if not brain.get_decision(symbol.upper()):
        brain.select_strategy_from_hypothesis(symbol.upper())
    
    summary = brain.get_summary(symbol.upper())
    
    return {
        "symbol": summary.symbol,
        "total_decisions": summary.total_decisions,
        "strategies": {
            "trend_following": summary.trend_following_count,
            "breakout_trading": summary.breakout_trading_count,
            "mean_reversion": summary.mean_reversion_count,
            "volatility_expansion": summary.volatility_expansion_count,
            "liquidation_capture": summary.liquidation_capture_count,
            "range_trading": summary.range_trading_count,
            "basis_trade": summary.basis_trade_count,
            "funding_arb": summary.funding_arb_count,
            "none": summary.none_count,
        },
        "averages": {
            "suitability_score": summary.avg_suitability_score,
            "confidence": summary.avg_confidence,
            "reliability": summary.avg_reliability,
        },
        "current": {
            "strategy": summary.current_strategy,
            "hypothesis": summary.current_hypothesis,
        },
    }


@router.get("/history/{symbol}", response_model=Dict[str, Any])
async def get_strategy_history(symbol: str, limit: int = 50):
    """
    Get strategy decision history for symbol.
    """
    brain = get_strategy_brain()
    history = brain.get_history(symbol.upper(), limit=limit)
    
    return {
        "symbol": symbol.upper(),
        "total": len(history),
        "decisions": [
            {
                "hypothesis_type": d.hypothesis_type,
                "directional_bias": d.directional_bias,
                "selected_strategy": d.selected_strategy,
                "suitability_score": d.suitability_score,
                "execution_state": d.execution_state,
                "confidence": d.confidence,
                "reliability": d.reliability,
                "reason": d.reason,
                "created_at": d.created_at.isoformat(),
            }
            for d in history
        ],
    }


@router.post("/recompute/{symbol}", response_model=Dict[str, Any])
async def recompute_strategy(symbol: str):
    """
    Force recompute of strategy decision.
    
    Regenerates hypothesis and selects new strategy.
    """
    try:
        brain = get_strategy_brain()
        
        # Recompute decision
        decision = brain.select_strategy_from_hypothesis(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": decision.symbol,
            "hypothesis_type": decision.hypothesis_type,
            "directional_bias": decision.directional_bias,
            "selected_strategy": decision.selected_strategy,
            "alternative_strategies": decision.alternative_strategies,
            "suitability_score": decision.suitability_score,
            "execution_state": decision.execution_state,
            "confidence": decision.confidence,
            "reliability": decision.reliability,
            "reason": decision.reason,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Strategy recompute failed: {str(e)}",
        )


@router.get("/available", response_model=Dict[str, Any])
async def get_available_strategies():
    """
    Get list of all available strategies.
    """
    from .strategy_types import AVAILABLE_STRATEGIES, HYPOTHESIS_STRATEGY_MAP
    
    return {
        "strategies": AVAILABLE_STRATEGIES,
        "hypothesis_mapping": HYPOTHESIS_STRATEGY_MAP,
    }
