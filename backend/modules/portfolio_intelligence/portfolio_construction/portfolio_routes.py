"""
PHASE 10 - Portfolio Construction API Routes
=============================================
REST API endpoints for portfolio management.

Endpoints:
- GET /api/portfolio-construction/state
- GET /api/portfolio-construction/allocations
- GET /api/portfolio-construction/risk-parity
- GET /api/portfolio-construction/volatility
- GET /api/portfolio-construction/drawdown
- GET /api/portfolio-construction/correlation
- GET /api/portfolio-construction/rebalance
- GET /api/portfolio-construction/history
- GET /api/portfolio-construction/health
"""

import random
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from .portfolio_types import (
    StrategyMetrics, PortfolioState, AllocationMethod,
    DEFAULT_PORTFOLIO_CONFIG
)
from .risk_parity_engine import RiskParityEngine
from .volatility_targeting_engine import VolatilityTargetingEngine
from .drawdown_control_engine import DrawdownControlEngine
from .strategy_correlation_engine import StrategyCorrelationEngine
from .capital_allocator import CapitalAllocator
from .rebalance_engine import RebalanceEngine
from .portfolio_repository import PortfolioRepository


router = APIRouter(prefix="/api/portfolio-construction", tags=["Portfolio Construction"])


# Initialize engines
risk_parity_engine = RiskParityEngine()
vol_targeting_engine = VolatilityTargetingEngine()
drawdown_engine = DrawdownControlEngine()
correlation_engine = StrategyCorrelationEngine()
capital_allocator = CapitalAllocator()
rebalance_engine = RebalanceEngine()
repository = PortfolioRepository()


# ===== Mock Data Generators =====

def generate_mock_strategies(count: int = 5) -> List[StrategyMetrics]:
    """Generate mock strategy metrics."""
    names = [
        "MTF_BREAKOUT", "DOUBLE_BOTTOM", "MOMENTUM_CONT",
        "MEAN_REVERSION", "TREND_FOLLOWING", "VOLATILITY_BREAKOUT",
        "CHANNEL_BREAKOUT", "HARMONIC_PATTERN"
    ]
    
    strategies = []
    for i in range(min(count, len(names))):
        vol = 0.08 + random.random() * 0.15  # 8-23% volatility
        returns = vol * (0.5 + random.random() * 1.5)  # Positive expected return
        
        strategies.append(StrategyMetrics(
            strategy_id=f"strat_{i}",
            name=names[i],
            returns=returns,
            volatility=vol,
            sharpe_ratio=returns / vol if vol > 0 else 0,
            max_drawdown=vol * 2,
            current_drawdown=random.random() * vol,
            var_95=vol * 1.65,
            active=True,
            weight=1.0 / count
        ))
    
    return strategies


# ===== Response Models =====

class StateResponse(BaseModel):
    portfolioVolatility: float
    targetVolatility: float
    portfolioDrawdown: float
    riskBudgetUsed: float
    capitalDeployment: float
    strategyAllocations: dict
    drawdownState: str
    volatilityRegime: str
    rebalanceRecommendation: str
    portfolioHealthScore: float
    computed_at: str


class AllocationsResponse(BaseModel):
    allocations: dict
    total_risk_contribution: float
    adjustments_needed: int
    computed_at: str


class RiskParityResponse(BaseModel):
    allocations: dict
    portfolio_risk: float
    risk_contributions: dict
    risk_concentration: float
    converged: bool
    computed_at: str


class VolatilityResponse(BaseModel):
    target_volatility: float
    current_volatility: float
    realized_volatility: float
    volatility_scalar: float
    position_adjustment: float
    volatility_regime: str
    computed_at: str


class DrawdownResponse(BaseModel):
    current_drawdown: float
    max_drawdown_limit: float
    drawdown_state: str
    risk_reduction_factor: float
    capital_deployment: float
    days_in_drawdown: int
    computed_at: str


class CorrelationResponse(BaseModel):
    avg_correlation: float
    max_correlation: float
    diversification_ratio: float
    high_corr_pairs: list
    matrix_preview: dict
    computed_at: str


class RebalanceResponse(BaseModel):
    action: str
    urgency: float
    trigger_reason: str
    deltas: dict
    estimated_turnover: float
    estimated_cost_bps: float
    computed_at: str


# ===== API Endpoints =====

@router.get("/health")
async def portfolio_health():
    """Health check for Portfolio Construction module."""
    return {
        "status": "healthy",
        "version": "phase10_portfolio_v1",
        "engines": {
            "risk_parity": "ready",
            "volatility_targeting": "ready",
            "drawdown_control": "ready",
            "correlation": "ready",
            "capital_allocator": "ready",
            "rebalance": "ready"
        },
        "config": {
            "target_volatility": DEFAULT_PORTFOLIO_CONFIG["target_volatility"],
            "max_drawdown_limit": DEFAULT_PORTFOLIO_CONFIG["max_drawdown_limit"],
            "correlation_threshold": DEFAULT_PORTFOLIO_CONFIG["correlation_threshold"]
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/state", response_model=StateResponse)
async def get_portfolio_state(
    current_equity: float = Query(1000000, description="Current portfolio equity"),
    portfolio_volatility: float = Query(0.11, description="Current portfolio volatility")
):
    """
    Get complete portfolio state snapshot.
    
    Returns unified view of portfolio including:
    - Volatility vs target
    - Drawdown state
    - Risk budget usage
    - Rebalance recommendation
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate mock strategies
        strategies = generate_mock_strategies(5)
        
        # Get portfolio state
        state = capital_allocator.get_portfolio_state(
            strategies, current_equity, portfolio_volatility
        )
        
        # Save to repository
        try:
            repository.save_portfolio_state(state)
        except Exception:
            pass
        
        return StateResponse(
            portfolioVolatility=round(state.portfolio_volatility, 4),
            targetVolatility=round(state.target_volatility, 4),
            portfolioDrawdown=round(state.portfolio_drawdown, 4),
            riskBudgetUsed=round(state.risk_budget_used, 4),
            capitalDeployment=round(state.capital_deployment, 4),
            strategyAllocations=state.strategy_allocations,
            drawdownState=state.drawdown_state.value,
            volatilityRegime=state.volatility_regime.value,
            rebalanceRecommendation=state.rebalance_recommendation.value,
            portfolioHealthScore=round(state.portfolio_health_score, 3),
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/allocations", response_model=AllocationsResponse)
async def get_allocations(
    current_equity: float = Query(1000000, description="Current portfolio equity"),
    portfolio_volatility: float = Query(0.11, description="Current portfolio volatility"),
    method: str = Query("COMPOSITE", description="Allocation method")
):
    """
    Get optimal capital allocations.
    
    Methods:
    - COMPOSITE: Combined approach (default)
    - RISK_PARITY: Equal risk contribution
    - VOLATILITY_SCALED: Scaled by volatility
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Parse method
        try:
            alloc_method = AllocationMethod(method)
        except ValueError:
            alloc_method = AllocationMethod.COMPOSITE
        
        # Generate strategies
        strategies = generate_mock_strategies(5)
        
        # Calculate allocations
        allocations = capital_allocator.calculate_allocations(
            strategies, current_equity, portfolio_volatility, alloc_method
        )
        
        # Save to repository
        try:
            repository.save_allocations(allocations)
        except Exception:
            pass
        
        alloc_dict = {
            sid: {
                "target_weight": round(a.target_weight, 4),
                "risk_contribution": round(a.risk_contribution, 4),
                "needs_adjustment": a.needs_adjustment
            }
            for sid, a in allocations.items()
        }
        
        total_risk = sum(a.risk_contribution for a in allocations.values())
        adjustments = sum(1 for a in allocations.values() if a.needs_adjustment)
        
        return AllocationsResponse(
            allocations=alloc_dict,
            total_risk_contribution=round(total_risk, 4),
            adjustments_needed=adjustments,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk-parity", response_model=RiskParityResponse)
async def get_risk_parity():
    """
    Get risk parity allocations.
    
    Allocates capital so each strategy contributes equal risk.
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate strategies
        strategies = generate_mock_strategies(5)
        
        # Calculate risk parity
        result = risk_parity_engine.calculate_risk_parity(strategies)
        
        return RiskParityResponse(
            allocations=result.allocations,
            portfolio_risk=round(result.total_portfolio_risk, 4),
            risk_contributions=result.risk_contributions,
            risk_concentration=round(result.risk_concentration, 4),
            converged=result.converged,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/volatility", response_model=VolatilityResponse)
async def get_volatility_targeting(
    current_volatility: float = Query(0.11, description="Current portfolio volatility"),
    target_volatility: float = Query(0.12, description="Target volatility")
):
    """
    Get volatility targeting recommendation.
    
    Scales positions to maintain target volatility.
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate some mock returns
        mock_returns = [random.gauss(0.0005, 0.015) for _ in range(20)]
        
        # Calculate volatility scaling
        result = vol_targeting_engine.calculate_volatility_scaling(
            current_volatility, target_volatility, mock_returns
        )
        
        return VolatilityResponse(
            target_volatility=round(result.target_volatility, 4),
            current_volatility=round(result.current_volatility, 4),
            realized_volatility=round(result.realized_volatility, 4),
            volatility_scalar=round(result.volatility_scalar, 4),
            position_adjustment=round(result.position_size_adjustment, 2),
            volatility_regime=result.volatility_regime.value,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drawdown", response_model=DrawdownResponse)
async def get_drawdown_control(
    current_equity: float = Query(970000, description="Current portfolio equity"),
    peak_equity: float = Query(1000000, description="Peak portfolio equity")
):
    """
    Get drawdown control state.
    
    Monitors drawdown and recommends risk reduction.
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Set peak equity
        drawdown_engine.peak_equity = peak_equity
        
        # Analyze drawdown
        result = drawdown_engine.analyze_drawdown(current_equity)
        
        return DrawdownResponse(
            current_drawdown=round(result.current_drawdown, 4),
            max_drawdown_limit=round(result.max_drawdown_limit, 4),
            drawdown_state=result.drawdown_state.value,
            risk_reduction_factor=round(result.risk_reduction_factor, 4),
            capital_deployment=round(result.capital_deployment, 4),
            days_in_drawdown=result.days_in_drawdown,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/correlation", response_model=CorrelationResponse)
async def get_correlation_analysis():
    """
    Get strategy correlation analysis.
    
    Identifies highly correlated strategies that should have reduced allocation.
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate strategies
        strategies = generate_mock_strategies(5)
        
        # Calculate correlations
        result = correlation_engine.calculate_correlation_matrix(strategies)
        
        # Create matrix preview (first 3x3)
        preview = {}
        strategy_ids = list(result.matrix.keys())[:3]
        for sid in strategy_ids:
            preview[sid] = {
                sid2: round(result.matrix[sid].get(sid2, 0), 3)
                for sid2 in strategy_ids
            }
        
        return CorrelationResponse(
            avg_correlation=round(result.avg_correlation, 4),
            max_correlation=round(result.max_correlation, 4),
            diversification_ratio=round(result.diversification_ratio, 4),
            high_corr_pairs=[
                {"pair": f"{p[0]}-{p[1]}", "correlation": round(p[2], 4)}
                for p in result.high_corr_pairs[:5]
            ],
            matrix_preview=preview,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rebalance", response_model=RebalanceResponse)
async def get_rebalance_recommendation(
    current_equity: float = Query(1000000, description="Current portfolio equity")
):
    """
    Get rebalance recommendation.
    
    Evaluates if portfolio needs rebalancing based on:
    - Time since last rebalance
    - Allocation drift
    - Regime changes
    - Drawdown state
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate strategies
        strategies = generate_mock_strategies(5)
        
        # Get current allocations
        allocations = capital_allocator.calculate_allocations(
            strategies, current_equity, 0.11
        )
        
        # Target allocations (equal weight for simplicity)
        target_allocs = {sid: 1.0 / len(strategies) for sid in [s.strategy_id for s in strategies]}
        
        # Get drawdown state
        dd = drawdown_engine.analyze_drawdown(current_equity)
        
        # Evaluate rebalance
        result = rebalance_engine.evaluate_rebalance(
            allocations, target_allocs, dd.drawdown_state, "NORMAL"
        )
        
        # Save to repository
        try:
            repository.save_rebalance(result)
        except Exception:
            pass
        
        return RebalanceResponse(
            action=result.action.value,
            urgency=round(result.urgency, 3),
            trigger_reason=result.trigger_reason,
            deltas=result.allocations_delta,
            estimated_turnover=round(result.estimated_turnover, 4),
            estimated_cost_bps=round(result.estimated_cost_bps, 2),
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_portfolio_history(
    hours_back: int = Query(24, description="Hours to look back"),
    limit: int = Query(50, description="Maximum records")
):
    """Get historical portfolio states."""
    try:
        states = repository.get_state_history(hours_back, limit)
        allocations = repository.get_allocation_history(hours_back, min(limit, 20))
        rebalances = repository.get_rebalance_history(hours_back * 7, min(limit, 20))
        
        return {
            "hours_back": hours_back,
            "states": {"count": len(states), "records": states},
            "allocations": {"count": len(allocations), "records": allocations},
            "rebalances": {"count": len(rebalances), "records": rebalances},
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_portfolio_stats():
    """Get portfolio construction statistics."""
    try:
        repo_stats = repository.get_stats()
        
        return {
            "repository": repo_stats,
            "engines": {
                "risk_parity": risk_parity_engine.get_allocation_summary(),
                "volatility": vol_targeting_engine.get_volatility_summary(),
                "drawdown": drawdown_engine.get_drawdown_summary(),
                "correlation": correlation_engine.get_correlation_summary(),
                "allocator": capital_allocator.get_state_summary(),
                "rebalance": rebalance_engine.get_rebalance_summary()
            },
            "config": DEFAULT_PORTFOLIO_CONFIG,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
