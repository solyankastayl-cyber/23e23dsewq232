"""
Risk Budget Routes

PHASE 38.5 — Risk Budget Engine

API endpoints for risk budget management.

Endpoints:
- GET  /api/v1/risk-budget                    - Get portfolio risk budget
- GET  /api/v1/risk-budget/strategies         - Get strategy risk allocations
- POST /api/v1/risk-budget/recompute          - Recompute risk budgets
- POST /api/v1/risk-budget/allocate           - Allocate risk budgets
- POST /api/v1/risk-budget/volatility-target  - Compute vol-targeted size
- GET  /api/v1/risk-budget/history            - Get risk budget history
- GET  /api/v1/risk-budget/stats              - Get statistics
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .risk_budget_engine import get_risk_budget_engine
from .risk_budget_registry import get_risk_budget_registry
from .risk_budget_types import (
    RiskBudgetAllocationRequest,
    VolatilityTargetRequest,
    DEFAULT_RISK_BUDGETS,
    PORTFOLIO_RISK_LIMITS,
)


router = APIRouter(prefix="/api/v1/risk-budget", tags=["Risk Budget"])


# ══════════════════════════════════════════════════════════════
# Request/Response Models
# ══════════════════════════════════════════════════════════════

class AllocateRiskBudgetRequest(BaseModel):
    """Request to allocate risk budgets."""
    strategies: List[str] = Field(
        default_factory=lambda: list(DEFAULT_RISK_BUDGETS.keys()),
        description="List of strategies to allocate risk to"
    )
    method: str = Field(
        default="EQUAL_RISK",
        description="Allocation method: EQUAL_RISK, VOLATILITY_WEIGHTED, PERFORMANCE_WEIGHTED, CUSTOM"
    )
    custom_allocations: Optional[dict] = Field(
        default=None,
        description="Custom allocations if method is CUSTOM"
    )


class VolatilityTargetSizeRequest(BaseModel):
    """Request to compute volatility-targeted size."""
    symbol: str
    strategy: str
    direction: str = "LONG"
    base_size_usd: float = Field(gt=0)
    target_volatility: Optional[float] = None


class AddPositionRiskRequest(BaseModel):
    """Request to add position to risk tracking."""
    symbol: str
    strategy: str
    position_size_usd: float = Field(gt=0)


class SetStrategyBudgetRequest(BaseModel):
    """Request to set strategy risk budget."""
    strategy: str
    risk_target: float = Field(ge=0.05, le=0.40)
    volatility: Optional[float] = None


class ExecutionSizeRequest(BaseModel):
    """Request to get execution-adjusted size."""
    symbol: str
    strategy: str
    base_size_usd: float = Field(gt=0)
    current_price: float = Field(gt=0)


# ══════════════════════════════════════════════════════════════
# Portfolio Risk Budget Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("")
async def get_portfolio_risk_budget():
    """
    Get current portfolio risk budget state.
    
    Returns complete risk budget with:
    - Total portfolio risk
    - Strategy budgets
    - Position risks
    - Volatility targeting info
    """
    try:
        engine = get_risk_budget_engine()
        state = engine.get_portfolio_risk_budget()
        
        return {
            "status": "ok",
            "phase": "38.5",
            "portfolio_risk_budget": {
                "total_risk": state.total_risk,
                "total_risk_limit": state.total_risk_limit,
                "risk_utilization": state.risk_utilization,
                "risk_state": state.risk_state,
                "needs_rebalance": state.needs_rebalance,
                "strategy_count": state.strategy_count,
                "position_count": state.position_count,
                "systematic_risk": state.systematic_risk,
                "idiosyncratic_risk": state.idiosyncratic_risk,
                "target_volatility": state.target_volatility,
                "current_volatility": state.current_volatility,
                "volatility_ratio": state.volatility_ratio,
                "vol_scale_factor": state.vol_scale_factor,
                "total_capital": state.total_capital,
                "risk_capital": state.risk_capital,
                "warnings": state.warnings,
                "timestamp": state.timestamp.isoformat(),
            },
            "strategy_budgets": [
                {
                    "strategy": b.strategy,
                    "strategy_type": b.strategy_type,
                    "risk_target": b.risk_target,
                    "risk_used": b.risk_used,
                    "risk_contribution": b.risk_contribution,
                    "allocated_capital": b.allocated_capital,
                    "max_capital": b.max_capital,
                    "volatility": b.volatility,
                    "position_count": b.position_count,
                    "is_active": b.is_active,
                    "is_over_budget": b.is_over_budget,
                }
                for b in state.strategy_budgets
            ],
            "position_risks": [
                {
                    "symbol": p.symbol,
                    "strategy": p.strategy,
                    "position_size_usd": p.position_size_usd,
                    "weight": p.weight,
                    "asset_volatility": p.asset_volatility,
                    "volatility_annualized": p.volatility_annualized,
                    "risk_contribution": p.risk_contribution,
                    "marginal_risk": p.marginal_risk,
                    "avg_correlation": p.avg_correlation,
                    "is_within_budget": p.is_within_budget,
                }
                for p in state.position_risks
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
async def get_strategy_risk_allocations():
    """
    Get all strategy risk allocations.
    
    Shows risk budget per strategy.
    """
    try:
        engine = get_risk_budget_engine()
        budgets = engine.get_all_risk_budgets()
        
        return {
            "status": "ok",
            "phase": "38.5",
            "strategy_count": len(budgets),
            "default_budgets": DEFAULT_RISK_BUDGETS,
            "limits": PORTFOLIO_RISK_LIMITS,
            "strategies": [
                {
                    "strategy": b.strategy,
                    "strategy_type": b.strategy_type,
                    "risk_target": b.risk_target,
                    "risk_used": b.risk_used,
                    "risk_remaining": round(b.risk_target - b.risk_used, 4),
                    "utilization": round(b.risk_used / b.risk_target, 4) if b.risk_target > 0 else 0,
                    "allocated_capital": b.allocated_capital,
                    "max_capital": b.max_capital,
                    "volatility": b.volatility,
                    "position_count": b.position_count,
                    "is_active": b.is_active,
                    "is_over_budget": b.is_over_budget,
                }
                for b in budgets.values()
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies/{strategy}")
async def get_strategy_risk_budget(strategy: str):
    """Get risk budget for specific strategy."""
    try:
        engine = get_risk_budget_engine()
        budget = engine.get_strategy_risk_budget(strategy)
        
        if not budget:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy} not found")
        
        return {
            "status": "ok",
            "phase": "38.5",
            "strategy": {
                "strategy": budget.strategy,
                "strategy_type": budget.strategy_type,
                "risk_target": budget.risk_target,
                "risk_used": budget.risk_used,
                "risk_remaining": round(budget.risk_target - budget.risk_used, 4),
                "risk_contribution": budget.risk_contribution,
                "allocated_capital": budget.allocated_capital,
                "max_capital": budget.max_capital,
                "volatility": budget.volatility,
                "position_count": budget.position_count,
                "is_active": budget.is_active,
                "is_over_budget": budget.is_over_budget,
                "sharpe_ratio": budget.sharpe_ratio,
                "recent_pnl": budget.recent_pnl,
                "last_updated": budget.last_updated.isoformat(),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Risk Budget Operations
# ══════════════════════════════════════════════════════════════

@router.post("/recompute")
async def recompute_risk_budgets():
    """
    Recompute all risk budgets.
    
    Recalculates:
    - Strategy risk allocations
    - Position risk contributions
    - Portfolio risk state
    """
    try:
        engine = get_risk_budget_engine()
        registry = get_risk_budget_registry()
        
        # Get current state
        state = engine.get_portfolio_risk_budget()
        
        # Check if rebalance needed
        needs_rebalance, reason = engine.check_rebalance_needed()
        
        # Rebalance if needed
        rebalance_result = None
        if needs_rebalance:
            rebalance_result = engine.rebalance_risk()
        
        # Save to registry
        registry.save_portfolio_risk_budget(state)
        for budget in state.strategy_budgets:
            registry.save_strategy_allocation(budget)
        
        return {
            "status": "ok",
            "phase": "38.5",
            "recomputed": True,
            "portfolio_risk": state.total_risk,
            "risk_state": state.risk_state,
            "needs_rebalance": needs_rebalance,
            "rebalance_reason": reason,
            "rebalance_result": {
                "triggered": rebalance_result.triggered,
                "reason": rebalance_result.reason,
                "risk_before": rebalance_result.risk_before,
                "risk_after": rebalance_result.risk_after,
                "global_scale_factor": rebalance_result.global_scale_factor,
                "positions_to_scale": len(rebalance_result.positions_to_scale),
                "capital_freed": rebalance_result.capital_freed,
            } if rebalance_result else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/allocate")
async def allocate_risk_budgets(request: AllocateRiskBudgetRequest):
    """
    Allocate risk budgets to strategies.
    
    Methods:
    - EQUAL_RISK: Equal risk per strategy
    - VOLATILITY_WEIGHTED: Inverse volatility weighting
    - PERFORMANCE_WEIGHTED: Based on recent performance
    - CUSTOM: Custom allocations
    """
    try:
        engine = get_risk_budget_engine()
        registry = get_risk_budget_registry()
        
        # Create allocation request
        alloc_request = RiskBudgetAllocationRequest(
            strategies=request.strategies,
            method=request.method,
            custom_allocations=request.custom_allocations,
        )
        
        # Allocate
        budgets = engine.allocate_risk_budgets(alloc_request)
        
        # Save to registry
        for budget in budgets.values():
            registry.save_strategy_allocation(budget)
        
        return {
            "status": "ok",
            "phase": "38.5",
            "method": request.method,
            "strategies_allocated": len(budgets),
            "allocations": [
                {
                    "strategy": b.strategy,
                    "risk_target": b.risk_target,
                    "max_capital": b.max_capital,
                }
                for b in budgets.values()
            ],
            "total_risk_budget": sum(b.risk_target for b in budgets.values()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategy")
async def set_strategy_risk_budget(request: SetStrategyBudgetRequest):
    """Set risk budget for a specific strategy."""
    try:
        engine = get_risk_budget_engine()
        registry = get_risk_budget_registry()
        
        # Set budget
        budget = engine.set_strategy_risk_budget(
            strategy=request.strategy,
            risk_target=request.risk_target,
            volatility=request.volatility,
        )
        
        # Save to registry
        registry.save_strategy_allocation(budget)
        
        return {
            "status": "ok",
            "phase": "38.5",
            "strategy": budget.strategy,
            "risk_target": budget.risk_target,
            "max_capital": budget.max_capital,
            "volatility": budget.volatility,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Volatility Targeting
# ══════════════════════════════════════════════════════════════

@router.post("/volatility-target")
async def compute_volatility_target_size(request: VolatilityTargetSizeRequest):
    """
    Compute volatility-targeted position size.
    
    Formula:
    vol_scaled_size = base_size * (target_vol / asset_vol)
    
    This ensures equal risk contribution per position.
    """
    try:
        engine = get_risk_budget_engine()
        
        # Create request
        vol_request = VolatilityTargetRequest(
            symbol=request.symbol,
            strategy=request.strategy,
            direction=request.direction,
            base_size_usd=request.base_size_usd,
            target_volatility=request.target_volatility,
        )
        
        # Compute
        response = engine.compute_volatility_target_size(vol_request)
        
        return {
            "status": "ok",
            "phase": "38.5",
            "symbol": response.symbol,
            "strategy": response.strategy,
            "base_size_usd": response.base_size_usd,
            "asset_volatility": {
                "daily": response.asset_volatility,
                "annualized": response.asset_volatility_annualized,
            },
            "target_volatility": response.target_volatility,
            "volatility_ratio": response.volatility_ratio,
            "vol_scaled_size_usd": response.vol_scaled_size_usd,
            "size_reduction_pct": response.size_reduction_pct,
            "risk_budget": {
                "strategy_budget": response.strategy_risk_budget,
                "remaining": response.risk_budget_remaining,
                "within_budget": response.within_budget,
            },
            "final_size_usd": response.final_size_usd,
            "reason": response.reason,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vol-scale-factor")
async def get_volatility_scale_factor():
    """
    Get global volatility scale factor.
    
    Factor = target_vol / current_portfolio_vol
    """
    try:
        engine = get_risk_budget_engine()
        
        factor = engine.get_vol_scale_factor()
        state = engine.get_portfolio_risk_budget()
        
        return {
            "status": "ok",
            "phase": "38.5",
            "vol_scale_factor": factor,
            "target_volatility": state.target_volatility,
            "current_volatility": state.current_volatility,
            "interpretation": "Scale all position sizes by this factor" if factor != 1.0 else "No scaling needed",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Risk Contribution
# ══════════════════════════════════════════════════════════════

@router.post("/risk-contribution")
async def calculate_risk_contribution(request: AddPositionRiskRequest):
    """
    Calculate risk contribution for a position.
    
    Formula:
    risk_contribution = weight * volatility * correlation_adjustment
    """
    try:
        engine = get_risk_budget_engine()
        
        result = engine.calculate_risk_contribution(
            symbol=request.symbol,
            strategy=request.strategy,
            position_size_usd=request.position_size_usd,
        )
        
        return {
            "status": "ok",
            "phase": "38.5",
            "symbol": result.symbol,
            "strategy": result.strategy,
            "components": {
                "weight": result.weight,
                "volatility": result.volatility,
                "correlation_adjustment": result.correlation_adjustment,
            },
            "risk_contribution": result.risk_contribution,
            "risk_contribution_pct": result.risk_contribution_pct,
            "marginal_risk": result.marginal_risk,
            "impact_on_portfolio_risk": result.impact_on_portfolio_risk,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/position")
async def add_position_risk(request: AddPositionRiskRequest):
    """
    Add position to risk tracking.
    
    Tracks risk contribution and budget usage.
    """
    try:
        engine = get_risk_budget_engine()
        registry = get_risk_budget_registry()
        
        # Add position
        position = engine.add_position_risk(
            symbol=request.symbol,
            strategy=request.strategy,
            position_size_usd=request.position_size_usd,
        )
        
        # Save to registry
        registry.save_position_risk(position)
        
        return {
            "status": "ok",
            "phase": "38.5",
            "position": {
                "symbol": position.symbol,
                "strategy": position.strategy,
                "position_size_usd": position.position_size_usd,
                "weight": position.weight,
                "volatility_annualized": position.volatility_annualized,
                "risk_contribution": position.risk_contribution,
                "marginal_risk": position.marginal_risk,
                "avg_correlation": position.avg_correlation,
                "risk_budget_used": position.risk_budget_used,
                "is_within_budget": position.is_within_budget,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/position/{symbol}")
async def remove_position_risk(symbol: str):
    """Remove position from risk tracking."""
    try:
        engine = get_risk_budget_engine()
        registry = get_risk_budget_registry()
        
        # Remove from engine
        removed = engine.remove_position_risk(symbol)
        
        if not removed:
            raise HTTPException(status_code=404, detail=f"Position {symbol} not found")
        
        # Remove from registry
        registry.remove_position_risk(symbol)
        
        return {
            "status": "ok",
            "phase": "38.5",
            "removed": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Integration Endpoints
# ══════════════════════════════════════════════════════════════

@router.post("/validate")
async def validate_position_for_risk_budget(request: AddPositionRiskRequest):
    """
    Validate position against risk budget.
    
    Returns approval status and adjusted size if needed.
    """
    try:
        engine = get_risk_budget_engine()
        
        approved, message, adjusted_size = engine.validate_position_for_risk_budget(
            symbol=request.symbol,
            strategy=request.strategy,
            size_usd=request.position_size_usd,
        )
        
        return {
            "status": "ok",
            "phase": "38.5",
            "symbol": request.symbol,
            "strategy": request.strategy,
            "original_size_usd": request.position_size_usd,
            "approved": approved,
            "message": message,
            "adjusted_size_usd": adjusted_size,
            "size_change_pct": round(1 - adjusted_size / request.position_size_usd, 4) if request.position_size_usd > 0 else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution-constraints/{symbol}")
async def get_execution_constraints(
    symbol: str,
    strategy: str = Query(default="MOMENTUM"),
):
    """
    Get risk-based constraints for execution.
    
    Used by Execution Brain for position sizing.
    """
    try:
        engine = get_risk_budget_engine()
        
        constraints = engine.get_execution_constraints_for_risk(
            symbol=symbol,
            strategy=strategy,
        )
        
        return {
            "status": "ok",
            "phase": "38.5",
            **constraints,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execution-size")
async def get_execution_adjusted_size(request: ExecutionSizeRequest):
    """
    Get execution-adjusted position size.
    
    Applies:
    1. Volatility targeting
    2. Risk budget constraint
    3. Portfolio risk limit
    """
    try:
        engine = get_risk_budget_engine()
        
        result = engine.adjust_size_for_execution(
            symbol=request.symbol,
            strategy=request.strategy,
            base_size_usd=request.base_size_usd,
            current_price=request.current_price,
        )
        
        return {
            "status": "ok",
            "phase": "38.5",
            **result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Risk Check Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/check-limit")
async def check_portfolio_risk_limit():
    """Check if portfolio risk is within limit."""
    try:
        engine = get_risk_budget_engine()
        
        within_limit, current_risk, message = engine.check_portfolio_risk_limit()
        
        return {
            "status": "ok",
            "phase": "38.5",
            "within_limit": within_limit,
            "current_risk": current_risk,
            "risk_limit": PORTFOLIO_RISK_LIMITS["MAX_TOTAL_RISK"],
            "message": message,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-rebalance")
async def check_rebalance_needed():
    """Check if risk rebalancing is needed."""
    try:
        engine = get_risk_budget_engine()
        
        needed, reason = engine.check_rebalance_needed()
        
        return {
            "status": "ok",
            "phase": "38.5",
            "needs_rebalance": needed,
            "reason": reason,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebalance")
async def rebalance_risk():
    """
    Rebalance portfolio to match risk budgets.
    
    Reduces positions that exceed risk allocation.
    """
    try:
        engine = get_risk_budget_engine()
        
        result = engine.rebalance_risk()
        
        return {
            "status": "ok",
            "phase": "38.5",
            "rebalance": {
                "triggered": result.triggered,
                "reason": result.reason,
                "risk_before": result.risk_before,
                "risk_after": result.risk_after,
                "risk_reduction": result.risk_reduction,
                "global_scale_factor": result.global_scale_factor,
                "strategy_scale_factors": result.strategy_scale_factors,
                "strategies_to_reduce": result.strategies_to_reduce,
                "strategies_to_increase": result.strategies_to_increase,
                "positions_to_scale": result.positions_to_scale,
                "capital_freed": result.capital_freed,
                "timestamp": result.timestamp.isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# History & Stats
# ══════════════════════════════════════════════════════════════

@router.get("/history")
async def get_risk_budget_history(
    limit: int = Query(default=100, ge=1, le=1000),
    hours_back: Optional[int] = Query(default=None, ge=1, le=720),
):
    """Get risk budget history."""
    try:
        registry = get_risk_budget_registry()
        
        history = registry.get_history(limit=limit, hours_back=hours_back)
        
        return {
            "status": "ok",
            "phase": "38.5",
            "count": len(history),
            "history": history,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_risk_budget_stats():
    """Get risk budget statistics."""
    try:
        registry = get_risk_budget_registry()
        engine = get_risk_budget_engine()
        
        # Registry stats
        registry_stats = registry.get_statistics()
        
        # Engine state
        state = engine.get_portfolio_risk_budget()
        
        return {
            "status": "ok",
            "phase": "38.5",
            "registry": registry_stats,
            "engine": {
                "total_risk": state.total_risk,
                "risk_utilization": state.risk_utilization,
                "risk_state": state.risk_state,
                "vol_scale_factor": state.vol_scale_factor,
                "strategy_count": state.strategy_count,
                "position_count": state.position_count,
            },
            "limits": PORTFOLIO_RISK_LIMITS,
            "defaults": DEFAULT_RISK_BUDGETS,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def risk_budget_health():
    """Risk Budget Engine health check."""
    return {
        "status": "ok",
        "phase": "38.5",
        "module": "Risk Budget Engine",
        "endpoints": [
            "GET  /api/v1/risk-budget",
            "GET  /api/v1/risk-budget/strategies",
            "POST /api/v1/risk-budget/recompute",
            "POST /api/v1/risk-budget/allocate",
            "POST /api/v1/risk-budget/volatility-target",
            "POST /api/v1/risk-budget/position",
            "POST /api/v1/risk-budget/validate",
            "GET  /api/v1/risk-budget/execution-constraints/{symbol}",
            "POST /api/v1/risk-budget/rebalance",
            "GET  /api/v1/risk-budget/history",
            "GET  /api/v1/risk-budget/stats",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
