"""
Adaptive Weight Routes

PHASE 30.5 — API endpoints for Adaptive Weight Engine.

Endpoints:
- GET  /api/v1/hypothesis/adaptive/{symbol}
- GET  /api/v1/hypothesis/adaptive/summary/{symbol}
- POST /api/v1/hypothesis/adaptive/recompute/{symbol}
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime, timezone

from .adaptive_weight_engine import (
    AdaptiveWeightEngine,
    get_adaptive_weight_engine,
)
from .adaptive_weight_registry import get_adaptive_weight_registry


router = APIRouter(prefix="/api/v1/hypothesis/adaptive", tags=["hypothesis-adaptive"])


@router.get("/{symbol}", response_model=Dict[str, Any])
async def get_adaptive_weights(symbol: str):
    """
    Get adaptive weights for all hypothesis types.
    
    Returns weights with modifiers and performance data.
    """
    engine = get_adaptive_weight_engine()
    
    # Generate weights (uses outcome tracking data)
    weights = engine.generate_adaptive_weights(symbol.upper())
    
    # Save to MongoDB
    if weights:
        registry = get_adaptive_weight_registry()
        registry.save_weights_batch(symbol.upper(), weights)
    
    return {
        "symbol": symbol.upper(),
        "total_types": len(weights),
        "weights": [
            {
                "hypothesis_type": w.hypothesis_type,
                "success_rate": w.success_rate,
                "avg_pnl": w.avg_pnl,
                "success_modifier": w.success_modifier,
                "pnl_modifier": w.pnl_modifier,
                "adaptive_modifier": w.adaptive_modifier,
                "final_weight": w.final_weight,
                "observations": w.observations,
                "status": _get_modifier_status(w.adaptive_modifier),
            }
            for w in weights
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/summary/{symbol}", response_model=Dict[str, Any])
async def get_adaptive_summary(symbol: str):
    """
    Get summary of adaptive weights for a symbol.
    
    Returns boost/penalize counts and best/worst performers.
    """
    # Try engine first (has latest data)
    engine = get_adaptive_weight_engine()
    summary = engine.get_summary(symbol.upper())
    
    # Fallback to MongoDB if no in-memory data
    if summary.total_hypothesis_types == 0:
        registry = get_adaptive_weight_registry()
        summary = registry.get_summary(symbol.upper())
    
    return {
        "symbol": summary.symbol,
        "totals": {
            "hypothesis_types": summary.total_hypothesis_types,
            "observations": summary.total_observations,
        },
        "modifiers": {
            "average": summary.avg_adaptive_modifier,
            "max": summary.max_adaptive_modifier,
            "min": summary.min_adaptive_modifier,
        },
        "distribution": {
            "boosted": summary.boosted_count,
            "penalized": summary.penalized_count,
            "neutral": summary.neutral_count,
        },
        "performers": {
            "best_hypothesis": summary.best_hypothesis,
            "best_modifier": summary.best_modifier,
            "worst_hypothesis": summary.worst_hypothesis,
            "worst_modifier": summary.worst_modifier,
        },
        "last_updated": summary.last_updated.isoformat() if summary.last_updated else None,
    }


@router.post("/recompute/{symbol}", response_model=Dict[str, Any])
async def recompute_adaptive_weights(symbol: str):
    """
    Force recompute of adaptive weights.
    
    Recalculates all modifiers from latest outcome data.
    """
    try:
        engine = get_adaptive_weight_engine()
        
        # Recompute
        weights = engine.generate_adaptive_weights(symbol.upper())
        
        # Save to MongoDB
        if weights:
            registry = get_adaptive_weight_registry()
            registry.save_weights_batch(symbol.upper(), weights)
        
        # Calculate summary stats
        if weights:
            boosted = sum(1 for w in weights if w.adaptive_modifier > 1.0)
            penalized = sum(1 for w in weights if w.adaptive_modifier < 1.0)
        else:
            boosted = penalized = 0
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "weights_computed": len(weights),
            "boosted_count": boosted,
            "penalized_count": penalized,
            "weights": [
                {
                    "hypothesis_type": w.hypothesis_type,
                    "adaptive_modifier": w.adaptive_modifier,
                    "final_weight": w.final_weight,
                    "status": _get_modifier_status(w.adaptive_modifier),
                }
                for w in weights
            ],
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Adaptive weight recompute failed: {str(e)}",
        )


def _get_modifier_status(modifier: float) -> str:
    """Get human-readable status for modifier."""
    if modifier > 1.05:
        return "BOOSTED"
    elif modifier < 0.95:
        return "PENALIZED"
    else:
        return "NEUTRAL"
