"""
PHASE 17.1 — Feature Governance Routes
=======================================
API endpoints for Feature Governance Engine.

Endpoints:
- GET /api/v1/research-control/feature-governance/health
- GET /api/v1/research-control/feature-governance/config
- GET /api/v1/research-control/feature-governance/features/list
- POST /api/v1/research-control/feature-governance/batch
- GET /api/v1/research-control/feature-governance/summary/{feature}
- GET /api/v1/research-control/feature-governance/{feature}
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from modules.research_control.feature_governance.feature_governance_engine import (
    get_feature_governance_engine,
)
from modules.research_control.feature_governance.feature_governance_types import (
    GOVERNANCE_WEIGHTS,
    GOVERNANCE_THRESHOLDS,
    GOVERNANCE_MODIFIERS,
    GovernanceState,
)

router = APIRouter(
    prefix="/api/v1/research-control/feature-governance",
    tags=["Feature Governance"]
)


# ══════════════════════════════════════════════════════════════
# REQUEST MODELS
# ══════════════════════════════════════════════════════════════

class BatchEvaluateRequest(BaseModel):
    features: List[str]


# ══════════════════════════════════════════════════════════════
# STATIC ROUTES (must be before dynamic routes)
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def feature_governance_health():
    """Feature Governance Engine health check."""
    try:
        engine = get_feature_governance_engine()
        
        # Quick test evaluation
        test_result = engine.evaluate("funding_skew")
        
        return {
            "status": "healthy",
            "phase": "17.1",
            "module": "Feature Governance Engine",
            "description": "First layer of Research Control Fabric",
            "dimensions": list(GOVERNANCE_WEIGHTS.keys()),
            "weights": GOVERNANCE_WEIGHTS,
            "states": [s.value for s in GovernanceState],
            "thresholds": GOVERNANCE_THRESHOLDS,
            "test_result": {
                "feature": "funding_skew",
                "governance_score": round(test_result.governance_score, 4),
                "governance_state": test_result.governance_state.value,
                "weakest_dimension": test_result.weakest_dimension.value,
            },
            "known_features_count": len(engine.get_all_known_features()),
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
    """
    Get governance configuration.
    """
    return {
        "status": "ok",
        "weights": GOVERNANCE_WEIGHTS,
        "thresholds": GOVERNANCE_THRESHOLDS,
        "modifiers": {
            state.value: {
                "confidence_modifier": mods["confidence_modifier"],
                "size_modifier": mods["size_modifier"],
            }
            for state, mods in GOVERNANCE_MODIFIERS.items()
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/features/list")
async def list_features():
    """
    List all known features that can be evaluated.
    """
    try:
        engine = get_feature_governance_engine()
        features = engine.get_all_known_features()
        
        return {
            "status": "ok",
            "features": features,
            "count": len(features),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# BATCH ENDPOINT
# ══════════════════════════════════════════════════════════════

@router.post("/batch")
async def batch_evaluate(request: BatchEvaluateRequest):
    """
    Batch governance evaluation for multiple features.
    """
    try:
        engine = get_feature_governance_engine()
        results = {}
        
        summary = {
            "total": len(request.features),
            "healthy": 0,
            "watchlist": 0,
            "degraded": 0,
            "retire": 0,
        }
        
        for feature in request.features:
            try:
                result = engine.evaluate(feature)
                results[feature] = result.to_summary()
                
                # Update summary counts
                state = result.governance_state.value.lower()
                if state in summary:
                    summary[state] += 1
            except Exception as e:
                results[feature] = {
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

@router.get("/summary/{feature}")
async def feature_summary(feature: str):
    """
    Compact governance summary for quick integration.
    """
    try:
        engine = get_feature_governance_engine()
        result = engine.evaluate(feature)
        
        return {
            "status": "ok",
            **result.to_summary(),
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{feature}")
async def evaluate_feature(feature: str):
    """
    Full governance evaluation for a feature.
    
    Returns detailed assessment across all 5 dimensions:
    - stability_score
    - drift_score
    - coverage_score
    - redundancy_score
    - utility_score
    
    Plus aggregated:
    - governance_score (0-1)
    - governance_state (HEALTHY/WATCHLIST/DEGRADED/RETIRE)
    - confidence_modifier
    - size_modifier
    """
    try:
        engine = get_feature_governance_engine()
        result = engine.evaluate(feature)
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
