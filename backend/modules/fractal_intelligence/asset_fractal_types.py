"""
PHASE 25.2 — Unified Asset Fractal Types

Standard contract for all asset-specific fractal contexts.
BTC, SPX, DXY fractals will all conform to this interface.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, List
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# Asset Types
# ══════════════════════════════════════════════════════════════

AssetType = Literal["BTC", "SPX", "DXY"]

DirectionType = Literal["LONG", "SHORT", "HOLD"]

PhaseType = Literal[
    "MARKUP",
    "MARKDOWN",
    "ACCUMULATION",
    "DISTRIBUTION",
    "RECOVERY",
    "CAPITULATION",
    "UNKNOWN",
]

ContextStateType = Literal[
    "SUPPORTIVE",
    "NEUTRAL",
    "CONFLICTED",
    "BLOCKED",
]


# ══════════════════════════════════════════════════════════════
# Unified Asset Fractal Context
# ══════════════════════════════════════════════════════════════

class AssetFractalContext(BaseModel):
    """
    Unified contract for asset-specific fractal intelligence.
    
    All three assets (BTC, SPX, DXY) conform to this interface.
    This enables the Cross-Asset Bridge Engine to work uniformly.
    """
    
    # Asset identifier
    asset: AssetType = Field(
        description="Asset symbol: BTC, SPX, or DXY"
    )
    
    # Core signal
    direction: DirectionType = Field(
        description="Directional signal: LONG, SHORT, HOLD"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Signal confidence 0..1"
    )
    reliability: float = Field(
        ge=0.0, le=1.0,
        description="Signal reliability based on fractal match quality"
    )
    
    # Horizon analysis
    dominant_horizon: Optional[int] = Field(
        default=None,
        description="Dominant horizon in days (7, 14, 30, 60)"
    )
    expected_return: Optional[float] = Field(
        default=None,
        description="Expected return from dominant horizon"
    )
    
    # Market phase
    phase: Optional[PhaseType] = Field(
        default=None,
        description="Market phase classification"
    )
    phase_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Confidence in phase classification"
    )
    
    # Computed strength
    strength: float = Field(
        ge=0.0, le=1.0,
        description="Combined signal strength"
    )
    
    # Context state
    context_state: ContextStateType = Field(
        description="Overall context classification for system integration"
    )
    
    # Explainability
    reason: str = Field(
        description="Human-readable explanation"
    )
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_version: str = Field(default="25.2.0")


# ══════════════════════════════════════════════════════════════
# Multi-Asset Response
# ══════════════════════════════════════════════════════════════

class MultiAssetFractalContext(BaseModel):
    """Container for all three asset fractal contexts."""
    btc: AssetFractalContext
    spx: AssetFractalContext
    dxy: AssetFractalContext
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# Health Status
# ══════════════════════════════════════════════════════════════

class AssetFractalHealthStatus(BaseModel):
    """Health status for asset fractal module."""
    status: Literal["OK", "DEGRADED", "ERROR"]
    btc_available: bool
    spx_available: bool
    dxy_available: bool
    last_update: Optional[datetime]
