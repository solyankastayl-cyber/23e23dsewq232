"""
Liquidity Impact Routes

PHASE 37 Sublayer — Liquidity Impact Engine

API endpoints:
- GET  /api/v1/impact/{symbol}         - Estimate impact for default size
- POST /api/v1/impact/estimate         - Estimate impact for custom size
- GET  /api/v1/impact/history/{symbol} - Get historical estimates
- GET  /api/v1/impact/summary/{symbol} - Get summary statistics
- POST /api/v1/impact/recompute/{symbol} - Recompute and save
- GET  /api/v1/impact/health           - Health check
"""

from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from .impact_types import LiquidityImpactEstimate, ImpactSummary
from .impact_engine import get_liquidity_impact_engine
from .impact_registry import get_impact_registry


router = APIRouter(
    prefix="/api/v1/impact",
    tags=["PHASE 37 - Liquidity Impact Engine"]
)


class ImpactEstimateRequest(BaseModel):
    symbol: str
    size_usd: float
    side: str = "BUY"


# ══════════════════════════════════════════════════════════════
# Health Check
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def impact_health():
    """Health check for Liquidity Impact Engine."""
    engine = get_liquidity_impact_engine()
    registry = get_impact_registry()
    
    return {
        "status": "ok",
        "phase": "PHASE 37",
        "module": "Liquidity Impact Engine",
        "engine_ready": engine is not None,
        "db_connected": registry.collection is not None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ══════════════════════════════════════════════════════════════
# Core Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/{symbol}")
async def get_impact(
    symbol: str,
    size_usd: float = Query(default=100000),
    side: str = Query(default="BUY", pattern="^(BUY|SELL)$"),
):
    """
    Estimate liquidity impact for a trade.
    """
    engine = get_liquidity_impact_engine()
    
    try:
        estimate = engine.estimate_impact(symbol.upper(), size_usd, side)
        
        return {
            "status": "ok",
            "symbol": estimate.symbol,
            "intended_size_usd": estimate.intended_size_usd,
            "side": estimate.side,
            "expected_slippage_bps": estimate.expected_slippage_bps,
            "expected_market_impact_bps": estimate.expected_market_impact_bps,
            "expected_fill_quality": estimate.expected_fill_quality,
            "liquidity_bucket": estimate.liquidity_bucket,
            "impact_state": estimate.impact_state,
            "execution_recommendation": estimate.execution_recommendation,
            "size_modifier": estimate.size_modifier,
            "reason": estimate.reason,
            "timestamp": estimate.timestamp.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/estimate")
async def estimate_impact(request: ImpactEstimateRequest):
    """
    Estimate impact for custom trade parameters.
    """
    engine = get_liquidity_impact_engine()
    
    try:
        estimate = engine.estimate_impact(
            request.symbol.upper(),
            request.size_usd,
            request.side.upper(),
        )
        
        return {
            "status": "ok",
            "symbol": estimate.symbol,
            "intended_size_usd": estimate.intended_size_usd,
            "side": estimate.side,
            "expected_slippage_bps": estimate.expected_slippage_bps,
            "expected_market_impact_bps": estimate.expected_market_impact_bps,
            "expected_fill_quality": estimate.expected_fill_quality,
            "liquidity_bucket": estimate.liquidity_bucket,
            "impact_state": estimate.impact_state,
            "execution_recommendation": estimate.execution_recommendation,
            "size_modifier": estimate.size_modifier,
            "components": {
                "vacuum_penalty_bps": estimate.vacuum_penalty_bps,
                "pressure_penalty_bps": estimate.pressure_penalty_bps,
                "effective_depth_usd": estimate.effective_depth_usd,
                "depth_ratio": estimate.depth_ratio,
            },
            "reason": estimate.reason,
            "timestamp": estimate.timestamp.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{symbol}")
async def get_impact_history(
    symbol: str,
    limit: int = Query(default=50, le=200),
):
    """Get historical impact estimates."""
    engine = get_liquidity_impact_engine()
    
    try:
        history = engine.get_history(symbol.upper(), limit)
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "count": len(history),
            "records": [
                {
                    "intended_size_usd": e.intended_size_usd,
                    "side": e.side,
                    "expected_slippage_bps": e.expected_slippage_bps,
                    "expected_market_impact_bps": e.expected_market_impact_bps,
                    "impact_state": e.impact_state,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in history
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{symbol}")
async def get_impact_summary(symbol: str):
    """Get summary statistics for impact estimates."""
    engine = get_liquidity_impact_engine()
    
    try:
        summary = engine.generate_summary(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": summary.symbol,
            "current_liquidity_bucket": summary.current_liquidity_bucket,
            "current_impact_state": summary.current_impact_state,
            "total_estimates": summary.total_estimates,
            "avg_slippage_bps": summary.avg_slippage_bps,
            "avg_market_impact_bps": summary.avg_market_impact_bps,
            "avg_fill_quality": summary.avg_fill_quality,
            "state_distribution": {
                "low_impact": summary.low_impact_count,
                "manageable": summary.manageable_count,
                "high_impact": summary.high_impact_count,
                "untradeable": summary.untradeable_count,
            },
            "recent_avg_slippage_bps": summary.recent_avg_slippage_bps,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recompute/{symbol}")
async def recompute_impact(
    symbol: str,
    size_usd: float = Query(default=100000),
    side: str = Query(default="BUY", pattern="^(BUY|SELL)$"),
    save: bool = Query(default=True),
):
    """Recompute impact and optionally save."""
    engine = get_liquidity_impact_engine()
    registry = get_impact_registry()
    
    try:
        estimate = engine.estimate_impact(symbol.upper(), size_usd, side)
        
        saved = False
        if save:
            saved = registry.save_estimate(estimate)
        
        return {
            "status": "ok",
            "symbol": estimate.symbol,
            "expected_slippage_bps": estimate.expected_slippage_bps,
            "expected_market_impact_bps": estimate.expected_market_impact_bps,
            "impact_state": estimate.impact_state,
            "execution_recommendation": estimate.execution_recommendation,
            "saved": saved,
            "timestamp": estimate.timestamp.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/adjust-plan")
async def adjust_execution_plan(
    symbol: str,
    size_usd: float,
    side: str = Query(default="BUY", pattern="^(BUY|SELL)$"),
    planned_type: str = Query(default="MARKET"),
):
    """
    Adjust execution plan based on impact analysis.
    
    This is used by Execution Brain.
    """
    engine = get_liquidity_impact_engine()
    
    try:
        result = engine.adjust_execution_plan(
            symbol.upper(),
            size_usd,
            side,
            planned_type,
        )
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "original_size_usd": size_usd,
            "adjusted_size_usd": result["adjusted_size_usd"],
            "size_reduction_pct": result["size_reduction_pct"],
            "original_execution_type": planned_type,
            "adjusted_execution_type": result["adjusted_execution_type"],
            "type_changed": result["type_changed"],
            "impact_state": result["impact_estimate"].impact_state,
            "recommendation": result["impact_estimate"].execution_recommendation,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
