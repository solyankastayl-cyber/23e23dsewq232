"""
PHASE 4.6 — Wrong Early Re-Measurement

The main metric: Did Wrong Early rate actually decrease?
"""

from typing import Dict, List


class WrongEarlyRemeasurement:
    """
    Compares Wrong Early rate before and after Entry Timing Stack.
    """
    
    def compute(self, trades_before: List[Dict], trades_after: List[Dict]) -> Dict:
        """
        Compute Wrong Early improvement.
        
        Args:
            trades_before: Trades without Entry Timing Stack
            trades_after: Trades with Entry Timing Stack
        
        Returns:
            Before/After comparison with improvement metrics
        """
        before_total = len(trades_before) or 1
        after_total = len(trades_after) or 1
        
        before_wrong_early = sum(1 for t in trades_before if t.get("wrong_early"))
        after_wrong_early = sum(1 for t in trades_after if t.get("wrong_early"))
        
        before_rate = before_wrong_early / before_total
        after_rate = after_wrong_early / after_total
        
        improvement = before_rate - after_rate
        improvement_pct = (improvement / before_rate) if before_rate > 0 else 0
        
        return {
            "before": {
                "total_trades": before_total,
                "wrong_early_count": before_wrong_early,
                "wrong_early_rate": round(before_rate, 4)
            },
            "after": {
                "total_trades": after_total,
                "wrong_early_count": after_wrong_early,
                "wrong_early_rate": round(after_rate, 4)
            },
            "improvement": {
                "absolute": round(improvement, 4),
                "percentage": round(improvement_pct, 4),
                "wrong_early_reduced_by": f"{round(improvement_pct * 100, 1)}%"
            },
            "target_met": after_rate < 0.25,  # Target: < 25%
            "summary": self._generate_summary(before_rate, after_rate)
        }
    
    def _generate_summary(self, before_rate: float, after_rate: float) -> str:
        """Generate human-readable summary."""
        before_pct = round(before_rate * 100, 1)
        after_pct = round(after_rate * 100, 1)
        
        if after_rate < before_rate * 0.5:
            return f"Excellent improvement: {before_pct}% → {after_pct}% (more than halved)"
        elif after_rate < before_rate:
            return f"Good improvement: {before_pct}% → {after_pct}%"
        elif after_rate == before_rate:
            return f"No change: {before_pct}% → {after_pct}%"
        else:
            return f"Warning: Wrong Early increased: {before_pct}% → {after_pct}%"
