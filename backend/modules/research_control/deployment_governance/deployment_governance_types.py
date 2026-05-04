"""
PHASE 17.3 — Deployment Governance Types
=========================================
Contracts for Deployment Governance Engine.

Purpose:
    Define deployment lifecycle states and governance actions.
    Controls factor promotion, rollback, and retirement.

Key Difference from Factor Governance:
    - Factor Governance: evaluates factor quality
    - Deployment Governance: controls factor LIFECYCLE and LIVE deployment
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# DEPLOYMENT STATE ENUM
# ══════════════════════════════════════════════════════════════

class DeploymentState(str, Enum):
    """Factor deployment state in the system lifecycle."""
    SHADOW = "SHADOW"         # Running in shadow mode (no real capital)
    CANDIDATE = "CANDIDATE"   # Candidate for promotion to live
    LIVE = "LIVE"             # Live trading with real capital
    FROZEN = "FROZEN"         # Temporarily frozen (no new positions)
    RETIRED = "RETIRED"       # Permanently retired


class GovernanceAction(str, Enum):
    """Deployment governance actions."""
    KEEP_SHADOW = "KEEP_SHADOW"   # Stay in shadow mode
    PROMOTE = "PROMOTE"           # Promote to next state
    HOLD = "HOLD"                 # Keep current state
    REDUCE = "REDUCE"             # Reduce capital allocation
    ROLLBACK = "ROLLBACK"         # Roll back to previous state
    RETIRE = "RETIRE"             # Retire the factor


class DeploymentDimension(str, Enum):
    """Deployment evaluation dimensions."""
    FACTOR_GOVERNANCE = "factor_governance"
    FEATURE_GOVERNANCE = "feature_governance"
    ECOLOGY = "ecology"
    INTERACTION = "interaction"
    SHADOW_READINESS = "shadow_readiness"


# ══════════════════════════════════════════════════════════════
# DEPLOYMENT THRESHOLDS
# ══════════════════════════════════════════════════════════════

DEPLOYMENT_THRESHOLDS = {
    # Promotion thresholds
    "promotion_score_min": 0.70,      # Min score to promote
    "shadow_readiness_min": 0.65,     # Min shadow readiness to promote
    "rollback_risk_max": 0.35,        # Max rollback risk to promote
    
    # State transition thresholds
    "reduce_threshold": 0.50,         # Below this → REDUCE
    "rollback_threshold": 0.35,       # Below this → ROLLBACK
    "retire_threshold": 0.20,         # Below this → RETIRE
    
    # Shadow duration (days)
    "min_shadow_days": 7,             # Minimum days in shadow
    "optimal_shadow_days": 30,        # Optimal shadow duration
}


# ══════════════════════════════════════════════════════════════
# DEPLOYMENT WEIGHTS
# ══════════════════════════════════════════════════════════════

DEPLOYMENT_WEIGHTS = {
    "factor_governance": 0.35,
    "feature_governance": 0.20,
    "ecology": 0.20,
    "interaction": 0.15,
    "shadow_readiness": 0.10,
}


# ══════════════════════════════════════════════════════════════
# DEPLOYMENT MODIFIERS BY ACTION
# ══════════════════════════════════════════════════════════════

DEPLOYMENT_MODIFIERS = {
    GovernanceAction.PROMOTE: {
        "capital_modifier": 1.10,
        "confidence_modifier": 1.05,
    },
    GovernanceAction.HOLD: {
        "capital_modifier": 1.00,
        "confidence_modifier": 1.00,
    },
    GovernanceAction.KEEP_SHADOW: {
        "capital_modifier": 0.85,
        "confidence_modifier": 0.95,
    },
    GovernanceAction.REDUCE: {
        "capital_modifier": 0.75,
        "confidence_modifier": 0.85,
    },
    GovernanceAction.ROLLBACK: {
        "capital_modifier": 0.50,
        "confidence_modifier": 0.70,
    },
    GovernanceAction.RETIRE: {
        "capital_modifier": 0.00,
        "confidence_modifier": 0.50,
    },
}


# ══════════════════════════════════════════════════════════════
# INPUT TYPES
# ══════════════════════════════════════════════════════════════

@dataclass
class FactorGovernanceInput:
    """Input from Factor Governance."""
    governance_score: float
    governance_state: str
    capital_modifier: float
    confidence_modifier: float
    weakest_dimension: str


@dataclass
class FeatureGovernanceInput:
    """Input from Feature Governance."""
    governance_score: float
    governance_state: str
    weakest_dimension: str


@dataclass
class EcologyInput:
    """Input from Alpha Ecology."""
    ecology_score: float
    ecology_state: str


@dataclass
class InteractionInput:
    """Input from Alpha Interaction."""
    interaction_score: float  # -1 to 1
    interaction_state: str


@dataclass
class DeploymentHistoryInput:
    """Input from deployment history."""
    current_state: DeploymentState
    shadow_duration_days: float
    recent_errors: int
    last_promotion_date: Optional[datetime]
    last_rollback_date: Optional[datetime]


# ══════════════════════════════════════════════════════════════
# DIMENSION RESULT TYPE
# ══════════════════════════════════════════════════════════════

@dataclass
class DeploymentDimensionResult:
    """Result from a single dimension evaluation."""
    dimension: DeploymentDimension
    score: float  # 0..1
    status: str   # READY / CAUTION / NOT_READY
    reason: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "dimension": self.dimension.value,
            "score": round(self.score, 4),
            "status": self.status,
            "reason": self.reason,
            "inputs": self.inputs,
        }


# ══════════════════════════════════════════════════════════════
# DEPLOYMENT GOVERNANCE STATE CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class DeploymentGovernanceResult:
    """
    Output from Deployment Governance Engine.
    
    Controls factor lifecycle:
    - SHADOW: Running without real capital
    - CANDIDATE: Ready for promotion consideration
    - LIVE: Trading with real capital
    - FROZEN: Temporarily stopped
    - RETIRED: Permanently removed
    
    Key Principle:
        Deployment Governance controls LIFECYCLE.
        This is the final gate before live trading.
    """
    factor_name: str
    timestamp: datetime
    
    # Current and target state
    deployment_state: DeploymentState
    deployment_score: float
    
    # Readiness metrics
    shadow_readiness: float
    promotion_readiness: float
    rollback_risk: float
    
    # Governance decision
    governance_action: GovernanceAction
    
    # Modifiers
    capital_modifier: float
    confidence_modifier: float
    
    # Explainability
    reason: str
    strongest_dimension: DeploymentDimension
    weakest_dimension: DeploymentDimension
    
    # Detailed results
    dimension_results: List[DeploymentDimensionResult] = field(default_factory=list)
    
    # Metadata
    drivers: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "factor_name": self.factor_name,
            "timestamp": self.timestamp.isoformat(),
            "deployment_state": self.deployment_state.value,
            "deployment_score": round(self.deployment_score, 4),
            "shadow_readiness": round(self.shadow_readiness, 4),
            "promotion_readiness": round(self.promotion_readiness, 4),
            "rollback_risk": round(self.rollback_risk, 4),
            "governance_action": self.governance_action.value,
            "capital_modifier": round(self.capital_modifier, 4),
            "confidence_modifier": round(self.confidence_modifier, 4),
            "reason": self.reason,
            "strongest_dimension": self.strongest_dimension.value,
            "weakest_dimension": self.weakest_dimension.value,
            "dimension_results": [r.to_dict() for r in self.dimension_results],
            "drivers": self.drivers,
        }
    
    def to_summary(self) -> Dict:
        """Compact summary for quick integration."""
        return {
            "factor_name": self.factor_name,
            "deployment_state": self.deployment_state.value,
            "deployment_score": round(self.deployment_score, 4),
            "governance_action": self.governance_action.value,
            "capital_modifier": round(self.capital_modifier, 4),
            "confidence_modifier": round(self.confidence_modifier, 4),
            "promotion_readiness": round(self.promotion_readiness, 4),
            "rollback_risk": round(self.rollback_risk, 4),
            "reason": self.reason,
        }
