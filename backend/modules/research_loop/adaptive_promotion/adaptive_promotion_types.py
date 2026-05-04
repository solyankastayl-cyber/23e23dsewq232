"""
PHASE 20.3 — Adaptive Promotion Types
=====================================
Type definitions for Adaptive Promotion/Demotion Engine.

Core contracts:
- AdaptivePromotionDecision: Single factor lifecycle decision
- AdaptivePromotionSummary: Aggregated decisions
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# LIFECYCLE STATE
# ══════════════════════════════════════════════════════════════

class LifecycleState(str, Enum):
    """Factor lifecycle state."""
    SHADOW = "SHADOW"          # Testing phase, minimal weight
    CANDIDATE = "CANDIDATE"    # Ready for promotion
    LIVE = "LIVE"              # Active production
    REDUCED = "REDUCED"        # Reduced allocation
    FROZEN = "FROZEN"          # Temporarily disabled
    RETIRED = "RETIRED"        # Permanently disabled


# ══════════════════════════════════════════════════════════════
# TRANSITION ACTION
# ══════════════════════════════════════════════════════════════

class TransitionAction(str, Enum):
    """Lifecycle transition action."""
    PROMOTE = "PROMOTE"        # Move to higher state
    DEMOTE = "DEMOTE"          # Move to lower state
    FREEZE = "FREEZE"          # Temporarily disable
    RETIRE = "RETIRE"          # Permanently disable
    HOLD = "HOLD"              # Keep current state


# ══════════════════════════════════════════════════════════════
# TRANSITION STRENGTH
# ══════════════════════════════════════════════════════════════

class TransitionStrength(str, Enum):
    """Strength of transition recommendation."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ══════════════════════════════════════════════════════════════
# ALLOWED TRANSITIONS
# ══════════════════════════════════════════════════════════════

ALLOWED_TRANSITIONS = {
    LifecycleState.SHADOW: [
        LifecycleState.CANDIDATE,  # Promote
        LifecycleState.RETIRED,    # Retire
    ],
    LifecycleState.CANDIDATE: [
        LifecycleState.LIVE,       # Promote
        LifecycleState.SHADOW,     # Demote
        LifecycleState.RETIRED,    # Retire
    ],
    LifecycleState.LIVE: [
        LifecycleState.REDUCED,    # Demote
        LifecycleState.FROZEN,     # Freeze
        LifecycleState.RETIRED,    # Retire
    ],
    LifecycleState.REDUCED: [
        LifecycleState.LIVE,       # Promote back
        LifecycleState.SHADOW,     # Demote further
        LifecycleState.FROZEN,     # Freeze
        LifecycleState.RETIRED,    # Retire
    ],
    LifecycleState.FROZEN: [
        LifecycleState.REDUCED,    # Unfreeze to reduced
        LifecycleState.RETIRED,    # Retire
    ],
    LifecycleState.RETIRED: [],    # No transitions from retired
}


# ══════════════════════════════════════════════════════════════
# ADAPTIVE PROMOTION DECISION
# ══════════════════════════════════════════════════════════════

@dataclass
class AdaptivePromotionDecision:
    """
    Single factor lifecycle transition decision.
    """
    factor_name: str
    
    # States
    current_state: LifecycleState
    recommended_state: LifecycleState
    
    # Action
    transition_action: TransitionAction
    transition_strength: TransitionStrength
    
    # Modifiers
    confidence_modifier: float
    capital_modifier: float
    
    # Context
    reason: str
    
    # Input signals
    governance_state: str = "STABLE"
    deployment_state: str = "LIVE"
    failure_count: int = 0
    critical_failures: int = 0
    weight_adjustment_action: str = "HOLD"
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "factor_name": self.factor_name,
            "current_state": self.current_state.value,
            "recommended_state": self.recommended_state.value,
            "transition_action": self.transition_action.value,
            "transition_strength": self.transition_strength.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "reason": self.reason,
            "signals": {
                "governance_state": self.governance_state,
                "deployment_state": self.deployment_state,
                "failure_count": self.failure_count,
                "critical_failures": self.critical_failures,
                "weight_adjustment_action": self.weight_adjustment_action,
            },
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "factor": self.factor_name,
            "current": self.current_state.value,
            "recommended": self.recommended_state.value,
            "action": self.transition_action.value,
            "strength": self.transition_strength.value,
        }


# ══════════════════════════════════════════════════════════════
# ADAPTIVE PROMOTION SUMMARY
# ══════════════════════════════════════════════════════════════

@dataclass
class AdaptivePromotionSummary:
    """
    Aggregated summary of all lifecycle decisions.
    """
    total_factors: int
    
    # Factors by action
    promoted: List[str]
    demoted: List[str]
    frozen: List[str]
    retired: List[str]
    held: List[str]
    
    # Counts
    promote_count: int
    demote_count: int
    freeze_count: int
    retire_count: int
    hold_count: int
    
    # Full decisions
    decisions: List[AdaptivePromotionDecision] = field(default_factory=list)
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_factors": self.total_factors,
            "promoted": self.promoted,
            "demoted": self.demoted,
            "frozen": self.frozen,
            "retired": self.retired,
            "held": self.held,
            "counts": {
                "promote": self.promote_count,
                "demote": self.demote_count,
                "freeze": self.freeze_count,
                "retire": self.retire_count,
                "hold": self.hold_count,
            },
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with all decision details."""
        result = self.to_dict()
        result["decisions"] = [d.to_dict() for d in self.decisions]
        return result
