"""
PHASE 18.2 — Portfolio Constraint Types
=======================================
Contracts for Portfolio Constraint Engine.

Purpose:
    Define contracts for portfolio constraint checking,
    violation detection, and trade permission logic.

Key Concept:
    HARD CONSTRAINTS - cannot be violated
    SOFT CONSTRAINTS - can violate with penalty
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class ConstraintState(str, Enum):
    """Portfolio constraint state."""
    OK = "OK"                   # No violations
    SOFT_LIMIT = "SOFT_LIMIT"  # Soft constraint violated (allowed with penalty)
    HARD_LIMIT = "HARD_LIMIT"  # Hard constraint violated (not allowed)


class ConstraintType(str, Enum):
    """Type of constraint."""
    HARD = "HARD"   # Cannot be violated
    SOFT = "SOFT"   # Can violate with penalty


class ViolationType(str, Enum):
    """Type of violation."""
    EXPOSURE = "EXPOSURE"       # Net/Gross exposure
    CLUSTER = "CLUSTER"         # Cluster concentration
    FACTOR = "FACTOR"           # Factor concentration
    LEVERAGE = "LEVERAGE"       # Leverage limit


# ══════════════════════════════════════════════════════════════
# CONSTRAINT LIMITS
# ══════════════════════════════════════════════════════════════

# Hard constraints - cannot be violated
EXPOSURE_LIMITS = {
    "max_net_exposure": 1.5,
    "max_gross_exposure": 2.5,
}

LEVERAGE_LIMITS = {
    "max_leverage": 2.5,  # Same as gross exposure
}

# Soft constraints - can violate with penalty
CLUSTER_LIMITS = {
    "max_cluster_exposure": 0.65,
}

FACTOR_LIMITS = {
    "max_factor_exposure": 0.70,
}


# ══════════════════════════════════════════════════════════════
# STATE MODIFIERS
# ══════════════════════════════════════════════════════════════

CONSTRAINT_STATE_MODIFIERS = {
    ConstraintState.OK: {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    ConstraintState.SOFT_LIMIT: {
        "confidence_modifier": 0.90,
        "capital_modifier": 0.85,
    },
    ConstraintState.HARD_LIMIT: {
        "confidence_modifier": 0.70,
        "capital_modifier": 0.00,  # No capital allocation
    },
}


# ══════════════════════════════════════════════════════════════
# VIOLATION DATACLASS
# ══════════════════════════════════════════════════════════════

@dataclass
class ConstraintViolation:
    """Individual constraint violation."""
    violation_type: ViolationType
    constraint_type: ConstraintType
    current_value: float
    limit_value: float
    severity: float  # 0-1, how much over the limit
    description: str
    
    def to_dict(self) -> Dict:
        return {
            "violation_type": self.violation_type.value,
            "constraint_type": self.constraint_type.value,
            "current_value": round(self.current_value, 4),
            "limit_value": round(self.limit_value, 4),
            "severity": round(self.severity, 4),
            "description": self.description,
        }


# ══════════════════════════════════════════════════════════════
# MAIN OUTPUT CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class PortfolioConstraintState:
    """
    Portfolio Constraint State - Main output contract.
    
    Determines if a trade is allowed based on portfolio constraints.
    
    Key fields:
    - constraint_state: OK / SOFT_LIMIT / HARD_LIMIT
    - allowed: Whether new position can be opened
    - confidence_modifier: Applied to trade confidence
    - capital_modifier: Applied to position sizing
    """
    # Main state
    constraint_state: ConstraintState
    
    # Violation flags
    exposure_violation: bool
    cluster_violation: bool
    factor_violation: bool
    leverage_violation: bool
    
    # Permission
    allowed: bool
    
    # Modifiers
    confidence_modifier: float
    capital_modifier: float
    
    # Reason
    reason: str
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Detailed violations
    violations: List[ConstraintViolation] = field(default_factory=list)
    
    # Constraint values
    constraint_values: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            "constraint_state": self.constraint_state.value,
            "exposure_violation": self.exposure_violation,
            "cluster_violation": self.cluster_violation,
            "factor_violation": self.factor_violation,
            "leverage_violation": self.leverage_violation,
            "allowed": self.allowed,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict:
        """Full dictionary with all details."""
        result = self.to_dict()
        result["violations"] = [v.to_dict() for v in self.violations]
        result["constraint_values"] = self.constraint_values
        return result
    
    def to_summary(self) -> Dict:
        """Compact summary for quick integration."""
        return {
            "state": self.constraint_state.value,
            "allowed": self.allowed,
            "confidence_mod": round(self.confidence_modifier, 2),
            "capital_mod": round(self.capital_modifier, 2),
            "reason": self.reason[:100] if len(self.reason) > 100 else self.reason,
        }


# ══════════════════════════════════════════════════════════════
# CHECK REQUEST
# ══════════════════════════════════════════════════════════════

@dataclass
class ConstraintCheckRequest:
    """Request to check if a new trade would violate constraints."""
    symbol: str
    direction: str
    size: float
    portfolio_id: str = "default"
