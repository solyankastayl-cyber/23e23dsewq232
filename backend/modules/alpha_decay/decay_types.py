"""
Alpha Decay Types

PHASE 43.8 — Alpha Decay Engine

Types for signal aging and decay management.

Problem solved:
- Trading stale signals
- Increased churn
- Catching noise

Decay formula:
    decay_factor = exp(-age_minutes / half_life)

Decay stages:
    FRESH: 0.75 - 1.00
    ACTIVE: 0.50 - 0.75
    WEAKENING: 0.25 - 0.50
    EXPIRED: < 0.25
"""

from typing import Optional, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum
import math


class DecayStage(str, Enum):
    """Signal decay stage."""
    FRESH = "FRESH"           # 0.75 - 1.00
    ACTIVE = "ACTIVE"         # 0.50 - 0.75
    WEAKENING = "WEAKENING"   # 0.25 - 0.50
    EXPIRED = "EXPIRED"       # < 0.25


class SignalType(str, Enum):
    """Signal types with different half-lives."""
    TREND = "TREND"               # half_life = 120 min
    BREAKOUT = "BREAKOUT"         # half_life = 90 min
    MEAN_REVERSION = "MEAN_REVERSION"  # half_life = 30 min
    FRACTAL = "FRACTAL"           # half_life = 180 min
    CAPITAL_FLOW = "CAPITAL_FLOW" # half_life = 240 min
    REGIME = "REGIME"             # half_life = 360 min
    DEFAULT = "DEFAULT"           # half_life = 60 min


# Dynamic half-lives per signal type (minutes)
SIGNAL_HALF_LIVES: Dict[SignalType, int] = {
    SignalType.TREND: 120,
    SignalType.BREAKOUT: 90,
    SignalType.MEAN_REVERSION: 30,
    SignalType.FRACTAL: 180,
    SignalType.CAPITAL_FLOW: 240,
    SignalType.REGIME: 360,
    SignalType.DEFAULT: 60,
}

# Decay stage thresholds
DECAY_STAGE_THRESHOLDS = {
    "FRESH_MIN": 0.75,
    "ACTIVE_MIN": 0.50,
    "WEAKENING_MIN": 0.25,
    "EXPIRED_THRESHOLD": 0.25,
}


class AlphaDecayState(BaseModel):
    """
    Alpha signal decay state.
    
    PHASE 43.8 Core Contract.
    
    Tracks signal aging and adjusts confidence accordingly.
    """
    decay_id: str = Field(default_factory=lambda: f"decay_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    # Signal identification
    hypothesis_id: str
    symbol: str
    signal_type: SignalType = SignalType.DEFAULT
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Age tracking
    age_minutes: int = 0
    half_life_minutes: int = 60  # Dynamic per signal type
    
    # Decay values
    initial_confidence: float
    decay_factor: float = 1.0
    adjusted_confidence: float = 0.0
    
    # Stage
    decay_stage: DecayStage = DecayStage.FRESH
    
    # Expiration
    expires_at: Optional[datetime] = None
    is_expired: bool = False
    execution_blocked: bool = False
    
    # Additional context
    source: str = "hypothesis_engine"
    metadata: Dict = Field(default_factory=dict)
    
    def compute_decay(self) -> "AlphaDecayState":
        """Compute decay factor and update state."""
        now = datetime.now(timezone.utc)
        
        # Calculate age in minutes
        age_delta = now - self.created_at
        self.age_minutes = int(age_delta.total_seconds() / 60)
        
        # Decay formula: exp(-age / half_life)
        self.decay_factor = math.exp(-self.age_minutes / self.half_life_minutes)
        
        # Adjusted confidence
        self.adjusted_confidence = self.initial_confidence * self.decay_factor
        
        # Determine stage
        self.decay_stage = self._determine_stage()
        
        # Check expiration
        if self.decay_factor < DECAY_STAGE_THRESHOLDS["EXPIRED_THRESHOLD"]:
            self.is_expired = True
            self.execution_blocked = True
        
        self.updated_at = now
        
        return self
    
    def _determine_stage(self) -> DecayStage:
        """Determine decay stage from decay factor."""
        if self.decay_factor >= DECAY_STAGE_THRESHOLDS["FRESH_MIN"]:
            return DecayStage.FRESH
        elif self.decay_factor >= DECAY_STAGE_THRESHOLDS["ACTIVE_MIN"]:
            return DecayStage.ACTIVE
        elif self.decay_factor >= DECAY_STAGE_THRESHOLDS["WEAKENING_MIN"]:
            return DecayStage.WEAKENING
        else:
            return DecayStage.EXPIRED


class AlphaDecayConfig(BaseModel):
    """Alpha Decay Engine configuration."""
    # Default half-life
    default_half_life_minutes: int = 60
    
    # Dynamic half-lives enabled
    use_dynamic_half_life: bool = True
    
    # Expiration threshold
    expiration_threshold: float = 0.25
    
    # Stage thresholds
    fresh_threshold: float = 0.75
    active_threshold: float = 0.50
    weakening_threshold: float = 0.25
    
    # Scheduler
    recompute_interval_minutes: int = 5
    
    # Auto-expire
    auto_expire_enabled: bool = True
    max_age_hours: int = 24  # Max age before forced expiration


class DecayComputeResult(BaseModel):
    """Result of decay computation."""
    hypothesis_id: str
    symbol: str
    age_minutes: int
    decay_factor: float
    adjusted_confidence: float
    decay_stage: str
    is_expired: bool
    execution_blocked: bool
    half_life_used: int
    message: str = ""


class DecaySummary(BaseModel):
    """Summary of all decay states."""
    total_signals: int = 0
    fresh_count: int = 0
    active_count: int = 0
    weakening_count: int = 0
    expired_count: int = 0
    blocked_count: int = 0
    avg_decay_factor: float = 0.0
    avg_age_minutes: float = 0.0
    signals: List[DecayComputeResult] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
