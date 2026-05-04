"""
Alpha Decay Monitor — Routes

API endpoints for decay monitoring.

Endpoints:
- GET /api/v1/alpha-factory/decay
- GET /api/v1/alpha-factory/decay/{factor_id}
- GET /api/v1/alpha-factory/decay/critical
- POST /api/v1/alpha-factory/decay/recompute
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from datetime import datetime, timezone

from .decay_engine import AlphaDecayEngine, get_alpha_decay_engine
from .decay_registry import AlphaDecayRegistry, get_alpha_decay_registry


router = APIRouter(prefix="/api/v1/alpha-factory/decay", tags=["alpha-decay"])


@router.get("", response_model=Dict[str, Any])
async def get_all_decay():
    """
    Get decay state for all factors.
    
    Computes decay if not already computed.
    Returns list of AlphaDecayState and summary.
    """
    engine = get_alpha_decay_engine()
    
    # Compute if no states yet
    states = engine.get_all_decay_states()
    if not states:
        states = await engine.compute_all_decay()
    
    summary = engine.get_summary()
    
    return {
        "factors": [
            {
                "factor_id": s.factor_id,
                "factor_name": s.factor_name,
                "current_alpha_score": s.current_alpha_score,
                "previous_alpha_score": s.previous_alpha_score,
                "alpha_drift": s.alpha_drift,
                "decay_rate": s.decay_rate,
                "decay_state": s.decay_state,
                "recommended_action": s.recommended_action,
                "confidence_modifier": s.confidence_modifier,
                "capital_modifier": s.capital_modifier,
                "reason": s.reason,
            }
            for s in states
        ],
        "summary": {
            "total_factors": summary.total_factors,
            "stable_count": summary.stable_count,
            "decaying_count": summary.decaying_count,
            "critical_count": summary.critical_count,
            "average_decay_rate": summary.average_decay_rate,
            "max_decay_rate": summary.max_decay_rate,
        },
        "count": len(states),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/critical", response_model=Dict[str, Any])
async def get_critical_factors():
    """
    Get all factors in CRITICAL decay state.
    
    These factors should be deprecated immediately.
    """
    engine = get_alpha_decay_engine()
    
    # Ensure decay is computed
    states = engine.get_all_decay_states()
    if not states:
        await engine.compute_all_decay()
    
    critical = engine.get_critical_factors()
    
    return {
        "critical_factors": [
            {
                "factor_id": s.factor_id,
                "factor_name": s.factor_name,
                "current_alpha_score": s.current_alpha_score,
                "previous_alpha_score": s.previous_alpha_score,
                "alpha_drift": s.alpha_drift,
                "decay_rate": s.decay_rate,
                "recommended_action": s.recommended_action,
                "reason": s.reason,
            }
            for s in critical
        ],
        "count": len(critical),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{factor_id}", response_model=Dict[str, Any])
async def get_factor_decay(factor_id: str):
    """
    Get decay state for a specific factor.
    """
    engine = get_alpha_decay_engine()
    
    # Ensure decay is computed
    states = engine.get_all_decay_states()
    if not states:
        await engine.compute_all_decay()
    
    state = engine.get_decay_state(factor_id)
    
    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"Factor {factor_id} not found"
        )
    
    return {
        "factor_id": state.factor_id,
        "factor_name": state.factor_name,
        "current_alpha_score": state.current_alpha_score,
        "previous_alpha_score": state.previous_alpha_score,
        "alpha_drift": state.alpha_drift,
        "decay_rate": state.decay_rate,
        "decay_state": state.decay_state,
        "recommended_action": state.recommended_action,
        "confidence_modifier": state.confidence_modifier,
        "capital_modifier": state.capital_modifier,
        "reason": state.reason,
        "computed_at": state.computed_at.isoformat(),
    }


@router.post("/recompute", response_model=Dict[str, Any])
async def recompute_decay():
    """
    Force recompute of all decay states.
    
    Also stores results in decay history.
    """
    try:
        engine = get_alpha_decay_engine()
        registry = get_alpha_decay_registry()
        
        # Recompute all decay
        states = await engine.recompute_decay()
        
        # Store in history
        await registry.store_decay_states_bulk(states)
        
        summary = engine.get_summary()
        
        return {
            "status": "ok",
            "recomputed": len(states),
            "summary": {
                "total_factors": summary.total_factors,
                "stable_count": summary.stable_count,
                "decaying_count": summary.decaying_count,
                "critical_count": summary.critical_count,
                "average_decay_rate": summary.average_decay_rate,
                "max_decay_rate": summary.max_decay_rate,
                "critical_factors": summary.critical_factors,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recompute failed: {str(e)}"
        )


@router.get("/history/{factor_id}", response_model=Dict[str, Any])
async def get_factor_decay_history(factor_id: str, limit: int = 50):
    """
    Get decay history for a specific factor.
    """
    registry = get_alpha_decay_registry()
    history = await registry.get_factor_history(factor_id, limit)
    
    return {
        "factor_id": factor_id,
        "history": [
            {
                "previous_alpha_score": h.previous_alpha_score,
                "current_alpha_score": h.current_alpha_score,
                "alpha_drift": h.alpha_drift,
                "decay_rate": h.decay_rate,
                "decay_state": h.decay_state,
                "recorded_at": h.recorded_at.isoformat(),
            }
            for h in history
        ],
        "count": len(history),
    }
