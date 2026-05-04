"""
Regime Transition Detector — Types

Contracts for regime transition detection.

Transition States:
- STABLE: No transition expected
- EARLY_SHIFT: Early signs of regime change
- ACTIVE_TRANSITION: Regime change in progress
- UNSTABLE: High volatility, unpredictable
"""

from typing import Literal, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

RegimeType = Literal["TRENDING", "RANGING", "VOLATILE", "ILLIQUID"]
NextRegimeCandidate = Literal["TRENDING", "RANGING", "VOLATILE", "ILLIQUID", "NONE"]
TransitionState = Literal["STABLE", "EARLY_SHIFT", "ACTIVE_TRANSITION", "UNSTABLE"]


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Transition state thresholds
STABLE_THRESHOLD = 0.25
EARLY_SHIFT_THRESHOLD = 0.45
ACTIVE_TRANSITION_THRESHOLD = 0.70

# Score weights
WEIGHT_TREND_SHIFT = 0.35
WEIGHT_VOLATILITY_SHIFT = 0.35
WEIGHT_LIQUIDITY_SHIFT = 0.20
WEIGHT_CONFIDENCE_DECAY = 0.10

# Probability weights
PROB_WEIGHT_SCORE = 0.70
PROB_WEIGHT_CONFIDENCE = 0.30

# Modifiers by transition state
TRANSITION_MODIFIERS = {
    "STABLE": {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    "EARLY_SHIFT": {
        "confidence_modifier": 0.97,
        "capital_modifier": 0.95,
    },
    "ACTIVE_TRANSITION": {
        "confidence_modifier": 0.92,
        "capital_modifier": 0.88,
    },
    "UNSTABLE": {
        "confidence_modifier": 0.85,
        "capital_modifier": 0.75,
    },
}

# Trigger thresholds
TREND_SHIFT_THRESHOLD = 0.10
VOLATILITY_SHIFT_THRESHOLD = 0.12
LIQUIDITY_SHIFT_THRESHOLD = 0.15
CONFIDENCE_DECAY_THRESHOLD = 0.10


# ══════════════════════════════════════════════════════════════
# Main Contract
# ══════════════════════════════════════════════════════════════

class RegimeTransitionState(BaseModel):
    """
    Current regime transition state.
    
    Detects probability of regime change before it happens.
    """
    # Current state
    current_regime: RegimeType
    
    # Predicted next regime
    next_regime_candidate: NextRegimeCandidate
    
    # Transition metrics
    transition_probability: float = Field(ge=0.0, le=1.0)
    transition_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Classification
    transition_state: TransitionState
    
    # Triggers
    trigger_factors: List[str] = Field(default_factory=list)
    
    # Modifiers for execution
    confidence_modifier: float = Field(ge=0.0, le=1.0)
    capital_modifier: float = Field(ge=0.0, le=1.0)
    
    # Explanation
    reason: str
    
    # Metadata
    symbol: str = "BTCUSDT"
    timeframe: str = "1H"
    computed_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# History Record
# ══════════════════════════════════════════════════════════════

class TransitionHistoryRecord(BaseModel):
    """Historical record of transition state."""
    current_regime: RegimeType
    next_regime_candidate: NextRegimeCandidate
    transition_probability: float
    transition_state: TransitionState
    trigger_factors: List[str]
    symbol: str
    timeframe: str
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════

class TransitionSummary(BaseModel):
    """Summary of transition history."""
    total_records: int
    
    stable_count: int
    early_shift_count: int
    active_transition_count: int
    unstable_count: int
    
    current_state: TransitionState
    average_probability: float
    
    most_common_trigger: str
    transition_frequency: float  # How often transitions occur


# ══════════════════════════════════════════════════════════════
# Metric Snapshot
# ══════════════════════════════════════════════════════════════

class RegimeMetricSnapshot(BaseModel):
    """Snapshot of regime metrics for comparison."""
    regime_type: RegimeType
    trend_strength: float
    volatility_level: float
    liquidity_level: float
    regime_confidence: float
    dominant_driver: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
