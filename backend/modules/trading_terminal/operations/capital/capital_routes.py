"""
OPS4 Capital Flow Routes
========================

API endpoints for Capital Flow management.
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .capital_flow_service import capital_flow_service


router = APIRouter(prefix="/api/ops/capital", tags=["ops-capital"])


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for OPS4 Capital Flow"""
    return capital_flow_service.get_health()


# ===========================================
# Capital State
# ===========================================

@router.get("/state")
async def get_capital_state():
    """
    Get current capital state.
    
    Returns:
    - Total equity, used/free margin
    - Unrealized/realized PnL
    - Total exposure
    - Open positions count
    """
    state = capital_flow_service.get_capital_state()
    return state.to_dict()


# ===========================================
# Strategy Allocations
# ===========================================

@router.get("/strategies")
async def get_strategy_allocations():
    """
    Get capital allocation by strategy.
    
    Returns list of strategy allocations with:
    - Capital allocated/used/available
    - PnL per strategy
    - Utilization percentage
    """
    allocations = capital_flow_service.get_strategy_allocations()
    return {
        "strategies": [a.to_dict() for a in allocations],
        "count": len(allocations),
        "timestamp": int(time.time() * 1000)
    }


@router.get("/strategies/{strategy_id}")
async def get_strategy_allocation(strategy_id: str):
    """
    Get allocation for specific strategy.
    """
    allocation = capital_flow_service.get_strategy_allocation(strategy_id)
    
    if not allocation:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    
    return allocation.to_dict()


# ===========================================
# Exposure Analysis
# ===========================================

@router.get("/exposure/symbols")
async def get_exposure_by_symbol():
    """
    Get exposure breakdown by symbol.
    
    Shows capital at risk per trading symbol.
    """
    exposures = capital_flow_service.get_exposure_by_symbol()
    return {
        "exposures": [e.to_dict() for e in exposures],
        "count": len(exposures),
        "timestamp": int(time.time() * 1000)
    }


@router.get("/exposure/exchanges")
async def get_exposure_by_exchange():
    """
    Get exposure breakdown by exchange.
    
    Shows capital at risk per exchange.
    """
    exposures = capital_flow_service.get_exposure_by_exchange()
    return {
        "exposures": exposures,
        "timestamp": int(time.time() * 1000)
    }


@router.get("/exposure")
async def get_exposure_breakdown():
    """
    Get complete exposure breakdown.
    
    Returns exposure by:
    - Symbol
    - Strategy
    - Exchange
    - Side (LONG/SHORT)
    """
    breakdown = capital_flow_service.get_exposure_breakdown()
    return breakdown.to_dict()


# ===========================================
# Capital Timeline
# ===========================================

@router.get("/timeline")
async def get_capital_timeline(
    period_hours: int = Query(24, description="Time period in hours")
):
    """
    Get capital flow timeline.
    
    Shows history of capital movements:
    - Position opens/closes
    - PnL realizations
    - Scaling events
    """
    timeline = capital_flow_service.get_capital_timeline(period_hours)
    return timeline.to_dict()


# ===========================================
# Risk Concentration
# ===========================================

@router.get("/risk")
async def get_risk_concentration():
    """
    Get risk concentration analysis.
    
    Shows:
    - Largest position/strategy/exchange
    - Herfindahl concentration index
    - Top 3 concentration
    - Risk flags
    """
    concentration = capital_flow_service.get_risk_concentration()
    return concentration.to_dict()


# ===========================================
# Capital Efficiency
# ===========================================

@router.get("/efficiency")
async def get_capital_efficiency():
    """
    Get capital efficiency metrics.
    
    Shows:
    - Capital utilization
    - Return on capital
    - PnL per trade/dollar
    - Capital turnover
    """
    efficiency = capital_flow_service.get_capital_efficiency()
    return efficiency.to_dict()


# ===========================================
# Portfolio Metrics
# ===========================================

@router.get("/portfolio")
async def get_portfolio_metrics():
    """
    Get portfolio-level metrics.
    
    Returns:
    - Returns (daily/weekly/monthly)
    - Risk metrics (volatility, drawdown)
    - Risk-adjusted returns (Sharpe, Sortino, Calmar)
    - Win/loss statistics
    """
    metrics = capital_flow_service.get_portfolio_metrics()
    return metrics.to_dict()


# ===========================================
# Summary Endpoint
# ===========================================

@router.get("/summary")
async def get_capital_summary():
    """
    Get complete capital summary.
    
    Aggregates all capital flow data in one response.
    """
    state = capital_flow_service.get_capital_state()
    allocations = capital_flow_service.get_strategy_allocations()
    concentration = capital_flow_service.get_risk_concentration()
    efficiency = capital_flow_service.get_capital_efficiency()
    
    return {
        "state": state.to_dict(),
        "allocations": {
            "count": len(allocations),
            "strategies": [a.to_dict() for a in allocations[:5]]  # Top 5
        },
        "riskConcentration": concentration.to_dict(),
        "efficiency": efficiency.to_dict(),
        "timestamp": int(time.time() * 1000)
    }
