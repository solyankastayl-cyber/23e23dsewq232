"""
Liquidation Cascade Probability — Types

PHASE 28.4 — Liquidation Cascade Detection

Key concepts:
- Aggregate liquidation pressure + vacuum + orderbook pressure
- Detect cascade direction (UP/DOWN/NONE)
- Calculate cascade probability with alignment multiplier
- Classify severity and state

Severity levels:
- LOW: probability < 0.25
- MEDIUM: 0.25 <= p < 0.45
- HIGH: 0.45 <= p < 0.70
- EXTREME: p >= 0.70

Cascade states:
- STABLE: LOW severity, no direction
- BUILDING: MEDIUM severity, direction visible
- ACTIVE: HIGH severity, direction aligned
- CRITICAL: EXTREME severity, thin liquidity + strong pressure
"""

from typing import Literal, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

CascadeDirection = Literal["UP", "DOWN", "NONE"]
CascadeSeverity = Literal["LOW", "MEDIUM", "HIGH", "EXTREME"]
CascadeState = Literal["STABLE", "BUILDING", "ACTIVE", "CRITICAL"]


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Cascade probability weights
CASCADE_WEIGHT_LIQUIDATION = 0.40
CASCADE_WEIGHT_VACUUM = 0.30
CASCADE_WEIGHT_SWEEP = 0.20
CASCADE_WEIGHT_DEPTH = 0.10

# Alignment multipliers
ALIGNMENT_FULL = 1.15  # 3/3 aligned
ALIGNMENT_PARTIAL = 1.0  # 2/3 aligned
ALIGNMENT_CONFLICT = 0.75  # signals conflict

# Severity thresholds
SEVERITY_LOW_THRESHOLD = 0.25
SEVERITY_MEDIUM_THRESHOLD = 0.45
SEVERITY_HIGH_THRESHOLD = 0.70

# Confidence weights
CONF_WEIGHT_LIQUIDATION = 0.35
CONF_WEIGHT_VACUUM = 0.25
CONF_WEIGHT_SWEEP = 0.20
CONF_WEIGHT_ALIGNMENT = 0.20


# ══════════════════════════════════════════════════════════════
# Input Context
# ══════════════════════════════════════════════════════════════

class CascadeInputContext(BaseModel):
    """Aggregated context from all microstructure layers."""
    # From MicrostructureSnapshot
    liquidation_pressure: float = 0.0
    funding_pressure: float = 0.0
    oi_pressure: float = 0.0
    depth_score: float = 0.5
    
    # From LiquidityVacuumState
    vacuum_direction: str = "NONE"
    vacuum_probability: float = 0.0
    liquidity_state: str = "NORMAL"
    
    # From OrderbookPressureMap
    pressure_bias: str = "BALANCED"
    sweep_risk: str = "NONE"
    sweep_probability: float = 0.0
    pressure_state: str = "NEUTRAL"


# ══════════════════════════════════════════════════════════════
# Main Contract
# ══════════════════════════════════════════════════════════════

class LiquidationCascadeState(BaseModel):
    """
    Liquidation cascade probability state for a symbol.
    
    Aggregates liquidation pressure, vacuum, and orderbook pressure
    to assess cascade risk.
    """
    symbol: str
    
    # Direction
    cascade_direction: CascadeDirection
    
    # Probability
    cascade_probability: float = Field(ge=0.0, le=1.0)
    
    # Input metrics (for transparency)
    liquidation_pressure: float
    vacuum_probability: float
    sweep_probability: float
    
    # Classifications
    cascade_severity: CascadeSeverity
    cascade_state: CascadeState
    
    # Confidence
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Explanation
    reason: str
    
    # Metadata
    computed_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# History Record
# ══════════════════════════════════════════════════════════════

class LiquidationCascadeHistoryRecord(BaseModel):
    """Historical record of liquidation cascade state."""
    symbol: str
    cascade_direction: CascadeDirection
    cascade_probability: float
    liquidation_pressure: float
    vacuum_probability: float
    sweep_probability: float
    cascade_severity: CascadeSeverity
    cascade_state: CascadeState
    confidence: float
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════

class LiquidationCascadeSummary(BaseModel):
    """Summary of liquidation cascade history."""
    symbol: str
    total_records: int
    
    # Direction counts
    up_count: int
    down_count: int
    none_count: int
    
    # Severity counts
    low_count: int
    medium_count: int
    high_count: int
    extreme_count: int
    
    # State counts
    stable_count: int
    building_count: int
    active_count: int
    critical_count: int
    
    # Averages
    average_cascade_probability: float
    average_liquidation_pressure: float
    average_vacuum_probability: float
    average_sweep_probability: float
    average_confidence: float
    
    # Current
    current_state: CascadeState
    current_direction: CascadeDirection
    current_severity: CascadeSeverity
