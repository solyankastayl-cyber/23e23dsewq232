"""
Outcome Tracking Routes

PHASE 30.4 — API endpoints for Outcome Tracking Engine.

Endpoints:
- GET  /api/v1/hypothesis/outcomes/{symbol}
- GET  /api/v1/hypothesis/outcomes/summary/{symbol}
- GET  /api/v1/hypothesis/performance/{symbol}
- POST /api/v1/hypothesis/outcomes/evaluate/{symbol}
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .outcome_tracking_engine import (
    OutcomeTrackingEngine,
    get_outcome_tracking_engine,
)
from .outcome_tracking_registry import get_outcome_tracking_registry
from .capital_allocation_engine import get_capital_allocation_engine


router = APIRouter(prefix="/api/v1/hypothesis", tags=["hypothesis-outcomes"])


@router.get("/outcomes/{symbol}", response_model=Dict[str, Any])
async def get_outcomes(
    symbol: str,
    limit: int = Query(default=50, ge=1, le=500),
    hypothesis_type: Optional[str] = None,
    horizon: Optional[int] = None,
):
    """
    Get hypothesis outcomes for symbol.
    
    Returns evaluated outcomes with PnL, success, and direction info.
    """
    # Try MongoDB first
    registry = get_outcome_tracking_registry()
    outcomes = registry.get_outcomes(
        symbol.upper(),
        limit=limit,
        hypothesis_type=hypothesis_type,
        horizon=horizon,
    )
    
    # Fallback to in-memory
    if not outcomes:
        engine = get_outcome_tracking_engine()
        memory_outcomes = engine.get_outcomes(symbol.upper(), limit=limit)
        outcomes = [
            {
                "symbol": o.symbol,
                "hypothesis_type": o.hypothesis_type,
                "directional_bias": o.directional_bias,
                "price_at_creation": o.price_at_creation,
                "evaluation_price": o.evaluation_price,
                "horizon_minutes": o.horizon_minutes,
                "expected_direction": o.expected_direction,
                "actual_direction": o.actual_direction,
                "pnl_percent": o.pnl_percent,
                "success": o.success,
                "confidence": o.confidence,
                "reliability": o.reliability,
                "created_at": o.created_at.isoformat(),
                "evaluated_at": o.evaluated_at.isoformat(),
            }
            for o in memory_outcomes
        ]
    
    return {
        "symbol": symbol.upper(),
        "total": len(outcomes),
        "outcomes": outcomes,
    }


@router.get("/outcomes/summary/{symbol}", response_model=Dict[str, Any])
async def get_outcomes_summary(symbol: str):
    """
    Get outcome summary for symbol.
    
    Returns aggregated statistics including:
    - Overall success rate
    - Success rate by direction
    - Best/worst hypothesis types
    """
    # Try MongoDB first
    registry = get_outcome_tracking_registry()
    summary = registry.get_summary(symbol.upper())
    
    # Fallback to in-memory
    if summary.total_outcomes == 0:
        engine = get_outcome_tracking_engine()
        summary = engine.get_summary(symbol.upper())
    
    return {
        "symbol": summary.symbol,
        "total_outcomes": summary.total_outcomes,
        "overall": {
            "success_rate": summary.overall_success_rate,
            "avg_pnl": summary.overall_avg_pnl,
        },
        "by_direction": {
            "long_success_rate": summary.long_success_rate,
            "short_success_rate": summary.short_success_rate,
            "neutral_success_rate": summary.neutral_success_rate,
        },
        "performers": {
            "best_hypothesis": summary.best_hypothesis_type,
            "best_success_rate": summary.best_success_rate,
            "worst_hypothesis": summary.worst_hypothesis_type,
            "worst_success_rate": summary.worst_success_rate,
        },
        "quality": {
            "avg_confidence_accuracy_correlation": summary.avg_confidence_accuracy_correlation,
        },
        "last_evaluated_at": summary.last_evaluated_at.isoformat() if summary.last_evaluated_at else None,
    }


@router.get("/performance/{symbol}", response_model=Dict[str, Any])
async def get_performance(
    symbol: str,
    hypothesis_type: Optional[str] = None,
):
    """
    Get hypothesis performance metrics.
    
    Returns success rate, avg PnL, and correlations by hypothesis type.
    """
    # Try MongoDB first
    registry = get_outcome_tracking_registry()
    performances = registry.get_performance(symbol.upper(), hypothesis_type)
    
    # Fallback to in-memory
    if not performances:
        engine = get_outcome_tracking_engine()
        performances = engine.calculate_performance(symbol.upper(), hypothesis_type)
    
    return {
        "symbol": symbol.upper(),
        "total_types": len(performances),
        "performances": [
            {
                "hypothesis_type": p.hypothesis_type,
                "total_predictions": p.total_predictions,
                "success_rate": p.success_rate,
                "avg_pnl": p.avg_pnl,
                "avg_confidence": p.avg_confidence,
                "avg_reliability": p.avg_reliability,
                "confidence_accuracy_correlation": p.confidence_accuracy_correlation,
                "reliability_accuracy_correlation": p.reliability_accuracy_correlation,
                "success_by_horizon": {
                    "5m": p.success_rate_5m,
                    "15m": p.success_rate_15m,
                    "60m": p.success_rate_60m,
                    "240m": p.success_rate_240m,
                },
            }
            for p in performances
        ],
    }


@router.post("/outcomes/evaluate/{symbol}", response_model=Dict[str, Any])
async def evaluate_outcomes(
    symbol: str,
    current_price: Optional[float] = None,
):
    """
    Trigger outcome evaluation for pending hypotheses.
    
    If current_price not provided, uses last known price or mock.
    """
    try:
        engine = get_outcome_tracking_engine()
        
        # Get current price (mock if not provided)
        if current_price is None:
            # Try to get from candles or use mock
            from core.database import get_database
            db = get_database()
            if db is not None:
                candle = db.candles.find_one(
                    {"symbol": symbol.upper()},
                    sort=[("timestamp", -1)],
                )
                current_price = candle.get("close", 50000.0) if candle else 50000.0
            else:
                current_price = 50000.0
        
        # Check pending count
        pending_count = engine.get_pending_count(symbol.upper())
        
        # Force evaluate all pending
        outcomes = engine.force_evaluate(symbol.upper(), current_price)
        
        # Save to MongoDB
        if outcomes:
            registry = get_outcome_tracking_registry()
            registry.save_outcomes_batch(outcomes)
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "pending_before": pending_count,
            "outcomes_evaluated": len(outcomes),
            "outcomes": [
                {
                    "hypothesis_type": o.hypothesis_type,
                    "directional_bias": o.directional_bias,
                    "horizon_minutes": o.horizon_minutes,
                    "pnl_percent": o.pnl_percent,
                    "success": o.success,
                }
                for o in outcomes
            ],
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Outcome evaluation failed: {str(e)}",
        )


@router.post("/outcomes/register/{symbol}", response_model=Dict[str, Any])
async def register_for_tracking(
    symbol: str,
    current_price: Optional[float] = None,
):
    """
    Register current portfolio allocation for outcome tracking.
    
    Called after capital allocation to track results.
    """
    try:
        # Get current allocation
        alloc_engine = get_capital_allocation_engine()
        allocation = alloc_engine.generate_allocation(symbol.upper())
        
        # Get current price
        if current_price is None:
            from core.database import get_database
            db = get_database()
            if db is not None:
                candle = db.candles.find_one(
                    {"symbol": symbol.upper()},
                    sort=[("timestamp", -1)],
                )
                current_price = candle.get("close", 50000.0) if candle else 50000.0
            else:
                current_price = 50000.0
        
        # Register for tracking
        tracking_engine = get_outcome_tracking_engine()
        registered = tracking_engine.register_hypothesis(allocation, current_price)
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "hypotheses_registered": registered,
            "price_at_registration": current_price,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}",
        )
