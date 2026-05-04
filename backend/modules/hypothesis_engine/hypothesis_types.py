"""
Hypothesis Engine — Types

PHASE 29.1 — Hypothesis Contract + Core Engine

Contracts:
- MarketHypothesis (main output)
- HypothesisCandidate (internal)
- HypothesisInputLayers (engine input from intelligence layers)
- HypothesisHistoryRecord (registry storage)
- HypothesisSummary (aggregated statistics)
"""

from typing import Literal
from datetime import datetime
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

HypothesisType = Literal[
    "BULLISH_CONTINUATION",
    "BEARISH_CONTINUATION",
    "BREAKOUT_FORMING",
    "BREAKOUT_FAILURE_RISK",
    "RANGE_MEAN_REVERSION",
    "SHORT_SQUEEZE_SETUP",
    "LONG_SQUEEZE_SETUP",
    "VOLATILE_UNWIND",
    "NO_EDGE",
]

DirectionalBias = Literal["LONG", "SHORT", "NEUTRAL"]

ExecutionState = Literal["FAVORABLE", "CAUTIOUS", "UNFAVORABLE"]

# PHASE 29.3 — Conflict State
ConflictStateType = Literal["LOW_CONFLICT", "MODERATE_CONFLICT", "HIGH_CONFLICT"]


# ══════════════════════════════════════════════════════════════
# Constants — Scoring Weights
# ══════════════════════════════════════════════════════════════

WEIGHT_ALPHA = 0.40
WEIGHT_REGIME = 0.30
WEIGHT_MICROSTRUCTURE = 0.20
WEIGHT_MACRO = 0.10


# ══════════════════════════════════════════════════════════════
# Main Contract
# ══════════════════════════════════════════════════════════════

class MarketHypothesis(BaseModel):
    """
    Market hypothesis — output of the Hypothesis Engine.

    Represents the engine's best guess about current market state
    based on signals from all intelligence layers.
    
    PHASE 29.2 additions:
    - structural_score: How market-logically sound is the idea
    - execution_score: How safe is it to trade now
    - conflict_score: How much do layers contradict each other
    
    PHASE 29.3 additions:
    - conflict_state: Classification of conflict level (LOW/MODERATE/HIGH)
    """
    symbol: str

    hypothesis_type: HypothesisType

    directional_bias: DirectionalBias

    # PHASE 29.2 — New scoring components
    structural_score: float = Field(default=0.0, ge=0.0, le=1.0)
    execution_score: float = Field(default=0.0, ge=0.0, le=1.0)
    conflict_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # PHASE 29.3 — Conflict state classification
    conflict_state: ConflictStateType = Field(default="LOW_CONFLICT")

    # Derived from structural + execution scores (adjusted by conflict resolver)
    confidence: float = Field(ge=0.0, le=1.0)
    reliability: float = Field(ge=0.0, le=1.0)

    # Support from intelligence layers
    alpha_support: float = Field(ge=0.0, le=1.0)
    regime_support: float = Field(ge=0.0, le=1.0)
    microstructure_support: float = Field(ge=0.0, le=1.0)
    macro_fractal_support: float = Field(ge=0.0, le=1.0)

    # PHASE 29.2/29.3 — Execution state now derived from execution_score and conflict
    execution_state: ExecutionState

    created_at: datetime = Field(default_factory=datetime.utcnow)

    reason: str


# ══════════════════════════════════════════════════════════════
# Internal Candidate
# ══════════════════════════════════════════════════════════════

class HypothesisCandidate(BaseModel):
    """
    Internal candidate generated during hypothesis evaluation.

    Multiple candidates are scored; the best one becomes MarketHypothesis.
    """
    hypothesis_type: str

    alpha_support: float = Field(ge=0.0, le=1.0)
    regime_support: float = Field(ge=0.0, le=1.0)
    microstructure_support: float = Field(ge=0.0, le=1.0)
    macro_support: float = Field(ge=0.0, le=1.0)

    directional_bias: str


# ══════════════════════════════════════════════════════════════
# Engine Input Layers
# ══════════════════════════════════════════════════════════════

class HypothesisInputLayers(BaseModel):
    """
    Input data collected from all intelligence layers.

    Sources:
    - AlphaFactory
    - RegimeContext
    - MicrostructureContext
    - MacroFractalContext
    - ExecutionContext
    """
    # Alpha Factory
    alpha_direction: str = "NEUTRAL"          # BULLISH / BEARISH / NEUTRAL
    alpha_strength: float = 0.5               # overall alpha factor strength [0-1]
    alpha_breakout_strength: float = 0.0      # breakout factors strength [0-1]
    alpha_mean_reversion_strength: float = 0.0  # mean reversion factors [0-1]

    # Regime Context
    regime_type: str = "UNCERTAIN"            # TRENDING / RANGING / VOLATILE / UNCERTAIN
    regime_confidence: float = 0.5            # regime detection confidence [0-1]
    regime_in_transition: bool = False        # currently transitioning

    # Microstructure Context
    microstructure_state: str = "NEUTRAL"     # SUPPORTIVE / NEUTRAL / FRAGILE / STRESSED
    microstructure_confidence: float = 0.5    # microstructure confidence [0-1]
    vacuum_direction: str = "NONE"            # UP / DOWN / NONE
    pressure_directional: bool = False        # is pressure directional
    pressure_direction: str = "NONE"          # UP / DOWN / NONE

    # Macro-Fractal Context
    macro_confidence: float = 0.5             # macro context confidence [0-1]


# ══════════════════════════════════════════════════════════════
# History Record
# ══════════════════════════════════════════════════════════════

class HypothesisHistoryRecord(BaseModel):
    """Record stored in market_hypothesis_history collection."""
    symbol: str
    hypothesis_type: str
    directional_bias: str
    confidence: float
    reliability: float
    execution_state: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════

class HypothesisSummary(BaseModel):
    """Aggregated statistics from hypothesis history."""
    symbol: str
    total_records: int

    # Type counts
    bullish_continuation_count: int = 0
    bearish_continuation_count: int = 0
    breakout_forming_count: int = 0
    range_mean_reversion_count: int = 0
    no_edge_count: int = 0
    other_count: int = 0

    # Bias counts
    long_count: int = 0
    short_count: int = 0
    neutral_count: int = 0

    # Execution state counts
    favorable_count: int = 0
    cautious_count: int = 0
    unfavorable_count: int = 0

    # Averages
    average_confidence: float = 0.0
    average_reliability: float = 0.0

    # Current
    current_hypothesis: str = "NO_EDGE"
    current_bias: str = "NEUTRAL"
