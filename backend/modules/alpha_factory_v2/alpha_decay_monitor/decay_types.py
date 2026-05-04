"""
Alpha Decay Monitor — Types

Contracts for alpha decay detection.

Key entities:
- AlphaDecayState: Current decay state of a factor
- DecayHistory: Historical decay record
"""

from typing import Literal, Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Decay State Enum
# ══════════════════════════════════════════════════════════════

DecayState = Literal["STABLE", "DECAYING", "CRITICAL"]
RecommendedAction = Literal["KEEP", "REDUCE", "DEPRECATE"]


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Alpha drift thresholds
DRIFT_STABLE_MAX = 0.10
DRIFT_DECAYING_MAX = 0.20

# Decay rate thresholds
DECAY_RATE_STABLE_MAX = 0.10
DECAY_RATE_DECAYING_MAX = 0.25

# Modifiers
MODIFIERS = {
    "STABLE": {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    "DECAYING": {
        "confidence_modifier": 0.90,
        "capital_modifier": 0.85,
    },
    "CRITICAL": {
        "confidence_modifier": 0.70,
        "capital_modifier": 0.50,
    },
}


# ══════════════════════════════════════════════════════════════
# Main Contract
# ══════════════════════════════════════════════════════════════

class AlphaDecayState(BaseModel):
    """
    Decay state for a single alpha factor.
    
    Computed from current vs previous alpha_score.
    """
    factor_id: str
    factor_name: str = ""
    
    # Alpha scores
    current_alpha_score: float
    previous_alpha_score: float
    
    # Decay metrics
    alpha_drift: float = Field(
        ge=0.0,
        description="Absolute difference: |current - previous|"
    )
    decay_rate: float = Field(
        ge=0.0,
        description="Relative decay: (prev - curr) / prev, 0 if improving"
    )
    
    # Classification
    decay_state: DecayState
    recommended_action: RecommendedAction
    
    # Modifiers for downstream systems
    confidence_modifier: float = Field(ge=0.0, le=1.0)
    capital_modifier: float = Field(ge=0.0, le=1.0)
    
    # Explanation
    reason: str
    
    # Metadata
    computed_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# History Record
# ══════════════════════════════════════════════════════════════

class DecayHistoryRecord(BaseModel):
    """Historical record of decay state."""
    factor_id: str
    previous_alpha_score: float
    current_alpha_score: float
    alpha_drift: float
    decay_rate: float
    decay_state: DecayState
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════

class DecaySummary(BaseModel):
    """Summary of all factors' decay states."""
    total_factors: int
    stable_count: int
    decaying_count: int
    critical_count: int
    
    average_decay_rate: float
    max_decay_rate: float
    
    critical_factors: List[str] = Field(default_factory=list)
