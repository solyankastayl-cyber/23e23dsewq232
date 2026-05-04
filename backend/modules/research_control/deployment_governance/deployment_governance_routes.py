"""
PHASE 17.3 — Deployment Governance Routes
==========================================
API endpoints for Deployment Governance Engine.

Endpoints:
- GET /api/v1/research-control/deployment-governance/health
- GET /api/v1/research-control/deployment-governance/config
- GET /api/v1/research-control/deployment-governance/factors/list
- POST /api/v1/research-control/deployment-governance/batch
- GET /api/v1/research-control/deployment-governance/summary/{factor}
- GET /api/v1/research-control/deployment-governance/{factor}
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from modules.research_control.deployment_governance.deployment_governance_engine import (
    get_deployment_governance_engine,
)
from modules.research_control.deployment_governance.deployment_governance_types import (
    DEPLOYMENT_WEIGHTS,
    DEPLOYMENT_THRESHOLDS,
    DEPLOYMENT_MODIFIERS,
    DeploymentState,
    GovernanceAction,
)

router = APIRouter(
    prefix="/api/v1/research-control/deployment-governance",
    tags=["Deployment Governance"]
)


# ══════════════════════════════════════════════════════════════
# REQUEST MODELS
# ══════════════════════════════════════════════════════════════

class DeploymentBatchRequest(BaseModel):
    factors: List[str]


# ══════════════════════════════════════════════════════════════
# STATIC ROUTES (must be before dynamic routes)
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def deployment_governance_health():
    """Deployment Governance Engine health check."""
    try:
        engine = get_deployment_governance_engine()
        
        # Quick test evaluation
        test_result = engine.evaluate("trend_breakout_factor")
        
        return {
            "status": "healthy",
            "phase": "17.3",
            "module": "Deployment Governance Engine",
            "description": "Third layer of Research Control Fabric - Lifecycle Management",
            "dimensions": list(DEPLOYMENT_WEIGHTS.keys()),
            "weights": DEPLOYMENT_WEIGHTS,
            "deployment_states": [s.value for s in DeploymentState],
            "governance_actions": [a.value for a in GovernanceAction],
            "thresholds": DEPLOYMENT_THRESHOLDS,
            "test_result": {
                "factor": "trend_breakout_factor",
                "deployment_state": test_result.deployment_state.value,
                "deployment_score": round(test_result.deployment_score, 4),
                "governance_action": test_result.governance_action.value,
                "promotion_readiness": round(test_result.promotion_readiness, 4),
                "rollback_risk": round(test_result.rollback_risk, 4),
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
    """Get deployment governance configuration."""
    return {
        "status": "ok",
        "weights": DEPLOYMENT_WEIGHTS,
        "thresholds": DEPLOYMENT_THRESHOLDS,
        "modifiers": {
            action.value: {
                "capital_modifier": mods["capital_modifier"],
                "confidence_modifier": mods["confidence_modifier"],
            }
            for action, mods in DEPLOYMENT_MODIFIERS.items()
        },
        "deployment_states": [s.value for s in DeploymentState],
        "governance_actions": [a.value for a in GovernanceAction],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/factors/list")
async def list_factors():
    """List all known factors with deployment state."""
    try:
        engine = get_deployment_governance_engine()
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
async def batch_evaluate(request: DeploymentBatchRequest):
    """Batch deployment governance evaluation."""
    try:
        engine = get_deployment_governance_engine()
        results = {}
        
        summary = {
            "total": len(request.factors),
            "shadow": 0,
            "candidate": 0,
            "live": 0,
            "frozen": 0,
            "retired": 0,
            "actions": {
                "PROMOTE": 0,
                "HOLD": 0,
                "KEEP_SHADOW": 0,
                "REDUCE": 0,
                "ROLLBACK": 0,
                "RETIRE": 0,
            }
        }
        
        for factor in request.factors:
            try:
                result = engine.evaluate(factor)
                results[factor] = result.to_summary()
                
                # Update state counts
                state = result.deployment_state.value.lower()
                if state in summary:
                    summary[state] += 1
                
                # Update action counts
                action = result.governance_action.value
                if action in summary["actions"]:
                    summary["actions"][action] += 1
            except Exception as e:
                results[factor] = {
                    "error": str(e),
                    "deployment_state": "UNKNOWN",
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
    """Compact deployment governance summary."""
    try:
        engine = get_deployment_governance_engine()
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
    Full deployment governance evaluation for a factor.
    
    Returns:
    - deployment_state: Current lifecycle state (SHADOW/CANDIDATE/LIVE/FROZEN/RETIRED)
    - deployment_score: Overall deployment readiness
    - shadow_readiness: Readiness to exit shadow mode
    - promotion_readiness: Readiness for promotion
    - rollback_risk: Risk level requiring rollback
    - governance_action: Recommended action (PROMOTE/HOLD/KEEP_SHADOW/REDUCE/ROLLBACK/RETIRE)
    - capital_modifier: Capital allocation modifier
    - confidence_modifier: Confidence modifier
    """
    try:
        engine = get_deployment_governance_engine()
        result = engine.evaluate(factor)
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
