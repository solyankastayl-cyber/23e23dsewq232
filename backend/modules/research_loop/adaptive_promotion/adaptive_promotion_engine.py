"""
PHASE 20.3 — Adaptive Promotion Engine
======================================
Main engine for recommending lifecycle transitions.

Combines signals from:
- Factor Governance
- Deployment Governance  
- Failure Pattern Engine
- Factor Weight Adjustment
- Attribution

Outputs:
- Promotion/Demotion/Freeze/Retire recommendations
- Summary of all decisions
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from modules.research_loop.adaptive_promotion.adaptive_promotion_types import (
    LifecycleState,
    TransitionAction,
    TransitionStrength,
    AdaptivePromotionDecision,
    AdaptivePromotionSummary,
    ALLOWED_TRANSITIONS,
)
from modules.research_loop.adaptive_promotion.adaptive_promotion_policy import (
    get_adaptive_promotion_policy,
    AdaptivePromotionPolicy,
)
from modules.research_loop.adaptive_promotion.adaptive_promotion_registry import (
    get_adaptive_promotion_registry,
    AdaptivePromotionRegistry,
)

# Import dependent engines
from modules.research_loop.failure_patterns import (
    get_failure_pattern_engine,
    PatternSeverity,
)
from modules.research_loop.factor_weight_adjustment import (
    get_factor_weight_adjustment_engine,
)


class AdaptivePromotionEngine:
    """
    Adaptive Promotion/Demotion Engine - PHASE 20.3
    
    Recommends lifecycle state transitions for factors based on
    governance, failure patterns, and weight adjustments.
    
    Note: This is a RECOMMENDATION engine. It does not automatically
    execute transitions. Transitions require approval.
    """
    
    def __init__(self):
        """Initialize engine."""
        self.policy = get_adaptive_promotion_policy()
        self.registry = get_adaptive_promotion_registry()
        self.failure_engine = get_failure_pattern_engine()
        self.weight_engine = get_factor_weight_adjustment_engine()
        
        # Cache for governance data
        self._governance_cache: Dict[str, Dict[str, Any]] = {}
        self._deployment_cache: Dict[str, Dict[str, Any]] = {}
    
    # ═══════════════════════════════════════════════════════════
    # MAIN API
    # ═══════════════════════════════════════════════════════════
    
    def compute_all_decisions(self) -> AdaptivePromotionSummary:
        """
        Compute lifecycle decisions for all factors.
        
        Returns AdaptivePromotionSummary with all recommendations.
        """
        now = datetime.now(timezone.utc)
        
        # Build input data
        failure_map = self._build_failure_map()
        weight_map = self._build_weight_adjustment_map()
        
        # Get all factors
        factor_names = self.registry.get_factor_names()
        
        # Compute decisions
        decisions = []
        promoted = []
        demoted = []
        frozen = []
        retired = []
        held = []
        
        for factor_name in factor_names:
            decision = self._compute_factor_decision(
                factor_name=factor_name,
                failure_map=failure_map,
                weight_map=weight_map,
            )
            decisions.append(decision)
            
            # Categorize by action
            if decision.transition_action == TransitionAction.PROMOTE:
                promoted.append(factor_name)
            elif decision.transition_action == TransitionAction.DEMOTE:
                demoted.append(factor_name)
            elif decision.transition_action == TransitionAction.FREEZE:
                frozen.append(factor_name)
            elif decision.transition_action == TransitionAction.RETIRE:
                retired.append(factor_name)
            else:
                held.append(factor_name)
        
        return AdaptivePromotionSummary(
            total_factors=len(decisions),
            promoted=promoted,
            demoted=demoted,
            frozen=frozen,
            retired=retired,
            held=held,
            promote_count=len(promoted),
            demote_count=len(demoted),
            freeze_count=len(frozen),
            retire_count=len(retired),
            hold_count=len(held),
            decisions=decisions,
            timestamp=now,
        )
    
    def compute_factor_decision(
        self,
        factor_name: str,
    ) -> Optional[AdaptivePromotionDecision]:
        """
        Compute decision for a single factor.
        """
        failure_map = self._build_failure_map()
        weight_map = self._build_weight_adjustment_map()
        
        return self._compute_factor_decision(
            factor_name=factor_name,
            failure_map=failure_map,
            weight_map=weight_map,
        )
    
    def apply_decision(
        self,
        decision: AdaptivePromotionDecision,
    ) -> bool:
        """
        Apply a decision to the registry.
        
        Note: In production, this would require governance approval.
        
        Returns True if transition was applied.
        """
        return self.registry.record_transition(decision)
    
    def recompute_all(self) -> AdaptivePromotionSummary:
        """
        Recompute all decisions and apply transitions.
        
        Returns summary of applied changes.
        """
        summary = self.compute_all_decisions()
        
        # Apply non-HOLD decisions
        for decision in summary.decisions:
            if decision.transition_action != TransitionAction.HOLD:
                self.apply_decision(decision)
        
        return summary
    
    def get_factor_state(self, factor_name: str) -> Optional[Dict[str, Any]]:
        """Get current state for a factor."""
        state = self.registry.get_factor_state(factor_name)
        if state is None:
            return None
        return state.to_full_dict()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get current promotion summary without recomputing."""
        summary = self.compute_all_decisions()
        return summary.to_dict()
    
    # ═══════════════════════════════════════════════════════════
    # INTERNAL METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _compute_factor_decision(
        self,
        factor_name: str,
        failure_map: Dict[str, Dict[str, Any]],
        weight_map: Dict[str, Dict[str, Any]],
    ) -> AdaptivePromotionDecision:
        """
        Compute lifecycle decision for a single factor.
        """
        now = datetime.now(timezone.utc)
        
        # Get current state
        current_state = self.registry.get_current_state(factor_name)
        if current_state is None:
            current_state = LifecycleState.SHADOW
        
        # Get governance data (simulated)
        governance = self._get_factor_governance(factor_name)
        deployment = self._get_deployment_governance(factor_name)
        
        # Get failure data
        failure_data = failure_map.get(factor_name, {
            "critical_patterns": 0,
            "high_patterns": 0,
            "total_patterns": 0,
        })
        
        # Get weight adjustment data
        weight_data = weight_map.get(factor_name, {
            "adjustment_action": "HOLD",
            "recommended_weight": 0.1,
        })
        
        # Extract signals
        governance_state = governance.get("governance_state", "STABLE")
        deployment_action = deployment.get("governance_action", "HOLD")
        promotion_readiness = deployment.get("promotion_readiness", 0.5)
        rollback_risk = deployment.get("rollback_risk", 0.3)
        
        critical_failures = failure_data.get("critical_patterns", 0)
        high_failures = failure_data.get("high_patterns", 0)
        
        weight_adjustment_action = weight_data.get("adjustment_action", "HOLD")
        recommended_weight = weight_data.get("recommended_weight", 0.1)
        
        interaction_state = governance.get("interaction_state", "NEUTRAL")
        
        # Determine action priority: RETIRE > FREEZE > DEMOTE > PROMOTE > HOLD
        
        # 1. Check for RETIRE
        should_retire, retire_strength, retire_reason = self.policy.should_retire(
            governance_state=governance_state,
            critical_failures=critical_failures,
            recommended_weight=recommended_weight,
            deployment_action=deployment_action,
        )
        
        if should_retire:
            return self._create_decision(
                factor_name=factor_name,
                current_state=current_state,
                recommended_state=LifecycleState.RETIRED,
                action=TransitionAction.RETIRE,
                strength=retire_strength,
                reason=retire_reason,
                governance_state=governance_state,
                deployment_state=deployment_action,
                failure_count=critical_failures + high_failures,
                critical_failures=critical_failures,
                weight_adjustment_action=weight_adjustment_action,
            )
        
        # 2. Check for FREEZE
        should_freeze, freeze_strength, freeze_reason = self.policy.should_freeze(
            current_state=current_state,
            rollback_risk=rollback_risk,
            deployment_action=deployment_action,
            critical_failures=critical_failures,
            interaction_state=interaction_state,
        )
        
        if should_freeze:
            return self._create_decision(
                factor_name=factor_name,
                current_state=current_state,
                recommended_state=LifecycleState.FROZEN,
                action=TransitionAction.FREEZE,
                strength=freeze_strength,
                reason=freeze_reason,
                governance_state=governance_state,
                deployment_state=deployment_action,
                failure_count=critical_failures + high_failures,
                critical_failures=critical_failures,
                weight_adjustment_action=weight_adjustment_action,
            )
        
        # 3. Check for DEMOTE
        should_demote, demote_strength, demote_reason = self.policy.should_demote(
            current_state=current_state,
            governance_state=governance_state,
            critical_failures=critical_failures,
            high_failures=high_failures,
            weight_adjustment_action=weight_adjustment_action,
            rollback_risk=rollback_risk,
        )
        
        if should_demote:
            demote_target = self.policy.get_next_state_demote(current_state)
            if demote_target and self.policy.is_valid_transition(current_state, demote_target):
                return self._create_decision(
                    factor_name=factor_name,
                    current_state=current_state,
                    recommended_state=demote_target,
                    action=TransitionAction.DEMOTE,
                    strength=demote_strength,
                    reason=demote_reason,
                    governance_state=governance_state,
                    deployment_state=deployment_action,
                    failure_count=critical_failures + high_failures,
                    critical_failures=critical_failures,
                    weight_adjustment_action=weight_adjustment_action,
                )
        
        # 4. Check for PROMOTE
        should_promote, promote_strength, promote_reason = self.policy.should_promote(
            current_state=current_state,
            governance_state=governance_state,
            deployment_action=deployment_action,
            critical_failures=critical_failures,
            weight_adjustment_action=weight_adjustment_action,
            promotion_readiness=promotion_readiness,
        )
        
        if should_promote:
            promote_target = self.policy.get_next_state_promote(current_state)
            if promote_target and self.policy.is_valid_transition(current_state, promote_target):
                return self._create_decision(
                    factor_name=factor_name,
                    current_state=current_state,
                    recommended_state=promote_target,
                    action=TransitionAction.PROMOTE,
                    strength=promote_strength,
                    reason=promote_reason,
                    governance_state=governance_state,
                    deployment_state=deployment_action,
                    failure_count=critical_failures + high_failures,
                    critical_failures=critical_failures,
                    weight_adjustment_action=weight_adjustment_action,
                )
        
        # 5. Default: HOLD
        return self._create_decision(
            factor_name=factor_name,
            current_state=current_state,
            recommended_state=current_state,
            action=TransitionAction.HOLD,
            strength=TransitionStrength.LOW,
            reason="no transition signals met threshold",
            governance_state=governance_state,
            deployment_state=deployment_action,
            failure_count=critical_failures + high_failures,
            critical_failures=critical_failures,
            weight_adjustment_action=weight_adjustment_action,
        )
    
    def _create_decision(
        self,
        factor_name: str,
        current_state: LifecycleState,
        recommended_state: LifecycleState,
        action: TransitionAction,
        strength: TransitionStrength,
        reason: str,
        governance_state: str,
        deployment_state: str,
        failure_count: int,
        critical_failures: int,
        weight_adjustment_action: str,
    ) -> AdaptivePromotionDecision:
        """Create a decision with calculated modifiers."""
        conf_mod, cap_mod = self.policy.calculate_modifiers(
            action=action,
            strength=strength,
            current_state=current_state,
            recommended_state=recommended_state,
        )
        
        return AdaptivePromotionDecision(
            factor_name=factor_name,
            current_state=current_state,
            recommended_state=recommended_state,
            transition_action=action,
            transition_strength=strength,
            confidence_modifier=conf_mod,
            capital_modifier=cap_mod,
            reason=reason,
            governance_state=governance_state,
            deployment_state=deployment_state,
            failure_count=failure_count,
            critical_failures=critical_failures,
            weight_adjustment_action=weight_adjustment_action,
        )
    
    # ═══════════════════════════════════════════════════════════
    # DATA BUILDERS
    # ═══════════════════════════════════════════════════════════
    
    def _build_failure_map(self) -> Dict[str, Dict[str, Any]]:
        """Build map of factor → failure statistics."""
        failure_summary = self.failure_engine.analyze_trades()
        
        factor_map: Dict[str, Dict[str, Any]] = {}
        
        for pattern in failure_summary.patterns:
            factor = pattern.involved_factor
            
            if factor not in factor_map:
                factor_map[factor] = {
                    "total_patterns": 0,
                    "critical_patterns": 0,
                    "high_patterns": 0,
                }
            
            factor_map[factor]["total_patterns"] += 1
            
            if pattern.severity == PatternSeverity.CRITICAL:
                factor_map[factor]["critical_patterns"] += 1
            elif pattern.severity == PatternSeverity.HIGH:
                factor_map[factor]["high_patterns"] += 1
        
        return factor_map
    
    def _build_weight_adjustment_map(self) -> Dict[str, Dict[str, Any]]:
        """Build map of factor → weight adjustment data."""
        weight_summary = self.weight_engine.compute_adjustments()
        
        weight_map: Dict[str, Dict[str, Any]] = {}
        
        for adjustment in weight_summary.adjustments:
            weight_map[adjustment.factor_name] = {
                "adjustment_action": adjustment.adjustment_action.value,
                "recommended_weight": adjustment.recommended_weight,
                "weight_delta": adjustment.weight_delta,
            }
        
        return weight_map
    
    def _get_factor_governance(self, factor_name: str) -> Dict[str, Any]:
        """
        Get factor governance data.
        
        In production, this would call FactorGovernanceEngine.
        For now, returns simulated data based on factor patterns.
        """
        if factor_name in self._governance_cache:
            return self._governance_cache[factor_name]
        
        # Simulate governance based on factor name patterns
        if "breakout" in factor_name:
            governance = {
                "governance_state": "WATCHLIST",
                "governance_score": 0.58,
                "interaction_state": "NEUTRAL",
            }
        elif "mean_reversion" in factor_name:
            governance = {
                "governance_state": "STABLE",
                "governance_score": 0.72,
                "interaction_state": "REINFORCED",
            }
        elif "flow" in factor_name:
            governance = {
                "governance_state": "ELITE",
                "governance_score": 0.88,
                "interaction_state": "REINFORCED",
            }
        elif "funding" in factor_name:
            governance = {
                "governance_state": "STABLE",
                "governance_score": 0.75,
                "interaction_state": "NEUTRAL",
            }
        elif "structure" in factor_name:
            governance = {
                "governance_state": "DEGRADED",
                "governance_score": 0.45,
                "interaction_state": "CONFLICTED",
            }
        elif "volatility" in factor_name:
            governance = {
                "governance_state": "STABLE",
                "governance_score": 0.70,
                "interaction_state": "NEUTRAL",
            }
        elif "momentum" in factor_name:
            governance = {
                "governance_state": "STABLE",
                "governance_score": 0.73,
                "interaction_state": "REINFORCED",
            }
        elif "liquidation" in factor_name:
            governance = {
                "governance_state": "WATCHLIST",
                "governance_score": 0.55,
                "interaction_state": "CANCELLED",
            }
        elif "correlation" in factor_name:
            governance = {
                "governance_state": "ELITE",
                "governance_score": 0.85,
                "interaction_state": "REINFORCED",
            }
        else:
            governance = {
                "governance_state": "STABLE",
                "governance_score": 0.65,
                "interaction_state": "NEUTRAL",
            }
        
        self._governance_cache[factor_name] = governance
        return governance
    
    def _get_deployment_governance(self, factor_name: str) -> Dict[str, Any]:
        """
        Get deployment governance data.
        
        In production, this would call DeploymentGovernanceEngine.
        """
        if factor_name in self._deployment_cache:
            return self._deployment_cache[factor_name]
        
        # Get current state
        current_state = self.registry.get_current_state(factor_name)
        
        # Simulate deployment data
        if current_state == LifecycleState.SHADOW:
            deployment = {
                "governance_action": "HOLD",
                "promotion_readiness": 0.55,
                "rollback_risk": 0.20,
            }
        elif current_state == LifecycleState.CANDIDATE:
            deployment = {
                "governance_action": "PROMOTE",
                "promotion_readiness": 0.72,
                "rollback_risk": 0.25,
            }
        elif current_state == LifecycleState.LIVE:
            deployment = {
                "governance_action": "HOLD",
                "promotion_readiness": 0.80,
                "rollback_risk": 0.30,
            }
        elif current_state == LifecycleState.REDUCED:
            deployment = {
                "governance_action": "HOLD",
                "promotion_readiness": 0.50,
                "rollback_risk": 0.45,
            }
        else:
            deployment = {
                "governance_action": "HOLD",
                "promotion_readiness": 0.40,
                "rollback_risk": 0.35,
            }
        
        # Adjust based on factor patterns
        if "structure" in factor_name:
            deployment["governance_action"] = "REDUCE"
            deployment["rollback_risk"] = 0.55
        elif "flow" in factor_name:
            deployment["governance_action"] = "PROMOTE"
            deployment["promotion_readiness"] = 0.85
        
        self._deployment_cache[factor_name] = deployment
        return deployment


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[AdaptivePromotionEngine] = None


def get_adaptive_promotion_engine() -> AdaptivePromotionEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = AdaptivePromotionEngine()
    return _engine
