"""
Setup Types
============
Core data structures for Setup Graph Architecture.

Setup = unified market analysis object that combines:
- Patterns
- Indicators
- Structure
- Levels
- Confluence

This is what gets:
- Displayed on chart
- Explained by AI
- Saved as Idea
- Validated by system
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


class SetupType(Enum):
    """Types of trading setups."""
    # Breakout setups
    ASCENDING_TRIANGLE_BREAKOUT = "ascending_triangle_breakout"
    DESCENDING_TRIANGLE_BREAKOUT = "descending_triangle_breakout"
    SYMMETRICAL_TRIANGLE_BREAKOUT = "symmetrical_triangle_breakout"
    CHANNEL_BREAKOUT = "channel_breakout"
    RANGE_BREAKOUT = "range_breakout"
    COMPRESSION_BREAKOUT = "compression_breakout"
    
    # Continuation setups
    TREND_CONTINUATION = "trend_continuation"
    PULLBACK_ENTRY = "pullback_entry"
    FLAG_CONTINUATION = "flag_continuation"
    PENNANT_CONTINUATION = "pennant_continuation"
    
    # Reversal setups
    DOUBLE_TOP_REVERSAL = "double_top_reversal"
    DOUBLE_BOTTOM_REVERSAL = "double_bottom_reversal"
    HEAD_SHOULDERS_REVERSAL = "head_shoulders_reversal"
    LIQUIDITY_SWEEP_REVERSAL = "liquidity_sweep_reversal"
    DIVERGENCE_REVERSAL = "divergence_reversal"
    
    # Range setups
    RANGE_SUPPORT_BOUNCE = "range_support_bounce"
    RANGE_RESISTANCE_REJECTION = "range_resistance_rejection"
    MEAN_REVERSION = "mean_reversion"
    
    # Structure setups
    BOS_CONTINUATION = "bos_continuation"
    CHOCH_REVERSAL = "choch_reversal"
    
    # Other
    NO_SETUP = "no_setup"
    CUSTOM = "custom"


class Direction(Enum):
    """Trade direction."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    
    def to_numeric(self) -> float:
        return {"bullish": 1.0, "bearish": -1.0, "neutral": 0.0}[self.value]


class PatternType(Enum):
    """Chart pattern types."""
    # Triangles
    ASCENDING_TRIANGLE = "ascending_triangle"
    DESCENDING_TRIANGLE = "descending_triangle"
    SYMMETRICAL_TRIANGLE = "symmetrical_triangle"
    
    # Channels
    ASCENDING_CHANNEL = "ascending_channel"
    DESCENDING_CHANNEL = "descending_channel"
    HORIZONTAL_CHANNEL = "horizontal_channel"
    
    # Wedges
    RISING_WEDGE = "rising_wedge"
    FALLING_WEDGE = "falling_wedge"
    
    # Double patterns
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    
    # Head & Shoulders
    HEAD_AND_SHOULDERS = "head_and_shoulders"
    INVERSE_HEAD_AND_SHOULDERS = "inverse_head_and_shoulders"
    
    # Flags & Pennants
    BULL_FLAG = "bull_flag"
    BEAR_FLAG = "bear_flag"
    PENNANT = "pennant"
    
    # Compression
    COMPRESSION = "compression"
    SQUEEZE = "squeeze"
    
    # Other
    CUP_AND_HANDLE = "cup_and_handle"
    ROUNDING_BOTTOM = "rounding_bottom"
    NONE = "none"


class StructureType(Enum):
    """Market structure types."""
    HIGHER_HIGH = "HH"
    HIGHER_LOW = "HL"
    LOWER_HIGH = "LH"
    LOWER_LOW = "LL"
    BREAK_OF_STRUCTURE = "BOS"
    CHANGE_OF_CHARACTER = "CHOCH"
    EQUAL_HIGH = "EQH"
    EQUAL_LOW = "EQL"


class LevelType(Enum):
    """Price level types."""
    SUPPORT = "support"
    RESISTANCE = "resistance"
    FIB_236 = "fib_236"
    FIB_382 = "fib_382"
    FIB_500 = "fib_500"
    FIB_618 = "fib_618"
    FIB_786 = "fib_786"
    LIQUIDITY_HIGH = "liquidity_high"
    LIQUIDITY_LOW = "liquidity_low"
    PIVOT = "pivot"
    POC = "poc"  # Point of Control


@dataclass
class DetectedPattern:
    """A detected chart pattern."""
    pattern_type: PatternType
    direction: Direction
    confidence: float  # 0-1
    start_time: datetime
    end_time: Optional[datetime]
    points: List[Dict[str, float]]  # [{time, price}, ...]
    breakout_level: Optional[float] = None
    target_price: Optional[float] = None
    invalidation: Optional[float] = None
    notes: Optional[str] = None  # Structure validation notes
    
    def to_dict(self) -> dict:
        return {
            "type": self.pattern_type.value,
            "direction": self.direction.value,
            "confidence": round(self.confidence, 4),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "points": self.points,
            "breakout_level": self.breakout_level,
            "target_price": self.target_price,
            "invalidation": self.invalidation,
            "notes": self.notes,
        }


@dataclass
class IndicatorSignal:
    """Signal from a technical indicator."""
    name: str  # e.g., "EMA_20", "RSI", "MACD"
    direction: Direction
    strength: float  # 0-1
    value: float
    signal_type: str  # "bullish_cross", "overbought", "divergence", etc.
    description: str
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "direction": self.direction.value,
            "strength": round(self.strength, 4),
            "value": round(self.value, 6),
            "signal_type": self.signal_type,
            "description": self.description,
        }


@dataclass
class StructurePoint:
    """Market structure point."""
    structure_type: StructureType
    price: float
    time: datetime
    confirmed: bool = True
    
    def to_dict(self) -> dict:
        return {
            "type": self.structure_type.value,
            "price": self.price,
            "time": self.time.isoformat(),
            "confirmed": self.confirmed,
        }


@dataclass
class PriceLevel:
    """A significant price level."""
    level_type: LevelType
    price: float
    strength: float  # 0-1, how strong/tested the level is
    touches: int  # Number of times price touched this level
    last_touch: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "type": self.level_type.value,
            "price": self.price,
            "strength": round(self.strength, 4),
            "touches": self.touches,
            "last_touch": self.last_touch.isoformat() if self.last_touch else None,
        }


@dataclass
class Confluence:
    """Confluence analysis result."""
    score: float  # 0-1
    direction: Direction
    components: List[str]  # What contributes to confluence
    description: str
    
    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 4),
            "direction": self.direction.value,
            "components": self.components,
            "description": self.description,
        }


@dataclass
class ConflictSignal:
    """A signal that conflicts with the main thesis."""
    name: str
    description: str
    severity: str  # "low", "medium", "high"
    impact: float  # -1 to 0
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "impact": round(self.impact, 4),
        }


@dataclass
class Setup:
    """
    The main Setup object.
    
    This is the central data structure that:
    - Gets displayed on chart
    - Gets explained by AI
    - Gets saved as Idea
    - Gets validated by system
    """
    # Identity
    setup_id: str
    asset: str
    timeframe: str
    
    # Setup classification
    setup_type: SetupType
    direction: Direction
    
    # Scores
    confidence: float  # 0-1
    confluence_score: float  # 0-1
    
    # Components
    patterns: List[DetectedPattern] = field(default_factory=list)
    indicators: List[IndicatorSignal] = field(default_factory=list)
    levels: List[PriceLevel] = field(default_factory=list)
    structure: List[StructurePoint] = field(default_factory=list)
    
    # Confluence analysis
    primary_confluence: Optional[Confluence] = None
    secondary_confluence: List[Confluence] = field(default_factory=list)
    conflicts: List[ConflictSignal] = field(default_factory=list)
    
    # Trade parameters
    entry_zone: Optional[Dict[str, float]] = None  # {low, high}
    invalidation: Optional[float] = None
    targets: List[float] = field(default_factory=list)
    
    # Market context
    current_price: float = 0.0
    market_regime: str = "unknown"
    
    # Explanation
    explanation: str = ""
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "setup_id": self.setup_id,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "setup_type": self.setup_type.value,
            "direction": self.direction.value,
            "confidence": round(self.confidence, 4),
            "confluence_score": round(self.confluence_score, 4),
            "patterns": [p.to_dict() for p in self.patterns],
            "indicators": [i.to_dict() for i in self.indicators],
            "levels": [l.to_dict() for l in self.levels],
            "structure": [s.to_dict() for s in self.structure],
            "primary_confluence": self.primary_confluence.to_dict() if self.primary_confluence else None,
            "secondary_confluence": [c.to_dict() for c in self.secondary_confluence],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "entry_zone": self.entry_zone,
            "invalidation": self.invalidation,
            "targets": self.targets,
            "current_price": self.current_price,
            "market_regime": self.market_regime,
            "explanation": self.explanation,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_summary_dict(self) -> dict:
        """Compact summary for listings."""
        return {
            "setup_id": self.setup_id,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "setup_type": self.setup_type.value,
            "direction": self.direction.value,
            "confidence": round(self.confidence, 4),
            "confluence_score": round(self.confluence_score, 4),
            "primary_pattern": self.patterns[0].pattern_type.value if self.patterns else None,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SetupAnalysisResult:
    """Result of full setup analysis."""
    top_setup: Optional[Setup]
    alternative_setups: List[Setup]
    technical_bias: Direction
    bias_confidence: float
    analysis_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        return {
            "top_setup": self.top_setup.to_dict() if self.top_setup else None,
            "alternative_setups": [s.to_summary_dict() for s in self.alternative_setups],
            "technical_bias": self.technical_bias.value,
            "bias_confidence": round(self.bias_confidence, 4),
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }
