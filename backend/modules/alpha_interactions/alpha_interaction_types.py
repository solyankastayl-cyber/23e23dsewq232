"""
PHASE 16.1 — Alpha Interaction Types
=====================================
Contracts for Alpha Interaction Layer.

Purpose:
    Define signal interaction analysis contracts.
    Interaction Layer analyzes how signals reinforce or conflict.

Key Principle:
    Interaction NEVER blocks a signal.
    It only modifies confidence based on signal combinations.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# INTERACTION STATE ENUM
# ══════════════════════════════════════════════════════════════

class InteractionState(str, Enum):
    """Signal interaction classification."""
    REINFORCED = "REINFORCED"      # Signals align and strengthen each other
    NEUTRAL = "NEUTRAL"            # Signals are independent
    CONFLICTED = "CONFLICTED"      # Signals contradict each other


# ══════════════════════════════════════════════════════════════
# INTERACTION THRESHOLDS
# ══════════════════════════════════════════════════════════════

INTERACTION_THRESHOLDS = {
    "reinforced_min": 0.20,      # net_score > 0.20 = REINFORCED
    "conflicted_max": -0.20,    # net_score < -0.20 = CONFLICTED
    # Between = NEUTRAL
}


# ══════════════════════════════════════════════════════════════
# CONFIDENCE MODIFIERS BY STATE
# ══════════════════════════════════════════════════════════════

INTERACTION_MODIFIERS = {
    InteractionState.REINFORCED: {
        "confidence_modifier_min": 1.05,
        "confidence_modifier_max": 1.15,
    },
    InteractionState.NEUTRAL: {
        "confidence_modifier_min": 1.00,
        "confidence_modifier_max": 1.00,
    },
    InteractionState.CONFLICTED: {
        "confidence_modifier_min": 0.75,
        "confidence_modifier_max": 0.90,
    },
}


# ══════════════════════════════════════════════════════════════
# INPUT SNAPSHOT TYPES
# ══════════════════════════════════════════════════════════════

@dataclass
class TAInputForInteraction:
    """
    TA Hypothesis input for interaction analysis.
    """
    direction: str  # LONG / SHORT / NEUTRAL
    conviction: float  # 0..1
    trend_strength: float  # 0..1
    setup_quality: float  # 0..1
    regime: str  # TREND_UP / TREND_DOWN / RANGE / etc
    
    def to_dict(self) -> Dict:
        return {
            "direction": self.direction,
            "conviction": round(self.conviction, 4),
            "trend_strength": round(self.trend_strength, 4),
            "setup_quality": round(self.setup_quality, 4),
            "regime": self.regime,
        }


@dataclass
class ExchangeInputForInteraction:
    """
    Exchange Context input for interaction analysis.
    """
    bias: str  # BULLISH / BEARISH / NEUTRAL
    confidence: float  # 0..1
    dominant_signal: str  # funding / flow / derivatives / etc
    conflict_ratio: float  # 0..1, high = conflicting signals
    
    def to_dict(self) -> Dict:
        return {
            "bias": self.bias,
            "confidence": round(self.confidence, 4),
            "dominant_signal": self.dominant_signal,
            "conflict_ratio": round(self.conflict_ratio, 4),
        }


@dataclass
class MarketStateInputForInteraction:
    """
    Market State Matrix input for interaction analysis.
    """
    trend_state: str  # TREND_UP / TREND_DOWN / RANGE / MIXED
    exchange_state: str  # BULLISH / BEARISH / CONFLICTED / NEUTRAL
    combined_state: str  # Full combined state label
    
    def to_dict(self) -> Dict:
        return {
            "trend_state": self.trend_state,
            "exchange_state": self.exchange_state,
            "combined_state": self.combined_state,
        }


@dataclass
class EcologyInputForInteraction:
    """
    Alpha Ecology input for interaction analysis.
    """
    ecology_score: float  # 0..1
    ecology_state: str  # HEALTHY / STABLE / STRESSED / CRITICAL
    
    def to_dict(self) -> Dict:
        return {
            "ecology_score": round(self.ecology_score, 4),
            "ecology_state": self.ecology_state,
        }


# ══════════════════════════════════════════════════════════════
# ALPHA INTERACTION STATE CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class AlphaInteractionState:
    """
    Output from Alpha Interaction Engine.
    
    Analyzes how multiple signal sources interact:
    - Do they reinforce each other? (same direction)
    - Do they conflict? (opposite directions)
    - Are they neutral? (independent)
    
    Key Principle:
        Interaction NEVER blocks a signal.
        It only provides a confidence modifier.
    """
    symbol: str
    timestamp: datetime
    
    # Interaction scores (0..1)
    reinforcement_score: float
    conflict_score: float
    
    # Net interaction score (-1..1)
    net_interaction_score: float
    
    # Final state
    interaction_state: InteractionState
    
    # Confidence modifier (0.5..1.15)
    confidence_modifier: float
    
    # Explainability
    drivers: Dict[str, Any] = field(default_factory=dict)
    
    # Input snapshots for debugging
    ta_input: Optional[TAInputForInteraction] = None
    exchange_input: Optional[ExchangeInputForInteraction] = None
    market_state_input: Optional[MarketStateInputForInteraction] = None
    ecology_input: Optional[EcologyInputForInteraction] = None
    
    def to_dict(self) -> Dict:
        result = {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "reinforcement_score": round(self.reinforcement_score, 4),
            "conflict_score": round(self.conflict_score, 4),
            "net_interaction_score": round(self.net_interaction_score, 4),
            "interaction_state": self.interaction_state.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "drivers": self.drivers,
        }
        
        # Add input snapshots if available
        if self.ta_input:
            result["ta_input"] = self.ta_input.to_dict()
        if self.exchange_input:
            result["exchange_input"] = self.exchange_input.to_dict()
        if self.market_state_input:
            result["market_state_input"] = self.market_state_input.to_dict()
        if self.ecology_input:
            result["ecology_input"] = self.ecology_input.to_dict()
        
        return result


# ══════════════════════════════════════════════════════════════
# INTERACTION ANALYSIS WEIGHTS
# ══════════════════════════════════════════════════════════════

REINFORCEMENT_WEIGHTS = {
    "ta_exchange_alignment": 0.40,  # TA direction matches exchange bias
    "trend_alignment": 0.30,        # TA direction matches trend state
    "ecology_support": 0.30,        # Ecology is supportive (HEALTHY/STABLE)
}

CONFLICT_WEIGHTS = {
    "ta_exchange_conflict": 0.50,   # TA direction opposes exchange bias
    "exchange_conflict_ratio": 0.30,  # Exchange internal conflict
    "hostile_market_mismatch": 0.20,  # Market state doesn't support signal
}
