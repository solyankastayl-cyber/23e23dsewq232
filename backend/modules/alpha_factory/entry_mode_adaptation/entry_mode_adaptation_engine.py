"""
Entry Mode Adaptation Engine - Main orchestrator for AF4
"""
from datetime import datetime, timezone
from typing import List, Dict, Any

from .entry_mode_models import EntryModeMetrics, EntryModeEvaluation, EntryModeAction, EntryModeSummary
from .entry_mode_metrics_engine import EntryModeMetricsEngine
from .entry_mode_evaluator import EntryModeEvaluator
from .entry_mode_actions_engine import EntryModeActionsEngine


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EntryModeAdaptationEngine:
    """
    Main AF4 engine that orchestrates:
    1. Compute metrics per entry mode
    2. Evaluate and assign verdicts
    3. Generate actions
    """
    
    def __init__(self):
        self.metrics_engine = EntryModeMetricsEngine()
        self.evaluator = EntryModeEvaluator()
        self.actions_engine = EntryModeActionsEngine()
    
    def run(
        self, 
        shadow_trades: List[Dict[str, Any]], 
        validation_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run full AF4 adaptation cycle.
        
        Returns:
            {
                "metrics": [...],
                "evaluations": [...],
                "actions": [...],
                "summary": {...},
                "timestamp": "..."
            }
        """
        # Step 1: Build metrics per entry mode
        metrics = self.metrics_engine.build(shadow_trades, validation_results)
        
        # Step 2: Evaluate and get verdicts
        evaluations = self.evaluator.evaluate([m.to_dict() for m in metrics])
        
        # Step 3: Generate actions
        actions = self.actions_engine.build([e.to_dict() for e in evaluations])
        
        # Step 4: Build summary
        summary = self._build_summary(evaluations)
        
        return {
            "metrics": [m.to_dict() for m in metrics],
            "evaluations": [e.to_dict() for e in evaluations],
            "actions": [a.to_dict() for a in actions],
            "summary": summary.to_dict(),
            "timestamp": utc_now(),
        }
    
    def run_metrics_only(
        self, 
        shadow_trades: List[Dict[str, Any]], 
        validation_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Run only metrics computation."""
        metrics = self.metrics_engine.build(shadow_trades, validation_results)
        return [m.to_dict() for m in metrics]
    
    def run_evaluations_only(
        self, 
        metrics: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Run only evaluations on existing metrics."""
        evaluations = self.evaluator.evaluate(metrics)
        return [e.to_dict() for e in evaluations]
    
    def _build_summary(self, evaluations: List[EntryModeEvaluation]) -> EntryModeSummary:
        """Build summary from evaluations."""
        verdicts = [e.verdict for e in evaluations]
        
        strong = sum(1 for v in verdicts if v == "STRONG_ENTRY_MODE")
        weak = sum(1 for v in verdicts if v == "WEAK_ENTRY_MODE")
        unstable = sum(1 for v in verdicts if v == "UNSTABLE_ENTRY_MODE")
        broken = sum(1 for v in verdicts if v == "BROKEN_ENTRY_MODE")
        
        total = len(evaluations)
        
        # Determine health
        if broken > total * 0.4 or (broken > 0 and total <= 3):
            health = "critical"
        elif broken > 0 or unstable > total * 0.5:
            health = "warning"
        else:
            health = "healthy"
        
        return EntryModeSummary(
            strong=strong,
            weak=weak,
            unstable=unstable,
            broken=broken,
            total_modes=total,
            health=health,
        )
