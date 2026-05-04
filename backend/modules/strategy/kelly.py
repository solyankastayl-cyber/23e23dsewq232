"""Kelly Sizing — Fund-level capital allocation

Fractional Kelly formula for safe position sizing.
"""

import logging

logger = logging.getLogger(__name__)


def raw_kelly(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Calculate raw Kelly fraction.
    
    Formula: f* = W - (1 - W) / R
    where W = win rate, R = avg_win / avg_loss
    
    Args:
        win_rate: Probability of win (0..1)
        avg_win: Average profit per winning trade
        avg_loss: Average loss per losing trade (positive value)
    
    Returns:
        Kelly fraction (0..1)
    """
    if avg_win <= 0 or avg_loss <= 0:
        return 0.0
    
    r = avg_win / avg_loss
    if r <= 0:
        return 0.0
    
    kelly = win_rate - ((1.0 - win_rate) / r)
    return max(0.0, kelly)


def fractional_kelly(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    fraction: float = 0.25,
    cap: float = 0.03
) -> float:
    """
    Calculate fractional Kelly (safer than full Kelly).
    
    Args:
        win_rate: Probability of win
        avg_win: Average profit per winning trade
        avg_loss: Average loss per losing trade (positive)
        fraction: Kelly fraction to use (0.1-0.3 recommended)
        cap: Maximum allowed risk per trade
    
    Returns:
        Safe Kelly fraction (0..cap)
    """
    k_raw = raw_kelly(win_rate, avg_win, avg_loss)
    k_fractional = k_raw * fraction
    
    # Cap at maximum
    return max(0.0, min(k_fractional, cap))


def kelly_multiplier(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    base_risk: float = 0.01,
    fraction: float = 0.25
) -> float:
    """
    Calculate Kelly multiplier for base risk.
    
    Returns multiplier to apply to base_risk:
    - Strong strategy: multiplier > 1.0
    - Weak strategy: multiplier < 1.0
    
    Args:
        win_rate: Win rate (0..1)
        avg_win: Average win
        avg_loss: Average loss (positive)
        base_risk: Base risk per trade (default 1%)
        fraction: Kelly fraction
    
    Returns:
        Multiplier (0.5 - 2.0)
    """
    kelly = fractional_kelly(win_rate, avg_win, avg_loss, fraction)
    
    if base_risk <= 0:
        return 1.0
    
    multiplier = kelly / base_risk
    
    # Clamp to reasonable range
    return max(0.5, min(multiplier, 2.0))
