"""
PHASE 20.2 — Factor Weight Adjustment Types
===========================================
Type definitions for Factor Weight Adjustment Engine.

Core contracts:
- FactorWeightAdjustment: Single factor adjustment recommendation
- FactorWeightAdjustmentSummary: Aggregated adjustments
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# ADJUSTMENT ACTION
# ══════════════════════════════════════════════════════════════

class AdjustmentAction(str, Enum):
    """Factor weight adjustment action."""
    INCREASE = "INCREASE"      # Boost weight
    DECREASE = "DECREASE"      # Reduce weight
    HOLD = "HOLD"              # Keep current weight
    SHADOW = "SHADOW"          # Move to shadow mode (low weight)
    RETIRE = "RETIRE"          # Set weight to 0


# ══════════════════════════════════════════════════════════════
# ADJUSTMENT STRENGTH
# ══════════════════════════════════════════════════════════════

class AdjustmentStrength(str, Enum):
    """Strength of adjustment recommendation."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ══════════════════════════════════════════════════════════════
# WEIGHT DELTAS BY ACTION
# ══════════════════════════════════════════════════════════════

WEIGHT_DELTA_RANGES = {
    AdjustmentAction.INCREASE: (0.05, 0.15),
    AdjustmentAction.DECREASE: (-0.20, -0.05),
    AdjustmentAction.HOLD: (0.0, 0.0),
    AdjustmentAction.SHADOW: None,  # Set to shadow weight
    AdjustmentAction.RETIRE: None,  # Set to 0
}

SHADOW_WEIGHT = 0.05
RETIRE_WEIGHT = 0.0

# Weight bounds
WEIGHT_MIN = 0.0
WEIGHT_MAX = 1.0


# ══════════════════════════════════════════════════════════════
# FACTOR WEIGHT STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class FactorWeightState:
    """
    Current state of a factor's weight.
    """
    factor_name: str
    current_weight: float
    previous_weight: float
    deployment_state: str        # LIVE / SHADOW / CANDIDATE / RETIRED
    governance_state: str        # ELITE / STABLE / WATCHLIST / DEGRADED / RETIRE
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "factor_name": self.factor_name,
            "current_weight": round(self.current_weight, 4),
            "previous_weight": round(self.previous_weight, 4),
            "deployment_state": self.deployment_state,
            "governance_state": self.governance_state,
            "last_updated": self.last_updated.isoformat(),
        }


# ══════════════════════════════════════════════════════════════
# FACTOR WEIGHT ADJUSTMENT
# ══════════════════════════════════════════════════════════════

@dataclass
class FactorWeightAdjustment:
    """
    Single factor weight adjustment recommendation.
    """
    factor_name: str
    
    # Weights
    current_weight: float
    recommended_weight: float
    weight_delta: float
    
    # Action
    adjustment_action: AdjustmentAction
    adjustment_strength: AdjustmentStrength
    
    # Modifiers
    confidence_modifier: float
    capital_modifier: float
    
    # Context
    reason: str
    
    # Input signals
    failure_patterns_count: int = 0
    critical_failures: int = 0
    governance_state: str = "STABLE"
    deployment_state: str = "LIVE"
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "factor_name": self.factor_name,
            "current_weight": round(self.current_weight, 4),
            "recommended_weight": round(self.recommended_weight, 4),
            "weight_delta": round(self.weight_delta, 4),
            "adjustment_action": self.adjustment_action.value,
            "adjustment_strength": self.adjustment_strength.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "reason": self.reason,
            "signals": {
                "failure_patterns_count": self.failure_patterns_count,
                "critical_failures": self.critical_failures,
                "governance_state": self.governance_state,
                "deployment_state": self.deployment_state,
            },
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "factor": self.factor_name,
            "action": self.adjustment_action.value,
            "delta": round(self.weight_delta, 3),
            "strength": self.adjustment_strength.value,
        }


# ══════════════════════════════════════════════════════════════
# FACTOR WEIGHT ADJUSTMENT SUMMARY
# ══════════════════════════════════════════════════════════════

@dataclass
class FactorWeightAdjustmentSummary:
    """
    Aggregated summary of all factor weight adjustments.
    """
    total_factors: int
    
    # Factors by action
    increased: List[str]
    decreased: List[str]
    held: List[str]
    shadowed: List[str]
    retired: List[str]
    
    # Counts
    increase_count: int
    decrease_count: int
    hold_count: int
    shadow_count: int
    retire_count: int
    
    # Full adjustments
    adjustments: List[FactorWeightAdjustment] = field(default_factory=list)
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_factors": self.total_factors,
            "increased": self.increased,
            "decreased": self.decreased,
            "held": self.held,
            "shadowed": self.shadowed,
            "retired": self.retired,
            "counts": {
                "increase": self.increase_count,
                "decrease": self.decrease_count,
                "hold": self.hold_count,
                "shadow": self.shadow_count,
                "retire": self.retire_count,
            },
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with all adjustment details."""
        result = self.to_dict()
        result["adjustments"] = [a.to_dict() for a in self.adjustments]
        return result
