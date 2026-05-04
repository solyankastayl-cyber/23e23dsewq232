"""
Walk Forward Routes (S2.6)
==========================

REST API for Walk Forward analysis.

Endpoints:

# Experiments
POST /api/research/walkforward/experiments              - Create WF experiment
GET  /api/research/walkforward/experiments              - List WF experiments
GET  /api/research/walkforward/experiments/{id}         - Get experiment
POST /api/research/walkforward/experiments/{id}/start   - Start experiment
DELETE /api/research/walkforward/experiments/{id}       - Delete experiment

# Windows
GET /api/research/walkforward/experiments/{id}/windows  - Get windows

# Runs
GET /api/research/walkforward/experiments/{id}/runs     - Get all runs

# Results & Robustness
GET /api/research/walkforward/experiments/{id}/results    - Get full results
GET /api/research/walkforward/experiments/{id}/robustness - Get robustness analysis
GET /api/research/walkforward/experiments/{id}/best       - Get best strategy
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from .walkforward_types import WalkForwardStatus
from .walkforward_engine import walkforward_engine
from .robustness_analyzer import robustness_analyzer
from .window_generator import window_generator


router = APIRouter(tags=["Walk Forward (S2.6)"])


# ===========================================
# Request Models
# ===========================================

class CreateWFExperimentRequest(BaseModel):
    """Request body for creating Walk Forward experiment"""
    name: str
    asset: str = "BTCUSDT"
    strategies: List[str]
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    train_window_bars: int = 730   # ~2 years daily
    test_window_bars: int = 365    # ~1 year daily
    step_bars: int = 365           # Roll forward 1 year
    capital_profile: str = "SMALL"
    initial_capital_usd: Optional[float] = None
    timeframe: str = "1D"
    description: str = ""


# ===========================================
# Experiments
# ===========================================

@router.post("/experiments")
async def create_wf_experiment(request: CreateWFExperimentRequest):
    """
    Create a new Walk Forward experiment.
    
    Walk Forward analyzes strategy robustness by:
    - Splitting data into rolling train/test windows
    - Comparing train vs test performance
    - Calculating degradation and stability
    - Determining verdict: ROBUST, STABLE, WEAK, OVERFIT, UNSTABLE
    """
    if not request.strategies:
        raise HTTPException(
            status_code=400,
            detail="At least one strategy is required"
        )
    
    if request.train_window_bars <= 0 or request.test_window_bars <= 0:
        raise HTTPException(
            status_code=400,
            detail="Window sizes must be positive"
        )
    
    experiment = walkforward_engine.create_experiment(
        name=request.name,
        asset=request.asset,
        strategies=request.strategies,
        start_date=request.start_date,
        end_date=request.end_date,
        train_window_bars=request.train_window_bars,
        test_window_bars=request.test_window_bars,
        step_bars=request.step_bars,
        capital_profile=request.capital_profile,
        initial_capital_usd=request.initial_capital_usd,
        timeframe=request.timeframe,
        description=request.description
    )
    
    return {
        "status": "created",
        "experiment": experiment.to_dict()
    }


@router.get("/experiments")
async def list_wf_experiments(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Max results")
):
    """
    List Walk Forward experiments.
    """
    status_filter = None
    if status:
        try:
            status_filter = WalkForwardStatus(status)
        except ValueError:
            pass
    
    experiments = walkforward_engine.list_experiments(
        status=status_filter,
        limit=limit
    )
    
    return {
        "experiments": [e.to_dict() for e in experiments],
        "count": len(experiments)
    }


@router.get("/experiments/{experiment_id}")
async def get_wf_experiment(experiment_id: str):
    """
    Get Walk Forward experiment by ID.
    """
    experiment = walkforward_engine.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment not found: {experiment_id}"
        )
    
    return experiment.to_dict()


@router.post("/experiments/{experiment_id}/start")
async def start_wf_experiment(experiment_id: str):
    """
    Start Walk Forward experiment.
    
    Generates windows and starts train/test simulations.
    """
    experiment = walkforward_engine.start_experiment(experiment_id)
    if not experiment:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment not found: {experiment_id}"
        )
    
    return {
        "status": "started",
        "experiment_id": experiment_id,
        "total_windows": experiment.total_windows,
        "strategies_count": len(experiment.strategies),
        "experiment": experiment.to_dict()
    }


@router.delete("/experiments/{experiment_id}")
async def delete_wf_experiment(experiment_id: str):
    """
    Delete Walk Forward experiment.
    """
    success = walkforward_engine.delete_experiment(experiment_id)
    
    # Also clear robustness cache
    robustness_analyzer.clear_cache(experiment_id)
    
    return {
        "status": "deleted" if success else "failed",
        "experiment_id": experiment_id
    }


# ===========================================
# Windows
# ===========================================

@router.get("/experiments/{experiment_id}/windows")
async def get_windows(experiment_id: str):
    """
    Get all windows for experiment.
    
    Each window shows:
    - Train period (start/end bars and dates)
    - Test period (start/end bars and dates)
    """
    windows = walkforward_engine.get_windows(experiment_id)
    
    return {
        "experiment_id": experiment_id,
        "windows": [w.to_dict() for w in windows],
        "count": len(windows)
    }


@router.get("/experiments/{experiment_id}/windows/preview")
async def preview_windows(
    experiment_id: str,
    dataset_length: int = Query(2000, description="Dataset length in bars"),
    train_bars: int = Query(730, description="Train window size"),
    test_bars: int = Query(365, description="Test window size"),
    step_bars: int = Query(365, description="Step size")
):
    """
    Preview windows that would be generated.
    
    Useful before creating experiment.
    """
    count = window_generator.calculate_windows_count(
        dataset_length,
        train_bars,
        test_bars,
        step_bars
    )
    
    # Generate sample windows
    windows = window_generator.generate_windows(
        experiment_id="preview",
        dataset_length_bars=dataset_length,
        train_window_bars=train_bars,
        test_window_bars=test_bars,
        step_bars=step_bars
    )
    
    return {
        "total_windows": count,
        "windows_preview": [w.to_dict() for w in windows[:5]],
        "config": {
            "dataset_length": dataset_length,
            "train_bars": train_bars,
            "test_bars": test_bars,
            "step_bars": step_bars
        }
    }


# ===========================================
# Runs
# ===========================================

@router.get("/experiments/{experiment_id}/runs")
async def get_runs(experiment_id: str):
    """
    Get all runs for experiment.
    
    Each run links a strategy to a window's train/test simulations.
    """
    runs = walkforward_engine.get_runs(experiment_id)
    
    return {
        "experiment_id": experiment_id,
        "runs": [r.to_dict() for r in runs],
        "count": len(runs)
    }


@router.get("/experiments/{experiment_id}/runs/by-window/{window_id}")
async def get_runs_by_window(
    experiment_id: str,
    window_id: str
):
    """
    Get runs for a specific window.
    """
    runs = walkforward_engine.get_runs_by_window(experiment_id, window_id)
    
    return {
        "experiment_id": experiment_id,
        "window_id": window_id,
        "runs": [r.to_dict() for r in runs],
        "count": len(runs)
    }


# ===========================================
# Results & Robustness
# ===========================================

@router.get("/experiments/{experiment_id}/results")
async def get_results(experiment_id: str):
    """
    Get complete Walk Forward results.
    
    Includes:
    - Robustness analysis for each strategy
    - Train vs test comparisons
    - Best strategy selection
    """
    results = robustness_analyzer.get_results(experiment_id)
    
    if not results:
        return {
            "experiment_id": experiment_id,
            "error": "No results available"
        }
    
    return results.to_dict()


@router.get("/experiments/{experiment_id}/robustness")
async def get_robustness(experiment_id: str):
    """
    Get robustness analysis summary.
    
    Returns:
    - Robustness score per strategy
    - Verdict (ROBUST, STABLE, WEAK, OVERFIT, UNSTABLE)
    - Train vs test degradation
    - Stability metrics
    """
    results = robustness_analyzer.get_results(experiment_id)
    
    if not results:
        return {
            "experiment_id": experiment_id,
            "strategies": [],
            "error": "Analysis not available"
        }
    
    # Simplified robustness view
    strategy_summaries = []
    for r in results.strategy_results:
        strategy_summaries.append({
            "strategy_id": r.strategy_id,
            "robustness_score": round(r.robustness_score, 4),
            "stability_score": round(r.stability_score, 4),
            "degradation_score": round(r.degradation_score, 4),
            "verdict": r.verdict.value,
            "verdict_reasons": r.verdict_reasons,
            "avg_train_sharpe": round(r.avg_train_sharpe, 4),
            "avg_test_sharpe": round(r.avg_test_sharpe, 4),
            "sharpe_degradation": round(r.avg_sharpe_degradation, 4)
        })
    
    return {
        "experiment_id": experiment_id,
        "strategies": strategy_summaries,
        "best_strategy": {
            "strategy_id": results.best_strategy_id,
            "robustness_score": round(results.best_robustness_score, 4)
        },
        "summary": {
            "total_strategies": results.total_strategies,
            "robust_count": results.robust_count,
            "overfit_count": results.overfit_count
        },
        "analyzed_at": results.analyzed_at
    }


@router.get("/experiments/{experiment_id}/best")
async def get_best_strategy(experiment_id: str):
    """
    Get the best (most robust) strategy.
    """
    results = robustness_analyzer.get_results(experiment_id)
    
    if not results or not results.best_strategy_id:
        return {
            "experiment_id": experiment_id,
            "best_strategy": None,
            "message": "No robust strategy found"
        }
    
    # Find the best strategy's full robustness data
    best_robustness = robustness_analyzer.get_strategy_robustness(
        experiment_id,
        results.best_strategy_id
    )
    
    return {
        "experiment_id": experiment_id,
        "best_strategy": best_robustness.to_dict() if best_robustness else None
    }


@router.get("/experiments/{experiment_id}/strategies/{strategy_id}")
async def get_strategy_robustness(
    experiment_id: str,
    strategy_id: str
):
    """
    Get detailed robustness for a specific strategy.
    """
    robustness = robustness_analyzer.get_strategy_robustness(
        experiment_id,
        strategy_id
    )
    
    if not robustness:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy not found: {strategy_id}"
        )
    
    return robustness.to_dict()


# ===========================================
# Health
# ===========================================

@router.get("/health")
async def walkforward_health():
    """
    Health check for Walk Forward Engine.
    """
    return {
        "status": "healthy",
        "version": "S2.6",
        "modules": {
            "window_generator": "ready",
            "walkforward_engine": "ready",
            "robustness_analyzer": "ready"
        },
        "config": {
            "max_parallel_windows": 2,
            "robustness_weights": {
                "test_sharpe": 0.35,
                "test_pf": 0.20,
                "test_calmar": 0.15,
                "stability": 0.15,
                "low_degradation": 0.15
            }
        },
        "verdicts": ["ROBUST", "STABLE", "WEAK", "OVERFIT", "UNSTABLE"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
