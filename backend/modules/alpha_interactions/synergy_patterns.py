"""
PHASE 16.4 — Synergy Patterns Types
====================================
Contracts for Synergy Pattern detection.

Synergy vs Reinforcement:
- Reinforcement: signals say the same thing (trend + momentum)
- Synergy: signals create NEW edge together (trend + compression + breakout)

Synergy Patterns:
1. trend_compression_breakout - Trend + Low Vol + Breakout = Volatility Expansion
2. flow_liquidation_cascade - Flow + Liquidation Risk = Cascade Move
3. volatility_expansion_trend - Expanding Vol + Trend = Trend Acceleration
4. structure_break_momentum - Structure Break + Momentum = Strong Continuation

Key Insight:
    Each signal alone is weak.
    Together they create a powerful setup.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# SYNERGY PATTERN REGISTRY
# ══════════════════════════════════════════════════════════════

class SynergyPattern(str, Enum):
    """Known synergy patterns."""
    TREND_COMPRESSION_BREAKOUT = "trend_compression_breakout"
    FLOW_LIQUIDATION_CASCADE = "flow_liquidation_cascade"
    VOLATILITY_EXPANSION_TREND = "volatility_expansion_trend"
    STRUCTURE_BREAK_MOMENTUM = "structure_break_momentum"


SYNERGY_PATTERNS: Set[str] = {
    SynergyPattern.TREND_COMPRESSION_BREAKOUT.value,
    SynergyPattern.FLOW_LIQUIDATION_CASCADE.value,
    SynergyPattern.VOLATILITY_EXPANSION_TREND.value,
    SynergyPattern.STRUCTURE_BREAK_MOMENTUM.value,
}


# ══════════════════════════════════════════════════════════════
# SYNERGY PATTERN WEIGHTS
# ══════════════════════════════════════════════════════════════

SYNERGY_PATTERN_WEIGHTS = {
    SynergyPattern.TREND_COMPRESSION_BREAKOUT.value: 0.30,   # Classic volatility expansion
    SynergyPattern.FLOW_LIQUIDATION_CASCADE.value: 0.25,    # Cascade moves
    SynergyPattern.VOLATILITY_EXPANSION_TREND.value: 0.25,  # Trend acceleration
    SynergyPattern.STRUCTURE_BREAK_MOMENTUM.value: 0.20,    # Strong continuation
}

# Modifier range based on synergy patterns detected
SYNERGY_MODIFIER_CONFIG = {
    "no_synergy": {"modifier": 1.00},
    "single_synergy": {"modifier_min": 1.05, "modifier_max": 1.08},
    "dual_synergy": {"modifier_min": 1.09, "modifier_max": 1.12},
    "multi_synergy": {"modifier_min": 1.13, "modifier_max": 1.15},
}


# ══════════════════════════════════════════════════════════════
# INPUT TYPES FOR SYNERGY DETECTION
# ══════════════════════════════════════════════════════════════

@dataclass
class TrendCompressionInput:
    """Input for trend + compression + breakout synergy."""
    trend_direction: str  # LONG / SHORT / NEUTRAL
    trend_strength: float  # 0..1
    volatility_state: str  # LOW_VOL / NORMAL / HIGH_VOL / EXPANDING
    volatility_percentile: float  # 0..1 (how compressed)
    breakout_detected: bool
    breakout_strength: float  # 0..1
    
    def to_dict(self) -> Dict:
        return {
            "trend_direction": self.trend_direction,
            "trend_strength": round(self.trend_strength, 4),
            "volatility_state": self.volatility_state,
            "volatility_percentile": round(self.volatility_percentile, 4),
            "breakout_detected": self.breakout_detected,
            "breakout_strength": round(self.breakout_strength, 4),
        }


@dataclass
class FlowLiquidationInput:
    """Input for flow + liquidation cascade synergy."""
    flow_direction: str  # BUY / SELL / NEUTRAL
    flow_intensity: float  # 0..1
    liquidation_risk: float  # 0..1
    liquidation_direction: str  # LONG_LIQUIDATION / SHORT_LIQUIDATION / NONE
    leverage_index: float  # 0..1
    
    def to_dict(self) -> Dict:
        return {
            "flow_direction": self.flow_direction,
            "flow_intensity": round(self.flow_intensity, 4),
            "liquidation_risk": round(self.liquidation_risk, 4),
            "liquidation_direction": self.liquidation_direction,
            "leverage_index": round(self.leverage_index, 4),
        }


@dataclass
class VolatilityTrendInput:
    """Input for volatility expansion + trend synergy."""
    volatility_state: str  # LOW_VOL / NORMAL / HIGH_VOL / EXPANDING
    volatility_change_rate: float  # Rate of vol change
    trend_direction: str  # LONG / SHORT / NEUTRAL
    trend_strength: float  # 0..1
    regime: str  # Market regime
    
    def to_dict(self) -> Dict:
        return {
            "volatility_state": self.volatility_state,
            "volatility_change_rate": round(self.volatility_change_rate, 4),
            "trend_direction": self.trend_direction,
            "trend_strength": round(self.trend_strength, 4),
            "regime": self.regime,
        }


@dataclass
class StructureMomentumInput:
    """Input for structure break + momentum synergy."""
    structure_break_detected: bool
    structure_break_direction: str  # BULLISH / BEARISH / NONE
    structure_quality: float  # 0..1
    momentum_direction: str  # LONG / SHORT / NEUTRAL
    momentum_strength: float  # 0..1
    
    def to_dict(self) -> Dict:
        return {
            "structure_break_detected": self.structure_break_detected,
            "structure_break_direction": self.structure_break_direction,
            "structure_quality": round(self.structure_quality, 4),
            "momentum_direction": self.momentum_direction,
            "momentum_strength": round(self.momentum_strength, 4),
        }


# ══════════════════════════════════════════════════════════════
# SYNERGY DETECTION RESULT
# ══════════════════════════════════════════════════════════════

@dataclass
class SynergyDetectionResult:
    """Result of single synergy pattern detection."""
    pattern_name: str
    detected: bool
    strength: float  # 0..1, how strong is the synergy
    potential: str  # LOW / MEDIUM / HIGH / EXPLOSIVE
    reason: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "pattern_name": self.pattern_name,
            "detected": self.detected,
            "strength": round(self.strength, 4),
            "potential": self.potential,
            "reason": self.reason,
            "inputs": self.inputs,
        }


# ══════════════════════════════════════════════════════════════
# SYNERGY STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class SynergyState:
    """
    Output from Synergy Engine.
    
    Synergy patterns create emergent edge from signal combinations.
    """
    symbol: str
    timestamp: datetime
    
    # Detected patterns
    patterns_detected: List[str]
    pattern_count: int
    
    # Pattern details
    pattern_results: List[SynergyDetectionResult]
    
    # Aggregated scores
    synergy_strength: float  # 0..1
    synergy_modifier: float  # 1.0 - 1.15
    
    # Best synergy pattern
    dominant_synergy: Optional[str]
    
    # Overall potential
    synergy_potential: str  # LOW / MEDIUM / HIGH / EXPLOSIVE
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "patterns_detected": self.patterns_detected,
            "pattern_count": self.pattern_count,
            "pattern_results": [p.to_dict() for p in self.pattern_results],
            "synergy_strength": round(self.synergy_strength, 4),
            "synergy_modifier": round(self.synergy_modifier, 4),
            "dominant_synergy": self.dominant_synergy,
            "synergy_potential": self.synergy_potential,
        }
