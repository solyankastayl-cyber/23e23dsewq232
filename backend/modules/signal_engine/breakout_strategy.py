"""Breakout Strategy V2 — Adaptive Range Breakout + Volume Confirmation

Key improvements:
- Returns {triggered, reason, signal} for debugging
- Uses adaptive breakout buffer based on regime/volatility
- Includes volume confirmation
- Detailed rejection reasons
"""

from modules.signal_engine.signal_models import TradingSignal
from modules.signal_engine.indicators import atr, realized_volatility
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def evaluate_breakout(
    symbol: str,
    timeframe: str,
    candles: list,
    thresholds: Dict[str, Any],
    lookback: int = 20
) -> Dict[str, Any]:
    """
    Evaluate breakout signal with adaptive thresholds.
    
    Returns:
        {
            "triggered": bool,
            "reason": str,
            "signal": TradingSignal | None
        }
    """
    if not candles or len(candles) < lookback + 2:
        return {
            "triggered": False,
            "reason": f"not_enough_data_{len(candles)}_candles_need_{lookback+2}",
            "signal": None
        }

    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    volumes = [c.get("volume", 0) for c in candles]

    price = closes[-1]
    prev_range_high = max(highs[-lookback-1:-1])
    prev_range_low = min(lows[-lookback-1:-1])

    atr_val = atr(highs, lows, closes, 14)
    vol = realized_volatility(closes, 20)

    if not atr_val or atr_val <= 0:
        return {
            "triggered": False,
            "reason": "invalid_atr",
            "signal": None
        }
    
    # Get adaptive thresholds
    breakout_buffer = float(thresholds.get("breakout", {}).get("breakout_buffer", 0.0030))
    volume_boost_min = float(thresholds.get("breakout", {}).get("volume_boost_min", 1.05))
    
    # Calculate volume confirmation
    avg_volume = sum(volumes[-10:-1]) / max(len(volumes[-10:-1]), 1) if len(volumes) >= 10 else 1
    curr_volume = volumes[-1] if volumes else 0
    volume_ratio = curr_volume / max(avg_volume, 1e-9)
    
    # Breakout UP
    breakout_level_up = prev_range_high * (1.0 + breakout_buffer)
    if price > breakout_level_up:
        # Check volume confirmation
        if volume_ratio < volume_boost_min:
            return {
                "triggered": False,
                "reason": f"volume_not_confirmed_{volume_ratio:.2f}_needs_{volume_boost_min:.2f}",
                "signal": None
            }
        
        entry = price
        stop = prev_range_high - atr_val * 0.8
        target = price + atr_val * 3.5
        confidence = min(0.92, 0.58 + min(volume_ratio - 1.0, 1.0) * 0.12)

        signal = TradingSignal(
            symbol=symbol,
            timeframe=timeframe,
            direction="LONG",
            strategy="breakout_v2",
            confidence=confidence,
            entry=entry,
            stop=stop,
            target=target,
            reason=f"breakout_up over {prev_range_high:.2f} (buffer={breakout_buffer:.4f})",
            asset_vol=vol,
            metadata={
                "range_high": prev_range_high,
                "breakout_level": breakout_level_up,
                "atr": atr_val,
                "volume_ratio": volume_ratio,
                "signals": [
                    f"Breakout above {prev_range_high:.2f}",
                    f"Volume ratio {volume_ratio:.2f}x",
                    f"ATR {atr_val:.2f}"
                ]
            },
        )
        
        logger.debug(f"[BreakoutV2] {symbol}: LONG triggered (vol_ratio={volume_ratio:.2f})")
        
        return {
            "triggered": True,
            "reason": "breakout_long",
            "signal": signal
        }
    
    # Breakout DOWN
    breakout_level_down = prev_range_low * (1.0 - breakout_buffer)
    if price < breakout_level_down:
        # Check volume confirmation
        if volume_ratio < volume_boost_min:
            return {
                "triggered": False,
                "reason": f"volume_not_confirmed_{volume_ratio:.2f}",
                "signal": None
            }
        
        entry = price
        stop = prev_range_low + atr_val * 0.8
        target = price - atr_val * 3.5
        confidence = min(0.92, 0.58 + min(volume_ratio - 1.0, 1.0) * 0.12)

        signal = TradingSignal(
            symbol=symbol,
            timeframe=timeframe,
            direction="SHORT",
            strategy="breakout_v2",
            confidence=confidence,
            entry=entry,
            stop=stop,
            target=target,
            reason=f"breakout_down under {prev_range_low:.2f}",
            asset_vol=vol,
            metadata={
                "range_low": prev_range_low,
                "breakout_level": breakout_level_down,
                "atr": atr_val,
                "volume_ratio": volume_ratio,
                "signals": [
                    f"Breakout below {prev_range_low:.2f}",
                    f"Volume ratio {volume_ratio:.2f}x",
                    f"ATR {atr_val:.2f}"
                ]
            },
        )
        
        logger.debug(f"[BreakoutV2] {symbol}: SHORT triggered (vol_ratio={volume_ratio:.2f})")
        
        return {
            "triggered": True,
            "reason": "breakout_short",
            "signal": signal
        }
    
    # No breakout
    if price > prev_range_high and price <= breakout_level_up:
        return {
            "triggered": False,
            "reason": f"near_breakout_but_buffer_not_met_{price:.2f}_vs_{breakout_level_up:.2f}",
            "signal": None
        }
    elif price < prev_range_low and price >= breakout_level_down:
        return {
            "triggered": False,
            "reason": f"near_breakdown_but_buffer_not_met_{price:.2f}_vs_{breakout_level_down:.2f}",
            "signal": None
        }
    else:
        return {
            "triggered": False,
            "reason": f"price_in_range_{price:.2f}_between_{prev_range_low:.2f}_and_{prev_range_high:.2f}",
            "signal": None
        }


# Legacy wrapper
def generate_breakout_signal(symbol, timeframe, candles, lookback=20):
    """Legacy wrapper - returns signal or None"""
    default_thresholds = {
        "breakout": {
            "breakout_buffer": 0.0030,
            "volume_boost_min": 1.05
        }
    }
    result = evaluate_breakout(symbol, timeframe, candles, default_thresholds, lookback)
    return result.get("signal")
