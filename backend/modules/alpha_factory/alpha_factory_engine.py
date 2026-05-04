"""
AF1 - Alpha Factory Engine
==========================
Main orchestrator that connects TT4 Forensics → Metrics → Evaluation → Actions.
"""

from typing import List, Dict, Any, Optional
from .alpha_models import AlphaFactoryResult, utc_now
from .alpha_repository import AlphaRepository
from .alpha_metrics_engine import AlphaMetricsEngine
from .alpha_evaluator import AlphaEvaluator
from .alpha_actions_engine import AlphaActionsEngine


class AlphaFactoryEngine:
    """
    Main Alpha Factory orchestrator.
    
    Flow:
    1. Load trades from TT4 Forensics
    2. Compute metrics by scope (symbol, entry_mode)
    3. Evaluate each scope → verdict
    4. Generate recommended actions
    5. Store results
    """
    
    def __init__(self, repo: AlphaRepository):
        self.repo = repo
        self.metrics_engine = AlphaMetricsEngine()
        self.evaluator = AlphaEvaluator()
        self.actions_engine = AlphaActionsEngine()

    def run(self, trades: List[Dict[str, Any]], symbol: Optional[str] = None) -> AlphaFactoryResult:
        """
        Run complete Alpha Factory analysis.
        
        Args:
            trades: List of trade dicts from TT4
            symbol: Optional symbol filter
            
        Returns:
            AlphaFactoryResult with all metrics, evaluations, and actions
        """
        timestamp = utc_now()
        
        # Filter by symbol if specified
        if symbol:
            trades = [t for t in trades if t.get("symbol", "").upper() == symbol.upper()]
        
        # === Step 1: Compute Metrics ===
        symbol_metrics = self.metrics_engine.build_for_scope(trades, scope="symbol")
        entry_mode_metrics = self.metrics_engine.build_for_scope(trades, scope="entry_mode")

        # Save metrics
        self.repo.save_metrics("symbol", symbol_metrics)
        self.repo.save_metrics("entry_mode", entry_mode_metrics)

        # === Step 2: Evaluate ===
        symbol_evals = self.evaluator.evaluate([m.to_dict() for m in symbol_metrics])
        entry_mode_evals = self.evaluator.evaluate([m.to_dict() for m in entry_mode_metrics])

        # Save evaluations
        self.repo.save_evaluations("symbol", symbol_evals)
        self.repo.save_evaluations("entry_mode", entry_mode_evals)

        # === Step 3: Generate Actions ===
        all_evals = [e.to_dict() for e in symbol_evals] + [e.to_dict() for e in entry_mode_evals]
        actions = self.actions_engine.build_actions(all_evals)
        
        # Save actions
        self.repo.save_actions(actions)
        self.repo.set_last_run(timestamp)

        return AlphaFactoryResult(
            metrics_symbol=symbol_metrics,
            metrics_entry_mode=entry_mode_metrics,
            evaluations_symbol=symbol_evals,
            evaluations_entry_mode=entry_mode_evals,
            actions=actions,
            run_timestamp=timestamp,
            trades_analyzed=len(trades),
        )

    def get_recommendation(self, scope: str, scope_key: str) -> Dict[str, Any]:
        """Get specific recommendation for a scope/key"""
        evaluation = self.repo.get_evaluation_by_key(scope, scope_key)
        metrics = self.repo.get_metrics_by_key(scope, scope_key)
        
        if not evaluation:
            return {"found": False, "scope": scope, "scope_key": scope_key}
            
        # Find matching action
        action = None
        for a in self.repo.get_actions():
            if a.scope == scope and a.scope_key == scope_key:
                action = a
                break
                
        return {
            "found": True,
            "scope": scope,
            "scope_key": scope_key,
            "metrics": metrics.to_dict() if metrics else None,
            "evaluation": evaluation.to_dict(),
            "action": action.to_dict() if action else None,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get overall Alpha Factory summary"""
        summary = self.repo.get_summary()
        
        # Add action breakdown
        actions = self.repo.get_actions()
        summary["action_breakdown"] = self.actions_engine.get_action_summary(actions)
        summary["actionable_count"] = len(self.actions_engine.filter_actionable(actions))
        summary["auto_applicable_count"] = len(self.actions_engine.filter_auto_applicable(actions))
        
        return summary
