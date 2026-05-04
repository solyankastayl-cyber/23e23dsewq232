"""
PHASE 18.3 — Meta Portfolio Routes
==================================
API endpoints for Meta Portfolio Aggregator.

Endpoints:
- GET /api/v1/meta-portfolio/health
- GET /api/v1/meta-portfolio/state
- GET /api/v1/meta-portfolio/summary
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from modules.portfolio.meta_portfolio.meta_portfolio_engine import (
    get_meta_portfolio_engine,
)
from modules.portfolio.meta_portfolio.meta_portfolio_types import (
    PortfolioState,
    INTELLIGENCE_TO_PORTFOLIO,
)

router = APIRouter(
    prefix="/api/v1/meta-portfolio",
    tags=["Meta Portfolio"]
)


# ══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def meta_portfolio_health():
    """Meta Portfolio health check."""
    try:
        engine = get_meta_portfolio_engine()
        
        # Quick test analysis
        test_result = engine.analyze_portfolio("default")
        
        return {
            "status": "healthy",
            "phase": "18.3",
            "module": "Meta Portfolio Aggregator",
            "description": "Unified portfolio management layer combining Intelligence + Constraints",
            "capabilities": [
                "Unified Portfolio State",
                "Combined Risk Assessment",
                "Trade Permission Logic",
                "Modifier Aggregation",
            ],
            "portfolio_states": [s.value for s in PortfolioState],
            "state_mapping": {
                "constraint": {
                    "HARD_LIMIT": "RISK_OFF",
                    "SOFT_LIMIT": "CONSTRAINED",
                },
                "intelligence": {
                    k: v.value for k, v in INTELLIGENCE_TO_PORTFOLIO.items()
                },
            },
            "test_result": {
                "portfolio_state": test_result.portfolio_state.value,
                "intelligence_state": test_result.intelligence_state,
                "constraint_state": test_result.constraint_state,
                "allowed": test_result.allowed,
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
async def get_meta_portfolio_state(
    portfolio_id: str = Query("default", description="Portfolio ID to analyze")
):
    """
    Full meta portfolio state.
    
    Returns unified analysis combining:
    - Portfolio Intelligence (risk assessment)
    - Portfolio Constraints (limit enforcement)
    
    Key fields:
    - portfolio_state: BALANCED / CONSTRAINED / RISK_OFF
    - allowed: Whether new positions can be opened
    - confidence_modifier, capital_modifier: Combined modifiers
    - recommended_action: What to do next
    """
    try:
        engine = get_meta_portfolio_engine()
        result = engine.analyze_portfolio(portfolio_id)
        
        return {
            "status": "ok",
            "portfolio_id": portfolio_id,
            "data": result.to_full_dict(),
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
    Compact meta portfolio summary.
    
    Returns minimal data for quick integration into trading pipeline.
    """
    try:
        engine = get_meta_portfolio_engine()
        result = engine.analyze_portfolio(portfolio_id)
        
        return {
            "status": "ok",
            "portfolio_id": portfolio_id,
            "data": result.to_summary(),
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
