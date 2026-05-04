"""
Adaptive Weight Types

PHASE 30.5 — Adaptive Weight Engine Types

Types for hypothesis adaptive weighting based on performance.
"""

from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Minimum observations required for adaptive weighting
MIN_OBSERVATIONS = 30

# Success rate modifier bounds
SUCCESS_MODIFIER_MIN = 0.70
SUCCESS_MODIFIER_MAX = 1.30
SUCCESS_MODIFIER_SCALE = 1.2

# PnL modifier bounds
PNL_MODIFIER_MIN = 0.75
PNL_MODIFIER_MAX = 1.25
PNL_POSITIVE_SCALE = 0.25
PNL_NEGATIVE_SCALE = 0.40

# Combined modifier bounds
COMBINED_MODIFIER_MIN = 0.65
COMBINED_MODIFIER_MAX = 1.35

# Modifier weights
SUCCESS_WEIGHT = 0.60
PNL_WEIGHT = 0.40


# ══════════════════════════════════════════════════════════════
# Hypothesis Adaptive Weight
# ══════════════════════════════════════════════════════════════

class HypothesisAdaptiveWeight(BaseModel):
    """
    Adaptive weight for a hypothesis type.
    
    Calculated from performance data to boost/penalize hypotheses.
    """
    hypothesis_type: str
    
    # Performance metrics
    success_rate: float = Field(ge=0.0, le=1.0, default=0.5)
    avg_pnl: float = 0.0
    
    # Weight components
    base_weight: float = Field(ge=0.0, le=1.0, default=1.0)
    success_modifier: float = Field(ge=SUCCESS_MODIFIER_MIN, le=SUCCESS_MODIFIER_MAX, default=1.0)
    pnl_modifier: float = Field(ge=PNL_MODIFIER_MIN, le=PNL_MODIFIER_MAX, default=1.0)
    adaptive_modifier: float = Field(ge=COMBINED_MODIFIER_MIN, le=COMBINED_MODIFIER_MAX, default=1.0)
    
    # Final weight
    final_weight: float = Field(ge=0.0, default=1.0)
    
    # Observations count
    observations: int = 0
    
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Adaptive Weight Summary
# ══════════════════════════════════════════════════════════════

class AdaptiveWeightSummary(BaseModel):
    """
    Summary of adaptive weights for a symbol.
    """
    symbol: str
    
    total_hypothesis_types: int = 0
    total_observations: int = 0
    
    # Modifiers distribution
    avg_adaptive_modifier: float = 1.0
    max_adaptive_modifier: float = 1.0
    min_adaptive_modifier: float = 1.0
    
    # Boost/penalize counts
    boosted_count: int = 0  # modifier > 1.0
    penalized_count: int = 0  # modifier < 1.0
    neutral_count: int = 0  # modifier == 1.0
    
    # Best/worst performers
    best_hypothesis: str = "NONE"
    best_modifier: float = 1.0
    worst_hypothesis: str = "NONE"
    worst_modifier: float = 1.0
    
    last_updated: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# Adaptive Weight History Record
# ══════════════════════════════════════════════════════════════

class AdaptiveWeightRecord(BaseModel):
    """
    MongoDB storage record for adaptive weights.
    """
    symbol: str
    hypothesis_type: str
    success_rate: float
    avg_pnl: float
    success_modifier: float
    pnl_modifier: float
    adaptive_modifier: float
    final_weight: float
    observations: int
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
