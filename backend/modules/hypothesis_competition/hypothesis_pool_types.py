"""
Hypothesis Competition — Types

PHASE 30.1 — Hypothesis Pool Engine

Types for hypothesis pool and competition model.
"""

from typing import List, Optional, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Pool filtering thresholds
CONFIDENCE_THRESHOLD = 0.30
RELIABILITY_THRESHOLD = 0.25

# Pool size limit
MAX_POOL_SIZE = 5

# Ranking weights
RANKING_WEIGHT_CONFIDENCE = 0.50
RANKING_WEIGHT_RELIABILITY = 0.30
RANKING_WEIGHT_EXECUTION = 0.20

# Pool confidence calculation (top N)
POOL_CONFIDENCE_TOP_N = 3


# ══════════════════════════════════════════════════════════════
# Hypothesis Pool Item
# ══════════════════════════════════════════════════════════════

class HypothesisPoolItem(BaseModel):
    """
    Single hypothesis in the pool.
    
    Contains all scoring metrics and ranking score.
    """
    hypothesis_type: str
    directional_bias: str
    
    # Core scores
    confidence: float = Field(ge=0.0, le=1.0)
    reliability: float = Field(ge=0.0, le=1.0)
    
    # Detailed scores (from PHASE 29.2)
    structural_score: float = Field(ge=0.0, le=1.0)
    execution_score: float = Field(ge=0.0, le=1.0)
    conflict_score: float = Field(ge=0.0, le=1.0)
    
    # Ranking in pool
    ranking_score: float = Field(ge=0.0, le=1.0)
    
    # Execution context
    execution_state: str
    
    # Explanation
    reason: str


# ══════════════════════════════════════════════════════════════
# Hypothesis Pool
# ══════════════════════════════════════════════════════════════

class HypothesisPool(BaseModel):
    """
    Pool of competing hypotheses.
    
    Contains top hypotheses ranked by confidence and reliability.
    Maximum 5 hypotheses per pool.
    """
    symbol: str
    
    # Ranked hypotheses (top first)
    hypotheses: List[HypothesisPoolItem] = Field(default_factory=list)
    
    # Best hypothesis
    top_hypothesis: str = "NO_EDGE"
    
    # Pool-level metrics
    pool_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    pool_reliability: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Pool size
    pool_size: int = 0
    
    # Timestamp
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Hypothesis Pool Summary
# ══════════════════════════════════════════════════════════════

class HypothesisPoolSummary(BaseModel):
    """
    Summary statistics for hypothesis pools.
    """
    symbol: str
    total_pools: int
    
    # Top hypothesis distribution
    top_hypothesis_counts: dict = Field(default_factory=dict)
    
    # Averages
    avg_pool_size: float = 0.0
    avg_pool_confidence: float = 0.0
    avg_pool_reliability: float = 0.0
    
    # Current
    current_top_hypothesis: str = "NO_EDGE"
    current_pool_size: int = 0


# ══════════════════════════════════════════════════════════════
# Hypothesis Pool History Record
# ══════════════════════════════════════════════════════════════

class HypothesisPoolHistoryRecord(BaseModel):
    """
    History record for pool storage.
    """
    symbol: str
    hypotheses: List[dict]
    top_hypothesis: str
    pool_confidence: float
    pool_reliability: float
    pool_size: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
