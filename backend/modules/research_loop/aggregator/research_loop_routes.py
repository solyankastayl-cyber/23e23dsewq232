"""
PHASE 20.4 — Research Loop Routes
=================================
API endpoints for Research Loop Aggregator.

Endpoints:
- GET  /api/v1/research-loop/state
- GET  /api/v1/research-loop/summary
- GET  /api/v1/research-loop/registry
- POST /api/v1/research-loop/recompute
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from typing import Optional

from modules.research_loop.aggregator.research_loop_engine import (
    get_research_loop_engine,
)
from modules.research_loop.aggregator.research_loop_registry import (
    get_research_loop_registry,
)

router = APIRouter(
    prefix="/api/v1/research-loop",
    tags=["PHASE 20.4 - Research Loop Aggregator"],
)


@router.get("/state")
async def get_loop_state():
    """
    Get full research loop state.
    
    Returns unified state with all aggregated data and signals.
    """
    try:
        engine = get_research_loop_engine()
        state = engine.compute_state()
        
        return {
            "status": "ok",
            "phase": "20.4",
            "data": state.to_full_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_loop_summary():
    """
    Get research loop summary.
    
    Returns compact summary of loop state.
    """
    try:
        engine = get_research_loop_engine()
        summary = engine.get_summary()
        
        return {
            "status": "ok",
            "phase": "20.4",
            "data": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registry")
async def get_loop_registry():
    """
    Get research loop registry statistics.
    
    Returns history and state distribution.
    """
    try:
        registry = get_research_loop_registry()
        stats = registry.get_stats()
        
        return {
            "status": "ok",
            "phase": "20.4",
            "data": stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_loop_history(limit: int = 20):
    """
    Get research loop state history.
    """
    try:
        registry = get_research_loop_registry()
        history = registry.get_history(limit=limit)
        
        return {
            "status": "ok",
            "phase": "20.4",
            "history": [h.to_dict() for h in history],
            "count": len(history),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recompute")
async def recompute_loop():
    """
    Recompute research loop state and record to registry.
    
    Returns new state after recomputation.
    """
    try:
        engine = get_research_loop_engine()
        state = engine.recompute()
        
        return {
            "status": "ok",
            "phase": "20.4",
            "message": "Research loop state recomputed and recorded",
            "data": state.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals")
async def get_loop_signals():
    """
    Get detailed signal analysis.
    """
    try:
        engine = get_research_loop_engine()
        state = engine.compute_state()
        
        return {
            "status": "ok",
            "phase": "20.4",
            "loop_state": state.loop_state.value,
            "loop_score": round(state.loop_score, 4),
            "signals": [s.to_dict() for s in state.signals],
            "strongest_signal": state.strongest_signal,
            "weakest_signal": state.weakest_signal,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_recommendations():
    """
    Get all current recommendations from research loop.
    """
    try:
        engine = get_research_loop_engine()
        state = engine.compute_state()
        
        return {
            "status": "ok",
            "phase": "20.4",
            "loop_state": state.loop_state.value,
            "recommendations": {
                "weight_adjustments": {
                    "increase": state.recommended_increases,
                    "decrease": state.recommended_decreases,
                },
                "lifecycle_transitions": {
                    "promote": state.recommended_promotions,
                    "demote": state.recommended_demotions,
                    "freeze": state.recommended_freezes,
                    "retire": state.recommended_retires,
                },
                "critical_patterns_to_address": state.critical_failure_patterns,
            },
            "modifiers": {
                "confidence": round(state.confidence_modifier, 4),
                "capital": round(state.capital_modifier, 4),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
