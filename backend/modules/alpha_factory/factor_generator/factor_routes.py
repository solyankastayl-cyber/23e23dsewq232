"""
PHASE 13.3 - Factor Routes
===========================
API endpoints for Factor Generator.

Endpoints:
- GET  /api/factor-generator/health
- POST /api/factor-generator/run
- POST /api/factor-generator/generate-batch
- GET  /api/factor-generator/factors
- GET  /api/factor-generator/families
- GET  /api/factor-generator/stats
- GET  /api/factor-generator/{factor_id}
- GET  /api/factor-generator/runs
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from .factor_generator import get_factor_generator, FactorGenerator
from .factor_repository import FactorRepository
from .factor_types import FactorFamily, FactorTemplate

# Import Feature Registry to get features
try:
    from modules.alpha_factory.feature_library import get_feature_registry
    FEATURE_REGISTRY_OK = True
except ImportError:
    FEATURE_REGISTRY_OK = False
    get_feature_registry = None


router = APIRouter(prefix="/api/factor-generator", tags=["Factor Generator"])


# ===== Pydantic Models =====

class GenerateBatchRequest(BaseModel):
    max_total: int = Field(default=1500, ge=100, le=5000)
    max_single: int = Field(default=50, ge=0, le=200)
    max_pair: int = Field(default=400, ge=0, le=1000)
    max_triple: int = Field(default=300, ge=0, le=500)
    max_ratio: int = Field(default=200, ge=0, le=500)
    max_diff: int = Field(default=150, ge=0, le=300)
    max_interaction: int = Field(default=200, ge=0, le=500)
    max_regime: int = Field(default=150, ge=0, le=300)
    clear_existing: bool = False


# ===== Singletons =====

_generator: Optional[FactorGenerator] = None
_repository: Optional[FactorRepository] = None


def get_generator() -> FactorGenerator:
    global _generator
    if _generator is None:
        _generator = get_factor_generator()
    return _generator


def get_repository() -> FactorRepository:
    global _repository
    if _repository is None:
        _repository = FactorRepository()
    return _repository


# ===== Health & Stats =====

@router.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "module": "factor_generator",
        "version": "phase13.3_factor_generator",
        "feature_registry_available": FEATURE_REGISTRY_OK,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/stats")
async def get_stats():
    """Get Factor Generator statistics."""
    generator = get_generator()
    repo = get_repository()
    
    return {
        "generator": generator.get_stats(),
        "repository": repo.get_stats(),
        "computed_at": datetime.now(timezone.utc).isoformat()
    }


# ===== Generation =====

@router.post("/run")
async def run_generation(request: GenerateBatchRequest = None):
    """
    Run factor generation.
    
    Generates factors from Feature Library using templates.
    """
    if not FEATURE_REGISTRY_OK:
        raise HTTPException(
            status_code=503,
            detail="Feature Registry not available"
        )
    
    request = request or GenerateBatchRequest()
    
    # Get features
    feature_registry = get_feature_registry()
    features = feature_registry.list_features(limit=500)
    feature_dicts = [f.to_dict() for f in features]
    
    if not feature_dicts:
        raise HTTPException(
            status_code=400,
            detail="No features available in Feature Library"
        )
    
    # Clear existing if requested
    repo = get_repository()
    if request.clear_existing:
        deleted = repo.clear_factors()
        print(f"[FactorGenerator] Cleared {deleted} existing factors")
    
    # Generate
    generator = get_generator()
    config = {
        "max_total": request.max_total,
        "max_single": request.max_single,
        "max_pair": request.max_pair,
        "max_triple": request.max_triple,
        "max_ratio": request.max_ratio,
        "max_diff": request.max_diff,
        "max_interaction": request.max_interaction,
        "max_regime": request.max_regime,
    }
    
    run = generator.generate_batch(feature_dicts, config)
    
    return {
        "status": "completed",
        "run": run.to_dict(),
        "features_used": len(feature_dicts)
    }


@router.post("/generate-batch")
async def generate_batch(request: GenerateBatchRequest = None):
    """
    Alias for /run.
    """
    return await run_generation(request)


# ===== Factor CRUD =====

@router.get("/factors")
async def list_factors(
    family: Optional[str] = Query(None, description="Filter by family"),
    template: Optional[str] = Query(None, description="Filter by template"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000)
):
    """List generated factors."""
    repo = get_repository()
    factors = repo.list_factors(
        family=family,
        template=template,
        status=status,
        limit=limit
    )
    
    return {
        "count": len(factors),
        "factors": [f.to_dict() for f in factors],
        "filters": {
            "family": family,
            "template": template,
            "status": status
        }
    }


@router.get("/factors/search")
async def search_factors(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=200)
):
    """Search factors."""
    repo = get_repository()
    factors = repo.search_factors(q, limit=limit)
    
    return {
        "query": q,
        "count": len(factors),
        "factors": [f.to_dict() for f in factors]
    }


@router.get("/families")
async def get_families():
    """Get factor families with counts."""
    repo = get_repository()
    family_stats = repo.get_family_stats()
    
    return {
        "families": [f.value for f in FactorFamily],
        "counts": family_stats,
        "total": sum(family_stats.values())
    }


@router.get("/templates")
async def get_templates():
    """Get factor templates."""
    repo = get_repository()
    stats = repo.get_stats()
    
    return {
        "templates": [t.value for t in FactorTemplate],
        "counts": stats.get("template_counts", {})
    }


@router.get("/runs")
async def get_runs(limit: int = Query(10, ge=1, le=50)):
    """Get recent generation runs."""
    repo = get_repository()
    runs = repo.get_runs(limit=limit)
    
    return {
        "count": len(runs),
        "runs": runs
    }


@router.get("/{factor_id}")
async def get_factor(factor_id: str):
    """Get a specific factor."""
    repo = get_repository()
    factor = repo.get_factor(factor_id)
    
    if not factor:
        raise HTTPException(status_code=404, detail=f"Factor '{factor_id}' not found")
    
    return {
        "factor": factor.to_dict()
    }


@router.delete("/factors")
async def clear_factors():
    """Clear all factors (for regeneration)."""
    repo = get_repository()
    deleted = repo.clear_factors()
    
    return {
        "deleted": deleted,
        "message": f"Cleared {deleted} factors"
    }
