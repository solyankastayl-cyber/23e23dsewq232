"""
PHASE 24.1 — Fractal Context Types

Core data models for Fractal Intelligence integration.
These types define the contract between fractal module and the rest of the system.
"""

from pydantic import BaseModel, Field
from typing import Dict, Optional, Literal
from datetime import datetime


class HorizonBias(BaseModel):
    """Bias data for a single horizon."""
    expected_return: float = Field(default=0.0, description="Expected return for this horizon")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score 0..1")
    weight: float = Field(default=0.0, ge=0.0, le=1.0, description="Weight in final decision")
    action: Optional[str] = Field(default=None, description="BUY/SELL/HOLD for this horizon")


class FractalContext(BaseModel):
    """
    Main contract for Fractal Intelligence signal.
    
    This is the only interface through which the core system
    interacts with fractal intelligence.
    """
    
    # Core signal
    direction: Literal["LONG", "SHORT", "HOLD"] = Field(
        description="Primary directional signal"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Signal confidence 0..1"
    )
    reliability: float = Field(
        ge=0.0, le=1.0,
        description="Signal reliability based on drift/calibration/rolling metrics"
    )
    
    # Horizon analysis
    dominant_horizon: Optional[int] = Field(
        default=None,
        description="Horizon with strongest signal (7/14/30/60)"
    )
    horizon_bias: Dict[str, HorizonBias] = Field(
        default_factory=dict,
        description="Per-horizon breakdown {'7': {...}, '14': {...}, '30': {...}}"
    )
    
    # Expected outcome
    expected_return: Optional[float] = Field(
        default=None,
        description="Expected return from dominant horizon"
    )
    
    # Market phase
    phase: Optional[str] = Field(
        default=None,
        description="Market phase: MARKUP/MARKDOWN/ACCUMULATION/DISTRIBUTION/RECOVERY/CAPITULATION"
    )
    phase_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Confidence in phase classification"
    )
    
    # Risk & governance
    risk_badge: Optional[str] = Field(
        default=None,
        description="Risk badge: OK/WARN/DEGRADED/CRITICAL"
    )
    governance_mode: str = Field(
        default="NORMAL",
        description="Governance mode: NORMAL/PROTECTION/FROZEN_ONLY/HALT"
    )
    
    # Computed metrics
    fractal_strength: float = Field(
        ge=0.0, le=1.0,
        description="Combined quality score: 0.45*conf + 0.35*rel + 0.20*phase_conf"
    )
    context_state: Literal["SUPPORTIVE", "NEUTRAL", "CONFLICTED", "BLOCKED"] = Field(
        description="Overall context classification for system integration"
    )
    
    # Explainability
    reason: str = Field(
        description="Human-readable explanation of the signal"
    )
    
    # Metadata
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this context was generated"
    )
    source_version: str = Field(
        default="v2.1.0",
        description="Version of the fractal signal source"
    )


class FractalContextSummary(BaseModel):
    """Compact summary for quick access."""
    direction: Literal["LONG", "SHORT", "HOLD"]
    confidence: float
    reliability: float
    phase: Optional[str]
    dominant_horizon: Optional[int]
    context_state: Literal["SUPPORTIVE", "NEUTRAL", "CONFLICTED", "BLOCKED"]
    fractal_strength: float


class FractalHealthStatus(BaseModel):
    """Health check response for fractal service."""
    connected: bool = Field(description="Whether fractal TS service is reachable")
    governance_mode: str = Field(description="Current governance mode")
    status: Literal["OK", "DEGRADED", "ERROR", "UNAVAILABLE"] = Field(
        description="Overall health status"
    )
    last_signal_ts: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last successful signal fetch"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if status is not OK"
    )
    latency_ms: Optional[int] = Field(
        default=None,
        description="Response latency in milliseconds"
    )


# Raw TS contract types (for internal use in adapter)
class RawFractalDecision(BaseModel):
    """Raw decision from TS fractal contract."""
    action: str
    confidence: float = 0.0
    reliability: float = 0.0
    sizeMultiplier: Optional[float] = None


class RawFractalHorizon(BaseModel):
    """Raw horizon from TS fractal contract."""
    h: int
    action: Optional[str] = None
    expectedReturn: float = 0.0
    confidence: float = 0.0
    weight: float = 0.0
    dominant: Optional[bool] = None


class RawFractalRisk(BaseModel):
    """Raw risk from TS fractal contract."""
    maxDD_WF: Optional[float] = None
    mcP95_DD: Optional[float] = None
    entropy: Optional[float] = None
    tailBadge: Optional[str] = None


class RawFractalReliability(BaseModel):
    """Raw reliability from TS fractal contract."""
    score: float = 0.0
    badge: Optional[str] = None
    effectiveN: Optional[float] = None
    driftScore: Optional[float] = None


class RawFractalGovernance(BaseModel):
    """Raw governance from TS fractal contract."""
    mode: str = "NORMAL"
    frozenVersionId: Optional[str] = None
    guardLevel: Optional[str] = None


class RawFractalSignal(BaseModel):
    """Complete raw signal from TS fractal endpoint."""
    decision: Optional[RawFractalDecision] = None
    horizons: list = Field(default_factory=list)
    risk: Optional[RawFractalRisk] = None
    reliability: Optional[RawFractalReliability] = None
    governance: Optional[RawFractalGovernance] = None
    market: Optional[dict] = None
    explain: Optional[dict] = None


class RawPhaseResponse(BaseModel):
    """Raw phase response from TS fractal phase endpoint."""
    ok: bool = False
    phase: Optional[str] = None
    confidence: Optional[float] = None
    phaseDetails: Optional[dict] = None
