"""
PHASE 6.1 - Hypothesis Engine Routes
=====================================
REST API endpoints for Hypothesis Engine.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from .hypothesis_types import HypothesisStatus, HypothesisCategory, HypothesisVerdict
from .hypothesis_registry import get_hypothesis_registry
from .hypothesis_builder import HypothesisBuilder
from .hypothesis_runner import HypothesisRunner
from .hypothesis_evaluator import HypothesisEvaluator
from .hypothesis_repository import HypothesisRepository

router = APIRouter(prefix="/api/hypothesis", tags=["Hypothesis Engine"])

# Initialize components
_repository: Optional[HypothesisRepository] = None
_runner: Optional[HypothesisRunner] = None
_evaluator: Optional[HypothesisEvaluator] = None


def get_repository() -> HypothesisRepository:
    global _repository
    if _repository is None:
        _repository = HypothesisRepository()
    return _repository


def get_runner() -> HypothesisRunner:
    global _runner
    if _runner is None:
        repo = get_repository()
        _runner = HypothesisRunner(db=repo.db)
    return _runner


def get_evaluator() -> HypothesisEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = HypothesisEvaluator()
    return _evaluator


# ==================== Request/Response Models ====================

class ConditionInput(BaseModel):
    indicator: str
    operator: str
    value: Any
    description: Optional[str] = ""
    weight: float = 1.0


class ExpectedOutcomeInput(BaseModel):
    direction: str
    target_move_pct: float
    time_horizon_candles: int
    confidence: float = 0.5


class HypothesisCreateRequest(BaseModel):
    name: str
    description: str
    category: str
    conditions: List[ConditionInput]
    expected_outcome: ExpectedOutcomeInput
    applicable_regimes: List[str] = ["TREND_UP", "TREND_DOWN", "RANGE"]
    applicable_timeframes: List[str] = ["1h", "4h", "1d"]
    applicable_symbols: List[str] = ["BTC", "ETH", "SOL"]
    tags: List[str] = []
    author: str = "user"


class HypothesisRunRequest(BaseModel):
    symbol: str = "BTC"
    timeframe: str = "1d"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


# ==================== Health & Status ====================

@router.get("/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "module": "hypothesis_engine",
        "version": "phase6.1",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ==================== Hypothesis CRUD ====================

@router.post("/create")
async def create_hypothesis(request: HypothesisCreateRequest):
    """Create a new hypothesis"""
    try:
        builder = HypothesisBuilder()
        builder.with_name(request.name)
        builder.with_description(request.description)
        builder.with_category(HypothesisCategory(request.category))
        
        for cond in request.conditions:
            from .hypothesis_types import ConditionOperator
            builder.add_condition(
                indicator=cond.indicator,
                operator=ConditionOperator(cond.operator),
                value=cond.value,
                description=cond.description or "",
                weight=cond.weight
            )
        
        builder.with_expected_outcome(
            direction=request.expected_outcome.direction,
            target_move_pct=request.expected_outcome.target_move_pct,
            time_horizon_candles=request.expected_outcome.time_horizon_candles,
            confidence=request.expected_outcome.confidence
        )
        
        builder.with_applicable_regimes(request.applicable_regimes)
        builder.with_applicable_timeframes(request.applicable_timeframes)
        builder.with_applicable_symbols(request.applicable_symbols)
        builder.with_tags(request.tags)
        builder.with_author(request.author)
        
        hypothesis = builder.build()
        
        # Save to repository
        repo = get_repository()
        success = repo.save_hypothesis(hypothesis)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save hypothesis")
        
        # Add to registry
        registry = get_hypothesis_registry()
        registry.add(hypothesis)
        
        return {
            "success": True,
            "hypothesis_id": hypothesis.hypothesis_id,
            "message": "Hypothesis created successfully",
            "hypothesis": hypothesis.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_hypotheses(
    status: Optional[str] = None,
    category: Optional[str] = None
):
    """List all hypotheses"""
    registry = get_hypothesis_registry()
    
    if status:
        hypotheses = registry.get_by_status(HypothesisStatus(status))
    elif category:
        hypotheses = registry.get_by_category(HypothesisCategory(category))
    else:
        hypotheses = registry.get_all()
    
    return {
        "count": len(hypotheses),
        "hypotheses": [h.to_dict() for h in hypotheses]
    }


# ==================== Rankings (before /{hypothesis_id}) ====================

@router.get("/top")
async def get_top_hypotheses(limit: int = 10):
    """Get top performing hypotheses"""
    repo = get_repository()
    results = repo.get_top_hypotheses(limit)
    
    return {
        "count": len(results),
        "top_hypotheses": results
    }


@router.get("/weak")
async def get_weak_hypotheses(limit: int = 10):
    """Get weak performing hypotheses"""
    repo = get_repository()
    results = repo.get_weak_hypotheses(limit)
    
    return {
        "count": len(results),
        "weak_hypotheses": results
    }


@router.get("/stats/overview")
async def get_stats():
    """Get overall statistics"""
    repo = get_repository()
    registry = get_hypothesis_registry()
    
    db_stats = repo.get_statistics()
    registry_stats = registry.get_stats()
    
    return {
        "database": db_stats,
        "registry": registry_stats,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/registry")
async def get_registry_info():
    """Get hypothesis registry information"""
    registry = get_hypothesis_registry()
    
    hypotheses = registry.get_all()
    stats = registry.get_stats()
    
    return {
        "total": len(hypotheses),
        "stats": stats,
        "categories": [c.value for c in HypothesisCategory],
        "statuses": [s.value for s in HypothesisStatus],
        "verdicts": [v.value for v in HypothesisVerdict],
        "hypotheses": [
            {
                "id": h.hypothesis_id,
                "name": h.name,
                "category": h.category.value if hasattr(h.category, 'value') else h.category,
                "status": h.status.value if hasattr(h.status, 'value') else h.status
            }
            for h in hypotheses
        ]
    }


@router.get("/{hypothesis_id}")
async def get_hypothesis(hypothesis_id: str):
    """Get hypothesis by ID"""
    registry = get_hypothesis_registry()
    hypothesis = registry.get(hypothesis_id)
    
    if not hypothesis:
        # Try repository
        repo = get_repository()
        data = repo.get_hypothesis(hypothesis_id)
        if data:
            return {"hypothesis": data}
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    
    return {"hypothesis": hypothesis.to_dict()}


@router.delete("/{hypothesis_id}")
async def delete_hypothesis(hypothesis_id: str):
    """Delete hypothesis"""
    registry = get_hypothesis_registry()
    repo = get_repository()
    
    registry.delete(hypothesis_id)
    repo.delete_hypothesis(hypothesis_id)
    
    return {"success": True, "message": f"Hypothesis {hypothesis_id} deleted"}


@router.patch("/{hypothesis_id}/status")
async def update_status(hypothesis_id: str, status: str):
    """Update hypothesis status"""
    registry = get_hypothesis_registry()
    repo = get_repository()
    
    try:
        new_status = HypothesisStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    registry.update_status(hypothesis_id, new_status)
    repo.update_hypothesis_status(hypothesis_id, status)
    
    return {"success": True, "hypothesis_id": hypothesis_id, "status": status}


# ==================== Run Hypothesis ====================

@router.post("/run")
async def run_hypothesis(hypothesis_id: str, request: HypothesisRunRequest):
    """Run hypothesis test"""
    registry = get_hypothesis_registry()
    hypothesis = registry.get(hypothesis_id)
    
    if not hypothesis:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    
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
    
    # Run hypothesis
    run, triggers = await runner.run_hypothesis(
        hypothesis=hypothesis,
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_date=start_date,
        end_date=end_date
    )
    
    # Save run
    repo.save_run(run)
    
    # Evaluate results
    result = evaluator.evaluate(hypothesis_id, run, triggers)
    
    # Save result
    repo.save_result(result)
    
    return {
        "success": True,
        "run": run.to_dict(),
        "result": result.to_dict(),
        "triggers_sample": triggers[:10] if triggers else []  # Sample of triggers
    }


# ==================== Results ====================

@router.get("/{hypothesis_id}/results")
async def get_results(hypothesis_id: str, limit: int = 10):
    """Get results for hypothesis"""
    repo = get_repository()
    results = repo.get_results_for_hypothesis(hypothesis_id, limit)
    
    return {
        "hypothesis_id": hypothesis_id,
        "count": len(results),
        "results": results
    }


@router.get("/{hypothesis_id}/history")
async def get_history(hypothesis_id: str, limit: int = 10):
    """Get run history for hypothesis"""
    repo = get_repository()
    runs = repo.get_runs_for_hypothesis(hypothesis_id, limit)
    
    return {
        "hypothesis_id": hypothesis_id,
        "count": len(runs),
        "runs": runs
    }




# ==================== Batch Operations ====================

@router.post("/run-batch")
async def run_batch(
    hypothesis_ids: List[str],
    symbol: str = "BTC",
    timeframe: str = "1d"
):
    """Run multiple hypotheses in batch"""
    registry = get_hypothesis_registry()
    runner = get_runner()
    evaluator = get_evaluator()
    repo = get_repository()
    
    results = []
    
    for h_id in hypothesis_ids:
        hypothesis = registry.get(h_id)
        if not hypothesis:
            results.append({
                "hypothesis_id": h_id,
                "success": False,
                "error": "Hypothesis not found"
            })
            continue
        
        try:
            run, triggers = await runner.run_hypothesis(
                hypothesis=hypothesis,
                symbol=symbol,
                timeframe=timeframe
            )
            
            repo.save_run(run)
            
            result = evaluator.evaluate(h_id, run, triggers)
            repo.save_result(result)
            
            results.append({
                "hypothesis_id": h_id,
                "success": True,
                "verdict": result.verdict.value,
                "win_rate": result.win_rate,
                "profit_factor": result.profit_factor,
                "sample_size": result.sample_size
            })
        except Exception as e:
            results.append({
                "hypothesis_id": h_id,
                "success": False,
                "error": str(e)
            })
    
    # Compare results
    successful_results = [r for r in results if r.get('success')]
    
    return {
        "batch_size": len(hypothesis_ids),
        "successful": len(successful_results),
        "failed": len(hypothesis_ids) - len(successful_results),
        "results": results
    }
