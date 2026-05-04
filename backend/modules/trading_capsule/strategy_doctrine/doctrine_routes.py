"""
Strategy Doctrine Routes
========================

API endpoints for Strategy Doctrine (PHASE 1.1)
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .doctrine_service import doctrine_service
from .doctrine_types import StrategyType, RegimeType, ProfileType, TimeframeType


router = APIRouter(prefix="/api/strategy-doctrine", tags=["phase1-doctrine"])


# ===========================================
# Request Models
# ===========================================

class CompatibilityCheckRequest(BaseModel):
    """Request for compatibility check"""
    strategy: str = Field(..., description="Strategy type")
    regime: Optional[str] = Field(None, description="Regime type")
    profile: Optional[str] = Field(None, description="Profile type")
    timeframe: Optional[str] = Field(None, description="Timeframe")


class StrategySelectionRequest(BaseModel):
    """Request for strategy selection"""
    regime: str = Field(..., description="Current regime")
    profile: str = Field(..., description="Risk profile")
    candidates: Optional[List[str]] = Field(None, description="Candidate strategies")


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for Strategy Doctrine"""
    return doctrine_service.get_health()


# ===========================================
# Strategy Definitions
# ===========================================

@router.get("/strategies")
async def get_all_strategies():
    """
    Get all strategy definitions.
    
    Returns complete doctrine for each strategy including:
    - Regime compatibility
    - Profile compatibility
    - Timeframe preferences
    - Asset preferences
    - Strengths/weaknesses
    - Recovery policy
    """
    strategies = doctrine_service.get_all_strategies()
    return {
        "strategies": [s.to_dict() for s in strategies],
        "count": len(strategies),
        "timestamp": int(time.time() * 1000)
    }


@router.get("/strategies/{strategy_type}")
async def get_strategy_definition(strategy_type: str):
    """
    Get definition for specific strategy.
    """
    try:
        strategy = StrategyType(strategy_type.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid strategy type: {strategy_type}")
    
    definition = doctrine_service.get_strategy_definition(strategy)
    
    if not definition:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_type} not found")
    
    return definition.to_dict()


# ===========================================
# Compatibility Matrices
# ===========================================

@router.get("/regimes")
async def get_regime_matrix():
    """
    Get strategy-regime compatibility matrix.
    
    Shows which strategies are:
    - OPTIMAL for each regime
    - ALLOWED
    - CONDITIONAL (reduced confidence)
    - FORBIDDEN
    """
    return doctrine_service.get_regime_matrix()


@router.get("/profiles")
async def get_profile_matrix():
    """
    Get strategy-profile compatibility matrix.
    
    Shows which strategies work with:
    - CONSERVATIVE profile
    - BALANCED profile
    - AGGRESSIVE profile
    """
    return doctrine_service.get_profile_matrix()


# ===========================================
# Strategy Hierarchy
# ===========================================

@router.get("/hierarchy")
async def get_all_hierarchies():
    """
    Get strategy hierarchy for all regimes.
    
    Shows priority ranking of strategies per regime.
    """
    return doctrine_service.get_all_hierarchies()


@router.get("/hierarchy/{regime}")
async def get_regime_hierarchy(regime: str):
    """
    Get strategy hierarchy for specific regime.
    """
    try:
        regime_type = RegimeType(regime.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid regime: {regime}")
    
    return doctrine_service.get_strategy_hierarchy(regime_type)


# ===========================================
# Compatibility Checks
# ===========================================

@router.post("/compatibility")
async def check_compatibility(request: CompatibilityCheckRequest):
    """
    Check strategy compatibility with conditions.
    """
    try:
        strategy = StrategyType(request.strategy.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid strategy: {request.strategy}")
    
    regime = None
    profile = None
    timeframe = None
    
    if request.regime:
        try:
            regime = RegimeType(request.regime.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid regime: {request.regime}")
    
    if request.profile:
        try:
            profile = ProfileType(request.profile.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid profile: {request.profile}")
    
    if request.timeframe:
        try:
            timeframe = TimeframeType(request.timeframe.upper())
        except ValueError:
            pass  # Timeframe validation is optional
    
    return doctrine_service.check_strategy_compatibility(
        strategy=strategy,
        regime=regime,
        profile=profile,
        timeframe=timeframe
    )


@router.get("/compatibility/{strategy}")
async def get_strategy_compatibility(
    strategy: str,
    regime: Optional[str] = Query(None),
    profile: Optional[str] = Query(None)
):
    """
    Get compatibility for strategy (GET version).
    """
    try:
        strategy_type = StrategyType(strategy.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy}")
    
    regime_type = None
    profile_type = None
    
    if regime:
        try:
            regime_type = RegimeType(regime.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid regime: {regime}")
    
    if profile:
        try:
            profile_type = ProfileType(profile.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid profile: {profile}")
    
    return doctrine_service.check_strategy_compatibility(
        strategy=strategy_type,
        regime=regime_type,
        profile=profile_type
    )


# ===========================================
# Strategy Selection
# ===========================================

@router.post("/select")
async def select_strategy(request: StrategySelectionRequest):
    """
    Select best strategy for conditions.
    
    Uses doctrine rules to select optimal strategy based on:
    - Current regime
    - Risk profile
    - Strategy hierarchy
    - Blocking rules
    """
    try:
        regime = RegimeType(request.regime.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid regime: {request.regime}")
    
    try:
        profile = ProfileType(request.profile.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid profile: {request.profile}")
    
    candidates = None
    if request.candidates:
        candidates = []
        for c in request.candidates:
            try:
                candidates.append(StrategyType(c.upper()))
            except ValueError:
                pass
    
    return doctrine_service.select_best_strategy(
        regime=regime,
        profile=profile,
        candidates=candidates
    )


@router.get("/select/{regime}/{profile}")
async def select_strategy_get(regime: str, profile: str):
    """
    Select best strategy (GET version).
    """
    try:
        regime_type = RegimeType(regime.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid regime: {regime}")
    
    try:
        profile_type = ProfileType(profile.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid profile: {profile}")
    
    return doctrine_service.select_best_strategy(
        regime=regime_type,
        profile=profile_type
    )


# ===========================================
# Blocking Rules
# ===========================================

@router.get("/rules")
async def get_blocking_rules():
    """
    Get all blocking rules.
    
    Shows rules that:
    - Block strategies in certain conditions
    - Reduce confidence
    - Warn about suboptimal conditions
    """
    return doctrine_service.get_blocking_rules()


@router.get("/blocking/{strategy}")
async def get_blocking_decision(
    strategy: str,
    regime: Optional[str] = Query(None),
    profile: Optional[str] = Query(None)
):
    """
    Get blocking decision for strategy.
    """
    try:
        strategy_type = StrategyType(strategy.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy}")
    
    regime_type = None
    profile_type = None
    
    if regime:
        try:
            regime_type = RegimeType(regime.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid regime: {regime}")
    
    if profile:
        try:
            profile_type = ProfileType(profile.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid profile: {profile}")
    
    decision = doctrine_service.get_blocking_decision(
        strategy=strategy_type,
        regime=regime_type,
        profile=profile_type
    )
    
    return decision.to_dict()


# ===========================================
# Recovery Policy
# ===========================================

@router.get("/recovery/{strategy}")
async def get_recovery_policy(strategy: str):
    """
    Get recovery policy for strategy.
    
    Shows:
    - Whether recovery (averaging) is allowed
    - Conditions for recovery
    - Maximum adds allowed
    """
    try:
        strategy_type = StrategyType(strategy.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy}")
    
    return doctrine_service.get_recovery_policy(strategy_type)
