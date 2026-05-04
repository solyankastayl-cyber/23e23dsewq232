"""
Pattern Expiration Engine
=========================

CRITICAL: Old patterns that have already played out should NOT be shown.

A triangle from 6 months ago is NOT relevant today.
This engine filters out stale patterns based on:
- Age (distance from last touch to current candle)
- Timeframe-specific thresholds
"""

from typing import Dict


class PatternExpirationEngine:
    """
    Filters out patterns that are too old to be relevant.
    
    Key insight: A pattern that was valid 100 candles ago
    has likely already broken out or invalidated.
    """
    
    # Maximum age (in candles) for a pattern to be considered relevant
    # Higher TFs have stricter limits because each candle = more time
    MAX_PATTERN_AGE = {
        "4H": 40,      # ~6.5 days
        "1D": 60,      # ~2 months
        "7D": 50,      # ~1 year of weekly context
        "30D": 40,     # ~3 years of monthly context
        "180D": 30,    # Macro - only recent matters
        "1Y": 20,      # Cycle level - very strict
    }
    
    def __init__(self):
        pass

    def is_relevant(self, candidate, current_index: int, timeframe: str) -> bool:
        """
        Check if pattern is still relevant.
        
        Args:
            candidate: PatternCandidate with last_touch_index
            current_index: Current candle index
            timeframe: TF string for age lookup
            
        Returns:
            True if pattern is fresh enough to show
        """
        max_age = self.MAX_PATTERN_AGE.get(timeframe.upper(), 60)
        age = current_index - candidate.last_touch_index
        
        # Pattern is relevant only if last touch is recent
        return age <= max_age
    
    def filter_expired(self, candidates: list, current_index: int, timeframe: str) -> list:
        """Filter out all expired patterns."""
        return [
            c for c in candidates
            if self.is_relevant(c, current_index, timeframe)
        ]


# Singleton instance
pattern_expiration_engine = PatternExpirationEngine()
