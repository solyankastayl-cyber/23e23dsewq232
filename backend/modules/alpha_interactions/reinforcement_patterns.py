"""
PHASE 16.2 — Reinforcement Patterns Engine
============================================
Detects specific signal combinations that historically provide strong edge.

Patterns:
1. trend_momentum_alignment - Trend + Momentum same direction
2. breakout_volatility_expansion - Breakout + Volatility expanding
3. flow_squeeze_alignment - Flow buy + Short squeeze probability
4. trend_structure_break - Trend + Structure break aligned

Purpose:
    Move from abstract reinforcement scoring to concrete pattern detection.
    Each pattern represents a proven signal combination.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# PATTERN REGISTRY
# ══════════════════════════════════════════════════════════════

class ReinforcementPattern(str, Enum):
    """Known reinforcement patterns."""
    TREND_MOMENTUM_ALIGNMENT = "trend_momentum_alignment"
    BREAKOUT_VOLATILITY_EXPANSION = "breakout_volatility_expansion"
    FLOW_SQUEEZE_ALIGNMENT = "flow_squeeze_alignment"
    TREND_STRUCTURE_BREAK = "trend_structure_break"


REINFORCEMENT_PATTERNS: Set[str] = {
    ReinforcementPattern.TREND_MOMENTUM_ALIGNMENT.value,
    ReinforcementPattern.BREAKOUT_VOLATILITY_EXPANSION.value,
    ReinforcementPattern.FLOW_SQUEEZE_ALIGNMENT.value,
    ReinforcementPattern.TREND_STRUCTURE_BREAK.value,
}


# ══════════════════════════════════════════════════════════════
# PATTERN WEIGHTS
# ══════════════════════════════════════════════════════════════

PATTERN_WEIGHTS = {
    ReinforcementPattern.TREND_MOMENTUM_ALIGNMENT.value: 0.30,
    ReinforcementPattern.BREAKOUT_VOLATILITY_EXPANSION.value: 0.25,
    ReinforcementPattern.FLOW_SQUEEZE_ALIGNMENT.value: 0.25,
    ReinforcementPattern.TREND_STRUCTURE_BREAK.value: 0.20,
}

# Modifier range based on patterns detected
PATTERN_MODIFIER_CONFIG = {
    "no_patterns": {"modifier": 1.00},
    "single_pattern": {"modifier_min": 1.03, "modifier_max": 1.06},
    "dual_patterns": {"modifier_min": 1.07, "modifier_max": 1.10},
    "multi_patterns": {"modifier_min": 1.11, "modifier_max": 1.15},
}


# ══════════════════════════════════════════════════════════════
# INPUT TYPES FOR PATTERN DETECTION
# ══════════════════════════════════════════════════════════════

@dataclass
class TrendMomentumInput:
    """Input for trend + momentum pattern."""
    trend_direction: str  # LONG / SHORT / NEUTRAL
    trend_strength: float  # 0..1
    momentum_direction: str  # LONG / SHORT / NEUTRAL
    momentum_strength: float  # 0..1
    
    def to_dict(self) -> Dict:
        return {
            "trend_direction": self.trend_direction,
            "trend_strength": round(self.trend_strength, 4),
            "momentum_direction": self.momentum_direction,
            "momentum_strength": round(self.momentum_strength, 4),
        }


@dataclass
class BreakoutVolatilityInput:
    """Input for breakout + volatility pattern."""
    breakout_detected: bool
    breakout_direction: str  # LONG / SHORT / NEUTRAL
    breakout_strength: float  # 0..1
    volatility_state: str  # LOW / NORMAL / HIGH / EXPANDING
    volatility_expansion_rate: float  # 0..1
    
    def to_dict(self) -> Dict:
        return {
            "breakout_detected": self.breakout_detected,
            "breakout_direction": self.breakout_direction,
            "breakout_strength": round(self.breakout_strength, 4),
            "volatility_state": self.volatility_state,
            "volatility_expansion_rate": round(self.volatility_expansion_rate, 4),
        }


@dataclass
class FlowSqueezeInput:
    """Input for flow + squeeze pattern."""
    flow_direction: str  # BUY / SELL / NEUTRAL
    flow_intensity: float  # 0..1
    squeeze_probability: float  # 0..1
    squeeze_type: str  # LONG_SQUEEZE / SHORT_SQUEEZE / NONE
    
    def to_dict(self) -> Dict:
        return {
            "flow_direction": self.flow_direction,
            "flow_intensity": round(self.flow_intensity, 4),
            "squeeze_probability": round(self.squeeze_probability, 4),
            "squeeze_type": self.squeeze_type,
        }


@dataclass
class TrendStructureInput:
    """Input for trend + structure break pattern."""
    trend_direction: str  # LONG / SHORT / NEUTRAL
    trend_strength: float  # 0..1
    structure_break_detected: bool
    structure_break_direction: str  # BULLISH / BEARISH / NONE
    structure_quality: float  # 0..1
    
    def to_dict(self) -> Dict:
        return {
            "trend_direction": self.trend_direction,
            "trend_strength": round(self.trend_strength, 4),
            "structure_break_detected": self.structure_break_detected,
            "structure_break_direction": self.structure_break_direction,
            "structure_quality": round(self.structure_quality, 4),
        }


# ══════════════════════════════════════════════════════════════
# PATTERN DETECTION RESULT
# ══════════════════════════════════════════════════════════════

@dataclass
class PatternDetectionResult:
    """Result of single pattern detection."""
    pattern_name: str
    detected: bool
    strength: float  # 0..1, how strong is the pattern
    confidence: float  # 0..1
    reason: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "pattern_name": self.pattern_name,
            "detected": self.detected,
            "strength": round(self.strength, 4),
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
            "inputs": self.inputs,
        }


# ══════════════════════════════════════════════════════════════
# REINFORCEMENT PATTERN STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class ReinforcementPatternState:
    """
    Output from Reinforcement Patterns Engine.
    
    Contains all detected patterns and their combined effect.
    """
    symbol: str
    timestamp: datetime
    
    # Detected patterns
    patterns_detected: List[str]
    pattern_count: int
    
    # Pattern details
    pattern_results: List[PatternDetectionResult]
    
    # Aggregated scores
    reinforcement_strength: float  # 0..1
    reinforcement_modifier: float  # 1.0 - 1.15
    
    # Dominant pattern
    dominant_pattern: Optional[str]
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "patterns_detected": self.patterns_detected,
            "pattern_count": self.pattern_count,
            "pattern_results": [p.to_dict() for p in self.pattern_results],
            "reinforcement_strength": round(self.reinforcement_strength, 4),
            "reinforcement_modifier": round(self.reinforcement_modifier, 4),
            "dominant_pattern": self.dominant_pattern,
        }
