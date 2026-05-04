"""
PHASE 4.6 — Entry Mode Metrics

Analyzes which entry modes perform best.
"""

from typing import Dict, List


class EntryModeMetrics:
    """
    Computes metrics for each entry mode.
    """
    
    def compute(self, trades: List[Dict]) -> Dict:
        """
        Compute metrics per entry mode.
        
        Args:
            trades: List of trades with entry_mode field
        
        Returns:
            Metrics breakdown by mode
        """
        result: Dict[str, Dict] = {}
        
        for trade in trades:
            mode = trade.get("entry_mode", "UNKNOWN")
            
            if mode not in result:
                result[mode] = {
                    "trades": 0,
                    "wins": 0,
                    "wrong_early": 0,
                    "pnl": 0.0,
                    "rr_sum": 0.0
                }
            
            result[mode]["trades"] += 1
            result[mode]["pnl"] += trade.get("pnl", 0.0)
            result[mode]["rr_sum"] += trade.get("rr", 0.0)
            
            if trade.get("win"):
                result[mode]["wins"] += 1
            
            if trade.get("wrong_early"):
                result[mode]["wrong_early"] += 1
        
        # Compute derived metrics
        for mode, stats in result.items():
            n = stats["trades"] or 1
            stats["win_rate"] = round(stats["wins"] / n, 4)
            stats["wrong_early_rate"] = round(stats["wrong_early"] / n, 4)
            stats["avg_rr"] = round(stats["rr_sum"] / n, 4)
            stats["avg_pnl"] = round(stats["pnl"] / n, 6)
            stats["total_pnl"] = round(stats["pnl"], 6)
        
        # Rank by effectiveness
        ranked = sorted(
            result.items(),
            key=lambda x: (x[1]["win_rate"], -x[1]["wrong_early_rate"]),
            reverse=True
        )
        
        return {
            "by_mode": result,
            "best_mode": ranked[0][0] if ranked else None,
            "worst_mode": ranked[-1][0] if ranked else None,
            "ranking": [{"mode": m, **s} for m, s in ranked]
        }
