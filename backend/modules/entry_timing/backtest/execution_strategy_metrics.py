"""
PHASE 4.6 — Execution Strategy Metrics

Analyzes which execution strategies perform best.
"""

from typing import Dict, List


class ExecutionStrategyMetrics:
    """
    Computes metrics for each execution strategy.
    """
    
    def compute(self, trades: List[Dict]) -> Dict:
        """
        Compute metrics per execution strategy.
        
        Args:
            trades: List of trades with execution_strategy field
        
        Returns:
            Metrics breakdown by strategy
        """
        result: Dict[str, Dict] = {}
        
        for trade in trades:
            strategy = trade.get("execution_strategy", "UNKNOWN")
            
            if strategy not in result:
                result[strategy] = {
                    "trades": 0,
                    "wins": 0,
                    "wrong_early": 0,
                    "pnl": 0.0,
                    "rr_sum": 0.0,
                    "slippage_sum": 0.0
                }
            
            result[strategy]["trades"] += 1
            result[strategy]["pnl"] += trade.get("pnl", 0.0)
            result[strategy]["rr_sum"] += trade.get("rr", 0.0)
            result[strategy]["slippage_sum"] += trade.get("slippage", 0.0)
            
            if trade.get("win"):
                result[strategy]["wins"] += 1
            
            if trade.get("wrong_early"):
                result[strategy]["wrong_early"] += 1
        
        # Compute derived metrics
        for strategy, stats in result.items():
            n = stats["trades"] or 1
            stats["win_rate"] = round(stats["wins"] / n, 4)
            stats["wrong_early_rate"] = round(stats["wrong_early"] / n, 4)
            stats["avg_rr"] = round(stats["rr_sum"] / n, 4)
            stats["avg_pnl"] = round(stats["pnl"] / n, 6)
            stats["avg_slippage"] = round(stats["slippage_sum"] / n, 6)
            stats["total_pnl"] = round(stats["pnl"], 6)
        
        # Rank by effectiveness
        ranked = sorted(
            result.items(),
            key=lambda x: (x[1]["avg_pnl"], -x[1]["wrong_early_rate"]),
            reverse=True
        )
        
        return {
            "by_strategy": result,
            "best_strategy": ranked[0][0] if ranked else None,
            "worst_strategy": ranked[-1][0] if ranked else None,
            "ranking": [{"strategy": s, **stats} for s, stats in ranked]
        }
