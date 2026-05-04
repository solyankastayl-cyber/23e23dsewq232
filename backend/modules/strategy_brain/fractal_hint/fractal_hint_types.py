"""
PHASE 24.3 — Fractal Hint Types

Types for Fractal Intelligence integration into Strategy Brain.
Fractal provides regime hints with LIMITED influence (≤10%).
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List
from datetime import datetime, timezone
from enum import Enum


class FractalPhase(str, Enum):
    """Fractal market phases from FractalContext."""
    MARKUP = "MARKUP"
    MARKDOWN = "MARKDOWN"
    ACCUMULATION = "ACCUMULATION"
    DISTRIBUTION = "DISTRIBUTION"
    RECOVERY = "RECOVERY"
    CAPITULATION = "CAPITULATION"
    UNKNOWN = "UNKNOWN"


# ══════════════════════════════════════════════════════════════
# FRACTAL PHASE → STRATEGY MAPPING
# ══════════════════════════════════════════════════════════════

# Which strategies are supported by each fractal phase
FRACTAL_PHASE_STRATEGY_MAP = {
    FractalPhase.MARKUP: {
        "supported": ["trend_following", "breakout", "flow_following"],
        "anti": ["mean_reversion", "structure_reversal"],
        "regime_hint": "bullish_trend",
    },
    FractalPhase.MARKDOWN: {
        "supported": ["trend_following", "breakout", "flow_following"],
        "anti": ["mean_reversion", "structure_reversal"],
        "regime_hint": "bearish_trend",
    },
    FractalPhase.ACCUMULATION: {
        "supported": ["mean_reversion", "liquidation_capture", "funding_arb"],
        "anti": ["trend_following", "breakout"],
        "regime_hint": "range_compression",
    },
    FractalPhase.DISTRIBUTION: {
        "supported": ["mean_reversion", "volatility_expansion", "structure_reversal"],
        "anti": ["trend_following"],
        "regime_hint": "range_topping",
    },
    FractalPhase.RECOVERY: {
        "supported": ["trend_following", "flow_following"],
        "anti": ["mean_reversion"],
        "regime_hint": "transition_bullish",
    },
    FractalPhase.CAPITULATION: {
        "supported": ["liquidation_capture", "structure_reversal"],
        "anti": ["trend_following", "breakout"],
        "regime_hint": "crisis_mode",
    },
    FractalPhase.UNKNOWN: {
        "supported": [],
        "anti": [],
        "regime_hint": "undefined",
    },
}


# ══════════════════════════════════════════════════════════════
# FRACTAL HINT INPUT
# ══════════════════════════════════════════════════════════════

@dataclass
class FractalHintInput:
    """
    Fractal hint input for Strategy Brain.
    
    Key principle: Fractal influence is LIMITED to ≤10%.
    """
    phase: FractalPhase = FractalPhase.UNKNOWN
    phase_confidence: float = 0.0
    fractal_strength: float = 0.0
    context_state: str = "BLOCKED"
    direction: str = "HOLD"
    
    def to_dict(self) -> Dict:
        return {
            "phase": self.phase.value,
            "phase_confidence": round(self.phase_confidence, 4),
            "fractal_strength": round(self.fractal_strength, 4),
            "context_state": self.context_state,
            "direction": self.direction,
        }
    
    def is_active(self) -> bool:
        """Check if fractal hint should be used."""
        return (
            self.context_state not in ["BLOCKED"] and
            self.phase != FractalPhase.UNKNOWN and
            self.fractal_strength > 0.3
        )
    
    def get_supported_strategies(self) -> List[str]:
        """Get strategies supported by current phase."""
        return FRACTAL_PHASE_STRATEGY_MAP.get(self.phase, {}).get("supported", [])
    
    def get_anti_strategies(self) -> List[str]:
        """Get strategies to avoid in current phase."""
        return FRACTAL_PHASE_STRATEGY_MAP.get(self.phase, {}).get("anti", [])
    
    def get_regime_hint(self) -> str:
        """Get regime hint from fractal phase."""
        return FRACTAL_PHASE_STRATEGY_MAP.get(self.phase, {}).get("regime_hint", "undefined")


# ══════════════════════════════════════════════════════════════
# FRACTAL HINT SCORE
# ══════════════════════════════════════════════════════════════

@dataclass
class FractalHintScore:
    """
    Computed fractal hint score for a strategy.
    
    Score range: 0.0 to 1.0
    Weight in regime: 0.10 (10%)
    """
    strategy_name: str
    fractal_score: float = 0.5  # Neutral default
    
    # Breakdown
    phase_alignment: float = 0.0  # How well phase aligns with strategy
    direction_alignment: float = 0.0  # How well direction aligns
    strength_factor: float = 0.0  # Fractal strength contribution
    
    # Metadata
    phase: str = "UNKNOWN"
    is_supported: bool = False
    is_anti: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "strategy_name": self.strategy_name,
            "fractal_score": round(self.fractal_score, 4),
            "breakdown": {
                "phase_alignment": round(self.phase_alignment, 4),
                "direction_alignment": round(self.direction_alignment, 4),
                "strength_factor": round(self.strength_factor, 4),
            },
            "phase": self.phase,
            "is_supported": self.is_supported,
            "is_anti": self.is_anti,
        }


# ══════════════════════════════════════════════════════════════
# UPDATED REGIME CONFIDENCE WEIGHTS WITH FRACTAL
# ══════════════════════════════════════════════════════════════

# Original weights (PHASE 19.3):
# regime: 0.40, volatility: 0.20, breadth: 0.15, interaction: 0.15, ecology: 0.10

# New weights with fractal (≤10% for fractal):
REGIME_CONFIDENCE_WEIGHTS_WITH_FRACTAL = {
    "regime": 0.38,       # -0.02
    "volatility": 0.18,   # -0.02
    "breadth": 0.14,      # -0.01
    "interaction": 0.14,  # -0.01
    "ecology": 0.08,      # -0.02
    "fractal": 0.08,      # NEW: 8% (conservative, ≤10%)
}

# Validation: sum should be ~1.0
assert abs(sum(REGIME_CONFIDENCE_WEIGHTS_WITH_FRACTAL.values()) - 1.0) < 0.01
