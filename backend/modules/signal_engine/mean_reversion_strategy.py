"""Mean Reversion Strategy V2 — Adaptive RSI + SMA Deviation

Key improvements:
- Returns {triggered, reason, signal} for debugging
- Uses adaptive RSI thresholds based on regime
- Adaptive deviation threshold
- Detailed rejection reasons
"""

from modules.signal_engine.signal_models import TradingSignal
from modules.signal_engine.indicators import sma, rsi, atr, realized_volatility
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def evaluate_mean_reversion(
    symbol: str,
    timeframe: str,
    candles: list,
    thresholds: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluate mean reversion signal with adaptive thresholds.
    
    Returns:
        {
            "triggered": bool,
            "reason": str,
            "signal": TradingSignal | None
        }
    """
    if not candles or len(candles) < 30:
        return {
            "triggered": False,
            "reason": f"not_enough_data_{len(candles)}_candles",
            "signal": None
        }

    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]

    ma20 = sma(closes, 20)
    rsi14 = rsi(closes, 14)
    atr_val = atr(highs, lows, closes, 14)
    vol = realized_volatility(closes, 20)

    if not ma20 or rsi14 is None or not atr_val or ma20 <= 0:
        return {
            "triggered": False,
            "reason": "invalid_indicators",
            "signal": None
        }

    price = closes[-1]
    deviation = (price - ma20) / ma20
    
    # Get adaptive thresholds
    rsi_low = float(thresholds.get("meanrev", {}).get("rsi_low", 35.0))
    rsi_high = float(thresholds.get("meanrev", {}).get("rsi_high", 65.0))
    min_deviation = float(thresholds.get("meanrev", {}).get("dev_from_sma", 0.010))

    # Oversold → LONG
    if rsi14 < rsi_low:
        # Check deviation
        if abs(deviation) < min_deviation:
            return {
                "triggered": False,
                "reason": f"deviation_too_small_{abs(deviation):.4f}_needs_{min_deviation:.4f}",
                "signal": None
            }
        
        entry = price
        stop = price - atr_val * 1.2
        target = ma20
        confidence = min(0.88, 0.52 + (max(0.0, (35 - rsi14)) / 35.0) * 0.25)

        signal = TradingSignal(
            symbol=symbol,
            timeframe=timeframe,
            direction="LONG",
            strategy="meanrev_v2",
            confidence=confidence,
            entry=entry,
            stop=stop,
            target=target,
            reason=f"oversold rsi={rsi14:.1f}, deviation={deviation:.3f}",
            asset_vol=vol,
            metadata={
                "sma20": ma20,
                "rsi14": rsi14,
                "atr": atr_val,
                "deviation": deviation,
                "signals": [
                    f"RSI {rsi14:.2f} oversold (< {rsi_low})",
                    f"Deviation {deviation:.4f} from SMA20 ({ma20:.2f})",
                    "Mean reversion setup"
                ]
            },
        )
        
        logger.debug(f"[MeanRevV2] {symbol}: LONG triggered (rsi={rsi14:.2f}, dev={deviation:.4f})")
        
        return {
            "triggered": True,
            "reason": "meanrev_long",
            "signal": signal
        }

    # Overbought → SHORT
    if rsi14 > rsi_high:
        # Check deviation
        if abs(deviation) < min_deviation:
            return {
                "triggered": False,
                "reason": f"deviation_too_small_{abs(deviation):.4f}",
                "signal": None
            }
        
        entry = price
        stop = price + atr_val * 1.2
        target = ma20
        confidence = min(0.88, 0.52 + (max(0.0, (rsi14 - 65)) / 35.0) * 0.25)

        signal = TradingSignal(
            symbol=symbol,
            timeframe=timeframe,
            direction="SHORT",
            strategy="meanrev_v2",
            confidence=confidence,
            entry=entry,
            stop=stop,
            target=target,
            reason=f"overbought rsi={rsi14:.1f}, deviation={deviation:.3f}",
            asset_vol=vol,
            metadata={
                "sma20": ma20,
                "rsi14": rsi14,
                "atr": atr_val,
                "deviation": deviation,
                "signals": [
                    f"RSI {rsi14:.2f} overbought (> {rsi_high})",
                    f"Deviation {deviation:.4f} from SMA20 ({ma20:.2f})",
                    "Mean reversion setup"
                ]
            },
        )
        
        logger.debug(f"[MeanRevV2] {symbol}: SHORT triggered (rsi={rsi14:.2f}, dev={deviation:.4f})")
        
        return {
            "triggered": True,
            "reason": "meanrev_short",
            "signal": signal
        }

    # No mean reversion signal
    return {
        "triggered": False,
        "reason": f"rsi_neutral_{rsi14:.2f}_between_{rsi_low}_and_{rsi_high}",
        "signal": None
    }


# Legacy wrapper
def generate_mean_reversion_signal(symbol, timeframe, candles):
    """Legacy wrapper - returns signal or None"""
    default_thresholds = {
        "meanrev": {
            "rsi_low": 35.0,
            "rsi_high": 65.0,
            "dev_from_sma": 0.010
        }
    }
    result = evaluate_mean_reversion(symbol, timeframe, candles, default_thresholds)
    return result.get("signal")
