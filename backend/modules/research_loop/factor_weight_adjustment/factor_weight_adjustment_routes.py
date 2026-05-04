"""
PHASE 20.2 — Factor Weight Adjustment Routes
============================================
API endpoints for Factor Weight Adjustment Engine.

Endpoints:
- GET /api/v1/research-loop/factor-weight-adjustments
- GET /api/v1/research-loop/factor-weight-adjustments/summary
- GET /api/v1/research-loop/factor-weight-adjustments/{factor}
- POST /api/v1/research-loop/factor-weight-adjustments/recompute
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timezone

from modules.research_loop.factor_weight_adjustment import (
    get_factor_weight_adjustment_engine,
    get_factor_weight_registry,
    AdjustmentAction,
    AdjustmentStrength,
    WEIGHT_MIN,
    WEIGHT_MAX,
)


router = APIRouter(
    prefix="/api/v1/research-loop/factor-weight-adjustments",
    tags=["Research Loop - Factor Weight Adjustments"]
)


# ══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def factor_weight_adjustments_health():
    """Factor Weight Adjustment Engine health check."""
    try:
        engine = get_factor_weight_adjustment_engine()
        registry = get_factor_weight_registry()
        
        # Quick test
        summary = engine.compute_adjustments()
        
        return {
            "status": "healthy",
            "phase": "20.2",
            "module": "Factor Weight Adjustment Engine",
            "description": "Self-learning loop - recommends factor weight adjustments based on failure patterns",
            "capabilities": [
                "Weight Adjustment Recommendations",
                "Policy-based Decision Making",
                "Registry Persistence",
                "History Tracking",
            ],
            "adjustment_actions": [a.value for a in AdjustmentAction],
            "adjustment_strengths": [s.value for s in AdjustmentStrength],
            "weight_bounds": {"min": WEIGHT_MIN, "max": WEIGHT_MAX},
            "test_result": {
                "total_factors": summary.total_factors,
                "increased": len(summary.increased),
                "decreased": len(summary.decreased),
                "held": len(summary.held),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ══════════════════════════════════════════════════════════════
# ADJUSTMENTS ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("")
async def get_factor_weight_adjustments():
    """
    Get all factor weight adjustment recommendations.
    
    Computes recommendations based on current failure patterns.
    """
    try:
        engine = get_factor_weight_adjustment_engine()
        summary = engine.compute_adjustments()
        
        return {
            "status": "ok",
            "data": summary.to_full_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_factor_weight_adjustments_summary():
    """
    Get factor weight adjustments summary.
    
    Returns compact summary without full adjustment details.
    """
    try:
        engine = get_factor_weight_adjustment_engine()
        summary = engine.compute_adjustments()
        
        return {
            "status": "ok",
            "data": summary.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registry")
async def get_factor_weight_registry_data():
    """
    Get current factor weight registry state.
    
    Returns all factors with their current weights and states.
    """
    try:
        registry = get_factor_weight_registry()
        summary = registry.get_registry_summary()
        
        return {
            "status": "ok",
            "data": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{factor}")
async def get_factor_adjustment(factor: str):
    """
    Get adjustment recommendation for specific factor.
    """
    try:
        engine = get_factor_weight_adjustment_engine()
        registry = get_factor_weight_registry()
        
        # Check if factor exists
        factor_state = registry.get_weight(factor)
        if factor_state is None:
            raise HTTPException(
                status_code=404,
                detail=f"Factor '{factor}' not found. Available: {registry.get_factor_names()}"
            )
        
        adjustment = engine.compute_factor_adjustment(factor)
        
        # Get history
        history = registry.get_recent_adjustments(factor, limit=5)
        
        return {
            "status": "ok",
            "data": adjustment.to_dict() if adjustment else None,
            "current_state": factor_state.to_dict(),
            "history": history,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recompute")
async def recompute_factor_weight_adjustments():
    """
    Recompute and apply all factor weight adjustments.
    
    WARNING: This applies recommendations to the registry.
    In production, this would require governance approval.
    """
    try:
        engine = get_factor_weight_adjustment_engine()
        summary = engine.recompute_all()
        
        return {
            "status": "ok",
            "message": "Adjustments recomputed and applied",
            "data": summary.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
