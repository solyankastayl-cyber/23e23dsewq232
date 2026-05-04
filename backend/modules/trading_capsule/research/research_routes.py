"""
Research Routes (S2)
====================

REST API for Strategy Research Lab.

Endpoints:

# Experiments (S2.1)
POST /api/research/experiments              - Create experiment
GET  /api/research/experiments              - List experiments
GET  /api/research/experiments/{id}         - Get experiment
POST /api/research/experiments/{id}/start   - Start experiment
POST /api/research/experiments/{id}/cancel  - Cancel experiment
DELETE /api/research/experiments/{id}       - Delete experiment

# Runs (S2.2)
GET /api/research/experiments/{id}/runs     - Get experiment runs

# Comparison (S2.3)
GET /api/research/experiments/{id}/compare  - Compare strategies

# Ranking (S2.4)
GET /api/research/experiments/{id}/ranking  - Get strategy ranking
GET /api/research/experiments/{id}/winner   - Get winning strategy
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from .experiment_types import ExperimentStatus
from .experiment_manager import experiment_manager
from .simulation_runner import simulation_runner
from .strategy_comparator import strategy_comparator
from .ranking_engine import ranking_engine
from ...research_analytics.chart_data import get_chart_data_service


router = APIRouter(tags=["Research Lab (S2)"])


# ===========================================
# Request Models
# ===========================================

class CreateExperimentRequest(BaseModel):
    """Request body for creating experiment"""
    name: str
    asset: str = "BTCUSDT"
    strategies: List[str]
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    capital_profile: str = "SMALL"  # SMALL, MEDIUM, LARGE
    initial_capital_usd: Optional[float] = None
    timeframe: str = "1D"  # 1D, 4H, 1H
    description: str = ""


# ===========================================
# Experiments (S2.1)
# ===========================================

@router.post("/experiments")
async def create_experiment(request: CreateExperimentRequest):
    """
    Create a new research experiment.
    
    Single asset / single dataset / N strategies.
    """
    if not request.strategies:
        raise HTTPException(
            status_code=400,
            detail="At least one strategy is required"
        )
    
    experiment = experiment_manager.create_experiment(
        name=request.name,
        asset=request.asset,
        strategies=request.strategies,
        start_date=request.start_date,
        end_date=request.end_date,
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
async def list_experiments(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Max results")
):
    """
    List all experiments.
    """
    status_filter = None
    if status:
        try:
            status_filter = ExperimentStatus(status)
        except ValueError:
            pass
    
    experiments = experiment_manager.list_experiments(
        status=status_filter,
        limit=limit
    )
    
    return {
        "experiments": [e.to_dict() for e in experiments],
        "count": len(experiments)
    }


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    """
    Get experiment by ID.
    """
    experiment = experiment_manager.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment not found: {experiment_id}"
        )
    
    return experiment.to_dict()


@router.post("/experiments/{experiment_id}/start")
async def start_experiment(experiment_id: str):
    """
    Start an experiment.
    
    Generates runs and starts simulations.
    """
    experiment = experiment_manager.start_experiment(experiment_id)
    if not experiment:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment not found: {experiment_id}"
        )
    
    # Start simulation runs
    runs_started = simulation_runner.start_runs(experiment_id)
    
    return {
        "status": "started",
        "experiment_id": experiment_id,
        "runs_started": runs_started,
        "experiment": experiment.to_dict()
    }


@router.post("/experiments/{experiment_id}/cancel")
async def cancel_experiment(experiment_id: str):
    """
    Cancel running experiment.
    """
    # Cancel simulation runs
    simulation_runner.cancel_runs(experiment_id)
    
    # Update experiment status
    experiment = experiment_manager.cancel_experiment(experiment_id)
    if not experiment:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment not found: {experiment_id}"
        )
    
    return {
        "status": "cancelled",
        "experiment": experiment.to_dict()
    }


@router.delete("/experiments/{experiment_id}")
async def delete_experiment(experiment_id: str):
    """
    Delete experiment and all associated runs.
    """
    success = experiment_manager.delete_experiment(experiment_id)
    
    return {
        "status": "deleted" if success else "failed",
        "experiment_id": experiment_id
    }


# ===========================================
# Runs (S2.2)
# ===========================================

@router.get("/experiments/{experiment_id}/runs")
async def get_experiment_runs(experiment_id: str):
    """
    Get all runs for an experiment.
    """
    runs = experiment_manager.get_experiment_runs(experiment_id)
    
    return {
        "experiment_id": experiment_id,
        "runs": [r.to_dict() for r in runs],
        "count": len(runs)
    }


# ===========================================
# Comparison (S2.3)
# ===========================================

@router.get("/experiments/{experiment_id}/compare")
async def compare_strategies(experiment_id: str):
    """
    Compare all strategies in an experiment.
    
    Returns normalized metrics and warnings for each strategy.
    """
    comparables = strategy_comparator.compare_experiment(experiment_id)
    
    # Build dominance map
    dominance = strategy_comparator.get_dominance_map(comparables)
    
    return {
        "experiment_id": experiment_id,
        "strategies": [c.to_dict() for c in comparables],
        "dominance_map": dominance,
        "count": len(comparables)
    }


@router.get("/experiments/{experiment_id}/scorecards")
async def get_scorecards(experiment_id: str):
    """
    Get raw scorecards for all strategies.
    """
    scorecards = strategy_comparator.collect_scorecards(experiment_id)
    
    return {
        "experiment_id": experiment_id,
        "scorecards": [sc.to_dict() for sc in scorecards],
        "count": len(scorecards)
    }


# ===========================================
# Ranking (S2.4)
# ===========================================

@router.get("/experiments/{experiment_id}/ranking")
async def get_ranking(
    experiment_id: str,
    policy: str = Query("default", description="Ranking policy")
):
    """
    Get strategy ranking for an experiment.
    
    Returns leaderboard with composite scores.
    """
    leaderboard = ranking_engine.rank_experiment(
        experiment_id,
        policy=policy
    )
    
    return leaderboard.to_dict()


@router.get("/experiments/{experiment_id}/winner")
async def get_winner(experiment_id: str):
    """
    Get the winning strategy for an experiment.
    """
    winner = ranking_engine.get_winner(experiment_id)
    
    if not winner:
        return {
            "experiment_id": experiment_id,
            "winner": None,
            "message": "No valid strategies found"
        }
    
    return {
        "experiment_id": experiment_id,
        "winner": winner.to_dict()
    }


@router.get("/experiments/{experiment_id}/top")
async def get_top_strategies(
    experiment_id: str,
    count: int = Query(3, description="Number of top strategies")
):
    """
    Get top N strategies for an experiment.
    """
    top = ranking_engine.get_top_strategies(experiment_id, count)
    
    return {
        "experiment_id": experiment_id,
        "top_strategies": [t.to_dict() for t in top],
        "count": len(top)
    }


@router.get("/experiments/{experiment_id}/strategies/{strategy_id}/breakdown")
async def get_strategy_breakdown(
    experiment_id: str,
    strategy_id: str
):
    """
    Get detailed ranking breakdown for a specific strategy.
    """
    breakdown = ranking_engine.get_ranking_breakdown(
        experiment_id,
        strategy_id
    )
    
    if not breakdown:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy not found in experiment: {strategy_id}"
        )
    
    return breakdown


@router.get("/experiments/{experiment_id}/compare/{strategy_a}/{strategy_b}")
async def compare_two_strategies(
    experiment_id: str,
    strategy_a: str,
    strategy_b: str
):
    """
    Direct comparison of two strategies.
    """
    comparison = ranking_engine.compare_two_strategies(
        experiment_id,
        strategy_a,
        strategy_b
    )
    
    return comparison


# ===========================================
# Chart Data Endpoint
# ===========================================

@router.get("/chart/{symbol}")
async def get_chart_data(
    symbol: str,
    timeframe: str = Query("1d", description="Timeframe"),
    limit: int = Query(500, description="Number of candles")
):
    """
    Get chart data for research analysis.
    
    Returns candles and volume data for chart visualization.
    """
    try:
        chart_service = get_chart_data_service()
        chart_data = await chart_service.get_chart_data(
            symbol=symbol.upper(),
            timeframe=timeframe,
            limit=limit,
            include_volume=True
        )
        
        return {
            "ok": True,
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "candles": chart_data.candles,
            "volume": chart_data.volume,
            "metadata": chart_data.metadata,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "candles": [],
            "volume": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# ===========================================
# Health
# ===========================================

@router.get("/health")
async def research_health():
    """
    Health check for Research Lab.
    """
    return {
        "status": "healthy",
        "version": "S2.4",
        "modules": {
            "experiment_manager": "ready",
            "run_generator": "ready",
            "simulation_runner": "ready",
            "strategy_comparator": "ready",
            "ranking_engine": "ready"
        },
        "config": {
            "max_parallel_runs": simulation_runner.max_parallel,
            "ranking_metrics": list(ranking_engine.weights.keys())
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
