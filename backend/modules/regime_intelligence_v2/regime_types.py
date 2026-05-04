"""
Regime Intelligence v2 — Types

Contracts for market regime detection.

Regime Types:
- TRENDING: Strong directional movement
- RANGING: Sideways consolidation
- VOLATILE: High volatility environment
- ILLIQUID: Low liquidity conditions
"""

from typing import Literal, Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

RegimeType = Literal["TRENDING", "RANGING", "VOLATILE", "ILLIQUID"]
ContextState = Literal["SUPPORTIVE", "NEUTRAL", "CONFLICTED"]
DominantDriver = Literal["TREND", "VOLATILITY", "LIQUIDITY", "FRACTAL"]


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Trend thresholds
TREND_STRONG_THRESHOLD = 0.03
TREND_WEAK_THRESHOLD = 0.02

# Volatility thresholds
VOLATILITY_LOW_THRESHOLD = 0.04
VOLATILITY_MEDIUM_THRESHOLD = 0.05
VOLATILITY_HIGH_THRESHOLD = 0.06

# Liquidity thresholds
LIQUIDITY_LOW_THRESHOLD = 0.30

# Confidence weights
CONFIDENCE_WEIGHT_TREND = 0.4
CONFIDENCE_WEIGHT_VOLATILITY = 0.3
CONFIDENCE_WEIGHT_LIQUIDITY = 0.3


# ══════════════════════════════════════════════════════════════
# Main Contract
# ══════════════════════════════════════════════════════════════

class MarketRegime(BaseModel):
    """
    Current market regime state.
    
    Determines execution and strategy allocation.
    """
    # Classification
    regime_type: RegimeType
    
    # Core metrics (0.0 - 1.0 normalized)
    trend_strength: float = Field(ge=0.0, le=1.0)
    volatility_level: float = Field(ge=0.0, le=1.0)
    liquidity_level: float = Field(ge=0.0, le=1.0)
    
    # Confidence
    regime_confidence: float = Field(ge=0.0, le=1.0)
    
    # Attribution
    dominant_driver: DominantDriver
    
    # Context
    context_state: ContextState
    
    # Metadata
    symbol: str = "BTCUSDT"
    timeframe: str = "1H"
    computed_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# History Record
# ══════════════════════════════════════════════════════════════

class RegimeHistoryRecord(BaseModel):
    """Historical record of regime state."""
    regime_type: RegimeType
    confidence: float
    trend_strength: float
    volatility: float
    liquidity: float
    dominant_driver: DominantDriver
    context_state: ContextState
    symbol: str
    timeframe: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# Input Metrics
# ══════════════════════════════════════════════════════════════

class RegimeInputMetrics(BaseModel):
    """Input metrics for regime detection."""
    # Price data
    price: float
    ema_50: float
    ema_200: float
    atr: float
    
    # Liquidity data
    orderbook_depth: float = Field(ge=0.0, le=1.0)
    volume_profile: float = Field(ge=0.0, le=1.0)
    spread_inverse: float = Field(ge=0.0, le=1.0)
    
    # Optional fractal
    fractal_alignment: float = Field(default=0.5, ge=0.0, le=1.0)


# ══════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════

class RegimeSummary(BaseModel):
    """Summary of regime history."""
    total_records: int
    
    trending_count: int
    ranging_count: int
    volatile_count: int
    illiquid_count: int
    
    current_regime: RegimeType
    average_confidence: float
    
    dominant_regime: RegimeType
    regime_stability: float  # How often regime stays same
