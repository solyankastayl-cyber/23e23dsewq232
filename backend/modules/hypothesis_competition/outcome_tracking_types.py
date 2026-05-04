"""
Outcome Tracking Types

PHASE 30.4 — Outcome Tracking Engine Types

Types for hypothesis outcome tracking and performance measurement.
"""

from typing import List, Literal, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Evaluation horizons (in minutes)
EVALUATION_HORIZONS = [5, 15, 60, 240]

# Success tolerance (to filter micro noise)
SUCCESS_TOLERANCE = 0.0015  # 0.15%

# Volatility threshold for NEUTRAL success
NEUTRAL_VOLATILITY_THRESHOLD = 0.005  # 0.5%


# ══════════════════════════════════════════════════════════════
# Direction Type
# ══════════════════════════════════════════════════════════════

DirectionType = Literal["LONG", "SHORT", "NEUTRAL", "UP", "DOWN", "FLAT"]


# ══════════════════════════════════════════════════════════════
# Hypothesis Outcome
# ══════════════════════════════════════════════════════════════

class HypothesisOutcome(BaseModel):
    """
    Outcome of a hypothesis after evaluation.
    
    Tracks:
    - Original hypothesis parameters
    - Price movement
    - PnL calculation
    - Success/failure determination
    """
    symbol: str
    
    hypothesis_type: str
    directional_bias: str
    
    price_at_creation: float = Field(gt=0)
    evaluation_price: float = Field(gt=0)
    
    horizon_minutes: int = Field(ge=5)
    
    expected_direction: str
    actual_direction: str
    
    pnl_percent: float
    
    success: bool
    
    confidence: float = Field(ge=0.0, le=1.0)
    reliability: float = Field(ge=0.0, le=1.0)
    
    # Capital allocation info
    capital_weight: float = Field(ge=0.0, le=1.0, default=0.0)
    
    created_at: datetime
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Hypothesis Performance (Aggregated)
# ══════════════════════════════════════════════════════════════

class HypothesisPerformance(BaseModel):
    """
    Aggregated performance metrics for a hypothesis type.
    
    Used for system self-learning and calibration.
    """
    hypothesis_type: str
    
    total_predictions: int = 0
    
    success_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    
    avg_pnl: float = 0.0
    
    avg_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    avg_reliability: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Correlation metrics
    confidence_accuracy_correlation: float = Field(ge=-1.0, le=1.0, default=0.0)
    reliability_accuracy_correlation: float = Field(ge=-1.0, le=1.0, default=0.0)
    
    # Breakdown by horizon
    success_rate_5m: float = Field(ge=0.0, le=1.0, default=0.0)
    success_rate_15m: float = Field(ge=0.0, le=1.0, default=0.0)
    success_rate_60m: float = Field(ge=0.0, le=1.0, default=0.0)
    success_rate_240m: float = Field(ge=0.0, le=1.0, default=0.0)


# ══════════════════════════════════════════════════════════════
# Symbol Performance Summary
# ══════════════════════════════════════════════════════════════

class SymbolOutcomeSummary(BaseModel):
    """
    Overall outcome summary for a symbol.
    """
    symbol: str
    
    total_outcomes: int = 0
    
    overall_success_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    overall_avg_pnl: float = 0.0
    
    # By direction
    long_success_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    short_success_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    neutral_success_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Best/worst performers
    best_hypothesis_type: str = "NONE"
    best_success_rate: float = 0.0
    worst_hypothesis_type: str = "NONE"
    worst_success_rate: float = 0.0
    
    # Correlation quality
    avg_confidence_accuracy_correlation: float = 0.0
    
    last_evaluated_at: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# Pending Evaluation Record
# ══════════════════════════════════════════════════════════════

class PendingHypothesisEvaluation(BaseModel):
    """
    Record of hypothesis waiting for outcome evaluation.
    """
    symbol: str
    hypothesis_type: str
    directional_bias: str
    confidence: float
    reliability: float
    capital_weight: float
    price_at_creation: float
    created_at: datetime
    horizons_evaluated: List[int] = Field(default_factory=list)


# ══════════════════════════════════════════════════════════════
# Outcome History Record
# ══════════════════════════════════════════════════════════════

class OutcomeHistoryRecord(BaseModel):
    """
    MongoDB storage record for outcomes.
    """
    symbol: str
    hypothesis_type: str
    directional_bias: str
    confidence: float
    reliability: float
    capital_weight: float
    price_at_creation: float
    evaluation_price: float
    horizon_minutes: int
    expected_direction: str
    actual_direction: str
    pnl_percent: float
    success: bool
    created_at: datetime
    evaluated_at: datetime
