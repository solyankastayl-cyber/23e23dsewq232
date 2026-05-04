"""
PHASE 4.3 — Execution Splitter

Splits execution strategies into concrete order legs.
"""

from typing import Dict, List, Optional


class ExecutionSplitter:
    """
    Splits execution strategy into concrete order legs.
    
    Output format:
    {
        "legs": [
            {"type": "market", "entry": 62410, "size_pct": 0.5},
            {"type": "limit", "entry": 62100, "size_pct": 0.5}
        ]
    }
    """
    
    def __init__(self):
        self.default_retest_offset = 0.005  # 0.5% below entry for retest
        self.default_pullback_offset = 0.008  # 0.8% below for pullback
    
    def split(
        self,
        strategy: str,
        setup: Dict,
        direction: str = "LONG",
        retest_level: Optional[float] = None
    ) -> Dict:
        """
        Split strategy into execution legs.
        
        Args:
            strategy: Execution strategy name
            setup: Trade setup with entry, stop_loss, target
            direction: LONG or SHORT
            retest_level: Optional explicit retest level
        
        Returns:
            Dict with legs array
        """
        entry = setup.get("entry", 0)
        
        if strategy == "FULL_ENTRY_NOW":
            return self._full_market(entry)
        
        if strategy == "ENTER_ON_CLOSE_FULL":
            return self._close_confirmed_market(entry)
        
        if strategy == "PARTIAL_NOW_PARTIAL_RETEST":
            return self._partial_split(entry, direction, retest_level)
        
        if strategy == "WAIT_RETEST_FULL":
            return self._retest_limit(entry, direction, retest_level)
        
        if strategy == "WAIT_PULLBACK_LIMIT":
            return self._pullback_limit(entry, direction)
        
        if strategy == "CONFIRM_THEN_ENTER":
            return self._confirmation_market(entry)
        
        if strategy == "SKIP_ENTRY":
            return {"legs": [], "reason": "entry_skipped"}
        
        return {"legs": [], "reason": "unknown_strategy"}
    
    def _full_market(self, entry: float) -> Dict:
        """Full position at market."""
        return {
            "legs": [
                {"type": "market", "entry": entry, "size_pct": 1.0, "immediate": True}
            ],
            "total_legs": 1,
            "execution_type": "immediate"
        }
    
    def _close_confirmed_market(self, entry: float) -> Dict:
        """Full position after candle close."""
        return {
            "legs": [
                {"type": "close_confirmed_market", "entry": entry, "size_pct": 1.0, "immediate": False}
            ],
            "total_legs": 1,
            "execution_type": "on_close"
        }
    
    def _partial_split(self, entry: float, direction: str, retest_level: Optional[float]) -> Dict:
        """50% now, 50% on retest."""
        if direction == "LONG":
            retest = retest_level or entry * (1 - self.default_retest_offset)
        else:
            retest = retest_level or entry * (1 + self.default_retest_offset)
        
        return {
            "legs": [
                {"type": "market", "entry": entry, "size_pct": 0.5, "immediate": True},
                {"type": "limit", "entry": round(retest, 2), "size_pct": 0.5, "immediate": False}
            ],
            "total_legs": 2,
            "execution_type": "split"
        }
    
    def _retest_limit(self, entry: float, direction: str, retest_level: Optional[float]) -> Dict:
        """Full position at retest level."""
        if direction == "LONG":
            level = retest_level or entry * (1 - self.default_retest_offset)
        else:
            level = retest_level or entry * (1 + self.default_retest_offset)
        
        return {
            "legs": [
                {"type": "limit", "entry": round(level, 2), "size_pct": 1.0, "immediate": False}
            ],
            "total_legs": 1,
            "execution_type": "limit_retest"
        }
    
    def _pullback_limit(self, entry: float, direction: str) -> Dict:
        """Full position at pullback level (for extended entries)."""
        if direction == "LONG":
            level = entry * (1 - self.default_pullback_offset)
        else:
            level = entry * (1 + self.default_pullback_offset)
        
        return {
            "legs": [
                {"type": "limit", "entry": round(level, 2), "size_pct": 1.0, "immediate": False}
            ],
            "total_legs": 1,
            "execution_type": "limit_pullback"
        }
    
    def _confirmation_market(self, entry: float) -> Dict:
        """Market entry after confirmation signal."""
        return {
            "legs": [
                {"type": "confirmation_market", "entry": entry, "size_pct": 1.0, "immediate": False}
            ],
            "total_legs": 1,
            "execution_type": "on_confirmation"
        }
