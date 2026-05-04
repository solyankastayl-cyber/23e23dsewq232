"""
Orderbook Pressure Map — Types

PHASE 28.3 — Orderbook Pressure Detection

Key concepts:
- Bid/Ask pressure: weighted sum of sizes by distance
- Net pressure: (bid - ask) / (bid + ask)
- Absorption zones: large walls that absorb price movement
- Sweep risk: probability of fast price move through thin side

States:
- pressure_bias: BID_DOMINANT, ASK_DOMINANT, BALANCED
- absorption_zone: BID_ABSORPTION, ASK_ABSORPTION, NONE
- sweep_risk: UP, DOWN, NONE
- pressure_state: SUPPORTIVE, NEUTRAL, FRAGILE, STRESSED
"""

from typing import Literal, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

PressureBias = Literal["BID_DOMINANT", "ASK_DOMINANT", "BALANCED"]
AbsorptionZone = Literal["BID_ABSORPTION", "ASK_ABSORPTION", "NONE"]
SweepRisk = Literal["UP", "DOWN", "NONE"]
PressureState = Literal["SUPPORTIVE", "NEUTRAL", "FRAGILE", "STRESSED"]


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Pressure bias thresholds
BIAS_THRESHOLD = 0.15

# Absorption detection
WALL_SIZE_MULTIPLIER = 3.0
ABSORPTION_DISTANCE_THRESHOLD_BPS = 10.0

# Sweep probability weights
SWEEP_WEIGHT_NET_PRESSURE = 0.40
SWEEP_WEIGHT_VACUUM = 0.30
SWEEP_WEIGHT_DEPTH = 0.30

# Confidence weights
CONF_WEIGHT_NET_PRESSURE = 0.35
CONF_WEIGHT_DEPTH = 0.25
CONF_WEIGHT_SWEEP = 0.20
CONF_WEIGHT_ABSORPTION = 0.20

# State thresholds
SWEEP_PROB_HIGH = 0.6
SWEEP_PROB_MODERATE = 0.4


# ══════════════════════════════════════════════════════════════
# Input Data
# ══════════════════════════════════════════════════════════════

class OrderbookPressureLevel(BaseModel):
    """Single orderbook level for pressure calculation."""
    price: float
    size: float
    distance_bps: float = 0.0


class OrderbookPressureInput(BaseModel):
    """Orderbook levels for pressure calculation."""
    bids: List[OrderbookPressureLevel] = Field(default_factory=list)
    asks: List[OrderbookPressureLevel] = Field(default_factory=list)
    mid_price: float = 0.0


class MicrostructurePressureContext(BaseModel):
    """Context from MicrostructureSnapshot and LiquidityVacuumState."""
    depth_score: float = 0.5
    imbalance_score: float = 0.0
    spread_bps: float = 1.0
    vacuum_probability: float = 0.0
    vacuum_direction: str = "NONE"
    liquidity_state: str = "NORMAL"


# ══════════════════════════════════════════════════════════════
# Main Contract
# ══════════════════════════════════════════════════════════════

class OrderbookPressureMap(BaseModel):
    """
    Orderbook pressure map for a symbol.
    
    Identifies bid/ask pressure, absorption zones, and sweep risk.
    """
    symbol: str
    
    # Pressure metrics
    bid_pressure: float = Field(ge=0.0, description="Weighted bid pressure")
    ask_pressure: float = Field(ge=0.0, description="Weighted ask pressure")
    net_pressure: float = Field(ge=-1.0, le=1.0, description="Net pressure ratio")
    
    # Classifications
    pressure_bias: PressureBias
    absorption_zone: AbsorptionZone
    sweep_risk: SweepRisk
    
    # Sweep probability
    sweep_probability: float = Field(ge=0.0, le=1.0)
    
    # Overall state
    pressure_state: PressureState
    
    # Confidence
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Explanation
    reason: str
    
    # Metadata
    computed_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# History Record
# ══════════════════════════════════════════════════════════════

class OrderbookPressureHistoryRecord(BaseModel):
    """Historical record of orderbook pressure."""
    symbol: str
    bid_pressure: float
    ask_pressure: float
    net_pressure: float
    pressure_bias: PressureBias
    absorption_zone: AbsorptionZone
    sweep_risk: SweepRisk
    sweep_probability: float
    pressure_state: PressureState
    confidence: float
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════

class OrderbookPressureSummary(BaseModel):
    """Summary of orderbook pressure history."""
    symbol: str
    total_records: int
    
    # Bias counts
    bid_dominant_count: int
    ask_dominant_count: int
    balanced_count: int
    
    # Absorption counts
    bid_absorption_count: int
    ask_absorption_count: int
    no_absorption_count: int
    
    # Sweep risk counts
    sweep_up_count: int
    sweep_down_count: int
    sweep_none_count: int
    
    # State counts
    supportive_count: int
    neutral_count: int
    fragile_count: int
    stressed_count: int
    
    # Averages
    average_bid_pressure: float
    average_ask_pressure: float
    average_net_pressure: float
    average_sweep_probability: float
    average_confidence: float
    
    # Current
    current_state: PressureState
    current_bias: PressureBias
