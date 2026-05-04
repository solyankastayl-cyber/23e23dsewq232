"""
Real Learning Engine - AF6

Main orchestrator for the learning system.
Coordinates: outcome registration → classification → metrics → actions → policy apply.
"""

from typing import Dict, Any
import logging

from .outcome_registry import OutcomeRegistry
from .outcome_classifier import OutcomeClassifier
from .learning_metrics_engine import LearningMetricsEngine
from .alpha_feedback_engine import AlphaFeedbackEngine
from .learning_policy_bridge import LearningPolicyBridge

logger = logging.getLogger(__name__)


class RealLearningEngine:
    """
    Real Learning Engine - AF6.
    
    Complete intelligence loop orchestrator:
    1. Register trade outcomes
    2. Classify quality and mistakes
    3. Compute aggregated metrics
    4. Generate adaptive actions
    5. Apply to override registry
    6. Future decisions change via FinalGate
    
    This is the brain that makes the system self-improving.
    """
    
    def __init__(self, integration_engine, audit_controller=None):
        """
        Args:
            integration_engine: ORCH-3 IntegrationEngine for policy application
            audit_controller: P0.7 AuditController for learning audit
        """
        self.registry = OutcomeRegistry()
        self.classifier = OutcomeClassifier()
        self.metrics_engine = LearningMetricsEngine()
        self.feedback_engine = AlphaFeedbackEngine()
        self.policy_bridge = LearningPolicyBridge(integration_engine)
        self.audit_controller = audit_controller  # P0.7
        
        logger.info("[RealLearningEngine] Initialized AF6 Real Learning Engine")
    
    def register_outcome(self, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a trade outcome.
        
        Args:
            outcome: Raw outcome from TradeOutcomeEngine
            
        Returns:
            Classified outcome
        """
        # Classify outcome (add quality metadata)
        classified = self.classifier.classify(outcome)
        
        # Store in registry
        self.registry.register(classified)
        
        logger.info(
            f"[RealLearningEngine] Registered outcome: {classified['trade_id']} | "
            f"{classified['outcome_type']} | {classified['entry_mode']} | "
            f"pnl={classified['pnl']:.2f}"
        )
        
        return classified
    
    def run_cycle(self, trace_id: str = None) -> Dict[str, Any]:
        """
        Run full learning cycle.
        
        Workflow:
        1. Get all outcomes
        2. Compute metrics
        3. Generate adaptive actions
        4. Apply to override registry
        5. (P0.7) Log to learning audit
        
        Args:
            trace_id: P0.7+ correlation ID for causal graph
        
        Returns:
            Cycle result with metrics, actions, applied
        """
        from datetime import datetime, timezone
        import uuid
        
        # P0.7+: Generate trace_id if not provided
        if trace_id is None:
            trace_id = str(uuid.uuid4())
        
        logger.info(f"[RealLearningEngine] Running learning cycle... (trace={trace_id})")
        
        # Get all outcomes
        outcomes = self.registry.list_all()
        
        if not outcomes:
            logger.info("[RealLearningEngine] No outcomes to process")
            return {
                "outcomes_count": 0,
                "metrics": {},
                "actions": [],
                "applied": {
                    "alpha_actions_applied": [],
                    "regime_actions_applied": [],
                    "total_applied": 0,
                },
            }
        
        # Compute metrics
        metrics = self.metrics_engine.compute(outcomes)
        
        # Generate adaptive actions
        actions = self.feedback_engine.generate_actions(metrics)
        
        # Apply to override registry
        applied = self.policy_bridge.apply(actions)
        
        # P0.7: LEARNING AUDIT (Hook 4)
        if self.audit_controller:
            from modules.audit.audit_helper import run_audit_task
            run_audit_task(
                self.audit_controller.learning.insert({
                    "timestamp": datetime.now(timezone.utc),
                    "trace_id": trace_id,  # P0.7+ CRITICAL: trace ID for causal graph
                    "outcomes_count": len(outcomes),
                    "metrics_snapshot": {
                        "win_rate_overall": metrics.get("overall", {}).get("win_rate"),
                        "avg_pnl": metrics.get("overall", {}).get("avg_pnl"),
                        "total_pnl": metrics.get("overall", {}).get("total_pnl"),
                        "by_entry_mode": metrics.get("by_entry_mode", {})
                    },
                    "actions_generated": [
                        {
                            "type": a.get("type"),
                            "strategy_id": a.get("strategy_id"),
                            "reason": a.get("reason"),
                            "confidence": a.get("confidence")
                        }
                        for a in actions
                    ],
                    "actions_applied": {
                        "alpha_actions": applied.get("alpha_actions_applied", []),
                        "regime_actions": applied.get("regime_actions_applied", []),
                        "total_count": applied.get("total_applied", 0)
                    }
                }),
                context="learning_cycle_audit"
            )
        
        logger.info(
            f"[RealLearningEngine] Cycle complete: {len(outcomes)} outcomes → "
            f"{len(actions)} actions → {applied['total_applied']} applied"
        )
        
        return {
            "outcomes_count": len(outcomes),
            "metrics": metrics,
            "actions": actions,
            "applied": applied,
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get learning system summary.
        
        Returns:
            Summary dict with counts and recent actions
        """
        outcomes = self.registry.list_all()
        
        # Get metrics
        if outcomes:
            metrics = self.metrics_engine.compute(outcomes)
            actions = self.feedback_engine.generate_actions(metrics)
        else:
            metrics = {}
            actions = []
        
        return {
            "total_outcomes": len(outcomes),
            "by_entry_mode": {
                mode: m["count"]
                for mode, m in metrics.get("by_entry_mode", {}).items()
            },
            "recent_actions": actions[:5],  # Last 5 actions
            "active": len(outcomes) > 0,
        }
