"""
Position Health Engine
======================

Computes position health based on:
- Distance to stop
- PnL status
- Market structure

Health levels:
- GOOD: Normal operation
- WARNING: Near stop or adverse conditions
- CRITICAL: Stop breached or severe conditions
"""

from typing import Dict, Any


class PositionHealthEngine:
    """
    Simple health model based on price vs stop/target.
    
    CRITICAL: stop breached
    WARNING: within 1% of stop
    GOOD: otherwise
    """
    
    # Threshold for WARNING (1% from stop)
    WARNING_THRESHOLD = 0.01
    
    def compute(self, position: Dict[str, Any]) -> str:
        """Compute health status for position"""
        mark = position.get("mark_price")
        stop = position.get("stop")
        entry = position.get("entry_price")
        side = position.get("side")
        
        # If missing data, assume GOOD
        if mark is None or stop is None or entry is None or not side:
            return "GOOD"
        
        # Prevent division by zero
        if entry <= 0:
            return "GOOD"
        
        if side == "LONG":
            return self._compute_long_health(mark, stop, entry)
        elif side == "SHORT":
            return self._compute_short_health(mark, stop, entry)
        
        return "GOOD"
    
    def _compute_long_health(self, mark: float, stop: float, entry: float) -> str:
        """Health for LONG position"""
        # Stop breached = CRITICAL
        if mark <= stop:
            return "CRITICAL"
        
        # Near stop = WARNING
        distance_to_stop = (mark - stop) / entry
        if distance_to_stop < self.WARNING_THRESHOLD:
            return "WARNING"
        
        return "GOOD"
    
    def _compute_short_health(self, mark: float, stop: float, entry: float) -> str:
        """Health for SHORT position"""
        # Stop breached = CRITICAL
        if mark >= stop:
            return "CRITICAL"
        
        # Near stop = WARNING
        distance_to_stop = (stop - mark) / entry
        if distance_to_stop < self.WARNING_THRESHOLD:
            return "WARNING"
        
        return "GOOD"
    
    def compute_detailed(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Compute detailed health with reasons"""
        health = self.compute(position)
        
        mark = position.get("mark_price", 0)
        stop = position.get("stop", 0)
        target = position.get("target", 0)
        entry = position.get("entry_price", 0)
        side = position.get("side", "LONG")
        
        reasons = []
        
        if health == "CRITICAL":
            reasons.append("Stop loss breached")
        elif health == "WARNING":
            reasons.append("Price near stop loss")
        
        # Calculate distance to target
        if target and entry and mark:
            if side == "LONG":
                distance_to_target = (target - mark) / entry
                if distance_to_target < 0:
                    reasons.append("Target reached")
            else:
                distance_to_target = (mark - target) / entry
                if distance_to_target < 0:
                    reasons.append("Target reached")
        
        return {
            "health": health,
            "reasons": reasons,
            "distance_to_stop_pct": self._calc_distance_pct(mark, stop, entry, side, "stop"),
            "distance_to_target_pct": self._calc_distance_pct(mark, target, entry, side, "target"),
        }
    
    def _calc_distance_pct(self, mark: float, level: float, entry: float, side: str, level_type: str) -> float:
        """Calculate distance to level as percentage"""
        if not all([mark, level, entry]) or entry <= 0:
            return 0.0
        
        if side == "LONG":
            if level_type == "stop":
                return round((mark - level) / entry * 100, 2)
            else:  # target
                return round((level - mark) / entry * 100, 2)
        else:  # SHORT
            if level_type == "stop":
                return round((level - mark) / entry * 100, 2)
            else:  # target
                return round((mark - level) / entry * 100, 2)
