"""
PHASE 23.3 — Strategy Survival Routes
=====================================
API endpoints for Strategy Survival Matrix.

Endpoints:
- GET  /api/v1/simulation/strategy-survival
- GET  /api/v1/simulation/strategy-survival/{strategy}
- GET  /api/v1/simulation/strategy-survival/summary
- GET  /api/v1/simulation/strategy-survival/matrix
- POST /api/v1/simulation/strategy-survival/recompute
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timezone

from .strategy_survival_aggregator import StrategySurvivalAggregator
from .strategy_survival_types import DEFAULT_STRATEGIES


router = APIRouter(
    prefix="/api/v1/simulation/strategy-survival",
    tags=["simulation-engine", "strategy-survival"]
)

# Singleton aggregator
_aggregator = StrategySurvivalAggregator()


def get_aggregator() -> StrategySurvivalAggregator:
    """Get strategy survival aggregator instance."""
    return _aggregator


@router.get("")
async def get_strategy_survival_matrix(
    # Portfolio state
    net_exposure: float = Query(0.5, description="Net portfolio exposure"),
    gross_exposure: float = Query(0.8, description="Gross portfolio exposure"),
    
    # Risk metrics
    current_var: float = Query(0.10, description="Current VaR"),
    current_volatility: float = Query(0.20, description="Current volatility"),
    
    # Portfolio
    portfolio_beta: float = Query(1.0, description="Portfolio beta"),
    crisis_state: str = Query("NORMAL", description="Crisis state"),
):
    """
    Get complete strategy survival matrix.
    
    Analyzes all default strategies across all scenarios.
    """
    aggregator = get_aggregator()
    
    matrix = aggregator.build_matrix(
        net_exposure=net_exposure,
        gross_exposure=gross_exposure,
        current_var=current_var,
        current_volatility=current_volatility,
        portfolio_beta=portfolio_beta,
        crisis_state=crisis_state,
    )
    
    return matrix.to_dict()


@router.get("/summary")
async def get_strategy_survival_summary(
    net_exposure: float = Query(0.5),
    gross_exposure: float = Query(0.8),
    portfolio_beta: float = Query(1.0),
):
    """
    Get compact strategy survival summary.
    """
    aggregator = get_aggregator()
    
    matrix = aggregator.build_matrix(
        net_exposure=net_exposure,
        gross_exposure=gross_exposure,
        portfolio_beta=portfolio_beta,
    )
    
    return matrix.to_summary()


@router.get("/matrix")
async def get_strategy_matrix_with_ranking(
    net_exposure: float = Query(0.5),
    gross_exposure: float = Query(0.8),
    portfolio_beta: float = Query(1.0),
):
    """
    Get strategy matrix with ranking and action summary.
    """
    aggregator = get_aggregator()
    
    matrix = aggregator.build_matrix(
        net_exposure=net_exposure,
        gross_exposure=gross_exposure,
        portfolio_beta=portfolio_beta,
    )
    
    ranking = aggregator.get_strategy_ranking(matrix)
    actions = aggregator.get_action_summary(matrix)
    
    return {
        "summary": matrix.to_summary(),
        "ranking": ranking,
        "action_summary": actions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/strategy/{strategy_name}")
async def get_single_strategy_survival(
    strategy_name: str,
    net_exposure: float = Query(0.5),
    gross_exposure: float = Query(0.8),
    current_var: float = Query(0.10),
    current_volatility: float = Query(0.20),
    portfolio_beta: float = Query(1.0),
):
    """
    Get survival analysis for a single strategy.
    """
    aggregator = get_aggregator()
    
    state = aggregator.analyze_strategy(
        strategy_name=strategy_name.upper(),
        net_exposure=net_exposure,
        gross_exposure=gross_exposure,
        current_var=current_var,
        current_volatility=current_volatility,
        portfolio_beta=portfolio_beta,
    )
    
    return state.to_full_dict()


@router.post("/recompute")
async def recompute_strategy_survival(
    strategies: Optional[str] = Query(None, description="Comma-separated strategy names"),
    net_exposure: float = Query(0.5),
    gross_exposure: float = Query(0.8),
    current_var: float = Query(0.10),
    current_volatility: float = Query(0.20),
    portfolio_beta: float = Query(1.0),
    crisis_state: str = Query("NORMAL"),
):
    """
    Force recompute strategy survival matrix.
    """
    aggregator = get_aggregator()
    
    # Parse strategies
    strategy_list = None
    if strategies:
        strategy_list = [s.strip().upper() for s in strategies.split(",")]
    
    matrix = aggregator.build_matrix(
        strategies=strategy_list,
        net_exposure=net_exposure,
        gross_exposure=gross_exposure,
        current_var=current_var,
        current_volatility=current_volatility,
        portfolio_beta=portfolio_beta,
        crisis_state=crisis_state,
    )
    
    return {
        "status": "recomputed",
        "strategies_analyzed": len(matrix.strategies),
        "most_robust": matrix.most_robust,
        "most_fragile": matrix.most_fragile,
        "average_robustness": round(matrix.average_system_strategy_robustness, 4),
        "distribution": {
            "robust": matrix.robust_count,
            "stable": matrix.stable_count,
            "fragile": matrix.fragile_count,
            "broken": matrix.broken_count,
        },
        "action_summary": aggregator.get_action_summary(matrix),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/available-strategies")
async def get_available_strategies():
    """
    Get list of available strategies for analysis.
    """
    return {
        "strategies": DEFAULT_STRATEGIES,
        "count": len(DEFAULT_STRATEGIES),
    }
