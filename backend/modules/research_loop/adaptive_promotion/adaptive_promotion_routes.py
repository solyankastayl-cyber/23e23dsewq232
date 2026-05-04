"""
PHASE 20.3 — Adaptive Promotion Routes
======================================
API endpoints for Adaptive Promotion/Demotion Engine.

Endpoints:
- GET  /api/v1/research-loop/adaptive-promotion
- GET  /api/v1/research-loop/adaptive-promotion/summary
- GET  /api/v1/research-loop/adaptive-promotion/{factor}
- POST /api/v1/research-loop/adaptive-promotion/recompute
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from typing import Optional

from modules.research_loop.adaptive_promotion.adaptive_promotion_engine import (
    get_adaptive_promotion_engine,
)
from modules.research_loop.adaptive_promotion.adaptive_promotion_registry import (
    get_adaptive_promotion_registry,
)

router = APIRouter(
    prefix="/api/v1/research-loop/adaptive-promotion",
    tags=["PHASE 20.3 - Adaptive Promotion"],
)


@router.get("")
async def get_all_decisions():
    """
    Get lifecycle transition decisions for all factors.
    
    Returns full list of promotion/demotion recommendations.
    """
    try:
        engine = get_adaptive_promotion_engine()
        summary = engine.compute_all_decisions()
        
        return {
            "status": "ok",
            "phase": "20.3",
            "data": summary.to_full_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_summary():
    """
    Get summary of lifecycle decisions.
    
    Returns counts and factor names by action type.
    """
    try:
        engine = get_adaptive_promotion_engine()
        summary = engine.compute_all_decisions()
        
        return {
            "status": "ok",
            "phase": "20.3",
            "data": summary.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registry")
async def get_registry_stats():
    """
    Get registry statistics.
    
    Returns state distribution and transition counts.
    """
    try:
        registry = get_adaptive_promotion_registry()
        stats = registry.get_stats()
        
        return {
            "status": "ok",
            "phase": "20.3",
            "data": stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{factor_name}")
async def get_factor_decision(factor_name: str):
    """
    Get lifecycle decision for a specific factor.
    
    Returns current state and transition recommendation.
    """
    try:
        engine = get_adaptive_promotion_engine()
        decision = engine.compute_factor_decision(factor_name)
        
        if decision is None:
            raise HTTPException(status_code=404, detail=f"Factor '{factor_name}' not found")
        
        # Get full state from registry
        state = engine.get_factor_state(factor_name)
        
        return {
            "status": "ok",
            "phase": "20.3",
            "factor_name": factor_name,
            "decision": decision.to_dict(),
            "current_state": state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{factor_name}/history")
async def get_factor_history(factor_name: str, limit: int = 10):
    """
    Get transition history for a factor.
    """
    try:
        registry = get_adaptive_promotion_registry()
        history = registry.get_transition_history(factor_name, limit=limit)
        
        return {
            "status": "ok",
            "phase": "20.3",
            "factor_name": factor_name,
            "history": [t.to_dict() for t in history],
            "count": len(history),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recompute")
async def recompute_all():
    """
    Recompute and apply all lifecycle transitions.
    
    Note: This applies transitions to the registry.
    In production, this would require governance approval.
    """
    try:
        engine = get_adaptive_promotion_engine()
        summary = engine.recompute_all()
        
        return {
            "status": "ok",
            "phase": "20.3",
            "message": "Transitions recomputed and applied",
            "data": summary.to_dict(),
            "applied": {
                "promoted": summary.promoted,
                "demoted": summary.demoted,
                "frozen": summary.frozen,
                "retired": summary.retired,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/factors/by-state/{state}")
async def get_factors_by_state(state: str):
    """
    Get factors in a specific lifecycle state.
    """
    try:
        registry = get_adaptive_promotion_registry()
        
        # Validate state
        valid_states = ["SHADOW", "CANDIDATE", "LIVE", "REDUCED", "FROZEN", "RETIRED"]
        if state.upper() not in valid_states:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid state. Must be one of: {valid_states}"
            )
        
        from modules.research_loop.adaptive_promotion.adaptive_promotion_types import LifecycleState
        lifecycle_state = LifecycleState(state.upper())
        
        factors = registry.get_factors_by_state(lifecycle_state)
        
        return {
            "status": "ok",
            "phase": "20.3",
            "state": state.upper(),
            "factors": factors,
            "count": len(factors),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
