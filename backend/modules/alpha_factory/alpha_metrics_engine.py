"""
AF1 - Alpha Metrics Engine
==========================
Calculates metrics from TT4 trades by scope (symbol, entry_mode).
"""

from collections import defaultdict
from typing import List, Dict, Any
from .alpha_models import AlphaMetrics, utc_now


class AlphaMetricsEngine:
    """Calculates alpha metrics from trade history"""
    
    def build_for_scope(self, trades: List[Dict[str, Any]], scope: str) -> List[AlphaMetrics]:
        """
        Build metrics for all unique values in a scope.
        
        Args:
            trades: List of trade dicts from TT4
            scope: "symbol" or "entry_mode"
            
        Returns:
            List of AlphaMetrics sorted by expectancy descending
        """
        grouped = defaultdict(list)

        for t in trades:
            key = self._extract_scope_key(t, scope)
            if not key or key == "UNKNOWN":
                continue
            grouped[key].append(t)

        output = []
        for key, items in grouped.items():
            metrics = self._compute_metrics(scope, key, items)
            output.append(metrics)

        # Sort by expectancy (best performers first)
        output.sort(key=lambda x: x.expectancy, reverse=True)
        return output

    def _extract_scope_key(self, trade: Dict[str, Any], scope: str) -> str:
        """Extract the grouping key based on scope"""
        if scope == "symbol":
            return trade.get("symbol", "UNKNOWN")
        if scope == "entry_mode":
            return trade.get("entry_mode") or trade.get("prediction_action") or "UNKNOWN"
        if scope == "execution_mode":
            return trade.get("execution_mode", "UNKNOWN")
        return "UNKNOWN"

    def _compute_metrics(self, scope: str, key: str, items: List[Dict[str, Any]]) -> AlphaMetrics:
        """Compute comprehensive metrics for a group of trades"""
        n = len(items)
        
        # Categorize trades
        wins = [t for t in items if t.get("result") == "WIN"]
        losses = [t for t in items if t.get("result") == "LOSS"]

        # PnL calculations
        gross_profit = sum(float(t.get("pnl", 0) or 0) for t in wins)
        gross_loss = abs(sum(float(t.get("pnl", 0) or 0) for t in losses))
        net_pnl = sum(float(t.get("pnl", 0) or 0) for t in items)

        # Averages
        rr_values = [float(t.get("rr", 0) or 0) for t in items if t.get("rr")]
        avg_rr = sum(rr_values) / len(rr_values) if rr_values else 0.0

        # Diagnostic rates
        wrong_early_rate = sum(1 for t in items if t.get("wrong_early")) / n if n else 0.0
        late_entry_rate = sum(1 for t in items if t.get("late_entry")) / n if n else 0.0
        mtf_conflict_rate = sum(1 for t in items if t.get("mtf_conflict")) / n if n else 0.0

        # Core metrics
        pf = (gross_profit / gross_loss) if gross_loss > 0 else None
        expectancy = net_pnl / n if n else 0.0
        win_rate = len(wins) / n if n else 0.0

        # Stability score
        stability = self._compute_stability(
            expectancy=expectancy,
            wrong_early_rate=wrong_early_rate,
            late_entry_rate=late_entry_rate,
            mtf_conflict_rate=mtf_conflict_rate,
            win_rate=win_rate,
            profit_factor=pf,
            sample_size=n,
        )

        return AlphaMetrics(
            scope=scope,
            scope_key=key,
            trades=n,
            win_rate=round(win_rate, 4),
            profit_factor=round(pf, 4) if pf is not None else None,
            expectancy=round(expectancy, 2),
            avg_rr=round(avg_rr, 2),
            gross_profit=round(gross_profit, 2),
            gross_loss=round(gross_loss, 2),
            net_pnl=round(net_pnl, 2),
            wrong_early_rate=round(wrong_early_rate, 4),
            late_entry_rate=round(late_entry_rate, 4),
            mtf_conflict_rate=round(mtf_conflict_rate, 4),
            stability=round(stability, 4),
            last_updated=utc_now(),
        )

    def _compute_stability(
        self,
        expectancy: float,
        wrong_early_rate: float,
        late_entry_rate: float,
        mtf_conflict_rate: float,
        win_rate: float,
        profit_factor: float = None,
        sample_size: int = 0,
    ) -> float:
        """
        Compute stability score (0-1).
        
        Higher = more stable/reliable edge.
        """
        base = 0.5
        
        # Positive contributions
        if expectancy > 0:
            base += 0.15
        if win_rate > 0.55:
            base += 0.08
        if profit_factor and profit_factor > 1.5:
            base += 0.10
        if sample_size >= 20:
            base += 0.07
            
        # Penalties for diagnostic issues
        penalty = (
            (wrong_early_rate * 0.35) + 
            (late_entry_rate * 0.25) + 
            (mtf_conflict_rate * 0.20)
        )
        
        # Low sample penalty
        if sample_size < 10:
            penalty += 0.15
        elif sample_size < 5:
            penalty += 0.30
            
        return max(0.0, min(1.0, base - penalty))
