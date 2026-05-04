"""Adaptive thresholds based on market regime and volatility.

Key innovation: Thresholds adjust dynamically instead of being static.
This prevents Signal Engine from going silent in different market conditions.
"""

from typing import Dict, Any


def build_thresholds(regime: str, volatility: float) -> Dict[str, Any]:
    """
    Build adaptive thresholds based on market regime and realized volatility.
    
    Args:
        regime: "trend" | "chop" | "high_vol"
        volatility: Realized volatility (e.g., 0.025 = 2.5%)
    
    Returns:
        Dict with thresholds for each strategy
    """
    vol = float(volatility or 0.0)
    
    # Base thresholds (moderate)
    thresholds = {
        "trend": {
            "momentum_min": 0.40,
            "ema_spread_min": 0.0020,  # 0.2%
        },
        "breakout": {
            "breakout_buffer": 0.0030,  # 0.3% above resistance
            "volume_boost_min": 1.05,   # 5% volume increase
        },
        "meanrev": {
            "rsi_low": 35.0,
            "rsi_high": 65.0,
            "dev_from_sma": 0.010,  # 1% deviation
        },
    }
    
    # Regime-based adjustments
    if regime == "trend":
        # Trend regime: easier trend triggers, harder mean reversion
        thresholds["trend"]["momentum_min"] = 0.35
        thresholds["trend"]["ema_spread_min"] = 0.0015
        thresholds["breakout"]["breakout_buffer"] = 0.0020
    
    elif regime == "chop":
        # Chop regime: easier mean reversion, harder trend
        thresholds["meanrev"]["rsi_low"] = 40.0
        thresholds["meanrev"]["rsi_high"] = 60.0
        thresholds["meanrev"]["dev_from_sma"] = 0.0075
        thresholds["trend"]["momentum_min"] = 0.55  # harder
    
    elif regime == "high_vol":
        # High vol: easier breakout, wider RSI bands
        thresholds["breakout"]["breakout_buffer"] = 0.0010
        thresholds["breakout"]["volume_boost_min"] = 1.00
        thresholds["meanrev"]["rsi_low"] = 30.0
        thresholds["meanrev"]["rsi_high"] = 70.0
    
    # Volatility-based adjustments
    if vol > 0.04:  # High vol (>4%)
        thresholds["breakout"]["breakout_buffer"] *= 0.7  # easier breakouts
        thresholds["trend"]["ema_spread_min"] *= 1.1     # harder trends
    
    if vol < 0.01:  # Low vol (<1%)
        thresholds["meanrev"]["dev_from_sma"] *= 0.8     # easier mean rev
        thresholds["breakout"]["breakout_buffer"] *= 1.2  # harder breakouts
    
    return thresholds
