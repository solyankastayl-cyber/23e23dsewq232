"""
Trading Engine API Routes

Endpoints:
- /api/trading/decision/{symbol}/{timeframe} - Get trading decision
- /api/trading/state/{symbol}/{timeframe} - Get market state
- /api/trading/entry-filter - Evaluate entry conditions
- /api/trading/position-size - Calculate position size
- /api/trading/full-analysis - Complete trading analysis
- /api/trading/signals - Signal management
- /api/trading/alerts - Alert management
- /api/trading/performance - Performance analytics
- /api/trading/indicator-quality - Indicator quality analysis
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict
from datetime import datetime, timezone

from .entry_filter_engine import (
    get_trading_engine,
    TradingDecision,
    EntryDecision,
    PositionSizeDecision,
)
from .market_state_engine import (
    get_market_state_engine,
    MarketStateResult,
)
from .signal_engine import (
    get_signal_engine,
    TradingSignal,
    SignalStatus,
    SignalDirection,
)
from .signal_storage import get_signal_storage
from .signal_lifecycle_engine import get_lifecycle_engine
from ..research_analytics.market_feature_vector import get_feature_vector_service
from ..research_analytics.chart_data import get_chart_data_service


router = APIRouter(prefix="/api/trading", tags=["Trading Engine"])


async def _get_candles(symbol: str, timeframe: str, limit: int = 100):
    """Helper to fetch candle data."""
    chart_service = get_chart_data_service()
    chart_data = await chart_service.get_chart_data(
        symbol=symbol.upper().replace("USDT", ""),
        timeframe=timeframe.upper(),
        limit=limit
    )
    return chart_data.candles if chart_data else []


@router.get("/status")
async def trading_engine_status():
    """Health check for trading engine."""
    return {
        "ok": True,
        "module": "trading_engine",
        "version": "1.0",
        "components": {
            "entry_filter": "active",
            "position_sizer": "active",
            "stop_engine": "active",
            "tp_engine": "active",
            "state_engine": "active",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/decision/{symbol}/{timeframe}")
async def get_trading_decision(
    symbol: str,
    timeframe: str = "1H",
    limit: int = Query(default=100, ge=50, le=500),
) -> dict:
    """
    Get complete trading decision for symbol.
    """
    try:
        candles = await _get_candles(symbol, timeframe, limit)
        
        if not candles or len(candles) < 50:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data for {symbol}/{timeframe}"
            )
        
        engine = get_trading_engine()
        decision = engine.generate_decision(candles, symbol, timeframe)
        
        return decision.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state/{symbol}/{timeframe}")
async def get_market_state(
    symbol: str,
    timeframe: str = "1H",
    limit: int = Query(default=100, ge=50, le=500),
) -> dict:
    """
    Get current market state (regime detection).
    """
    try:
        candles = await _get_candles(symbol, timeframe, limit)
        
        if not candles or len(candles) < 30:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data for {symbol}/{timeframe}"
            )
        
        # Get feature vector for enhanced detection
        feature_service = get_feature_vector_service()
        feature_vector = feature_service.build_feature_vector(candles, symbol, timeframe)
        
        # Detect state
        state_engine = get_market_state_engine()
        state_result = state_engine.detect_state(
            candles,
            feature_vector={
                "trend_score": feature_vector.trend_score,
                "momentum_score": feature_vector.momentum_score,
                "breakout_score": feature_vector.breakout_score,
            }
        )
        
        return state_result.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entry-filter/{symbol}/{timeframe}")
async def evaluate_entry_filter(
    symbol: str,
    timeframe: str = "1H",
    limit: int = Query(default=100, ge=50, le=500),
) -> dict:
    """
    Evaluate entry conditions only.
    """
    try:
        candles = await _get_candles(symbol, timeframe, limit)
        
        if not candles or len(candles) < 50:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data for {symbol}/{timeframe}"
            )
        
        feature_service = get_feature_vector_service()
        feature_vector = feature_service.build_feature_vector(candles, symbol, timeframe)
        
        engine = get_trading_engine()
        entry_decision = engine.entry_filter.evaluate(feature_vector)
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "entry": entry_decision.model_dump(),
            "feature_vector": {
                "trend_score": feature_vector.trend_score,
                "momentum_score": feature_vector.momentum_score,
                "net_score": feature_vector.net_score,
                "confidence": feature_vector.confidence,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/position-size/{symbol}/{timeframe}")
async def calculate_position_size(
    symbol: str,
    timeframe: str = "1H",
    limit: int = Query(default=100, ge=50, le=500),
) -> dict:
    """
    Calculate position size multiplier.
    """
    try:
        candles = await _get_candles(symbol, timeframe, limit)
        
        if not candles or len(candles) < 50:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data for {symbol}/{timeframe}"
            )
        
        feature_service = get_feature_vector_service()
        feature_vector = feature_service.build_feature_vector(candles, symbol, timeframe)
        
        engine = get_trading_engine()
        size_decision = engine.position_sizer.calculate(feature_vector)
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "position_size": size_decision.model_dump(),
            "indicator_confidence": abs(feature_vector.net_score),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/full-analysis/{symbol}/{timeframe}")
async def get_full_trading_analysis(
    symbol: str,
    timeframe: str = "1H",
    limit: int = Query(default=100, ge=50, le=500),
) -> dict:
    """
    Get complete trading analysis including:
    - Market state
    - Trading decision  
    - Entry filter
    - Position size
    - Stop/TP levels
    - Feature vector
    - Indicator drivers
    """
    try:
        candles = await _get_candles(symbol, timeframe, limit)
        
        if not candles or len(candles) < 50:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data for {symbol}/{timeframe}"
            )
        
        # Get feature vector
        feature_service = get_feature_vector_service()
        feature_vector = feature_service.build_feature_vector(candles, symbol, timeframe)
        
        # Get market state
        state_engine = get_market_state_engine()
        market_state = state_engine.detect_state(
            candles,
            feature_vector={
                "trend_score": feature_vector.trend_score,
                "momentum_score": feature_vector.momentum_score,
                "breakout_score": feature_vector.breakout_score,
            }
        )
        
        # Get trading decision
        trading_engine = get_trading_engine()
        trading_decision = trading_engine.generate_decision(candles, symbol, timeframe)
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": candles[-1]["close"],
            
            "market_state": {
                "state": market_state.state.value,
                "confidence": market_state.confidence,
                "sub_states": market_state.sub_states,
                "trend_strength": market_state.trend_strength,
                "volatility_level": market_state.volatility_level,
                "recommended_indicators": market_state.recommended_indicators,
                "recommended_strategy": market_state.recommended_strategy,
                "reasoning": market_state.reasoning,
                "regime_confidence": market_state.regime_confidence,
                "regime_stability": market_state.regime_stability,
                "regime_outlook": market_state.regime_outlook,
            },
            
            "trading_decision": {
                "entry": trading_decision.entry.model_dump(),
                "position_size": trading_decision.position_size.model_dump(),
                "stop_loss": trading_decision.stop_loss.model_dump() if trading_decision.stop_loss else None,
                "take_profit": trading_decision.take_profit.model_dump() if trading_decision.take_profit else None,
                "explanation": trading_decision.explanation,
            },
            
            "feature_vector": {
                "trend_score": feature_vector.trend_score,
                "momentum_score": feature_vector.momentum_score,
                "volatility_score": feature_vector.volatility_score,
                "breakout_score": feature_vector.breakout_score,
                "net_score": feature_vector.net_score,
                "confidence": feature_vector.confidence,
                "agreement_ratio": feature_vector.agreement_ratio,
            },
            
            "indicator_drivers": trading_decision.indicator_summary,
            
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ═══════════════════════════════════════════════════════════════
# Signal Endpoints
# ═══════════════════════════════════════════════════════════════

@router.get("/signals/generate/{symbol}/{timeframe}")
async def generate_signal(
    symbol: str,
    timeframe: str = "1H",
    limit: int = Query(default=100, ge=50, le=500),
    save: bool = Query(default=True, description="Save signal to database"),
) -> dict:
    """
    Generate a trading signal for the symbol.
    
    Returns the signal if quality passes, or null if no valid signal.
    """
    try:
        candles = await _get_candles(symbol, timeframe, limit)
        
        if not candles or len(candles) < 50:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data for {symbol}/{timeframe}"
            )
        
        current_price = candles[-1]["close"]
        
        # Get feature vector
        feature_service = get_feature_vector_service()
        feature_vector = feature_service.build_feature_vector(candles, symbol, timeframe)
        
        # Get market state
        state_engine = get_market_state_engine()
        market_state = state_engine.detect_state(
            candles,
            feature_vector={
                "trend_score": feature_vector.trend_score,
                "momentum_score": feature_vector.momentum_score,
                "breakout_score": feature_vector.breakout_score,
            }
        )
        
        # Get trading decision
        trading_engine = get_trading_engine()
        trading_decision = trading_engine.generate_decision(candles, symbol, timeframe)
        
        # Generate signal
        signal_engine = get_signal_engine()
        signal = signal_engine.generate_signal(
            trading_decision=trading_decision.model_dump(),
            market_state=market_state.model_dump(),
            feature_vector={
                "trend_score": feature_vector.trend_score,
                "momentum_score": feature_vector.momentum_score,
                "volatility_score": feature_vector.volatility_score,
                "breakout_score": feature_vector.breakout_score,
                "net_score": feature_vector.net_score,
                "confidence": feature_vector.confidence,
            },
            symbol=symbol.upper(),
            timeframe=timeframe.upper(),
            current_price=current_price,
        )
        
        if signal is None:
            return {
                "signal": None,
                "reason": "No valid signal generated (conditions not met or confidence too low)",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        
        # Save to database if requested
        if save:
            storage = get_signal_storage()
            storage.save_signal(signal)
        
        # Get pending alerts
        alerts = signal_engine.get_pending_alerts()
        
        # Save alerts
        if save and alerts:
            for alert in alerts:
                storage.save_alert(alert)
        
        return {
            "signal": signal.model_dump(),
            "alerts": [a.model_dump() for a in alerts],
            "saved": save,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals")
async def get_signals(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    direction: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
) -> dict:
    """
    Get trading signals with optional filters.
    """
    try:
        storage = get_signal_storage()
        
        # Parse status
        status_enum = None
        if status:
            try:
                status_enum = SignalStatus(status.lower())
            except ValueError:
                pass
        
        # Parse direction
        direction_enum = None
        if direction:
            try:
                direction_enum = SignalDirection(direction.lower())
            except ValueError:
                pass
        
        signals = storage.get_signals(
            symbol=symbol.upper() if symbol else None,
            status=status_enum,
            direction=direction_enum,
            limit=limit,
            skip=skip,
        )
        
        return {
            "signals": [s.model_dump() for s in signals],
            "count": len(signals),
            "filters": {
                "symbol": symbol,
                "status": status,
                "direction": direction,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/active")
async def get_active_signals(
    symbol: Optional[str] = None,
) -> dict:
    """
    Get all active (non-closed) signals.
    """
    try:
        storage = get_signal_storage()
        signals = storage.get_active_signals(symbol=symbol.upper() if symbol else None)
        
        return {
            "signals": [s.model_dump() for s in signals],
            "count": len(signals),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# Performance Endpoints (BEFORE parameterized routes)
# ═══════════════════════════════════════════════════════════════

@router.get("/signals/stats")
async def get_signal_stats(
    symbol: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    """
    Get signal performance statistics.
    """
    try:
        storage = get_signal_storage()
        stats = storage.get_signal_stats(
            symbol=symbol.upper() if symbol else None,
            days=days,
        )
        
        return {
            "stats": stats,
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/{signal_id}")
async def get_signal_by_id(signal_id: str) -> dict:
    """
    Get a specific signal by ID.
    """
    try:
        storage = get_signal_storage()
        signal = storage.get_signal(signal_id)
        
        if not signal:
            raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")
        
        return {
            "signal": signal.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/signals/{signal_id}")
async def delete_signal(signal_id: str) -> dict:
    """
    Delete a signal.
    """
    try:
        storage = get_signal_storage()
        success = storage.delete_signal(signal_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")
        
        return {
            "deleted": True,
            "signal_id": signal_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/signals/{signal_id}/cancel")
async def cancel_signal(signal_id: str) -> dict:
    """
    Cancel an active signal.
    """
    try:
        storage = get_signal_storage()
        success = storage.update_signal_status(
            signal_id=signal_id,
            status=SignalStatus.CANCELLED,
            exit_reason="Manually cancelled",
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")
        
        return {
            "cancelled": True,
            "signal_id": signal_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# Alert Endpoints
# ═══════════════════════════════════════════════════════════════

@router.get("/alerts")
async def get_alerts(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    """
    Get trading alerts.
    """
    try:
        storage = get_signal_storage()
        alerts = storage.get_alerts(unread_only=unread_only, limit=limit)
        
        return {
            "alerts": [a.model_dump() for a in alerts],
            "count": len(alerts),
            "unread_only": unread_only,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/mark-read")
async def mark_alerts_read(
    alert_ids: List[str],
) -> dict:
    """
    Mark alerts as read.
    """
    try:
        storage = get_signal_storage()
        count = storage.mark_alerts_read(alert_ids)
        
        return {
            "marked_read": count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# Performance & Lifecycle Endpoints
# ═══════════════════════════════════════════════════════════════

@router.get("/performance")
async def get_performance(
    symbol: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    """
    Get comprehensive signal performance metrics.
    
    Returns:
    - Win rate, profit factor, average R:R
    - TP hit rates (TP1, TP2, TP3)
    - Performance by direction (long/short)
    - Performance by signal strength
    """
    try:
        lifecycle = get_lifecycle_engine()
        performance = lifecycle.calculate_performance(
            symbol=symbol.upper() if symbol else None,
            days=days,
        )
        
        return {
            "performance": performance.model_dump(),
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicator-quality")
async def get_indicator_quality(
    symbol: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    """
    Analyze indicator contribution to winning trades.
    
    Returns:
    - Best/worst performing indicator drivers
    - Win rates per indicator
    - Suggested weight adjustments
    """
    try:
        lifecycle = get_lifecycle_engine()
        report = lifecycle.analyze_indicator_quality(
            symbol=symbol.upper() if symbol else None,
            days=days,
        )
        
        return {
            "quality_report": report.model_dump(),
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outcomes")
async def get_signal_outcomes(
    symbol: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    """
    Get detailed outcomes for closed signals.
    """
    try:
        lifecycle = get_lifecycle_engine()
        outcomes = lifecycle.get_signal_outcomes(
            symbol=symbol.upper() if symbol else None,
            limit=limit,
        )
        
        return {
            "outcomes": [o.model_dump() for o in outcomes],
            "count": len(outcomes),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/signals/update-prices")
async def update_signals_with_prices(
    price_updates: Dict[str, float],
) -> dict:
    """
    Update all active signals with current prices.
    
    Body:
    {"BTC": 50000.0, "ETH": 3000.0, ...}
    
    This triggers TP/SL detection for all active signals.
    """
    try:
        lifecycle = get_lifecycle_engine()
        updated_signals, alerts = lifecycle.process_all_active_signals(price_updates)
        
        return {
            "signals_updated": len(updated_signals),
            "alerts_generated": len(alerts),
            "alerts": [a.model_dump() for a in alerts],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/signals/{signal_id}/invalidate")
async def invalidate_signal(
    signal_id: str,
    reason: str = Query(default="Market conditions changed"),
) -> dict:
    """
    Invalidate a signal when market conditions no longer support it.
    """
    try:
        lifecycle = get_lifecycle_engine()
        success = lifecycle.invalidate_signal(signal_id, reason)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Signal {signal_id} not found or already closed"
            )
        
        return {
            "invalidated": True,
            "signal_id": signal_id,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

