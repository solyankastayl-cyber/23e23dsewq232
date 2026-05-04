"""
TA Hypothesis Types
====================
Phase 14.2 — Unified hypothesis contracts for TA signals.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone


class TADirection(Enum):
    """Direction of TA hypothesis."""
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"
    
    def to_numeric(self) -> float:
        mapping = {
            TADirection.LONG: 1.0,
            TADirection.SHORT: -1.0,
            TADirection.NEUTRAL: 0.0,
        }
        return mapping[self]


class MarketRegime(Enum):
    """Market regime classification."""
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    COMPRESSION = "COMPRESSION"
    EXPANSION = "EXPANSION"
    UNKNOWN = "UNKNOWN"


class SetupType(Enum):
    """Type of trading setup detected."""
    BREAKOUT = "BREAKOUT"
    PULLBACK = "PULLBACK"
    REVERSAL = "REVERSAL"
    CONTINUATION = "CONTINUATION"
    RANGE_TRADE = "RANGE_TRADE"
    NO_SETUP = "NO_SETUP"


@dataclass
class TrendSignal:
    """Trend analysis signal."""
    direction: TADirection
    strength: float  # 0..1
    ma_alignment: float  # -1 to 1, positive = bullish
    price_position: float  # -1 to 1, position relative to MAs
    confidence: float
    
    def to_dict(self) -> dict:
        return {
            "direction": self.direction.value,
            "strength": round(self.strength, 4),
            "ma_alignment": round(self.ma_alignment, 4),
            "price_position": round(self.price_position, 4),
            "confidence": round(self.confidence, 4),
        }


@dataclass
class MomentumSignal:
    """Momentum analysis signal."""
    direction: TADirection
    strength: float  # 0..1
    rsi_value: float  # 0-100
    macd_histogram: float
    momentum_divergence: bool
    confidence: float
    
    def to_dict(self) -> dict:
        return {
            "direction": self.direction.value,
            "strength": round(self.strength, 4),
            "rsi_value": round(self.rsi_value, 2),
            "macd_histogram": round(self.macd_histogram, 6),
            "momentum_divergence": self.momentum_divergence,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class StructureSignal:
    """Market structure signal."""
    bias: TADirection
    structure_score: float  # 0..1
    higher_highs: bool
    higher_lows: bool
    recent_bos: bool  # Break of structure
    recent_choch: bool  # Change of character
    confidence: float
    
    def to_dict(self) -> dict:
        return {
            "bias": self.bias.value,
            "structure_score": round(self.structure_score, 4),
            "higher_highs": self.higher_highs,
            "higher_lows": self.higher_lows,
            "recent_bos": self.recent_bos,
            "recent_choch": self.recent_choch,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class BreakoutSignal:
    """Breakout detection signal."""
    detected: bool
    direction: TADirection
    strength: float  # 0..1
    volume_confirmation: bool
    level_quality: float  # 0..1
    confidence: float
    
    def to_dict(self) -> dict:
        return {
            "detected": self.detected,
            "direction": self.direction.value,
            "strength": round(self.strength, 4),
            "volume_confirmation": self.volume_confirmation,
            "level_quality": round(self.level_quality, 4),
            "confidence": round(self.confidence, 4),
        }


@dataclass
class TAHypothesis:
    """
    Unified TA Hypothesis.
    This is what Trading Layer consumes from TA.
    
    CANONICAL CONTRACT — Sprint 1 Consistency Core:
    All price fields are REQUIRED for runtime decision pipeline.
    """
    symbol: str
    
    # Direction and quality
    direction: TADirection
    setup_quality: float  # 0..1
    setup_type: SetupType
    
    # Component scores
    trend_strength: float  # 0..1
    entry_quality: float  # 0..1
    regime_fit: float  # 0..1
    
    # Final conviction
    conviction: float  # 0..1
    
    # Market context
    regime: MarketRegime
    
    # PRICE LEVELS — Sprint 1: canonical decision contract
    # These are computed from real market data (candles + ATR + structure)
    current_price: float = 0.0
    entry_price: float = 0.0
    stop_price: float = 0.0
    target_price: float = 0.0
    timeframe: str = "1h"
    
    # Component signals for explainability
    drivers: Dict[str, float] = field(default_factory=dict)
    
    # Detailed signals
    trend_signal: Optional[TrendSignal] = None
    momentum_signal: Optional[MomentumSignal] = None
    structure_signal: Optional[StructureSignal] = None
    breakout_signal: Optional[BreakoutSignal] = None
    
    # Timestamp
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "direction": self.direction.value,
            "setup_quality": round(self.setup_quality, 4),
            "setup_type": self.setup_type.value,
            "trend_strength": round(self.trend_strength, 4),
            "entry_quality": round(self.entry_quality, 4),
            "regime_fit": round(self.regime_fit, 4),
            "conviction": round(self.conviction, 4),
            "regime": self.regime.value,
            "current_price": round(self.current_price, 2),
            "entry_price": round(self.entry_price, 2),
            "stop_price": round(self.stop_price, 2),
            "target_price": round(self.target_price, 2),
            "timeframe": self.timeframe,
            "drivers": {k: round(v, 4) for k, v in self.drivers.items()},
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> dict:
        """Include detailed signals."""
        result = self.to_dict()
        if self.trend_signal:
            result["trend_detail"] = self.trend_signal.to_dict()
        if self.momentum_signal:
            result["momentum_detail"] = self.momentum_signal.to_dict()
        if self.structure_signal:
            result["structure_detail"] = self.structure_signal.to_dict()
        if self.breakout_signal:
            result["breakout_detail"] = self.breakout_signal.to_dict()
        return result
