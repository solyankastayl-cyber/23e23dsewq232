"""
PHASE 22.2 — Tail Risk Types
============================
Type definitions for Tail Risk Engine.

Core contracts:
- TailRiskState: Tail risk metrics and state
- TailRiskLevel: Risk level enum
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# TAIL RISK LEVEL ENUM
# ══════════════════════════════════════════════════════════════

class TailRiskLevel(str, Enum):
    """Tail risk level."""
    LOW = "LOW"             # score < 0.25
    ELEVATED = "ELEVATED"   # score 0.25-0.45
    HIGH = "HIGH"           # score 0.45-0.65
    EXTREME = "EXTREME"     # score > 0.65


# ══════════════════════════════════════════════════════════════
# TAIL RECOMMENDED ACTION ENUM
# ══════════════════════════════════════════════════════════════

class TailRecommendedAction(str, Enum):
    """Tail risk recommended action."""
    HOLD = "HOLD"                       # LOW
    HEDGE = "HEDGE"                     # ELEVATED
    DELEVER = "DELEVER"                 # HIGH
    EMERGENCY_HEDGE = "EMERGENCY_HEDGE" # EXTREME


# ══════════════════════════════════════════════════════════════
# TAIL RISK STATE THRESHOLDS
# ══════════════════════════════════════════════════════════════

TAIL_RISK_THRESHOLDS = {
    TailRiskLevel.LOW: 0.25,
    TailRiskLevel.ELEVATED: 0.45,
    TailRiskLevel.HIGH: 0.65,
    # > 0.65 = EXTREME
}


# ══════════════════════════════════════════════════════════════
# CRASH VOLATILITY MULTIPLIERS
# ══════════════════════════════════════════════════════════════

CRASH_VOLATILITY_MULTIPLIERS = {
    "LOW": 0.7,
    "NORMAL": 1.0,
    "HIGH": 1.4,
    "EXPANDING": 1.8,
    "EXTREME": 2.2,
    "COMPRESSED": 0.8,
}


# ══════════════════════════════════════════════════════════════
# CRASH CONCENTRATION MULTIPLIERS
# ══════════════════════════════════════════════════════════════

CRASH_CONCENTRATION_MULTIPLIERS = {
    "LOW": 0.8,       # concentration < 0.25
    "MEDIUM": 1.0,    # concentration 0.25-0.45
    "HIGH": 1.3,      # concentration 0.45-0.65
    "VERY_HIGH": 1.6, # concentration > 0.65
}


# ══════════════════════════════════════════════════════════════
# TAIL RISK STATE MODIFIERS
# ══════════════════════════════════════════════════════════════

TAIL_RISK_MODIFIERS = {
    TailRiskLevel.LOW: {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    TailRiskLevel.ELEVATED: {
        "confidence_modifier": 0.95,
        "capital_modifier": 0.90,
    },
    TailRiskLevel.HIGH: {
        "confidence_modifier": 0.85,
        "capital_modifier": 0.75,
    },
    TailRiskLevel.EXTREME: {
        "confidence_modifier": 0.70,
        "capital_modifier": 0.50,
    },
}


# ══════════════════════════════════════════════════════════════
# TAIL RISK SCORE WEIGHTS
# ══════════════════════════════════════════════════════════════

TAIL_RISK_WEIGHTS = {
    "tail_loss": 0.35,
    "crash_sensitivity": 0.25,
    "tail_concentration": 0.20,
    "asymmetry": 0.20,
}


# ══════════════════════════════════════════════════════════════
# TAIL RISK STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class TailRiskState:
    """
    Tail Risk State.
    
    Contains:
    - Tail loss at 95% and 99%
    - Crash sensitivity
    - Tail concentration
    - Asymmetry score
    - Composite tail risk score and state
    """
    # Tail losses
    tail_loss_95: float
    tail_loss_99: float

    # Components
    crash_sensitivity: float
    tail_concentration: float
    asymmetry_score: float

    # Composite
    tail_risk_score: float
    tail_risk_state: TailRiskLevel
    recommended_action: TailRecommendedAction

    # Modifiers
    confidence_modifier: float
    capital_modifier: float

    # Explainability
    reason: str

    # Input details
    gross_exposure: float = 0.0
    deployable_capital: float = 1.0
    volatility_state: str = "NORMAL"
    var_risk_state: str = "NORMAL"

    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tail_loss_95": round(self.tail_loss_95, 4),
            "tail_loss_99": round(self.tail_loss_99, 4),
            "crash_sensitivity": round(self.crash_sensitivity, 4),
            "tail_concentration": round(self.tail_concentration, 4),
            "asymmetry_score": round(self.asymmetry_score, 4),
            "tail_risk_score": round(self.tail_risk_score, 4),
            "tail_risk_state": self.tail_risk_state.value,
            "recommended_action": self.recommended_action.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with input details."""
        result = self.to_dict()
        result["inputs"] = {
            "gross_exposure": round(self.gross_exposure, 4),
            "deployable_capital": round(self.deployable_capital, 4),
            "volatility_state": self.volatility_state,
            "var_risk_state": self.var_risk_state,
        }
        return result

    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "tail_risk_score": round(self.tail_risk_score, 4),
            "tail_risk_state": self.tail_risk_state.value,
            "recommended_action": self.recommended_action.value,
            "crash_sensitivity": round(self.crash_sensitivity, 4),
            "asymmetry_score": round(self.asymmetry_score, 4),
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
        }


# ══════════════════════════════════════════════════════════════
# TAIL RISK HISTORY ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass
class TailRiskHistoryEntry:
    """Single history entry for tail risk state."""
    tail_risk_state: TailRiskLevel
    tail_risk_score: float
    crash_sensitivity: float
    recommended_action: TailRecommendedAction
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tail_risk_state": self.tail_risk_state.value,
            "tail_risk_score": round(self.tail_risk_score, 4),
            "crash_sensitivity": round(self.crash_sensitivity, 4),
            "recommended_action": self.recommended_action.value,
            "timestamp": self.timestamp.isoformat(),
        }
