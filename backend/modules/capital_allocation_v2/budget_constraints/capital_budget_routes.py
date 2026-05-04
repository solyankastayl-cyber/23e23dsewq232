"""
PHASE 21.2 — Capital Budget Routes
==================================
API endpoints for Capital Budget Engine.

Endpoints:
- GET  /api/v1/capital-allocation/budget
- GET  /api/v1/capital-allocation/budget/summary
- GET  /api/v1/capital-allocation/budget/sleeves
- GET  /api/v1/capital-allocation/budget/dry-powder
- GET  /api/v1/capital-allocation/budget/reserve
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from typing import Optional

from modules.capital_allocation_v2.budget_constraints.capital_budget_engine import (
    get_capital_budget_engine,
)
from modules.capital_allocation_v2.budget_constraints.sleeve_limit_engine import (
    get_sleeve_limit_engine,
)

router = APIRouter(
    prefix="/api/v1/capital-allocation/budget",
    tags=["PHASE 21.2 - Capital Budget"],
)


@router.get("")
async def get_budget_state(
    total_capital: float = Query(1.0, description="Total capital"),
    regime: str = Query("MIXED", description="Market regime"),
    portfolio_state: str = Query("NORMAL", description="Portfolio state"),
    risk_state: str = Query("NORMAL", description="Risk state"),
    loop_state: str = Query("HEALTHY", description="Research loop state"),
    volatility_state: str = Query("NORMAL", description="Volatility state"),
    regime_confidence: float = Query(0.7, description="Regime confidence"),
    allocation_confidence: float = Query(0.7, description="Allocation confidence"),
):
    """
    Get full capital budget state.
    
    Returns budget constraints and deployable capital.
    """
    try:
        engine = get_capital_budget_engine()
        state = engine.compute_budget(
            total_capital=total_capital,
            regime=regime,
            portfolio_state=portfolio_state,
            risk_state=risk_state,
            loop_state=loop_state,
            volatility_state=volatility_state,
            regime_confidence=regime_confidence,
            allocation_confidence=allocation_confidence,
        )
        
        return {
            "status": "ok",
            "phase": "21.2",
            "data": state.to_full_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_budget_summary():
    """
    Get capital budget summary.
    
    Returns compact summary of budget state.
    """
    try:
        engine = get_capital_budget_engine()
        summary = engine.get_summary()
        
        return {
            "status": "ok",
            "phase": "21.2",
            "data": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sleeves")
async def get_sleeve_limits():
    """
    Get sleeve limits.
    
    Returns max allocation limits per category.
    """
    try:
        engine = get_sleeve_limit_engine()
        limits = engine.get_limits()
        
        return {
            "status": "ok",
            "phase": "21.2",
            "data": {
                "sleeve_limits": limits,
                "description": {
                    "strategy": "Max allocation to any single strategy",
                    "factor": "Max allocation to any single factor",
                    "asset": "Max allocation to any single asset",
                    "cluster": "Max allocation to any single cluster",
                },
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dry-powder")
async def get_dry_powder(
    total_capital: float = Query(1.0, description="Total capital"),
    regime: str = Query("MIXED", description="Market regime"),
    volatility_state: str = Query("NORMAL", description="Volatility state"),
    opportunity_score: float = Query(0.5, description="Opportunity score (0-1)"),
    squeeze_probability: float = Query(0.3, description="Squeeze probability (0-1)"),
):
    """
    Get dry powder allocation.
    
    Returns capital reserved for opportunities.
    """
    try:
        engine = get_capital_budget_engine()
        result = engine.dry_powder_engine.compute_dry_powder(
            total_capital=total_capital,
            regime=regime,
            volatility_state=volatility_state,
            opportunity_score=opportunity_score,
            squeeze_probability=squeeze_probability,
        )
        
        return {
            "status": "ok",
            "phase": "21.2",
            "data": {
                "dry_powder": round(result["dry_powder"], 4),
                "dry_powder_ratio": round(result["dry_powder_ratio"], 4),
                "components": {k: round(v, 4) for k, v in result["components"].items()},
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reserve")
async def get_reserve_capital(
    total_capital: float = Query(1.0, description="Total capital"),
    regime: str = Query("normal", description="Regime category"),
    portfolio_state: str = Query("NORMAL", description="Portfolio state"),
    risk_state: str = Query("NORMAL", description="Risk state"),
):
    """
    Get reserve capital allocation.
    
    Returns capital held inactive.
    """
    try:
        engine = get_capital_budget_engine()
        result = engine.reserve_engine.compute_reserve(
            total_capital=total_capital,
            regime=regime,
            portfolio_state=portfolio_state,
            risk_state=risk_state,
        )
        
        return {
            "status": "ok",
            "phase": "21.2",
            "data": {
                "reserve_capital": round(result["reserve_capital"], 4),
                "reserve_ratio": round(result["reserve_ratio"], 4),
                "regime_category": result["regime_category"],
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emergency")
async def get_emergency_state(
    portfolio_state: str = Query("NORMAL", description="Portfolio state"),
    risk_state: str = Query("NORMAL", description="Risk state"),
    loop_state: str = Query("HEALTHY", description="Research loop state"),
    volatility_extreme: bool = Query(False, description="Extreme volatility flag"),
):
    """
    Get emergency cut state.
    
    Returns emergency capital reduction status.
    """
    try:
        engine = get_capital_budget_engine()
        result = engine.emergency_engine.compute_emergency_cut(
            portfolio_state=portfolio_state,
            risk_state=risk_state,
            loop_state=loop_state,
            volatility_extreme=volatility_extreme,
        )
        
        return {
            "status": "ok",
            "phase": "21.2",
            "data": {
                "emergency_cut": round(result["emergency_cut"], 4),
                "cut_level": result["cut_level"],
                "triggers": result["triggers"],
                "is_emergency": engine.emergency_engine.is_emergency(result["cut_level"]),
                "is_defensive": engine.emergency_engine.is_defensive(result["cut_level"]),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/throttle")
async def get_throttle_state(
    regime: str = Query("MIXED", description="Market regime"),
    regime_confidence: float = Query(0.7, description="Regime confidence"),
    allocation_confidence: float = Query(0.7, description="Allocation confidence"),
):
    """
    Get regime throttle state.
    
    Returns regime-based capital throttling.
    """
    try:
        engine = get_capital_budget_engine()
        result = engine.throttle_engine.compute_throttle(
            regime=regime,
            regime_confidence=regime_confidence,
            allocation_confidence=allocation_confidence,
        )
        
        return {
            "status": "ok",
            "phase": "21.2",
            "data": {
                "regime_throttle": round(result["regime_throttle"], 4),
                "base_throttle": round(result["base_throttle"], 4),
                "confidence_adjustment": round(result["confidence_adjustment"], 4),
                "regime_input": result["regime_input"],
                "is_throttled": engine.throttle_engine.is_throttled(result["regime_throttle"]),
                "is_severely_throttled": engine.throttle_engine.is_severely_throttled(result["regime_throttle"]),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
