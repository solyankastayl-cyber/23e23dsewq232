"""
Reflexivity Engine Types

PHASE 35 — Market Reflexivity Engine

Types for modeling market reflexivity (Soros theory).

Reflexivity Score Formula:
  reflexivity_score = 0.35 * sentiment
                    + 0.25 * positioning
                    + 0.20 * trend_acceleration
                    + 0.20 * volatility_expansion

Interpretation:
  score < 0.35 → weak reflexivity
  0.35-0.65 → moderate reflexivity
  > 0.65 → strong reflexivity
"""

from typing import List, Literal, Optional, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Reflexivity weight in Hypothesis Engine formula
REFLEXIVITY_WEIGHT = 0.06

# Component weights
WEIGHT_SENTIMENT = 0.35
WEIGHT_POSITIONING = 0.25
WEIGHT_TREND_ACCELERATION = 0.20
WEIGHT_VOLATILITY_EXPANSION = 0.20

# Score thresholds
WEAK_REFLEXIVITY_THRESHOLD = 0.35
STRONG_REFLEXIVITY_THRESHOLD = 0.65

# Feedback direction thresholds
POSITIVE_FEEDBACK_THRESHOLD = 0.15
NEGATIVE_FEEDBACK_THRESHOLD = -0.15


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

SentimentStateType = Literal[
    "EXTREME_GREED",
    "GREED",
    "NEUTRAL",
    "FEAR",
    "EXTREME_FEAR",
]

FeedbackDirectionType = Literal[
    "POSITIVE",      # Self-reinforcing loop (trend acceleration)
    "NEGATIVE",      # Mean-reverting loop (trend exhaustion)
    "NEUTRAL",       # No clear feedback
]

ReflexivityStrengthType = Literal[
    "WEAK",
    "MODERATE",
    "STRONG",
]


# ══════════════════════════════════════════════════════════════
# Reflexivity Source Data
# ══════════════════════════════════════════════════════════════

class ReflexivitySource(BaseModel):
    """
    Source data for reflexivity calculation.
    
    Derived from:
    - Funding rates
    - Open interest changes
    - Liquidations
    - Volume spikes
    - Trend acceleration
    """
    # Funding context
    funding_rate: float = 0.0
    funding_sentiment: float = 0.0  # [-1, 1] derived from funding
    
    # Open interest
    oi_change_24h: float = 0.0  # Percent change
    oi_expansion: bool = False
    
    # Liquidations
    long_liquidations: float = 0.0
    short_liquidations: float = 0.0
    liquidation_imbalance: float = 0.0  # [-1, 1]
    
    # Volume
    volume_spike_ratio: float = 1.0  # Current / avg volume
    
    # Trend
    price_momentum: float = 0.0  # [-1, 1]
    trend_acceleration: float = 0.0  # Rate of change of momentum


# ══════════════════════════════════════════════════════════════
# Reflexivity State
# ══════════════════════════════════════════════════════════════

class ReflexivityState(BaseModel):
    """
    Current reflexivity state for a symbol.
    
    Main contract for PHASE 35.
    """
    symbol: str
    
    # Sentiment derived from market data
    sentiment_state: SentimentStateType = "NEUTRAL"
    
    # Crowd positioning [-1, 1] (negative = short-heavy, positive = long-heavy)
    crowd_positioning: float = Field(default=0.0, ge=-1.0, le=1.0)
    
    # Core reflexivity score [0, 1]
    reflexivity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Feedback loop direction
    feedback_direction: FeedbackDirectionType = "NEUTRAL"
    
    # Reflexivity strength
    strength: ReflexivityStrengthType = "WEAK"
    
    # Confidence in the reflexivity signal
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Component scores (for debugging/transparency)
    sentiment_score: float = Field(default=0.0, ge=0.0, le=1.0)
    positioning_score: float = Field(default=0.0, ge=0.0, le=1.0)
    trend_acceleration_score: float = Field(default=0.0, ge=0.0, le=1.0)
    volatility_expansion_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Source data
    source: Optional[ReflexivitySource] = None
    
    # Timestamp
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Explanation
    reason: str = ""


# ══════════════════════════════════════════════════════════════
# Reflexivity History
# ══════════════════════════════════════════════════════════════

class ReflexivityHistory(BaseModel):
    """
    Historical reflexivity record for analysis.
    """
    symbol: str
    
    # Core metrics
    reflexivity_score: float
    feedback_direction: str
    sentiment_state: str
    crowd_positioning: float
    confidence: float
    
    # Timestamp
    recorded_at: datetime


# ══════════════════════════════════════════════════════════════
# Reflexivity Modifier (for Hypothesis Engine)
# ══════════════════════════════════════════════════════════════

class ReflexivityModifier(BaseModel):
    """
    Modifier for hypothesis scoring based on reflexivity analysis.
    
    New Hypothesis Formula (PHASE 35):
      0.28 alpha
    + 0.20 regime
    + 0.15 microstructure
    + 0.08 macro
    + 0.05 fractal_market
    + 0.05 fractal_similarity
    + 0.05 cross_asset_similarity
    + 0.08 regime_memory
    + 0.06 reflexivity  <-- NEW
    = 1.00
    """
    symbol: str
    
    # Reflexivity contribution
    reflexivity_score: float = Field(ge=0.0, le=1.0)
    reflexivity_weight: float = REFLEXIVITY_WEIGHT
    
    # Weighted contribution to hypothesis
    weighted_contribution: float = Field(ge=0.0, le=1.0)
    
    # Direction alignment
    feedback_direction: str = "NEUTRAL"
    is_trend_aligned: bool = False  # True if feedback supports current trend
    
    # Modifier value
    modifier: float = 1.0  # >1 boosts, <1 reduces
    
    # Context
    strength: str = "WEAK"
    confidence: float = 0.0
    reason: str = ""


# ══════════════════════════════════════════════════════════════
# Reflexivity Summary
# ══════════════════════════════════════════════════════════════

class ReflexivitySummary(BaseModel):
    """
    Summary statistics for reflexivity analysis.
    """
    symbol: str
    
    # Current state
    current_score: float = 0.0
    current_direction: str = "NEUTRAL"
    current_strength: str = "WEAK"
    
    # Historical stats
    total_records: int = 0
    avg_score: float = 0.0
    
    # Distribution
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0
    neutral_count: int = 0
    
    # Strength distribution
    strong_reflexivity_count: int = 0
    moderate_reflexivity_count: int = 0
    weak_reflexivity_count: int = 0
    
    # Recent trend
    recent_avg_score: float = 0.0  # Last 24h
    score_trend: str = "STABLE"  # INCREASING / DECREASING / STABLE
    
    last_updated: Optional[datetime] = None
