"""
Health Routes
=============

PHASE 3.2 - API endpoints for Advanced Trade Health Engine.
"""

import time
import uuid
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .trade_health_engine import advanced_trade_health_engine
from .health_event_engine import health_event_engine
from .health_decay_engine import health_decay_engine
from .health_alert_engine import health_alert_engine
from .health_repository import health_repository


router = APIRouter(prefix="/api/trade-health", tags=["phase3.2-trade-health"])


# ===========================================
# Request Models
# ===========================================

class HealthStatusRequest(BaseModel):
    """Request for health status calculation"""
    position_id: str = Field(..., description="Position ID")
    entry_price: float = Field(40000.0, description="Entry price")
    current_price: float = Field(40500.0, description="Current price")
    stop_price: float = Field(39000.0, description="Stop price")
    target_price: float = Field(42000.0, description="Target price")
    direction: str = Field("LONG", description="Direction (LONG/SHORT)")
    bars_in_trade: int = Field(10, description="Bars since entry")
    max_bars: int = Field(100, description="Max allowed bars")
    indicators: Optional[Dict[str, float]] = Field(None, description="Current indicators")
    previous_indicators: Optional[Dict[str, float]] = Field(None, description="Previous indicators")


class EventDetectionRequest(BaseModel):
    """Request for event detection"""
    position_id: str = Field(..., description="Position ID")
    direction: str = Field("LONG", description="Direction")
    entry_price: float = Field(40000.0, description="Entry price")
    current_price: float = Field(40500.0, description="Current price")
    stop_price: float = Field(39000.0, description="Stop price")
    target_price: float = Field(42000.0, description="Target price")
    current_health: float = Field(75.0, description="Current health score")
    previous_indicators: Optional[Dict[str, float]] = Field(None)
    current_indicators: Optional[Dict[str, float]] = Field(None)


class DecayCalculationRequest(BaseModel):
    """Request for decay calculation"""
    position_id: str = Field(..., description="Position ID")
    bars_in_trade: int = Field(20, description="Bars in trade")
    current_health: float = Field(70.0, description="Current health")
    r_multiple: float = Field(0.5, description="Current R multiple")
    volatility_ratio: float = Field(1.0, description="ATR/ATR_avg ratio")
    momentum_declining: bool = Field(False, description="Is momentum declining")
    structure_broken: bool = Field(False, description="Is structure broken")
    recent_negative_events: int = Field(0, description="Count of recent negative events")


# ===========================================
# Health Status Endpoints
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for Trade Health module"""
    return {
        "module": "PHASE 3.2 Advanced Trade Health Engine",
        "status": "healthy",
        "version": "2.0.0",
        "engines": {
            "healthEngine": advanced_trade_health_engine.get_health(),
            "eventEngine": health_event_engine.get_health(),
            "decayEngine": health_decay_engine.get_health(),
            "alertEngine": health_alert_engine.get_health()
        },
        "repository": health_repository.get_stats(),
        "timestamp": int(time.time() * 1000)
    }


@router.post("/status")
async def calculate_health_status(request: HealthStatusRequest):
    """
    Calculate comprehensive trade health status.
    
    Returns:
    - Health score (0-100)
    - Component scores
    - Health trend
    - Stability score
    - Events
    - Alerts
    """
    
    # Get previous health
    prev_health = health_repository.get_health(request.position_id)
    previous_score = prev_health.current_health if prev_health else 100.0
    
    indicators = request.indicators or {
        "rsi": 55, "macdHist": 2, "adx": 25,
        "atr": request.current_price * 0.02,
        "atr_avg": request.current_price * 0.02,
        "close": request.current_price,
        "support": request.stop_price * 1.01,
        "resistance": request.entry_price * 1.05
    }
    
    # Detect events
    events = health_event_engine.detect_events(
        position_id=request.position_id,
        direction=request.direction,
        entry_price=request.entry_price,
        current_price=request.current_price,
        stop_price=request.stop_price,
        target_price=request.target_price,
        current_health=previous_score,
        previous_indicators=request.previous_indicators,
        current_indicators=indicators
    )
    
    # Calculate R-multiple for decay
    if request.direction == "LONG":
        risk = request.entry_price - request.stop_price
        current_pnl = request.current_price - request.entry_price
    else:
        risk = request.stop_price - request.entry_price
        current_pnl = request.entry_price - request.current_price
    
    r_multiple = current_pnl / risk if risk > 0 else 0
    
    # Calculate decay
    atr = indicators.get("atr", 0)
    atr_avg = indicators.get("atr_avg", atr)
    vol_ratio = atr / atr_avg if atr_avg > 0 else 1.0
    
    negative_events = len([e for e in events if e.impact < 0])
    
    decay, decay_records = health_decay_engine.calculate_decay(
        position_id=request.position_id,
        bars_in_trade=request.bars_in_trade,
        current_health=previous_score,
        r_multiple=r_multiple,
        volatility_ratio=vol_ratio,
        momentum_declining=indicators.get("macdHist", 0) < -1,
        structure_broken=indicators.get("close", 0) < indicators.get("support", 0),
        recent_negative_events=negative_events
    )
    
    # Calculate health
    health = advanced_trade_health_engine.calculate_health(
        position_id=request.position_id,
        entry_price=request.entry_price,
        current_price=request.current_price,
        stop_price=request.stop_price,
        target_price=request.target_price,
        direction=request.direction,
        bars_in_trade=request.bars_in_trade,
        max_bars=request.max_bars,
        previous_health=previous_score,
        indicators=indicators,
        events=events,
        decay_applied=decay
    )
    
    # Generate alerts
    alerts = health_alert_engine.generate_alerts(
        position_id=request.position_id,
        health=health
    )
    health.active_alerts = alerts
    
    # Save to repository
    health_repository.save_health(health)
    health_repository.save_events(request.position_id, events)
    health_repository.save_decay(request.position_id, decay_records)
    health_repository.save_alerts(request.position_id, alerts)
    if health.stability:
        health_repository.save_stability(health.stability)
    
    return health.to_dict()


@router.get("/status/{position_id}")
async def get_health_status(position_id: str):
    """Get current health status for a position"""
    health = health_repository.get_health(position_id)
    if not health:
        raise HTTPException(status_code=404, detail=f"Health not found for {position_id}")
    return health.to_dict()


# ===========================================
# History Endpoint
# ===========================================

@router.get("/history/{position_id}")
async def get_health_history(
    position_id: str,
    limit: int = Query(50, le=100)
):
    """Get health history for a position"""
    history = health_repository.get_history(position_id, limit)
    return {
        "positionId": position_id,
        "history": [h.to_dict() for h in history],
        "count": len(history)
    }


# ===========================================
# Events Endpoints
# ===========================================

@router.post("/events/detect")
async def detect_events(request: EventDetectionRequest):
    """Detect health events for a position"""
    
    events = health_event_engine.detect_events(
        position_id=request.position_id,
        direction=request.direction,
        entry_price=request.entry_price,
        current_price=request.current_price,
        stop_price=request.stop_price,
        target_price=request.target_price,
        current_health=request.current_health,
        previous_indicators=request.previous_indicators,
        current_indicators=request.current_indicators
    )
    
    health_repository.save_events(request.position_id, events)
    
    return {
        "positionId": request.position_id,
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


@router.get("/events/{position_id}")
async def get_events(
    position_id: str,
    hours: int = Query(4, le=24)
):
    """Get recent events for a position"""
    events = health_repository.get_recent_events(position_id, hours)
    return {
        "positionId": position_id,
        "events": [e.to_dict() for e in events],
        "count": len(events),
        "hours": hours
    }


# ===========================================
# Stability Endpoint
# ===========================================

@router.get("/stability/{position_id}")
async def get_stability(position_id: str):
    """Get stability score for a position"""
    stability = health_repository.get_stability(position_id)
    if not stability:
        raise HTTPException(status_code=404, detail=f"Stability not found for {position_id}")
    return stability.to_dict()


# ===========================================
# Alerts Endpoints
# ===========================================

@router.get("/alerts")
async def get_all_alerts():
    """Get all active alerts"""
    alerts = health_alert_engine.get_all_active_alerts()
    return {
        "alerts": [a.to_dict() for a in alerts],
        "count": len(alerts),
        "summary": health_alert_engine.get_alert_summary()
    }


@router.get("/alerts/{position_id}")
async def get_position_alerts(position_id: str):
    """Get alerts for a position"""
    alerts = health_repository.get_active_alerts(position_id)
    return {
        "positionId": position_id,
        "alerts": [a.to_dict() for a in alerts],
        "count": len(alerts)
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert"""
    success = health_repository.acknowledge_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return {"success": True, "alertId": alert_id, "action": "acknowledged"}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve an alert"""
    success = health_repository.resolve_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return {"success": True, "alertId": alert_id, "action": "resolved"}


# ===========================================
# Decay Endpoints
# ===========================================

@router.post("/decay/calculate")
async def calculate_decay(request: DecayCalculationRequest):
    """Calculate health decay"""
    
    decay, records = health_decay_engine.calculate_decay(
        position_id=request.position_id,
        bars_in_trade=request.bars_in_trade,
        current_health=request.current_health,
        r_multiple=request.r_multiple,
        volatility_ratio=request.volatility_ratio,
        momentum_declining=request.momentum_declining,
        structure_broken=request.structure_broken,
        recent_negative_events=request.recent_negative_events
    )
    
    health_repository.save_decay(request.position_id, records)
    
    return {
        "positionId": request.position_id,
        "totalDecay": round(decay, 2),
        "records": [r.to_dict() for r in records],
        "cumulativeDecay": round(health_decay_engine.get_cumulative_decay(request.position_id), 2)
    }


@router.get("/decay/{position_id}")
async def get_decay(position_id: str):
    """Get decay records for a position"""
    records = health_repository.get_decay(position_id)
    return {
        "positionId": position_id,
        "records": [r.to_dict() for r in records[-20:]],
        "totalDecay": round(health_repository.get_total_decay(position_id), 2),
        "breakdown": health_decay_engine.get_decay_breakdown(position_id)
    }


@router.get("/decay/config")
async def get_decay_config():
    """Get decay configuration"""
    return health_decay_engine.get_decay_rate_info()


# ===========================================
# Demo & Testing
# ===========================================

@router.post("/demo")
async def run_demo():
    """
    Run demo calculations to test the module.
    """
    
    demo_positions = [
        {
            "position_id": f"demo_btc_{uuid.uuid4().hex[:4]}",
            "symbol": "BTC",
            "direction": "LONG",
            "entry": 40000,
            "current": 40800,
            "stop": 39000,
            "target": 43000,
            "bars": 15
        },
        {
            "position_id": f"demo_eth_{uuid.uuid4().hex[:4]}",
            "symbol": "ETH",
            "direction": "LONG",
            "entry": 2500,
            "current": 2420,  # Losing
            "stop": 2400,
            "target": 2700,
            "bars": 30
        },
        {
            "position_id": f"demo_sol_{uuid.uuid4().hex[:4]}",
            "symbol": "SOL",
            "direction": "SHORT",
            "entry": 100,
            "current": 95,  # Winning
            "stop": 105,
            "target": 85,
            "bars": 8
        }
    ]
    
    results = []
    
    for pos in demo_positions:
        # Create request
        req = HealthStatusRequest(
            position_id=pos["position_id"],
            entry_price=pos["entry"],
            current_price=pos["current"],
            stop_price=pos["stop"],
            target_price=pos["target"],
            direction=pos["direction"],
            bars_in_trade=pos["bars"],
            max_bars=100,
            indicators={
                "rsi": 55 if pos["current"] > pos["entry"] else 45,
                "macdHist": 2 if pos["current"] > pos["entry"] else -2,
                "adx": 28,
                "atr": pos["current"] * 0.025,
                "atr_avg": pos["current"] * 0.02,
                "close": pos["current"],
                "support": pos["stop"] * 1.01,
                "resistance": pos["entry"] * 1.05
            }
        )
        
        # Calculate health (reuse the endpoint logic)
        health_response = await calculate_health_status(req)
        
        results.append({
            "positionId": pos["position_id"],
            "symbol": pos["symbol"],
            "direction": pos["direction"],
            "pnl_pct": round((pos["current"] - pos["entry"]) / pos["entry"] * 100, 2) if pos["direction"] == "LONG" else round((pos["entry"] - pos["current"]) / pos["entry"] * 100, 2),
            "health": health_response["health"]["current"],
            "status": health_response["health"]["status"],
            "trend": health_response["trend"]["direction"],
            "stability": health_response["stability"]["stabilityScore"] if health_response["stability"] else None,
            "alertCount": len(health_response["alerts"]),
            "action": health_response["action"]["recommended"]
        })
    
    return {
        "demo": "complete",
        "positions": results,
        "count": len(results),
        "repositoryStats": health_repository.get_stats()
    }


@router.delete("/clear/{position_id}")
async def clear_position_data(position_id: str):
    """Clear all data for a position"""
    health_repository.clear_position(position_id)
    health_event_engine.clear_events(position_id)
    health_decay_engine.clear_decay(position_id)
    health_alert_engine.clear_alerts(position_id)
    advanced_trade_health_engine.clear_history(position_id)
    
    return {"success": True, "positionId": position_id, "action": "cleared"}


@router.get("/stats")
async def get_stats():
    """Get module statistics"""
    return health_repository.get_stats()
