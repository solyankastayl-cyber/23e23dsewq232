"""Market Regime Detection

Week 4: Strategy Allocator V2

Regimes:
- trend: Strong directional move
- chop: Range-bound, low trend
- high_vol: Elevated volatility
"""

from typing import Dict, Any


def detect_regime(market: Dict[str, Any]) -> str:
    """
    Detect current market regime.
    
    Args:
        market: {
            "trend_strength": float (0..1),
            "volatility": float (0.01 = 1%),
            "volume_ratio": float (vs avg)
        }
    
    Returns:
        "trend" | "chop" | "high_vol"
    """
    trend_strength = market.get("trend_strength", 0.5)
    volatility = market.get("volatility", 0.02)
    
    # High volatility overrides other regimes
    if volatility > 0.04:  # 4% volatility
        return "high_vol"
    
    # Strong trend
    if trend_strength > 0.6:
        return "trend"
    
    # Default: choppy/range
    return "chop"


def calculate_trend_strength(candles: list) -> float:
    """
    Calculate trend strength from candles.
    
    Simple implementation: ADX proxy
    
    Returns:
        0..1 (0 = no trend, 1 = strong trend)
    """
    if len(candles) < 14:
        return 0.5
    
    # Simple: count directional bars
    up_bars = sum(1 for c in candles[-14:] if c.get("close", 0) > c.get("open", 0))
    down_bars = 14 - up_bars
    
    # Trend strength: how lopsided is it?
    strength = abs(up_bars - down_bars) / 14
    
    return strength


def calculate_volatility(candles: list) -> float:
    """
    Calculate volatility (simple: ATR as % of price).
    
    Returns:
        Volatility as decimal (0.02 = 2%)
    """
    if len(candles) < 14:
        return 0.02
    
    recent = candles[-14:]
    
    # Average true range
    tr_sum = sum(
        c.get("high", 0) - c.get("low", 0)
        for c in recent
    )
    atr = tr_sum / 14
    
    # As % of price
    avg_price = sum(c.get("close", 0) for c in recent) / 14
    
    if avg_price == 0:
        return 0.02
    
    volatility = atr / avg_price
    
    return volatility
