"""
Entry Mode Metrics Engine - Computes metrics per entry mode from validation data
"""
from collections import defaultdict
from typing import List, Dict, Any

from .entry_mode_models import EntryModeMetrics


class EntryModeMetricsEngine:
    """
    Reads shadow trades + validation results and computes metrics grouped by entry_mode.
    """
    
    def build(
        self, 
        shadow_trades: List[Dict[str, Any]], 
        validation_results: List[Dict[str, Any]]
    ) -> List[EntryModeMetrics]:
        """
        Build entry mode metrics from shadow trades and their validation results.
        """
        # Create map of shadow_id -> shadow trade
        shadow_map = {x["shadow_id"]: x for x in shadow_trades}
        
        # Group by entry_mode
        grouped = defaultdict(list)
        
        for result in validation_results:
            shadow = shadow_map.get(result.get("shadow_id"))
            if not shadow:
                continue
            
            entry_mode = shadow.get("entry_mode", "UNKNOWN")
            grouped[entry_mode].append({
                "shadow": shadow,
                "result": result,
            })
        
        # Compute metrics for each entry mode
        output = []
        for entry_mode, items in grouped.items():
            metrics = self._compute_metrics(entry_mode, items)
            output.append(metrics)
        
        # Sort by expectancy descending
        output.sort(key=lambda x: x.expectancy, reverse=True)
        return output
    
    def _compute_metrics(self, entry_mode: str, items: List[Dict[str, Any]]) -> EntryModeMetrics:
        """Compute metrics for a single entry mode."""
        n = len(items)
        if n == 0:
            return self._empty_metrics(entry_mode)
        
        # Categorize results
        wins = [x for x in items if x["result"].get("result") == "WIN"]
        losses = [x for x in items if x["result"].get("result") == "LOSS"]
        expired = [x for x in items if x["result"].get("result") == "EXPIRED"]
        
        # PnL calculations
        gross_profit = sum(self._safe_float(x["result"].get("pnl", 0)) for x in wins)
        gross_loss = abs(sum(self._safe_float(x["result"].get("pnl", 0)) for x in losses))
        total_pnl = sum(self._safe_float(x["result"].get("pnl", 0)) for x in items)
        
        # Core metrics
        pf = gross_profit / gross_loss if gross_loss > 0 else None
        expectancy = total_pnl / n if n > 0 else 0.0
        win_rate = len(wins) / n if n > 0 else 0.0
        
        # RR metrics
        rr_values = [self._safe_float(x["shadow"].get("planned_rr", 0)) for x in items]
        avg_rr = sum(rr_values) / n if n > 0 else 0.0
        
        # Quality metrics
        wrong_early_count = sum(1 for x in items if x["result"].get("wrong_early", False))
        wrong_early_rate = wrong_early_count / n if n > 0 else 0.0
        
        expired_rate = len(expired) / n if n > 0 else 0.0
        
        drift_values = [self._safe_float(x["result"].get("drift_bps", 0)) for x in items]
        avg_drift_bps = sum(drift_values) / n if n > 0 else 0.0
        
        # Stability score
        stability = self._compute_stability(
            expectancy=expectancy,
            pf=pf,
            wrong_early_rate=wrong_early_rate,
            expired_rate=expired_rate,
            n=n
        )
        
        return EntryModeMetrics(
            entry_mode=entry_mode,
            trades=n,
            win_rate=round(win_rate, 4),
            profit_factor=round(pf, 4) if pf is not None else None,
            expectancy=round(expectancy, 4),
            avg_rr=round(avg_rr, 4),
            wrong_early_rate=round(wrong_early_rate, 4),
            expired_rate=round(expired_rate, 4),
            avg_drift_bps=round(avg_drift_bps, 4),
            stability=round(stability, 4),
            gross_profit=round(gross_profit, 4),
            gross_loss=round(gross_loss, 4),
            total_pnl=round(total_pnl, 4),
        )
    
    def _compute_stability(
        self, 
        expectancy: float, 
        pf: float | None, 
        wrong_early_rate: float, 
        expired_rate: float,
        n: int
    ) -> float:
        """Compute stability score (0-1)."""
        score = 0.5
        
        # Sample size bonus
        if n >= 20:
            score += 0.10
        elif n < 5:
            score -= 0.15
        
        # Expectancy signal
        if expectancy > 50:
            score += 0.20
        elif expectancy > 0:
            score += 0.10
        elif expectancy < -20:
            score -= 0.15
        
        # PF signal
        if pf is not None:
            if pf > 1.8:
                score += 0.20
            elif pf > 1.25:
                score += 0.10
            elif pf < 0.9:
                score -= 0.20
        
        # Wrong early penalty
        if wrong_early_rate > 0.25:
            score -= 0.25
        elif wrong_early_rate > 0.15:
            score -= 0.10
        elif wrong_early_rate < 0.08:
            score += 0.10
        
        # Expired penalty
        if expired_rate > 0.25:
            score -= 0.15
        elif expired_rate > 0.15:
            score -= 0.05
        
        return max(0.0, min(1.0, score))
    
    def _empty_metrics(self, entry_mode: str) -> EntryModeMetrics:
        return EntryModeMetrics(
            entry_mode=entry_mode,
            trades=0,
            win_rate=0.0,
            profit_factor=None,
            expectancy=0.0,
            avg_rr=0.0,
            wrong_early_rate=0.0,
            expired_rate=0.0,
            avg_drift_bps=0.0,
            stability=0.0,
        )
    
    def _safe_float(self, val) -> float:
        try:
            return float(val) if val is not None else 0.0
        except (ValueError, TypeError):
            return 0.0
