"""Trend Strategy V2 — Adaptive EMA Cross + Momentum

Key improvements:
- Returns {triggered, reason, signal} instead of signal|None
- Uses adaptive thresholds based on regime
- Provides detailed rejection reasons for debugging
"""

from modules.signal_engine.signal_models import TradingSignal
from modules.signal_engine.indicators import ema, atr, momentum, realized_volatility
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def evaluate_trend(symbol: str, timeframe: str, candles: list, thresholds: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate trend signal with adaptive thresholds.
    
    Returns:
        {
            "triggered": bool,
            "reason": str,  # Why it triggered or didn't trigger
            "signal": TradingSignal | None
        }
    """
    if not candles or len(candles) < 50:
        return {
            "triggered": False,
            "reason": f"not_enough_data_{len(candles)}_candles",
            "signal": None
        }
    
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]

    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    atr_val = atr(highs, lows, closes, 14)
    mom = momentum(closes, 10)
    vol = realized_volatility(closes, 20)

    if not ema20 or not ema50 or not atr_val or mom is None:
        return {
            "triggered": False,
            "reason": "invalid_indicators",
            "signal": None
        }

    price = closes[-1]
    
    # Get adaptive thresholds
    min_momentum = float(thresholds.get("trend", {}).get("momentum_min", 0.40))
    min_ema_spread = float(thresholds.get("trend", {}).get("ema_spread_min", 0.0020))
    
    ema_spread = abs(ema20 - ema50) / max(price, 1e-9)
    
    # LONG signal
    if price > ema20 and ema20 > ema50:
        # Check momentum threshold
        if mom <= min_momentum / 100:  # Convert to decimal
            return {
                "triggered": False,
                "reason": f"momentum_too_low_{mom:.4f}_needs_{min_momentum/100:.4f}",
                "signal": None
            }
        
        # Check EMA spread
        if ema_spread < min_ema_spread:
            return {
                "triggered": False,
                "reason": f"ema_spread_too_small_{ema_spread:.4f}_needs_{min_ema_spread:.4f}",
                "signal": None
            }
        
        # Trigger LONG
        entry = price
        stop = price - atr_val * 1.5
        target = price + atr_val * 3.0
        confidence = min(0.55 + abs(mom) * 5, 0.92)

        signal = TradingSignal(
            symbol=symbol,
            timeframe=timeframe,
            direction="LONG",
            strategy="trend_v2",
            confidence=confidence,
            entry=entry,
            stop=stop,
            target=target,
            reason=f"trend_up price>{ema20:.2f}>{ema50:.2f}, momentum={mom:.4f}",
            asset_vol=vol,
            metadata={
                "ema20": ema20,
                "ema50": ema50,
                "atr": atr_val,
                "momentum": mom,
                "ema_spread": ema_spread,
                "signals": [
                    f"EMA20 ({ema20:.2f}) above EMA50 ({ema50:.2f})",
                    f"Momentum {mom:.4f} confirmed",
                    f"EMA spread {ema_spread:.4f}"
                ]
            },
        )
        
        logger.debug(f"[TrendV2] {symbol}: LONG triggered (mom={mom:.4f}, spread={ema_spread:.4f})")
        
        return {
            "triggered": True,
            "reason": "trend_long",
            "signal": signal
        }
    
    # SHORT signal
    elif price < ema20 and ema20 < ema50:
        # Check momentum threshold (negative)
        if mom >= -min_momentum / 100:
            return {
                "triggered": False,
                "reason": f"momentum_not_negative_enough_{mom:.4f}",
                "signal": None
            }
        
        # Check EMA spread
        if ema_spread < min_ema_spread:
            return {
                "triggered": False,
                "reason": f"ema_spread_too_small_{ema_spread:.4f}",
                "signal": None
            }
        
        # Trigger SHORT
        entry = price
        stop = price + atr_val * 1.5
        target = price - atr_val * 3.0
        confidence = min(0.55 + abs(mom) * 5, 0.92)

        signal = TradingSignal(
            symbol=symbol,
            timeframe=timeframe,
            direction="SHORT",
            strategy="trend_v2",
            confidence=confidence,
            entry=entry,
            stop=stop,
            target=target,
            reason=f"trend_down price<{ema20:.2f}<{ema50:.2f}, momentum={mom:.4f}",
            asset_vol=vol,
            metadata={
                "ema20": ema20,
                "ema50": ema50,
                "atr": atr_val,
                "momentum": mom,
                "ema_spread": ema_spread,
                "signals": [
                    f"EMA20 ({ema20:.2f}) below EMA50 ({ema50:.2f})",
                    f"Momentum {mom:.4f} confirmed",
                    f"EMA spread {ema_spread:.4f}"
                ]
            },
        )
        
        logger.debug(f"[TrendV2] {symbol}: SHORT triggered (mom={mom:.4f}, spread={ema_spread:.4f})")
        
        return {
            "triggered": True,
            "reason": "trend_short",
            "signal": signal
        }
    
    # No trend detected
    if ema20 <= ema50:
        return {
            "triggered": False,
            "reason": f"ema20_below_ema50_{ema20:.2f}_vs_{ema50:.2f}",
            "signal": None
        }
    else:
        return {
            "triggered": False,
            "reason": f"price_below_ema20_{price:.2f}_vs_{ema20:.2f}",
            "signal": None
        }


# Legacy wrapper for backward compatibility
def generate_trend_signal(symbol, timeframe, candles):
    """Legacy wrapper - returns signal or None"""
    # Use default thresholds if not provided
    default_thresholds = {
        "trend": {
            "momentum_min": 0.40,
            "ema_spread_min": 0.0020
        }
    }
    result = evaluate_trend(symbol, timeframe, candles, default_thresholds)
    return result.get("signal")
