"""
Position Intelligence Routes
============================

API endpoints for Position Intelligence (PHASE 3.1)
"""

import time
import uuid
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .position_quality_engine import position_quality_engine
from .trade_health_engine import trade_health_engine
from .risk_adjustment_engine import risk_adjustment_engine
from .position_repository import position_intelligence_repository
from .position_quality_types import (
    PositionQualityScore,
    TradeHealthScore,
    RiskAdjustment,
    PositionIntelligence
)


router = APIRouter(prefix="/api/position-intelligence", tags=["phase3-position-intelligence"])


# ===========================================
# Request Models
# ===========================================

class QualityRequest(BaseModel):
    """Request for quality calculation"""
    position_id: Optional[str] = Field(None, description="Position ID (auto-generated if not provided)")
    symbol: str = Field("BTC", description="Symbol")
    strategy: str = Field("TREND_CONFIRMATION", description="Strategy")
    direction: str = Field("LONG", description="Direction")
    regime: str = Field("TRENDING", description="Market regime")
    entry_price: float = Field(40000.0, description="Entry price")
    stop_price: float = Field(39000.0, description="Stop price")
    target_price: float = Field(42000.0, description="Target price")
    current_exposure_pct: float = Field(5.0, description="Current exposure %")
    current_drawdown_pct: float = Field(1.0, description="Current drawdown %")
    indicators: Optional[Dict[str, float]] = Field(None, description="Indicator values")


class HealthRequest(BaseModel):
    """Request for health calculation"""
    position_id: str = Field(..., description="Position ID")
    entry_price: float = Field(40000.0, description="Entry price")
    current_price: float = Field(40500.0, description="Current price")
    stop_price: float = Field(39000.0, description="Stop price")
    target_price: float = Field(42000.0, description="Target price")
    direction: str = Field("LONG", description="Direction")
    bars_in_trade: int = Field(10, description="Bars since entry")
    max_bars: int = Field(100, description="Max allowed bars")
    indicators: Optional[Dict[str, float]] = Field(None, description="Indicator values")


class RiskAdjustmentRequest(BaseModel):
    """Request for risk adjustment"""
    position_id: str = Field(..., description="Position ID")
    base_risk_pct: float = Field(1.0, description="Base risk %")
    regime_stability: str = Field("NORMAL", description="Regime stability")
    signal_confidence: float = Field(0.8, description="Signal confidence")


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for Position Intelligence"""
    return {
        "module": "PHASE 3.1 Position Intelligence",
        "status": "healthy",
        "version": "1.0.0",
        "engines": {
            "quality": position_quality_engine.get_health(),
            "health": trade_health_engine.get_health(),
            "riskAdjustment": risk_adjustment_engine.get_health()
        },
        "timestamp": int(time.time() * 1000)
    }


# ===========================================
# Quality Score
# ===========================================

@router.post("/quality")
async def calculate_quality(request: QualityRequest):
    """
    Calculate Position Quality Score (0-100).
    
    Evaluates:
    - Signal quality
    - Market context
    - Risk quality
    - Timing quality
    - Execution quality
    """
    
    position_id = request.position_id or f"pos_{uuid.uuid4().hex[:8]}"
    indicators = request.indicators or {
        "rsi": 55,
        "macdHist": 5,
        "close": request.entry_price,
        "sma20": request.entry_price * 0.99,
        "atr": request.entry_price * 0.02
    }
    
    quality = position_quality_engine.calculate_quality(
        position_id=position_id,
        symbol=request.symbol,
        strategy=request.strategy,
        direction=request.direction,
        regime=request.regime,
        indicators=indicators,
        entry_price=request.entry_price,
        stop_price=request.stop_price,
        target_price=request.target_price,
        current_exposure_pct=request.current_exposure_pct,
        current_drawdown_pct=request.current_drawdown_pct
    )
    
    position_intelligence_repository.save_quality(quality)
    
    return quality.to_dict()


@router.get("/quality/history")
async def get_quality_history(limit: int = Query(50, le=100)):
    """Get recent quality scores"""
    history = position_intelligence_repository.get_quality_history(limit)
    return {
        "history": [q.to_dict() for q in history],
        "count": len(history)
    }


@router.get("/quality/{position_id}")
async def get_quality(position_id: str):
    """Get quality score for position"""
    quality = position_intelligence_repository.get_quality(position_id)
    if not quality:
        raise HTTPException(status_code=404, detail=f"Quality not found for {position_id}")
    return quality.to_dict()


# ===========================================
# Trade Health
# ===========================================

@router.post("/health")
async def calculate_health(request: HealthRequest):
    """
    Calculate Trade Health Score (0-100).
    
    Monitors:
    - Price action health
    - Structure health
    - Momentum health
    - Time health
    - P&L health
    """
    
    # Get previous health if exists
    prev_health = position_intelligence_repository.get_health(request.position_id)
    previous_score = prev_health.current_health if prev_health else 100.0
    
    indicators = request.indicators or {"rsi": 50, "macdHist": 0}
    
    health = trade_health_engine.calculate_health(
        position_id=request.position_id,
        entry_price=request.entry_price,
        current_price=request.current_price,
        stop_price=request.stop_price,
        target_price=request.target_price,
        direction=request.direction,
        bars_in_trade=request.bars_in_trade,
        max_bars=request.max_bars,
        previous_health=previous_score,
        indicators=indicators
    )
    
    position_intelligence_repository.save_health(health)
    
    return health.to_dict()


@router.get("/health/history")
async def get_health_history(limit: int = Query(50, le=100)):
    """Get recent health scores"""
    history = position_intelligence_repository.get_health_history(limit)
    return {
        "history": [h.to_dict() for h in history],
        "count": len(history)
    }


@router.get("/health/{position_id}")
async def get_health_score(position_id: str):
    """Get health score for position"""
    health = position_intelligence_repository.get_health(position_id)
    if not health:
        raise HTTPException(status_code=404, detail=f"Health not found for {position_id}")
    return health.to_dict()


# ===========================================
# Risk Adjustment
# ===========================================

@router.post("/risk")
async def calculate_risk_adjustment(request: RiskAdjustmentRequest):
    """
    Calculate dynamic risk adjustment.
    
    Based on:
    - Quality score
    - Health score
    - Regime stability
    - Signal confidence
    """
    
    # Get quality and health
    quality = position_intelligence_repository.get_quality(request.position_id)
    if not quality:
        raise HTTPException(
            status_code=400,
            detail=f"Quality score required. Calculate quality first for {request.position_id}"
        )
    
    health = position_intelligence_repository.get_health(request.position_id)
    
    adjustment = risk_adjustment_engine.calculate_adjustment(
        position_id=request.position_id,
        base_risk_pct=request.base_risk_pct,
        quality=quality,
        health=health,
        regime_stability=request.regime_stability,
        signal_confidence=request.signal_confidence
    )
    
    position_intelligence_repository.save_risk_adjustment(adjustment)
    
    return adjustment.to_dict()


@router.get("/risk/tables")
async def get_multiplier_tables():
    """Get all risk multiplier tables"""
    return risk_adjustment_engine.get_multiplier_tables()


@router.get("/risk/{position_id}")
async def get_risk_adjustment(position_id: str):
    """Get risk adjustment for position"""
    adjustment = position_intelligence_repository.get_risk_adjustment(position_id)
    if not adjustment:
        raise HTTPException(status_code=404, detail=f"Risk adjustment not found for {position_id}")
    return adjustment.to_dict()


# ===========================================
# Combined Intelligence
# ===========================================

@router.get("/full/{position_id}")
async def get_full_intelligence(position_id: str):
    """
    Get complete position intelligence.
    
    Includes quality, health, and risk adjustment.
    """
    
    quality = position_intelligence_repository.get_quality(position_id)
    health = position_intelligence_repository.get_health(position_id)
    risk = position_intelligence_repository.get_risk_adjustment(position_id)
    
    if not quality:
        raise HTTPException(status_code=404, detail=f"No intelligence found for {position_id}")
    
    # Calculate overall score
    overall_score = quality.total_score
    if health:
        overall_score = (quality.total_score * 0.6 + health.current_health * 0.4)
    
    # Determine status
    if overall_score >= 80:
        status = "STRONG"
    elif overall_score >= 65:
        status = "GOOD"
    elif overall_score >= 50:
        status = "NEUTRAL"
    elif overall_score >= 35:
        status = "WEAK"
    else:
        status = "EXIT"
    
    # Determine action
    if health and health.recommended_action != "HOLD":
        action = health.recommended_action
    elif quality.grade.value in ["D", "F"]:
        action = "REDUCE"
    else:
        action = "HOLD"
    
    intelligence = PositionIntelligence(
        position_id=position_id,
        symbol=quality.symbol,
        strategy=quality.strategy,
        quality=quality,
        health=health or TradeHealthScore(position_id=position_id),
        risk_adjustment=risk or RiskAdjustment(position_id=position_id),
        overall_score=overall_score,
        overall_status=status,
        primary_action=action,
        computed_at=int(time.time() * 1000)
    )
    
    position_intelligence_repository.save_intelligence(intelligence)
    
    return intelligence.to_dict()


@router.get("/all")
async def get_all_positions():
    """Get all tracked positions"""
    intelligence = position_intelligence_repository.get_all_intelligence()
    return {
        "positions": [i.to_dict() for i in intelligence],
        "count": len(intelligence)
    }


# ===========================================
# Demo & Testing
# ===========================================

@router.post("/demo")
async def run_demo():
    """
    Run demo calculations for testing.
    
    Creates sample positions and calculates intelligence.
    """
    
    demo_positions = [
        {
            "symbol": "BTC",
            "strategy": "TREND_CONFIRMATION",
            "direction": "LONG",
            "regime": "TRENDING",
            "entry": 40000,
            "stop": 39000,
            "target": 42000,
            "current": 40800
        },
        {
            "symbol": "ETH",
            "strategy": "MEAN_REVERSION",
            "direction": "LONG",
            "regime": "RANGE",
            "entry": 2500,
            "stop": 2400,
            "target": 2650,
            "current": 2480
        },
        {
            "symbol": "SOL",
            "strategy": "MOMENTUM_BREAKOUT",
            "direction": "LONG",
            "regime": "HIGH_VOLATILITY",
            "entry": 100,
            "stop": 95,
            "target": 115,
            "current": 108
        }
    ]
    
    results = []
    
    for pos in demo_positions:
        position_id = f"demo_{pos['symbol'].lower()}_{uuid.uuid4().hex[:4]}"
        
        # Calculate quality
        quality = position_quality_engine.calculate_quality(
            position_id=position_id,
            symbol=pos["symbol"],
            strategy=pos["strategy"],
            direction=pos["direction"],
            regime=pos["regime"],
            indicators={"rsi": 55, "macdHist": 5, "close": pos["current"], "sma20": pos["entry"] * 0.99, "atr": pos["entry"] * 0.02},
            entry_price=pos["entry"],
            stop_price=pos["stop"],
            target_price=pos["target"],
            current_exposure_pct=5.0,
            current_drawdown_pct=1.0
        )
        position_intelligence_repository.save_quality(quality)
        
        # Calculate health
        health = trade_health_engine.calculate_health(
            position_id=position_id,
            entry_price=pos["entry"],
            current_price=pos["current"],
            stop_price=pos["stop"],
            target_price=pos["target"],
            direction=pos["direction"],
            bars_in_trade=15,
            max_bars=100,
            previous_health=100.0,
            indicators={"rsi": 55, "macdHist": 5}
        )
        position_intelligence_repository.save_health(health)
        
        # Calculate risk
        risk = risk_adjustment_engine.calculate_adjustment(
            position_id=position_id,
            base_risk_pct=1.0,
            quality=quality,
            health=health,
            regime_stability="NORMAL",
            signal_confidence=0.8
        )
        position_intelligence_repository.save_risk_adjustment(risk)
        
        results.append({
            "positionId": position_id,
            "symbol": pos["symbol"],
            "strategy": pos["strategy"],
            "qualityScore": round(quality.total_score, 1),
            "qualityGrade": quality.grade.value,
            "healthScore": round(health.current_health, 1),
            "healthStatus": health.status.value,
            "adjustedRisk": round(risk.adjusted_risk_pct, 2),
            "riskLevel": risk.risk_level.value
        })
    
    return {
        "demo": "complete",
        "positions": results,
        "count": len(results)
    }


@router.get("/stats")
async def get_stats():
    """Get repository statistics"""
    return position_intelligence_repository.get_stats()
