"""
PHASE 4.6 — Timing Comparison Engine

Compares aggregate metrics before and after Entry Timing Stack.
"""

from typing import Dict, List


class TimingComparisonEngine:
    """
    Compares trading metrics before and after Entry Timing Stack.
    """
    
    def compare(self, trades_before: List[Dict], trades_after: List[Dict]) -> Dict:
        """
        Compare aggregate metrics.
        
        Args:
            trades_before: Trades without Entry Timing Stack
            trades_after: Trades with Entry Timing Stack
        
        Returns:
            Before/After comparison with deltas
        """
        before = self._aggregate(trades_before)
        after = self._aggregate(trades_after)
        
        delta = {
            "win_rate": round(after["win_rate"] - before["win_rate"], 4),
            "wrong_early_rate": round(after["wrong_early_rate"] - before["wrong_early_rate"], 4),
            "total_pnl": round(after["total_pnl"] - before["total_pnl"], 6),
            "avg_rr": round(after["avg_rr"] - before["avg_rr"], 4),
            "avg_pnl": round(after["avg_pnl"] - before["avg_pnl"], 6)
        }
        
        return {
            "before": before,
            "after": after,
            "delta": delta,
            "improvements": self._identify_improvements(delta),
            "summary": self._generate_summary(before, after, delta)
        }
    
    def _aggregate(self, trades: List[Dict]) -> Dict:
        """Compute aggregate metrics."""
        n = len(trades) or 1
        wins = sum(1 for t in trades if t.get("win"))
        wrong_early = sum(1 for t in trades if t.get("wrong_early"))
        total_pnl = sum(t.get("pnl", 0.0) for t in trades)
        total_rr = sum(t.get("rr", 0.0) for t in trades)
        
        return {
            "trades": len(trades),
            "wins": wins,
            "wrong_early": wrong_early,
            "win_rate": round(wins / n, 4),
            "wrong_early_rate": round(wrong_early / n, 4),
            "total_pnl": round(total_pnl, 6),
            "avg_pnl": round(total_pnl / n, 6),
            "avg_rr": round(total_rr / n, 4)
        }
    
    def _identify_improvements(self, delta: Dict) -> List[str]:
        """Identify which metrics improved."""
        improvements = []
        
        if delta["win_rate"] > 0:
            improvements.append(f"Win rate improved by {round(delta['win_rate'] * 100, 1)}%")
        
        if delta["wrong_early_rate"] < 0:
            improvements.append(f"Wrong Early reduced by {round(abs(delta['wrong_early_rate']) * 100, 1)}%")
        
        if delta["total_pnl"] > 0:
            improvements.append(f"Total PnL improved by {round(delta['total_pnl'], 4)}")
        
        if delta["avg_rr"] > 0:
            improvements.append(f"Average RR improved by {round(delta['avg_rr'], 2)}")
        
        return improvements
    
    def _generate_summary(self, before: Dict, after: Dict, delta: Dict) -> str:
        """Generate summary statement."""
        we_before = round(before["wrong_early_rate"] * 100, 1)
        we_after = round(after["wrong_early_rate"] * 100, 1)
        
        if delta["wrong_early_rate"] < -0.10:
            return f"Entry Timing Stack achieved significant improvement: Wrong Early {we_before}% → {we_after}%"
        elif delta["wrong_early_rate"] < 0:
            return f"Entry Timing Stack showed improvement: Wrong Early {we_before}% → {we_after}%"
        else:
            return f"Entry Timing Stack needs tuning: Wrong Early {we_before}% → {we_after}%"
