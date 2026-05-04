"""
PHASE 22.5 — Crisis Exposure Types
==================================
Type definitions for Crisis Exposure Aggregator.

Core contracts:
- CrisisExposureState: Unified crisis metrics
- CrisisState: Crisis level enum
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# CRISIS STATE ENUM
# ══════════════════════════════════════════════════════════════

class CrisisState(str, Enum):
    """Crisis exposure state."""
    NORMAL = "NORMAL"       # score < 0.30
    GUARDED = "GUARDED"     # score 0.30-0.50
    STRESSED = "STRESSED"   # score 0.50-0.70
    CRISIS = "CRISIS"       # score > 0.70


# ══════════════════════════════════════════════════════════════
# CRISIS RECOMMENDED ACTION ENUM
# ══════════════════════════════════════════════════════════════

class CrisisAction(str, Enum):
    """Crisis-based recommended action."""
    HOLD = "HOLD"                     # NORMAL
    REDUCE_RISK = "REDUCE_RISK"       # GUARDED
    DELEVER = "DELEVER"               # STRESSED
    EMERGENCY_MODE = "EMERGENCY_MODE" # CRISIS


# ══════════════════════════════════════════════════════════════
# CRISIS STATE THRESHOLDS
# ══════════════════════════════════════════════════════════════

CRISIS_THRESHOLDS = {
    CrisisState.NORMAL: 0.30,
    CrisisState.GUARDED: 0.50,
    CrisisState.STRESSED: 0.70,
    # > 0.70 = CRISIS
}


# ══════════════════════════════════════════════════════════════
# STATE NORMALIZATION SCORES
# ══════════════════════════════════════════════════════════════

STATE_SCORES = {
    # VaR states
    "var": {
        "NORMAL": 0.20,
        "ELEVATED": 0.45,
        "HIGH": 0.70,
        "CRITICAL": 0.95,
    },
    # Tail Risk states
    "tail": {
        "LOW": 0.20,
        "ELEVATED": 0.45,
        "HIGH": 0.70,
        "EXTREME": 0.95,
    },
    # Contagion states
    "contagion": {
        "LOW": 0.20,
        "ELEVATED": 0.45,
        "HIGH": 0.70,
        "SYSTEMIC": 0.95,
    },
    # Correlation states
    "correlation": {
        "NORMAL": 0.20,
        "ELEVATED": 0.45,
        "HIGH": 0.70,
        "SYSTEMIC": 0.95,
    },
}


# ══════════════════════════════════════════════════════════════
# CRISIS SCORE WEIGHTS
# ══════════════════════════════════════════════════════════════

CRISIS_SCORE_WEIGHTS = {
    "var": 0.30,
    "tail": 0.25,
    "contagion": 0.25,
    "correlation": 0.20,
}


# ══════════════════════════════════════════════════════════════
# CRISIS STATE MODIFIERS
# ══════════════════════════════════════════════════════════════

CRISIS_MODIFIERS = {
    CrisisState.NORMAL: {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    CrisisState.GUARDED: {
        "confidence_modifier": 0.92,
        "capital_modifier": 0.85,
    },
    CrisisState.STRESSED: {
        "confidence_modifier": 0.80,
        "capital_modifier": 0.65,
    },
    CrisisState.CRISIS: {
        "confidence_modifier": 0.60,
        "capital_modifier": 0.40,
    },
}


# ══════════════════════════════════════════════════════════════
# RISK DIMENSION LABELS
# ══════════════════════════════════════════════════════════════

RISK_DIMENSIONS = {
    "var": "VaR Risk",
    "tail": "Tail Risk",
    "contagion": "Contagion Risk",
    "correlation": "Correlation Risk",
}


# ══════════════════════════════════════════════════════════════
# CRISIS EXPOSURE STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class CrisisExposureState:
    """
    Unified Crisis Exposure State.
    
    Aggregates all institutional risk dimensions into a single state.
    """
    # Input states
    var_state: str
    tail_state: str
    contagion_state: str
    correlation_state: str
    
    # Normalized scores
    var_score: float
    tail_score: float
    contagion_score: float
    correlation_score: float
    
    # Composite
    crisis_score: float
    crisis_state: CrisisState
    
    # Action
    recommended_action: CrisisAction
    
    # Combined modifiers (conservative min logic)
    confidence_modifier: float
    capital_modifier: float
    
    # Analysis
    strongest_risk: str
    weakest_risk: str
    
    # Explainability
    reason: str
    
    # Component modifiers (for reference)
    component_modifiers: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "var_state": self.var_state,
            "tail_state": self.tail_state,
            "contagion_state": self.contagion_state,
            "correlation_state": self.correlation_state,
            "crisis_score": round(self.crisis_score, 4),
            "crisis_state": self.crisis_state.value,
            "recommended_action": self.recommended_action.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "strongest_risk": self.strongest_risk,
            "weakest_risk": self.weakest_risk,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with all details."""
        result = self.to_dict()
        result["scores"] = {
            "var": round(self.var_score, 4),
            "tail": round(self.tail_score, 4),
            "contagion": round(self.contagion_score, 4),
            "correlation": round(self.correlation_score, 4),
        }
        result["component_modifiers"] = self.component_modifiers
        return result
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "crisis_score": round(self.crisis_score, 4),
            "crisis_state": self.crisis_state.value,
            "recommended_action": self.recommended_action.value,
            "strongest_risk": self.strongest_risk,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
        }


# ══════════════════════════════════════════════════════════════
# CRISIS HISTORY ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass
class CrisisHistoryEntry:
    """Single history entry for crisis state."""
    crisis_state: CrisisState
    crisis_score: float
    strongest_risk: str
    recommended_action: CrisisAction
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "crisis_state": self.crisis_state.value,
            "crisis_score": round(self.crisis_score, 4),
            "strongest_risk": self.strongest_risk,
            "recommended_action": self.recommended_action.value,
            "timestamp": self.timestamp.isoformat(),
        }
