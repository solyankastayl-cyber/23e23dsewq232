"""
PHASE 26.5 & 26.6 — Alpha Factory Routes

API endpoints for Alpha Factory.

Endpoints:
- POST /api/v1/alpha-factory/run
- GET /api/v1/alpha-factory/status
- GET /api/v1/alpha-factory/active
- GET /api/v1/alpha-factory/summary
- GET /api/v1/alpha-factory/factors
- GET /api/v1/alpha-factory/history/{factor_id}
- GET /api/v1/alpha-factory/validation  (PHASE 26.6)
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from datetime import datetime, timezone

from .alpha_factory_engine import (
    AlphaFactoryEngine,
    get_alpha_factory_engine,
    AlphaFactoryResult,
    AlphaFactoryStatus,
)
from .alpha_registry import get_alpha_registry
from .alpha_validation_engine import (
    AlphaValidationEngine,
    get_alpha_validation_engine,
    AlphaValidationReport,
)


router = APIRouter(prefix="/api/v1/alpha-factory", tags=["alpha-factory"])


@router.post("/run", response_model=Dict[str, Any])
async def run_pipeline():
    """
    Run full alpha pipeline.
    
    Pipeline:
    Discovery → Scoring → Survival → Registry
    
    Returns pipeline result with statistics.
    """
    try:
        engine = get_alpha_factory_engine()
        result = await engine.run_alpha_pipeline()
        
        return {
            "status": "ok",
            "data": result.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline failed: {str(e)}"
        )


@router.get("/status", response_model=Dict[str, Any])
async def get_status():
    """
    Get alpha factory status.
    
    Returns:
    - pipeline_state: READY | RUNNING | ERROR
    - last_run timestamp
    - active/deprecated counts
    """
    engine = get_alpha_factory_engine()
    status = await engine.get_status()
    
    return {
        "pipeline_state": status.pipeline_state,
        "last_run": status.last_run.isoformat() if status.last_run else None,
        "active_factors": status.active_factors,
        "deprecated_factors": status.deprecated_factors,
        "total_factors": status.total_factors,
    }


@router.get("/active", response_model=Dict[str, Any])
async def get_active_factors():
    """
    Get all active alpha factors.
    
    Returns list of ACTIVE factors sorted by alpha_score.
    """
    engine = get_alpha_factory_engine()
    factors = await engine.get_active_factors()
    
    # Sort by alpha_score descending
    sorted_factors = sorted(
        factors,
        key=lambda f: f.alpha_score,
        reverse=True,
    )
    
    return {
        "active_factors": [
            {
                "name": f.name,
                "category": f.category,
                "alpha_score": f.alpha_score,
                "lookback": f.lookback,
            }
            for f in sorted_factors
        ],
        "count": len(sorted_factors),
    }


@router.get("/summary", response_model=Dict[str, Any])
async def get_summary():
    """
    Get alpha factory summary.
    
    Returns:
    - total_factors
    - active_factors
    - deprecated_factors
    - top_factor
    - average_alpha_score
    """
    engine = get_alpha_factory_engine()
    return await engine.get_summary()


@router.get("/factors", response_model=Dict[str, Any])
async def get_all_factors():
    """
    Get all factors from registry.
    """
    registry = get_alpha_registry()
    factors = await registry.get_all_factors()
    
    return {
        "factors": [
            {
                "factor_id": f.factor_id,
                "name": f.name,
                "category": f.category,
                "alpha_score": f.alpha_score,
                "status": f.status,
                "lookback": f.lookback,
            }
            for f in factors
        ],
        "count": len(factors),
    }


@router.get("/history/{factor_id}", response_model=Dict[str, Any])
async def get_factor_history(factor_id: str):
    """
    Get historical metrics for a factor.
    
    Shows how alpha_score evolved over time.
    """
    registry = get_alpha_registry()
    history = await registry.get_factor_history(factor_id)
    
    if not history:
        return {
            "factor_id": factor_id,
            "history": [],
            "count": 0,
        }
    
    return {
        "factor_id": factor_id,
        "history": [
            {
                "alpha_score": h.alpha_score,
                "sharpe_score": h.sharpe_score,
                "stability_score": h.stability_score,
                "drawdown_score": h.drawdown_score,
                "status": h.status,
                "recorded_at": h.recorded_at.isoformat(),
            }
            for h in history
        ],
        "count": len(history),
    }


@router.get("/top", response_model=Dict[str, Any])
async def get_top_factors(n: int = 10):
    """
    Get top N factors by alpha_score.
    """
    registry = get_alpha_registry()
    factors = await registry.get_top_factors(n)
    
    return {
        "top_factors": [
            {
                "name": f.name,
                "alpha_score": f.alpha_score,
                "status": f.status,
            }
            for f in factors
        ],
        "count": len(factors),
    }


# ============================================
# PHASE 26.6 — Validation Endpoint
# ============================================

@router.get("/validation", response_model=Dict[str, Any])
async def get_validation():
    """
    Run validation on alpha factory.
    
    Checks:
    - Alpha stability (drift ≤ 0.20)
    - Factor turnover (≤ 0.40)
    - Alpha distribution (mean ∈ [0.40, 0.70])
    - Category balance (no category > 60%)
    - Active factor limit (≤ 30)
    
    Returns AlphaValidationReport with validation_state: PASSED | WARNING | FAILED
    """
    try:
        # Use shared registry from factory engine
        registry = get_alpha_registry()
        engine = AlphaValidationEngine(registry=registry)
        report = await engine.validate()
        
        return {
            "stability_passed": report.stability_passed,
            "turnover_rate": report.turnover_rate,
            "alpha_drift_max": report.alpha_drift_max,
            "average_alpha_score": report.average_alpha_score,
            "alpha_score_min": report.alpha_score_min,
            "alpha_score_max": report.alpha_score_max,
            "active_factors": report.active_factors,
            "deprecated_factors": report.deprecated_factors,
            "total_factors": report.total_factors,
            "category_balance": report.category_balance,
            "category_balance_passed": report.category_balance_passed,
            "validation_state": report.validation_state,
            "warnings": report.warnings,
            "errors": report.errors,
            "validated_at": report.validated_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )
