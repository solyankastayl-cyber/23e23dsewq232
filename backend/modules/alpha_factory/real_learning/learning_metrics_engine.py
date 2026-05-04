"""
Learning Metrics Engine - AF6

Computes aggregated learning metrics from trade outcomes.
Groups by symbol, entry_mode, regime for performance analysis.
"""

from collections import defaultdict
from typing import Dict, List, Any, Callable
import logging

logger = logging.getLogger(__name__)


class LearningMetricsEngine:
    """
    Learning metrics computation engine.
    
    Aggregates trade outcomes into actionable metrics:
    - Win rate
    - Profit factor
    - Wrong early rate
    - Average PnL
    - Bad execution rate
    
    Groups by: symbol, entry_mode, regime, symbol::mode
    """
    
    def compute(self, outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute learning metrics from outcomes.
        
        Args:
            outcomes: List of classified outcomes
            
        Returns:
            Metrics dict grouped by various dimensions
        """
        logger.info(f"[LearningMetricsEngine] Computing metrics for {len(outcomes)} outcomes")
        
        return {
            "by_symbol": self._group_metrics(outcomes, lambda o: o["symbol"]),
            "by_entry_mode": self._group_metrics(outcomes, lambda o: o["entry_mode"]),
            "by_regime": self._group_metrics(outcomes, lambda o: o["regime"]),
            "by_symbol_mode": self._group_metrics(
                outcomes,
                lambda o: f'{o["symbol"]}::{o["entry_mode"]}'
            ),
            "by_strategy": self._group_metrics(outcomes, lambda o: o.get("strategy_id", "default")),  # NEW: ORCH-7
            "by_strategy_symbol": self._group_metrics(
                outcomes,
                lambda o: f'{o.get("strategy_id", "default")}::{o["symbol"]}'  # NEW: ORCH-7
            ),
        }
    
    def _group_metrics(
        self,
        outcomes: List[Dict[str, Any]],
        key_fn: Callable[[Dict[str, Any]], str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Group outcomes and compute metrics for each group.
        
        Args:
            outcomes: List of outcomes
            key_fn: Function to extract grouping key from outcome
            
        Returns:
            Dict mapping group key to metrics
        """
        grouped = defaultdict(list)
        for o in outcomes:
            try:
                grouped[key_fn(o)].append(o)
            except (KeyError, TypeError) as e:
                logger.warning(f"[LearningMetricsEngine] Skipping outcome due to key error: {e}")
                continue
        
        result = {}
        for key, items in grouped.items():
            result[key] = self._metrics(items)
        
        return result
    
    def _metrics(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute metrics for a group of outcomes.
        
        Args:
            items: List of outcomes in group
            
        Returns:
            Metrics dict
        """
        n = len(items)
        if n == 0:
            return {
                "count": 0,
                "win_rate": 0.0,
                "profit_factor": None,
                "avg_pnl": 0.0,
                "wrong_early_rate": 0.0,
                "bad_execution_rate": 0.0,
            }
        
        wins = [x for x in items if x.get("pnl", 0) > 0]
        losses = [x for x in items if x.get("pnl", 0) < 0]
        
        gross_profit = sum(x.get("pnl", 0) for x in wins)
        gross_loss = abs(sum(x.get("pnl", 0) for x in losses))
        pf = gross_profit / gross_loss if gross_loss > 0 else None
        
        wrong_early_count = sum(1 for x in items if x.get("wrong_early"))
        bad_execution_count = sum(
            1 for x in items
            if "bad_execution" in x.get("mistake_type", [])
        )
        
        avg_pnl = sum(x.get("pnl", 0) for x in items) / n if n else 0.0
        
        return {
            "count": n,
            "win_rate": len(wins) / n if n else 0.0,
            "profit_factor": pf,
            "avg_pnl": avg_pnl,
            "wrong_early_rate": wrong_early_count / n if n else 0.0,
            "bad_execution_rate": bad_execution_count / n if n else 0.0,
        }
