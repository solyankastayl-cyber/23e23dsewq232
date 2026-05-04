"""
Typed contracts for ta_prediction_intelligence.
Canonical input contract is `TAPredictionSetup` (architect-blessed).
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PredictionBias(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class PredictionHorizon(str, Enum):
    H1 = "h1"
    H3 = "h3"
    H6 = "h6"


class TAEngineName(str, Enum):
    STRUCTURE = "structure"
    PATTERN = "pattern"
    MOMENTUM = "momentum"
    LEVEL_ZONE = "level_zone"
    VOLATILITY = "volatility"


# ──────────────────────────────────────────────────────────────────────
# CANONICAL INPUT CONTRACT (architect spec)
# Single, flat, typed structure - the only entry point external callers
# should rely on for the typed API. Internally the service adapts this into
# the dict shape existing engines understand.
# Engines treat missing data honestly: no data -> confidence = 0.
# ──────────────────────────────────────────────────────────────────────


@dataclass
class TAPredictionSetup:
    symbol: str
    timeframe: str
    price: float

    # Top-level TA signal (already produced upstream).
    direction: str = "neutral"           # bullish | bearish | neutral
    confidence: float = 0.0              # 0..1
    strength: float = 0.0                # 0..1

    # Structure
    trend_strength: float = 0.0          # -1..1
    structure_state: str = "range"       # trend | range | breakout | compression | ...

    # Momentum
    rsi: Optional[float] = None
    macd_hist: Optional[float] = None

    # Levels
    support: Optional[float] = None
    resistance: Optional[float] = None

    # Volatility
    atr_pct: Optional[float] = None
    volatility_state: str = "normal"     # low | normal | high

    # Patterns: list of {type|name, direction, confidence, lifecycle?}
    patterns: List[Dict[str, Any]] = field(default_factory=list)

    # Optional explicit volatility flags (override of state mapping)
    compression: bool = False
    expansion: bool = False


# ──────────────────────────────────────────────────────────────────────
# OUTPUT CONTRACTS
# ──────────────────────────────────────────────────────────────────────


@dataclass
class EngineContribution:
    engine: str
    bias: PredictionBias
    score: float
    confidence: float
    expected_move_pct: float
    horizon: str
    quality: float = 0.0          # NEW (production contract): cleanness of the underlying signal,
                                  # independent of direction. 0..1.
    drivers: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["bias"] = self.bias.value if isinstance(self.bias, PredictionBias) else self.bias
        return d


@dataclass
class PredictionScenario:
    name: str
    bias: PredictionBias
    probability: float
    target_price: Optional[float]
    invalidation_price: Optional[float]
    expected_move_pct: float
    drivers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["bias"] = self.bias.value if isinstance(self.bias, PredictionBias) else self.bias
        return d


@dataclass
class TAPredictionContext:
    symbol: str
    timeframe: str
    bias: PredictionBias
    confidence: float
    expected_move_pct: float
    conflict_ratio: float
    dominant_engine: Optional[str]
    contributions: List[EngineContribution]
    scenarios: List[PredictionScenario]
    drivers: List[str]
    risks: List[str]
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "bias": self.bias.value if isinstance(self.bias, PredictionBias) else self.bias,
            "confidence": self.confidence,
            "expected_move_pct": self.expected_move_pct,
            "conflict_ratio": self.conflict_ratio,
            "dominant_engine": self.dominant_engine,
            "contributions": [c.to_dict() for c in self.contributions],
            "scenarios": [s.to_dict() for s in self.scenarios],
            "drivers": self.drivers,
            "risks": self.risks,
            "meta": self.meta,
        }
