"""
Portfolio Manager Routes

PHASE 38 — Portfolio Manager

API endpoints for portfolio management.

Endpoints:
- GET  /api/v1/portfolio/state     - Get current portfolio state
- GET  /api/v1/portfolio/exposure  - Get exposure breakdown
- GET  /api/v1/portfolio/positions - Get all positions
- GET  /api/v1/portfolio/targets   - Get target allocations
- POST /api/v1/portfolio/rebalance - Trigger rebalance
- POST /api/v1/portfolio/targets   - Set new targets
- POST /api/v1/portfolio/position  - Add position
- DELETE /api/v1/portfolio/position/{symbol} - Close position
- GET  /api/v1/portfolio/history   - Get history
- GET  /api/v1/portfolio/risk      - Get risk metrics
- POST /api/v1/portfolio/rotate    - Rotate capital
- GET  /api/v1/portfolio/constraints/{symbol} - Get execution constraints
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .portfolio_types import (
    PortfolioState,
    PortfolioPosition,
    PortfolioTarget,
    PortfolioRisk,
    ExposureState,
    RebalanceResult,
    PositionRequest,
    CapitalRotationRequest,
    PortfolioHistoryEntry,
    DirectionType,
)
from .portfolio_engine import get_portfolio_manager_engine
from .portfolio_registry import get_portfolio_registry


router = APIRouter(prefix="/api/v1/portfolio", tags=["Portfolio Manager"])


# ══════════════════════════════════════════════════════════════
# Request/Response Models
# ══════════════════════════════════════════════════════════════

class TargetInput(BaseModel):
    """Input for single target."""
    symbol: str
    target_weight: float = Field(ge=0, le=1)
    direction: DirectionType
    confidence: float = Field(ge=0, le=1, default=0.5)
    priority: int = Field(default=0, ge=0)
    source_hypothesis_id: Optional[str] = None


class SetTargetsRequest(BaseModel):
    """Request to set portfolio targets."""
    targets: List[TargetInput]


class AddPositionRequest(BaseModel):
    """Request to add a position."""
    symbol: str
    direction: DirectionType
    size_usd: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    take_profit: float = Field(gt=0)


class UpdatePriceRequest(BaseModel):
    """Request to update position price."""
    symbol: str
    current_price: float = Field(gt=0)


class RotateCapitalRequest(BaseModel):
    """Request to rotate capital."""
    targets: List[TargetInput]
    consider_correlation: bool = True
    consider_risk_contribution: bool = True


class ValidateExecutionRequest(BaseModel):
    """Request to validate execution plan."""
    symbol: str
    direction: DirectionType
    size_usd: float = Field(gt=0)


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool
    message: str
    data: Optional[dict] = None


# ══════════════════════════════════════════════════════════════
# GET Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/state", response_model=PortfolioState)
async def get_portfolio_state():
    """
    Get current portfolio state.
    
    Returns complete portfolio snapshot including:
    - Capital allocation
    - Positions and targets
    - Exposure metrics
    - Risk metrics (Markowitz variance)
    - Diversification score
    """
    engine = get_portfolio_manager_engine()
    return engine.get_state()


@router.get("/exposure", response_model=ExposureState)
async def get_portfolio_exposure():
    """
    Get portfolio exposure breakdown.
    
    Returns:
    - Long/short exposure
    - Net/gross exposure
    - Exposure by symbol
    - Available capacity
    """
    engine = get_portfolio_manager_engine()
    return engine.calculate_exposure()


@router.get("/positions", response_model=List[PortfolioPosition])
async def get_portfolio_positions():
    """
    Get all active positions.
    
    Returns list of positions with:
    - Size and direction
    - P&L
    - Risk contribution
    - Correlation info
    """
    engine = get_portfolio_manager_engine()
    return engine.get_positions()


@router.get("/positions/{symbol}", response_model=PortfolioPosition)
async def get_position(symbol: str):
    """Get specific position by symbol."""
    engine = get_portfolio_manager_engine()
    position = engine.get_position(symbol)
    
    if not position:
        raise HTTPException(
            status_code=404,
            detail=f"No position found for {symbol.upper()}"
        )
    
    return position


@router.get("/targets", response_model=List[PortfolioTarget])
async def get_portfolio_targets():
    """
    Get target allocations.
    
    Returns list of targets from hypothesis pipeline.
    """
    engine = get_portfolio_manager_engine()
    return engine.get_targets()


@router.get("/targets/{symbol}", response_model=PortfolioTarget)
async def get_target(symbol: str):
    """Get specific target by symbol."""
    engine = get_portfolio_manager_engine()
    target = engine.get_target(symbol)
    
    if not target:
        raise HTTPException(
            status_code=404,
            detail=f"No target found for {symbol.upper()}"
        )
    
    return target


@router.get("/risk", response_model=PortfolioRisk)
async def get_portfolio_risk():
    """
    Get portfolio risk metrics.
    
    Returns Markowitz-based risk:
    - Portfolio variance (wᵀΣw)
    - Portfolio volatility
    - Risk level classification
    - VaR estimates
    - Risk contribution by asset
    """
    engine = get_portfolio_manager_engine()
    return engine.calculate_risk()


@router.get("/history", response_model=List[PortfolioHistoryEntry])
async def get_portfolio_history(
    limit: int = Query(default=100, ge=1, le=1000),
):
    """
    Get portfolio history.
    
    Returns historical snapshots for performance analysis.
    """
    engine = get_portfolio_manager_engine()
    return engine.get_history(limit=limit)


@router.get("/history/stats")
async def get_history_stats(
    period_days: int = Query(default=30, ge=1, le=365),
):
    """
    Get aggregated history statistics.
    
    Returns:
    - Average/min/max risk
    - Average/min/max P&L
    - Diversification trends
    """
    registry = get_portfolio_registry()
    return await registry.get_history_stats(period_days=period_days)


@router.get("/constraints/{symbol}")
async def get_execution_constraints(
    symbol: str,
    direction: DirectionType = Query(...),
):
    """
    Get execution constraints for a symbol.
    
    Returns constraints for execution brain:
    - Max position size
    - Correlation penalty
    - Effective max after penalty
    """
    engine = get_portfolio_manager_engine()
    return engine.get_execution_constraints(symbol, direction)


@router.get("/rebalance/check")
async def check_rebalance_needed():
    """
    Check if rebalance is needed.
    
    Returns:
    - Whether rebalance is triggered
    - Weight deviations
    - Max deviation
    """
    engine = get_portfolio_manager_engine()
    needs_rebalance, deviations, max_dev = engine.check_rebalance_needed()
    
    return {
        "rebalance_needed": needs_rebalance,
        "weight_deviations": deviations,
        "max_deviation": max_dev,
        "threshold": 0.03,
    }


# ══════════════════════════════════════════════════════════════
# POST Endpoints
# ══════════════════════════════════════════════════════════════

@router.post("/targets", response_model=SuccessResponse)
async def set_portfolio_targets(request: SetTargetsRequest):
    """
    Set portfolio targets from hypothesis.
    
    Pipeline: hypothesis → portfolio targets → portfolio manager → execution brain
    """
    engine = get_portfolio_manager_engine()
    registry = get_portfolio_registry()
    
    # Convert to PortfolioTarget objects
    targets = [
        PortfolioTarget(
            symbol=t.symbol.upper(),
            target_weight=t.target_weight,
            direction=t.direction,
            confidence=t.confidence,
            priority=t.priority,
            source_hypothesis_id=t.source_hypothesis_id,
        )
        for t in request.targets
    ]
    
    result = engine.set_targets(targets)
    
    # Persist targets
    await registry.save_targets(engine.get_targets())
    
    return SuccessResponse(
        success=True,
        message=f"Set {result['targets_set']} targets",
        data=result
    )


@router.post("/position", response_model=SuccessResponse)
async def add_position(request: AddPositionRequest):
    """
    Add a new position to portfolio.
    
    Validates:
    - Position limit (max 10%)
    - Exposure limit (max 70%)
    - Applies correlation penalty
    """
    engine = get_portfolio_manager_engine()
    registry = get_portfolio_registry()
    
    pos_request = PositionRequest(
        symbol=request.symbol,
        direction=request.direction,
        size_usd=request.size_usd,
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
    )
    
    success, message, position = engine.add_position(pos_request)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    # Persist positions
    await registry.save_positions(engine.get_positions())
    
    # Save state
    state = engine.get_state()
    await registry.save_state(state)
    
    return SuccessResponse(
        success=True,
        message=message,
        data=position.model_dump() if position else None
    )


@router.post("/position/update-price", response_model=SuccessResponse)
async def update_position_price(request: UpdatePriceRequest):
    """Update current price for a position."""
    engine = get_portfolio_manager_engine()
    
    success = engine.update_position_price(request.symbol, request.current_price)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No position found for {request.symbol.upper()}"
        )
    
    position = engine.get_position(request.symbol)
    
    return SuccessResponse(
        success=True,
        message=f"Updated {request.symbol.upper()} price to {request.current_price}",
        data={
            "unrealized_pnl_usd": position.unrealized_pnl_usd,
            "unrealized_pnl_percent": position.unrealized_pnl_percent,
        }
    )


@router.post("/rebalance", response_model=RebalanceResult)
async def trigger_rebalance():
    """
    Trigger portfolio rebalance.
    
    Analyzes current state and generates rebalance plan.
    
    Triggers when:
    - |current_weight - target_weight| > 3%
    - Exposure limits exceeded
    - Risk level CRITICAL
    """
    engine = get_portfolio_manager_engine()
    registry = get_portfolio_registry()
    
    result = engine.rebalance()
    
    # Save rebalance event
    if result.rebalance_triggered:
        await registry.save_rebalance(result)
    
    return result


@router.post("/rotate", response_model=SuccessResponse)
async def rotate_capital(request: RotateCapitalRequest):
    """
    Rotate capital to new targets.
    
    Considers:
    - Portfolio correlation
    - Risk contribution
    - Confidence scores
    """
    engine = get_portfolio_manager_engine()
    registry = get_portfolio_registry()
    
    # Convert targets
    targets = [
        PortfolioTarget(
            symbol=t.symbol.upper(),
            target_weight=t.target_weight,
            direction=t.direction,
            confidence=t.confidence,
            priority=t.priority,
            source_hypothesis_id=t.source_hypothesis_id,
        )
        for t in request.targets
    ]
    
    rotation_request = CapitalRotationRequest(
        targets=targets,
        consider_correlation=request.consider_correlation,
        consider_risk_contribution=request.consider_risk_contribution,
    )
    
    result = engine.rotate_capital(rotation_request)
    
    # Persist targets
    await registry.save_targets(engine.get_targets())
    
    return SuccessResponse(
        success=True,
        message=f"Capital rotation plan generated for {result['targets_processed']} assets",
        data=result
    )


@router.post("/validate-execution", response_model=SuccessResponse)
async def validate_execution(request: ValidateExecutionRequest):
    """
    Validate execution plan against portfolio constraints.
    
    Returns:
    - Whether approved
    - Adjusted size after penalties
    """
    engine = get_portfolio_manager_engine()
    
    approved, message, adjusted_size = engine.validate_execution_plan(
        request.symbol,
        request.direction,
        request.size_usd,
    )
    
    return SuccessResponse(
        success=approved,
        message=message,
        data={
            "original_size_usd": request.size_usd,
            "adjusted_size_usd": adjusted_size,
            "size_reduction": round(request.size_usd - adjusted_size, 2),
        }
    )


# ══════════════════════════════════════════════════════════════
# DELETE Endpoints
# ══════════════════════════════════════════════════════════════

@router.delete("/position/{symbol}", response_model=SuccessResponse)
async def close_position(symbol: str):
    """Close a position."""
    engine = get_portfolio_manager_engine()
    registry = get_portfolio_registry()
    
    success, message = engine.close_position(symbol)
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    # Persist positions
    await registry.save_positions(engine.get_positions())
    
    # Save state
    state = engine.get_state()
    await registry.save_state(state)
    
    return SuccessResponse(
        success=True,
        message=message
    )


# ══════════════════════════════════════════════════════════════
# Integration Endpoints (for Execution Brain)
# ══════════════════════════════════════════════════════════════

@router.post("/execution-brain/validate")
async def validate_for_execution_brain(
    symbol: str = Query(...),
    direction: DirectionType = Query(...),
    size_usd: float = Query(..., gt=0),
):
    """
    Validate execution plan for Execution Brain integration.
    
    This endpoint is called by Execution Brain before creating execution plans.
    """
    engine = get_portfolio_manager_engine()
    
    approved, message, adjusted_size = engine.validate_execution_plan(
        symbol, direction, size_usd
    )
    
    constraints = engine.get_execution_constraints(symbol, direction)
    
    return {
        "approved": approved,
        "message": message,
        "original_size_usd": size_usd,
        "adjusted_size_usd": adjusted_size,
        "constraints": constraints,
    }


@router.get("/execution-brain/portfolio-limits")
async def get_portfolio_limits_for_execution():
    """
    Get current portfolio limits for Execution Brain.
    
    Returns available capacity for new positions.
    """
    engine = get_portfolio_manager_engine()
    exposure = engine.calculate_exposure()
    risk = engine.calculate_risk()
    
    return {
        "available_long_capacity_percent": exposure.available_long_capacity,
        "available_short_capacity_percent": exposure.available_short_capacity,
        "available_long_capacity_usd": exposure.available_long_capacity * engine._capital,
        "available_short_capacity_usd": exposure.available_short_capacity * engine._capital,
        "max_single_position_percent": 0.10,
        "max_single_position_usd": engine._capital * 0.10,
        "current_risk_level": risk.risk_level,
        "can_add_positions": risk.risk_level != "CRITICAL",
    }
