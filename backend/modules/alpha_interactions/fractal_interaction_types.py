"""
PHASE 24.2 — Fractal Interaction Types

Types for Fractal Intelligence integration into Alpha Interaction Layer.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Literal
from datetime import datetime, timezone
from enum import Enum


class FractalInteractionState(str, Enum):
    """Fractal interaction classification."""
    ALIGNED = "ALIGNED"           # All 3 legs agree (TA + Exchange + Fractal)
    MIXED = "MIXED"               # Partial agreement
    CONFLICTED = "CONFLICTED"     # Signals contradict
    WEAK = "WEAK"                 # Signals too weak to classify


class DominantSignal(str, Enum):
    """Which signal source dominates."""
    TA = "TA"
    EXCHANGE = "EXCHANGE"
    FRACTAL = "FRACTAL"
    MIXED = "MIXED"


# ══════════════════════════════════════════════════════════════
# FRACTAL INTERACTION INPUT
# ══════════════════════════════════════════════════════════════

@dataclass
class FractalInputForInteraction:
    """
    Fractal Context input for interaction analysis.
    
    From FractalContext contract:
    - direction: LONG/SHORT/HOLD
    - confidence: 0..1
    - reliability: 0..1
    - phase: MARKUP/MARKDOWN/ACCUMULATION/etc
    - context_state: SUPPORTIVE/NEUTRAL/CONFLICTED/BLOCKED
    - fractal_strength: 0..1
    """
    direction: str = "HOLD"
    confidence: float = 0.0
    reliability: float = 0.0
    phase: Optional[str] = None
    context_state: str = "BLOCKED"
    fractal_strength: float = 0.0
    dominant_horizon: Optional[int] = None
    expected_return: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            "direction": self.direction,
            "confidence": round(self.confidence, 4),
            "reliability": round(self.reliability, 4),
            "phase": self.phase,
            "context_state": self.context_state,
            "fractal_strength": round(self.fractal_strength, 4),
            "dominant_horizon": self.dominant_horizon,
            "expected_return": round(self.expected_return, 4) if self.expected_return else None,
        }
    
    def is_directional(self) -> bool:
        """Check if fractal has directional signal."""
        return self.direction in ["LONG", "SHORT"]
    
    def is_active(self) -> bool:
        """Check if fractal is active (not BLOCKED/NEUTRAL hold)."""
        return self.context_state not in ["BLOCKED"] and self.direction != "HOLD"


# ══════════════════════════════════════════════════════════════
# FRACTAL INTERACTION PATTERNS
# ══════════════════════════════════════════════════════════════

# Pattern 1: TA ↔ Fractal Alignment
TA_FRACTAL_ALIGNMENT_CONFIG = {
    "name": "ta_fractal_alignment",
    "description": "TA direction matches Fractal direction with SUPPORTIVE state",
    "confidence_bonus": 0.05,
    "capital_bonus": 0.05,
    "required_fractal_state": "SUPPORTIVE",
}

# Pattern 2: Exchange ↔ Fractal Alignment
EXCHANGE_FRACTAL_ALIGNMENT_CONFIG = {
    "name": "exchange_fractal_alignment",
    "description": "Exchange bias matches Fractal direction with strength > 0.55",
    "confidence_bonus": 0.04,
    "capital_bonus": 0.03,
    "min_fractal_strength": 0.55,
}

# Pattern 3: Fractal Conflict
FRACTAL_CONFLICT_CONFIG = {
    "name": "fractal_conflict",
    "description": "TA direction opposes Fractal direction with strength >= 0.60",
    "confidence_penalty": -0.07,
    "capital_penalty": -0.06,
    "min_fractal_strength": 0.60,
}

# Pattern 4: Phase Direction Support
PHASE_DIRECTION_SUPPORT_CONFIG = {
    "name": "phase_direction_support",
    "description": "Fractal phase supports signal direction (MARKUP→LONG, MARKDOWN→SHORT)",
    "confidence_bonus": 0.04,
    "capital_bonus": 0.02,
    "min_fractal_strength": 0.50,
    "phase_direction_map": {
        "MARKUP": "LONG",
        "MARKDOWN": "SHORT",
        "RECOVERY": "LONG",
        "CAPITULATION": "SHORT",
    },
}


# ══════════════════════════════════════════════════════════════
# INTERACTION RESULT WITH FRACTAL
# ══════════════════════════════════════════════════════════════

@dataclass
class FractalInteractionResult:
    """
    Result of interaction analysis with Fractal as third leg.
    
    Key principle: Fractal does NOT change direction.
    It only modifies confidence and capital.
    """
    symbol: str
    timestamp: datetime
    
    # Final direction (from TA, NOT from Fractal)
    final_direction: str
    
    # Support scores from each leg
    ta_support: float           # 0..1
    exchange_support: float     # 0..1
    fractal_support: float      # 0..1
    
    # Base values
    base_confidence: float
    
    # Modifiers from fractal interaction
    confidence_modifier: float  # 0.75..1.25
    capital_modifier: float     # 0.70..1.15
    
    # Interaction analysis
    interaction_state: FractalInteractionState
    dominant_signal: DominantSignal
    
    # Fields with defaults must come after non-default fields
    base_capital: float = 1.0
    
    # Detected patterns
    patterns_detected: list = field(default_factory=list)
    
    # Fractal-specific data
    fractal_direction: str = "HOLD"
    fractal_phase: Optional[str] = None
    fractal_context_state: str = "BLOCKED"
    
    # Explainability
    drivers: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "final_direction": self.final_direction,
            "ta_support": round(self.ta_support, 4),
            "exchange_support": round(self.exchange_support, 4),
            "fractal_support": round(self.fractal_support, 4),
            "base_confidence": round(self.base_confidence, 4),
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "interaction_state": self.interaction_state.value,
            "dominant_signal": self.dominant_signal.value,
            "patterns_detected": self.patterns_detected,
            "fractal": {
                "direction": self.fractal_direction,
                "phase": self.fractal_phase,
                "context_state": self.fractal_context_state,
            },
            "drivers": self.drivers,
        }
    
    def to_snapshot(self) -> Dict:
        """Compact snapshot for Trading Product."""
        return {
            "final_direction": self.final_direction,
            "ta_support": round(self.ta_support, 4),
            "exchange_support": round(self.exchange_support, 4),
            "fractal_support": round(self.fractal_support, 4),
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "interaction_state": self.interaction_state.value,
            "dominant_signal": self.dominant_signal.value,
        }


# ══════════════════════════════════════════════════════════════
# MODIFIER BOUNDS
# ══════════════════════════════════════════════════════════════

MODIFIER_BOUNDS = {
    "confidence_min": 0.75,
    "confidence_max": 1.25,
    "capital_min": 0.70,
    "capital_max": 1.15,
}

# Alias for test compatibility
FRACTAL_INFLUENCE_LIMITS = {
    "confidence_modifier_min": 0.75,
    "confidence_modifier_max": 1.25,
    "capital_modifier_min": 0.70,
    "capital_modifier_max": 1.15,
}
