"""
PHASE 25.6 — A/B Test Types

Data models for system validation.

Key principle:
- Direction MUST NOT change across A/B/C
- Strategy MUST NOT change across A/B/C
- Confidence/Capital drift must be within bounds
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# Types
# ══════════════════════════════════════════════════════════════

ValidationState = Literal["PASSED", "WARNING", "FAILED"]
SystemType = Literal["A", "B", "C"]
DirectionType = Literal["LONG", "SHORT", "HOLD"]


# ══════════════════════════════════════════════════════════════
# System Configuration
# ══════════════════════════════════════════════════════════════

class SystemConfig(BaseModel):
    """
    Configuration for each system variant.
    
    System A: TA + Exchange (baseline)
    System B: TA + Exchange + Fractal
    System C: TA + Exchange + Fractal + Macro
    """
    system_type: SystemType
    has_ta: bool = True
    has_exchange: bool = True
    has_fractal: bool = False
    has_macro: bool = False
    description: str


# ══════════════════════════════════════════════════════════════
# System Output
# ══════════════════════════════════════════════════════════════

class SystemOutput(BaseModel):
    """Output from a single system configuration."""
    system_type: SystemType
    direction: DirectionType
    strategy: str
    confidence: float = Field(ge=0.0, le=1.0)
    capital_modifier: float = Field(ge=0.5, le=2.0)
    context_state: str


# ══════════════════════════════════════════════════════════════
# Main Comparison Contract
# ══════════════════════════════════════════════════════════════

class SystemComparison(BaseModel):
    """
    A/B/C System Comparison Result.
    
    Validates that Macro-Fractal layer does NOT break core signals.
    
    Key assertions:
    - direction_consistency: A == B == C (MUST BE TRUE)
    - strategy_consistency: A == B == C (MUST BE TRUE)
    - confidence_drift: |C - A| <= 0.15
    - capital_drift: |C - A| <= 0.20
    """
    
    # ─────────────────────────────────────────────────────────
    # Direction (MUST NOT CHANGE)
    # ─────────────────────────────────────────────────────────
    system_a_direction: DirectionType
    system_b_direction: DirectionType
    system_c_direction: DirectionType
    
    # ─────────────────────────────────────────────────────────
    # Strategy (MUST NOT CHANGE)
    # ─────────────────────────────────────────────────────────
    system_a_strategy: str
    system_b_strategy: str
    system_c_strategy: str
    
    # ─────────────────────────────────────────────────────────
    # Confidence Values
    # ─────────────────────────────────────────────────────────
    system_a_confidence: float = Field(ge=0.0, le=1.0)
    system_b_confidence: float = Field(ge=0.0, le=1.0)
    system_c_confidence: float = Field(ge=0.0, le=1.0)
    
    # ─────────────────────────────────────────────────────────
    # Capital Modifiers
    # ─────────────────────────────────────────────────────────
    system_a_capital: float
    system_b_capital: float
    system_c_capital: float
    
    # ─────────────────────────────────────────────────────────
    # Drift Metrics
    # ─────────────────────────────────────────────────────────
    confidence_drift: float = Field(
        ge=0.0,
        description="|confidence_C - confidence_A|"
    )
    capital_drift: float = Field(
        ge=0.0,
        description="|capital_C - capital_A|"
    )
    
    # ─────────────────────────────────────────────────────────
    # Consistency Checks
    # ─────────────────────────────────────────────────────────
    direction_consistency: bool = Field(
        description="direction_A == direction_B == direction_C"
    )
    strategy_consistency: bool = Field(
        description="strategy_A == strategy_B == strategy_C"
    )
    
    # ─────────────────────────────────────────────────────────
    # Validation Result
    # ─────────────────────────────────────────────────────────
    validation_state: ValidationState = Field(
        description="PASSED | WARNING | FAILED"
    )
    reason: str = Field(
        description="Human-readable explanation"
    )
    
    # ─────────────────────────────────────────────────────────
    # Metadata
    # ─────────────────────────────────────────────────────────
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="25.6.0")


# ══════════════════════════════════════════════════════════════
# Summary Contract
# ══════════════════════════════════════════════════════════════

class SystemComparisonSummary(BaseModel):
    """Compact summary for API responses."""
    system_a_confidence: float
    system_b_confidence: float
    system_c_confidence: float
    system_a_capital: float
    system_b_capital: float
    system_c_capital: float
    confidence_drift: float
    capital_drift: float
    direction_consistency: bool
    strategy_consistency: bool
    validation_state: ValidationState
    reason: str


# ══════════════════════════════════════════════════════════════
# Health Status
# ══════════════════════════════════════════════════════════════

class SystemValidationHealth(BaseModel):
    """Health status for system validation module."""
    status: Literal["OK", "DEGRADED", "ERROR"]
    system_a_available: bool
    system_b_available: bool
    system_c_available: bool
    last_validation: Optional[ValidationState]
    last_update: Optional[datetime]


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Drift thresholds
CONFIDENCE_DRIFT_THRESHOLD = 0.15
CAPITAL_DRIFT_THRESHOLD = 0.20

# System configurations
SYSTEM_A_CONFIG = SystemConfig(
    system_type="A",
    has_ta=True,
    has_exchange=True,
    has_fractal=False,
    has_macro=False,
    description="TA + Exchange (baseline)"
)

SYSTEM_B_CONFIG = SystemConfig(
    system_type="B",
    has_ta=True,
    has_exchange=True,
    has_fractal=True,
    has_macro=False,
    description="TA + Exchange + Fractal"
)

SYSTEM_C_CONFIG = SystemConfig(
    system_type="C",
    has_ta=True,
    has_exchange=True,
    has_fractal=True,
    has_macro=True,
    description="TA + Exchange + Fractal + Macro (full)"
)
