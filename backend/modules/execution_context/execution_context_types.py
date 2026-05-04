"""
PHASE 25.5 — Execution Context Types

Data models for Execution Context Layer.

Key principle:
This layer modifies ONLY execution parameters (confidence, capital),
NEVER strategy/direction/signal.

Weight model:
- fractal_weight = 0.16 (16%)
- macro_weight = 0.02 (2%)
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# Types
# ══════════════════════════════════════════════════════════════

ContextBiasType = Literal["BULLISH", "BEARISH", "NEUTRAL", "MIXED"]
ContextStateType = Literal["SUPPORTIVE", "NEUTRAL", "CONFLICTED", "BLOCKED"]


# ══════════════════════════════════════════════════════════════
# Main Contract
# ══════════════════════════════════════════════════════════════

class ExecutionContext(BaseModel):
    """
    Execution Context from Macro-Fractal Intelligence.
    
    Key principles:
    - Modifies confidence_modifier and capital_modifier ONLY
    - Does NOT change strategy
    - Does NOT change direction
    - Does NOT change signal
    
    Weight limits:
    - Fractal contribution: max 16%
    - Macro contribution: max 2%
    """
    
    # ─────────────────────────────────────────────────────────
    # Directional Bias (from MacroFractalContext.final_bias)
    # ─────────────────────────────────────────────────────────
    context_bias: ContextBiasType = Field(
        description="Directional bias from macro-fractal layer"
    )
    
    # ─────────────────────────────────────────────────────────
    # Strength Components
    # ─────────────────────────────────────────────────────────
    fractal_strength: float = Field(
        ge=0.0, le=1.0,
        description="Fractal signal strength (from BTC fractal)"
    )
    macro_strength: float = Field(
        ge=0.0, le=1.0,
        description="Macro regime strength"
    )
    cross_asset_strength: float = Field(
        ge=0.0, le=1.0,
        description="Cross-asset alignment strength"
    )
    
    # ─────────────────────────────────────────────────────────
    # Execution Modifiers
    # ─────────────────────────────────────────────────────────
    confidence_modifier: float = Field(
        ge=0.90, le=1.18,
        description="Modifier for signal confidence. Range: [0.90, 1.18]"
    )
    capital_modifier: float = Field(
        ge=0.85, le=1.20,
        description="Modifier for capital allocation. Range: [0.85, 1.20]"
    )
    
    # ─────────────────────────────────────────────────────────
    # Context State
    # ─────────────────────────────────────────────────────────
    context_state: ContextStateType = Field(
        description="Overall context state from macro-fractal analysis"
    )
    
    # ─────────────────────────────────────────────────────────
    # Explainability
    # ─────────────────────────────────────────────────────────
    reason: str = Field(
        description="Human-readable explanation of the execution context"
    )
    
    # ─────────────────────────────────────────────────────────
    # Metadata
    # ─────────────────────────────────────────────────────────
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="25.5.0")


# ══════════════════════════════════════════════════════════════
# Summary Contract
# ══════════════════════════════════════════════════════════════

class ExecutionContextSummary(BaseModel):
    """Compact summary for API responses."""
    context_bias: ContextBiasType
    confidence_modifier: float
    capital_modifier: float
    context_state: ContextStateType


# ══════════════════════════════════════════════════════════════
# Health Status
# ══════════════════════════════════════════════════════════════

class ExecutionContextHealthStatus(BaseModel):
    """Health status for execution context module."""
    status: Literal["OK", "DEGRADED", "ERROR"]
    has_macro_fractal: bool
    has_fractal: bool
    has_cross_asset: bool
    context_state: ContextStateType
    last_update: Optional[datetime]


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Weight limits
FRACTAL_WEIGHT = 0.16
MACRO_WEIGHT = 0.02

# Confidence modifier bounds
CONFIDENCE_MIN = 0.90
CONFIDENCE_MAX = 1.18

# Capital modifier bounds  
CAPITAL_MIN = 0.85
CAPITAL_MAX = 1.20

# Capital modifier component weights
CAPITAL_FRACTAL_WEIGHT = 0.12
CAPITAL_CROSS_ASSET_WEIGHT = 0.05
CAPITAL_MACRO_WEIGHT = 0.02

# Conflict penalty multipliers
CONFLICT_CONFIDENCE_PENALTY = 0.95
CONFLICT_CAPITAL_PENALTY = 0.92
