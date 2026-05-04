"""Soft fallback signal generator.

When no hard strategy triggers, generate a low-confidence directional signal
instead of returning nothing. This prevents the system from going completely silent.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def generate_soft_signal(
    symbol: str,
    candles: List[Dict[str, Any]],
    indicators: Dict[str, Any],
    regime: str
) -> Optional[Dict[str, Any]]:
    """
    Generate a soft fallback signal when no hard strategy triggers.
    
    Uses simple directional bias (EMA20 vs EMA50) with low confidence.
    Better to have a low-confidence signal than no signal at all.
    
    Args:
        symbol: Trading symbol
        candles: Price candles
        indicators: Computed indicators
        regime: Market regime
    
    Returns:
        Soft signal dict or None if insufficient data
    """
    if not candles or len(candles) < 30:
        return None
    
    close = float(candles[-1].get("close", 0.0))
    if close <= 0:
        return None
    
    atr = float(indicators.get("atr", 0.0))
    ema20 = float(indicators.get("ema20", close))
    ema50 = float(indicators.get("ema50", close))
    
    # Determine directional bias
    side = "LONG" if ema20 >= ema50 else "SHORT"
    
    # Use ATR for stop/target, or default to 1% of price
    if atr <= 0:
        atr = close * 0.01
    
    # Calculate levels
    if side == "LONG":
        stop = close - atr * 1.5
        target = close + atr * 2.0
    else:
        stop = close + atr * 1.5
        target = close - atr * 2.0
    
    signal = {
        "symbol": symbol,
        "strategy": "soft_fallback_v1",
        "side": side,
        "entry": close,
        "stop": stop,
        "target": target,
        "confidence": 0.46,  # Just above min_score threshold
        "reason": f"soft_fallback_in_{regime}",
        "meta": {
            "signals": [
                "No hard trigger found",
                f"Fallback {side} bias (EMA20 vs EMA50)",
                f"Regime: {regime}"
            ],
            "regime": regime,
            "fallback": True
        }
    }
    
    logger.debug(
        f"[SoftSignal] {symbol}: Generated {side} fallback signal "
        f"(no hard triggers in {regime} regime)"
    )
    
    return signal
