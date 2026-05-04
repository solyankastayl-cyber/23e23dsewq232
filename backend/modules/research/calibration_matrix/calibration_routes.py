"""
Calibration Routes
==================

API endpoints for Strategy Calibration Matrix (PHASE 2.1)
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .calibration_runner import calibration_runner
from .calibration_types import CalibrationConfig


router = APIRouter(prefix="/api/calibration", tags=["phase2-calibration"])


# ===========================================
# Request Models
# ===========================================

class CalibrationRunRequest(BaseModel):
    """Request to start calibration run"""
    strategies: Optional[List[str]] = Field(
        None,
        description="Strategies to calibrate (default: all)"
    )
    symbols: Optional[List[str]] = Field(
        None,
        description="Symbols to calibrate (default: BTC, ETH, SOL)"
    )
    timeframes: Optional[List[str]] = Field(
        None,
        description="Timeframes to calibrate (default: 15m, 1h, 4h, 1d)"
    )
    regimes: Optional[List[str]] = Field(
        None,
        description="Regimes to calibrate (default: all)"
    )
    min_sample_size: int = Field(30, description="Minimum sample size")


class ResultQueryRequest(BaseModel):
    """Request for specific result"""
    strategy: str
    symbol: str
    timeframe: str
    regime: str


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for Calibration Matrix"""
    return calibration_runner.get_health()


# ===========================================
# Run Management
# ===========================================

@router.post("/run")
async def start_calibration(request: Optional[CalibrationRunRequest] = None):
    """
    Start new calibration run.
    
    Runs strategy x symbol x timeframe x regime matrix calibration.
    """
    
    config = CalibrationConfig()
    
    if request:
        if request.strategies:
            config.strategies = request.strategies
        if request.symbols:
            config.symbols = request.symbols
        if request.timeframes:
            config.timeframes = request.timeframes
        if request.regimes:
            config.regimes = request.regimes
        config.min_sample_size = request.min_sample_size
    
    run = calibration_runner.start_run(config)
    return run.to_dict()


@router.get("/run/{run_id}")
async def get_run(run_id: str):
    """Get calibration run by ID"""
    run = calibration_runner.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run.to_dict()


@router.get("/runs")
async def get_runs(limit: int = Query(20, le=100)):
    """Get recent calibration runs"""
    runs = calibration_runner.get_runs(limit)
    return {
        "runs": [r.to_dict() for r in runs],
        "count": len(runs)
    }


@router.get("/latest")
async def get_latest_run():
    """Get most recent calibration run"""
    run = calibration_runner.get_latest_run()
    if not run:
        return {"hasRun": False, "message": "No calibration runs yet"}
    return run.to_dict()


# ===========================================
# Matrix & Results
# ===========================================

@router.get("/matrix")
async def get_matrix():
    """
    Get latest calibration matrix.
    
    Returns complete strategy x symbol x timeframe x regime matrix.
    """
    matrix = calibration_runner.get_matrix()
    if not matrix:
        return {
            "hasMatrix": False,
            "message": "No calibration matrix yet. Run /api/calibration/run first."
        }
    return matrix.to_dict()


@router.get("/results")
async def get_results(
    strategy: Optional[str] = None,
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    regime: Optional[str] = None
):
    """
    Get calibration results with optional filters.
    """
    
    matrix = calibration_runner.get_matrix()
    if not matrix:
        return {"hasMatrix": False, "results": []}
    
    results = matrix.results
    
    # Apply filters
    if strategy:
        results = [r for r in results if r.strategy == strategy.upper()]
    if symbol:
        results = [r for r in results if r.symbol == symbol.upper()]
    if timeframe:
        results = [r for r in results if r.timeframe == timeframe.lower()]
    if regime:
        results = [r for r in results if r.regime == regime.upper()]
    
    return {
        "results": [r.to_dict() for r in results],
        "count": len(results),
        "filters": {
            "strategy": strategy,
            "symbol": symbol,
            "timeframe": timeframe,
            "regime": regime
        }
    }


@router.post("/result")
async def get_specific_result(request: ResultQueryRequest):
    """Get specific calibration result"""
    result = calibration_runner.get_result(
        request.strategy,
        request.symbol,
        request.timeframe,
        request.regime
    )
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Result not found for {request.strategy}/{request.symbol}/{request.timeframe}/{request.regime}"
        )
    return result


# ===========================================
# Strategy Endpoints
# ===========================================

@router.get("/strategy/{strategy}")
async def get_strategy_results(strategy: str):
    """
    Get all calibration results for a strategy.
    """
    results = calibration_runner.get_results_by_strategy(strategy)
    if not results:
        return {
            "strategy": strategy,
            "hasData": False,
            "message": f"No results for strategy {strategy}"
        }
    
    return {
        "strategy": strategy.upper(),
        "results": results,
        "count": len(results)
    }


@router.get("/strategy/{strategy}/summary")
async def get_strategy_summary(strategy: str):
    """
    Get summary metrics for a strategy.
    """
    return calibration_runner.get_strategy_summary(strategy)


# ===========================================
# Symbol Endpoints
# ===========================================

@router.get("/symbol/{symbol}")
async def get_symbol_results(symbol: str):
    """
    Get all calibration results for a symbol.
    """
    results = calibration_runner.get_results_by_symbol(symbol)
    if not results:
        return {
            "symbol": symbol,
            "hasData": False,
            "message": f"No results for symbol {symbol}"
        }
    
    return {
        "symbol": symbol.upper(),
        "results": results,
        "count": len(results)
    }


# ===========================================
# Top/Worst Performers
# ===========================================

@router.get("/top")
async def get_top_performers(limit: int = Query(10, le=50)):
    """
    Get top performing strategy combinations.
    """
    results = calibration_runner.get_top_performers(limit)
    return {
        "performers": results,
        "count": len(results),
        "sortedBy": "profitFactor"
    }


@router.get("/worst")
async def get_worst_performers(limit: int = Query(10, le=50)):
    """
    Get worst performing strategy combinations.
    """
    results = calibration_runner.get_worst_performers(limit)
    return {
        "performers": results,
        "count": len(results),
        "sortedBy": "profitFactor"
    }


# ===========================================
# Analysis Endpoints
# ===========================================

@router.get("/analysis/regime/{regime}")
async def analyze_regime(regime: str):
    """
    Analyze strategy performance across a regime.
    """
    matrix = calibration_runner.get_matrix()
    if not matrix:
        return {"hasMatrix": False}
    
    results = [r for r in matrix.results if r.regime == regime.upper() and r.is_valid]
    
    if not results:
        return {"regime": regime, "hasData": False}
    
    # Aggregate by strategy
    by_strategy = {}
    for r in results:
        if r.strategy not in by_strategy:
            by_strategy[r.strategy] = {
                "wins": 0,
                "losses": 0,
                "pf_sum": 0,
                "wr_sum": 0,
                "count": 0
            }
        s = by_strategy[r.strategy]
        s["count"] += 1
        s["pf_sum"] += r.metrics.profit_factor
        s["wr_sum"] += r.metrics.win_rate
    
    strategy_performance = {
        strat: {
            "avgProfitFactor": round(data["pf_sum"] / data["count"], 2),
            "avgWinRate": round(data["wr_sum"] / data["count"], 4),
            "combinations": data["count"]
        }
        for strat, data in by_strategy.items()
    }
    
    # Best strategy for regime
    best_strategy = max(
        strategy_performance.keys(),
        key=lambda k: strategy_performance[k]["avgProfitFactor"]
    )
    
    return {
        "regime": regime.upper(),
        "totalCombinations": len(results),
        "strategyPerformance": strategy_performance,
        "bestStrategy": best_strategy,
        "recommendation": f"Use {best_strategy} in {regime.upper()} regime"
    }


@router.get("/analysis/summary")
async def get_calibration_summary():
    """
    Get overall calibration summary.
    """
    matrix = calibration_runner.get_matrix()
    if not matrix:
        return {"hasMatrix": False}
    
    valid = [r for r in matrix.results if r.is_valid]
    
    # Overall stats
    avg_wr = sum(r.metrics.win_rate for r in valid) / len(valid) if valid else 0
    avg_pf = sum(r.metrics.profit_factor for r in valid) / len(valid) if valid else 0
    total_trades = sum(r.metrics.total_trades for r in valid)
    
    # By strategy
    strategies = set(r.strategy for r in valid)
    by_strategy = {}
    for s in strategies:
        strat_results = [r for r in valid if r.strategy == s]
        by_strategy[s] = {
            "avgWinRate": round(sum(r.metrics.win_rate for r in strat_results) / len(strat_results), 4),
            "avgProfitFactor": round(sum(r.metrics.profit_factor for r in strat_results) / len(strat_results), 2),
            "combinations": len(strat_results)
        }
    
    return {
        "summary": {
            "totalCombinations": matrix.total_combinations,
            "validCombinations": matrix.valid_combinations,
            "avgWinRate": round(avg_wr, 4),
            "avgProfitFactor": round(avg_pf, 2),
            "totalTrades": total_trades,
            "gradeDistribution": matrix.grade_distribution
        },
        "byStrategy": by_strategy,
        "bestPerformers": matrix.best_performers[:3],
        "worstPerformers": matrix.worst_performers[:3],
        "computedAt": matrix.computed_at
    }
