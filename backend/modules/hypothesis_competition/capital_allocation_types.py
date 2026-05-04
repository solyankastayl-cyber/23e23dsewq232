"""
Capital Allocation Types

PHASE 30.3 — Capital Allocation Engine Types

Types for hypothesis capital allocation and portfolio management.
"""

from typing import List, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Execution state modifiers
EXECUTION_STATE_MODIFIERS = {
    "FAVORABLE": 1.00,
    "CAUTIOUS": 0.80,
    "UNFAVORABLE": 0.00,
}

# Directional risk cap
MAX_DIRECTIONAL_EXPOSURE = 0.65

# Neutral hypothesis cap
MAX_NEUTRAL_ALLOCATION = 0.30

# Minimum allocation threshold
MIN_ALLOCATION_THRESHOLD = 0.05


# ══════════════════════════════════════════════════════════════
# Hypothesis Allocation Item
# ══════════════════════════════════════════════════════════════

class HypothesisAllocation(BaseModel):
    """
    Single hypothesis allocation in the portfolio.
    
    Contains capital weight, percent, and ranking info.
    """
    hypothesis_type: str
    directional_bias: str
    
    ranking_score: float = Field(ge=0.0, le=1.0)
    
    capital_weight: float = Field(ge=0.0, le=1.0)
    capital_percent: float = Field(ge=0.0, le=100.0)
    
    execution_state: str
    
    # Original scores for reference
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    reliability: float = Field(ge=0.0, le=1.0, default=0.0)


# ══════════════════════════════════════════════════════════════
# Hypothesis Capital Allocation (Main Contract)
# ══════════════════════════════════════════════════════════════

class HypothesisCapitalAllocation(BaseModel):
    """
    Capital allocation across hypotheses.
    
    Main output of Capital Allocation Engine.
    Creates portfolio of hypotheses, not single hypothesis selection.
    """
    symbol: str
    
    allocations: List[HypothesisAllocation] = Field(default_factory=list)
    
    total_allocated: float = Field(ge=0.0, le=1.01, default=0.0)  # Allow small rounding errors
    
    portfolio_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    portfolio_reliability: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Allocation metadata
    total_hypotheses_input: int = 0
    hypotheses_removed_unfavorable: int = 0
    hypotheses_removed_min_threshold: int = 0
    directional_cap_applied: bool = False
    neutral_cap_applied: bool = False
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Capital Allocation Summary
# ══════════════════════════════════════════════════════════════

class CapitalAllocationSummary(BaseModel):
    """
    Summary statistics for capital allocations.
    """
    symbol: str
    total_allocations: int
    
    # Directional distribution
    avg_long_exposure: float = 0.0
    avg_short_exposure: float = 0.0
    avg_neutral_exposure: float = 0.0
    
    # Averages
    avg_portfolio_confidence: float = 0.0
    avg_portfolio_reliability: float = 0.0
    avg_hypothesis_count: float = 0.0
    
    # Current state
    current_allocation_count: int = 0
    current_top_hypothesis: str = "NONE"


# ══════════════════════════════════════════════════════════════
# Capital Allocation History Record
# ══════════════════════════════════════════════════════════════

class CapitalAllocationHistoryRecord(BaseModel):
    """
    History record for MongoDB storage.
    """
    symbol: str
    allocations: List[dict]
    portfolio_confidence: float
    portfolio_reliability: float
    total_allocated: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
