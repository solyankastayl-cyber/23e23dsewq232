"""
Regime Memory Types

PHASE 34 — Market Regime Memory Layer

Types for storing and querying historical market states (regime, structure, 
hypothesis, outcome) to inform current analysis.

Structure Vector (7 elements):
- trend_slope
- volatility
- volume_delta
- microstructure_bias
- liquidity_state
- regime_numeric
- fractal_alignment
"""

from typing import List, Literal, Optional, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Structure vector size
VECTOR_SIZE = 7

# Similarity threshold for matches
SIMILARITY_THRESHOLD = 0.75

# Memory score weights
WEIGHT_SIMILARITY = 0.50
WEIGHT_SUCCESS_RATE = 0.30
WEIGHT_RECENCY = 0.20

# Regime memory weight for Hypothesis Engine integration
REGIME_MEMORY_WEIGHT = 0.09

# Scheduler interval
RECOMPUTE_INTERVAL_MINUTES = 60


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

RegimeStateType = Literal[
    "TRENDING",
    "RANGING",
    "VOLATILE",
    "UNCERTAIN",
]

FractalStateType = Literal[
    "ALIGNED",
    "DIVERGENT",
    "NEUTRAL",
]

HypothesisTypeEnum = Literal[
    "BULLISH_CONTINUATION",
    "BEARISH_CONTINUATION",
    "BREAKOUT_FORMING",
    "RANGE_MEAN_REVERSION",
    "NO_EDGE",
]

MicrostructureStateType = Literal[
    "SUPPORTIVE",
    "NEUTRAL",
    "FRAGILE",
    "STRESSED",
]


# ══════════════════════════════════════════════════════════════
# Structure Vector
# ══════════════════════════════════════════════════════════════

class StructureVector(BaseModel):
    """
    Normalized market structure vector for similarity comparison.
    
    7 elements:
    - trend_slope: [-1, 1] — EMA slope normalized
    - volatility: [0, 1] — ATR / avg ATR normalized
    - volume_delta: [-1, 1] — Volume change ratio
    - microstructure_bias: [-1, 1] — Orderbook/pressure directional bias
    - liquidity_state: [0, 1] — Liquidity health normalized
    - regime_numeric: [0, 1] — Regime type encoded (TRENDING=1, RANGING=0.66, VOLATILE=0.33, UNCERTAIN=0)
    - fractal_alignment: [-1, 1] — Multi-timeframe alignment
    """
    trend_slope: float = Field(default=0.0, ge=-1.0, le=1.0)
    volatility: float = Field(default=0.5, ge=0.0, le=1.0)
    volume_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    microstructure_bias: float = Field(default=0.0, ge=-1.0, le=1.0)
    liquidity_state: float = Field(default=0.5, ge=0.0, le=1.0)
    regime_numeric: float = Field(default=0.5, ge=0.0, le=1.0)
    fractal_alignment: float = Field(default=0.0, ge=-1.0, le=1.0)
    
    def to_vector(self) -> List[float]:
        """Convert to list for cosine similarity calculation."""
        return [
            self.trend_slope,
            self.volatility,
            self.volume_delta,
            self.microstructure_bias,
            self.liquidity_state,
            self.regime_numeric,
            self.fractal_alignment,
        ]
    
    @classmethod
    def from_vector(cls, vec: List[float]) -> "StructureVector":
        """Create from list."""
        if len(vec) != VECTOR_SIZE:
            raise ValueError(f"Vector must have {VECTOR_SIZE} elements, got {len(vec)}")
        return cls(
            trend_slope=vec[0],
            volatility=vec[1],
            volume_delta=vec[2],
            microstructure_bias=vec[3],
            liquidity_state=vec[4],
            regime_numeric=vec[5],
            fractal_alignment=vec[6],
        )


# ══════════════════════════════════════════════════════════════
# Regime Memory Record
# ══════════════════════════════════════════════════════════════

class RegimeMemoryRecord(BaseModel):
    """
    Memory record storing market state snapshot with future outcome.
    
    This is the core data structure for regime memory.
    Records are created after outcome tracking completes.
    """
    # Identifiers
    record_id: str = Field(default="")
    symbol: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Discrete state at snapshot time
    regime_state: RegimeStateType = "UNCERTAIN"
    fractal_state: FractalStateType = "NEUTRAL"
    hypothesis_type: HypothesisTypeEnum = "NO_EDGE"
    microstructure_state: MicrostructureStateType = "NEUTRAL"
    
    # Encoded structure vector (7 elements)
    structure_vector: List[float] = Field(default_factory=lambda: [0.0] * VECTOR_SIZE)
    
    # Future outcome (filled after horizon_minutes)
    future_move_percent: float = 0.0
    horizon_minutes: int = 60
    
    # Success flag (True if hypothesis direction matched outcome)
    success: bool = False
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Memory Match
# ══════════════════════════════════════════════════════════════

class MemoryMatch(BaseModel):
    """
    Result of similarity search against historical memory.
    """
    record_id: str
    similarity: float = Field(ge=0.0, le=1.0)
    memory_score: float = Field(ge=0.0, le=1.0)
    future_move: float
    success_rate: float = Field(ge=0.0, le=1.0)
    timestamp: datetime
    
    # Context from matched record
    regime_state: str = ""
    hypothesis_type: str = ""
    horizon_minutes: int = 60


# ══════════════════════════════════════════════════════════════
# Memory Query
# ══════════════════════════════════════════════════════════════

class MemoryQuery(BaseModel):
    """
    Query for finding similar historical memories.
    """
    symbol: str
    query_vector: List[float] = Field(default_factory=list)
    
    # Optional filters
    regime_filter: Optional[RegimeStateType] = None
    hypothesis_filter: Optional[HypothesisTypeEnum] = None
    min_similarity: float = SIMILARITY_THRESHOLD
    
    # Limits
    limit: int = 10


# ══════════════════════════════════════════════════════════════
# Memory Response
# ══════════════════════════════════════════════════════════════

class MemoryResponse(BaseModel):
    """
    Response from memory query.
    """
    symbol: str
    query_vector: List[float] = Field(default_factory=list)
    
    # Matches found
    matches: List[MemoryMatch] = Field(default_factory=list)
    top_matches: List[MemoryMatch] = Field(default_factory=list)  # Top 5
    
    # Aggregated signals
    expected_direction: str = "NEUTRAL"  # LONG / SHORT / NEUTRAL
    aggregated_success_rate: float = 0.0
    avg_future_move: float = 0.0
    
    # Memory score (for hypothesis engine)
    memory_score: float = 0.0
    memory_confidence: float = 0.0
    
    # Stats
    total_records_searched: int = 0
    matches_found: int = 0
    best_similarity: float = 0.0
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Memory Pattern
# ══════════════════════════════════════════════════════════════

class MemoryPattern(BaseModel):
    """
    Aggregated pattern from memory analysis.
    """
    pattern_type: str  # e.g., "BULLISH_TRENDING", "BEARISH_VOLATILE"
    occurrence_count: int = 0
    avg_success_rate: float = 0.0
    avg_future_move: float = 0.0
    
    regime_state: str = ""
    hypothesis_type: str = ""
    
    sample_records: List[str] = Field(default_factory=list)  # record_ids


# ══════════════════════════════════════════════════════════════
# Memory Summary
# ══════════════════════════════════════════════════════════════

class MemorySummary(BaseModel):
    """
    Summary of regime memory for a symbol.
    """
    symbol: str
    
    # Counts
    total_records: int = 0
    successful_records: int = 0
    failed_records: int = 0
    
    # Success rates by regime
    trending_success_rate: float = 0.0
    ranging_success_rate: float = 0.0
    volatile_success_rate: float = 0.0
    
    # Success rates by hypothesis
    bullish_continuation_success: float = 0.0
    bearish_continuation_success: float = 0.0
    breakout_success: float = 0.0
    mean_reversion_success: float = 0.0
    
    # Overall
    overall_success_rate: float = 0.0
    avg_future_move: float = 0.0
    
    # Recent performance
    recent_accuracy: float = 0.0  # Last 100 records
    
    last_updated: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# Memory Modifier (for Hypothesis Engine)
# ══════════════════════════════════════════════════════════════

class MemoryModifier(BaseModel):
    """
    Modifier for hypothesis scoring based on memory analysis.
    """
    symbol: str
    
    # Memory-based adjustment
    memory_score: float = Field(ge=0.0, le=1.0)
    memory_confidence: float = Field(ge=0.0, le=1.0)
    
    # Direction signal from memory
    expected_direction: str = "NEUTRAL"
    is_aligned: bool = False
    
    # Modifier value
    modifier: float = 1.0  # 1.0 = neutral, >1 = boost, <1 = reduce
    
    # Stats
    matches_found: int = 0
    best_similarity: float = 0.0
    historical_success_rate: float = 0.0
    
    reason: str = ""


# ══════════════════════════════════════════════════════════════
# Pending Outcome Record
# ══════════════════════════════════════════════════════════════

class PendingOutcomeRecord(BaseModel):
    """
    Record waiting for outcome evaluation.
    
    Memory layer is read-heavy: writes happen only after outcome tracking.
    This tracks pending records that haven't been evaluated yet.
    """
    pending_id: str
    symbol: str
    
    # Snapshot at creation time
    regime_state: RegimeStateType
    fractal_state: FractalStateType
    hypothesis_type: HypothesisTypeEnum
    microstructure_state: MicrostructureStateType
    structure_vector: List[float]
    
    # Tracking info
    entry_price: float
    horizon_minutes: int = 60
    expected_outcome_time: datetime
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
