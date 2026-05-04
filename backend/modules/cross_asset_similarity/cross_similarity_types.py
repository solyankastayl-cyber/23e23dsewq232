"""
Cross-Asset Similarity Types

PHASE 32.4 — Cross-Asset Similarity Engine Types

Types for cross-asset pattern matching and similarity analysis.
"""

from typing import List, Literal, Optional, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Asset Universe
ASSET_UNIVERSE = ["BTC", "ETH", "SOL", "SPX", "NDX", "DXY"]

# Crypto assets
CRYPTO_ASSETS = ["BTC", "ETH", "SOL"]

# Traditional assets
TRADITIONAL_ASSETS = ["SPX", "NDX", "DXY"]

# Direction types
DirectionType = Literal["LONG", "SHORT", "NEUTRAL"]

# Similarity threshold
SIMILARITY_THRESHOLD = 0.78

# Confidence weights
WEIGHT_SIMILARITY = 0.50
WEIGHT_HISTORICAL_SUCCESS = 0.30
WEIGHT_CROSS_ASSET = 0.20

# Cross-asset weights (how much influence each asset type has)
CROSS_ASSET_WEIGHTS = {
    "BTC": {"ETH": 0.85, "SOL": 0.75, "SPX": 0.60, "NDX": 0.55, "DXY": 0.40},
    "ETH": {"BTC": 0.85, "SOL": 0.80, "SPX": 0.55, "NDX": 0.50, "DXY": 0.35},
    "SOL": {"BTC": 0.75, "ETH": 0.80, "SPX": 0.50, "NDX": 0.45, "DXY": 0.30},
    "SPX": {"BTC": 0.40, "ETH": 0.35, "SOL": 0.30, "NDX": 0.90, "DXY": 0.70},
    "NDX": {"BTC": 0.45, "ETH": 0.40, "SOL": 0.35, "SPX": 0.90, "DXY": 0.65},
    "DXY": {"BTC": 0.50, "ETH": 0.45, "SOL": 0.40, "SPX": 0.70, "NDX": 0.65},
}

# Window sizes for comparison
WINDOW_SIZES = [50, 100, 200]


# ══════════════════════════════════════════════════════════════
# Structure Vector
# ══════════════════════════════════════════════════════════════

class StructureVector(BaseModel):
    """
    Market structure encoded as a vector for similarity comparison.
    """
    symbol: str
    window_size: int = 50
    
    # Vector components
    trend_slope: float = Field(default=0.0, ge=-1.0, le=1.0)
    volatility: float = Field(default=0.0, ge=0.0, le=1.0)
    volume_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    liquidity_state: float = Field(default=0.0, ge=0.0, le=1.0)
    microstructure_bias: float = Field(default=0.0, ge=-1.0, le=1.0)
    
    # Metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_vector(self) -> List[float]:
        """Convert to numeric vector."""
        return [
            self.trend_slope,
            self.volatility,
            self.volume_delta,
            self.liquidity_state,
            self.microstructure_bias,
        ]


# ══════════════════════════════════════════════════════════════
# Cross-Asset Similarity Match
# ══════════════════════════════════════════════════════════════

class CrossAssetMatch(BaseModel):
    """
    Single cross-asset similarity match.
    """
    match_id: str
    
    # Source (current)
    source_symbol: str
    source_timestamp: datetime
    
    # Reference (historical match from different asset)
    reference_symbol: str
    reference_timestamp: datetime
    
    # Similarity metrics
    similarity_score: float = Field(ge=0.0, le=1.0)
    window_size: int = 50
    
    # Historical outcome
    historical_move_percent: float = 0.0
    historical_direction: DirectionType = "NEUTRAL"
    horizon_minutes: int = 60
    
    # Derived metrics
    expected_direction: DirectionType = "NEUTRAL"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    cross_asset_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Cross-Asset Analysis
# ══════════════════════════════════════════════════════════════

class CrossAssetAnalysis(BaseModel):
    """
    Complete cross-asset similarity analysis for a symbol.
    """
    symbol: str
    
    # Current structure
    current_vector: Optional[StructureVector] = None
    
    # All matches above threshold
    matches: List[CrossAssetMatch] = Field(default_factory=list)
    
    # Top match
    top_match: Optional[CrossAssetMatch] = None
    
    # Aggregated signals
    expected_direction: DirectionType = "NEUTRAL"
    aggregated_confidence: float = 0.0
    
    # Asset breakdown
    asset_signals: Dict[str, DirectionType] = Field(default_factory=dict)
    asset_confidences: Dict[str, float] = Field(default_factory=dict)
    
    # Metadata
    assets_compared: List[str] = Field(default_factory=list)
    matches_found: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Cross-Asset Modifier
# ══════════════════════════════════════════════════════════════

class CrossAssetModifier(BaseModel):
    """
    Modifier for hypothesis engine based on cross-asset similarity.
    """
    symbol: str
    
    # Modifier value
    modifier: float = Field(default=1.0, ge=0.85, le=1.15)
    
    # Top cross-asset signal
    top_reference_symbol: str = "NONE"
    top_similarity: float = 0.0
    expected_direction: DirectionType = "NEUTRAL"
    
    # Confidence
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Metadata
    reason: str = ""
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Cross-Asset Summary
# ══════════════════════════════════════════════════════════════

class CrossAssetSummary(BaseModel):
    """
    Summary of cross-asset similarity for a symbol.
    """
    symbol: str
    
    # Current state
    current_top_reference: str = "NONE"
    current_similarity: float = 0.0
    current_direction: DirectionType = "NEUTRAL"
    
    # Historical stats
    total_analyses: int = 0
    avg_similarity: float = 0.0
    most_similar_asset: str = "NONE"
    
    # Asset correlation matrix (simplified)
    asset_correlations: Dict[str, float] = Field(default_factory=dict)
    
    last_updated: Optional[datetime] = None
