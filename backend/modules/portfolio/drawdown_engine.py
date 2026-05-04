"""
Drawdown Engine
===============

Tracks drawdown and determines throttle levels.

drawdown = (equity - peak) / peak
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class DrawdownEngine:
    """Drawdown tracking and throttling engine."""
    
    def __init__(self):
        self.max_drawdown_observed = 0.0
    
    def calculate(
        self,
        equity: float,
        equity_peak: float
    ) -> Dict[str, Any]:
        """
        Calculate drawdown state and throttle level.
        
        Args:
            equity: Current equity
            equity_peak: Highest equity reached
        
        Returns:
            Drawdown state dictionary
        """
        # Calculate current drawdown
        if equity_peak > 0:
            current_dd = ((equity - equity_peak) / equity_peak)
        else:
            current_dd = 0.0
        
        # Track max drawdown
        if current_dd < self.max_drawdown_observed:
            self.max_drawdown_observed = current_dd
            logger.warning(f"[DrawdownEngine] New max drawdown: {current_dd*100:.2f}%")
        
        # Determine throttle level
        if current_dd >= -0.02:
            throttle_level = "NONE"
            can_trade = True
            can_open_new = True
        elif current_dd >= -0.05:
            throttle_level = "LOW"
            can_trade = True
            can_open_new = True
        elif current_dd >= -0.10:
            throttle_level = "MEDIUM"
            can_trade = True
            can_open_new = True  # But size will be reduced by allocator
        elif current_dd >= -0.15:
            throttle_level = "HIGH"
            can_trade = True
            can_open_new = False  # Block new entries
        else:
            throttle_level = "CRITICAL"
            can_trade = False  # Hard stop
            can_open_new = False
        
        return {
            "current_dd": round(current_dd, 4),
            "current_dd_pct": round(current_dd * 100, 2),
            "max_dd": round(self.max_drawdown_observed, 4),
            "max_dd_pct": round(self.max_drawdown_observed * 100, 2),
            "throttle_level": throttle_level,
            "can_trade": can_trade,
            "can_open_new": can_open_new,
        }


# Singleton instance
_engine: DrawdownEngine = None


def get_drawdown_engine() -> DrawdownEngine:
    """Get or create singleton drawdown engine."""
    global _engine
    if _engine is None:
        _engine = DrawdownEngine()
    return _engine
