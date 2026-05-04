"""
Forward Simulation Routes
=========================

API endpoints for Forward Simulation (PHASE 2.3)
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .forward_engine import forward_engine
from .forward_repository import forward_repository
from .forward_types import SimulationConfig, MarketScenario


router = APIRouter(prefix="/api/forward", tags=["phase2-forward-simulation"])


# ===========================================
# Request Models
# ===========================================

class RunSimulationRequest(BaseModel):
    """Request to run forward simulation"""
    symbol: str = Field("BTC", description="Symbol to simulate")
    timeframe: str = Field("4h", description="Timeframe")
    scenario: Optional[str] = Field(None, description="Market scenario")
    candle_count: int = Field(500, description="Number of candles", ge=100, le=2000)
    initial_capital: float = Field(10000.0, description="Starting capital")
    risk_per_trade_pct: float = Field(1.0, description="Risk per trade %")
    slippage_pct: float = Field(0.05, description="Slippage %")
    commission_pct: float = Field(0.1, description="Commission %")
    strategies: Optional[List[str]] = Field(None, description="Strategies to use")
    use_strategy_selection: bool = Field(True, description="Use auto strategy selection")


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for Forward Simulation"""
    return forward_engine.get_health()


# ===========================================
# Run Simulation
# ===========================================

@router.post("/run")
async def run_simulation(request: Optional[RunSimulationRequest] = None):
    """
    Run forward simulation.
    
    Simulates pseudo-live trading candle by candle.
    """
    
    config = SimulationConfig()
    
    if request:
        config.symbol = request.symbol
        config.timeframe = request.timeframe
        config.candle_count = request.candle_count
        config.initial_capital = request.initial_capital
        config.risk_per_trade_pct = request.risk_per_trade_pct
        config.slippage_pct = request.slippage_pct
        config.commission_pct = request.commission_pct
        config.use_strategy_selection = request.use_strategy_selection
        
        if request.strategies:
            config.strategies = request.strategies
        
        if request.scenario:
            try:
                config.scenario = MarketScenario(request.scenario)
            except ValueError:
                config.scenario = MarketScenario.CUSTOM
    
    # Run simulation
    run = forward_engine.run_simulation(config)
    
    # Save run
    forward_repository.save_run(run)
    
    return run.to_dict()


@router.get("/run/{run_id}")
async def get_run(run_id: str):
    """Get simulation run by ID"""
    run = forward_repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run.to_dict()


@router.get("/runs")
async def get_runs(limit: int = Query(20, le=50)):
    """Get recent simulation runs"""
    runs = forward_repository.get_runs(limit)
    return {
        "runs": [
            {
                "runId": r.run_id,
                "status": r.status.value,
                "scenario": r.config.scenario.value,
                "symbol": r.config.symbol,
                "tradesCount": len(r.trades),
                "totalReturn": r.metrics.total_return if r.metrics else 0,
                "winRate": r.metrics.win_rate if r.metrics else 0,
                "completedAt": r.completed_at
            }
            for r in runs
        ],
        "count": len(runs)
    }


# ===========================================
# Results & Status
# ===========================================

@router.get("/status")
async def get_status():
    """Get current simulation status"""
    latest = forward_repository.get_latest_run()
    
    if not latest:
        return {"hasRun": False, "message": "No simulations run yet"}
    
    return {
        "hasRun": True,
        "runId": latest.run_id,
        "status": latest.status.value,
        "progress": latest.progress_pct,
        "currentBar": latest.current_bar,
        "totalBars": latest.total_bars
    }


@router.get("/results")
async def get_results():
    """Get latest simulation results"""
    run = forward_repository.get_latest_run()
    
    if not run:
        return {"hasRun": False, "message": "No simulations run yet"}
    
    return run.to_dict()


# ===========================================
# Equity Curve
# ===========================================

@router.get("/equity")
async def get_equity_curve(run_id: Optional[str] = None):
    """
    Get equity curve from simulation.
    """
    if run_id:
        run = forward_repository.get_run(run_id)
    else:
        run = forward_repository.get_latest_run()
    
    if not run:
        return {"hasData": False}
    
    return {
        "runId": run.run_id,
        "equityCurve": run.equity_curve.to_dict(),
        "config": {
            "initialCapital": run.config.initial_capital,
            "scenario": run.config.scenario.value
        }
    }


# ===========================================
# Trades
# ===========================================

@router.get("/trades")
async def get_trades(
    run_id: Optional[str] = None,
    status: Optional[str] = None,
    strategy: Optional[str] = None,
    limit: int = Query(50, le=200)
):
    """
    Get trades from simulation.
    """
    if run_id:
        run = forward_repository.get_run(run_id)
    else:
        run = forward_repository.get_latest_run()
    
    if not run:
        return {"hasData": False, "trades": []}
    
    trades = run.trades
    
    # Apply filters
    if status:
        trades = [t for t in trades if t.status.value == status.upper()]
    if strategy:
        trades = [t for t in trades if t.strategy == strategy.upper()]
    
    return {
        "runId": run.run_id,
        "trades": [t.to_dict() for t in trades[:limit]],
        "total": len(trades),
        "filters": {
            "status": status,
            "strategy": strategy
        }
    }


@router.get("/trades/distribution")
async def get_trade_distribution(run_id: Optional[str] = None):
    """
    Get trade distribution analysis.
    """
    if run_id:
        run = forward_repository.get_run(run_id)
    else:
        run = forward_repository.get_latest_run()
    
    if not run or not run.trades:
        return {"hasData": False}
    
    trades = run.trades
    closed = [t for t in trades if t.status.value != "OPEN"]
    
    if not closed:
        return {"hasData": False}
    
    # P&L distribution
    pnls = [t.pnl for t in closed]
    r_multiples = [t.r_multiple for t in closed]
    
    # Duration distribution
    durations = [t.duration_bars for t in closed]
    
    # By status
    by_status = {}
    for t in closed:
        s = t.status.value
        if s not in by_status:
            by_status[s] = 0
        by_status[s] += 1
    
    return {
        "runId": run.run_id,
        "totalTrades": len(closed),
        "pnlDistribution": {
            "min": round(min(pnls), 2),
            "max": round(max(pnls), 2),
            "avg": round(sum(pnls) / len(pnls), 2),
            "median": round(sorted(pnls)[len(pnls) // 2], 2)
        },
        "rMultipleDistribution": {
            "min": round(min(r_multiples), 2),
            "max": round(max(r_multiples), 2),
            "avg": round(sum(r_multiples) / len(r_multiples), 2)
        },
        "durationDistribution": {
            "min": min(durations),
            "max": max(durations),
            "avg": round(sum(durations) / len(durations), 1)
        },
        "byStatus": by_status
    }


# ===========================================
# Metrics
# ===========================================

@router.get("/metrics")
async def get_metrics(run_id: Optional[str] = None):
    """
    Get simulation metrics.
    """
    if run_id:
        run = forward_repository.get_run(run_id)
    else:
        run = forward_repository.get_latest_run()
    
    if not run:
        return {"hasData": False}
    
    return {
        "runId": run.run_id,
        "metrics": run.metrics.to_dict(),
        "config": run.config.to_dict()
    }


@router.get("/metrics/comparison")
async def compare_metrics(limit: int = Query(5, le=10)):
    """
    Compare metrics across recent runs.
    """
    runs = forward_repository.get_completed_runs(limit)
    
    if not runs:
        return {"hasData": False}
    
    comparison = []
    for run in runs:
        comparison.append({
            "runId": run.run_id,
            "scenario": run.config.scenario.value,
            "symbol": run.config.symbol,
            "metrics": {
                "totalReturn": round(run.metrics.total_return, 2),
                "totalReturnPct": round(run.metrics.total_return_pct, 2),
                "winRate": round(run.metrics.win_rate, 4),
                "profitFactor": round(run.metrics.profit_factor, 2),
                "maxDrawdownPct": round(run.metrics.max_drawdown_pct, 4),
                "sharpeRatio": round(run.metrics.sharpe_ratio, 2),
                "totalTrades": run.metrics.total_trades
            },
            "completedAt": run.completed_at
        })
    
    return {
        "comparison": comparison,
        "count": len(comparison)
    }


# ===========================================
# Scenarios
# ===========================================

@router.get("/scenarios")
async def get_scenarios():
    """Get available market scenarios"""
    from .market_replay_engine import market_replay_engine
    
    scenarios = []
    for scenario in MarketScenario:
        info = market_replay_engine.get_scenario_info(scenario)
        scenarios.append(info)
    
    return {
        "scenarios": scenarios,
        "count": len(scenarios)
    }


@router.get("/stats")
async def get_stats():
    """Get repository statistics"""
    return forward_repository.get_stats()
