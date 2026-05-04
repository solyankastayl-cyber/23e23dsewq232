"""
PHASE 20.2 — Factor Weight Policy
=================================
Policy rules for factor weight adjustments.

Defines:
- When to increase/decrease/shadow/retire
- Delta calculation rules
- Modifier calculation rules
"""

from typing import Dict, Tuple, Optional
from modules.research_loop.factor_weight_adjustment.factor_weight_adjustment_types import (
    AdjustmentAction,
    AdjustmentStrength,
    WEIGHT_DELTA_RANGES,
    SHADOW_WEIGHT,
    RETIRE_WEIGHT,
    WEIGHT_MIN,
    WEIGHT_MAX,
)


class FactorWeightPolicy:
    """
    Policy engine for factor weight adjustments.
    
    Determines action, delta, and strength based on input signals.
    """
    
    def __init__(self):
        """Initialize policy."""
        pass
    
    def determine_action(
        self,
        critical_failures: int,
        failure_patterns_count: int,
        governance_state: str,
        deployment_state: str,
    ) -> Tuple[AdjustmentAction, AdjustmentStrength]:
        """
        Determine adjustment action and strength.
        
        Returns tuple of (action, strength).
        """
        # Case 1: Strong negative signal - RETIRE
        if governance_state == "RETIRE" or deployment_state == "RETIRE":
            return AdjustmentAction.RETIRE, AdjustmentStrength.CRITICAL
        
        # Case 2: Critical failures + degraded = SHADOW or heavy DECREASE
        if critical_failures >= 2 and governance_state in ["DEGRADED", "RETIRE"]:
            return AdjustmentAction.SHADOW, AdjustmentStrength.CRITICAL
        
        if critical_failures >= 1 and deployment_state in ["ROLLBACK", "REDUCE"]:
            return AdjustmentAction.DECREASE, AdjustmentStrength.HIGH
        
        # Case 3: Mild negative signal - DECREASE
        if failure_patterns_count > 0 and governance_state == "WATCHLIST":
            if critical_failures > 0:
                return AdjustmentAction.DECREASE, AdjustmentStrength.HIGH
            else:
                return AdjustmentAction.DECREASE, AdjustmentStrength.MEDIUM
        
        if failure_patterns_count > 0 and deployment_state == "HOLD":
            return AdjustmentAction.DECREASE, AdjustmentStrength.LOW
        
        # Case 4: Stable/healthy factor - HOLD or INCREASE
        if governance_state == "ELITE" and deployment_state == "PROMOTE":
            return AdjustmentAction.INCREASE, AdjustmentStrength.MEDIUM
        
        if governance_state == "STABLE" and deployment_state in ["PROMOTE", "LIVE"]:
            if failure_patterns_count == 0:
                return AdjustmentAction.INCREASE, AdjustmentStrength.LOW
            else:
                return AdjustmentAction.HOLD, AdjustmentStrength.LOW
        
        # Default: HOLD
        return AdjustmentAction.HOLD, AdjustmentStrength.LOW
    
    def calculate_delta(
        self,
        action: AdjustmentAction,
        strength: AdjustmentStrength,
        current_weight: float,
    ) -> float:
        """
        Calculate weight delta based on action and strength.
        
        Returns delta value.
        """
        if action == AdjustmentAction.RETIRE:
            return -current_weight  # Go to 0
        
        if action == AdjustmentAction.SHADOW:
            return SHADOW_WEIGHT - current_weight  # Go to shadow weight
        
        if action == AdjustmentAction.HOLD:
            return 0.0
        
        # Get delta range
        delta_range = WEIGHT_DELTA_RANGES.get(action)
        if delta_range is None:
            return 0.0
        
        min_delta, max_delta = delta_range
        
        # Scale by strength
        strength_multipliers = {
            AdjustmentStrength.LOW: 0.25,
            AdjustmentStrength.MEDIUM: 0.5,
            AdjustmentStrength.HIGH: 0.75,
            AdjustmentStrength.CRITICAL: 1.0,
        }
        
        multiplier = strength_multipliers.get(strength, 0.5)
        
        # Calculate delta within range
        range_size = max_delta - min_delta
        delta = min_delta + (range_size * multiplier)
        
        return delta
    
    def calculate_recommended_weight(
        self,
        current_weight: float,
        delta: float,
    ) -> float:
        """
        Calculate recommended weight with bounds.
        
        Ensures result is in [0.0, 1.0].
        """
        recommended = current_weight + delta
        return max(WEIGHT_MIN, min(WEIGHT_MAX, recommended))
    
    def calculate_modifiers(
        self,
        action: AdjustmentAction,
        strength: AdjustmentStrength,
        recommended_weight: float,
        current_weight: float,
    ) -> Tuple[float, float]:
        """
        Calculate confidence and capital modifiers.
        
        Returns tuple of (confidence_modifier, capital_modifier).
        """
        # Base modifiers from action
        base_modifiers = {
            AdjustmentAction.INCREASE: (1.05, 1.08),
            AdjustmentAction.HOLD: (1.0, 1.0),
            AdjustmentAction.DECREASE: (0.90, 0.85),
            AdjustmentAction.SHADOW: (0.80, 0.75),
            AdjustmentAction.RETIRE: (0.70, 0.0),
        }
        
        conf_base, cap_base = base_modifiers.get(action, (1.0, 1.0))
        
        # Adjust by strength
        strength_adjustments = {
            AdjustmentStrength.LOW: 0.02,
            AdjustmentStrength.MEDIUM: 0.05,
            AdjustmentStrength.HIGH: 0.08,
            AdjustmentStrength.CRITICAL: 0.12,
        }
        
        adjustment = strength_adjustments.get(strength, 0.05)
        
        if action in [AdjustmentAction.DECREASE, AdjustmentAction.SHADOW, AdjustmentAction.RETIRE]:
            conf_modifier = conf_base - adjustment
            cap_modifier = cap_base - adjustment
        else:
            conf_modifier = conf_base + adjustment
            cap_modifier = cap_base + adjustment
        
        # Bound modifiers
        conf_modifier = max(0.5, min(1.3, conf_modifier))
        cap_modifier = max(0.0, min(1.5, cap_modifier))
        
        return conf_modifier, cap_modifier
    
    def build_reason(
        self,
        action: AdjustmentAction,
        strength: AdjustmentStrength,
        critical_failures: int,
        failure_patterns_count: int,
        governance_state: str,
        deployment_state: str,
    ) -> str:
        """Build human-readable reason string."""
        parts = []
        
        if action == AdjustmentAction.RETIRE:
            parts.append("retire_governance_signal")
        elif action == AdjustmentAction.SHADOW:
            parts.append("critical_failures_detected")
        elif action == AdjustmentAction.DECREASE:
            if critical_failures > 0:
                parts.append(f"{critical_failures}_critical_failure_patterns")
            if governance_state == "WATCHLIST":
                parts.append("watchlist_governance")
            if deployment_state in ["REDUCE", "ROLLBACK"]:
                parts.append(f"{deployment_state.lower()}_deployment")
        elif action == AdjustmentAction.INCREASE:
            parts.append("positive_performance")
            if governance_state == "ELITE":
                parts.append("elite_governance")
        else:
            parts.append("stable_factor")
        
        return "_".join(parts) if parts else f"{action.value.lower()}_action"


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_policy: Optional[FactorWeightPolicy] = None


def get_factor_weight_policy() -> FactorWeightPolicy:
    """Get singleton policy instance."""
    global _policy
    if _policy is None:
        _policy = FactorWeightPolicy()
    return _policy
