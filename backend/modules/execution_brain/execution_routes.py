"""
Execution Brain Routes

PHASE 37 — Execution Brain

API endpoints:
- GET  /api/v1/execution/plan/{symbol}    - Get or generate execution plan
- GET  /api/v1/execution/history/{symbol} - Get historical plans
- GET  /api/v1/execution/active/{symbol}  - Get active plan
- POST /api/v1/execution/execute/{symbol} - Execute plan
- GET  /api/v1/execution/summary/{symbol} - Get summary statistics
- GET  /api/v1/execution/health           - Health check
"""

from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from .execution_types import ExecutionPlan, ExecutionSummary, MIN_CONFIDENCE_THRESHOLD
from .execution_engine import get_execution_brain_engine
from .execution_router import get_execution_router
from .execution_registry import get_execution_registry


router = APIRouter(
    prefix="/api/v1/execution",
    tags=["PHASE 37 - Execution Brain"]
)


class ExecutionRequest(BaseModel):
    symbol: str
    hypothesis_type: str = "BULLISH_CONTINUATION"
    direction: str = "LONG"
    confidence: float = 0.65
    reliability: float = 0.70
    portfolio_capital: float = 100000.0
    allocation_weight: float = 0.10


# ══════════════════════════════════════════════════════════════
# Health Check
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def execution_health():
    """Health check for Execution Brain."""
    engine = get_execution_brain_engine()
    registry = get_execution_registry()
    
    return {
        "status": "ok",
        "phase": "PHASE 37",
        "module": "Execution Brain",
        "engine_ready": engine is not None,
        "db_connected": registry.collection is not None,
        "min_confidence_threshold": MIN_CONFIDENCE_THRESHOLD,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ══════════════════════════════════════════════════════════════
# Core Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/plan/{symbol}")
async def get_execution_plan(
    symbol: str,
    hypothesis_type: str = Query(default="BULLISH_CONTINUATION"),
    direction: str = Query(default="LONG", pattern="^(LONG|SHORT)$"),
    confidence: float = Query(default=0.65, ge=0, le=1),
    reliability: float = Query(default=0.70, ge=0, le=1),
    portfolio_capital: float = Query(default=100000),
    allocation_weight: float = Query(default=0.10, ge=0, le=1),
):
    """
    Get or generate execution plan for a symbol.
    """
    engine = get_execution_brain_engine()
    
    try:
        plan = engine.generate_plan(
            symbol=symbol.upper(),
            hypothesis_type=hypothesis_type,
            direction=direction,
            confidence=confidence,
            reliability=reliability,
            portfolio_capital=portfolio_capital,
            allocation_weight=allocation_weight,
        )
        
        return {
            "status": "ok",
            "symbol": plan.symbol,
            "strategy": plan.strategy,
            "direction": plan.direction,
            "position_size_usd": plan.position_size_usd,
            "position_size_adjusted": plan.position_size_adjusted,
            "entry_price": plan.entry_price,
            "stop_loss": plan.stop_loss,
            "take_profit": plan.take_profit,
            "risk_level": plan.risk_level,
            "risk_reward_ratio": plan.risk_reward_ratio,
            "execution_type": plan.execution_type,
            "confidence": plan.confidence,
            "reliability": plan.reliability,
            "plan_status": plan.status,
            "blocked_reason": plan.blocked_reason,
            "impact_adjusted": plan.impact_adjusted,
            "size_reduction_pct": plan.size_reduction_pct,
            "type_changed": plan.type_changed,
            "reason": plan.reason,
            "timestamp": plan.timestamp.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_execution_plan(request: ExecutionRequest):
    """
    Generate execution plan from request body.
    """
    engine = get_execution_brain_engine()
    
    try:
        plan = engine.generate_plan(
            symbol=request.symbol.upper(),
            hypothesis_type=request.hypothesis_type,
            direction=request.direction.upper(),
            confidence=request.confidence,
            reliability=request.reliability,
            portfolio_capital=request.portfolio_capital,
            allocation_weight=request.allocation_weight,
        )
        
        return {
            "status": "ok",
            "symbol": plan.symbol,
            "strategy": plan.strategy,
            "direction": plan.direction,
            "position_size_usd": plan.position_size_usd,
            "position_size_adjusted": plan.position_size_adjusted,
            "entry_price": plan.entry_price,
            "stop_loss": plan.stop_loss,
            "take_profit": plan.take_profit,
            "risk_level": plan.risk_level,
            "risk_modifier": plan.risk_modifier,
            "risk_reward_ratio": plan.risk_reward_ratio,
            "execution_type": plan.execution_type,
            "execution_type_original": plan.execution_type_original,
            "confidence": plan.confidence,
            "reliability": plan.reliability,
            "plan_status": plan.status,
            "blocked_reason": plan.blocked_reason,
            "impact_adjusted": plan.impact_adjusted,
            "size_reduction_pct": plan.size_reduction_pct,
            "type_changed": plan.type_changed,
            "reason": plan.reason,
            "timestamp": plan.timestamp.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{symbol}")
async def get_execution_history(
    symbol: str,
    limit: int = Query(default=50, le=200),
):
    """Get historical execution plans."""
    engine = get_execution_brain_engine()
    
    try:
        history = engine.get_history(symbol.upper(), limit)
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "count": len(history),
            "records": [
                {
                    "strategy": p.strategy,
                    "direction": p.direction,
                    "position_size_usd": p.position_size_usd,
                    "entry_price": p.entry_price,
                    "risk_level": p.risk_level,
                    "execution_type": p.execution_type,
                    "status": p.status,
                    "timestamp": p.timestamp.isoformat(),
                }
                for p in history
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active/{symbol}")
async def get_active_plan(symbol: str):
    """Get active execution plan for symbol."""
    engine = get_execution_brain_engine()
    
    try:
        plan = engine.get_active_plan(symbol.upper())
        
        if plan is None:
            return {
                "status": "ok",
                "symbol": symbol.upper(),
                "has_active_plan": False,
                "message": "No active plan",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        return {
            "status": "ok",
            "symbol": plan.symbol,
            "has_active_plan": True,
            "strategy": plan.strategy,
            "direction": plan.direction,
            "position_size_adjusted": plan.position_size_adjusted,
            "entry_price": plan.entry_price,
            "stop_loss": plan.stop_loss,
            "take_profit": plan.take_profit,
            "execution_type": plan.execution_type,
            "plan_status": plan.status,
            "timestamp": plan.timestamp.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute/{symbol}")
async def execute_plan(
    symbol: str,
    save: bool = Query(default=True),
):
    """
    Execute the active plan for a symbol.
    
    This would integrate with exchange adapter in production.
    """
    engine = get_execution_brain_engine()
    registry = get_execution_registry()
    
    try:
        plan = engine.get_active_plan(symbol.upper())
        
        if plan is None:
            raise HTTPException(status_code=404, detail="No active plan to execute")
        
        if plan.status == "BLOCKED":
            raise HTTPException(
                status_code=400,
                detail=f"Plan is blocked: {plan.blocked_reason}"
            )
        
        # In production, this would send to exchange adapter
        # For now, we mark as executed
        plan.status = "EXECUTED"
        
        saved = False
        if save:
            saved = registry.save_plan(plan)
        
        return {
            "status": "ok",
            "symbol": plan.symbol,
            "direction": plan.direction,
            "position_size_usd": plan.position_size_adjusted,
            "entry_price": plan.entry_price,
            "execution_type": plan.execution_type,
            "executed": True,
            "saved": saved,
            "message": "Plan marked as executed (mock execution)",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{symbol}")
async def get_execution_summary(symbol: str):
    """Get summary statistics for execution plans."""
    engine = get_execution_brain_engine()
    
    try:
        summary = engine.generate_summary(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": summary.symbol,
            "has_active_plan": summary.has_active_plan,
            "current_direction": summary.current_direction,
            "current_status": summary.current_status,
            "total_plans": summary.total_plans,
            "approved_count": summary.approved_count,
            "blocked_count": summary.blocked_count,
            "executed_count": summary.executed_count,
            "risk_distribution": {
                "low": summary.low_risk_count,
                "medium": summary.medium_risk_count,
                "high": summary.high_risk_count,
                "extreme": summary.extreme_risk_count,
            },
            "execution_type_distribution": {
                "market": summary.market_count,
                "limit": summary.limit_count,
                "twap": summary.twap_count,
                "iceberg": summary.iceberg_count,
            },
            "avg_confidence": summary.avg_confidence,
            "avg_risk_reward": summary.avg_risk_reward,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Router Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/route/{symbol}")
async def get_execution_route(
    symbol: str,
    size_usd: float = Query(default=100000),
    liquidity_bucket: str = Query(default="NORMAL"),
    impact_state: str = Query(default="MANAGEABLE"),
):
    """
    Get execution routing recommendation.
    """
    router = get_execution_router()
    
    try:
        execution_type = router.route_execution(
            liquidity_bucket, size_usd, impact_state, symbol.upper()
        )
        
        split_rec = router.get_order_split_recommendation(execution_type, size_usd)
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "size_usd": size_usd,
            "liquidity_bucket": liquidity_bucket,
            "impact_state": impact_state,
            "recommended_execution_type": execution_type,
            "split_recommendation": split_rec,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
