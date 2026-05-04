"""
Strategy Routes (STG1)
======================

API endpoints for Strategy Taxonomy.

Endpoints:
- GET  /api/strategies/health          - Module health
- GET  /api/strategies                 - List all strategies
- GET  /api/strategies/summary         - Registry summary
- GET  /api/strategies/{id}            - Get strategy details
- POST /api/strategies/{id}/enable     - Enable strategy
- POST /api/strategies/{id}/disable    - Disable strategy
- GET  /api/strategies/{id}/stats      - Get strategy stats
- GET  /api/strategies/for-regime      - Get strategies for regime
- GET  /api/strategies/for-profile     - Get strategies for profile
- GET  /api/strategies/best-match      - Get best matching strategy
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from .strategy_registry import strategy_registry
from .strategy_types import MarketRegime, ProfileType


router = APIRouter(prefix="/api/strategy-taxonomy", tags=["STG1 - Strategy Taxonomy"])


# ===========================================
# Health & Summary
# ===========================================

@router.get("/health")
async def get_health():
    """Get STG1 module health."""
    summary = strategy_registry.get_summary()
    return {
        "module": "Strategy Taxonomy",
        "phase": "STG1",
        "status": "healthy",
        "summary": summary
    }


@router.get("/summary")
async def get_summary():
    """Get strategy registry summary."""
    return strategy_registry.get_summary()


# ===========================================
# Strategy CRUD
# ===========================================

@router.get("")
async def list_strategies(
    enabled_only: bool = Query(False, description="Only return enabled strategies")
):
    """List all registered strategies."""
    strategies = strategy_registry.list_strategies(enabled_only=enabled_only)
    return {
        "strategies": [s.to_dict() for s in strategies],
        "count": len(strategies)
    }


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str):
    """Get strategy details."""
    strategy = strategy_registry.get_strategy(strategy_id)
    
    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
    
    stats = strategy_registry.get_stats(strategy_id)
    
    return {
        "strategy": strategy.to_dict(),
        "stats": stats.to_dict() if stats else None
    }


@router.post("/{strategy_id}/enable")
async def enable_strategy(strategy_id: str):
    """Enable a strategy."""
    success = strategy_registry.enable_strategy(strategy_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
    
    return {
        "success": True,
        "message": f"Strategy {strategy_id} enabled"
    }


@router.post("/{strategy_id}/disable")
async def disable_strategy(strategy_id: str):
    """Disable a strategy."""
    success = strategy_registry.disable_strategy(strategy_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
    
    return {
        "success": True,
        "message": f"Strategy {strategy_id} disabled"
    }


@router.get("/{strategy_id}/stats")
async def get_strategy_stats(strategy_id: str):
    """Get strategy statistics."""
    stats = strategy_registry.get_stats(strategy_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
    
    return stats.to_dict()


# ===========================================
# Compatibility Queries
# ===========================================

@router.get("/query/for-regime")
async def get_strategies_for_regime(
    regime: str = Query(..., description="Market regime: TRENDING, RANGE, HIGH_VOLATILITY, LOW_VOLATILITY, TRANSITION")
):
    """Get strategies compatible with market regime."""
    try:
        regime_enum = MarketRegime(regime.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid regime: {regime}")
    
    strategies = strategy_registry.get_strategies_for_regime(regime_enum)
    
    return {
        "regime": regime.upper(),
        "strategies": [s.to_dict() for s in strategies],
        "count": len(strategies)
    }


@router.get("/query/for-profile")
async def get_strategies_for_profile(
    profile: str = Query(..., description="Profile: CONSERVATIVE, BALANCED, AGGRESSIVE")
):
    """Get strategies compatible with profile."""
    try:
        profile_enum = ProfileType(profile.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid profile: {profile}")
    
    strategies = strategy_registry.get_strategies_for_profile(profile_enum)
    
    return {
        "profile": profile.upper(),
        "strategies": [s.to_dict() for s in strategies],
        "count": len(strategies)
    }


@router.get("/query/for-asset")
async def get_strategies_for_asset(
    asset: str = Query(..., description="Asset symbol: BTC, ETH, SOL, SPX, GOLD, DXY")
):
    """Get strategies compatible with asset."""
    strategies = strategy_registry.get_strategies_for_asset(asset.upper())
    
    return {
        "asset": asset.upper(),
        "strategies": [s.to_dict() for s in strategies],
        "count": len(strategies)
    }


@router.get("/query/best-match")
async def get_best_strategy(
    regime: str = Query(..., description="Market regime"),
    profile: str = Query(..., description="Trading profile"),
    asset: str = Query("BTC", description="Asset symbol")
):
    """
    Get best matching strategy for current conditions.
    
    Returns the most suitable strategy based on regime, profile, and asset.
    """
    try:
        regime_enum = MarketRegime(regime.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid regime: {regime}")
    
    try:
        profile_enum = ProfileType(profile.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid profile: {profile}")
    
    strategy = strategy_registry.get_best_strategy(
        regime=regime_enum,
        profile=profile_enum,
        asset=asset.upper()
    )
    
    if not strategy:
        return {
            "strategy": None,
            "message": f"No compatible strategy for regime={regime}, profile={profile}, asset={asset}"
        }
    
    return {
        "strategy": strategy.to_dict(),
        "matchCriteria": {
            "regime": regime.upper(),
            "profile": profile.upper(),
            "asset": asset.upper()
        }
    }


# ===========================================
# Types Reference
# ===========================================

@router.get("/types/regimes")
async def list_regimes():
    """List available market regimes."""
    return {
        "regimes": [r.value for r in MarketRegime]
    }


@router.get("/types/profiles")
async def list_profiles():
    """List available profiles."""
    return {
        "profiles": [p.value for p in ProfileType]
    }


@router.get("/types/strategy-types")
async def list_strategy_types():
    """List available strategy types."""
    from .strategy_types import StrategyType
    return {
        "strategyTypes": [t.value for t in StrategyType]
    }
