"""Signal Engine API Routes"""

import logging
from fastapi import APIRouter
from typing import Dict, Any

from modules.signal_engine.signal_engine import SignalEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/signals", tags=["signals"])
signal_engine = SignalEngine()


@router.get("/debug")
async def debug_signals(symbol: str = "BTCUSDT", timeframe: str = "4h") -> Dict[str, Any]:
    """
    DEBUG endpoint: Shows why strategies triggered or didn't trigger.
    
    Critical for operational visibility. Returns detailed breakdown:
    - Candles count
    - Market regime
    - Each strategy's trigger status + rejection reason
    - Soft fallback usage
    
    Args:
        symbol: Trading symbol
        timeframe: Timeframe
    
    Returns:
        Full debug breakdown
    """
    try:
        from modules.market_data_live import get_market_data_service
        from modules.signal_engine.trend_strategy import evaluate_trend
        from modules.signal_engine.breakout_strategy import evaluate_breakout
        from modules.signal_engine.mean_reversion_strategy import evaluate_mean_reversion
        from modules.signal_engine.adaptive_thresholds import build_thresholds
        from modules.signal_engine.soft_signal import generate_soft_signal
        from modules.strategy.regime import detect_regime, calculate_volatility
        
        market_data_service = get_market_data_service()
        candles = await market_data_service.get_candles(symbol, timeframe=timeframe, limit=120)
        
        if not candles or len(candles) < 30:
            return {
                "ok": False,
                "error": "no_candles_or_insufficient_data",
                "symbol": symbol,
                "candles_count": len(candles) if candles else 0
            }
        
        # Detect regime
        market_data = {"volatility": calculate_volatility(candles), "trend_strength": 0.6}
        regime = detect_regime(market_data)
        volatility = calculate_volatility(candles)
        
        # Build thresholds
        thresholds = build_thresholds(regime, volatility)
        
        # Evaluate each strategy
        trend_result = evaluate_trend(symbol, timeframe, candles, thresholds)
        breakout_result = evaluate_breakout(symbol, timeframe, candles, thresholds)
        meanrev_result = evaluate_mean_reversion(symbol, timeframe, candles, thresholds)
        
        # Collect signals
        signals = []
        for result in [trend_result, breakout_result, meanrev_result]:
            if result.get("triggered") and result.get("signal"):
                sig = result["signal"]
                signals.append({
                    "strategy": sig.strategy,
                    "side": sig.direction,
                    "entry": sig.entry,
                    "stop": sig.stop,
                    "target": sig.target,
                    "confidence": sig.confidence,
                    "reason": sig.reason
                })
        
        # Check soft fallback
        soft_fallback_used = False
        if not signals:
            from modules.signal_engine.indicators import ema, atr as compute_atr
            closes = [c["close"] for c in candles]
            highs = [c["high"] for c in candles]
            lows = [c["low"] for c in candles]
            
            indicators = {
                "ema20": ema(closes, 20) or closes[-1],
                "ema50": ema(closes, 50) or closes[-1],
                "atr": compute_atr(highs, lows, closes, 14) or (closes[-1] * 0.01),
            }
            
            soft = generate_soft_signal(symbol, candles, indicators, regime)
            if soft:
                signals.append(soft)
                soft_fallback_used = True
        
        return {
            "ok": True,
            "data": {
                "symbol": symbol,
                "candles_count": len(candles),
                "last_price": candles[-1]["close"],
                "regime": regime,
                "volatility": round(volatility, 4),
                "thresholds": thresholds,
                "strategies": {
                    "trend": {
                        "triggered": trend_result.get("triggered"),
                        "reason": trend_result.get("reason")
                    },
                    "breakout": {
                        "triggered": breakout_result.get("triggered"),
                        "reason": breakout_result.get("reason")
                    },
                    "mean_reversion": {
                        "triggered": meanrev_result.get("triggered"),
                        "reason": meanrev_result.get("reason")
                    }
                },
                "signals": signals,
                "soft_fallback_used": soft_fallback_used
            }
        }
    except Exception as e:
        logger.error(f"[SignalsDebug] Error: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e)
        }


@router.get("/preview")
async def preview_signals(symbol: str = "BTCUSDT", timeframe: str = "4h") -> Dict[str, Any]:
    """
    Preview signals for a given symbol using REAL market data.
    
    Args:
        symbol: Trading symbol (default: BTCUSDT)
        timeframe: Timeframe (default: 4h)
    
    Returns:
        List of trading signals
    """
    try:
        # Get REAL candles from market data service
        from modules.market_data_live import get_market_data_service
        
        market_data_service = get_market_data_service()
        candles = await market_data_service.get_candles(symbol, timeframe=timeframe, limit=120)
        
        if not candles:
            return {
                "ok": False,
                "error": f"No candles for {symbol}",
                "count": 0,
                "signals": []
            }
        
        # Generate signals
        signals = signal_engine.run(symbol, timeframe, candles)
        
        return {
            "ok": True,
            "count": len(signals),
            "signals": [
                {
                    "symbol": s.symbol,
                    "timeframe": s.timeframe,
                    "direction": s.direction,
                    "strategy": s.strategy,
                    "confidence": round(s.confidence, 4),
                    "entry": round(s.entry, 2),
                    "stop": round(s.stop, 2),
                    "target": round(s.target, 2),
                    "reason": s.reason,
                    "asset_vol": round(s.asset_vol, 4),
                }
                for s in signals
            ],
        }
    
    except Exception as e:
        logger.error(f"[SignalEngine API] Error: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e),
            "count": 0,
            "signals": []
        }
