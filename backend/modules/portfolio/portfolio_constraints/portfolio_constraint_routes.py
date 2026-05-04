"""
PHASE 18.2 — Portfolio Constraint Routes
========================================
API endpoints for Portfolio Constraint Engine.

Endpoints:
- GET /api/v1/portfolio-constraints/health
- GET /api/v1/portfolio-constraints/state
- GET /api/v1/portfolio-constraints/check
- GET /api/v1/portfolio-constraints/summary
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from modules.portfolio.portfolio_constraints.portfolio_constraint_engine import (
    get_portfolio_constraint_engine,
)
from modules.portfolio.portfolio_constraints.portfolio_constraint_types import (
    ConstraintState,
    ConstraintType,
    ViolationType,
    CONSTRAINT_STATE_MODIFIERS,
    EXPOSURE_LIMITS,
    CLUSTER_LIMITS,
    FACTOR_LIMITS,
    LEVERAGE_LIMITS,
)

router = APIRouter(
    prefix="/api/v1/portfolio-constraints",
    tags=["Portfolio Constraints"]
)


# ══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def portfolio_constraints_health():
    """Portfolio Constraint Engine health check."""
    try:
        engine = get_portfolio_constraint_engine()
        
        # Quick test check
        test_result = engine.check_constraints("default")
        
        return {
            "status": "healthy",
            "phase": "18.2",
            "module": "Portfolio Constraint Engine",
            "description": "Checks portfolio constraints before trade execution",
            "capabilities": [
                "Exposure Constraint Checking (HARD)",
                "Cluster Constraint Checking (SOFT)",
                "Factor Constraint Checking (SOFT)",
                "Leverage Constraint Checking (HARD)",
            ],
            "constraint_states": [s.value for s in ConstraintState],
            "constraint_types": [t.value for t in ConstraintType],
            "violation_types": [v.value for v in ViolationType],
            "limits": {
                "exposure": EXPOSURE_LIMITS,
                "cluster": CLUSTER_LIMITS,
                "factor": FACTOR_LIMITS,
                "leverage": LEVERAGE_LIMITS,
            },
            "state_modifiers": {
                s.value: CONSTRAINT_STATE_MODIFIERS[s]
                for s in ConstraintState
            },
            "test_result": {
                "constraint_state": test_result.constraint_state.value,
                "allowed": test_result.allowed,
                "violations_count": len(test_result.violations),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ══════════════════════════════════════════════════════════════
# STATE ENDPOINT
# ══════════════════════════════════════════════════════════════

@router.get("/state")
async def get_constraint_state(
    portfolio_id: str = Query("default", description="Portfolio ID to check")
):
    """
    Full portfolio constraint state.
    
    Returns:
    - constraint_state: OK / SOFT_LIMIT / HARD_LIMIT
    - Violation flags (exposure, cluster, factor, leverage)
    - allowed: Whether new positions can be opened
    - confidence_modifier, capital_modifier
    - Detailed violations and constraint values
    """
    try:
        engine = get_portfolio_constraint_engine()
        result = engine.check_constraints(portfolio_id)
        
        return {
            "status": "ok",
            "portfolio_id": portfolio_id,
            "data": result.to_full_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# CHECK ENDPOINT
# ══════════════════════════════════════════════════════════════

@router.get("/check")
async def check_constraints(
    portfolio_id: str = Query("default", description="Portfolio ID to check")
):
    """
    Quick constraint check.
    
    Returns simplified constraint state for quick integration.
    """
    try:
        engine = get_portfolio_constraint_engine()
        result = engine.check_constraints(portfolio_id)
        
        return {
            "status": "ok",
            "portfolio_id": portfolio_id,
            "constraint_state": result.constraint_state.value,
            "allowed": result.allowed,
            "exposure_violation": result.exposure_violation,
            "cluster_violation": result.cluster_violation,
            "factor_violation": result.factor_violation,
            "leverage_violation": result.leverage_violation,
            "confidence_modifier": round(result.confidence_modifier, 4),
            "capital_modifier": round(result.capital_modifier, 4),
            "reason": result.reason,
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# SUMMARY ENDPOINT
# ══════════════════════════════════════════════════════════════

@router.get("/summary")
async def get_summary(
    portfolio_id: str = Query("default", description="Portfolio ID")
):
    """
    Compact constraint summary.
    
    Returns minimal data for quick integration.
    """
    try:
        engine = get_portfolio_constraint_engine()
        result = engine.check_constraints(portfolio_id)
        
        return {
            "status": "ok",
            "portfolio_id": portfolio_id,
            "data": result.to_summary(),
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
