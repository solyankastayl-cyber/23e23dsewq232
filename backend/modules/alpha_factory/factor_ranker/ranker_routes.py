"""
PHASE 13.4 - Factor Ranker Routes
==================================
API endpoints for Factor Ranker.

Endpoints:
- GET  /api/factor-ranker/health
- POST /api/factor-ranker/run
- POST /api/factor-ranker/evaluate/{factor_id}
- GET  /api/factor-ranker/rankings
- GET  /api/factor-ranker/top
- GET  /api/factor-ranker/approved
- GET  /api/factor-ranker/stats
- GET  /api/factor-ranker/runs
- GET  /api/factor-ranker/{factor_id}
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .factor_ranker import get_factor_ranker, FactorRanker
from .ranker_repository import RankerRepository


router = APIRouter(prefix="/api/factor-ranker", tags=["Factor Ranker"])


# ===== Pydantic Models =====

class RankingRunRequest(BaseModel):
    max_approved: int = Field(default=200, ge=50, le=500)
    clear_existing: bool = True
    seed: Optional[int] = 42


# ===== Singletons =====

_ranker: Optional[FactorRanker] = None
_repository: Optional[RankerRepository] = None


def get_ranker() -> FactorRanker:
    global _ranker
    if _ranker is None:
        _ranker = get_factor_ranker()
    return _ranker


def get_repository() -> RankerRepository:
    global _repository
    if _repository is None:
        _repository = RankerRepository()
    return _repository


# ===== Health & Stats =====

@router.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "module": "factor_ranker",
        "version": "phase13.4_factor_ranker",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/stats")
async def get_stats():
    """Get Factor Ranker statistics."""
    ranker = get_ranker()
    repo = get_repository()
    
    return {
        "ranker": ranker.get_stats(),
        "repository": repo.get_stats(),
        "computed_at": datetime.now(timezone.utc).isoformat()
    }


# ===== Ranking =====

@router.post("/run")
async def run_ranking(request: RankingRunRequest = None):
    """
    Run factor ranking.
    
    Evaluates all candidate factors and generates approved list.
    """
    request = request or RankingRunRequest()
    
    ranker = get_ranker()
    
    run = ranker.run_ranking(
        factors=None,  # Load from generator
        max_approved=request.max_approved,
        clear_existing=request.clear_existing,
        seed=request.seed
    )
    
    return {
        "status": "completed" if run.status == "completed" else "failed",
        "run": run.to_dict()
    }


@router.post("/evaluate/{factor_id}")
async def evaluate_factor(factor_id: str):
    """
    Evaluate a single factor.
    """
    ranker = get_ranker()
    result = ranker.evaluate_single(factor_id)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Factor '{factor_id}' not found")
    
    return {
        "factor_id": factor_id,
        "metrics": result.to_dict()
    }


# ===== Rankings =====

@router.get("/rankings")
async def get_rankings(
    verdict: Optional[str] = Query(None, description="Filter by verdict"),
    approved_only: bool = Query(False, description="Only approved factors"),
    limit: int = Query(100, ge=1, le=500)
):
    """Get factor rankings."""
    ranker = get_ranker()
    rankings = ranker.get_rankings(
        verdict=verdict,
        approved_only=approved_only,
        limit=limit
    )
    
    return {
        "count": len(rankings),
        "rankings": rankings,
        "filters": {
            "verdict": verdict,
            "approved_only": approved_only
        }
    }


@router.get("/top")
async def get_top_factors(
    n: int = Query(20, ge=1, le=100, description="Number of top factors")
):
    """Get top N factors by composite score."""
    ranker = get_ranker()
    top = ranker.get_top_factors(n)
    
    return {
        "count": len(top),
        "top_factors": top
    }


@router.get("/approved")
async def get_approved_factors():
    """Get all approved factors."""
    ranker = get_ranker()
    approved = ranker.get_approved_factors()
    
    return {
        "count": len(approved),
        "approved_factors": approved
    }


@router.get("/verdicts")
async def get_verdicts():
    """Get verdict breakdown."""
    repo = get_repository()
    verdict_counts = repo.count_by_verdict()
    
    return {
        "verdicts": ["ELITE", "STRONG", "PROMISING", "WEAK", "REJECTED"],
        "counts": verdict_counts,
        "total": sum(verdict_counts.values())
    }


@router.get("/runs")
async def get_runs(limit: int = Query(10, ge=1, le=50)):
    """Get recent ranking runs."""
    repo = get_repository()
    runs = repo.get_runs(limit=limit)
    
    return {
        "count": len(runs),
        "runs": runs
    }


@router.get("/{factor_id}")
async def get_factor_ranking(factor_id: str):
    """Get ranking for a specific factor."""
    repo = get_repository()
    ranking = repo.get_ranking(factor_id)
    
    if not ranking:
        raise HTTPException(status_code=404, detail=f"Ranking for '{factor_id}' not found")
    
    return {
        "factor_id": factor_id,
        "ranking": ranking
    }


@router.delete("/rankings")
async def clear_rankings():
    """Clear all rankings."""
    repo = get_repository()
    deleted = repo.clear_rankings()
    
    return {
        "deleted": deleted,
        "message": f"Cleared {deleted} rankings"
    }
