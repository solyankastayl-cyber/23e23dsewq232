"""
Analytics API Routes
Phase 4: Operational Analytics Layer

Read-only endpoints for operational visibility.
"""

from fastapi import APIRouter, HTTPException

from .service import get_analytics_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dynamic-risk/summary")
async def get_dynamic_risk_summary():
    """
    Dynamic Risk Analytics Summary.
    
    Provides aggregated R1 decision metrics:
    - Approved vs blocked counts
    - Approval rate
    - Average multiplier and notional
    - Clamp rate
    
    Returns:
        {
            "approved_count": int,
            "blocked_count": int,
            "approval_rate_pct": float,
            "avg_multiplier": float,
            "avg_notional_usd": float,
            "clamped_count": int,
            "clamp_rate_pct": float
        }
    """
    try:
        service = get_analytics_service()
        return await service.get_dynamic_risk_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dynamic-risk/reasons")
async def get_dynamic_risk_reasons():
    """
    Top Dynamic Risk block reasons.
    
    Returns list of block reasons sorted by frequency.
    
    Returns:
        [
            {"reason": "MAX_PORTFOLIO_EXPOSURE", "count": 5},
            {"reason": "NO_CONFIDENCE", "count": 4},
            ...
        ]
    """
    try:
        service = get_analytics_service()
        return await service.get_dynamic_risk_reasons()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution/summary")
async def get_execution_summary():
    """
    Execution Analytics Summary.
    
    Provides execution pipeline metrics:
    - Queued → Started → Submitted → Filled/Failed
    - Fill rate
    
    Returns:
        {
            "queued": int,
            "started": int,
            "submitted": int,
            "filled": int,
            "failed": int,
            "fill_rate_pct": float
        }
    """
    try:
        service = get_analytics_service()
        return await service.get_execution_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/safety/summary")
async def get_safety_summary():
    """
    Safety Analytics Summary.
    
    Provides safety block metrics:
    - Total blocks (R1 + AutoSafety)
    - R1 vs AutoSafety breakdown
    - Top blocking rule
    
    Returns:
        {
            "total_blocks": int,
            "dynamic_risk_block_count": int,
            "auto_block_count": int,
            "top_rule": str
        }
    """
    try:
        service = get_analytics_service()
        return await service.get_safety_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/adaptive-risk/summary")
async def get_adaptive_risk_summary():
    """
    Adaptive Risk (R2) Analytics Summary.
    
    Provides R2 behavior metrics to answer:
    - R2 работает вообще? (activation rate)
    - Насколько агрессивно? (avg multiplier)
    - Из-за чего? (components)
    
    Returns:
        {
            "activation_rate_pct": float,
            "avg_r2_multiplier": float,
            "avg_drawdown_component": float,
            "avg_loss_streak_component": float
        }
    """
    try:
        service = get_analytics_service()
        return await service.get_adaptive_risk_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
