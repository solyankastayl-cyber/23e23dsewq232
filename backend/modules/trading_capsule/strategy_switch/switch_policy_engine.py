"""
Switch Policy Engine (STR3)
===========================

Core engine for evaluating switch policies.

Features:
- Policy evaluation against context
- Priority-based decision making
- Multi-policy conflict resolution
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .switch_types import (
    SwitchPolicy,
    SwitchContext,
    SwitchDecision,
    SwitchTriggerType,
    SwitchPriority
)
from .switch_policy_registry import (
    get_enabled_policies,
    get_policy,
    get_policies_by_type
)


class SwitchPolicyEngine:
    """
    Policy Engine for strategy switching.
    
    Evaluates all enabled policies against current context
    and returns the highest priority switch decision.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._evaluation_history: List[SwitchDecision] = []
        self._initialized = True
        print("[SwitchPolicyEngine] Initialized")
    
    # ===========================================
    # Policy Evaluation
    # ===========================================
    
    def evaluate(self, context: SwitchContext) -> SwitchDecision:
        """
        Evaluate all enabled policies and return the highest priority decision.
        
        Args:
            context: Current switch context with all metrics
        
        Returns:
            SwitchDecision with the result
        """
        enabled_policies = get_enabled_policies()
        
        # Filter out MANUAL policies (they're explicit triggers)
        policies_to_evaluate = [
            p for p in enabled_policies 
            if p.trigger_type != SwitchTriggerType.MANUAL
        ]
        
        # Evaluate each policy
        triggered_policies: List[SwitchPolicy] = []
        context_dict = context.to_flat_dict()
        
        for policy in policies_to_evaluate:
            try:
                if policy.evaluate(context_dict):
                    triggered_policies.append(policy)
            except Exception as e:
                print(f"[SwitchPolicyEngine] Error evaluating {policy.name}: {e}")
        
        # No policies triggered
        if not triggered_policies:
            return SwitchDecision(
                should_switch=False,
                reason="No policies triggered",
                evaluated_at=datetime.now(timezone.utc)
            )
        
        # Sort by priority (lower value = higher priority)
        triggered_policies.sort(key=lambda p: p.priority.value)
        
        # Return highest priority policy decision
        winner = triggered_policies[0]
        
        decision = SwitchDecision(
            should_switch=True,
            target_profile=winner.target_profile,
            triggered_by_policy_id=winner.policy_id,
            triggered_by_policy_name=winner.name,
            trigger_type=winner.trigger_type,
            reason=f"Policy '{winner.name}' triggered",
            matched_conditions=[c.description for c in winner.conditions] if winner.conditions else [],
            priority=winner.priority.value,
            evaluated_at=datetime.now(timezone.utc)
        )
        
        # Update policy last_triggered
        winner.last_triggered = datetime.now(timezone.utc)
        
        # Store in history
        self._evaluation_history.append(decision)
        if len(self._evaluation_history) > 100:
            self._evaluation_history = self._evaluation_history[-100:]
        
        return decision
    
    def evaluate_specific(
        self, 
        policy_id: str, 
        context: SwitchContext
    ) -> SwitchDecision:
        """
        Evaluate a specific policy.
        
        Args:
            policy_id: Policy ID or name
            context: Switch context
        
        Returns:
            SwitchDecision for that specific policy
        """
        policy = get_policy(policy_id)
        
        if not policy:
            return SwitchDecision(
                should_switch=False,
                reason=f"Policy '{policy_id}' not found",
                evaluated_at=datetime.now(timezone.utc)
            )
        
        context_dict = context.to_flat_dict()
        
        if policy.evaluate(context_dict):
            return SwitchDecision(
                should_switch=True,
                target_profile=policy.target_profile,
                triggered_by_policy_id=policy.policy_id,
                triggered_by_policy_name=policy.name,
                trigger_type=policy.trigger_type,
                reason=f"Policy '{policy.name}' conditions met",
                matched_conditions=[c.description for c in policy.conditions] if policy.conditions else [],
                priority=policy.priority.value,
                evaluated_at=datetime.now(timezone.utc)
            )
        
        return SwitchDecision(
            should_switch=False,
            reason=f"Policy '{policy.name}' conditions not met",
            triggered_by_policy_id=policy.policy_id,
            triggered_by_policy_name=policy.name,
            evaluated_at=datetime.now(timezone.utc)
        )
    
    def evaluate_rules(self, context: SwitchContext) -> List[SwitchDecision]:
        """
        Evaluate only RULE type policies.
        
        Returns all matching decisions (not just highest priority).
        """
        rule_policies = get_policies_by_type(SwitchTriggerType.RULE)
        context_dict = context.to_flat_dict()
        
        decisions = []
        
        for policy in rule_policies:
            if policy.evaluate(context_dict):
                decisions.append(SwitchDecision(
                    should_switch=True,
                    target_profile=policy.target_profile,
                    triggered_by_policy_id=policy.policy_id,
                    triggered_by_policy_name=policy.name,
                    trigger_type=policy.trigger_type,
                    reason=f"Rule policy '{policy.name}' triggered",
                    matched_conditions=[c.description for c in policy.conditions],
                    priority=policy.priority.value,
                    evaluated_at=datetime.now(timezone.utc)
                ))
        
        return decisions
    
    def evaluate_schedules(self, context: SwitchContext) -> List[SwitchDecision]:
        """
        Evaluate only SCHEDULE type policies.
        
        Returns all active scheduled decisions.
        """
        schedule_policies = get_policies_by_type(SwitchTriggerType.SCHEDULE)
        
        decisions = []
        
        for policy in schedule_policies:
            if policy.schedule and policy.schedule.is_active():
                decisions.append(SwitchDecision(
                    should_switch=True,
                    target_profile=policy.target_profile,
                    triggered_by_policy_id=policy.policy_id,
                    triggered_by_policy_name=policy.name,
                    trigger_type=policy.trigger_type,
                    reason=f"Scheduled policy '{policy.name}' is active",
                    priority=policy.priority.value,
                    evaluated_at=datetime.now(timezone.utc)
                ))
        
        return decisions
    
    # ===========================================
    # Context Building
    # ===========================================
    
    def build_context(
        self,
        current_profile: str = "BALANCED",
        current_config_id: str = "",
        portfolio_metrics: Optional[Dict[str, float]] = None,
        market_metrics: Optional[Dict[str, Any]] = None,
        activity_metrics: Optional[Dict[str, Any]] = None
    ) -> SwitchContext:
        """
        Build a SwitchContext from various sources.
        
        Args:
            current_profile: Current active profile mode
            current_config_id: Current config ID
            portfolio_metrics: Dict with daily_loss_pct, drawdown_pct, etc.
            market_metrics: Dict with volatility_score, regime, etc.
            activity_metrics: Dict with trades_today, consecutive_losses, etc.
        
        Returns:
            SwitchContext ready for evaluation
        """
        now = datetime.now(timezone.utc)
        day_names = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", 
                     "FRIDAY", "SATURDAY", "SUNDAY"]
        
        context = SwitchContext(
            current_profile=current_profile,
            current_config_id=current_config_id,
            timestamp=now,
            day_of_week=day_names[now.weekday()],
            hour=now.hour
        )
        
        # Portfolio metrics
        if portfolio_metrics:
            context.daily_loss_pct = portfolio_metrics.get("daily_loss_pct", 0.0)
            context.portfolio_drawdown_pct = portfolio_metrics.get("drawdown_pct", 0.0)
            context.total_exposure_pct = portfolio_metrics.get("exposure_pct", 0.0)
            context.unrealized_pnl_pct = portfolio_metrics.get("unrealized_pnl_pct", 0.0)
        
        # Market metrics
        if market_metrics:
            context.volatility_score = market_metrics.get("volatility_score", 0.0)
            context.market_regime = market_metrics.get("regime", "NEUTRAL")
            context.btc_24h_change_pct = market_metrics.get("btc_24h_change_pct", 0.0)
        
        # Activity metrics
        if activity_metrics:
            context.trades_today = activity_metrics.get("trades_today", 0)
            context.consecutive_losses = activity_metrics.get("consecutive_losses", 0)
            context.win_rate_today = activity_metrics.get("win_rate_today", 0.0)
        
        return context
    
    # ===========================================
    # History
    # ===========================================
    
    def get_evaluation_history(self, limit: int = 50) -> List[SwitchDecision]:
        """Get recent evaluation history"""
        return list(reversed(self._evaluation_history[-limit:]))
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health status"""
        enabled = len(get_enabled_policies())
        
        return {
            "service": "SwitchPolicyEngine",
            "status": "healthy",
            "version": "str3",
            "enabled_policies": enabled,
            "evaluations_in_memory": len(self._evaluation_history)
        }


# Global singleton
switch_policy_engine = SwitchPolicyEngine()
