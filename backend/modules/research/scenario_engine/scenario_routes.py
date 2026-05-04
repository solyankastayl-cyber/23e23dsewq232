"""
PHASE 6.2 - Scenario Engine Routes
===================================
REST API endpoints for Scenario Engine.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from .scenario_types import (
    ScenarioType, ScenarioSeverity, ScenarioStatus, ScenarioVerdict
)
from .scenario_registry import get_scenario_registry
from .scenario_builder import ScenarioBuilder
from .scenario_runner import ScenarioRunner
from .scenario_evaluator import ScenarioEvaluator
from .scenario_repository import ScenarioRepository

router = APIRouter(prefix="/api/scenario", tags=["Scenario Engine"])

# Initialize components
_repository: Optional[ScenarioRepository] = None
_runner: Optional[ScenarioRunner] = None
_evaluator: Optional[ScenarioEvaluator] = None


def get_repository() -> ScenarioRepository:
    global _repository
    if _repository is None:
        _repository = ScenarioRepository()
    return _repository


def get_runner() -> ScenarioRunner:
    global _runner
    if _runner is None:
        repo = get_repository()
        _runner = ScenarioRunner(db=repo.db)
    return _runner


def get_evaluator() -> ScenarioEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = ScenarioEvaluator()
    return _evaluator


# ==================== Request/Response Models ====================

class ShockParametersInput(BaseModel):
    price_change_pct: float = 0.0
    price_volatility_multiplier: float = 1.0
    liquidity_reduction_pct: float = 0.0
    spread_multiplier: float = 1.0
    volume_spike_multiplier: float = 1.0
    shock_duration_candles: int = 10
    recovery_candles: int = 20
    slippage_multiplier: float = 1.0
    fee_multiplier: float = 1.0
    latency_ms: int = 0


class ScenarioCreateRequest(BaseModel):
    name: str
    description: str
    scenario_type: str
    shock_parameters: ShockParametersInput
    severity: str = "MEDIUM"
    duration_candles: int = 50
    applicable_symbols: List[str] = ["BTC", "ETH", "SOL"]
    applicable_timeframes: List[str] = ["1h", "4h", "1d"]
    tags: List[str] = []
    author: str = "user"


class ScenarioRunRequest(BaseModel):
    symbol: str = "BTC"
    timeframe: str = "1d"
    strategies: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


# ==================== Health & Status ====================

@router.get("/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "module": "scenario_engine",
        "version": "phase6.2",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ==================== Rankings (before /{scenario_id}) ====================

@router.get("/top")
async def get_top_scenarios(limit: int = 10):
    """Get scenarios with best results"""
    repo = get_repository()
    results = repo.get_top_scenarios(limit)
    
    return {
        "count": len(results),
        "top_scenarios": results
    }


@router.get("/weak")
async def get_weak_scenarios(limit: int = 10):
    """Get scenarios with worst results"""
    repo = get_repository()
    results = repo.get_weak_scenarios(limit)
    
    return {
        "count": len(results),
        "weak_scenarios": results
    }


@router.get("/stats/overview")
async def get_stats():
    """Get overall statistics"""
    repo = get_repository()
    registry = get_scenario_registry()
    
    db_stats = repo.get_statistics()
    registry_stats = registry.get_stats()
    
    return {
        "database": db_stats,
        "registry": registry_stats,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/registry")
async def get_registry_info():
    """Get scenario registry information"""
    registry = get_scenario_registry()
    
    scenarios = registry.get_all()
    stats = registry.get_stats()
    
    return {
        "total": len(scenarios),
        "stats": stats,
        "types": [t.value for t in ScenarioType],
        "severities": [s.value for s in ScenarioSeverity],
        "verdicts": [v.value for v in ScenarioVerdict],
        "scenarios": [
            {
                "id": s.scenario_id,
                "name": s.name,
                "type": s.scenario_type.value if hasattr(s.scenario_type, 'value') else s.scenario_type,
                "severity": s.severity.value if hasattr(s.severity, 'value') else s.severity
            }
            for s in scenarios
        ]
    }


# ==================== Scenario CRUD ====================

@router.post("/create")
async def create_scenario(request: ScenarioCreateRequest):
    """Create a new scenario"""
    try:
        builder = ScenarioBuilder()
        builder.with_name(request.name)
        builder.with_description(request.description)
        builder.with_type(ScenarioType(request.scenario_type))
        builder.with_severity(ScenarioSeverity(request.severity))
        builder.with_duration(request.duration_candles)
        
        sp = request.shock_parameters
        builder.with_shock_parameters(
            price_change_pct=sp.price_change_pct,
            price_volatility_multiplier=sp.price_volatility_multiplier,
            liquidity_reduction_pct=sp.liquidity_reduction_pct,
            spread_multiplier=sp.spread_multiplier,
            volume_spike_multiplier=sp.volume_spike_multiplier,
            shock_duration_candles=sp.shock_duration_candles,
            recovery_candles=sp.recovery_candles,
            slippage_multiplier=sp.slippage_multiplier,
            fee_multiplier=sp.fee_multiplier,
            latency_ms=sp.latency_ms
        )
        
        builder.with_applicable_symbols(request.applicable_symbols)
        builder.with_applicable_timeframes(request.applicable_timeframes)
        builder.with_tags(request.tags)
        builder.with_author(request.author)
        
        scenario = builder.build()
        
        # Save to repository
        repo = get_repository()
        success = repo.save_scenario(scenario)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save scenario")
        
        # Add to registry
        registry = get_scenario_registry()
        registry.add(scenario)
        
        return {
            "success": True,
            "scenario_id": scenario.scenario_id,
            "message": "Scenario created successfully",
            "scenario": scenario.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_scenarios(
    scenario_type: Optional[str] = None,
    severity: Optional[str] = None
):
    """List all scenarios"""
    registry = get_scenario_registry()
    
    if scenario_type:
        scenarios = registry.get_by_type(ScenarioType(scenario_type))
    elif severity:
        scenarios = registry.get_by_severity(ScenarioSeverity(severity))
    else:
        scenarios = registry.get_all()
    
    return {
        "count": len(scenarios),
        "scenarios": [s.to_dict() for s in scenarios]
    }


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str):
    """Get scenario by ID"""
    registry = get_scenario_registry()
    scenario = registry.get(scenario_id)
    
    if not scenario:
        # Try repository
        repo = get_repository()
        data = repo.get_scenario(scenario_id)
        if data:
            return {"scenario": data}
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return {"scenario": scenario.to_dict()}


@router.delete("/{scenario_id}")
async def delete_scenario(scenario_id: str):
    """Delete scenario"""
    registry = get_scenario_registry()
    repo = get_repository()
    
    registry.delete(scenario_id)
    repo.delete_scenario(scenario_id)
    
    return {"success": True, "message": f"Scenario {scenario_id} deleted"}


# ==================== Run Scenario ====================

@router.post("/run")
async def run_scenario(scenario_id: str, request: ScenarioRunRequest):
    """Run scenario stress test"""
    registry = get_scenario_registry()
    scenario = registry.get(scenario_id)
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    runner = get_runner()
    evaluator = get_evaluator()
    repo = get_repository()
    
    # Parse dates
    start_date = None
    end_date = None
    if request.start_date:
        start_date = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
    if request.end_date:
        end_date = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))
    
    # Run scenario
    run, strategy_results = await runner.run_scenario(
        scenario=scenario,
        symbol=request.symbol,
        timeframe=request.timeframe,
        strategies=request.strategies,
        start_date=start_date,
        end_date=end_date
    )
    
    # Save run
    repo.save_run(run)
    
    # Evaluate results
    result = evaluator.evaluate(scenario_id, run, strategy_results)
    
    # Save result
    repo.save_result(result)
    
    return {
        "success": True,
        "run": run.to_dict(),
        "result": result.to_dict()
    }


# ==================== Results ====================

@router.get("/{scenario_id}/results")
async def get_results(scenario_id: str, limit: int = 10):
    """Get results for scenario"""
    repo = get_repository()
    results = repo.get_results_for_scenario(scenario_id, limit)
    
    return {
        "scenario_id": scenario_id,
        "count": len(results),
        "results": results
    }


@router.get("/{scenario_id}/history")
async def get_history(scenario_id: str, limit: int = 10):
    """Get run history for scenario"""
    repo = get_repository()
    runs = repo.get_runs_for_scenario(scenario_id, limit)
    
    return {
        "scenario_id": scenario_id,
        "count": len(runs),
        "runs": runs
    }


# ==================== Batch Operations ====================

@router.post("/run-batch")
async def run_batch(
    scenario_ids: List[str],
    symbol: str = "BTC",
    timeframe: str = "1d"
):
    """Run multiple scenarios in batch"""
    registry = get_scenario_registry()
    runner = get_runner()
    evaluator = get_evaluator()
    repo = get_repository()
    
    results = []
    
    for s_id in scenario_ids:
        scenario = registry.get(s_id)
        if not scenario:
            results.append({
                "scenario_id": s_id,
                "success": False,
                "error": "Scenario not found"
            })
            continue
        
        try:
            run, strategy_results = await runner.run_scenario(
                scenario=scenario,
                symbol=symbol,
                timeframe=timeframe
            )
            
            repo.save_run(run)
            
            result = evaluator.evaluate(s_id, run, strategy_results)
            repo.save_result(result)
            
            results.append({
                "scenario_id": s_id,
                "success": True,
                "verdict": result.verdict.value if hasattr(result.verdict, 'value') else result.verdict,
                "stability_score": result.system_stability_score,
                "strategies_survived": result.strategies_survived,
                "total_strategies": result.total_strategies
            })
        except Exception as e:
            results.append({
                "scenario_id": s_id,
                "success": False,
                "error": str(e)
            })
    
    # Summary
    successful = [r for r in results if r.get('success')]
    
    return {
        "batch_size": len(scenario_ids),
        "successful": len(successful),
        "failed": len(scenario_ids) - len(successful),
        "results": results
    }


@router.post("/run-all")
async def run_all_scenarios(
    symbol: str = "BTC",
    timeframe: str = "1d"
):
    """Run all active scenarios"""
    registry = get_scenario_registry()
    scenarios = registry.get_active()
    
    scenario_ids = [s.scenario_id for s in scenarios]
    
    return await run_batch(scenario_ids, symbol, timeframe)


# ==================== Analysis ====================

@router.get("/analysis/strategy-ranking")
async def get_strategy_ranking():
    """Get strategy ranking across all scenarios"""
    repo = get_repository()
    evaluator = get_evaluator()
    
    # Get all results
    all_results = []
    for doc in repo.db.scenario_results.find({}, {"_id": 0}):
        # Convert to ScenarioResult
        from .scenario_types import ScenarioResult, StrategyScenarioResult
        
        strategy_results = [
            StrategyScenarioResult(**sr) for sr in doc.get("strategy_results", [])
        ]
        
        result = ScenarioResult(
            scenario_id=doc["scenario_id"],
            run_id=doc["run_id"],
            strategy_results=strategy_results,
            total_strategies=doc.get("total_strategies", 0),
            strategies_survived=doc.get("strategies_survived", 0),
            avg_max_drawdown=doc.get("avg_max_drawdown", 0),
            avg_recovery_time=doc.get("avg_recovery_time", 0),
            total_risk_breaches=doc.get("total_risk_breaches", 0),
            system_stability_score=doc.get("system_stability_score", 0),
            verdict=ScenarioVerdict(doc.get("verdict", "WEAK"))
        )
        all_results.append(result)
    
    if not all_results:
        return {"message": "No results available for ranking"}
    
    ranking = evaluator.get_strategy_ranking(all_results)
    return ranking
