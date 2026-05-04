"""
Pattern Lifecycle Manager
=========================
Manages pattern state transitions: forming → active → broken/invalidated/expired
"""

from __future__ import annotations

from typing import Any, Dict, List
from .pattern_candidate import PatternCandidate


class PatternLifecycleManager:
    """Evaluates and updates pattern lifecycle state."""
    
    def evaluate(
        self,
        candidate: PatternCandidate,
        candles: List[Dict[str, Any]],
        structure_context: Dict[str, Any],
    ) -> None:
        """
        Evaluate pattern state based on current market.
        
        Updates candidate.state in place.
        """
        if not candles:
            return
        
        current_price = float(candles[-1]["close"])
        current_high = float(candles[-1]["high"])
        current_low = float(candles[-1]["low"])
        
        # 1. Check invalidation by level breach
        if candidate.invalidation_level is not None:
            if candidate.direction_bias == "bullish":
                # Bullish pattern invalidated if price drops below invalidation
                if current_low < candidate.invalidation_level:
                    candidate.invalidated = True
                    candidate.state = "invalidated"
                    return
            elif candidate.direction_bias == "bearish":
                # Bearish pattern invalidated if price rises above invalidation
                if current_high > candidate.invalidation_level:
                    candidate.invalidated = True
                    candidate.state = "invalidated"
                    return
        
        # 2. Check breakout (pattern confirmed/broken)
        if candidate.breakout_level is not None:
            if candidate.direction_bias == "bullish":
                if current_price > candidate.breakout_level:
                    candidate.broken = True
                    candidate.state = "broken"
                    return
            elif candidate.direction_bias == "bearish":
                if current_price < candidate.breakout_level:
                    candidate.broken = True
                    candidate.state = "broken"
                    return
        
        # 3. Check expiry by age
        pattern_length = candidate.window.end_index - candidate.window.start_index
        age = len(candles) - 1 - candidate.window.end_index
        max_age = max(pattern_length // 2, 10)  # Pattern can't be older than half its formation time
        
        if age > max_age:
            candidate.expired = True
            candidate.state = "expired"
            return
        
        # 4. Check context invalidation (regime change)
        regime = structure_context.get("regime", "unknown")
        if self._is_context_invalidated(candidate, regime):
            candidate.invalidated = True
            candidate.state = "invalidated"
            return
        
        # If none of the above, pattern is active
        candidate.state = "active"
    
    def _is_context_invalidated(self, candidate: PatternCandidate, regime: str) -> bool:
        """Check if market regime invalidates the pattern."""
        # Bearish patterns in strong uptrend are suspicious
        if candidate.direction_bias == "bearish" and regime == "trend_up":
            return True
        # Bullish patterns in strong downtrend are suspicious
        if candidate.direction_bias == "bullish" and regime == "trend_down":
            return True
        return False
