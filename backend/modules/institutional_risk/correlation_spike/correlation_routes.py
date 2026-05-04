"""
PHASE 22.4 — Correlation Spike Routes
=====================================
API endpoints for Correlation Spike Engine.

Endpoints:
- GET /api/v1/institutional-risk/correlation
- GET /api/v1/institutional-risk/correlation/summary
- GET /api/v1/institutional-risk/correlation/diversification
- GET /api/v1/institutional-risk/correlation/state
"""

from fastapi import APIRouter, Query
from typing import Optional, List
from datetime import datetime, timezone

from .correlation_aggregator import CorrelationAggregator
from .correlation_types import CorrelationSpikeState


router = APIRouter(
    prefix="/api/v1/institutional-risk/correlation",
    tags=["institutional-risk", "correlation-spike"]
)

# Singleton aggregator
_aggregator = CorrelationAggregator()


def get_aggregator() -> CorrelationAggregator:
    """Get correlation aggregator instance."""
    return _aggregator


@router.get("")
async def get_correlation_state(
    # Asset allocations (comma-separated pairs like "BTC:0.4,ETH:0.3,SOL:0.3")
    assets: Optional[str] = Query(None, description="Asset allocations (BTC:0.4,ETH:0.3)"),
    
    # Strategy params
    strategies: Optional[str] = Query(None, description="Active strategies (comma-separated)"),
    
    # Market state
    volatility_state: str = Query("NORMAL", description="Volatility regime"),
    breadth_state: str = Query("NEUTRAL", description="Market breadth state"),
    dominance_regime: str = Query("NEUTRAL", description="Dominance regime"),
    
    # Risk state
    risk_state: str = Query("NORMAL", description="VaR risk state"),
    tail_risk_state: str = Query("LOW", description="Tail risk state"),
):
    """
    Get full correlation spike state.
    
    Analyzes asset, strategy, and factor correlations to detect
    correlation regime shifts and diversification breakdown.
    """
    aggregator = get_aggregator()
    
    # Parse asset allocations
    asset_allocations = None
    if assets:
        asset_allocations = {}
        for pair in assets.split(","):
            if ":" in pair:
                asset, weight = pair.split(":")
                asset_allocations[asset.strip()] = float(weight.strip())
    
    # Parse strategies
    active_strategies = None
    if strategies:
        active_strategies = [s.strip() for s in strategies.split(",")]
    
    # Calculate state
    state = aggregator.calculate(
        asset_allocations=asset_allocations,
        active_strategies=active_strategies,
        volatility_state=volatility_state,
        breadth_state=breadth_state,
        dominance_regime=dominance_regime,
        risk_state=risk_state,
        tail_risk_state=tail_risk_state,
    )
    
    return state.to_full_dict()


@router.get("/summary")
async def get_correlation_summary(
    volatility_state: str = Query("NORMAL", description="Volatility regime"),
    risk_state: str = Query("NORMAL", description="VaR risk state"),
):
    """
    Get compact correlation summary.
    """
    aggregator = get_aggregator()
    
    state = aggregator.calculate(
        volatility_state=volatility_state,
        risk_state=risk_state,
    )
    
    return aggregator.get_correlation_summary(state)


@router.get("/diversification")
async def get_diversification_analysis(
    assets: Optional[str] = Query(None, description="Asset allocations"),
    strategies: Optional[str] = Query(None, description="Active strategies"),
    volatility_state: str = Query("NORMAL", description="Volatility regime"),
):
    """
    Get diversification breakdown analysis.
    
    Shows whether diversification is effective or breaking down.
    """
    aggregator = get_aggregator()
    
    # Parse inputs
    asset_allocations = None
    if assets:
        asset_allocations = {}
        for pair in assets.split(","):
            if ":" in pair:
                asset, weight = pair.split(":")
                asset_allocations[asset.strip()] = float(weight.strip())
    
    active_strategies = None
    if strategies:
        active_strategies = [s.strip() for s in strategies.split(",")]
    
    state = aggregator.calculate(
        asset_allocations=asset_allocations,
        active_strategies=active_strategies,
        volatility_state=volatility_state,
    )
    
    return aggregator.get_diversification_breakdown(state)


@router.get("/state")
async def get_current_state(
    volatility_state: str = Query("NORMAL", description="Volatility regime"),
):
    """
    Get current correlation state classification.
    """
    aggregator = get_aggregator()
    
    state = aggregator.calculate(volatility_state=volatility_state)
    
    return {
        "correlation_state": state.correlation_state.value,
        "correlation_spike_intensity": state.correlation_spike_intensity,
        "recommended_action": state.recommended_action.value,
        "modifiers": {
            "confidence_modifier": state.confidence_modifier,
            "capital_modifier": state.capital_modifier,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
