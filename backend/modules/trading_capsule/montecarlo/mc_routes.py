"""
Monte Carlo Routes (S5)
=======================

API endpoints for Monte Carlo Stress Engine.

Endpoints:
- POST /api/montecarlo/experiments - Create experiment
- GET  /api/montecarlo/experiments - List experiments
- GET  /api/montecarlo/experiments/{id} - Get experiment
- POST /api/montecarlo/experiments/{id}/run - Run experiment
- GET  /api/montecarlo/experiments/{id}/results - Get results
- GET  /api/montecarlo/experiments/{id}/distribution - Get distribution
- GET  /api/montecarlo/experiments/{id}/tail-risk - Get tail risk
- GET  /api/montecarlo/experiments/{id}/scenarios - Get scenarios
- GET  /api/montecarlo/experiments/{id}/paths - Get paths
- DELETE /api/montecarlo/experiments/{id} - Delete experiment
- GET  /api/montecarlo/health - Health check
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from .mc_types import ExperimentStatus, PathGeneratorType
from .mc_simulation_engine import mc_simulation_engine
from .mc_distribution_analyzer import mc_distribution_analyzer

router = APIRouter(prefix="/api/montecarlo", tags=["Monte Carlo S5"])


# ===========================================
# Request Models
# ===========================================

class CreateExperimentRequest(BaseModel):
    """Request to create Monte Carlo experiment"""
    portfolio_simulation_id: str = Field(..., description="Source portfolio simulation ID")
    num_paths: int = Field(1000, ge=10, le=10000, description="Number of simulation paths")
    horizon_days: int = Field(365, ge=30, le=730, description="Simulation horizon in days")
    generator_type: str = Field("BOOTSTRAP", description="Path generation method: BOOTSTRAP, NOISE_INJECTION, CRASH_INJECTION, REGIME_SWITCH, MIXED")
    name: str = Field("", description="Optional experiment name")
    description: str = Field("", description="Optional description")
    
    # Advanced settings
    noise_std: float = Field(0.02, ge=0.0, le=0.1, description="Noise standard deviation")
    crash_probability: float = Field(0.05, ge=0.0, le=0.5, description="Probability of crash per path")
    crash_severity_min: float = Field(-0.20, ge=-0.50, le=0.0, description="Min crash magnitude")
    crash_severity_max: float = Field(-0.50, ge=-0.90, le=-0.10, description="Max crash magnitude")


class RunExperimentRequest(BaseModel):
    """Request to run experiment"""
    initial_capital: float = Field(100000.0, ge=1000, description="Reference capital for simulation")
    use_synthetic_returns: bool = Field(False, description="Use synthetic returns if no portfolio data")


# ===========================================
# Create Experiment
# ===========================================

@router.post("/experiments", summary="Create Monte Carlo Experiment")
async def create_experiment(request: CreateExperimentRequest):
    """
    Create a new Monte Carlo stress test experiment.
    
    Generator types:
    - BOOTSTRAP: Shuffle historical returns (safest)
    - NOISE_INJECTION: Add random noise
    - CRASH_INJECTION: Add market crashes
    - REGIME_SWITCH: Simulate regime changes
    - MIXED: Combination of methods
    """
    try:
        experiment = mc_simulation_engine.create_experiment(
            portfolio_simulation_id=request.portfolio_simulation_id,
            num_paths=request.num_paths,
            horizon_days=request.horizon_days,
            generator_type=request.generator_type,
            name=request.name,
            description=request.description,
            noise_std=request.noise_std,
            crash_probability=request.crash_probability,
            crash_severity_min=request.crash_severity_min,
            crash_severity_max=request.crash_severity_max
        )
        
        return {
            "success": True,
            "experiment": experiment.to_dict()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# List Experiments
# ===========================================

@router.get("/experiments", summary="List Monte Carlo Experiments")
async def list_experiments(
    limit: int = Query(50, ge=1, le=100)
):
    """List all Monte Carlo experiments"""
    experiments = mc_simulation_engine.list_experiments(limit)
    
    return {
        "experiments": [e.to_dict() for e in experiments],
        "count": len(experiments)
    }


# ===========================================
# Get Experiment
# ===========================================

@router.get("/experiments/{experiment_id}", summary="Get Monte Carlo Experiment")
async def get_experiment(experiment_id: str):
    """Get experiment details"""
    experiment = mc_simulation_engine.get_experiment(experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    
    return experiment.to_dict()


# ===========================================
# Run Experiment
# ===========================================

@router.post("/experiments/{experiment_id}/run", summary="Run Monte Carlo Experiment")
async def run_experiment(
    experiment_id: str,
    request: RunExperimentRequest,
    background_tasks: BackgroundTasks
):
    """
    Run Monte Carlo experiment.
    
    Generates all simulation paths and calculates metrics.
    For large experiments (>500 paths), consider running in background.
    """
    experiment = mc_simulation_engine.get_experiment(experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    
    if experiment.status == ExperimentStatus.RUNNING:
        return {
            "success": False,
            "message": "Experiment is already running",
            "experiment": experiment.to_dict()
        }
    
    try:
        # Run experiment (blocking for now, can be moved to background)
        result = mc_simulation_engine.run_experiment(
            experiment_id=experiment_id,
            initial_capital=request.initial_capital
        )
        
        return {
            "success": True,
            "experiment": result.to_dict(),
            "message": f"Completed {result.completed_paths} simulation paths"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# Get Results
# ===========================================

@router.get("/experiments/{experiment_id}/results", summary="Get Monte Carlo Results")
async def get_results(
    experiment_id: str,
    reference_capital: float = Query(100000.0, ge=1000)
):
    """
    Get complete Monte Carlo analysis results.
    
    Includes: distribution, tail risk, and scenarios.
    """
    experiment = mc_simulation_engine.get_experiment(experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    
    if experiment.status != ExperimentStatus.COMPLETED:
        return {
            "success": False,
            "message": f"Experiment not completed. Status: {experiment.status.value}",
            "experiment": experiment.to_dict()
        }
    
    analysis = mc_distribution_analyzer.analyze(experiment_id, reference_capital)
    
    return {
        "experiment": experiment.to_dict(),
        **analysis
    }


# ===========================================
# Distribution
# ===========================================

@router.get("/experiments/{experiment_id}/distribution", summary="Get Return Distribution")
async def get_distribution(experiment_id: str):
    """Get return distribution from Monte Carlo simulation"""
    distribution = mc_distribution_analyzer.calculate_distribution(experiment_id)
    
    if not distribution:
        raise HTTPException(status_code=404, detail=f"No results for experiment {experiment_id}")
    
    return distribution.to_dict()


# ===========================================
# Tail Risk
# ===========================================

@router.get("/experiments/{experiment_id}/tail-risk", summary="Get Tail Risk Metrics")
async def get_tail_risk(
    experiment_id: str,
    reference_capital: float = Query(100000.0, ge=1000)
):
    """
    Get tail risk metrics: VaR, CVaR, probability of ruin.
    
    VaR 95% = Maximum loss at 95% confidence
    CVaR 95% = Expected loss in worst 5% of cases
    """
    tail_risk = mc_distribution_analyzer.calculate_tail_risk(experiment_id, reference_capital)
    
    if not tail_risk:
        raise HTTPException(status_code=404, detail=f"No results for experiment {experiment_id}")
    
    return tail_risk.to_dict()


# ===========================================
# Scenarios
# ===========================================

@router.get("/experiments/{experiment_id}/scenarios", summary="Get Scenario Summary")
async def get_scenarios(experiment_id: str):
    """Get scenario classification: best, median, worst cases"""
    scenarios = mc_distribution_analyzer.classify_scenarios(experiment_id)
    
    if not scenarios:
        raise HTTPException(status_code=404, detail=f"No results for experiment {experiment_id}")
    
    return scenarios.to_dict()


# ===========================================
# Paths
# ===========================================

@router.get("/experiments/{experiment_id}/paths", summary="Get Simulation Paths")
async def get_paths(
    experiment_id: str,
    limit: int = Query(100, ge=1, le=1000),
    sort_by: str = Query("return", description="Sort by: return, drawdown, sharpe")
):
    """Get individual simulation paths"""
    paths = mc_simulation_engine.get_paths(experiment_id, limit=1000)
    
    if not paths:
        raise HTTPException(status_code=404, detail=f"No paths for experiment {experiment_id}")
    
    # Sort
    if sort_by == "return":
        paths = sorted(paths, key=lambda p: p.total_return_pct, reverse=True)
    elif sort_by == "drawdown":
        paths = sorted(paths, key=lambda p: p.max_drawdown_pct, reverse=True)
    elif sort_by == "sharpe":
        paths = sorted(paths, key=lambda p: p.sharpe_ratio, reverse=True)
    
    paths = paths[:limit]
    
    return {
        "paths": [p.to_dict() for p in paths],
        "count": len(paths)
    }


# ===========================================
# Get Specific Path
# ===========================================

@router.get("/experiments/{experiment_id}/paths/{path_id}", summary="Get Specific Path")
async def get_path(experiment_id: str, path_id: str):
    """Get a specific simulation path with full details"""
    paths = mc_simulation_engine.get_paths(experiment_id, limit=10000)
    
    for path in paths:
        if path.path_id == path_id:
            return path.to_dict()
    
    raise HTTPException(status_code=404, detail=f"Path {path_id} not found")


# ===========================================
# Percentile Path
# ===========================================

@router.get("/experiments/{experiment_id}/percentile/{percentile}", summary="Get Path at Percentile")
async def get_percentile_path(
    experiment_id: str,
    percentile: float
):
    """Get representative path at specific percentile (0-100)"""
    if percentile < 0 or percentile > 100:
        raise HTTPException(status_code=400, detail="Percentile must be between 0 and 100")
    
    path = mc_distribution_analyzer.get_path_by_percentile(experiment_id, percentile)
    
    if not path:
        raise HTTPException(status_code=404, detail=f"No path found for experiment {experiment_id}")
    
    return {
        "percentile": percentile,
        "path": path.to_dict()
    }


# ===========================================
# Delete Experiment
# ===========================================

@router.delete("/experiments/{experiment_id}", summary="Delete Experiment")
async def delete_experiment(experiment_id: str):
    """Delete a Monte Carlo experiment and all paths"""
    from .mc_simulation_engine import mc_repository
    
    experiment = mc_simulation_engine.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    
    mc_repository.delete_experiment(experiment_id)
    
    return {
        "success": True,
        "message": f"Experiment {experiment_id} deleted"
    }


# ===========================================
# Health
# ===========================================

@router.get("/health", summary="Monte Carlo Module Health")
async def health():
    """Health check for Monte Carlo module"""
    engine_health = mc_simulation_engine.get_health()
    
    return {
        "module": "Monte Carlo Stress Engine",
        "phase": "S5",
        "status": "healthy",
        "services": {
            "engine": engine_health
        },
        "endpoints": {
            "create": "POST /api/montecarlo/experiments",
            "list": "GET /api/montecarlo/experiments",
            "run": "POST /api/montecarlo/experiments/{id}/run",
            "results": "GET /api/montecarlo/experiments/{id}/results",
            "distribution": "GET /api/montecarlo/experiments/{id}/distribution",
            "tail_risk": "GET /api/montecarlo/experiments/{id}/tail-risk",
            "scenarios": "GET /api/montecarlo/experiments/{id}/scenarios",
            "paths": "GET /api/montecarlo/experiments/{id}/paths"
        },
        "generator_types": [t.value for t in PathGeneratorType]
    }
