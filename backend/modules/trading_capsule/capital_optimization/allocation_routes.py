"""
Allocation Routes
=================

PHASE 3.4 - API endpoints for Capital Optimization Engine.
"""

import time
import uuid
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .capital_optimizer import capital_optimizer
from .strategy_allocator import strategy_allocator
from .capital_efficiency_engine import capital_efficiency_engine
from .allocation_repository import allocation_repository


router = APIRouter(prefix="/api/capital-optimization", tags=["phase3.4-capital-optimization"])


# ===========================================
# Request Models
# ===========================================

class SetCapitalRequest(BaseModel):
    """Request to set portfolio capital"""
    total_capital: float = Field(1000000.0, description="Total portfolio capital")


class UpdatePerformanceRequest(BaseModel):
    """Request to update strategy performance"""
    strategy_id: str = Field(..., description="Strategy ID")
    trades: List[Dict[str, Any]] = Field(default_factory=list, description="Trade history")
    evaluation_days: int = Field(30, description="Evaluation period")


class SetAllocationRequest(BaseModel):
    """Request to set strategy allocation"""
    strategy_id: str = Field(..., description="Strategy ID")
    allocation_pct: float = Field(..., description="Allocation percentage")


class ReserveCapitalRequest(BaseModel):
    """Request to reserve capital for a position"""
    strategy_id: str = Field(..., description="Strategy ID")
    amount: float = Field(..., description="Amount to reserve")
    position_id: str = Field(..., description="Position ID")


class ReleaseCapitalRequest(BaseModel):
    """Request to release capital from a position"""
    strategy_id: str = Field(..., description="Strategy ID")
    amount: float = Field(..., description="Amount to release")
    position_id: str = Field(..., description="Position ID")
    pnl: float = Field(0.0, description="Realized PnL")


class SetRegimeRequest(BaseModel):
    """Request to set market regime"""
    regime: str = Field("RANGE", description="Market regime")


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for Capital Optimization module"""
    return {
        "module": "PHASE 3.4 Capital Optimization Engine",
        "status": "healthy",
        "version": "1.0.0",
        "engines": capital_optimizer.get_health(),
        "repository": allocation_repository.get_stats(),
        "timestamp": int(time.time() * 1000)
    }


# ===========================================
# Portfolio Endpoints
# ===========================================

@router.get("/portfolio")
async def get_portfolio():
    """Get current portfolio state"""
    portfolio = capital_optimizer.get_portfolio()
    allocation_repository.save_portfolio_snapshot(portfolio)
    return portfolio.to_dict()


@router.post("/portfolio/capital")
async def set_capital(request: SetCapitalRequest):
    """Set total portfolio capital"""
    capital_optimizer.set_total_capital(request.total_capital)
    return {
        "success": True,
        "totalCapital": request.total_capital,
        "portfolio": capital_optimizer.get_portfolio().to_dict()
    }


@router.post("/portfolio/regime")
async def set_regime(request: SetRegimeRequest):
    """Set market regime for allocation adjustments"""
    capital_optimizer.set_regime(request.regime)
    return {
        "success": True,
        "regime": request.regime,
        "allocations": [a.to_dict() for a in capital_optimizer.get_allocations()]
    }


# ===========================================
# Allocation Endpoints
# ===========================================

@router.get("/allocations")
async def get_allocations():
    """Get all strategy allocations"""
    allocations = capital_optimizer.get_allocations()
    return {
        "allocations": [a.to_dict() for a in allocations],
        "total": sum(a.current_allocation_pct for a in allocations),
        "count": len(allocations)
    }


@router.get("/allocations/{strategy_id}")
async def get_allocation(strategy_id: str):
    """Get allocation for a specific strategy"""
    alloc = strategy_allocator.get_allocation(strategy_id)
    if not alloc:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    return alloc.to_dict()


@router.post("/allocations")
async def set_allocation(request: SetAllocationRequest):
    """Set allocation for a strategy"""
    portfolio = capital_optimizer.get_portfolio()
    alloc = strategy_allocator.set_allocation(
        strategy_id=request.strategy_id,
        allocation_pct=request.allocation_pct,
        total_capital=portfolio.total_capital
    )
    allocation_repository.save_allocation(alloc)
    return alloc.to_dict()


@router.post("/allocations/{strategy_id}/suspend")
async def suspend_strategy(strategy_id: str, reason: str = Query("")):
    """Suspend a strategy"""
    success = strategy_allocator.suspend_strategy(strategy_id, reason)
    if not success:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    return {"success": True, "strategyId": strategy_id, "action": "suspended"}


@router.post("/allocations/{strategy_id}/activate")
async def activate_strategy(strategy_id: str):
    """Activate a suspended strategy"""
    success = strategy_allocator.activate_strategy(strategy_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    return {"success": True, "strategyId": strategy_id, "action": "activated"}


# ===========================================
# Efficiency Endpoints
# ===========================================

@router.get("/efficiency")
async def get_all_efficiency():
    """Get efficiency metrics for all strategies"""
    efficiencies = capital_optimizer.get_all_efficiencies()
    return {
        "efficiencies": [e.to_dict() for e in efficiencies],
        "count": len(efficiencies)
    }


@router.get("/efficiency/{strategy_id}")
async def get_efficiency(strategy_id: str):
    """Get efficiency for a specific strategy"""
    eff = capital_optimizer.get_strategy_efficiency(strategy_id)
    if not eff:
        raise HTTPException(status_code=404, detail=f"Efficiency not found for {strategy_id}")
    return eff.to_dict()


# ===========================================
# Strategy Performance Endpoints
# ===========================================

@router.get("/strategies")
async def get_strategies():
    """Get all strategy performances"""
    performances = capital_optimizer.get_all_performances()
    return {
        "strategies": [p.to_dict() for p in performances],
        "count": len(performances)
    }


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: str):
    """Get performance for a specific strategy"""
    perf = capital_optimizer.get_strategy_performance(strategy_id)
    if not perf:
        raise HTTPException(status_code=404, detail=f"Performance not found for {strategy_id}")
    return perf.to_dict()


@router.post("/strategies/performance")
async def update_performance(request: UpdatePerformanceRequest):
    """Update strategy performance from trades"""
    perf = capital_optimizer.update_strategy_performance(
        strategy_id=request.strategy_id,
        trades=request.trades,
        evaluation_days=request.evaluation_days
    )
    allocation_repository.save_performance(perf)
    return perf.to_dict()


# ===========================================
# Rebalance Endpoints
# ===========================================

@router.get("/rebalance")
async def get_rebalance_plan():
    """Generate rebalancing recommendation"""
    plan = capital_optimizer.optimize_allocations()
    allocation_repository.save_rebalance(plan)
    return plan.to_dict()


@router.post("/rebalance/apply")
async def apply_rebalance(step: int = Query(1)):
    """Apply rebalancing plan"""
    plan = allocation_repository.get_last_rebalance()
    if not plan:
        raise HTTPException(status_code=404, detail="No rebalance plan found. Call GET /rebalance first")
    
    result = capital_optimizer.apply_rebalance(plan, step)
    return result


@router.get("/rebalance/history")
async def get_rebalance_history(limit: int = Query(10, le=20)):
    """Get rebalance history"""
    history = allocation_repository.get_rebalance_history(limit)
    return {
        "history": [p.to_dict() for p in history],
        "count": len(history)
    }


# ===========================================
# Capital Management Endpoints
# ===========================================

@router.get("/capital/{strategy_id}")
async def get_capital_for_strategy(strategy_id: str):
    """Get available capital for a strategy"""
    return capital_optimizer.get_capital_for_strategy(strategy_id)


@router.post("/capital/reserve")
async def reserve_capital(request: ReserveCapitalRequest):
    """Reserve capital for a new position"""
    return capital_optimizer.reserve_capital(
        strategy_id=request.strategy_id,
        amount=request.amount,
        position_id=request.position_id
    )


@router.post("/capital/release")
async def release_capital(request: ReleaseCapitalRequest):
    """Release capital when position closes"""
    return capital_optimizer.release_capital(
        strategy_id=request.strategy_id,
        amount=request.amount,
        position_id=request.position_id,
        pnl=request.pnl
    )


# ===========================================
# Summary Endpoint
# ===========================================

@router.get("/summary")
async def get_summary():
    """Get complete capital optimization summary"""
    return capital_optimizer.get_summary()


# ===========================================
# Demo & Testing
# ===========================================

@router.post("/demo")
async def run_demo():
    """
    Run demo to test capital optimization.
    """
    
    # Set initial capital
    capital_optimizer.set_total_capital(1000000.0)
    
    # Simulated trade histories for each strategy
    demo_trades = {
        "TREND_CONFIRMATION": [
            {"pnl": 1500, "pnl_pct": 1.5, "duration_hours": 48, "closed_at": time.time() * 1000 - 86400000 * 5},
            {"pnl": 2200, "pnl_pct": 2.2, "duration_hours": 72, "closed_at": time.time() * 1000 - 86400000 * 4},
            {"pnl": -800, "pnl_pct": -0.8, "duration_hours": 24, "closed_at": time.time() * 1000 - 86400000 * 3},
            {"pnl": 1800, "pnl_pct": 1.8, "duration_hours": 36, "closed_at": time.time() * 1000 - 86400000 * 2},
            {"pnl": 2500, "pnl_pct": 2.5, "duration_hours": 60, "closed_at": time.time() * 1000 - 86400000 * 1},
        ],
        "MEAN_REVERSION": [
            {"pnl": 600, "pnl_pct": 0.6, "duration_hours": 12, "closed_at": time.time() * 1000 - 86400000 * 5},
            {"pnl": 450, "pnl_pct": 0.45, "duration_hours": 8, "closed_at": time.time() * 1000 - 86400000 * 4},
            {"pnl": -300, "pnl_pct": -0.3, "duration_hours": 6, "closed_at": time.time() * 1000 - 86400000 * 3},
            {"pnl": 550, "pnl_pct": 0.55, "duration_hours": 10, "closed_at": time.time() * 1000 - 86400000 * 2},
            {"pnl": 700, "pnl_pct": 0.7, "duration_hours": 14, "closed_at": time.time() * 1000 - 86400000 * 1},
        ],
        "MOMENTUM": [
            {"pnl": 3000, "pnl_pct": 3.0, "duration_hours": 96, "closed_at": time.time() * 1000 - 86400000 * 5},
            {"pnl": 2800, "pnl_pct": 2.8, "duration_hours": 84, "closed_at": time.time() * 1000 - 86400000 * 4},
            {"pnl": -1200, "pnl_pct": -1.2, "duration_hours": 48, "closed_at": time.time() * 1000 - 86400000 * 3},
            {"pnl": 2000, "pnl_pct": 2.0, "duration_hours": 60, "closed_at": time.time() * 1000 - 86400000 * 2},
            {"pnl": 1500, "pnl_pct": 1.5, "duration_hours": 36, "closed_at": time.time() * 1000 - 86400000 * 1},
        ],
        "BREAKOUT": [
            {"pnl": -500, "pnl_pct": -0.5, "duration_hours": 12, "closed_at": time.time() * 1000 - 86400000 * 5},
            {"pnl": 400, "pnl_pct": 0.4, "duration_hours": 18, "closed_at": time.time() * 1000 - 86400000 * 4},
            {"pnl": -600, "pnl_pct": -0.6, "duration_hours": 8, "closed_at": time.time() * 1000 - 86400000 * 3},
            {"pnl": 200, "pnl_pct": 0.2, "duration_hours": 24, "closed_at": time.time() * 1000 - 86400000 * 2},
            {"pnl": -400, "pnl_pct": -0.4, "duration_hours": 16, "closed_at": time.time() * 1000 - 86400000 * 1},
        ]
    }
    
    # Update performances
    results = []
    for strategy_id, trades in demo_trades.items():
        perf = capital_optimizer.update_strategy_performance(
            strategy_id=strategy_id,
            trades=trades,
            evaluation_days=30
        )
        
        alloc = strategy_allocator.get_allocation(strategy_id)
        eff = capital_optimizer.get_strategy_efficiency(strategy_id)
        
        results.append({
            "strategyId": strategy_id,
            "totalTrades": perf.total_trades,
            "winRate": round(perf.win_rate, 1),
            "profitFactor": round(perf.profit_factor, 2),
            "totalPnl": round(perf.total_pnl, 2),
            "grade": perf.grade.value,
            "allocation": round(alloc.current_allocation_pct, 1) if alloc else 0,
            "efficiency": round(eff.efficiency_score, 1) if eff else 0
        })
    
    # Generate rebalance plan
    plan = capital_optimizer.optimize_allocations()
    
    return {
        "demo": "complete",
        "strategies": results,
        "portfolio": capital_optimizer.get_portfolio().to_dict(),
        "rebalancePlan": {
            "recommendations": len(plan.recommendations),
            "toIncrease": plan.strategies_to_increase,
            "toDecrease": plan.strategies_to_decrease,
            "toSuspend": plan.strategies_to_suspend,
            "totalReallocation": round(plan.total_reallocation, 1)
        }
    }


@router.delete("/clear")
async def clear_all():
    """Clear all data and reset"""
    allocation_repository.clear()
    return {"success": True, "action": "cleared", "timestamp": int(time.time() * 1000)}


@router.get("/stats")
async def get_stats():
    """Get module statistics"""
    return allocation_repository.get_stats()
