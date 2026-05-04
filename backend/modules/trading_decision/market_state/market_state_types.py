"""
PHASE 14.3 — Market State Matrix Types
=======================================
Multi-dimensional market state contracts.

The system transitions from:
    single regime → multi-dimensional market state

This provides Decision Layer with comprehensive context:
- trend state
- volatility state
- exchange state
- derivatives state
- breadth state
- risk state
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# STATE ENUMS
# ══════════════════════════════════════════════════════════════

class TrendState(str, Enum):
    """Market trend state."""
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    MIXED = "MIXED"


class VolatilityState(str, Enum):
    """Market volatility state."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXPANDING = "EXPANDING"


class ExchangeState(str, Enum):
    """Exchange intelligence state."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    CONFLICTED = "CONFLICTED"
    NEUTRAL = "NEUTRAL"


class DerivativesState(str, Enum):
    """Derivatives market state."""
    CROWDED_LONG = "CROWDED_LONG"
    CROWDED_SHORT = "CROWDED_SHORT"
    BALANCED = "BALANCED"
    SQUEEZE = "SQUEEZE"


class BreadthState(str, Enum):
    """Market breadth / dominance state."""
    BTC_DOM = "BTC_DOM"
    ALT_DOM = "ALT_DOM"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class RiskState(str, Enum):
    """Risk sentiment state."""
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    NEUTRAL = "NEUTRAL"


class CombinedState(str, Enum):
    """Pre-defined combined market states (10-20 useful states)."""
    # Trending states
    TRENDING_HIGH_VOL_BTC_DOM = "TRENDING_HIGH_VOL_BTC_DOM"
    TRENDING_LOW_VOL_BULLISH = "TRENDING_LOW_VOL_BULLISH"
    TRENDING_EXPANSION_RISK_ON = "TRENDING_EXPANSION_RISK_ON"
    
    # Bearish states
    BEARISH_EXPANSION_RISK_OFF = "BEARISH_EXPANSION_RISK_OFF"
    BEARISH_HIGH_VOL_SQUEEZE = "BEARISH_HIGH_VOL_SQUEEZE"
    BEARISH_CAPITULATION = "BEARISH_CAPITULATION"
    
    # Range / Chop states
    CHOP_CONFLICTED = "CHOP_CONFLICTED"
    RANGE_LOW_VOL_NEUTRAL = "RANGE_LOW_VOL_NEUTRAL"
    RANGE_ACCUMULATION = "RANGE_ACCUMULATION"
    
    # Squeeze states
    SQUEEZE_SETUP_LONG = "SQUEEZE_SETUP_LONG"
    SQUEEZE_SETUP_SHORT = "SQUEEZE_SETUP_SHORT"
    
    # Transition states
    BREAKOUT_CONFIRMED = "BREAKOUT_CONFIRMED"
    BREAKDOWN_CONFIRMED = "BREAKDOWN_CONFIRMED"
    REVERSAL_POTENTIAL = "REVERSAL_POTENTIAL"
    
    # Extreme states
    EUPHORIA = "EUPHORIA"
    PANIC = "PANIC"
    
    # Default
    UNDEFINED = "UNDEFINED"


# ══════════════════════════════════════════════════════════════
# MARKET STATE MATRIX CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class MarketStateMatrix:
    """
    Multi-dimensional market state matrix.
    
    This is the main output consumed by Trading Decision Layer.
    Combines TA Hypothesis + Exchange Context into unified state.
    """
    symbol: str
    timestamp: datetime
    
    # Individual state dimensions
    trend_state: TrendState
    volatility_state: VolatilityState
    exchange_state: ExchangeState
    derivatives_state: DerivativesState
    breadth_state: BreadthState
    risk_state: RiskState
    
    # Combined state label
    combined_state: CombinedState
    
    # Confidence (0..1)
    confidence: float
    
    # Explainability drivers
    drivers: Dict[str, str] = field(default_factory=dict)
    
    # Raw scores for debugging
    raw_scores: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "trend_state": self.trend_state.value,
            "volatility_state": self.volatility_state.value,
            "exchange_state": self.exchange_state.value,
            "derivatives_state": self.derivatives_state.value,
            "breadth_state": self.breadth_state.value,
            "risk_state": self.risk_state.value,
            "combined_state": self.combined_state.value,
            "confidence": round(self.confidence, 4),
            "drivers": self.drivers,
        }
    
    def to_full_dict(self) -> Dict:
        """Include raw scores for debugging."""
        result = self.to_dict()
        result["raw_scores"] = {k: round(v, 4) for k, v in self.raw_scores.items()}
        return result


# ══════════════════════════════════════════════════════════════
# INPUT CONTRACTS (what we read from TA and Exchange)
# ══════════════════════════════════════════════════════════════

@dataclass
class TAInputSnapshot:
    """Snapshot of TA Hypothesis inputs for Market State."""
    direction: str  # LONG / SHORT / NEUTRAL
    regime: str  # TREND_UP / TREND_DOWN / RANGE / etc
    setup_quality: float  # 0..1
    trend_strength: float  # 0..1
    conviction: float  # 0..1
    entry_quality: float  # 0..1
    regime_fit: float  # 0..1


@dataclass
class ExchangeInputSnapshot:
    """Snapshot of Exchange Context inputs for Market State."""
    bias: str  # BULLISH / BEARISH / NEUTRAL
    dominant_signal: str  # funding / flow / derivatives / etc
    confidence: float  # 0..1
    conflict_ratio: float  # 0..1, high = conflicting signals
    crowding_risk: float  # 0..1
    squeeze_probability: float  # 0..1
    cascade_probability: float  # 0..1
    derivatives_pressure: float  # -1 to 1
    flow_pressure: float  # -1 to 1


@dataclass
class VolatilityInputSnapshot:
    """Snapshot of volatility context."""
    atr_normalized: float  # ATR / price
    volatility_percentile: float  # 0..1, percentile rank
    volatility_regime: str  # LOW / NORMAL / HIGH / EXPANDING
    recent_range: float  # recent price range %
