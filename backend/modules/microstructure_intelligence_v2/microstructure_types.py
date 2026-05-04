"""
Microstructure Intelligence v2 — Types

Contracts for microstructure snapshot.

Key metrics:
- spread_bps: Bid-ask spread in basis points
- depth_score: Orderbook depth (0-1)
- imbalance_score: Bid/ask volume imbalance (-1 to +1)
- liquidation_pressure: Liquidation intensity (-1 to +1)
- funding_pressure: Funding rate pressure (-1 to +1)
- oi_pressure: Open interest change pressure (-1 to +1)

States:
- liquidity_state: DEEP, NORMAL, THIN
- pressure_state: BUY_PRESSURE, SELL_PRESSURE, BALANCED
- microstructure_state: SUPPORTIVE, NEUTRAL, FRAGILE, STRESSED
"""

from typing import Literal, List
from datetime import datetime
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

LiquidityState = Literal["DEEP", "NORMAL", "THIN"]
PressureState = Literal["BUY_PRESSURE", "SELL_PRESSURE", "BALANCED"]
MicrostructureState = Literal["SUPPORTIVE", "NEUTRAL", "FRAGILE", "STRESSED"]


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Depth thresholds
DEPTH_DEEP_THRESHOLD = 0.70
DEPTH_NORMAL_THRESHOLD = 0.40

# Spread thresholds (bps)
SPREAD_LOW_THRESHOLD = 5.0
SPREAD_HIGH_THRESHOLD = 15.0

# Imbalance thresholds
IMBALANCE_THRESHOLD = 0.15

# Pressure thresholds
PRESSURE_HIGH_THRESHOLD = 0.50
PRESSURE_EXTREME_THRESHOLD = 0.70

# Confidence weights
CONF_WEIGHT_SPREAD = 0.25
CONF_WEIGHT_DEPTH = 0.25
CONF_WEIGHT_IMBALANCE = 0.20
CONF_WEIGHT_LIQUIDATION = 0.15
CONF_WEIGHT_OI = 0.15


# ══════════════════════════════════════════════════════════════
# Main Contract
# ══════════════════════════════════════════════════════════════

class MicrostructureSnapshot(BaseModel):
    """
    Microstructure snapshot of current market state.
    
    Combines orderbook, liquidation, funding, and OI data.
    """
    symbol: str
    
    # Core metrics
    spread_bps: float = Field(ge=0.0, description="Spread in basis points")
    depth_score: float = Field(ge=0.0, le=1.0, description="Normalized orderbook depth")
    imbalance_score: float = Field(ge=-1.0, le=1.0, description="Bid/ask volume imbalance")
    
    # Pressure metrics
    liquidation_pressure: float = Field(ge=-1.0, le=1.0, description="Liquidation intensity")
    funding_pressure: float = Field(ge=-1.0, le=1.0, description="Funding rate pressure")
    oi_pressure: float = Field(ge=-1.0, le=1.0, description="OI change pressure")
    
    # State classifications
    liquidity_state: LiquidityState
    pressure_state: PressureState
    microstructure_state: MicrostructureState
    
    # Confidence
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Explanation
    reason: str
    
    # Metadata
    computed_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# History Record
# ══════════════════════════════════════════════════════════════

class MicrostructureHistoryRecord(BaseModel):
    """Historical record of microstructure snapshot."""
    symbol: str
    spread_bps: float
    depth_score: float
    imbalance_score: float
    liquidation_pressure: float
    funding_pressure: float
    oi_pressure: float
    liquidity_state: LiquidityState
    pressure_state: PressureState
    microstructure_state: MicrostructureState
    confidence: float
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# Input Data
# ══════════════════════════════════════════════════════════════

class OrderbookData(BaseModel):
    """Raw orderbook data for snapshot calculation."""
    best_bid: float
    best_ask: float
    bid_volume: float
    ask_volume: float
    total_depth: float
    depth_reference: float = 1000000.0  # Reference depth for normalization


class ExchangeData(BaseModel):
    """Exchange intelligence data for snapshot calculation."""
    liquidation_long: float = 0.0
    liquidation_short: float = 0.0
    funding_rate: float = 0.0
    oi_current: float = 0.0
    oi_previous: float = 0.0


# ══════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════

class MicrostructureSummary(BaseModel):
    """Summary of microstructure history."""
    symbol: str
    total_records: int
    
    deep_count: int
    normal_count: int
    thin_count: int
    
    buy_pressure_count: int
    sell_pressure_count: int
    balanced_count: int
    
    supportive_count: int
    neutral_count: int
    fragile_count: int
    stressed_count: int
    
    average_spread_bps: float
    average_depth_score: float
    average_confidence: float
    
    current_state: MicrostructureState
