"""
PHASE 16.5 — Cancellation Patterns Types
=========================================
Contracts for Cancellation Pattern detection.

Cancellation vs Conflict:
- Conflict: signal A vs signal B (opposing signals)
- Cancellation: signal C makes entire setup INVALID

Cancellation Patterns:
1. extreme_crowding_reversal - Market overloaded, violent reversal likely
2. liquidity_trap - Fake breakout setup
3. volatility_fake_expansion - Move without volume confirmation
4. trend_exhaustion - Trend ending, divergence present

Key Principle:
    Cancellation should VOID a trade, not just reduce confidence.
    Even strong reinforcement + synergy can be cancelled.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# CANCELLATION PATTERN REGISTRY
# ══════════════════════════════════════════════════════════════

class CancellationPattern(str, Enum):
    """Known cancellation patterns."""
    EXTREME_CROWDING_REVERSAL = "extreme_crowding_reversal"
    LIQUIDITY_TRAP = "liquidity_trap"
    VOLATILITY_FAKE_EXPANSION = "volatility_fake_expansion"
    TREND_EXHAUSTION = "trend_exhaustion"


CANCELLATION_PATTERNS: Set[str] = {
    CancellationPattern.EXTREME_CROWDING_REVERSAL.value,
    CancellationPattern.LIQUIDITY_TRAP.value,
    CancellationPattern.VOLATILITY_FAKE_EXPANSION.value,
    CancellationPattern.TREND_EXHAUSTION.value,
}


# ══════════════════════════════════════════════════════════════
# CANCELLATION PATTERN WEIGHTS
# ══════════════════════════════════════════════════════════════

CANCELLATION_PATTERN_WEIGHTS = {
    CancellationPattern.EXTREME_CROWDING_REVERSAL.value: 0.30,  # Most dangerous
    CancellationPattern.LIQUIDITY_TRAP.value: 0.25,             # Common trap
    CancellationPattern.VOLATILITY_FAKE_EXPANSION.value: 0.25,  # Fake moves
    CancellationPattern.TREND_EXHAUSTION.value: 0.20,           # End of trend
}

# Modifier range based on cancellation patterns detected
CANCELLATION_MODIFIER_CONFIG = {
    "no_cancellation": {"modifier": 1.00},
    "single_cancellation": {"modifier_min": 0.85, "modifier_max": 0.90},
    "dual_cancellation": {"modifier_min": 0.75, "modifier_max": 0.82},
    "multi_cancellation": {"modifier_min": 0.60, "modifier_max": 0.70},
}


# ══════════════════════════════════════════════════════════════
# INPUT TYPES FOR CANCELLATION DETECTION
# ══════════════════════════════════════════════════════════════

@dataclass
class CrowdingReversalInput:
    """Input for extreme crowding reversal detection."""
    crowding_score: float  # 0..1
    funding_extreme: bool
    funding_direction: str  # LONG_CROWDED / SHORT_CROWDED / NEUTRAL
    leverage_index: float  # 0..1
    open_interest_change: float  # -1..1
    
    def to_dict(self) -> Dict:
        return {
            "crowding_score": round(self.crowding_score, 4),
            "funding_extreme": self.funding_extreme,
            "funding_direction": self.funding_direction,
            "leverage_index": round(self.leverage_index, 4),
            "open_interest_change": round(self.open_interest_change, 4),
        }


@dataclass
class LiquidityTrapInput:
    """Input for liquidity trap detection."""
    flow_direction: str  # BUY / SELL / NEUTRAL
    flow_intensity: float  # 0..1
    structure_break_direction: str  # BULLISH / BEARISH / NONE
    price_rejection: bool  # Price rejected from level
    wick_ratio: float  # 0..1, high = rejection
    
    def to_dict(self) -> Dict:
        return {
            "flow_direction": self.flow_direction,
            "flow_intensity": round(self.flow_intensity, 4),
            "structure_break_direction": self.structure_break_direction,
            "price_rejection": self.price_rejection,
            "wick_ratio": round(self.wick_ratio, 4),
        }


@dataclass
class FakeExpansionInput:
    """Input for volatility fake expansion detection."""
    volatility_expanding: bool
    volatility_change_rate: float  # 0..1
    volume_spike: bool
    volume_ratio: float  # Current vs average
    price_follow_through: bool  # Did price continue?
    
    def to_dict(self) -> Dict:
        return {
            "volatility_expanding": self.volatility_expanding,
            "volatility_change_rate": round(self.volatility_change_rate, 4),
            "volume_spike": self.volume_spike,
            "volume_ratio": round(self.volume_ratio, 4),
            "price_follow_through": self.price_follow_through,
        }


@dataclass
class TrendExhaustionInput:
    """Input for trend exhaustion detection."""
    trend_direction: str  # LONG / SHORT / NEUTRAL
    trend_strength: float  # 0..1
    momentum_divergence: bool  # Price vs momentum diverging
    divergence_strength: float  # 0..1
    rsi_extreme: bool  # RSI at extreme levels
    
    def to_dict(self) -> Dict:
        return {
            "trend_direction": self.trend_direction,
            "trend_strength": round(self.trend_strength, 4),
            "momentum_divergence": self.momentum_divergence,
            "divergence_strength": round(self.divergence_strength, 4),
            "rsi_extreme": self.rsi_extreme,
        }


# ══════════════════════════════════════════════════════════════
# CANCELLATION DETECTION RESULT
# ══════════════════════════════════════════════════════════════

@dataclass
class CancellationDetectionResult:
    """Result of single cancellation pattern detection."""
    pattern_name: str
    detected: bool
    strength: float  # 0..1, how strong is the cancellation signal
    severity: str  # WARNING / CANCEL / CRITICAL
    reason: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "pattern_name": self.pattern_name,
            "detected": self.detected,
            "strength": round(self.strength, 4),
            "severity": self.severity,
            "reason": self.reason,
            "inputs": self.inputs,
        }


# ══════════════════════════════════════════════════════════════
# CANCELLATION STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class CancellationState:
    """
    Output from Cancellation Engine.
    
    Cancellation patterns void trades even with reinforcement/synergy.
    """
    symbol: str
    timestamp: datetime
    
    # Detected patterns
    patterns_detected: List[str]
    pattern_count: int
    
    # Pattern details
    pattern_results: List[CancellationDetectionResult]
    
    # Aggregated scores
    cancellation_strength: float  # 0..1
    cancellation_modifier: float  # 0.60 - 1.00
    
    # Should trade be cancelled?
    trade_cancelled: bool
    
    # Most critical pattern
    dominant_cancellation: Optional[str]
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "patterns_detected": self.patterns_detected,
            "pattern_count": self.pattern_count,
            "pattern_results": [p.to_dict() for p in self.pattern_results],
            "cancellation_strength": round(self.cancellation_strength, 4),
            "cancellation_modifier": round(self.cancellation_modifier, 4),
            "trade_cancelled": self.trade_cancelled,
            "dominant_cancellation": self.dominant_cancellation,
        }
