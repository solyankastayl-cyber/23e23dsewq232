"""
Meta-Alpha Types

PHASE 31.1 — Meta-Alpha Pattern Engine Types

Types for meta-pattern detection across regime, hypothesis, and microstructure.
"""

from typing import List, Literal, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import hashlib


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Minimum observations for pattern validity
MIN_META_OBSERVATIONS = 50

# Meta score weights
META_SCORE_SUCCESS_WEIGHT = 0.50
META_SCORE_PNL_WEIGHT = 0.30
META_SCORE_OBSERVATIONS_WEIGHT = 0.20

# PnL normalization bounds
PNL_NORMALIZE_MIN = -10.0
PNL_NORMALIZE_MAX = 10.0

# Observations normalization (log scale)
OBS_NORMALIZE_BASE = 500  # ln(500) ≈ 6.2

# Classification thresholds
STRONG_META_ALPHA_THRESHOLD = 0.70
MODERATE_META_ALPHA_THRESHOLD = 0.55

# Meta alpha modifiers
META_ALPHA_MODIFIERS = {
    "STRONG_META_ALPHA": 1.25,
    "MODERATE_META_ALPHA": 1.10,
    "WEAK_PATTERN": 1.00,
}


# ══════════════════════════════════════════════════════════════
# Pattern Classification
# ══════════════════════════════════════════════════════════════

MetaAlphaClassification = Literal["STRONG_META_ALPHA", "MODERATE_META_ALPHA", "WEAK_PATTERN"]


# ══════════════════════════════════════════════════════════════
# Meta-Alpha Pattern
# ══════════════════════════════════════════════════════════════

class MetaAlphaPattern(BaseModel):
    """
    A meta-alpha pattern combining regime, hypothesis, and microstructure.
    
    Tracks success rate and PnL for specific combinations to find
    conditions where the system performs best.
    """
    pattern_id: str
    
    # Pattern components
    regime_type: str
    hypothesis_type: str
    microstructure_state: str
    
    # Statistics
    observations: int = 0
    success_rate: float = Field(ge=0.0, le=1.0, default=0.5)
    avg_pnl: float = 0.0
    
    # Meta score
    meta_score: float = Field(ge=0.0, le=1.0, default=0.0)
    classification: MetaAlphaClassification = "WEAK_PATTERN"
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @staticmethod
    def generate_pattern_id(
        regime: str,
        hypothesis: str,
        microstructure: str,
    ) -> str:
        """Generate unique pattern ID from components."""
        key = f"{regime}|{hypothesis}|{microstructure}"
        return hashlib.md5(key.encode()).hexdigest()[:12]


# ══════════════════════════════════════════════════════════════
# Pattern Summary
# ══════════════════════════════════════════════════════════════

class MetaAlphaSummary(BaseModel):
    """
    Summary of meta-alpha patterns for a symbol.
    """
    symbol: str
    
    total_patterns: int = 0
    valid_patterns: int = 0  # With sufficient observations
    
    # Classification counts
    strong_count: int = 0
    moderate_count: int = 0
    weak_count: int = 0
    
    # Average metrics
    avg_meta_score: float = 0.0
    avg_success_rate: float = 0.0
    avg_pnl: float = 0.0
    
    # Best pattern
    best_pattern_id: str = "NONE"
    best_pattern_score: float = 0.0
    best_pattern_description: str = ""
    
    total_observations: int = 0
    last_updated: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# Pattern Observation (for aggregation)
# ══════════════════════════════════════════════════════════════

class PatternObservation(BaseModel):
    """
    Single observation for pattern aggregation.
    """
    regime_type: str
    hypothesis_type: str
    microstructure_state: str
    success: bool
    pnl_percent: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Strong Pattern Response
# ══════════════════════════════════════════════════════════════

class StrongMetaPattern(BaseModel):
    """
    Response format for strong meta-alpha patterns.
    """
    pattern_id: str
    regime_type: str
    hypothesis_type: str
    microstructure_state: str
    meta_score: float
    success_rate: float
    avg_pnl: float
    observations: int
    modifier: float
