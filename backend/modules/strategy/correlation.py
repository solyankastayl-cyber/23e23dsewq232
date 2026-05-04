"""Correlation Penalty — V3 Risk Management

Penalizes adding correlated positions to the portfolio.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def correlation_penalty(
    symbol: str,
    open_positions: List[Dict[str, Any]],
    default_penalty: float = 0.85
) -> float:
    """
    Calculate correlation penalty for adding this symbol.
    
    Simple heuristic:
    - If same symbol already in portfolio → heavy penalty (0.3)
    - If same asset class (e.g., both crypto) → light penalty (0.85)
    - Otherwise → no penalty (1.0)
    
    Args:
        symbol: Candidate symbol
        open_positions: Currently open positions
        default_penalty: Default penalty factor
    
    Returns:
        Penalty multiplier (0..1), where 1 = no penalty
    """
    if not open_positions:
        return 1.0
    
    # Check for exact symbol match
    for pos in open_positions:
        if pos.get("symbol") == symbol:
            logger.debug(f"[Correlation] Same symbol {symbol} already in portfolio → penalty 0.3")
            return 0.3
    
    # For now, apply light default penalty
    # (In V4, this will use actual correlation matrix)
    return default_penalty
