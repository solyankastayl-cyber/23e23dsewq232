"""
Microstructure Context Integration — Types

PHASE 28.5 — Unified Microstructure Context

Aggregates all 4 microstructure layers:
- MicrostructureSnapshot (28.1)
- LiquidityVacuumState (28.2)
- OrderbookPressureMap (28.3)
- LiquidationCascadeState (28.4)

Into unified MicrostructureContext for execution decisions.
"""

from typing import Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

LiquidityState = Literal["DEEP", "NORMAL", "THIN"]
PressureBias = Literal["BID_DOMINANT", "ASK_DOMINANT", "BALANCED"]
Direction = Literal["UP", "DOWN", "NONE"]
MicrostructureState = Literal["SUPPORTIVE", "NEUTRAL", "FRAGILE", "STRESSED"]
DominantDriver = Literal["LIQUIDITY", "PRESSURE", "VACUUM", "CASCADE", "MIXED"]


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Confidence modifier weights
CONF_WEIGHT_DEPTH = 0.08
CONF_WEIGHT_PRESSURE = 0.06
CONF_WEIGHT_VACUUM = 0.08
CONF_WEIGHT_CASCADE = 0.12

# Capital modifier weights
CAP_WEIGHT_DEPTH = 0.10
CAP_WEIGHT_VACUUM = 0.10
CAP_WEIGHT_CASCADE = 0.15

# Modifier bounds
CONF_MOD_MIN = 0.82
CONF_MOD_MAX = 1.12
CAP_MOD_MIN = 0.70
CAP_MOD_MAX = 1.10

# State thresholds
CASCADE_STRESSED_THRESHOLD = 0.45
DRIVER_MIXED_THRESHOLD = 0.05


# ══════════════════════════════════════════════════════════════
# Input Context (from 4 layers)
# ══════════════════════════════════════════════════════════════

class MicrostructureInputLayers(BaseModel):
    """Input data from all 4 microstructure layers."""
    # From MicrostructureSnapshot (28.1)
    snapshot_liquidity_state: str = "NORMAL"
    snapshot_microstructure_state: str = "NEUTRAL"
    snapshot_confidence: float = 0.5
    snapshot_depth_score: float = 0.5
    
    # From LiquidityVacuumState (28.2)
    vacuum_direction: str = "NONE"
    vacuum_probability: float = 0.0
    vacuum_liquidity_state: str = "NORMAL"
    
    # From OrderbookPressureMap (28.3)
    pressure_bias: str = "BALANCED"
    sweep_probability: float = 0.0
    pressure_state: str = "NEUTRAL"
    net_pressure: float = 0.0
    
    # From LiquidationCascadeState (28.4)
    cascade_direction: str = "NONE"
    cascade_probability: float = 0.0
    cascade_state: str = "STABLE"
    cascade_severity: str = "LOW"


# ══════════════════════════════════════════════════════════════
# Main Contract
# ══════════════════════════════════════════════════════════════

class MicrostructureContext(BaseModel):
    """
    Unified microstructure context aggregating all 4 layers.
    
    Provides execution-critical modifiers for confidence and capital.
    """
    symbol: str
    
    # States from layers
    liquidity_state: LiquidityState
    pressure_bias: PressureBias
    vacuum_direction: Direction
    cascade_direction: Direction
    
    # Probabilities
    vacuum_probability: float = Field(ge=0.0, le=1.0)
    sweep_probability: float = Field(ge=0.0, le=1.0)
    cascade_probability: float = Field(ge=0.0, le=1.0)
    
    # Unified state
    microstructure_state: MicrostructureState
    
    # Modifiers
    confidence_modifier: float = Field(ge=CONF_MOD_MIN, le=CONF_MOD_MAX)
    capital_modifier: float = Field(ge=CAP_MOD_MIN, le=CAP_MOD_MAX)
    
    # Driver analysis
    dominant_driver: DominantDriver
    
    # Explanation
    reason: str
    
    # Metadata
    computed_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# Drivers Breakdown
# ══════════════════════════════════════════════════════════════

class MicrostructureDrivers(BaseModel):
    """Breakdown of microstructure drivers."""
    symbol: str
    
    liquidity_impact: float
    pressure_impact: float
    vacuum_impact: float
    cascade_impact: float
    
    dominant: DominantDriver
    
    direction_consistency: bool
    consistency_score: float


# ══════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════

class MicrostructureContextSummary(BaseModel):
    """Summary of microstructure context."""
    symbol: str
    
    # State counts (from recent history)
    supportive_count: int
    neutral_count: int
    fragile_count: int
    stressed_count: int
    
    # Driver counts
    liquidity_dominant_count: int
    pressure_dominant_count: int
    vacuum_dominant_count: int
    cascade_dominant_count: int
    mixed_dominant_count: int
    
    # Averages
    average_confidence_modifier: float
    average_capital_modifier: float
    average_vacuum_probability: float
    average_cascade_probability: float
    
    # Current
    current_state: MicrostructureState
    current_driver: DominantDriver
