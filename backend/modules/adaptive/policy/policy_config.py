"""
PHASE 3.2 — Policy Configuration

Defines all policy limits and thresholds.
Central place for adaptation constraints.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import timedelta


@dataclass
class PolicyConfig:
    """
    Policy configuration for adaptive layer.
    
    Controls what changes are allowed and at what rate.
    """
    
    # === Cycle Limits ===
    max_actions_per_cycle: int = 5
    max_disable_per_cycle: int = 2
    max_reduce_risk_per_cycle: int = 3
    max_increase_threshold_per_cycle: int = 3
    max_increase_allocation_per_cycle: int = 2
    max_cut_cluster_per_cycle: int = 2
    
    # === Confidence Filter ===
    min_confidence_to_apply: float = 0.5
    min_confidence_for_disable: float = 0.7  # Higher bar for disable
    min_confidence_for_increase_allocation: float = 0.75  # Highest bar
    
    # === Cooldown ===
    cycle_cooldown_hours: int = 24
    per_target_cooldown_hours: int = 48
    
    # === Emergency Mode ===
    enable_emergency_mode: bool = True
    emergency_trigger_degradation_rate: float = 0.3  # 30% of assets degrading
    emergency_allowed_actions: List[str] = field(default_factory=lambda: ["disable", "reduce_risk"])
    
    # === Velocity Limits ===
    max_assets_disabled_total: int = 10  # Never disable more than 10 assets total
    min_enabled_assets: int = 5  # Always keep at least 5 assets enabled
    max_risk_reduction_per_asset: float = 0.3  # Min risk multiplier
    max_threshold_per_asset: float = 0.9  # Max confidence threshold
    
    # === Action Priority ===
    action_priority_order: List[str] = field(default_factory=lambda: [
        "disable",  # Most impactful first
        "reduce_risk",
        "increase_threshold",
        "cut_cluster_exposure",
        "increase_allocation",
        "keep"
    ])
    
    # === Batch Limits ===
    max_batch_size: int = 20  # Max actions to process in one batch
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "max_actions_per_cycle": self.max_actions_per_cycle,
            "max_disable_per_cycle": self.max_disable_per_cycle,
            "max_reduce_risk_per_cycle": self.max_reduce_risk_per_cycle,
            "max_increase_threshold_per_cycle": self.max_increase_threshold_per_cycle,
            "max_increase_allocation_per_cycle": self.max_increase_allocation_per_cycle,
            "max_cut_cluster_per_cycle": self.max_cut_cluster_per_cycle,
            "min_confidence_to_apply": self.min_confidence_to_apply,
            "min_confidence_for_disable": self.min_confidence_for_disable,
            "min_confidence_for_increase_allocation": self.min_confidence_for_increase_allocation,
            "cycle_cooldown_hours": self.cycle_cooldown_hours,
            "per_target_cooldown_hours": self.per_target_cooldown_hours,
            "enable_emergency_mode": self.enable_emergency_mode,
            "emergency_trigger_degradation_rate": self.emergency_trigger_degradation_rate,
            "emergency_allowed_actions": self.emergency_allowed_actions,
            "max_assets_disabled_total": self.max_assets_disabled_total,
            "min_enabled_assets": self.min_enabled_assets,
            "max_risk_reduction_per_asset": self.max_risk_reduction_per_asset,
            "max_threshold_per_asset": self.max_threshold_per_asset,
            "action_priority_order": self.action_priority_order,
            "max_batch_size": self.max_batch_size
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PolicyConfig":
        """Create from dictionary."""
        return cls(
            max_actions_per_cycle=data.get("max_actions_per_cycle", 5),
            max_disable_per_cycle=data.get("max_disable_per_cycle", 2),
            max_reduce_risk_per_cycle=data.get("max_reduce_risk_per_cycle", 3),
            max_increase_threshold_per_cycle=data.get("max_increase_threshold_per_cycle", 3),
            max_increase_allocation_per_cycle=data.get("max_increase_allocation_per_cycle", 2),
            max_cut_cluster_per_cycle=data.get("max_cut_cluster_per_cycle", 2),
            min_confidence_to_apply=data.get("min_confidence_to_apply", 0.5),
            min_confidence_for_disable=data.get("min_confidence_for_disable", 0.7),
            min_confidence_for_increase_allocation=data.get("min_confidence_for_increase_allocation", 0.75),
            cycle_cooldown_hours=data.get("cycle_cooldown_hours", 24),
            per_target_cooldown_hours=data.get("per_target_cooldown_hours", 48),
            enable_emergency_mode=data.get("enable_emergency_mode", True),
            emergency_trigger_degradation_rate=data.get("emergency_trigger_degradation_rate", 0.3),
            emergency_allowed_actions=data.get("emergency_allowed_actions", ["disable", "reduce_risk"]),
            max_assets_disabled_total=data.get("max_assets_disabled_total", 10),
            min_enabled_assets=data.get("min_enabled_assets", 5),
            max_risk_reduction_per_asset=data.get("max_risk_reduction_per_asset", 0.3),
            max_threshold_per_asset=data.get("max_threshold_per_asset", 0.9),
            action_priority_order=data.get("action_priority_order", [
                "disable", "reduce_risk", "increase_threshold", 
                "cut_cluster_exposure", "increase_allocation", "keep"
            ]),
            max_batch_size=data.get("max_batch_size", 20)
        )


# Default configuration
DEFAULT_POLICY_CONFIG = PolicyConfig()


# Aggressive policy - more changes allowed (for testing)
AGGRESSIVE_POLICY_CONFIG = PolicyConfig(
    max_actions_per_cycle=10,
    max_disable_per_cycle=5,
    max_reduce_risk_per_cycle=5,
    min_confidence_to_apply=0.4,
    cycle_cooldown_hours=12
)


# Conservative policy - fewer changes allowed (for production)
CONSERVATIVE_POLICY_CONFIG = PolicyConfig(
    max_actions_per_cycle=3,
    max_disable_per_cycle=1,
    max_reduce_risk_per_cycle=2,
    max_increase_allocation_per_cycle=1,
    min_confidence_to_apply=0.6,
    min_confidence_for_disable=0.8,
    cycle_cooldown_hours=48
)
