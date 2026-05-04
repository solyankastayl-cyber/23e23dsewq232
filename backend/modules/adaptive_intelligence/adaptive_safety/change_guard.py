"""
PHASE 11.6.1 - Change Guard
============================
Validates proposed changes against safety policies.

Checks:
- Can parameter be changed at all
- Is change magnitude acceptable
- Does it conflict with risk policy
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, timezone

from ..adaptive_types import (
    ChangeDecision, ParameterAdjustment, FactorWeight,
    AdaptiveAction, DEFAULT_ADAPTIVE_CONFIG
)


class ChangeGuard:
    """
    Change Guard - First line of defense
    
    Validates all proposed changes before they can proceed
    to cooldown, shadow testing, or OOS validation.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_ADAPTIVE_CONFIG
        
        # Locked parameters that cannot be changed
        self.locked_parameters: set = set()
        
        # Risk policy constraints
        self.risk_constraints: Dict[str, Dict] = {}
        
        # Change frequency tracking
        self.change_counts: Dict[str, int] = {}
        self.change_window_hours: int = 24
    
    def lock_parameter(self, parameter_key: str):
        """Lock a parameter from changes."""
        self.locked_parameters.add(parameter_key)
    
    def unlock_parameter(self, parameter_key: str):
        """Unlock a parameter for changes."""
        self.locked_parameters.discard(parameter_key)
    
    def set_risk_constraint(
        self,
        parameter_key: str,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        max_change_pct: Optional[float] = None
    ):
        """Set risk constraints for a parameter."""
        self.risk_constraints[parameter_key] = {
            "min_val": min_val,
            "max_val": max_val,
            "max_change_pct": max_change_pct or self.config["max_parameter_change_pct"]
        }
    
    def validate_parameter_change(
        self,
        adjustment: ParameterAdjustment
    ) -> Tuple[bool, str]:
        """
        Validate a parameter change.
        
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        key = f"{adjustment.strategy_id}_{adjustment.parameter_name}"
        
        # Check if locked
        if key in self.locked_parameters:
            return False, f"Parameter {key} is locked"
        
        # Check risk constraints
        constraints = self.risk_constraints.get(key, {})
        
        if constraints:
            # Check value bounds
            if constraints.get("min_val") is not None:
                if adjustment.suggested_value < constraints["min_val"]:
                    return False, f"Value below minimum: {constraints['min_val']}"
            
            if constraints.get("max_val") is not None:
                if adjustment.suggested_value > constraints["max_val"]:
                    return False, f"Value above maximum: {constraints['max_val']}"
            
            # Check change magnitude
            max_change = constraints.get("max_change_pct", self.config["max_parameter_change_pct"])
            if adjustment.change_magnitude > max_change:
                return False, f"Change magnitude {adjustment.change_magnitude:.2%} exceeds limit {max_change:.2%}"
        else:
            # Use default limits
            if adjustment.change_magnitude > self.config["max_parameter_change_pct"]:
                return False, f"Change magnitude exceeds default limit"
        
        # Check change frequency
        if self._exceeds_change_frequency(key):
            return False, "Too many changes in short period"
        
        # Check confidence
        if adjustment.confidence < self.config["min_confidence_for_change"]:
            return False, f"Confidence {adjustment.confidence:.2f} below threshold"
        
        return True, ""
    
    def validate_weight_change(
        self,
        weight: FactorWeight
    ) -> Tuple[bool, str]:
        """Validate a factor weight change."""
        key = f"weight_{weight.factor_name}"
        
        # Check if locked
        if key in self.locked_parameters:
            return False, f"Factor {weight.factor_name} is locked"
        
        # Check change magnitude
        max_change = self.config["max_weight_change_pct"]
        if abs(weight.weight_change) > max_change:
            return False, f"Weight change {weight.weight_change:.2%} exceeds limit {max_change:.2%}"
        
        # Check bounds (weights should be 0.1 to 2.0)
        if weight.suggested_weight < 0.1:
            return False, "Weight too low (min 0.1)"
        if weight.suggested_weight > 2.0:
            return False, "Weight too high (max 2.0)"
        
        return True, ""
    
    def validate_action(
        self,
        action: AdaptiveAction,
        target: str,
        params: Dict
    ) -> Tuple[bool, str]:
        """Validate any adaptive action."""
        
        if action == AdaptiveAction.DISABLE_STRATEGY:
            # Can only disable if confirmed edge death
            if not params.get("confirmed_decay", False):
                return False, "Cannot disable strategy without confirmed decay"
            if params.get("decay_probability", 0) < 0.8:
                return False, "Decay probability too low to disable"
        
        elif action == AdaptiveAction.FULL_RESET:
            # Full reset requires emergency confirmation
            if not params.get("emergency_confirmed", False):
                return False, "Full reset requires emergency confirmation"
        
        elif action in [AdaptiveAction.INCREASE_ALLOCATION, AdaptiveAction.DECREASE_ALLOCATION]:
            # Check allocation change magnitude
            change_pct = abs(params.get("change_pct", 0))
            max_change = self.config["max_allocation_change_pct"]
            if change_pct > max_change:
                return False, f"Allocation change {change_pct:.2%} exceeds limit"
        
        return True, ""
    
    def _exceeds_change_frequency(self, key: str) -> bool:
        """Check if too many changes have been made recently."""
        # Simple frequency check - in real system would track timestamps
        count = self.change_counts.get(key, 0)
        max_changes_per_window = 3
        
        return count >= max_changes_per_window
    
    def record_change(self, key: str):
        """Record that a change was made."""
        self.change_counts[key] = self.change_counts.get(key, 0) + 1
    
    def reset_change_counts(self):
        """Reset change counts (called periodically)."""
        self.change_counts = {}
    
    def get_locked_parameters(self) -> set:
        """Get set of locked parameters."""
        return self.locked_parameters.copy()
    
    def get_guard_summary(self) -> Dict:
        """Get summary of change guard state."""
        return {
            "locked_parameters": list(self.locked_parameters),
            "risk_constraints": len(self.risk_constraints),
            "recent_changes": sum(self.change_counts.values()),
            "config": {
                "max_param_change": self.config["max_parameter_change_pct"],
                "max_weight_change": self.config["max_weight_change_pct"],
                "min_confidence": self.config["min_confidence_for_change"]
            }
        }
