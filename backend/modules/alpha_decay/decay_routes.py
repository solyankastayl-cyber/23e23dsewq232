"""
Alpha Decay Routes

PHASE 43.8 — Alpha Decay Engine

API endpoints for signal decay management.

Endpoints:
- GET  /api/v1/alpha-decay/{hypothesis_id} - Get decay state
- GET  /api/v1/alpha-decay/summary - Get summary
- POST /api/v1/alpha-decay/create - Create decay state
- POST /api/v1/alpha-decay/recompute - Recompute all
- POST /api/v1/alpha-decay/expire - Expire old signals
- GET  /api/v1/alpha-decay/statistics - Get statistics
- GET  /api/v1/alpha-decay/health - Health check
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1/alpha-decay", tags=["Alpha Decay"])


# ══════════════════════════════════════════════════════════════
# Main Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def alpha_decay_health():
    """Alpha Decay Engine health check."""
    from .decay_engine import get_alpha_decay_engine
    from .decay_types import SIGNAL_HALF_LIVES, DECAY_STAGE_THRESHOLDS
    
    engine = get_alpha_decay_engine()
    summary = engine.get_summary()
    
    return {
        "status": "ok",
        "phase": "43.8",
        "module": "Alpha Decay Engine",
        "active_signals": summary.total_signals,
        "by_stage": {
            "fresh": summary.fresh_count,
            "active": summary.active_count,
            "weakening": summary.weakening_count,
            "expired": summary.expired_count,
        },
        "avg_decay_factor": round(summary.avg_decay_factor, 4),
        "half_lives": {st.value: hl for st, hl in SIGNAL_HALF_LIVES.items()},
        "thresholds": DECAY_STAGE_THRESHOLDS,
        "effects": [
            "↓ Reduces unnecessary trades",
            "↓ Reduces noise trades",
            "↑ Improves timing",
            "↑ Increases Sharpe",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/state/{hypothesis_id}")
async def get_decay_state(hypothesis_id: str):
    """
    Get decay state for a hypothesis.
    
    Returns decay factor, adjusted confidence, and stage.
    """
    from .decay_engine import get_alpha_decay_engine
    
    engine = get_alpha_decay_engine()
    result = engine.compute_decay(hypothesis_id)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"No decay state for: {hypothesis_id}")
    
    return {
        "status": "ok",
        "phase": "43.8",
        **result.model_dump(),
    }


@router.get("/summary/all")
async def get_decay_summary(symbol: Optional[str] = None):
    """
    Get summary of all decay states.
    
    Optionally filter by symbol.
    """
    from .decay_engine import get_alpha_decay_engine
    
    engine = get_alpha_decay_engine()
    summary = engine.get_summary(symbol)
    
    return {
        "status": "ok",
        "phase": "43.8",
        **summary.model_dump(),
    }


@router.get("/statistics/all")
async def get_decay_statistics():
    """Get decay engine statistics."""
    from .decay_engine import get_alpha_decay_engine
    
    engine = get_alpha_decay_engine()
    return engine.get_statistics()


# ══════════════════════════════════════════════════════════════
# Create/Update Operations
# ══════════════════════════════════════════════════════════════

@router.post("/create")
async def create_decay_state(
    hypothesis_id: str = Query(..., description="Unique hypothesis ID"),
    symbol: str = Query(..., description="Symbol (e.g., BTC)"),
    initial_confidence: float = Query(..., description="Initial confidence (0-1)"),
    signal_type: str = Query(default="DEFAULT", description="Signal type for half-life"),
    source: str = Query(default="api", description="Source of signal"),
):
    """
    Create a new decay state for tracking.
    
    Signal types and their half-lives:
    - TREND: 120 min
    - BREAKOUT: 90 min
    - MEAN_REVERSION: 30 min
    - FRACTAL: 180 min
    - CAPITAL_FLOW: 240 min
    - REGIME: 360 min
    - DEFAULT: 60 min
    """
    from .decay_engine import get_alpha_decay_engine
    from .decay_types import SignalType
    
    try:
        sig_type = SignalType(signal_type.upper())
    except ValueError:
        sig_type = SignalType.DEFAULT
    
    engine = get_alpha_decay_engine()
    state = engine.create_decay_state(
        hypothesis_id=hypothesis_id,
        symbol=symbol,
        initial_confidence=initial_confidence,
        signal_type=sig_type,
        source=source,
    )
    
    return {
        "status": "ok",
        "phase": "43.8",
        "created": True,
        "decay_id": state.decay_id,
        "hypothesis_id": state.hypothesis_id,
        "half_life_minutes": state.half_life_minutes,
        "signal_type": state.signal_type.value,
    }


@router.post("/recompute")
async def recompute_all_decay():
    """
    Recompute decay for all active states.
    
    Called periodically by scheduler.
    """
    from .decay_engine import get_alpha_decay_engine
    
    engine = get_alpha_decay_engine()
    results = engine.recompute_all()
    
    return {
        "status": "ok",
        "phase": "43.8",
        "recomputed": len(results),
        "fresh": sum(1 for r in results if r.decay_stage == "FRESH"),
        "active": sum(1 for r in results if r.decay_stage == "ACTIVE"),
        "weakening": sum(1 for r in results if r.decay_stage == "WEAKENING"),
        "expired": sum(1 for r in results if r.decay_stage == "EXPIRED"),
        "blocked": sum(1 for r in results if r.execution_blocked),
    }


@router.post("/expire")
async def expire_old_signals(max_age_hours: int = Query(default=24)):
    """
    Expire signals older than max_age_hours.
    
    Marks signals as expired and blocks execution.
    """
    from .decay_engine import get_alpha_decay_engine
    
    engine = get_alpha_decay_engine()
    expired_count = engine.expire_old_signals(max_age_hours)
    
    return {
        "status": "ok",
        "phase": "43.8",
        "expired_count": expired_count,
        "max_age_hours": max_age_hours,
    }


@router.post("/remove-expired")
async def remove_expired():
    """Remove expired states from cache."""
    from .decay_engine import get_alpha_decay_engine
    
    engine = get_alpha_decay_engine()
    removed = engine.remove_expired()
    
    return {
        "status": "ok",
        "phase": "43.8",
        "removed_count": removed,
    }


# ══════════════════════════════════════════════════════════════
# Integration Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/confidence/{hypothesis_id}")
async def get_confidence_modifier(hypothesis_id: str):
    """
    Get decay-adjusted confidence.
    
    For Hypothesis Engine integration.
    """
    from .decay_engine import get_alpha_decay_engine
    
    engine = get_alpha_decay_engine()
    state = engine.get_state(hypothesis_id)
    
    if not state:
        raise HTTPException(status_code=404, detail=f"No decay state for: {hypothesis_id}")
    
    result = engine.get_confidence_modifier(hypothesis_id, state.initial_confidence)
    
    return {
        "status": "ok",
        "phase": "43.8",
        "integration": "hypothesis_engine",
        **result,
    }


@router.get("/position-size/{hypothesis_id}")
async def get_position_size_modifier(
    hypothesis_id: str,
    base_size: float = Query(default=1.0),
):
    """
    Get decay-adjusted position size.
    
    For Portfolio Manager integration.
    """
    from .decay_engine import get_alpha_decay_engine
    
    engine = get_alpha_decay_engine()
    result = engine.get_position_size_modifier(hypothesis_id, base_size)
    
    return {
        "status": "ok",
        "phase": "43.8",
        "integration": "portfolio_manager",
        **result,
    }


@router.get("/execution-check/{hypothesis_id}")
async def check_execution_eligibility(hypothesis_id: str):
    """
    Check if signal is eligible for execution.
    
    For Execution Brain integration.
    """
    from .decay_engine import get_alpha_decay_engine
    
    engine = get_alpha_decay_engine()
    result = engine.check_execution_eligibility(hypothesis_id)
    
    return {
        "status": "ok",
        "phase": "43.8",
        "integration": "execution_brain",
        **result,
    }
