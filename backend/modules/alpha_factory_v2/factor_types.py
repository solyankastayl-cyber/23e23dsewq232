"""
PHASE 26 — Factor Types

Core data models for Alpha Factory v2.

Key entities:
- AlphaFactor: Main factor entity with scoring
- FactorCandidate: Raw discovered factor
- FactorStatus: Lifecycle state
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, List, Any
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# Types
# ══════════════════════════════════════════════════════════════

FactorCategory = Literal["TA", "EXCHANGE", "FRACTAL", "REGIME"]
FactorStatus = Literal["CANDIDATE", "ACTIVE", "DEPRECATED"]


# ══════════════════════════════════════════════════════════════
# Factor Candidate (Discovery Output)
# ══════════════════════════════════════════════════════════════

class FactorCandidate(BaseModel):
    """
    Raw factor candidate from discovery engine.
    
    Not yet scored or evaluated.
    """
    factor_id: str = Field(
        description="Unique factor identifier"
    )
    name: str = Field(
        description="Human-readable factor name"
    )
    category: FactorCategory = Field(
        description="Factor source category"
    )
    lookback: int = Field(
        ge=1,
        description="Lookback period in bars/candles"
    )
    
    # Raw signal data
    raw_signal: float = Field(
        ge=-1.0, le=1.0,
        description="Raw signal value [-1, 1]"
    )
    
    # Source metadata
    source: str = Field(
        description="Source module/engine"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Factor parameters"
    )
    
    # Discovery metadata
    discovered_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# Alpha Factor (Full Entity)
# ══════════════════════════════════════════════════════════════

class AlphaFactor(BaseModel):
    """
    Full alpha factor with scoring and status.
    
    Lifecycle:
    CANDIDATE → ACTIVE (if alpha_score >= 0.55)
    CANDIDATE → DEPRECATED (if alpha_score < 0.55)
    ACTIVE → DEPRECATED (if score degrades)
    """
    
    # Identity
    factor_id: str = Field(
        description="Unique factor identifier"
    )
    name: str = Field(
        description="Human-readable factor name"
    )
    category: FactorCategory = Field(
        description="Factor source category"
    )
    lookback: int = Field(
        ge=1,
        description="Lookback period"
    )
    
    # ─────────────────────────────────────────────────────────
    # Scoring Components
    # ─────────────────────────────────────────────────────────
    signal_strength: float = Field(
        ge=0.0, le=1.0,
        description="Signal strength score"
    )
    stability_score: float = Field(
        ge=0.0, le=1.0,
        description="Signal stability over time"
    )
    sharpe_score: float = Field(
        ge=0.0, le=1.0,
        description="Normalized Sharpe ratio score"
    )
    drawdown_score: float = Field(
        ge=0.0, le=1.0,
        description="Drawdown resistance score (1 = no drawdown)"
    )
    
    # ─────────────────────────────────────────────────────────
    # Final Alpha Score
    # ─────────────────────────────────────────────────────────
    alpha_score: float = Field(
        ge=0.0, le=1.0,
        description="Composite alpha score"
    )
    
    # ─────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────
    status: FactorStatus = Field(
        default="CANDIDATE",
        description="Factor lifecycle status"
    )
    
    # ─────────────────────────────────────────────────────────
    # Metadata
    # ─────────────────────────────────────────────────────────
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Factor parameters"
    )
    source: str = Field(
        default="",
        description="Source module"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_evaluated: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="26.1.0")


# ══════════════════════════════════════════════════════════════
# Summary Contract
# ══════════════════════════════════════════════════════════════

class AlphaFactorSummary(BaseModel):
    """Summary of alpha factory state."""
    total_factors: int
    active_factors: int
    candidate_factors: int
    deprecated_factors: int
    strongest_factor: Optional[str]
    average_alpha_score: float
    
    # Category breakdown
    ta_factors: int = 0
    exchange_factors: int = 0
    fractal_factors: int = 0
    regime_factors: int = 0


# ══════════════════════════════════════════════════════════════
# Health Status
# ══════════════════════════════════════════════════════════════

class AlphaFactoryHealth(BaseModel):
    """Health status for alpha factory."""
    status: Literal["OK", "DEGRADED", "ERROR"]
    discovery_active: bool
    scoring_active: bool
    survival_active: bool
    registry_connected: bool
    total_factors: int
    last_discovery: Optional[datetime]


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Alpha score weights
ALPHA_SCORE_WEIGHTS = {
    "signal_strength": 0.35,
    "sharpe_score": 0.25,
    "stability_score": 0.20,
    "drawdown_score": 0.20,
}

# Survival threshold
SURVIVAL_THRESHOLD = 0.55

# Factor categories
FACTOR_CATEGORIES = ["TA", "EXCHANGE", "FRACTAL", "REGIME"]

# Default lookbacks per category
DEFAULT_LOOKBACKS = {
    "TA": [7, 14, 30, 60],
    "EXCHANGE": [5, 15, 30],
    "FRACTAL": [14, 30, 60],
    "REGIME": [30, 60, 90],
}
