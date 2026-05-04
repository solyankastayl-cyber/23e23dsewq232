"""
PHASE 18.1 — Portfolio Intelligence Routes
==========================================
API endpoints for Portfolio Intelligence Layer.

Endpoints:
- GET /api/v1/portfolio-intelligence/health
- GET /api/v1/portfolio-intelligence/state
- GET /api/v1/portfolio-intelligence/exposures
- GET /api/v1/portfolio-intelligence/factors
- GET /api/v1/portfolio-intelligence/clusters
- GET /api/v1/portfolio-intelligence/summary
- GET /api/v1/portfolio-intelligence/portfolios
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from modules.portfolio.portfolio_intelligence.portfolio_intelligence_engine import (
    get_portfolio_intelligence_engine,
)
from modules.portfolio.portfolio_intelligence.portfolio_intelligence_types import (
    PortfolioRiskState,
    RecommendedAction,
    RISK_STATE_MODIFIERS,
    CONCENTRATION_THRESHOLDS,
)

router = APIRouter(
    prefix="/api/v1/portfolio-intelligence",
    tags=["Portfolio Intelligence"]
)


# ══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def portfolio_intelligence_health():
    """Portfolio Intelligence health check."""
    try:
        engine = get_portfolio_intelligence_engine()
        
        # Quick test analysis
        test_result = engine.analyze_portfolio("default")
        
        return {
            "status": "healthy",
            "phase": "18.1",
            "module": "Portfolio Intelligence Layer",
            "description": "Meta Portfolio Intelligence - views portfolio as single risk object",
            "capabilities": [
                "Net/Gross Exposure Calculation",
                "Asset Exposure Analysis (BTC/ETH/ALT)",
                "Factor Concentration Tracking",
                "Cluster Exposure Analysis",
                "Portfolio Risk State Detection",
                "Recommended Action Generation",
            ],
            "risk_states": [s.value for s in PortfolioRiskState],
            "recommended_actions": [a.value for a in RecommendedAction],
            "state_modifiers": {
                s.value: RISK_STATE_MODIFIERS[s]
                for s in PortfolioRiskState
            },
            "concentration_thresholds": CONCENTRATION_THRESHOLDS,
            "test_result": {
                "portfolio_risk_state": test_result.portfolio_risk_state.value,
                "recommended_action": test_result.recommended_action.value,
                "net_exposure": round(test_result.net_exposure, 2),
                "concentration_score": round(test_result.concentration_score, 2),
            },
            "known_portfolios_count": len(engine.get_all_known_portfolios()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ══════════════════════════════════════════════════════════════
# LIST PORTFOLIOS
# ══════════════════════════════════════════════════════════════

@router.get("/portfolios")
async def list_portfolios():
    """List all known portfolios."""
    try:
        engine = get_portfolio_intelligence_engine()
        portfolios = engine.get_all_known_portfolios()
        
        return {
            "status": "ok",
            "portfolios": portfolios,
            "count": len(portfolios),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# MAIN STATE ENDPOINT
# ══════════════════════════════════════════════════════════════

@router.get("/state")
async def get_portfolio_state(
    portfolio_id: str = Query("default", description="Portfolio ID to analyze")
):
    """
    Full portfolio intelligence state.
    
    Returns complete analysis including:
    - Net/Gross exposure
    - Asset exposure (BTC, ETH, ALT)
    - Factor exposure
    - Cluster exposure
    - Concentration/Diversification scores
    - Risk state and recommended action
    - Confidence/Capital modifiers
    """
    try:
        engine = get_portfolio_intelligence_engine()
        result = engine.analyze_portfolio(portfolio_id)
        
        return {
            "status": "ok",
            "portfolio_id": portfolio_id,
            "data": result.to_full_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# EXPOSURE ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("/exposures")
async def get_exposures(
    portfolio_id: str = Query("default", description="Portfolio ID")
):
    """
    Get exposure metrics.
    
    Returns:
    - Net exposure (longs - shorts)
    - Gross exposure (abs(longs) + abs(shorts))
    - Asset exposures (BTC, ETH, ALT)
    """
    try:
        engine = get_portfolio_intelligence_engine()
        result = engine.get_exposures(portfolio_id)
        
        return {
            "status": "ok",
            "portfolio_id": portfolio_id,
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# FACTOR ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("/factors")
async def get_factors(
    portfolio_id: str = Query("default", description="Portfolio ID")
):
    """
    Get factor exposure analysis.
    
    Returns:
    - Factor exposure by category (trend, momentum, reversal, etc.)
    - Overload detection
    - Detailed breakdown
    """
    try:
        engine = get_portfolio_intelligence_engine()
        result = engine.get_factors(portfolio_id)
        
        return {
            "status": "ok",
            "portfolio_id": portfolio_id,
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# CLUSTER ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("/clusters")
async def get_clusters(
    portfolio_id: str = Query("default", description="Portfolio ID")
):
    """
    Get cluster exposure analysis.
    
    Returns:
    - Cluster exposure (btc_cluster, eth_cluster, majors_cluster, alts_cluster)
    - Overload detection
    - Detailed breakdown
    """
    try:
        engine = get_portfolio_intelligence_engine()
        result = engine.get_clusters(portfolio_id)
        
        return {
            "status": "ok",
            "portfolio_id": portfolio_id,
            "data": result,
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
    Compact portfolio intelligence summary.
    
    Returns minimal data for quick integration.
    """
    try:
        engine = get_portfolio_intelligence_engine()
        result = engine.analyze_portfolio(portfolio_id)
        
        return {
            "status": "ok",
            "portfolio_id": portfolio_id,
            "data": result.to_summary(),
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
