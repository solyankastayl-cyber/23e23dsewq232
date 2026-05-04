"""
PHASE 14.8 — Market Structure Engine
=====================================
Combined dominance + breadth with trading influence modifiers.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.market_structure.breadth_dominance.dominance_types import (
    MarketStructureState,
    MarketDominanceState,
    MarketBreadthState,
    DominanceRegime,
    RotationState,
    BreadthState,
)
from modules.market_structure.breadth_dominance.dominance_engine import get_dominance_engine
from modules.market_structure.breadth_dominance.breadth_engine import get_breadth_engine


# ══════════════════════════════════════════════════════════════
# INFLUENCE MODIFIERS
# ══════════════════════════════════════════════════════════════

# Confidence modifiers based on dominance regime
DOMINANCE_MODIFIERS = {
    # When BTC dominant
    DominanceRegime.BTC_DOM: {
        "btc": 1.15,   # BTC trades get confidence boost
        "eth": 0.95,   # ETH slightly penalized
        "alt": 0.85,   # Alts more penalized
    },
    # When ETH dominant
    DominanceRegime.ETH_DOM: {
        "btc": 1.0,
        "eth": 1.15,
        "alt": 1.05,
    },
    # When alts dominant
    DominanceRegime.ALT_DOM: {
        "btc": 0.90,
        "eth": 1.05,
        "alt": 1.20,
    },
    # Balanced
    DominanceRegime.BALANCED: {
        "btc": 1.0,
        "eth": 1.0,
        "alt": 1.0,
    },
}

# Size modifier based on breadth
BREADTH_SIZE_MODIFIERS = {
    BreadthState.STRONG: 1.10,   # Can size up
    BreadthState.MIXED: 1.0,    # Normal
    BreadthState.WEAK: 0.80,    # Size down
}

# Rotation modifiers (add to existing)
ROTATION_MODIFIERS = {
    RotationState.ROTATING_TO_BTC: {"btc": 1.1, "alt": 0.85},
    RotationState.ROTATING_TO_ALTS: {"btc": 0.9, "alt": 1.15},
    RotationState.ROTATING_TO_ETH: {"eth": 1.1},
    RotationState.EXITING_MARKET: {"btc": 0.7, "eth": 0.7, "alt": 0.6},
    RotationState.STABLE: {},
}


class MarketStructureEngine:
    """
    Combined market structure engine.
    
    Computes dominance + breadth and influence modifiers.
    """
    
    def __init__(self):
        self.dominance_engine = get_dominance_engine()
        self.breadth_engine = get_breadth_engine()
    
    def compute(self) -> MarketStructureState:
        """
        Compute full market structure state.
        """
        now = datetime.now(timezone.utc)
        
        # Get dominance and breadth
        dominance = self.dominance_engine.compute()
        breadth = self.breadth_engine.compute()
        
        # Compute influence modifiers
        btc_mod, eth_mod, alt_mod = self._compute_confidence_modifiers(
            dominance, breadth
        )
        size_mod = self._compute_size_modifier(breadth, dominance)
        
        # Determine overall quality
        quality = self._determine_structure_quality(dominance, breadth)
        
        return MarketStructureState(
            timestamp=now,
            dominance=dominance,
            breadth=breadth,
            btc_confidence_modifier=btc_mod,
            eth_confidence_modifier=eth_mod,
            alt_confidence_modifier=alt_mod,
            size_modifier=size_mod,
            market_structure_quality=quality,
        )
    
    def get_modifier_for_symbol(self, symbol: str) -> Dict[str, float]:
        """
        Get trading modifiers for specific symbol.
        
        Returns confidence and size modifiers.
        """
        state = self.compute()
        
        # Determine asset class
        if symbol == "BTC":
            conf_mod = state.btc_confidence_modifier
        elif symbol == "ETH":
            conf_mod = state.eth_confidence_modifier
        else:
            conf_mod = state.alt_confidence_modifier
        
        return {
            "confidence_modifier": conf_mod,
            "size_modifier": state.size_modifier,
            "dominance_regime": state.dominance.dominance_regime.value,
            "breadth_state": state.breadth.breadth_state.value,
            "rotation_state": state.dominance.rotation_state.value,
        }
    
    def _compute_confidence_modifiers(
        self,
        dominance: MarketDominanceState,
        breadth: MarketBreadthState,
    ) -> tuple:
        """Compute confidence modifiers for BTC, ETH, ALT."""
        regime = dominance.dominance_regime
        rotation = dominance.rotation_state
        
        # Base modifiers from regime
        base = DOMINANCE_MODIFIERS.get(regime, DOMINANCE_MODIFIERS[DominanceRegime.BALANCED])
        btc_mod = base["btc"]
        eth_mod = base["eth"]
        alt_mod = base["alt"]
        
        # Apply rotation modifiers
        rot_mods = ROTATION_MODIFIERS.get(rotation, {})
        btc_mod *= rot_mods.get("btc", 1.0)
        eth_mod *= rot_mods.get("eth", 1.0)
        alt_mod *= rot_mods.get("alt", 1.0)
        
        # Breadth penalty for all if weak
        if breadth.breadth_state == BreadthState.WEAK:
            btc_mod *= 0.95
            eth_mod *= 0.92
            alt_mod *= 0.88
        
        return (btc_mod, eth_mod, alt_mod)
    
    def _compute_size_modifier(
        self,
        breadth: MarketBreadthState,
        dominance: MarketDominanceState,
    ) -> float:
        """Compute overall size modifier."""
        # Base from breadth
        size_mod = BREADTH_SIZE_MODIFIERS.get(breadth.breadth_state, 1.0)
        
        # Additional penalty if exiting market
        if dominance.rotation_state == RotationState.EXITING_MARKET:
            size_mod *= 0.6
        
        # Bonus for strong participation
        if breadth.trend_participation > 0.7:
            size_mod *= 1.05
        elif breadth.trend_participation < 0.4:
            size_mod *= 0.90
        
        return size_mod
    
    def _determine_structure_quality(
        self,
        dominance: MarketDominanceState,
        breadth: MarketBreadthState,
    ) -> str:
        """Determine overall market structure quality."""
        score = 0
        
        # Breadth contribution
        if breadth.breadth_state == BreadthState.STRONG:
            score += 2
        elif breadth.breadth_state == BreadthState.WEAK:
            score -= 2
        
        # Participation contribution
        if breadth.trend_participation > 0.7:
            score += 1
        elif breadth.trend_participation < 0.4:
            score -= 1
        
        # Rotation contribution
        if dominance.rotation_state == RotationState.STABLE:
            score += 1
        elif dominance.rotation_state == RotationState.EXITING_MARKET:
            score -= 3
        
        # Flow strength contribution
        if dominance.capital_flow_strength > 0.7:
            score += 1
        
        # Determine quality
        if score >= 3:
            return "FAVORABLE"
        elif score <= -2:
            return "UNFAVORABLE"
        else:
            return "NEUTRAL"


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[MarketStructureEngine] = None


def get_market_structure_engine() -> MarketStructureEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = MarketStructureEngine()
    return _engine
