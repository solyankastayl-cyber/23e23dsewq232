"""
Selection Routes (STG5)
=======================

API endpoints for Strategy Comparison and Selection.

Endpoints:
- GET  /api/strategy-selection/health              - Module health
- GET  /api/strategy-selection/config              - Get selection config
- POST /api/strategy-selection/config              - Update config
- GET  /api/strategy-selection/best                - Get best strategy now
- GET  /api/strategy-selection/ranking             - Get full ranking
- GET  /api/strategy-selection/symbol/{symbol}     - Best for symbol
- GET  /api/strategy-selection/regime/{regime}     - Best for regime
- GET  /api/strategy-selection/profile/{profile}   - Best for profile
- GET  /api/strategy-selection/compare             - Compare strategies
- GET  /api/strategy-selection/{strategy_id}/score - Get strategy score
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from .selection_service import selection_service


router = APIRouter(prefix="/api/strategy-selection", tags=["STG5 - Strategy Selection"])


# ===========================================
# Request Models
# ===========================================

class ConfigUpdateInput(BaseModel):
    """Input for config update"""
    weights: Optional[Dict[str, float]] = None
    thresholds: Optional[Dict[str, float]] = None


class SelectionContextInput(BaseModel):
    """Input for selection with context"""
    symbol: Optional[str] = None
    regime: Optional[str] = None
    profile_id: Optional[str] = None


# ===========================================
# Health & Config
# ===========================================

@router.get("/health")
async def get_health():
    """Get STG5 module health."""
    return selection_service.get_health()


@router.get("/config")
async def get_config():
    """Get selection configuration."""
    return selection_service.get_config()


@router.post("/config")
async def update_config(input: ConfigUpdateInput):
    """Update selection configuration."""
    selection_service.update_config(input.dict(exclude_none=True))
    return {
        "success": True,
        "config": selection_service.get_config()
    }


# ===========================================
# Selection Endpoints
# ===========================================

@router.get("/best")
async def get_best_strategy(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    regime: Optional[str] = Query(None, description="Current market regime"),
    profile: Optional[str] = Query(None, description="Current profile")
):
    """
    Get the best strategy for current conditions.
    
    Returns the top-ranked strategy with reason summary.
    """
    result = selection_service.select_best_strategy(
        symbol=symbol,
        regime=regime,
        profile_id=profile
    )
    
    return result.to_dict()


@router.post("/best")
async def select_best_strategy(input: SelectionContextInput):
    """Select best strategy with full context."""
    result = selection_service.select_best_strategy(
        symbol=input.symbol,
        regime=input.regime,
        profile_id=input.profile_id
    )
    return result.to_dict()


@router.get("/ranking")
async def get_ranking(
    regime: Optional[str] = Query(None, description="Current market regime"),
    profile: Optional[str] = Query(None, description="Current profile")
):
    """
    Get full strategy ranking.
    
    Returns all strategies ranked by selection score.
    """
    result = selection_service.select_best_strategy(
        regime=regime,
        profile_id=profile
    )
    
    return {
        "context": {
            "regime": regime,
            "profile": profile
        },
        "ranking": [r.to_dict() for r in result.ranking],
        "count": len(result.ranking)
    }


# ===========================================
# Context-Specific Selection
# ===========================================

@router.get("/symbol/{symbol}")
async def select_for_symbol(symbol: str):
    """Get best strategy for a specific symbol."""
    result = selection_service.select_for_symbol(symbol)
    return result.to_dict()


@router.get("/regime/{regime}")
async def select_for_regime(regime: str):
    """
    Get best strategy for a specific market regime.
    
    Regimes: TRENDING, RANGE, HIGH_VOLATILITY, LOW_VOLATILITY, TRANSITION
    """
    result = selection_service.select_for_regime(regime)
    return result.to_dict()


@router.get("/profile/{profile_id}")
async def select_for_profile(profile_id: str):
    """
    Get best strategy for a specific profile.
    
    Profiles: CONSERVATIVE, BALANCED, AGGRESSIVE
    """
    result = selection_service.select_for_profile(profile_id)
    return result.to_dict()


# ===========================================
# Comparison
# ===========================================

@router.get("/compare")
async def compare_strategies(
    strategies: Optional[str] = Query(None, description="Comma-separated strategy IDs (optional)"),
    regime: Optional[str] = Query(None, description="Current regime for context"),
    profile: Optional[str] = Query(None, description="Current profile for context")
):
    """
    Compare strategies side-by-side.
    
    If no strategies specified, compares all enabled strategies.
    """
    strategy_ids = None
    if strategies:
        strategy_ids = [s.strip() for s in strategies.split(",")]
    
    comparisons = selection_service.compare_strategies(
        strategy_ids=strategy_ids,
        regime=regime,
        profile_id=profile
    )
    
    return {
        "context": {
            "regime": regime,
            "profile": profile
        },
        "comparison": [c.to_dict() for c in comparisons],
        "count": len(comparisons)
    }


# ===========================================
# Individual Strategy Score
# ===========================================

@router.get("/{strategy_id}/score")
async def get_strategy_score(
    strategy_id: str,
    regime: Optional[str] = Query(None, description="Current regime"),
    profile: Optional[str] = Query(None, description="Current profile")
):
    """Get detailed selection score for a specific strategy."""
    score = selection_service.get_strategy_score(
        strategy_id=strategy_id,
        regime=regime,
        profile_id=profile
    )
    
    if not score:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
    
    return score.to_dict()


# ===========================================
# History
# ===========================================

@router.get("/history")
async def get_selection_history(
    limit: int = Query(20, ge=1, le=100)
):
    """Get selection history."""
    history = selection_service.get_selection_history(limit=limit)
    
    return {
        "history": [h.to_dict() for h in history],
        "count": len(history)
    }


@router.get("/last")
async def get_last_selection():
    """Get the last selection result."""
    last = selection_service.get_last_selection()
    
    if not last:
        return {"message": "No selections performed yet"}
    
    return last.to_dict()
