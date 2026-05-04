"""
Routing Routes - PHASE 5.3
==========================

REST API endpoints for Order Routing Engine.

Endpoints:
- POST /api/routing/evaluate
- POST /api/routing/plan
- POST /api/routing/execute-plan
- GET  /api/routing/venues/{symbol}
- GET  /api/routing/slippage/{symbol}
- GET  /api/routing/history
- GET  /api/routing/events
- GET  /api/routing/stats
- GET  /api/routing/policies
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .routing_types import (
    RoutingRequest,
    RoutingPolicy,
    RoutingUrgency,
    EvaluateRequest,
    PlanRequest,
    ExecutePlanRequest
)
from .routing_engine import get_routing_engine
from .venue_selector import get_venue_selector
from .slippage_aware_router import get_slippage_router
from .routing_repository import RoutingRepository


router = APIRouter(prefix="/api/routing", tags=["Order Routing"])

# Initialize
repository = RoutingRepository()


# ============================================
# Health
# ============================================

@router.get("/health")
async def routing_health():
    """Health check"""
    return {
        "status": "healthy",
        "version": "phase_5.3",
        "components": [
            "routing_engine",
            "venue_selector",
            "execution_plan_builder",
            "slippage_aware_router"
        ],
        "supported_policies": [p.value for p in RoutingPolicy],
        "supported_urgency": [u.value for u in RoutingUrgency],
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Routing Evaluation
# ============================================

@router.post("/evaluate")
async def evaluate_routing(request: EvaluateRequest):
    """
    Evaluate routing options and get decision.
    
    Returns optimal venue and expected execution parameters.
    """
    engine = get_routing_engine()
    
    routing_request = RoutingRequest(
        symbol=request.symbol.upper(),
        side=request.side.upper(),
        size=request.size,
        order_type=request.order_type.upper(),
        limit_price=request.limit_price,
        policy=RoutingPolicy(request.policy.upper()) if request.policy else RoutingPolicy.BEST_EXECUTION,
        urgency=RoutingUrgency(request.urgency.upper()) if request.urgency else RoutingUrgency.NORMAL,
        max_slippage_bps=request.max_slippage_bps
    )
    
    decision = engine.evaluate(routing_request)
    
    # Save decision
    repository.save_decision(decision)
    
    return {
        "decision": {
            "request_id": decision.request_id,
            "selected_exchange": decision.selected_exchange,
            "selected_order_type": decision.selected_order_type,
            "expected_price": decision.expected_price,
            "expected_slippage_bps": decision.expected_slippage_bps,
            "expected_fee": decision.expected_fee,
            "confidence": decision.confidence,
            "routing_reason": decision.routing_reason,
            "alternative_venues": decision.alternative_venues,
            "policy_used": decision.policy_used.value
        },
        "venue_scores": [
            {
                "exchange": s.exchange,
                "price": s.price,
                "spread_bps": s.spread_bps,
                "liquidity_score": s.liquidity_score,
                "expected_slippage_bps": s.expected_slippage_bps,
                "health_status": s.health_status.value,
                "health_score": s.health_score,
                "total_score": s.total_score
            }
            for s in decision.venue_scores
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/predict")
async def predict_execution(request: EvaluateRequest):
    """Predict execution outcome for an order"""
    engine = get_routing_engine()
    
    routing_request = RoutingRequest(
        symbol=request.symbol.upper(),
        side=request.side.upper(),
        size=request.size,
        order_type=request.order_type.upper(),
        limit_price=request.limit_price,
        max_slippage_bps=request.max_slippage_bps
    )
    
    prediction = engine.predict_execution(routing_request)
    
    return {
        "prediction": prediction,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Execution Plans
# ============================================

@router.post("/plan")
async def create_execution_plan(request: PlanRequest):
    """
    Create execution plan for order.
    
    May return split plan for large orders.
    """
    engine = get_routing_engine()
    
    routing_request = RoutingRequest(
        symbol=request.symbol.upper(),
        side=request.side.upper(),
        size=request.size,
        order_type=request.order_type.upper(),
        limit_price=request.limit_price,
        policy=RoutingPolicy(request.policy.upper()) if request.policy else RoutingPolicy.BEST_EXECUTION
    )
    
    force_split = request.split_threshold < 10.0  # Force split if threshold is low
    plan = engine.create_plan(routing_request, force_split)
    
    # Save plan
    repository.save_plan(plan)
    
    return {
        "plan": {
            "plan_id": plan.plan_id,
            "symbol": plan.symbol,
            "side": plan.side,
            "total_size": plan.total_size,
            "execution_mode": plan.execution_mode.value,
            "estimated_avg_price": plan.estimated_avg_price,
            "estimated_total_cost": plan.estimated_total_cost,
            "estimated_slippage_bps": plan.estimated_slippage_bps,
            "estimated_fees": plan.estimated_fees,
            "estimated_duration_ms": plan.estimated_duration_ms,
            "status": plan.status
        },
        "legs": [
            {
                "exchange": leg.exchange,
                "size": leg.size,
                "percentage": leg.percentage,
                "order_type": leg.order_type,
                "expected_price": leg.expected_price,
                "expected_slippage_bps": leg.expected_slippage_bps,
                "priority": leg.priority
            }
            for leg in plan.legs
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/plan/{plan_id}")
async def get_plan(plan_id: str):
    """Get execution plan by ID"""
    plan = repository.get_plan(plan_id)
    
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    
    return {
        "plan": plan,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/execute-plan")
async def execute_plan(request: ExecutePlanRequest):
    """Execute an execution plan"""
    plan = repository.get_plan(request.plan_id)
    
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {request.plan_id} not found")
    
    if request.dry_run:
        return {
            "dry_run": True,
            "plan_id": request.plan_id,
            "status": "WOULD_EXECUTE",
            "plan": plan,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Update plan status
    repository.update_plan_status(request.plan_id, "EXECUTING")
    
    # In real implementation, would execute each leg
    # For now, mark as completed
    repository.update_plan_status(request.plan_id, "COMPLETED")
    
    return {
        "executed": True,
        "plan_id": request.plan_id,
        "status": "COMPLETED",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Venue Analysis
# ============================================

@router.get("/venues/{symbol}")
async def get_venues(
    symbol: str,
    side: str = Query(default="BUY"),
    size: float = Query(default=1.0, gt=0)
):
    """Get venue analysis for symbol"""
    venue_selector = get_venue_selector()
    
    analyses = venue_selector.get_all_venue_analyses(symbol.upper(), size, side.upper())
    
    return {
        "symbol": symbol.upper(),
        "side": side.upper(),
        "size": size,
        "venues": {
            exchange: {
                "best_bid": a.best_bid,
                "best_ask": a.best_ask,
                "mid_price": a.mid_price,
                "spread_bps": a.spread_bps,
                "bid_depth_usd": a.bid_depth_usd,
                "ask_depth_usd": a.ask_depth_usd,
                "slippage_for_size_bps": a.slippage_for_size_bps,
                "venue_status": a.venue_status.value,
                "health_score": a.health_score,
                "failover_status": a.failover_status,
                "recommended": a.recommended,
                "rejection_reason": a.rejection_reason
            }
            for exchange, a in analyses.items()
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/best-venues/{symbol}")
async def get_best_venues(
    symbol: str,
    side: str = Query(default="BUY"),
    size: float = Query(default=1.0, gt=0),
    top_n: int = Query(default=3, ge=1, le=5)
):
    """Get top N best venues for symbol"""
    engine = get_routing_engine()
    
    scores = engine.get_best_venues(symbol.upper(), side.upper(), size, top_n)
    
    return {
        "symbol": symbol.upper(),
        "side": side.upper(),
        "size": size,
        "best_venues": [
            {
                "rank": i + 1,
                "exchange": s.exchange,
                "price": s.price,
                "spread_bps": s.spread_bps,
                "liquidity_score": s.liquidity_score,
                "expected_slippage_bps": s.expected_slippage_bps,
                "health_score": s.health_score,
                "total_score": s.total_score
            }
            for i, s in enumerate(scores)
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Slippage Analysis
# ============================================

@router.get("/slippage/{symbol}")
async def get_slippage_analysis(
    symbol: str,
    exchange: Optional[str] = Query(default=None),
    side: str = Query(default="BUY"),
    size: float = Query(default=1.0, gt=0)
):
    """Get slippage analysis for symbol"""
    slippage_router = get_slippage_router()
    
    if exchange:
        # Single exchange analysis
        profile = slippage_router.get_slippage_profile(exchange.upper(), symbol.upper())
        prediction = slippage_router.predict_slippage(
            exchange.upper(), symbol.upper(), side.upper(), size
        )
        should_avoid, reason = slippage_router.should_avoid_venue(
            exchange.upper(), symbol.upper()
        )
        
        return {
            "exchange": exchange.upper(),
            "symbol": symbol.upper(),
            "profile": profile,
            "prediction": prediction,
            "should_avoid": should_avoid,
            "avoid_reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # All exchanges
    analyses = {}
    for ex in ["BINANCE", "BYBIT", "OKX"]:
        profile = slippage_router.get_slippage_profile(ex, symbol.upper())
        prediction = slippage_router.predict_slippage(
            ex, symbol.upper(), side.upper(), size
        )
        analyses[ex] = {
            "profile": profile,
            "prediction": prediction
        }
    
    return {
        "symbol": symbol.upper(),
        "side": side.upper(),
        "size": size,
        "analyses": analyses,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# History and Statistics
# ============================================

@router.get("/history")
async def get_routing_history(
    symbol: Optional[str] = Query(default=None),
    exchange: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500)
):
    """Get routing decision history"""
    decisions = repository.get_decisions(symbol, exchange, limit)
    
    return {
        "count": len(decisions),
        "decisions": decisions,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/events")
async def get_routing_events(
    event_type: Optional[str] = Query(default=None),
    request_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500)
):
    """Get routing events"""
    # Get from engine's in-memory log
    engine = get_routing_engine()
    events = engine.get_routing_events(limit)
    
    return {
        "count": len(events),
        "events": events,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/stats")
async def get_routing_stats():
    """Get routing statistics"""
    engine = get_routing_engine()
    stats = engine.get_routing_stats()
    
    # Add analytics from DB
    analytics = repository.get_routing_analytics(7)
    
    return {
        "stats": stats,
        "analytics": analytics,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/policies")
async def get_routing_policies():
    """Get available routing policies"""
    engine = get_routing_engine()
    
    return {
        "policies": engine.get_available_policies(),
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Venue Statistics
# ============================================

@router.get("/venue-stats")
async def get_venue_stats(
    exchange: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None)
):
    """Get venue statistics"""
    stats = repository.get_venue_stats(exchange, symbol)
    
    return {
        "count": len(stats),
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }
