"""
PHASE 14.8 — Dominance & Breadth Types
=======================================
Market structure contracts for capital distribution analysis.

This layer answers:
- Is capital in BTC, ETH, or alts?
- Is capital rotating?
- Is the market trend broad or narrow?
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# DOMINANCE ENUMS
# ══════════════════════════════════════════════════════════════

class DominanceRegime(str, Enum):
    """Market dominance regime."""
    BTC_DOM = "BTC_DOM"        # Bitcoin dominant
    ETH_DOM = "ETH_DOM"        # Ethereum dominant
    ALT_DOM = "ALT_DOM"        # Altcoins dominant
    BALANCED = "BALANCED"      # No clear dominance


class RotationState(str, Enum):
    """Capital rotation state."""
    ROTATING_TO_BTC = "ROTATING_TO_BTC"
    ROTATING_TO_ETH = "ROTATING_TO_ETH"
    ROTATING_TO_ALTS = "ROTATING_TO_ALTS"
    STABLE = "STABLE"
    EXITING_MARKET = "EXITING_MARKET"


class BreadthState(str, Enum):
    """Market breadth state."""
    STRONG = "STRONG"    # Broad participation
    WEAK = "WEAK"        # Narrow participation
    MIXED = "MIXED"      # Unclear


# ══════════════════════════════════════════════════════════════
# DOMINANCE CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class MarketDominanceState:
    """
    Market dominance state.
    
    Tracks capital distribution across BTC, ETH, and alts.
    """
    timestamp: datetime
    
    # Raw dominance percentages
    btc_dominance: float  # e.g., 52.4%
    eth_dominance: float  # e.g., 17.2%
    alt_dominance: float  # e.g., 30.4%
    
    # Derived states
    dominance_regime: DominanceRegime
    rotation_state: RotationState
    capital_flow_strength: float  # 0..1
    
    # Trend data
    btc_dom_change_24h: float  # +/- percentage points
    eth_dom_change_24h: float
    alt_dom_change_24h: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "btc_dominance": round(self.btc_dominance, 2),
            "eth_dominance": round(self.eth_dominance, 2),
            "alt_dominance": round(self.alt_dominance, 2),
            "dominance_regime": self.dominance_regime.value,
            "rotation_state": self.rotation_state.value,
            "capital_flow_strength": round(self.capital_flow_strength, 4),
            "btc_dom_change_24h": round(self.btc_dom_change_24h, 2),
            "eth_dom_change_24h": round(self.eth_dom_change_24h, 2),
            "alt_dom_change_24h": round(self.alt_dom_change_24h, 2),
        }


# ══════════════════════════════════════════════════════════════
# BREADTH CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class MarketBreadthState:
    """
    Market breadth state.
    
    Tracks how broad or narrow market participation is.
    """
    timestamp: datetime
    
    # Raw counts
    advancing_assets: int
    declining_assets: int
    unchanged_assets: int
    
    # Derived metrics
    breadth_ratio: float  # advancing / declining
    breadth_state: BreadthState
    trend_participation: float  # 0..1, what % of assets follow the trend
    
    # Additional metrics
    new_highs: int
    new_lows: int
    above_20d_ma: int
    below_20d_ma: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "advancing_assets": self.advancing_assets,
            "declining_assets": self.declining_assets,
            "unchanged_assets": self.unchanged_assets,
            "breadth_ratio": round(self.breadth_ratio, 4),
            "breadth_state": self.breadth_state.value,
            "trend_participation": round(self.trend_participation, 4),
            "new_highs": self.new_highs,
            "new_lows": self.new_lows,
            "above_20d_ma": self.above_20d_ma,
            "below_20d_ma": self.below_20d_ma,
        }


# ══════════════════════════════════════════════════════════════
# COMBINED MARKET STRUCTURE STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class MarketStructureState:
    """
    Combined market structure state.
    
    Merges dominance and breadth into unified view.
    """
    timestamp: datetime
    
    # Dominance
    dominance: MarketDominanceState
    
    # Breadth
    breadth: MarketBreadthState
    
    # Influence modifiers for trading
    btc_confidence_modifier: float  # Multiply BTC trade confidence
    eth_confidence_modifier: float
    alt_confidence_modifier: float
    size_modifier: float  # Overall size adjustment
    
    # Summary
    market_structure_quality: str  # FAVORABLE / NEUTRAL / UNFAVORABLE
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "dominance": self.dominance.to_dict(),
            "breadth": self.breadth.to_dict(),
            "btc_confidence_modifier": round(self.btc_confidence_modifier, 4),
            "eth_confidence_modifier": round(self.eth_confidence_modifier, 4),
            "alt_confidence_modifier": round(self.alt_confidence_modifier, 4),
            "size_modifier": round(self.size_modifier, 4),
            "market_structure_quality": self.market_structure_quality,
        }
    
    def to_summary_dict(self) -> Dict:
        """Condensed summary."""
        return {
            "dominance_regime": self.dominance.dominance_regime.value,
            "rotation_state": self.dominance.rotation_state.value,
            "breadth_state": self.breadth.breadth_state.value,
            "btc_dom": round(self.dominance.btc_dominance, 1),
            "structure_quality": self.market_structure_quality,
        }
