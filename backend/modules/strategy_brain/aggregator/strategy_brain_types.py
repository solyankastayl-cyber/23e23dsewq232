"""
PHASE 19.4 — Strategy Brain Aggregator Types
============================================
Type definitions for Strategy Brain Aggregator.

Core contracts:
- StrategyBrainState: Unified strategy overlay state
- StrategyOverlayEffect: Overlay effect enum
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# STRATEGY OVERLAY EFFECT
# ══════════════════════════════════════════════════════════════

class StrategyOverlayEffect(str, Enum):
    """Strategy overlay effect on trading."""
    SUPPORTIVE = "SUPPORTIVE"      # Strong primary, boost modifiers
    NEUTRAL = "NEUTRAL"            # Mixed strategies, no adjustment
    RESTRICTIVE = "RESTRICTIVE"    # Fragmented/unclear, reduce modifiers


# ══════════════════════════════════════════════════════════════
# RECOMMENDED BIAS
# ══════════════════════════════════════════════════════════════

class RecommendedBias(str, Enum):
    """Recommended strategy bias."""
    TREND = "TREND"
    MR = "MR"                      # Mean Reversion
    BREAKOUT = "BREAKOUT"
    SQUEEZE = "SQUEEZE"
    FLOW = "FLOW"
    VOL = "VOL"                    # Volatility
    ARB = "ARB"                    # Arbitrage
    REVERSAL = "REVERSAL"
    MIXED = "MIXED"


# Strategy to bias mapping
STRATEGY_BIAS_MAP = {
    "trend_following": RecommendedBias.TREND,
    "mean_reversion": RecommendedBias.MR,
    "breakout": RecommendedBias.BREAKOUT,
    "liquidation_capture": RecommendedBias.SQUEEZE,
    "flow_following": RecommendedBias.FLOW,
    "volatility_expansion": RecommendedBias.VOL,
    "funding_arb": RecommendedBias.ARB,
    "structure_reversal": RecommendedBias.REVERSAL,
}


# ══════════════════════════════════════════════════════════════
# MODIFIER BOUNDS
# ══════════════════════════════════════════════════════════════

CONFIDENCE_MODIFIER_MIN = 0.80
CONFIDENCE_MODIFIER_MAX = 1.20
CAPITAL_MODIFIER_MIN = 0.75
CAPITAL_MODIFIER_MAX = 1.25


# ══════════════════════════════════════════════════════════════
# STRATEGY BRAIN STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class StrategyBrainState:
    """
    Unified Strategy Brain state.
    
    Aggregates state, allocation, and regime priority
    into a single overlay for Trading Product.
    """
    # Regime
    market_regime: str
    regime_confidence: float
    
    # Strategy lists
    active_strategies: List[str]
    reduced_strategies: List[str]
    disabled_strategies: List[str]
    
    # Priority
    primary_strategy: str
    secondary_strategies: List[str]
    
    # Allocations
    allocations: Dict[str, float]
    
    # Modifiers
    confidence_modifier: float
    capital_modifier: float
    
    # Overlay
    strategy_overlay_effect: StrategyOverlayEffect
    recommended_bias: RecommendedBias
    reason: str
    
    # Counts
    active_count: int = 0
    reduced_count: int = 0
    disabled_count: int = 0
    
    # Breakdown scores
    primary_confidence_score: float = 0.0
    active_avg_modifier: float = 0.0
    regime_normalized: float = 0.0
    allocation_normalized: float = 0.0
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "market_regime": self.market_regime,
            "regime_confidence": round(self.regime_confidence, 4),
            "active_strategies": self.active_strategies,
            "reduced_strategies": self.reduced_strategies,
            "disabled_strategies": self.disabled_strategies,
            "primary_strategy": self.primary_strategy,
            "secondary_strategies": self.secondary_strategies,
            "allocations": {k: round(v, 4) for k, v in self.allocations.items()},
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "strategy_overlay_effect": self.strategy_overlay_effect.value,
            "recommended_bias": self.recommended_bias.value,
            "reason": self.reason,
            "counts": {
                "active": self.active_count,
                "reduced": self.reduced_count,
                "disabled": self.disabled_count,
            },
            "breakdown": {
                "primary_confidence_score": round(self.primary_confidence_score, 4),
                "active_avg_modifier": round(self.active_avg_modifier, 4),
                "regime_normalized": round(self.regime_normalized, 4),
                "allocation_normalized": round(self.allocation_normalized, 4),
            },
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary for Trading Product integration."""
        return {
            "regime": self.market_regime,
            "primary": self.primary_strategy,
            "bias": self.recommended_bias.value,
            "overlay_effect": self.strategy_overlay_effect.value,
            "conf_mod": round(self.confidence_modifier, 4),
            "cap_mod": round(self.capital_modifier, 4),
        }
    
    def to_trading_product_block(self) -> Dict[str, Any]:
        """Format for Trading Product snapshot integration."""
        return {
            "strategy_brain": {
                "market_regime": self.market_regime,
                "regime_confidence": round(self.regime_confidence, 4),
                "primary_strategy": self.primary_strategy,
                "recommended_bias": self.recommended_bias.value,
                "strategy_overlay_effect": self.strategy_overlay_effect.value,
                "confidence_modifier": round(self.confidence_modifier, 4),
                "capital_modifier": round(self.capital_modifier, 4),
                "active_count": self.active_count,
                "allocations_top3": dict(
                    sorted(self.allocations.items(), key=lambda x: x[1], reverse=True)[:3]
                ),
            }
        }
