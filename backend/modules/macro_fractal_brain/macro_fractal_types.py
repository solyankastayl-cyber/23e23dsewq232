"""
PHASE 25.4 — Macro-Fractal Brain Types

Unified MacroFractalContext that combines:
- MacroContext (macro regime)
- AssetFractalContext (BTC, SPX, DXY fractals)
- CrossAssetAlignment (causal chain)

This is the final intelligence layer for macro-fractal analysis.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# Types
# ══════════════════════════════════════════════════════════════

FinalBiasType = Literal["BULLISH", "BEARISH", "MIXED", "NEUTRAL"]
ContextStateType = Literal["SUPPORTIVE", "MIXED", "CONFLICTED", "BLOCKED"]
DriverType = Literal["MACRO", "DXY", "SPX", "BTC", "CROSS_ASSET", "MIXED"]


# ══════════════════════════════════════════════════════════════
# Main Contract
# ══════════════════════════════════════════════════════════════

class MacroFractalContext(BaseModel):
    """
    Unified Macro-Fractal Intelligence Context.
    
    This is the HIGH-LEVEL intelligence layer that answers:
    "What does the entire macro + fractal + cross-asset chain say?"
    
    Principles:
    - Does NOT change direction directly
    - Does NOT replace TA / Exchange
    - Does NOT hard override
    - Only provides: bias, confidence, reliability, context_state, regime hint
    """
    
    # ─────────────────────────────────────────────────────────
    # Macro Layer
    # ─────────────────────────────────────────────────────────
    macro_state: str = Field(
        description="Current macro regime: RISK_ON, RISK_OFF, TIGHTENING, etc."
    )
    
    # ─────────────────────────────────────────────────────────
    # Asset Directions
    # ─────────────────────────────────────────────────────────
    btc_direction: str = Field(
        description="BTC fractal direction: LONG, SHORT, HOLD"
    )
    spx_direction: str = Field(
        description="SPX fractal direction: LONG, SHORT, HOLD"
    )
    dxy_direction: str = Field(
        description="DXY fractal direction: LONG, SHORT, HOLD"
    )
    
    # ─────────────────────────────────────────────────────────
    # Asset Phases
    # ─────────────────────────────────────────────────────────
    btc_phase: Optional[str] = Field(
        default=None,
        description="BTC market phase"
    )
    spx_phase: Optional[str] = Field(
        default=None,
        description="SPX market phase"
    )
    dxy_phase: Optional[str] = Field(
        default=None,
        description="DXY market phase"
    )
    
    # ─────────────────────────────────────────────────────────
    # Cross-Asset Alignments
    # ─────────────────────────────────────────────────────────
    macro_dxy_alignment: str = Field(
        description="Macro → DXY alignment: SUPPORTIVE, CONTRARY, etc."
    )
    dxy_spx_alignment: str = Field(
        description="DXY → SPX alignment"
    )
    spx_btc_alignment: str = Field(
        description="SPX → BTC alignment"
    )
    
    cross_asset_strength: float = Field(
        ge=0.0, le=1.0,
        description="Aggregate cross-asset alignment score"
    )
    
    # ─────────────────────────────────────────────────────────
    # Final Assessment
    # ─────────────────────────────────────────────────────────
    final_bias: FinalBiasType = Field(
        description="Final directional bias for the system"
    )
    final_confidence: float = Field(
        ge=0.0, le=1.0,
        description="Aggregate confidence across all layers"
    )
    final_reliability: float = Field(
        ge=0.0, le=1.0,
        description="Aggregate reliability across all layers"
    )
    
    # ─────────────────────────────────────────────────────────
    # Context State
    # ─────────────────────────────────────────────────────────
    context_state: ContextStateType = Field(
        description="Overall context classification"
    )
    
    # ─────────────────────────────────────────────────────────
    # Driver Analysis
    # ─────────────────────────────────────────────────────────
    dominant_driver: DriverType = Field(
        description="Strongest signal source"
    )
    weakest_driver: DriverType = Field(
        description="Weakest signal source"
    )
    
    # ─────────────────────────────────────────────────────────
    # Explainability
    # ─────────────────────────────────────────────────────────
    reason: str = Field(
        description="Human-readable explanation"
    )
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="25.4.0")


# ══════════════════════════════════════════════════════════════
# Summary Contract
# ══════════════════════════════════════════════════════════════

class MacroFractalSummary(BaseModel):
    """Compact summary for quick access."""
    final_bias: FinalBiasType
    final_confidence: float
    final_reliability: float
    context_state: ContextStateType
    macro_state: str
    cross_asset_strength: float


# ══════════════════════════════════════════════════════════════
# Drivers Response
# ══════════════════════════════════════════════════════════════

class MacroFractalDrivers(BaseModel):
    """Driver strength analysis."""
    drivers: Dict[str, float] = Field(
        description="Strength of each driver: MACRO, BTC, SPX, DXY, CROSS_ASSET"
    )
    dominant_driver: DriverType
    weakest_driver: DriverType


# ══════════════════════════════════════════════════════════════
# Health Status
# ══════════════════════════════════════════════════════════════

class MacroFractalHealthStatus(BaseModel):
    """Health status for macro-fractal brain."""
    status: Literal["OK", "DEGRADED", "ERROR"]
    has_macro: bool
    has_btc: bool
    has_spx: bool
    has_dxy: bool
    has_cross_asset: bool
    context_state: ContextStateType
    last_update: Optional[datetime]


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Weights for final_confidence
CONFIDENCE_WEIGHTS = {
    "macro": 0.25,
    "btc": 0.20,
    "spx": 0.15,
    "dxy": 0.10,
    "cross_asset": 0.30,
}

# Weights for final_reliability
RELIABILITY_WEIGHTS = {
    "macro": 0.30,
    "btc": 0.20,
    "spx": 0.15,
    "dxy": 0.10,
    "cross_asset": 0.25,
}

# Thresholds for context state
SUPPORTIVE_CONFIDENCE_THRESHOLD = 0.60
SUPPORTIVE_RELIABILITY_THRESHOLD = 0.60
CONFLICTED_RELIABILITY_THRESHOLD = 0.45
BLOCKED_ALIGNMENT_THRESHOLD = 0.20
