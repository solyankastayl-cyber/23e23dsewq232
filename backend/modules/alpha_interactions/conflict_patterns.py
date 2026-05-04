"""
PHASE 16.3 — Conflict Patterns Types
=====================================
Contracts for Conflict Pattern detection.

Conflict Patterns:
1. ta_exchange_direction_conflict - TA vs Exchange opposite directions
2. trend_vs_mean_reversion - Trend signal vs mean reversion signal
3. flow_vs_structure_conflict - Order flow vs structure break
4. derivatives_vs_trend_conflict - Derivatives crowding vs trend

Key Principle:
    Different conflicts have different consequences.
    Not all conflicts are equally dangerous.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# CONFLICT PATTERN REGISTRY
# ══════════════════════════════════════════════════════════════

class ConflictPattern(str, Enum):
    """Known conflict patterns."""
    TA_EXCHANGE_DIRECTION = "ta_exchange_direction_conflict"
    TREND_VS_MEAN_REVERSION = "trend_vs_mean_reversion"
    FLOW_VS_STRUCTURE = "flow_vs_structure_conflict"
    DERIVATIVES_VS_TREND = "derivatives_vs_trend_conflict"


CONFLICT_PATTERNS: Set[str] = {
    ConflictPattern.TA_EXCHANGE_DIRECTION.value,
    ConflictPattern.TREND_VS_MEAN_REVERSION.value,
    ConflictPattern.FLOW_VS_STRUCTURE.value,
    ConflictPattern.DERIVATIVES_VS_TREND.value,
}


# ══════════════════════════════════════════════════════════════
# CONFLICT SEVERITY LEVELS
# ══════════════════════════════════════════════════════════════

class ConflictSeverity(str, Enum):
    """Conflict severity classification."""
    LOW_CONFLICT = "LOW_CONFLICT"
    MEDIUM_CONFLICT = "MEDIUM_CONFLICT"
    HIGH_CONFLICT = "HIGH_CONFLICT"


SEVERITY_THRESHOLDS = {
    "high_min": 0.6,      # >= 0.6 = HIGH
    "medium_min": 0.35,   # >= 0.35 = MEDIUM
    # below = LOW
}


# ══════════════════════════════════════════════════════════════
# CONFLICT PATTERN WEIGHTS
# ══════════════════════════════════════════════════════════════

CONFLICT_PATTERN_WEIGHTS = {
    ConflictPattern.TA_EXCHANGE_DIRECTION.value: 0.30,   # Direct signal conflict
    ConflictPattern.TREND_VS_MEAN_REVERSION.value: 0.25, # Strategy logic conflict
    ConflictPattern.FLOW_VS_STRUCTURE.value: 0.25,       # Liquidity trap risk
    ConflictPattern.DERIVATIVES_VS_TREND.value: 0.20,    # Crowding risk
}

# Modifier range based on conflicts detected
CONFLICT_MODIFIER_CONFIG = {
    "no_conflicts": {"modifier": 1.00},
    "single_conflict": {"modifier_min": 0.90, "modifier_max": 0.95},
    "dual_conflicts": {"modifier_min": 0.82, "modifier_max": 0.88},
    "multi_conflicts": {"modifier_min": 0.70, "modifier_max": 0.80},
}


# ══════════════════════════════════════════════════════════════
# INPUT TYPES FOR CONFLICT DETECTION
# ══════════════════════════════════════════════════════════════

@dataclass
class TAExchangeConflictInput:
    """Input for TA vs Exchange direction conflict."""
    ta_direction: str  # LONG / SHORT / NEUTRAL
    ta_conviction: float  # 0..1
    exchange_bias: str  # BULLISH / BEARISH / NEUTRAL
    exchange_confidence: float  # 0..1
    
    def to_dict(self) -> Dict:
        return {
            "ta_direction": self.ta_direction,
            "ta_conviction": round(self.ta_conviction, 4),
            "exchange_bias": self.exchange_bias,
            "exchange_confidence": round(self.exchange_confidence, 4),
        }


@dataclass
class TrendMeanReversionInput:
    """Input for trend vs mean reversion conflict."""
    trend_state: str  # TREND_UP / TREND_DOWN / RANGE
    trend_strength: float  # 0..1
    mean_reversion_signal: bool
    mean_reversion_strength: float  # 0..1
    rsi_extreme: bool  # RSI at extreme levels
    
    def to_dict(self) -> Dict:
        return {
            "trend_state": self.trend_state,
            "trend_strength": round(self.trend_strength, 4),
            "mean_reversion_signal": self.mean_reversion_signal,
            "mean_reversion_strength": round(self.mean_reversion_strength, 4),
            "rsi_extreme": self.rsi_extreme,
        }


@dataclass
class FlowStructureInput:
    """Input for flow vs structure conflict."""
    flow_direction: str  # BUY / SELL / NEUTRAL
    flow_intensity: float  # 0..1
    structure_break_direction: str  # BULLISH / BEARISH / NONE
    structure_quality: float  # 0..1
    
    def to_dict(self) -> Dict:
        return {
            "flow_direction": self.flow_direction,
            "flow_intensity": round(self.flow_intensity, 4),
            "structure_break_direction": self.structure_break_direction,
            "structure_quality": round(self.structure_quality, 4),
        }


@dataclass
class DerivativesTrendInput:
    """Input for derivatives vs trend conflict."""
    trend_direction: str  # LONG / SHORT / NEUTRAL
    trend_strength: float  # 0..1
    funding_state: str  # LONG_CROWDED / SHORT_CROWDED / NEUTRAL / EXTREME_LONG / EXTREME_SHORT
    crowding_risk: float  # 0..1
    leverage_index: float  # 0..1
    
    def to_dict(self) -> Dict:
        return {
            "trend_direction": self.trend_direction,
            "trend_strength": round(self.trend_strength, 4),
            "funding_state": self.funding_state,
            "crowding_risk": round(self.crowding_risk, 4),
            "leverage_index": round(self.leverage_index, 4),
        }


# ══════════════════════════════════════════════════════════════
# CONFLICT DETECTION RESULT
# ══════════════════════════════════════════════════════════════

@dataclass
class ConflictDetectionResult:
    """Result of single conflict pattern detection."""
    pattern_name: str
    detected: bool
    strength: float  # 0..1, how strong is the conflict
    danger_level: str  # LOW / MEDIUM / HIGH
    reason: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "pattern_name": self.pattern_name,
            "detected": self.detected,
            "strength": round(self.strength, 4),
            "danger_level": self.danger_level,
            "reason": self.reason,
            "inputs": self.inputs,
        }


# ══════════════════════════════════════════════════════════════
# CONFLICT PATTERN STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class ConflictPatternState:
    """
    Output from Conflict Patterns Engine.
    
    Contains all detected conflict patterns and their combined effect.
    """
    symbol: str
    timestamp: datetime
    
    # Detected patterns
    patterns_detected: List[str]
    pattern_count: int
    
    # Pattern details
    pattern_results: List[ConflictDetectionResult]
    
    # Aggregated scores
    conflict_strength: float  # 0..1
    conflict_modifier: float  # 0.70 - 1.00
    
    # Severity classification
    conflict_severity: ConflictSeverity
    
    # Most dangerous pattern
    dominant_conflict: Optional[str]
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "patterns_detected": self.patterns_detected,
            "pattern_count": self.pattern_count,
            "pattern_results": [p.to_dict() for p in self.pattern_results],
            "conflict_strength": round(self.conflict_strength, 4),
            "conflict_modifier": round(self.conflict_modifier, 4),
            "conflict_severity": self.conflict_severity.value,
            "dominant_conflict": self.dominant_conflict,
        }
