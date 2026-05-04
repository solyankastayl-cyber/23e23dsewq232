"""
Prediction Types

Core data structures for TA-based prediction.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Literal
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# INPUT TYPES (from TA Engine)
# ══════════════════════════════════════════════════════════════

@dataclass
class PatternInput:
    """Pattern detected by TA Engine."""
    type: str  # triangle, range, channel, wedge, flag, none
    direction: str  # bullish, bearish, neutral
    confidence: float  # 0-1
    breakout_level: Optional[float] = None
    target_price: Optional[float] = None
    bounds_top: Optional[float] = None
    bounds_bottom: Optional[float] = None


@dataclass
class StructureInput:
    """Market structure from TA Engine."""
    state: str  # trend, range, compression, expansion
    trend: str  # up, down, flat
    trend_strength: float = 0.5  # 0-1


@dataclass
class IndicatorsInput:
    """Indicator signals from TA Engine."""
    momentum: float = 0.0  # -1 to 1
    trend_strength: float = 0.5  # 0-1
    volatility: float = 0.3  # 0-1
    rsi: Optional[float] = None  # 0-100
    macd_signal: Optional[str] = None  # bullish, bearish, neutral


@dataclass
class PredictionInput:
    """
    Input contract for Prediction Engine.
    Built from TA Engine output.
    """
    symbol: str
    timeframe: str  # 4H, 1D, 7D, 1M
    price: float
    pattern: PatternInput
    structure: StructureInput
    indicators: IndicatorsInput
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# OUTPUT TYPES
# ══════════════════════════════════════════════════════════════

@dataclass
class PathPoint:
    """Single point on prediction path."""
    t: int  # Day offset (0 = today)
    price: float
    timestamp: Optional[datetime] = None


@dataclass
class Direction:
    """Predicted direction."""
    label: str  # bullish, bearish, neutral
    score: float  # -1 to 1
    reasoning: List[str] = field(default_factory=list)


@dataclass
class Confidence:
    """Prediction confidence."""
    value: float  # 0-1
    label: str  # HIGH, MEDIUM, LOW
    factors: Dict[str, float] = field(default_factory=dict)


@dataclass
class Scenario:
    """Single prediction scenario (bull/base/bear)."""
    name: str  # bull, base, bear
    probability: float  # 0-1
    target_price: float
    expected_return: float  # % move
    path: List[PathPoint] = field(default_factory=list)
    band_low: List[PathPoint] = field(default_factory=list)
    band_high: List[PathPoint] = field(default_factory=list)


@dataclass
class PredictionOutput:
    """
    Full prediction output.
    Contains direction, scenarios, confidence, and paths.
    """
    symbol: str
    timeframe: str
    current_price: float
    
    direction: Direction
    confidence: Confidence
    
    scenarios: Dict[str, Scenario]  # bull, base, bear
    
    horizon_days: int
    
    # Metadata
    version: str = "v2"
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "current_price": self.current_price,
            "direction": {
                "label": self.direction.label,
                "score": round(self.direction.score, 4),
                "reasoning": self.direction.reasoning,
            },
            "confidence": {
                "value": round(self.confidence.value, 4),
                "label": self.confidence.label,
                "factors": {k: round(v, 4) for k, v in self.confidence.factors.items()},
            },
            "scenarios": {
                name: {
                    "name": s.name,
                    "probability": round(s.probability, 4),
                    "target_price": round(s.target_price, 2),
                    "expected_return": round(s.expected_return, 4),
                    "path": [{"t": p.t, "price": round(p.price, 2)} for p in s.path],
                    "band_low": [{"t": p.t, "price": round(p.price, 2)} for p in s.band_low],
                    "band_high": [{"t": p.t, "price": round(p.price, 2)} for p in s.band_high],
                }
                for name, s in self.scenarios.items()
            },
            "horizon_days": self.horizon_days,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
        }


# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════

TIMEFRAME_HORIZONS = {
    "4H": 2,
    "1D": 5,
    "7D": 14,
    "1M": 30,
    "6M": 90,
    "1Y": 180,
}

DIRECTION_THRESHOLDS = {
    "bullish": 0.2,
    "bearish": -0.2,
}

CONFIDENCE_THRESHOLDS = {
    "HIGH": 0.7,
    "MEDIUM": 0.5,
}

# Weights for direction calculation
DIRECTION_WEIGHTS = {
    "pattern": 0.40,
    "structure": 0.30,
    "momentum": 0.30,
}

# Weights for confidence calculation
CONFIDENCE_WEIGHTS = {
    "pattern": 0.40,
    "trend_strength": 0.30,
    "momentum_agreement": 0.30,
}
