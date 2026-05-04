"""
Exchange Conflict Resolver Types
=================================
Phase 14.1 — Unified signal contracts for conflict resolution.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime, timezone


class ExchangeDirection(Enum):
    """Normalized direction for all exchange signals."""
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"
    
    def to_numeric(self) -> float:
        """Convert direction to numeric value for calculations."""
        mapping = {
            ExchangeDirection.LONG: 1.0,
            ExchangeDirection.SHORT: -1.0,
            ExchangeDirection.NEUTRAL: 0.0,
        }
        return mapping[self]


class DominantSignalType(Enum):
    """Types of dominant signals."""
    LIQUIDATIONS = "liquidations"
    DERIVATIVES = "derivatives"
    FLOW = "flow"
    FUNDING = "funding"
    VOLUME = "volume"
    NONE = "none"


@dataclass
class ExchangeSignal:
    """
    Unified signal contract from any exchange engine.
    All engines must normalize their output to this format.
    """
    engine: str
    direction: ExchangeDirection
    strength: float  # 0..1, absolute strength of signal
    confidence: float  # 0..1, data quality confidence
    raw_value: float = 0.0  # Original metric value for debugging
    drivers: list = field(default_factory=list)  # Explanation factors
    
    def weighted_score(self, weight: float) -> float:
        """Calculate weighted contribution to final score."""
        return self.direction.to_numeric() * self.strength * weight * self.confidence


@dataclass
class ExchangeContext:
    """
    Final unified exchange context after conflict resolution.
    This is what Trading Layer consumes.
    """
    symbol: str
    bias: ExchangeDirection
    confidence: float  # 0..1, overall confidence
    conflict_ratio: float  # 0..1, how much signals disagree
    dominant_signal: DominantSignalType
    
    # Individual contributions for explainability
    contributions: Dict[str, float] = field(default_factory=dict)
    
    # Raw signals for debugging
    signals: Dict[str, ExchangeSignal] = field(default_factory=dict)
    
    # Timestamp
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        """Convert to API-friendly dict."""
        return {
            "symbol": self.symbol,
            "bias": self.bias.value,
            "confidence": round(self.confidence, 4),
            "conflict_ratio": round(self.conflict_ratio, 4),
            "dominant_signal": self.dominant_signal.value,
            "contributions": {k: round(v, 4) for k, v in self.contributions.items()},
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ConflictAnalysis:
    """
    Detailed conflict analysis for debugging and monitoring.
    """
    bullish_strength: float
    bearish_strength: float
    total_strength: float
    conflict_ratio: float
    agreement_ratio: float
    
    bullish_engines: list = field(default_factory=list)
    bearish_engines: list = field(default_factory=list)
    neutral_engines: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "bullish_strength": round(self.bullish_strength, 4),
            "bearish_strength": round(self.bearish_strength, 4),
            "total_strength": round(self.total_strength, 4),
            "conflict_ratio": round(self.conflict_ratio, 4),
            "agreement_ratio": round(self.agreement_ratio, 4),
            "bullish_engines": self.bullish_engines,
            "bearish_engines": self.bearish_engines,
            "neutral_engines": self.neutral_engines,
        }
