"""
Recovery Routes
===============

API endpoints for Recovery Engine (PHASE 1.4)
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .recovery_service import recovery_service


router = APIRouter(prefix="/api/recovery", tags=["phase4-recovery"])


# ===========================================
# Request Models
# ===========================================

class RecoveryDecisionRequest(BaseModel):
    """Request for recovery decision"""
    strategy: str = Field(..., description="Strategy type")
    position_id: str = Field("", description="Position ID")
    entry_price: float = Field(..., description="Entry price")
    current_price: float = Field(..., description="Current price")
    stop_price: float = Field(..., description="Stop price")
    direction: str = Field("LONG", description="LONG or SHORT")
    current_size: float = Field(1.0, description="Current position size")
    current_adds: int = Field(0, description="Number of adds already made")
    portfolio_exposure_pct: float = Field(2.0, description="Portfolio exposure %")
    daily_loss_pct: float = Field(0.0, description="Daily PnL %")
    regime: str = Field("RANGE", description="Market regime")
    support_holding: bool = Field(True, description="Is support holding")
    range_boundary_valid: bool = Field(True, description="Is range valid")
    structure_broken: bool = Field(False, description="Is structure broken")
    trend_acceleration: bool = Field(False, description="Is trend accelerating")
    liquidity_cascade: bool = Field(False, description="Is liquidity cascading")
    vwap_distance_pct: Optional[float] = Field(None, description="Distance from VWAP %")


class StructureCheckRequest(BaseModel):
    """Request for structure check"""
    support_holding: bool = Field(True, description="Is support holding")
    range_boundary_valid: bool = Field(True, description="Is range valid")
    structure_broken: bool = Field(False, description="Is structure broken")
    trend_acceleration: bool = Field(False, description="Is trend accelerating")
    liquidity_cascade: bool = Field(False, description="Is liquidity cascading")
    vwap_distance_pct: Optional[float] = Field(None, description="Distance from VWAP %")


class RiskCheckRequest(BaseModel):
    """Request for risk limits check"""
    strategy: str = Field(..., description="Strategy type")
    current_adds: int = Field(0, description="Number of adds")
    current_exposure: float = Field(1.0, description="Current exposure")
    portfolio_exposure_pct: float = Field(2.0, description="Portfolio exposure %")
    daily_loss_pct: float = Field(0.0, description="Daily PnL %")


class AddSizeRequest(BaseModel):
    """Request for add size calculation"""
    strategy: str = Field(..., description="Strategy type")
    base_size: float = Field(1.0, description="Base position size")
    current_adds: int = Field(0, description="Number of adds")
    regime: str = Field("RANGE", description="Market regime")


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for Recovery Engine"""
    return recovery_service.get_health()


# ===========================================
# Main Decision Endpoint
# ===========================================

@router.post("/decision")
async def evaluate_recovery(request: RecoveryDecisionRequest):
    """
    Evaluate recovery decision.
    
    Main endpoint - runs full decision pipeline:
    1. Strategy compatibility
    2. Regime filter
    3. Structure filter
    4. Position health
    5. Risk limits
    6. Final decision
    """
    return recovery_service.evaluate_recovery(
        strategy=request.strategy,
        position_id=request.position_id,
        entry_price=request.entry_price,
        current_price=request.current_price,
        stop_price=request.stop_price,
        direction=request.direction,
        current_size=request.current_size,
        current_adds=request.current_adds,
        portfolio_exposure_pct=request.portfolio_exposure_pct,
        daily_loss_pct=request.daily_loss_pct,
        regime=request.regime,
        support_holding=request.support_holding,
        range_boundary_valid=request.range_boundary_valid,
        structure_broken=request.structure_broken,
        trend_acceleration=request.trend_acceleration,
        liquidity_cascade=request.liquidity_cascade,
        vwap_distance_pct=request.vwap_distance_pct
    )


# ===========================================
# Strategy Endpoints
# ===========================================

@router.get("/strategies")
async def get_strategy_compatibility():
    """
    Get strategy-recovery compatibility matrix.
    """
    return recovery_service.get_strategy_compatibility()


@router.get("/strategies/{strategy}")
async def get_strategy_policy(strategy: str):
    """
    Get recovery policy for specific strategy.
    """
    policy = recovery_service.get_strategy_policy(strategy)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy} not found")
    return policy


@router.get("/strategies/{strategy}/allowed")
async def check_strategy_allowed(strategy: str):
    """
    Check if recovery is allowed for strategy.
    """
    return recovery_service.is_recovery_allowed(strategy)


# ===========================================
# Regime Endpoints
# ===========================================

@router.get("/regime")
async def get_regime_compatibility():
    """
    Get regime-recovery compatibility matrix.
    """
    return recovery_service.get_regime_compatibility()


@router.get("/regime/{regime}")
async def check_regime(regime: str):
    """
    Check if regime allows recovery.
    """
    return recovery_service.check_regime(regime)


# ===========================================
# Structure Endpoints
# ===========================================

@router.get("/structure")
async def get_structure_requirements():
    """
    Get structure requirements for recovery.
    """
    return recovery_service.get_structure_requirements()


@router.post("/structure/check")
async def check_structure(request: StructureCheckRequest):
    """
    Check if market structure allows recovery.
    """
    return recovery_service.check_structure(
        support_holding=request.support_holding,
        range_boundary_valid=request.range_boundary_valid,
        structure_broken=request.structure_broken,
        trend_acceleration=request.trend_acceleration,
        liquidity_cascade=request.liquidity_cascade,
        vwap_distance_pct=request.vwap_distance_pct
    )


# ===========================================
# Risk Limits Endpoints
# ===========================================

@router.get("/limits")
async def get_risk_limits():
    """
    Get risk limits for recovery.
    """
    return recovery_service.get_risk_limits()


@router.post("/limits/check")
async def check_risk_limits(request: RiskCheckRequest):
    """
    Check if within risk limits.
    """
    return recovery_service.check_risk_limits(
        strategy=request.strategy,
        current_adds=request.current_adds,
        current_exposure=request.current_exposure,
        portfolio_exposure_pct=request.portfolio_exposure_pct,
        daily_loss_pct=request.daily_loss_pct
    )


@router.post("/limits/add-size")
async def calculate_add_size(request: AddSizeRequest):
    """
    Calculate recommended add size.
    """
    return recovery_service.calculate_add_size(
        strategy=request.strategy,
        base_size=request.base_size,
        current_adds=request.current_adds,
        regime=request.regime
    )


# ===========================================
# Rules & Types
# ===========================================

@router.get("/types")
async def get_recovery_types():
    """
    Get all recovery types.
    """
    return {
        "types": recovery_service.get_recovery_types(),
        "count": len(recovery_service.get_recovery_types())
    }


@router.get("/rules")
async def get_complete_rules():
    """
    Get all recovery rules.
    """
    return recovery_service.get_complete_rules()


@router.get("/rules/blocking")
async def get_blocking_rules():
    """
    Get all blocking rules.
    """
    return {
        "rules": recovery_service.get_blocking_rules(),
        "count": len(recovery_service.get_blocking_rules())
    }


# ===========================================
# Event Ledger
# ===========================================

@router.get("/events")
async def get_recent_events(limit: int = Query(50, le=200)):
    """
    Get recent recovery events.
    """
    return {
        "events": recovery_service.get_recent_events(limit),
        "limit": limit
    }


@router.get("/events/summary")
async def get_event_summary():
    """
    Get recovery event summary.
    """
    return recovery_service.get_event_summary()
