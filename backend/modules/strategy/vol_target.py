"""Volatility Targeting — Dynamic risk adjustment

Adjust position sizes based on asset volatility.
"""

import logging

logger = logging.getLogger(__name__)


def vol_target_multiplier(
    asset_vol: float,
    target_vol: float = 0.15,
    min_mult: float = 0.4,
    max_mult: float = 1.5
) -> float:
    """
    Calculate volatility targeting multiplier.
    
    Formula: multiplier = target_vol / asset_vol
    
    High volatility → smaller positions
    Low volatility → larger positions
    
    Args:
        asset_vol: Asset volatility (as decimal, e.g., 0.30 = 30%)
        target_vol: Target portfolio volatility (default 15%)
        min_mult: Minimum multiplier (floor)
        max_mult: Maximum multiplier (cap)
    
    Returns:
        Multiplier to apply to position size
    """
    if asset_vol <= 0:
        return 1.0
    
    mult = target_vol / asset_vol
    
    # Clamp to safe range
    return max(min_mult, min(mult, max_mult))


def calculate_atr_volatility(candles: list, period: int = 14) -> float:
    """
    Calculate ATR-based volatility.
    
    Returns volatility as percentage of price.
    
    Args:
        candles: List of candle dicts with 'high', 'low', 'close'
        period: ATR period (default 14)
    
    Returns:
        Volatility as decimal (0.02 = 2%)
    """
    if len(candles) < period:
        return 0.02  # Default 2%
    
    recent = candles[-period:]
    
    # True range
    tr_sum = 0.0
    for c in recent:
        tr = c.get('high', 0) - c.get('low', 0)
        tr_sum += tr
    
    atr = tr_sum / period
    
    # As % of price
    avg_price = sum(c.get('close', 0) for c in recent) / period
    
    if avg_price == 0:
        return 0.02
    
    volatility = atr / avg_price
    
    return max(0.005, min(volatility, 0.10))  # Clamp 0.5% - 10%


def regime_vol_multiplier(regime: str) -> float:
    """
    Get volatility multiplier based on market regime.
    
    Args:
        regime: Market regime ('trend', 'chop', 'high_vol')
    
    Returns:
        Multiplier for risk sizing
    """
    if regime == 'high_vol':
        return 0.5  # Cut risk in half
    elif regime == 'trend':
        return 1.2  # Increase slightly
    elif regime == 'chop':
        return 0.8  # Reduce slightly
    
    return 1.0
