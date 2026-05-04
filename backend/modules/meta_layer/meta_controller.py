"""
Meta Controller - ORCH-7
=========================

Main orchestrator for multi-strategy capital allocation.

Coordinates:
- Strategy Registry (what strategies exist)
- Strategy Score Engine (how good are they)
- Strategy Allocator (how much capital each gets)
- Strategy Policy Engine (what actions to take)
"""

import logging
from typing import Dict, Any, List

from .strategy_registry import get_strategy_registry
from .strategy_score_engine import get_strategy_score_engine
from .strategy_allocator import get_strategy_allocator
from .strategy_policy_engine import get_strategy_policy_engine

logger = logging.getLogger(__name__)


class MetaController:
    """Main meta-level orchestrator for ORCH-7."""
    
    def __init__(self, audit_controller=None):
        self.registry = get_strategy_registry()
        self.score_engine = get_strategy_score_engine()
        self.allocator = get_strategy_allocator()
        self.policy_engine = get_strategy_policy_engine()
        self.audit_controller = audit_controller  # P0.7
    
    def run(
        self,
        strategy_metrics: Dict[str, Dict[str, Any]],
        regime: Dict[str, Any],
        total_capital: float,
        alpha_feedback_actions: List[Dict[str, Any]] = None,  # ORCH-7 PHASE 5
        trace_id: str = None  # P0.7: Audit trace ID
    ) -> Dict[str, Any]:
        """
        Run meta-level orchestration.
        
        Args:
            strategy_metrics: Dict of {strategy_id: metrics}
            regime: Current market regime
            total_capital: Total capital available
        
        Returns:
            Meta state with scores, allocations, actions
        """
        from datetime import datetime, timezone
        
        logger.info(f"[MetaController] Running with ${total_capital:,.2f} capital")
        
        # 1. Get enabled strategies
        enabled_strategies = self.registry.list_enabled()
        
        if not enabled_strategies:
            logger.warning("[MetaController] No enabled strategies")
            return {
                "scores": [],
                "allocations": [],
                "actions": [],
                "total_capital": total_capital,
            }
        
        # 2. Compute scores for all strategies
        scores = self.score_engine.compute_all(
            strategies=enabled_strategies,
            strategy_metrics=strategy_metrics,
            regime=regime
        )
        
        # 3. Allocate capital based on scores
        allocations = self.allocator.allocate(
            scores=scores,
            total_capital=total_capital
        )
        
        # 4. Generate policy actions from allocations
        policy_actions = self.policy_engine.generate_actions(allocations)
        
        # P0.7: STRATEGY AUDIT (Hook 3) - Log policy actions
        if self.audit_controller:
            from modules.audit.audit_helper import run_audit_task
            for action in policy_actions:
                run_audit_task(
                    self.audit_controller.strategy.insert({
                        "timestamp": datetime.now(timezone.utc),
                        "trace_id": trace_id,  # P0.7 CRITICAL: trace ID
                        "strategy_id": action.get("strategy_id"),
                        "action_type": action.get("type"),
                        "reason": action.get("reason"),
                        "confidence": action.get("confidence"),
                        "source": "META_POLICY",
                        "capital_allocated": action.get("capital_allocated"),
                        "score": action.get("score")
                    }),
                    context=f"strategy_audit_{action.get('strategy_id')}"
                )
        
        # ORCH-7 PHASE 5: Merge alpha feedback actions
        alpha_actions = alpha_feedback_actions or []
        
        # P0.7: STRATEGY AUDIT (Hook 3) - Log alpha actions
        if self.audit_controller and alpha_actions:
            from modules.audit.audit_helper import run_audit_task
            for action in alpha_actions:
                run_audit_task(
                    self.audit_controller.strategy.insert({
                        "timestamp": datetime.now(timezone.utc),
                        "trace_id": trace_id,  # P0.7 CRITICAL: trace ID
                        "strategy_id": action.get("strategy_id"),
                        "action_type": action.get("type"),
                        "reason": action.get("reason"),
                        "confidence": action.get("confidence"),
                        "source": "AF6_ALPHA",
                        "score": action.get("score")
                    }),
                    context=f"alpha_audit_{action.get('strategy_id')}"
                )
        
        all_actions = [*policy_actions, *alpha_actions]
        
        logger.info(
            f"[MetaController] Complete: {len(scores)} scores, "
            f"{len(allocations)} allocations, {len(policy_actions)} policy actions, "
            f"{len(alpha_actions)} alpha actions"
        )
        
        return {
            "scores": scores,
            "allocations": allocations,
            "actions": all_actions,  # Combined actions
            "alpha_actions": alpha_actions,  # Separate for visibility
            "policy_actions": policy_actions,  # Separate for visibility
            "total_capital": total_capital,
            "strategies_count": len(enabled_strategies),
        }


# Singleton instance
_controller: MetaController = None
_audit_controller_ref_meta = None  # P0.7


def set_audit_controller_for_meta(audit_controller):
    """Set audit controller reference for meta controller (P0.7)"""
    global _audit_controller_ref_meta, _controller
    _audit_controller_ref_meta = audit_controller
    
    # If controller already exists, set audit_controller directly
    if _controller is not None:
        _controller.audit_controller = audit_controller
        logger.info("Audit controller set on existing MetaController instance")
    else:
        logger.info("Audit controller ref saved for future MetaController creation")


def get_meta_controller() -> MetaController:
    """Get or create singleton meta controller."""
    global _controller
    if _controller is None:
        _controller = MetaController(audit_controller=_audit_controller_ref_meta)
    return _controller
