"""
PHASE 17.2 — Factor Governance Routes
======================================
API endpoints for Factor Governance Engine.

Endpoints:
- GET /api/v1/research-control/factor-governance/health
- GET /api/v1/research-control/factor-governance/config
- GET /api/v1/research-control/factor-governance/factors/list
- POST /api/v1/research-control/factor-governance/batch
- GET /api/v1/research-control/factor-governance/summary/{factor}
- GET /api/v1/research-control/factor-governance/{factor}
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from modules.research_control.factor_governance.factor_governance_engine import (
    get_factor_governance_engine,
)
from modules.research_control.factor_governance.factor_governance_types import (
    FACTOR_GOVERNANCE_WEIGHTS,
    FACTOR_GOVERNANCE_THRESHOLDS,
    FACTOR_GOVERNANCE_MODIFIERS,
    FactorGovernanceState,
)

router = APIRouter(
    prefix="/api/v1/research-control/factor-governance",
    tags=["Factor Governance"]
)


# ══════════════════════════════════════════════════════════════
# REQUEST MODELS
# ══════════════════════════════════════════════════════════════

class FactorBatchRequest(BaseModel):
    factors: List[str]


# ══════════════════════════════════════════════════════════════
# STATIC ROUTES (must be before dynamic routes)
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def factor_governance_health():
    """Factor Governance Engine health check."""
    try:
        engine = get_factor_governance_engine()
        
        # Quick test evaluation
        test_result = engine.evaluate("trend_breakout_factor")
        
        return {
            "status": "healthy",
            "phase": "17.2",
            "module": "Factor Governance Engine",
            "description": "Second layer of Research Control Fabric - Alpha Factor Governance",
            "dimensions": list(FACTOR_GOVERNANCE_WEIGHTS.keys()),
            "weights": FACTOR_GOVERNANCE_WEIGHTS,
            "states": [s.value for s in FactorGovernanceState],
            "thresholds": FACTOR_GOVERNANCE_THRESHOLDS,
            "test_result": {
                "factor": "trend_breakout_factor",
                "governance_score": round(test_result.governance_score, 4),
                "governance_state": test_result.governance_state.value,
                "capital_modifier": round(test_result.capital_modifier, 4),
                "weakest_dimension": test_result.weakest_dimension.value,
            },
            "known_factors_count": len(engine.get_all_known_factors()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/config")
async def get_config():
    """Get factor governance configuration."""
    return {
        "status": "ok",
        "weights": FACTOR_GOVERNANCE_WEIGHTS,
        "thresholds": FACTOR_GOVERNANCE_THRESHOLDS,
        "modifiers": {
            state.value: {
                "capital_modifier": mods["capital_modifier"],
                "confidence_modifier": mods["confidence_modifier"],
            }
            for state, mods in FACTOR_GOVERNANCE_MODIFIERS.items()
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/factors/list")
async def list_factors():
    """List all known factors that can be evaluated."""
    try:
        engine = get_factor_governance_engine()
        factors = engine.get_all_known_factors()
        
        return {
            "status": "ok",
            "factors": factors,
            "count": len(factors),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# BATCH ENDPOINT
# ══════════════════════════════════════════════════════════════

@router.post("/batch")
async def batch_evaluate(request: FactorBatchRequest):
    """Batch factor governance evaluation."""
    try:
        engine = get_factor_governance_engine()
        results = {}
        
        summary = {
            "total": len(request.factors),
            "elite": 0,
            "stable": 0,
            "watchlist": 0,
            "degraded": 0,
            "retire": 0,
        }
        
        for factor in request.factors:
            try:
                result = engine.evaluate(factor)
                results[factor] = result.to_summary()
                
                # Update summary counts
                state = result.governance_state.value.lower()
                if state in summary:
                    summary[state] += 1
            except Exception as e:
                results[factor] = {
                    "error": str(e),
                    "governance_state": "UNKNOWN",
                }
        
        return {
            "status": "ok",
            "results": results,
            "summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# DYNAMIC ROUTES (must be after static routes)
# ══════════════════════════════════════════════════════════════

@router.get("/summary/{factor}")
async def factor_summary(factor: str):
    """Compact factor governance summary."""
    try:
        engine = get_factor_governance_engine()
        result = engine.evaluate(factor)
        
        return {
            "status": "ok",
            **result.to_summary(),
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{factor}")
async def evaluate_factor(factor: str):
    """
    Full governance evaluation for a factor.
    
    Returns detailed assessment across all 5 dimensions:
    - performance_score
    - regime_score
    - capacity_score
    - crowding_score
    - decay_score
    
    Plus aggregated:
    - governance_score (0-1)
    - governance_state (ELITE/STABLE/WATCHLIST/DEGRADED/RETIRE)
    - capital_modifier (affects capital allocation!)
    - confidence_modifier
    """
    try:
        engine = get_factor_governance_engine()
        result = engine.evaluate(factor)
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
