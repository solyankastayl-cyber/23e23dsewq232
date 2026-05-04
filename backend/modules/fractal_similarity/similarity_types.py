"""
Fractal Similarity Types

PHASE 32.2 — Fractal Similarity Engine Types

Types for historical pattern matching and similarity analysis.
"""

from typing import List, Literal, Optional, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Window sizes for structure encoding (candles)
WINDOW_SIZES = [50, 100, 200]

# Similarity threshold for match
SIMILARITY_THRESHOLD = 0.75

# Direction types
DirectionType = Literal["LONG", "SHORT", "NEUTRAL"]

# Confidence weights
SIMILARITY_WEIGHT = 0.60
HISTORICAL_SUCCESS_WEIGHT = 0.40

# Modifiers
SIMILARITY_ALIGNED_MODIFIER = 1.12
SIMILARITY_CONFLICT_MODIFIER = 0.90


# ══════════════════════════════════════════════════════════════
# Structure Vector
# ══════════════════════════════════════════════════════════════

class StructureVector(BaseModel):
    """
    Encoded market structure vector.
    
    Converts candle window into numeric features for similarity comparison.
    """
    symbol: str
    window_size: int
    
    # Core features
    trend_slope: float = Field(default=0.0, description="EMA slope normalized")
    volatility_ratio: float = Field(default=1.0, description="ATR / avg ATR")
    volume_delta: float = Field(default=0.0, description="Volume change ratio")
    momentum: float = Field(default=0.0, description="RSI normalized to [-1, 1]")
    range_position: float = Field(default=0.5, description="Price position in range [0, 1]")
    
    # Secondary features
    body_ratio: float = Field(default=0.5, description="Avg candle body / range")
    upper_wick_ratio: float = Field(default=0.25, description="Avg upper wick / range")
    lower_wick_ratio: float = Field(default=0.25, description="Avg lower wick / range")
    trend_strength: float = Field(default=0.5, description="ADX normalized [0, 1]")
    
    # Derived
    vector: List[float] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_vector(self) -> List[float]:
        """Convert to numeric vector for similarity calculation."""
        return [
            self.trend_slope,
            self.volatility_ratio,
            self.volume_delta,
            self.momentum,
            self.range_position,
            self.body_ratio,
            self.upper_wick_ratio,
            self.lower_wick_ratio,
            self.trend_strength,
        ]


# ══════════════════════════════════════════════════════════════
# Historical Pattern
# ══════════════════════════════════════════════════════════════

class HistoricalPattern(BaseModel):
    """
    Historical pattern stored for comparison.
    """
    pattern_id: str
    symbol: str
    window_size: int
    
    # Structure vector
    vector: List[float]
    
    # Outcome after pattern
    outcome_direction: DirectionType = "NEUTRAL"
    outcome_return: float = 0.0  # % return after X bars
    outcome_bars: int = 20  # How many bars until outcome
    
    # Success tracking
    was_successful: bool = False
    
    # Metadata
    start_timestamp: datetime
    end_timestamp: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Similarity Match
# ══════════════════════════════════════════════════════════════

class SimilarityMatch(BaseModel):
    """
    Result of similarity comparison.
    """
    pattern_id: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    
    # Historical outcome
    historical_direction: DirectionType
    historical_return: float
    was_successful: bool
    
    # Pattern metadata
    pattern_timestamp: datetime
    window_size: int


# ══════════════════════════════════════════════════════════════
# Similarity Analysis
# ══════════════════════════════════════════════════════════════

class SimilarityAnalysis(BaseModel):
    """
    Complete similarity analysis result.
    """
    symbol: str
    
    # Current structure
    current_vector: Optional[StructureVector] = None
    
    # Matches found
    matches: List[SimilarityMatch] = Field(default_factory=list)
    top_matches: List[SimilarityMatch] = Field(default_factory=list)  # Top 5
    
    # Inferred direction
    expected_direction: DirectionType = "NEUTRAL"
    direction_confidence: float = 0.0
    
    # Success rate of similar patterns
    historical_success_rate: float = 0.0
    avg_historical_return: float = 0.0
    
    # Confidence
    similarity_confidence: float = 0.0
    
    # Metadata
    patterns_searched: int = 0
    matches_found: int = 0
    best_similarity: float = 0.0
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Similarity Modifier
# ══════════════════════════════════════════════════════════════

class SimilarityModifier(BaseModel):
    """
    Modifier for hypothesis scoring based on similarity analysis.
    """
    hypothesis_direction: str
    expected_direction: DirectionType
    similarity_confidence: float
    
    is_aligned: bool
    modifier: float
    
    # Details
    matches_found: int
    best_similarity: float
    historical_success_rate: float
    
    reason: str


# ══════════════════════════════════════════════════════════════
# Similarity Summary
# ══════════════════════════════════════════════════════════════

class SimilaritySummary(BaseModel):
    """
    Summary of similarity analysis for a symbol.
    """
    symbol: str
    
    # Current state
    current_direction: DirectionType = "NEUTRAL"
    current_confidence: float = 0.0
    
    # Historical performance
    total_patterns_stored: int = 0
    total_analyses: int = 0
    avg_match_rate: float = 0.0
    avg_success_rate: float = 0.0
    
    # Best performing windows
    best_window_size: int = 100
    best_window_success_rate: float = 0.0
    
    last_updated: Optional[datetime] = None
