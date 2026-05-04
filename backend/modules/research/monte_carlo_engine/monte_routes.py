"""
PHASE 6.3 - Monte Carlo Routes
===============================
REST API endpoints for Monte Carlo Engine.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from .monte_types import (
    MonteCarloRun, MonteCarloResult, MonteCarloMethod,
    MonteCarloStatus, MonteCarloVerdict, TradeRecord
)
from .monte_registry import get_monte_registry
from .monte_simulator import MonteCarloSimulator
from .equity_curve_generator import EquityCurveGenerator
from .drawdown_analyzer import DrawdownAnalyzer
from .risk_of_ruin import RiskOfRuinCalculator
from .monte_evaluator import MonteCarloEvaluator
from .monte_repository import MonteCarloRepository

router = APIRouter(prefix="/api/monte", tags=["Monte Carlo Engine"])

# Initialize components
_repository: Optional[MonteCarloRepository] = None
_evaluator: Optional[MonteCarloEvaluator] = None


def get_repository() -> MonteCarloRepository:
    global _repository
    if _repository is None:
        _repository = MonteCarloRepository()
    return _repository


def get_evaluator() -> MonteCarloEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = MonteCarloEvaluator()
    return _evaluator


# ==================== Request/Response Models ====================

class TradeInput(BaseModel):
    trade_id: str
    return_pct: float
    duration_candles: int = 1
    win: bool = True
    risk_taken: float = 0.02


class MonteCarloRunRequest(BaseModel):
    strategy_id: str
    symbol: str = "BTC"
    timeframe: str = "1d"
    trades: Optional[List[TradeInput]] = None  # If None, will generate mock
    iterations: int = 1000
    method: str = "COMBINED"
    noise_level: float = 0.1
    config_id: Optional[str] = None  # Use preset config


class MockTradesRequest(BaseModel):
    n_trades: int = 100
    win_rate: float = 0.55
    avg_win: float = 0.02
    avg_loss: float = 0.015


# ==================== Health & Status ====================

@router.get("/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "module": "monte_carlo_engine",
        "version": "phase6.3",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ==================== Static routes (before /{run_id}) ====================

@router.get("/top")
async def get_top_strategies(limit: int = 10):
    """Get strategies with best risk profiles"""
    repo = get_repository()
    results = repo.get_top_strategies(limit)
    
    return {
        "count": len(results),
        "top_strategies": results
    }


@router.get("/risky")
async def get_risky_strategies(limit: int = 10):
    """Get strategies with worst risk profiles"""
    repo = get_repository()
    results = repo.get_risky_strategies(limit)
    
    return {
        "count": len(results),
        "risky_strategies": results
    }


@router.get("/stats/overview")
async def get_stats():
    """Get overall statistics"""
    repo = get_repository()
    registry = get_monte_registry()
    
    db_stats = repo.get_statistics()
    registry_stats = registry.get_stats()
    
    return {
        "database": db_stats,
        "registry": registry_stats,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/registry")
async def get_registry_info():
    """Get Monte Carlo registry information"""
    registry = get_monte_registry()
    
    configs = registry.get_all()
    stats = registry.get_stats()
    
    return {
        "total": len(configs),
        "stats": stats,
        "methods": [m.value for m in MonteCarloMethod],
        "verdicts": [v.value for v in MonteCarloVerdict],
        "configs": [c.to_dict() for c in configs]
    }


@router.get("/configs")
async def get_configs():
    """Get all simulation configuration presets"""
    registry = get_monte_registry()
    configs = registry.get_all()
    
    return {
        "count": len(configs),
        "configs": [c.to_dict() for c in configs]
    }


# ==================== Run Monte Carlo ====================

@router.post("/run")
async def run_monte_carlo(request: MonteCarloRunRequest):
    """Run Monte Carlo simulation"""
    
    repo = get_repository()
    evaluator = get_evaluator()
    
    # Get configuration
    config = None
    if request.config_id:
        registry = get_monte_registry()
        config = registry.get(request.config_id)
    
    iterations = config.iterations if config else request.iterations
    method_str = config.method.value if config else request.method
    noise_level = config.noise_level if config else request.noise_level
    
    try:
        method = MonteCarloMethod(method_str)
    except ValueError:
        method = MonteCarloMethod.COMBINED
    
    # Get or generate trades
    if request.trades:
        trades = [
            TradeRecord(
                trade_id=t.trade_id,
                return_pct=t.return_pct,
                duration_candles=t.duration_candles,
                win=t.win,
                risk_taken=t.risk_taken
            )
            for t in request.trades
        ]
    else:
        # Generate mock trades
        trades = MonteCarloSimulator.generate_mock_trades(
            n_trades=100,
            win_rate=0.55,
            avg_win=0.02,
            avg_loss=0.015,
            strategy_id=request.strategy_id
        )
    
    # Create run
    run = MonteCarloRun(
        run_id=f"mc_{uuid.uuid4().hex[:12]}",
        strategy_id=request.strategy_id,
        symbol=request.symbol,
        timeframe=request.timeframe,
        iterations=iterations,
        method=method,
        noise_level=noise_level,
        trades_count=len(trades),
        started_at=datetime.now(timezone.utc),
        status=MonteCarloStatus.RUNNING
    )
    
    try:
        # Run simulation
        simulator = MonteCarloSimulator(trades, method=method, noise_level=noise_level)
        simulations = simulator.simulate(iterations)
        
        # Generate equity curves
        equity_gen = EquityCurveGenerator()
        curves = equity_gen.generate_curves(simulations)
        
        run.status = MonteCarloStatus.COMPLETED
        run.finished_at = datetime.now(timezone.utc)
        
        # Save run
        repo.save_run(run)
        
        # Evaluate results
        result = evaluator.evaluate(run, curves)
        
        # Save result
        repo.save_result(result)
        
        return {
            "success": True,
            "run": run.to_dict(),
            "result": result.to_dict()
        }
        
    except Exception as e:
        run.status = MonteCarloStatus.FAILED
        run.error = str(e)
        run.finished_at = datetime.now(timezone.utc)
        repo.save_run(run)
        
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-batch")
async def run_batch(
    strategies: List[str],
    iterations: int = 1000,
    method: str = "COMBINED"
):
    """Run Monte Carlo for multiple strategies"""
    
    repo = get_repository()
    evaluator = get_evaluator()
    results = []
    
    try:
        monte_method = MonteCarloMethod(method)
    except ValueError:
        monte_method = MonteCarloMethod.COMBINED
    
    for strategy_id in strategies:
        try:
            # Generate mock trades for each strategy
            trades = MonteCarloSimulator.generate_mock_trades(
                n_trades=100,
                win_rate=0.55 + (hash(strategy_id) % 10) / 100,  # Vary win rate
                avg_win=0.02,
                avg_loss=0.015,
                strategy_id=strategy_id
            )
            
            run = MonteCarloRun(
                run_id=f"mc_{uuid.uuid4().hex[:12]}",
                strategy_id=strategy_id,
                symbol="BTC",
                timeframe="1d",
                iterations=iterations,
                method=monte_method,
                trades_count=len(trades),
                started_at=datetime.now(timezone.utc),
                status=MonteCarloStatus.RUNNING
            )
            
            simulator = MonteCarloSimulator(trades, method=monte_method)
            simulations = simulator.simulate(iterations)
            
            equity_gen = EquityCurveGenerator()
            curves = equity_gen.generate_curves(simulations)
            
            run.status = MonteCarloStatus.COMPLETED
            run.finished_at = datetime.now(timezone.utc)
            repo.save_run(run)
            
            result = evaluator.evaluate(run, curves)
            repo.save_result(result)
            
            results.append({
                "strategy_id": strategy_id,
                "success": True,
                "verdict": result.verdict.value,
                "risk_score": round(result.risk_score, 3),
                "profit_probability": round(result.profit_probability, 3),
                "p95_drawdown": round(result.drawdown_distribution.p95_drawdown, 4)
            })
            
        except Exception as e:
            results.append({
                "strategy_id": strategy_id,
                "success": False,
                "error": str(e)
            })
    
    successful = [r for r in results if r.get('success')]
    
    return {
        "batch_size": len(strategies),
        "successful": len(successful),
        "failed": len(strategies) - len(successful),
        "results": results
    }


# ==================== Results ====================

@router.get("/results")
async def get_results(
    strategy_id: Optional[str] = None,
    verdict: Optional[str] = None,
    limit: int = 20
):
    """Get Monte Carlo results"""
    repo = get_repository()
    
    if strategy_id:
        results = repo.get_results_for_strategy(strategy_id, limit)
    elif verdict:
        results = repo.get_results_by_verdict(verdict)[:limit]
    else:
        results = repo.get_recent_runs(limit)
    
    return {
        "count": len(results),
        "results": results
    }


@router.get("/{run_id}")
async def get_run(run_id: str):
    """Get Monte Carlo run details"""
    repo = get_repository()
    
    run = repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    result = repo.get_result(run_id)
    
    return {
        "run": run,
        "result": result
    }


@router.get("/{run_id}/distribution")
async def get_distribution(run_id: str):
    """Get return and drawdown distribution for a run"""
    repo = get_repository()
    
    result = repo.get_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    return {
        "run_id": run_id,
        "return_distribution": result.get("return_distribution", {}),
        "drawdown_distribution": result.get("drawdown_distribution", {}),
        "risk_of_ruin": result.get("risk_of_ruin", {})
    }


@router.get("/{run_id}/equity")
async def get_equity_info(run_id: str):
    """Get equity curve information for a run"""
    repo = get_repository()
    
    result = repo.get_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    return {
        "run_id": run_id,
        "iterations": result.get("iterations", 0),
        "profit_probability": result.get("profit_probability", 0),
        "ci_95": {
            "lower": result.get("ci_95_lower", 0),
            "upper": result.get("ci_95_upper", 0)
        },
        "ci_99": {
            "lower": result.get("ci_99_lower", 0),
            "upper": result.get("ci_99_upper", 0)
        },
        "sharpe_ratio_median": result.get("sharpe_ratio_median", 0),
        "sortino_ratio_median": result.get("sortino_ratio_median", 0)
    }


# ==================== Utilities ====================

@router.post("/generate-mock-trades")
async def generate_mock_trades(request: MockTradesRequest):
    """Generate mock trades for testing"""
    trades = MonteCarloSimulator.generate_mock_trades(
        n_trades=request.n_trades,
        win_rate=request.win_rate,
        avg_win=request.avg_win,
        avg_loss=request.avg_loss,
        strategy_id="MOCK"
    )
    
    return {
        "count": len(trades),
        "trades": [t.to_dict() for t in trades],
        "parameters": {
            "n_trades": request.n_trades,
            "win_rate": request.win_rate,
            "avg_win": request.avg_win,
            "avg_loss": request.avg_loss
        }
    }


class KellyRequest(BaseModel):
    win_rate: float
    avg_win: float
    avg_loss: float
    fraction: float = 0.5


@router.post("/calculate-kelly")
async def calculate_kelly(request: KellyRequest):
    """Calculate Kelly Criterion for position sizing"""
    ror_calc = RiskOfRuinCalculator()
    
    full_kelly = ror_calc.calculate_kelly_criterion(request.win_rate, request.avg_win, request.avg_loss)
    fractional_kelly = ror_calc.calculate_fractional_kelly(request.win_rate, request.avg_win, request.avg_loss, request.fraction)
    theoretical_ror = ror_calc.theoretical_risk_of_ruin(request.win_rate, request.avg_win, request.avg_loss)
    
    return {
        "full_kelly": round(full_kelly, 4),
        "fractional_kelly": round(fractional_kelly, 4),
        "fraction_used": request.fraction,
        "theoretical_risk_of_ruin": round(theoretical_ror, 4),
        "inputs": {
            "win_rate": request.win_rate,
            "avg_win": request.avg_win,
            "avg_loss": request.avg_loss
        }
    }

