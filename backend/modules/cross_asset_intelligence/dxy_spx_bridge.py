"""
PHASE 25.3 — DXY → SPX Bridge

Bridge 2: How DXY (US Dollar Index) influences SPX (S&P 500).

Causality (inverse relationship):
- DXY bullish (strong dollar) → Bearish pressure on SPX
- DXY bearish (weak dollar) → Bullish support for SPX
"""

from typing import Optional

from .cross_asset_types import (
    CrossAssetBridge,
    AlignmentType,
    InfluenceDirection,
    ALIGNMENT_MULTIPLIERS,
)
from modules.fractal_intelligence.asset_fractal_types import AssetFractalContext


class DxySpxBridge:
    """
    Bridge engine for DXY → SPX causality.
    
    Key principle: DXY and SPX have INVERSE relationship.
    - Strong dollar → multinational earnings hurt → SPX pressure
    - Weak dollar → exports benefit → SPX support
    """
    
    def compute(
        self,
        dxy: AssetFractalContext,
        spx: AssetFractalContext,
    ) -> CrossAssetBridge:
        """
        Compute DXY → SPX bridge.
        
        Args:
            dxy: DXY AssetFractalContext
            spx: SPX AssetFractalContext
        
        Returns:
            CrossAssetBridge with alignment and strength
        """
        
        # DXY direction
        dxy_bullish = dxy.direction == "LONG"
        dxy_bearish = dxy.direction == "SHORT"
        dxy_neutral = dxy.direction == "HOLD"
        
        # SPX direction
        spx_bullish = spx.direction == "LONG"
        spx_bearish = spx.direction == "SHORT"
        spx_neutral = spx.direction == "HOLD"
        
        # Determine alignment (inverse relationship)
        alignment, influence_direction = self._compute_alignment(
            dxy_bullish, dxy_bearish, dxy_neutral,
            spx_bullish, spx_bearish, spx_neutral,
            dxy.context_state, spx.context_state,
        )
        
        # Compute strength
        strength = self._compute_strength(dxy, spx)
        
        # Compute confidence
        confidence = self._compute_confidence(dxy, spx)
        
        # Effective strength with alignment penalty
        multiplier = ALIGNMENT_MULTIPLIERS.get(alignment, 0.5)
        effective_strength = round(strength * multiplier, 4)
        
        # Generate reason
        reason = self._generate_reason(
            dxy, spx, alignment, influence_direction
        )
        
        return CrossAssetBridge(
            source="DXY",
            target="SPX",
            alignment=alignment,
            influence_direction=influence_direction,
            strength=round(strength, 4),
            confidence=round(confidence, 4),
            effective_strength=effective_strength,
            reason=reason,
        )
    
    def _compute_alignment(
        self,
        dxy_bullish: bool,
        dxy_bearish: bool,
        dxy_neutral: bool,
        spx_bullish: bool,
        spx_bearish: bool,
        spx_neutral: bool,
        dxy_state: str,
        spx_state: str,
    ) -> tuple[AlignmentType, InfluenceDirection]:
        """
        Compute alignment and influence direction.
        
        INVERSE relationship:
        - DXY long + SPX short → SUPPORTIVE (expected bearish chain)
        - DXY short + SPX long → SUPPORTIVE (expected bullish chain)
        - DXY long + SPX long → CONTRARY (should be inverse)
        - DXY short + SPX short → CONTRARY (should be inverse)
        """
        
        # Handle blocked states
        if dxy_state == "BLOCKED" or spx_state == "BLOCKED":
            return "NEUTRAL", "NEUTRAL"
        
        # Handle neutral cases
        if dxy_neutral and spx_neutral:
            return "NEUTRAL", "NEUTRAL"
        
        if dxy_neutral:
            if spx_bullish:
                return "NEUTRAL", "BULLISH"
            elif spx_bearish:
                return "NEUTRAL", "BEARISH"
            return "NEUTRAL", "NEUTRAL"
        
        if spx_neutral:
            # DXY bullish implies bearish SPX pressure
            if dxy_bullish:
                return "NEUTRAL", "BEARISH"
            elif dxy_bearish:
                return "NEUTRAL", "BULLISH"
            return "NEUTRAL", "NEUTRAL"
        
        # SUPPORTIVE: Inverse relationship confirmed
        # DXY bullish → expects SPX bearish (strong dollar hurts equities)
        if dxy_bullish and spx_bearish:
            return "SUPPORTIVE", "BEARISH"
        
        # DXY bearish → expects SPX bullish (weak dollar helps equities)
        if dxy_bearish and spx_bullish:
            return "SUPPORTIVE", "BULLISH"
        
        # CONTRARY: Same direction (unexpected - breaks inverse relationship)
        if dxy_bullish and spx_bullish:
            return "CONTRARY", "BULLISH"  # Unusual - both bullish
        
        if dxy_bearish and spx_bearish:
            return "CONTRARY", "BEARISH"  # Unusual - both bearish
        
        return "MIXED", "NEUTRAL"
    
    def _compute_strength(
        self,
        dxy: AssetFractalContext,
        spx: AssetFractalContext,
    ) -> float:
        """
        Compute bridge strength.
        
        Formula: 0.50 * dxy.strength + 0.35 * spx.strength + 0.15 * min_conf
        """
        min_conf = min(dxy.confidence, spx.confidence)
        
        strength = (
            0.50 * dxy.strength +
            0.35 * spx.strength +
            0.15 * min_conf
        )
        
        return max(0.0, min(1.0, strength))
    
    def _compute_confidence(
        self,
        dxy: AssetFractalContext,
        spx: AssetFractalContext,
    ) -> float:
        """Compute bridge confidence."""
        return (dxy.confidence + spx.confidence) / 2
    
    def _generate_reason(
        self,
        dxy: AssetFractalContext,
        spx: AssetFractalContext,
        alignment: AlignmentType,
        influence_direction: InfluenceDirection,
    ) -> str:
        """Generate human-readable explanation."""
        
        dxy_desc = dxy.direction.lower()
        spx_desc = spx.direction.lower()
        
        if alignment == "SUPPORTIVE":
            if influence_direction == "BEARISH":
                return f"bullish dxy implies bearish pressure on spx and spx fractal confirms with {spx_desc} signal"
            else:
                return f"bearish dxy supports bullish spx and spx fractal confirms with {spx_desc} signal"
        
        if alignment == "CONTRARY":
            return f"dxy {dxy_desc} and spx {spx_desc} both point same direction - breaks inverse relationship"
        
        if alignment == "MIXED":
            return f"dxy {dxy_desc} with partial spx {spx_desc} alignment"
        
        return f"neutral cross-asset signal between dxy and spx"


# Singleton
_bridge: Optional[DxySpxBridge] = None

def get_dxy_spx_bridge() -> DxySpxBridge:
    global _bridge
    if _bridge is None:
        _bridge = DxySpxBridge()
    return _bridge
