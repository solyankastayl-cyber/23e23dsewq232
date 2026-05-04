"""
PHASE 20.3 — Adaptive Promotion Policy
======================================
Rules for determining lifecycle transitions.

Transition Rules:
- Promote: Move to higher state
- Demote: Move to lower state  
- Freeze: Temporarily disable
- Retire: Permanently disable
- Hold: Keep current state
"""

from typing import Tuple, Optional
from modules.research_loop.adaptive_promotion.adaptive_promotion_types import (
    LifecycleState,
    TransitionAction,
    TransitionStrength,
    ALLOWED_TRANSITIONS,
)


class AdaptivePromotionPolicy:
    """
    Policy engine for lifecycle transitions.
    
    Determines transition actions based on governance signals.
    """
    
    # ═══════════════════════════════════════════════════════════
    # PROMOTION RULES
    # ═══════════════════════════════════════════════════════════
    
    def should_promote(
        self,
        current_state: LifecycleState,
        governance_state: str,
        deployment_action: str,
        critical_failures: int,
        weight_adjustment_action: str,
        promotion_readiness: float,
    ) -> Tuple[bool, TransitionStrength, str]:
        """
        Determine if factor should be promoted.
        
        Promotion conditions:
        - current_state = SHADOW or CANDIDATE
        - deployment says PROMOTE
        - governance STABLE or ELITE
        - no critical failure patterns
        - weight adjustment not negative
        - promotion_readiness >= 0.65
        
        Returns:
            (should_promote, strength, reason)
        """
        # Cannot promote from LIVE, FROZEN, RETIRED
        if current_state not in [LifecycleState.SHADOW, LifecycleState.CANDIDATE, LifecycleState.REDUCED]:
            return False, TransitionStrength.LOW, "not in promotable state"
        
        # Check deployment action
        if deployment_action not in ["PROMOTE", "HOLD"]:
            return False, TransitionStrength.LOW, f"deployment action is {deployment_action}"
        
        # Check governance
        if governance_state not in ["ELITE", "STABLE"]:
            return False, TransitionStrength.LOW, f"governance {governance_state} not stable"
        
        # Check critical failures
        if critical_failures > 0:
            return False, TransitionStrength.LOW, f"{critical_failures} critical failures exist"
        
        # Check weight adjustment
        if weight_adjustment_action in ["DECREASE", "SHADOW", "RETIRE"]:
            return False, TransitionStrength.LOW, f"weight action is {weight_adjustment_action}"
        
        # Check promotion readiness
        if promotion_readiness < 0.65:
            return False, TransitionStrength.LOW, f"promotion readiness {promotion_readiness:.2f} < 0.65"
        
        # Determine strength
        if governance_state == "ELITE" and promotion_readiness >= 0.85:
            strength = TransitionStrength.HIGH
        elif promotion_readiness >= 0.75:
            strength = TransitionStrength.MEDIUM
        else:
            strength = TransitionStrength.LOW
        
        reason = f"stable governance ({governance_state}), promotion readiness {promotion_readiness:.2f}"
        return True, strength, reason
    
    # ═══════════════════════════════════════════════════════════
    # DEMOTION RULES
    # ═══════════════════════════════════════════════════════════
    
    def should_demote(
        self,
        current_state: LifecycleState,
        governance_state: str,
        critical_failures: int,
        high_failures: int,
        weight_adjustment_action: str,
        rollback_risk: float,
    ) -> Tuple[bool, TransitionStrength, str]:
        """
        Determine if factor should be demoted.
        
        Demotion conditions:
        - current_state = LIVE or REDUCED
        - governance WATCHLIST or DEGRADED
        - repeated failures exist
        - weight adjustment = DECREASE
        - rollback_risk > 0.35
        
        Returns:
            (should_demote, strength, reason)
        """
        # Cannot demote from SHADOW, FROZEN, RETIRED
        if current_state not in [LifecycleState.LIVE, LifecycleState.REDUCED, LifecycleState.CANDIDATE]:
            return False, TransitionStrength.LOW, "not in demotable state"
        
        reasons = []
        severity_score = 0
        
        # Check governance
        if governance_state == "DEGRADED":
            reasons.append(f"governance DEGRADED")
            severity_score += 3
        elif governance_state == "WATCHLIST":
            reasons.append(f"governance WATCHLIST")
            severity_score += 2
        
        # Check critical failures
        if critical_failures > 0:
            reasons.append(f"{critical_failures} critical failures")
            severity_score += critical_failures * 2
        
        # Check high failures
        if high_failures >= 2:
            reasons.append(f"{high_failures} high failures")
            severity_score += high_failures
        
        # Check weight adjustment
        if weight_adjustment_action == "DECREASE":
            reasons.append("weight decrease recommended")
            severity_score += 1
        elif weight_adjustment_action in ["SHADOW", "RETIRE"]:
            reasons.append(f"weight action {weight_adjustment_action}")
            severity_score += 2
        
        # Check rollback risk
        if rollback_risk > 0.50:
            reasons.append(f"high rollback risk {rollback_risk:.2f}")
            severity_score += 2
        elif rollback_risk > 0.35:
            reasons.append(f"elevated rollback risk {rollback_risk:.2f}")
            severity_score += 1
        
        # Need at least some reason to demote
        if severity_score == 0:
            return False, TransitionStrength.LOW, "no demotion signals"
        
        # Determine strength
        if severity_score >= 5:
            strength = TransitionStrength.HIGH
        elif severity_score >= 3:
            strength = TransitionStrength.MEDIUM
        else:
            strength = TransitionStrength.LOW
        
        reason = ", ".join(reasons)
        return True, strength, reason
    
    # ═══════════════════════════════════════════════════════════
    # FREEZE RULES
    # ═══════════════════════════════════════════════════════════
    
    def should_freeze(
        self,
        current_state: LifecycleState,
        rollback_risk: float,
        deployment_action: str,
        critical_failures: int,
        interaction_state: str,
    ) -> Tuple[bool, TransitionStrength, str]:
        """
        Determine if factor should be frozen.
        
        Freeze conditions:
        - rollback risk high (> 0.60)
        - deployment governance says ROLLBACK
        - repeated critical failures
        - ecology/interaction repeatedly critical
        
        Returns:
            (should_freeze, strength, reason)
        """
        # Cannot freeze already frozen or retired
        if current_state in [LifecycleState.FROZEN, LifecycleState.RETIRED]:
            return False, TransitionStrength.LOW, "already frozen or retired"
        
        # Cannot freeze SHADOW (just demote)
        if current_state == LifecycleState.SHADOW:
            return False, TransitionStrength.LOW, "SHADOW factors cannot be frozen"
        
        reasons = []
        severity_score = 0
        
        # High rollback risk
        if rollback_risk > 0.70:
            reasons.append(f"critical rollback risk {rollback_risk:.2f}")
            severity_score += 4
        elif rollback_risk > 0.60:
            reasons.append(f"high rollback risk {rollback_risk:.2f}")
            severity_score += 3
        
        # Deployment says rollback
        if deployment_action == "ROLLBACK":
            reasons.append("deployment governance recommends ROLLBACK")
            severity_score += 3
        
        # Critical failures
        if critical_failures >= 3:
            reasons.append(f"{critical_failures} critical failures")
            severity_score += 3
        elif critical_failures >= 2:
            reasons.append(f"{critical_failures} critical failures")
            severity_score += 2
        
        # Bad interaction state
        if interaction_state in ["CANCELLED", "CONFLICTED"]:
            reasons.append(f"interaction state {interaction_state}")
            severity_score += 2
        
        # Need significant reason to freeze
        if severity_score < 3:
            return False, TransitionStrength.LOW, "insufficient freeze signals"
        
        # Determine strength
        if severity_score >= 6:
            strength = TransitionStrength.CRITICAL
        elif severity_score >= 4:
            strength = TransitionStrength.HIGH
        else:
            strength = TransitionStrength.MEDIUM
        
        reason = ", ".join(reasons)
        return True, strength, reason
    
    # ═══════════════════════════════════════════════════════════
    # RETIRE RULES
    # ═══════════════════════════════════════════════════════════
    
    def should_retire(
        self,
        governance_state: str,
        critical_failures: int,
        recommended_weight: float,
        deployment_action: str,
    ) -> Tuple[bool, TransitionStrength, str]:
        """
        Determine if factor should be retired.
        
        Retire conditions:
        - governance = RETIRE
        - repeated critical failures (>= 4)
        - recommended_weight = 0
        - factor is structurally broken
        
        Returns:
            (should_retire, strength, reason)
        """
        reasons = []
        severity_score = 0
        
        # Governance says retire
        if governance_state == "RETIRE":
            reasons.append("governance state RETIRE")
            severity_score += 4
        
        # Many critical failures
        if critical_failures >= 5:
            reasons.append(f"{critical_failures} critical failures")
            severity_score += 4
        elif critical_failures >= 4:
            reasons.append(f"{critical_failures} critical failures")
            severity_score += 3
        
        # Zero weight recommended
        if recommended_weight <= 0.0:
            reasons.append("recommended weight is 0")
            severity_score += 2
        
        # Deployment says retire
        if deployment_action == "RETIRE":
            reasons.append("deployment governance says RETIRE")
            severity_score += 3
        
        # Need strong reason to retire
        if severity_score < 4:
            return False, TransitionStrength.LOW, "insufficient retire signals"
        
        # Determine strength (retire is always critical or high)
        if severity_score >= 6:
            strength = TransitionStrength.CRITICAL
        else:
            strength = TransitionStrength.HIGH
        
        reason = ", ".join(reasons)
        return True, strength, reason
    
    # ═══════════════════════════════════════════════════════════
    # TRANSITION HELPERS
    # ═══════════════════════════════════════════════════════════
    
    def get_next_state_promote(
        self,
        current_state: LifecycleState,
    ) -> Optional[LifecycleState]:
        """Get next state for promotion."""
        promotion_map = {
            LifecycleState.SHADOW: LifecycleState.CANDIDATE,
            LifecycleState.CANDIDATE: LifecycleState.LIVE,
            LifecycleState.REDUCED: LifecycleState.LIVE,
        }
        return promotion_map.get(current_state)
    
    def get_next_state_demote(
        self,
        current_state: LifecycleState,
    ) -> Optional[LifecycleState]:
        """Get next state for demotion."""
        demotion_map = {
            LifecycleState.LIVE: LifecycleState.REDUCED,
            LifecycleState.REDUCED: LifecycleState.SHADOW,
            LifecycleState.CANDIDATE: LifecycleState.SHADOW,
        }
        return demotion_map.get(current_state)
    
    def is_valid_transition(
        self,
        current_state: LifecycleState,
        target_state: LifecycleState,
    ) -> bool:
        """Check if transition is allowed."""
        allowed = ALLOWED_TRANSITIONS.get(current_state, [])
        return target_state in allowed
    
    # ═══════════════════════════════════════════════════════════
    # MODIFIER CALCULATION
    # ═══════════════════════════════════════════════════════════
    
    def calculate_modifiers(
        self,
        action: TransitionAction,
        strength: TransitionStrength,
        current_state: LifecycleState,
        recommended_state: LifecycleState,
    ) -> Tuple[float, float]:
        """
        Calculate confidence and capital modifiers.
        
        Returns:
            (confidence_modifier, capital_modifier)
        """
        # Base modifiers by action
        base_modifiers = {
            TransitionAction.PROMOTE: (1.05, 1.10),
            TransitionAction.DEMOTE: (0.85, 0.75),
            TransitionAction.FREEZE: (0.70, 0.50),
            TransitionAction.RETIRE: (0.50, 0.00),
            TransitionAction.HOLD: (1.00, 1.00),
        }
        
        conf, cap = base_modifiers.get(action, (1.0, 1.0))
        
        # Adjust by strength
        strength_multipliers = {
            TransitionStrength.CRITICAL: 0.15,
            TransitionStrength.HIGH: 0.10,
            TransitionStrength.MEDIUM: 0.05,
            TransitionStrength.LOW: 0.00,
        }
        
        mult = strength_multipliers.get(strength, 0.0)
        
        if action in [TransitionAction.DEMOTE, TransitionAction.FREEZE, TransitionAction.RETIRE]:
            conf -= mult
            cap -= mult
        elif action == TransitionAction.PROMOTE:
            conf += mult * 0.5
            cap += mult
        
        # Clamp values
        conf = max(0.50, min(1.15, conf))
        cap = max(0.00, min(1.20, cap))
        
        return round(conf, 4), round(cap, 4)


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_policy: Optional[AdaptivePromotionPolicy] = None


def get_adaptive_promotion_policy() -> AdaptivePromotionPolicy:
    """Get singleton policy instance."""
    global _policy
    if _policy is None:
        _policy = AdaptivePromotionPolicy()
    return _policy
