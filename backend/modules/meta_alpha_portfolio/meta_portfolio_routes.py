"""
Meta-Alpha Portfolio Routes

PHASE 45 — Meta-Alpha Portfolio Engine
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1/meta-alpha", tags=["Meta-Alpha Portfolio"])


@router.get("/health")
async def meta_alpha_health():
    """Meta-Alpha Portfolio Engine health check."""
    from .meta_portfolio_engine import get_meta_alpha_engine
    from .meta_portfolio_types import AlphaFamily
    
    engine = get_meta_alpha_engine()
    summary = engine.get_summary()
    
    return {
        "status": "ok",
        "phase": "45",
        "module": "Meta-Alpha Portfolio Engine",
        "alpha_families": [f.value for f in AlphaFamily],
        "dominant_family": summary["dominant_family"],
        "diversification": summary["diversification"],
        "total_signals": summary["total_signals"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/summary")
async def get_summary():
    """Get Meta-Alpha portfolio summary."""
    from .meta_portfolio_engine import get_meta_alpha_engine
    engine = get_meta_alpha_engine()
    return engine.get_summary()


@router.get("/state")
async def get_state():
    """Get full portfolio state."""
    from .meta_portfolio_engine import get_meta_alpha_engine
    engine = get_meta_alpha_engine()
    state = engine.get_state()
    return state.model_dump()


@router.get("/weights")
async def get_weights():
    """Get portfolio allocation weights by alpha family."""
    from .meta_portfolio_engine import get_meta_alpha_engine
    engine = get_meta_alpha_engine()
    return {
        "status": "ok",
        "allocation_weights": engine.get_portfolio_allocation_weights(),
        "risk_budget_weights": engine.get_risk_budget_weights(),
    }


@router.get("/family/{family_name}")
async def get_family_stats(family_name: str):
    """Get detailed stats for an alpha family."""
    from .meta_portfolio_engine import get_meta_alpha_engine
    from .meta_portfolio_types import AlphaFamily
    
    try:
        family = AlphaFamily(family_name.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown family: {family_name}")
    
    engine = get_meta_alpha_engine()
    return engine.get_family_stats(family)


@router.get("/hypothesis-modifier/{family_name}")
async def get_hypothesis_modifier(family_name: str):
    """Get hypothesis modifier for an alpha family."""
    from .meta_portfolio_engine import get_meta_alpha_engine
    from .meta_portfolio_types import AlphaFamily
    
    try:
        family = AlphaFamily(family_name.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown family: {family_name}")
    
    engine = get_meta_alpha_engine()
    result = engine.get_hypothesis_modifier(family)
    
    return {
        "status": "ok",
        "phase": "45",
        "integration": "hypothesis_engine",
        "alpha_family": family_name,
        **result,
    }


@router.post("/record-outcome")
async def record_outcome(
    hypothesis_id: str = Query(...),
    alpha_family: str = Query(...),
    symbol: str = Query(...),
    pnl_pct: float = Query(...),
    regime_at_entry: str = Query(default="UNKNOWN"),
    signal_age_at_execution: int = Query(default=0),
):
    """Record a trade outcome for learning."""
    from .meta_portfolio_engine import get_meta_alpha_engine
    from .meta_portfolio_types import AlphaFamily
    
    try:
        family = AlphaFamily(alpha_family.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown family: {alpha_family}")
    
    engine = get_meta_alpha_engine()
    outcome = engine.record_outcome(
        hypothesis_id=hypothesis_id,
        alpha_family=family,
        symbol=symbol,
        pnl_pct=pnl_pct,
        regime_at_entry=regime_at_entry,
        signal_age_at_execution=signal_age_at_execution,
    )
    
    return {
        "status": "ok",
        "outcome_id": outcome.outcome_id,
        "is_winner": outcome.is_winner,
    }


@router.post("/recompute")
async def recompute_weights():
    """Recompute all alpha family weights."""
    from .meta_portfolio_engine import get_meta_alpha_engine
    engine = get_meta_alpha_engine()
    state = engine.recompute_weights()
    
    return {
        "status": "ok",
        "recomputed": True,
        "dominant_family": state.dominant_alpha_family,
        "avg_meta_score": state.avg_meta_score,
    }
