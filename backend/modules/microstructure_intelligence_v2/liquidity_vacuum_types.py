"""
Liquidity Vacuum Detector — Types

PHASE 28.2 — Liquidity Vacuum Detection

Key concepts:
- Orderbook gaps: areas with no/thin liquidity
- Vacuum direction: UP (gap above price) or DOWN (gap below)
- Vacuum probability: likelihood of fast price movement through gap
- Liquidity wall: large order that blocks price movement

States:
- NORMAL: gap_bps < 2
- THIN_ZONE: 2 <= gap_bps < 5
- VACUUM: gap_bps >= 5
"""

from typing import Literal, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

VacuumDirection = Literal["UP", "DOWN", "NONE"]
VacuumLiquidityState = Literal["NORMAL", "THIN_ZONE", "VACUUM"]


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Gap thresholds (bps)
GAP_ANOMALY_THRESHOLD = 3.0
GAP_NORMAL_THRESHOLD = 2.0
GAP_THIN_THRESHOLD = 5.0

# Liquidity wall threshold (multiplier of median size)
WALL_SIZE_MULTIPLIER = 3.0

# Vacuum probability weights
VACUUM_WEIGHT_GAP = 0.45
VACUUM_WEIGHT_DEPTH = 0.35
VACUUM_WEIGHT_IMBALANCE = 0.20

# Confidence weights
CONF_WEIGHT_GAP = 0.40
CONF_WEIGHT_SPREAD = 0.30
CONF_WEIGHT_DEPTH = 0.30


# ══════════════════════════════════════════════════════════════
# Input Data
# ══════════════════════════════════════════════════════════════

class OrderbookLevel(BaseModel):
    """Single orderbook level."""
    price: float
    size: float


class OrderbookLevels(BaseModel):
    """Orderbook levels for vacuum detection."""
    bids: List[OrderbookLevel] = Field(default_factory=list, description="Bid levels (descending price)")
    asks: List[OrderbookLevel] = Field(default_factory=list, description="Ask levels (ascending price)")
    mid_price: float = 0.0


class MicrostructureContext(BaseModel):
    """Context from MicrostructureSnapshot."""
    depth_score: float = 0.5
    imbalance_score: float = 0.0
    spread_bps: float = 1.0


# ══════════════════════════════════════════════════════════════
# Gap Detection
# ══════════════════════════════════════════════════════════════

class OrderbookGap(BaseModel):
    """Detected gap in orderbook."""
    price_start: float
    price_end: float
    gap_bps: float
    side: Literal["BID", "ASK"]
    level_index: int


# ══════════════════════════════════════════════════════════════
# Main Contract
# ══════════════════════════════════════════════════════════════

class LiquidityVacuumState(BaseModel):
    """
    Liquidity vacuum state for a symbol.
    
    Identifies areas where price can move quickly due to lack of liquidity.
    """
    symbol: str
    
    # Vacuum direction
    vacuum_direction: VacuumDirection
    
    # Vacuum metrics
    vacuum_probability: float = Field(ge=0.0, le=1.0, description="Probability of fast movement")
    vacuum_size_bps: float = Field(ge=0.0, description="Size of largest gap in bps")
    
    # Liquidity wall
    nearest_liquidity_wall_distance: float = Field(ge=0.0, description="Distance to nearest wall in bps")
    
    # Gap analysis
    orderbook_gap_score: float = Field(ge=0.0, description="Ratio of max gap to expected gap")
    
    # State classification
    liquidity_state: VacuumLiquidityState
    
    # Confidence
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Explanation
    reason: str
    
    # Metadata
    computed_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# History Record
# ══════════════════════════════════════════════════════════════

class LiquidityVacuumHistoryRecord(BaseModel):
    """Historical record of liquidity vacuum state."""
    symbol: str
    vacuum_direction: VacuumDirection
    vacuum_probability: float
    vacuum_size_bps: float
    nearest_liquidity_wall_distance: float
    orderbook_gap_score: float
    liquidity_state: VacuumLiquidityState
    confidence: float
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════

class LiquidityVacuumSummary(BaseModel):
    """Summary of liquidity vacuum history."""
    symbol: str
    total_records: int
    
    # Direction counts
    up_count: int
    down_count: int
    none_count: int
    
    # State counts
    normal_count: int
    thin_zone_count: int
    vacuum_count: int
    
    # Averages
    average_vacuum_probability: float
    average_vacuum_size_bps: float
    average_wall_distance: float
    average_gap_score: float
    average_confidence: float
    
    # Current
    current_state: VacuumLiquidityState
    current_direction: VacuumDirection
