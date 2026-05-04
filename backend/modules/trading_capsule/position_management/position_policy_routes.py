"""
Position Policy Routes
======================

API endpoints for Position Management Policy (PHASE 1.3)
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .position_policy_service import position_policy_service


router = APIRouter(prefix="/api/position-policy", tags=["phase3-position-policy"])


# ===========================================
# Request Models
# ===========================================

class StopCalculationRequest(BaseModel):
    """Request for stop calculation"""
    strategy: str = Field(..., description="Strategy type")
    entry_price: float = Field(..., description="Entry price")
    direction: str = Field(..., description="LONG or SHORT")
    atr: Optional[float] = Field(None, description="Current ATR")
    swing_low: Optional[float] = Field(None, description="Recent swing low")
    swing_high: Optional[float] = Field(None, description="Recent swing high")
    support: Optional[float] = Field(None, description="Support level")
    resistance: Optional[float] = Field(None, description="Resistance level")


class TPCalculationRequest(BaseModel):
    """Request for TP calculation"""
    strategy: str = Field(..., description="Strategy type")
    entry_price: float = Field(..., description="Entry price")
    stop_price: float = Field(..., description="Stop price")
    direction: str = Field(..., description="LONG or SHORT")
    resistance: Optional[float] = Field(None, description="Resistance level")
    support: Optional[float] = Field(None, description="Support level")
    vwap: Optional[float] = Field(None, description="VWAP level")


class TrailingRequest(BaseModel):
    """Request for trailing calculation"""
    strategy: str = Field(..., description="Strategy type")
    entry_price: float = Field(..., description="Entry price")
    current_stop: float = Field(..., description="Current stop price")
    current_price: float = Field(..., description="Current market price")
    direction: str = Field(..., description="LONG or SHORT")
    atr: Optional[float] = Field(None, description="Current ATR")
    swing_low: Optional[float] = Field(None, description="Recent swing low")
    swing_high: Optional[float] = Field(None, description="Recent swing high")
    bars_in_trade: int = Field(0, description="Bars since entry")


class PartialCloseRequest(BaseModel):
    """Request for partial close evaluation"""
    strategy: str = Field(..., description="Strategy type")
    entry_price: float = Field(..., description="Entry price")
    current_price: float = Field(..., description="Current market price")
    stop_price: float = Field(..., description="Stop price")
    target_price: float = Field(..., description="Target price")
    direction: str = Field(..., description="LONG or SHORT")
    current_position_size: float = Field(1.0, description="Current position size (0-1)")
    already_closed_pct: float = Field(0.0, description="Already closed percentage")


class TimeStopRequest(BaseModel):
    """Request for time stop evaluation"""
    strategy: str = Field(..., description="Strategy type")
    bars_held: int = Field(..., description="Bars since entry")
    entry_price: float = Field(..., description="Entry price")
    current_price: float = Field(..., description="Current market price")
    direction: str = Field(..., description="LONG or SHORT")
    current_position_size: float = Field(1.0, description="Current position size")


class ForcedExitRequest(BaseModel):
    """Request for forced exit evaluation"""
    strategy: str = Field(..., description="Strategy type")
    current_regime: str = Field(..., description="Current market regime")
    previous_regime: Optional[str] = Field(None, description="Previous market regime")
    current_volatility: float = Field(1.0, description="Current volatility (normalized)")
    normal_volatility: float = Field(1.0, description="Normal volatility baseline")
    structure_broken: bool = Field(False, description="Is market structure broken")
    position_pnl_pct: float = Field(0.0, description="Position PnL %")
    daily_pnl_pct: float = Field(0.0, description="Daily PnL %")
    correlation_spike: bool = Field(False, description="Portfolio correlation spike")


class FullEvaluationRequest(BaseModel):
    """Request for full position evaluation"""
    strategy: str
    entry_price: float
    current_price: float
    stop_price: float
    target_price: float
    direction: str
    bars_held: int = 0
    current_regime: str = "TRENDING"
    previous_regime: Optional[str] = None
    atr: Optional[float] = None
    current_volatility: float = 1.0
    structure_broken: bool = False
    position_pnl_pct: float = 0.0


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for Position Policy"""
    return position_policy_service.get_health()


# ===========================================
# Complete Policies
# ===========================================

@router.get("/strategies")
async def get_all_strategies():
    """
    Get all strategies with position policies.
    """
    policies = position_policy_service.get_all_policies()
    return {
        "strategies": [p["primaryStrategy"] for p in policies],
        "count": len(policies),
        "timestamp": int(time.time() * 1000)
    }


@router.get("/policies")
async def get_all_policies():
    """
    Get all complete position policies.
    """
    policies = position_policy_service.get_all_policies()
    return {
        "policies": policies,
        "count": len(policies),
        "timestamp": int(time.time() * 1000)
    }


@router.get("/policies/{strategy}")
async def get_strategy_policy(strategy: str):
    """
    Get complete position policy for a strategy.
    """
    policy = position_policy_service.get_policy(strategy)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy for {strategy} not found")
    return policy


@router.get("/policies/{strategy}/summary")
async def get_policy_summary(strategy: str):
    """
    Get policy summary for a strategy.
    """
    summary = position_policy_service.get_policy_summary(strategy)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Policy for {strategy} not found")
    return summary


# ===========================================
# Stop Loss
# ===========================================

@router.get("/stops")
async def get_stop_types():
    """
    Get all stop loss types.
    """
    return {
        "stopTypes": position_policy_service.get_stop_types(),
        "matrix": position_policy_service.get_stop_matrix()
    }


@router.post("/stops/calculate")
async def calculate_stop(request: StopCalculationRequest):
    """
    Calculate stop loss for position.
    """
    return position_policy_service.calculate_stop(
        strategy=request.strategy,
        entry_price=request.entry_price,
        direction=request.direction,
        atr=request.atr,
        swing_low=request.swing_low,
        swing_high=request.swing_high,
        support=request.support,
        resistance=request.resistance
    )


@router.get("/stops/matrix")
async def get_stop_matrix():
    """
    Get strategy-stop matrix.
    """
    return position_policy_service.get_stop_matrix()


# ===========================================
# Take Profit
# ===========================================

@router.get("/take-profits")
async def get_tp_types():
    """
    Get all take profit types.
    """
    return {
        "tpTypes": position_policy_service.get_tp_types(),
        "matrix": position_policy_service.get_tp_matrix()
    }


@router.post("/take-profits/calculate")
async def calculate_tp(request: TPCalculationRequest):
    """
    Calculate take profit levels for position.
    """
    return position_policy_service.calculate_tp(
        strategy=request.strategy,
        entry_price=request.entry_price,
        stop_price=request.stop_price,
        direction=request.direction,
        resistance=request.resistance,
        support=request.support,
        vwap=request.vwap
    )


@router.get("/take-profits/matrix")
async def get_tp_matrix():
    """
    Get strategy-TP matrix.
    """
    return position_policy_service.get_tp_matrix()


# ===========================================
# Trailing Stop
# ===========================================

@router.get("/trailing")
async def get_trailing_types():
    """
    Get all trailing stop types.
    """
    return {
        "trailingTypes": position_policy_service.get_trailing_types(),
        "matrix": position_policy_service.get_trailing_matrix()
    }


@router.post("/trailing/calculate")
async def calculate_trailing(request: TrailingRequest):
    """
    Calculate trailing stop update.
    """
    return position_policy_service.calculate_trailing(
        strategy=request.strategy,
        entry_price=request.entry_price,
        current_stop=request.current_stop,
        current_price=request.current_price,
        direction=request.direction,
        atr=request.atr,
        swing_low=request.swing_low,
        swing_high=request.swing_high,
        bars_in_trade=request.bars_in_trade
    )


@router.get("/trailing/matrix")
async def get_trailing_matrix():
    """
    Get strategy-trailing matrix.
    """
    return position_policy_service.get_trailing_matrix()


# ===========================================
# Partial Close
# ===========================================

@router.get("/partial-close")
async def get_partial_types():
    """
    Get all partial close types.
    """
    return {
        "partialTypes": position_policy_service.get_partial_types(),
        "matrix": position_policy_service.get_partial_matrix()
    }


@router.post("/partial-close/evaluate")
async def evaluate_partial_close(request: PartialCloseRequest):
    """
    Evaluate partial close decision.
    """
    return position_policy_service.evaluate_partial_close(
        strategy=request.strategy,
        entry_price=request.entry_price,
        current_price=request.current_price,
        stop_price=request.stop_price,
        target_price=request.target_price,
        direction=request.direction,
        current_position_size=request.current_position_size,
        already_closed_pct=request.already_closed_pct
    )


@router.get("/partial-close/matrix")
async def get_partial_matrix():
    """
    Get strategy-partial close matrix.
    """
    return position_policy_service.get_partial_matrix()


# ===========================================
# Time Stop
# ===========================================

@router.get("/time-stop")
async def get_time_stop_types():
    """
    Get all time stop types.
    """
    return {
        "timeStopTypes": position_policy_service.get_time_stop_types(),
        "matrix": position_policy_service.get_time_stop_matrix()
    }


@router.post("/time-stop/evaluate")
async def evaluate_time_stop(request: TimeStopRequest):
    """
    Evaluate time stop decision.
    """
    return position_policy_service.evaluate_time_stop(
        strategy=request.strategy,
        bars_held=request.bars_held,
        entry_price=request.entry_price,
        current_price=request.current_price,
        direction=request.direction,
        current_position_size=request.current_position_size
    )


@router.get("/time-stop/matrix")
async def get_time_stop_matrix():
    """
    Get strategy-time stop matrix.
    """
    return position_policy_service.get_time_stop_matrix()


# ===========================================
# Forced Exit
# ===========================================

@router.get("/forced-exit")
async def get_forced_exit_triggers():
    """
    Get all forced exit triggers.
    """
    return {
        "triggers": position_policy_service.get_forced_exit_triggers(),
        "matrix": position_policy_service.get_forced_exit_matrix()
    }


@router.post("/forced-exit/evaluate")
async def evaluate_forced_exit(request: ForcedExitRequest):
    """
    Evaluate forced exit decision.
    """
    return position_policy_service.evaluate_forced_exit(
        strategy=request.strategy,
        current_regime=request.current_regime,
        previous_regime=request.previous_regime,
        current_volatility=request.current_volatility,
        normal_volatility=request.normal_volatility,
        structure_broken=request.structure_broken,
        position_pnl_pct=request.position_pnl_pct,
        daily_pnl_pct=request.daily_pnl_pct,
        correlation_spike=request.correlation_spike
    )


@router.get("/forced-exit/matrix")
async def get_forced_exit_matrix():
    """
    Get strategy-forced exit matrix.
    """
    return position_policy_service.get_forced_exit_matrix()


# ===========================================
# Combined / Full Evaluation
# ===========================================

@router.get("/matrix")
async def get_strategy_policy_matrix():
    """
    Get complete strategy-policy matrix.
    """
    return position_policy_service.get_strategy_policy_matrix()


@router.post("/evaluate")
async def full_evaluation(request: FullEvaluationRequest):
    """
    Get full position evaluation.
    
    Evaluates all policies at once for a position.
    """
    return position_policy_service.get_full_evaluation(
        strategy=request.strategy,
        entry_price=request.entry_price,
        current_price=request.current_price,
        stop_price=request.stop_price,
        target_price=request.target_price,
        direction=request.direction,
        bars_held=request.bars_held,
        current_regime=request.current_regime,
        previous_regime=request.previous_regime,
        atr=request.atr,
        current_volatility=request.current_volatility,
        structure_broken=request.structure_broken,
        position_pnl_pct=request.position_pnl_pct
    )
