"""
PHASE 3.2 — Policy Evaluator

Evaluates individual actions against policy rules.
Determines if action should be allowed, filtered, or blocked.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

from .policy_config import PolicyConfig


class PolicyDecision(Enum):
    """Policy decision types."""
    ALLOW = "allow"
    BLOCK = "block"
    DEFER = "defer"  # Blocked but can retry later


@dataclass
class PolicyEvaluation:
    """Result of policy evaluation for an action."""
    action: Dict
    decision: PolicyDecision
    reason: str
    details: Dict
    priority: int  # Lower = higher priority


class PolicyEvaluator:
    """
    Evaluates actions against policy rules.
    
    Checks:
    - Confidence thresholds
    - Per-action-type limits
    - Cooldowns
    - Emergency mode restrictions
    - Global constraints
    """
    
    def __init__(self, config: PolicyConfig):
        self.config = config
        self._last_cycle_time: Optional[datetime] = None
        self._action_counts: Dict[str, int] = {}
        self._target_last_action: Dict[str, datetime] = {}
    
    def evaluate(
        self,
        action: Dict,
        current_state: Dict,
        emergency_mode: bool = False
    ) -> PolicyEvaluation:
        """
        Evaluate single action against policy.
        
        Args:
            action: Action to evaluate
            current_state: Current adaptive state
            emergency_mode: Whether system is in emergency mode
        
        Returns:
            PolicyEvaluation with decision and details
        """
        action_type = action.get("action", "")
        target_id = action.get("target_id", "")
        confidence = action.get("confidence", 0.0)
        
        # Get priority
        priority = self._get_priority(action_type)
        
        # Check emergency mode
        if emergency_mode and action_type not in self.config.emergency_allowed_actions:
            return PolicyEvaluation(
                action=action,
                decision=PolicyDecision.BLOCK,
                reason="emergency_mode_restriction",
                details={
                    "action_type": action_type,
                    "allowed_in_emergency": self.config.emergency_allowed_actions
                },
                priority=priority
            )
        
        # Check confidence threshold
        conf_check = self._check_confidence(action_type, confidence)
        if not conf_check["passed"]:
            return PolicyEvaluation(
                action=action,
                decision=PolicyDecision.BLOCK,
                reason="confidence_below_threshold",
                details=conf_check,
                priority=priority
            )
        
        # Check per-type limits
        limit_check = self._check_action_type_limit(action_type)
        if not limit_check["passed"]:
            return PolicyEvaluation(
                action=action,
                decision=PolicyDecision.DEFER,
                reason="action_type_limit_reached",
                details=limit_check,
                priority=priority
            )
        
        # Check target cooldown
        cooldown_check = self._check_target_cooldown(target_id)
        if not cooldown_check["passed"]:
            return PolicyEvaluation(
                action=action,
                decision=PolicyDecision.DEFER,
                reason="target_in_cooldown",
                details=cooldown_check,
                priority=priority
            )
        
        # Check global constraints
        constraint_check = self._check_global_constraints(action, current_state)
        if not constraint_check["passed"]:
            return PolicyEvaluation(
                action=action,
                decision=PolicyDecision.BLOCK,
                reason="global_constraint_violation",
                details=constraint_check,
                priority=priority
            )
        
        # All checks passed
        return PolicyEvaluation(
            action=action,
            decision=PolicyDecision.ALLOW,
            reason="policy_passed",
            details={"checks_passed": ["confidence", "limits", "cooldown", "constraints"]},
            priority=priority
        )
    
    def evaluate_batch(
        self,
        actions: List[Dict],
        current_state: Dict,
        emergency_mode: bool = False
    ) -> Dict:
        """
        Evaluate batch of actions.
        
        Returns:
            {
                "allowed": [...],
                "blocked": [...],
                "deferred": [...],
                "summary": {...}
            }
        """
        allowed = []
        blocked = []
        deferred = []
        
        # Reset counters for new batch
        self._action_counts = {}
        
        # Sort by priority
        sorted_actions = sorted(
            actions,
            key=lambda a: self._get_priority(a.get("action", ""))
        )
        
        total_allowed = 0
        
        for action in sorted_actions:
            # Check total actions limit
            if total_allowed >= self.config.max_actions_per_cycle:
                deferred.append({
                    "action": action,
                    "reason": "max_actions_per_cycle_reached",
                    "limit": self.config.max_actions_per_cycle
                })
                continue
            
            evaluation = self.evaluate(action, current_state, emergency_mode)
            
            if evaluation.decision == PolicyDecision.ALLOW:
                allowed.append({
                    "action": action,
                    "priority": evaluation.priority,
                    "details": evaluation.details
                })
                
                # Update counters
                action_type = action.get("action", "")
                self._action_counts[action_type] = self._action_counts.get(action_type, 0) + 1
                total_allowed += 1
                
                # Record target action time
                target_id = action.get("target_id", "")
                self._target_last_action[target_id] = datetime.now(timezone.utc)
            
            elif evaluation.decision == PolicyDecision.BLOCK:
                blocked.append({
                    "action": action,
                    "reason": evaluation.reason,
                    "details": evaluation.details
                })
            
            else:  # DEFER
                deferred.append({
                    "action": action,
                    "reason": evaluation.reason,
                    "details": evaluation.details
                })
        
        return {
            "allowed": allowed,
            "blocked": blocked,
            "deferred": deferred,
            "summary": {
                "total_input": len(actions),
                "allowed_count": len(allowed),
                "blocked_count": len(blocked),
                "deferred_count": len(deferred),
                "action_counts": dict(self._action_counts),
                "emergency_mode": emergency_mode
            }
        }
    
    def _check_confidence(self, action_type: str, confidence: float) -> Dict:
        """Check if confidence meets threshold for action type."""
        # Get appropriate threshold
        if action_type == "disable":
            threshold = self.config.min_confidence_for_disable
        elif action_type == "increase_allocation":
            threshold = self.config.min_confidence_for_increase_allocation
        else:
            threshold = self.config.min_confidence_to_apply
        
        passed = confidence >= threshold
        
        return {
            "passed": passed,
            "confidence": confidence,
            "threshold": threshold,
            "action_type": action_type
        }
    
    def _check_action_type_limit(self, action_type: str) -> Dict:
        """Check if action type limit has been reached."""
        current_count = self._action_counts.get(action_type, 0)
        
        limits = {
            "disable": self.config.max_disable_per_cycle,
            "reduce_risk": self.config.max_reduce_risk_per_cycle,
            "increase_threshold": self.config.max_increase_threshold_per_cycle,
            "increase_allocation": self.config.max_increase_allocation_per_cycle,
            "cut_cluster_exposure": self.config.max_cut_cluster_per_cycle,
            "keep": 999  # No limit on keep
        }
        
        limit = limits.get(action_type, self.config.max_actions_per_cycle)
        passed = current_count < limit
        
        return {
            "passed": passed,
            "action_type": action_type,
            "current_count": current_count,
            "limit": limit
        }
    
    def _check_target_cooldown(self, target_id: str) -> Dict:
        """Check if target is in cooldown period."""
        now = datetime.now(timezone.utc)
        
        if target_id in self._target_last_action:
            last_action = self._target_last_action[target_id]
            cooldown_end = last_action + timedelta(hours=self.config.per_target_cooldown_hours)
            
            if now < cooldown_end:
                remaining = (cooldown_end - now).total_seconds() / 3600
                return {
                    "passed": False,
                    "target": target_id,
                    "cooldown_remaining_hours": round(remaining, 1),
                    "last_action": last_action.isoformat()
                }
        
        return {"passed": True, "target": target_id}
    
    def _check_global_constraints(self, action: Dict, state: Dict) -> Dict:
        """Check global system constraints."""
        action_type = action.get("action", "")
        target_id = action.get("target_id", "")
        
        # Check max disabled assets
        if action_type == "disable":
            disabled = state.get("disabled_assets", [])
            if len(disabled) >= self.config.max_assets_disabled_total:
                return {
                    "passed": False,
                    "constraint": "max_assets_disabled_total",
                    "current": len(disabled),
                    "limit": self.config.max_assets_disabled_total
                }
            
            # Check min enabled assets
            enabled = state.get("enabled_assets", [])
            if len(enabled) <= self.config.min_enabled_assets:
                return {
                    "passed": False,
                    "constraint": "min_enabled_assets",
                    "current": len(enabled),
                    "minimum": self.config.min_enabled_assets
                }
        
        # Check max risk reduction
        if action_type == "reduce_risk":
            risk_map = state.get("risk_multipliers", {})
            current_risk = risk_map.get(target_id, 1.0)
            new_risk = current_risk * 0.8
            
            if new_risk < self.config.max_risk_reduction_per_asset:
                return {
                    "passed": False,
                    "constraint": "max_risk_reduction",
                    "current": current_risk,
                    "proposed": new_risk,
                    "limit": self.config.max_risk_reduction_per_asset
                }
        
        # Check max threshold
        if action_type == "increase_threshold":
            thresholds = state.get("confidence_thresholds", {})
            current = thresholds.get(target_id, 0.5)
            new_threshold = current + 0.05
            
            if new_threshold > self.config.max_threshold_per_asset:
                return {
                    "passed": False,
                    "constraint": "max_threshold",
                    "current": current,
                    "proposed": new_threshold,
                    "limit": self.config.max_threshold_per_asset
                }
        
        return {"passed": True}
    
    def _get_priority(self, action_type: str) -> int:
        """Get priority for action type (lower = higher priority)."""
        try:
            return self.config.action_priority_order.index(action_type)
        except ValueError:
            return len(self.config.action_priority_order)
    
    def reset_counters(self):
        """Reset action counters for new cycle."""
        self._action_counts = {}
    
    def record_cycle(self):
        """Record cycle execution time."""
        self._last_cycle_time = datetime.now(timezone.utc)
    
    def can_start_cycle(self) -> Tuple[bool, Optional[str]]:
        """Check if new cycle can start (cooldown check)."""
        if self._last_cycle_time is None:
            return True, None
        
        now = datetime.now(timezone.utc)
        cooldown_end = self._last_cycle_time + timedelta(hours=self.config.cycle_cooldown_hours)
        
        if now < cooldown_end:
            remaining = (cooldown_end - now).total_seconds() / 3600
            return False, f"Cycle cooldown active. {remaining:.1f} hours remaining."
        
        return True, None
