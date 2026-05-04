"""
PHASE 11.6.6 - Adaptive Limits
===============================
Central configuration for all adaptive limits.

Defines:
- Maximum change rates
- Minimum confidence levels
- Cooldown periods
- Safety thresholds
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class AdaptiveLimitsConfig:
    """Configuration for adaptive limits."""
    
    # Parameter change limits
    max_parameter_change_pct: float = 0.10      # 10% max per cycle
    min_parameter_confidence: float = 0.70     # 70% confidence required
    parameter_cooldown_hours: int = 168        # 1 week
    
    # Weight change limits
    max_weight_change_pct: float = 0.15        # 15% max per cycle
    min_weight_confidence: float = 0.65        # 65% confidence required
    weight_cooldown_hours: int = 72            # 3 days
    
    # Allocation limits
    max_allocation_change_pct: float = 0.20    # 20% max per cycle
    allocation_cooldown_hours: int = 24        # 1 day
    
    # Strategy limits
    strategy_cooldown_hours: int = 336         # 2 weeks
    min_trades_before_disable: int = 50        # Need 50+ trades
    min_decay_probability_for_disable: float = 0.80
    
    # Shadow testing
    shadow_test_duration_hours: int = 48       # 2 days
    shadow_required_improvement: float = 0.05  # 5% improvement
    
    # OOS validation
    oos_validation_required: bool = True
    min_oos_gates_to_pass: int = 3
    
    # Edge decay
    edge_decay_lookback_days: int = 30
    edge_death_threshold: float = 0.90         # PF below 0.9 = dead
    
    # Frequency limits
    max_changes_per_day: int = 5
    max_changes_per_week: int = 15


class AdaptiveLimits:
    """
    Adaptive Limits Manager
    
    Central source of truth for all adaptive system limits.
    """
    
    def __init__(self, config: Optional[AdaptiveLimitsConfig] = None):
        self.config = config or AdaptiveLimitsConfig()
        self._overrides: Dict[str, any] = {}
    
    def get_limit(self, limit_name: str) -> any:
        """Get a specific limit value."""
        # Check overrides first
        if limit_name in self._overrides:
            return self._overrides[limit_name]
        
        # Get from config
        return getattr(self.config, limit_name, None)
    
    def set_override(self, limit_name: str, value: any):
        """Temporarily override a limit (use with caution)."""
        self._overrides[limit_name] = value
    
    def clear_override(self, limit_name: str):
        """Clear a limit override."""
        self._overrides.pop(limit_name, None)
    
    def clear_all_overrides(self):
        """Clear all overrides."""
        self._overrides = {}
    
    def validate_parameter_change(
        self,
        change_pct: float,
        confidence: float
    ) -> tuple:
        """
        Validate a parameter change against limits.
        
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        max_change = self.get_limit("max_parameter_change_pct")
        min_conf = self.get_limit("min_parameter_confidence")
        
        if abs(change_pct) > max_change:
            return False, f"Change {change_pct:.2%} exceeds limit {max_change:.2%}"
        
        if confidence < min_conf:
            return False, f"Confidence {confidence:.2%} below minimum {min_conf:.2%}"
        
        return True, ""
    
    def validate_weight_change(
        self,
        change_pct: float,
        confidence: float
    ) -> tuple:
        """Validate a weight change against limits."""
        max_change = self.get_limit("max_weight_change_pct")
        min_conf = self.get_limit("min_weight_confidence")
        
        if abs(change_pct) > max_change:
            return False, f"Weight change {change_pct:.2%} exceeds limit {max_change:.2%}"
        
        if confidence < min_conf:
            return False, f"Confidence {confidence:.2%} below minimum {min_conf:.2%}"
        
        return True, ""
    
    def validate_strategy_disable(
        self,
        trade_count: int,
        decay_probability: float
    ) -> tuple:
        """Validate strategy disable request."""
        min_trades = self.get_limit("min_trades_before_disable")
        min_decay = self.get_limit("min_decay_probability_for_disable")
        
        if trade_count < min_trades:
            return False, f"Only {trade_count} trades, need {min_trades} before disable"
        
        if decay_probability < min_decay:
            return False, f"Decay probability {decay_probability:.2%} below {min_decay:.2%}"
        
        return True, ""
    
    def get_cooldown_hours(self, change_type: str) -> int:
        """Get cooldown hours for a change type."""
        cooldown_map = {
            "PARAMETER": "parameter_cooldown_hours",
            "WEIGHT": "weight_cooldown_hours",
            "ALLOCATION": "allocation_cooldown_hours",
            "STRATEGY": "strategy_cooldown_hours"
        }
        
        limit_name = cooldown_map.get(change_type, "parameter_cooldown_hours")
        return self.get_limit(limit_name)
    
    def get_all_limits(self) -> Dict:
        """Get all current limits (with overrides applied)."""
        limits = {}
        
        for field in self.config.__dataclass_fields__:
            limits[field] = self.get_limit(field)
        
        return limits
    
    def get_limits_summary(self) -> Dict:
        """Get summary of adaptive limits."""
        return {
            "parameter_limits": {
                "max_change": self.get_limit("max_parameter_change_pct"),
                "min_confidence": self.get_limit("min_parameter_confidence"),
                "cooldown_hours": self.get_limit("parameter_cooldown_hours")
            },
            "weight_limits": {
                "max_change": self.get_limit("max_weight_change_pct"),
                "min_confidence": self.get_limit("min_weight_confidence"),
                "cooldown_hours": self.get_limit("weight_cooldown_hours")
            },
            "strategy_limits": {
                "cooldown_hours": self.get_limit("strategy_cooldown_hours"),
                "min_trades_to_disable": self.get_limit("min_trades_before_disable"),
                "min_decay_prob": self.get_limit("min_decay_probability_for_disable")
            },
            "safety_requirements": {
                "shadow_test_hours": self.get_limit("shadow_test_duration_hours"),
                "oos_required": self.get_limit("oos_validation_required"),
                "min_oos_gates": self.get_limit("min_oos_gates_to_pass")
            },
            "active_overrides": len(self._overrides)
        }
