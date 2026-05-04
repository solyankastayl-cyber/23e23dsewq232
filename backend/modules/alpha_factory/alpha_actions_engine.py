"""
AF1 - Alpha Actions Engine
==========================
Generates recommended actions based on evaluations.
"""

from typing import List, Tuple, Dict, Any
from .alpha_models import AlphaAction, utc_now


class AlphaActionsEngine:
    """Generates recommended actions from evaluations"""
    
    def build_actions(self, evaluations: List[Dict[str, Any]]) -> List[AlphaAction]:
        """Generate actions for all evaluations"""
        actions = []

        for e in evaluations:
            action, magnitude, reason, priority, auto_apply = self._decide(e)
            
            actions.append(
                AlphaAction(
                    scope=e["scope"],
                    scope_key=e["scope_key"],
                    action=action,
                    magnitude=magnitude,
                    reason=reason,
                    priority=priority,
                    auto_apply=auto_apply,
                    created_at=utc_now(),
                )
            )

        # Sort by priority (lower = more urgent)
        actions.sort(key=lambda x: x.priority)
        return actions

    def _decide(self, e: Dict[str, Any]) -> Tuple[str, float, str, int, bool]:
        """
        Decide action based on evaluation.
        
        Returns: (action, magnitude, reason, priority, auto_apply)
        """
        scope = e.get("scope")
        verdict = e.get("verdict")
        confidence = float(e.get("confidence", 0) or 0)
        is_actionable = e.get("is_actionable", True)
        
        # Not enough data - keep monitoring
        if not is_actionable:
            return "KEEP", 0.0, "insufficient_sample_size", 4, False

        # === Symbol scope actions ===
        if scope == "symbol":
            if verdict == "STRONG_EDGE":
                return "INCREASE_ALLOCATION", 0.10, "strong_edge_detected", 4, confidence > 0.70
            
            if verdict == "WEAK_EDGE":
                return "KEEP", 0.0, "weak_but_positive_edge", 4, False
            
            if verdict == "UNSTABLE_EDGE":
                return "REDUCE_RISK", 0.15, "unstable_edge_detected", 2, confidence > 0.60
            
            if verdict == "NO_EDGE":
                # High confidence = can auto-disable
                auto = confidence > 0.75
                return "DISABLE_SYMBOL", 1.0, "no_edge_detected", 1, auto

        # === Entry mode scope actions ===
        if scope == "entry_mode":
            if verdict == "STRONG_EDGE":
                return "UPGRADE_ENTRY_MODE", 0.10, "entry_mode_strong", 4, False
            
            if verdict == "WEAK_EDGE":
                return "KEEP", 0.0, "entry_mode_acceptable", 4, False
            
            if verdict == "UNSTABLE_EDGE":
                return "INCREASE_THRESHOLD", 0.10, "entry_mode_unstable", 3, False
            
            if verdict == "NO_EDGE":
                return "DOWNGRADE_ENTRY_MODE", 0.20, "entry_mode_no_edge", 2, False

        # Default: keep
        return "KEEP", 0.0, "default_keep", 4, False

    def filter_actionable(self, actions: List[AlphaAction]) -> List[AlphaAction]:
        """Filter to only actions that require attention (not KEEP)"""
        return [a for a in actions if a.action != "KEEP"]

    def filter_auto_applicable(self, actions: List[AlphaAction]) -> List[AlphaAction]:
        """Filter to only actions that can be auto-applied"""
        return [a for a in actions if a.auto_apply and a.action != "KEEP"]

    def get_action_summary(self, actions: List[AlphaAction]) -> Dict[str, int]:
        """Get counts by action type"""
        summary = {}
        for a in actions:
            summary[a.action] = summary.get(a.action, 0) + 1
        return summary
