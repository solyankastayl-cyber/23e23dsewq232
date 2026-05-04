"""
Regime Intelligence v2 — Routes

API endpoints for regime detection.

Endpoints:
- GET /api/v1/regime/current
- GET /api/v1/regime/history
- GET /api/v1/regime/summary
- POST /api/v1/regime/recompute
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from datetime import datetime, timezone

from .regime_detection_engine import (
    RegimeDetectionEngine,
    get_regime_detection_engine,
)
from .regime_registry import (
    RegimeRegistry,
    get_regime_registry,
)


router = APIRouter(prefix="/api/v1/regime", tags=["regime"])


@router.get("/current", response_model=Dict[str, Any])
async def get_current_regime(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
):
    """
    Get current market regime.
    
    Returns regime type, metrics, confidence, and context.
    """
    engine = get_regime_detection_engine()
    registry = get_regime_registry()
    
    # Detect current regime (simulated if no real data)
    regime = engine.detect_regime_simulated(symbol, timeframe)
    
    # Store in history
    await registry.store_regime(regime)
    
    return {
        "regime_type": regime.regime_type,
        "trend_strength": regime.trend_strength,
        "volatility_level": regime.volatility_level,
        "liquidity_level": regime.liquidity_level,
        "regime_confidence": regime.regime_confidence,
        "dominant_driver": regime.dominant_driver,
        "context_state": regime.context_state,
        "symbol": regime.symbol,
        "timeframe": regime.timeframe,
        "computed_at": regime.computed_at.isoformat(),
    }


@router.get("/history", response_model=Dict[str, Any])
async def get_regime_history(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
    limit: int = Query(50, ge=1, le=500, description="Max records"),
):
    """
    Get regime history for symbol/timeframe.
    """
    registry = get_regime_registry()
    history = await registry.get_history(symbol, timeframe, limit)
    
    return {
        "history": [
            {
                "regime_type": r.regime_type,
                "confidence": r.confidence,
                "trend_strength": r.trend_strength,
                "volatility": r.volatility,
                "liquidity": r.liquidity,
                "dominant_driver": r.dominant_driver,
                "context_state": r.context_state,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in history
        ],
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(history),
    }


@router.get("/summary", response_model=Dict[str, Any])
async def get_regime_summary(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
):
    """
    Get regime summary statistics.
    
    Returns counts, dominant regime, stability metrics.
    """
    registry = get_regime_registry()
    summary = await registry.get_summary(symbol, timeframe)
    
    return {
        "total_records": summary.total_records,
        "trending_count": summary.trending_count,
        "ranging_count": summary.ranging_count,
        "volatile_count": summary.volatile_count,
        "illiquid_count": summary.illiquid_count,
        "current_regime": summary.current_regime,
        "average_confidence": summary.average_confidence,
        "dominant_regime": summary.dominant_regime,
        "regime_stability": summary.regime_stability,
        "symbol": symbol,
        "timeframe": timeframe,
    }


@router.post("/recompute", response_model=Dict[str, Any])
async def recompute_regime(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
):
    """
    Force recompute of current regime.
    
    Useful for refreshing regime detection.
    """
    try:
        engine = get_regime_detection_engine()
        registry = get_regime_registry()
        
        # Recompute
        regime = engine.detect_regime_simulated(symbol, timeframe)
        
        # Store in history
        await registry.store_regime(regime)
        
        return {
            "status": "ok",
            "regime_type": regime.regime_type,
            "trend_strength": regime.trend_strength,
            "volatility_level": regime.volatility_level,
            "liquidity_level": regime.liquidity_level,
            "regime_confidence": regime.regime_confidence,
            "dominant_driver": regime.dominant_driver,
            "context_state": regime.context_state,
            "symbol": regime.symbol,
            "timeframe": regime.timeframe,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recompute failed: {str(e)}"
        )


@router.get("/metrics", response_model=Dict[str, Any])
async def get_regime_metrics(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
):
    """
    Get raw input metrics used for regime detection.
    """
    engine = get_regime_detection_engine()
    metrics = engine.get_cached_metrics(symbol, timeframe)
    
    if not metrics:
        # Generate new metrics
        engine.detect_regime_simulated(symbol, timeframe)
        metrics = engine.get_cached_metrics(symbol, timeframe)
    
    if not metrics:
        return {
            "error": "No metrics available",
            "symbol": symbol,
            "timeframe": timeframe,
        }
    
    return {
        "price": metrics.price,
        "ema_50": metrics.ema_50,
        "ema_200": metrics.ema_200,
        "atr": metrics.atr,
        "orderbook_depth": metrics.orderbook_depth,
        "volume_profile": metrics.volume_profile,
        "spread_inverse": metrics.spread_inverse,
        "fractal_alignment": metrics.fractal_alignment,
        "symbol": symbol,
        "timeframe": timeframe,
    }
