"""
PHASE 25.3 — SPX → BTC Bridge

Bridge 3: How SPX (S&P 500) influences BTC (Bitcoin).

Causality (risk appetite correlation):
- SPX bullish (risk-on) → Bullish support for BTC
- SPX bearish (risk-off) → Bearish pressure on BTC
"""

from typing import Optional

from .cross_asset_types import (
    CrossAssetBridge,
    AlignmentType,
    InfluenceDirection,
    ALIGNMENT_MULTIPLIERS,
)
from modules.fractal_intelligence.asset_fractal_types import AssetFractalContext


class SpxBtcBridge:
    """
    Bridge engine for SPX → BTC causality.
    
    Key principle: SPX and BTC have POSITIVE correlation (risk appetite).
    - Risk-on (SPX bullish) → BTC bullish
    - Risk-off (SPX bearish) → BTC bearish
    """
    
    def compute(
        self,
        spx: AssetFractalContext,
        btc: AssetFractalContext,
    ) -> CrossAssetBridge:
        """
        Compute SPX → BTC bridge.
        
        Args:
            spx: SPX AssetFractalContext
            btc: BTC AssetFractalContext
        
        Returns:
            CrossAssetBridge with alignment and strength
        """
        
        # SPX direction
        spx_bullish = spx.direction == "LONG"
        spx_bearish = spx.direction == "SHORT"
        spx_neutral = spx.direction == "HOLD"
        
        # BTC direction
        btc_bullish = btc.direction == "LONG"
        btc_bearish = btc.direction == "SHORT"
        btc_neutral = btc.direction == "HOLD"
        
        # Determine alignment (positive correlation)
        alignment, influence_direction = self._compute_alignment(
            spx_bullish, spx_bearish, spx_neutral,
            btc_bullish, btc_bearish, btc_neutral,
            spx.context_state, btc.context_state,
        )
        
        # Compute strength
        strength = self._compute_strength(spx, btc)
        
        # Compute confidence
        confidence = self._compute_confidence(spx, btc)
        
        # Effective strength with alignment penalty
        multiplier = ALIGNMENT_MULTIPLIERS.get(alignment, 0.5)
        effective_strength = round(strength * multiplier, 4)
        
        # Generate reason
        reason = self._generate_reason(
            spx, btc, alignment, influence_direction
        )
        
        return CrossAssetBridge(
            source="SPX",
            target="BTC",
            alignment=alignment,
            influence_direction=influence_direction,
            strength=round(strength, 4),
            confidence=round(confidence, 4),
            effective_strength=effective_strength,
            reason=reason,
        )
    
    def _compute_alignment(
        self,
        spx_bullish: bool,
        spx_bearish: bool,
        spx_neutral: bool,
        btc_bullish: bool,
        btc_bearish: bool,
        btc_neutral: bool,
        spx_state: str,
        btc_state: str,
    ) -> tuple[AlignmentType, InfluenceDirection]:
        """
        Compute alignment and influence direction.
        
        POSITIVE correlation (risk appetite):
        - SPX long + BTC long → SUPPORTIVE bullish
        - SPX short + BTC short → SUPPORTIVE bearish
        - SPX long + BTC short → CONTRARY (risk-on but BTC bearish)
        - SPX short + BTC long → CONTRARY (risk-off but BTC bullish)
        """
        
        # Handle blocked states
        if spx_state == "BLOCKED" or btc_state == "BLOCKED":
            return "NEUTRAL", "NEUTRAL"
        
        # Handle neutral cases
        if spx_neutral and btc_neutral:
            return "NEUTRAL", "NEUTRAL"
        
        if spx_neutral:
            if btc_bullish:
                return "NEUTRAL", "BULLISH"
            elif btc_bearish:
                return "NEUTRAL", "BEARISH"
            return "NEUTRAL", "NEUTRAL"
        
        if btc_neutral:
            if spx_bullish:
                return "NEUTRAL", "BULLISH"
            elif spx_bearish:
                return "NEUTRAL", "BEARISH"
            return "NEUTRAL", "NEUTRAL"
        
        # SUPPORTIVE: Positive correlation confirmed (same direction)
        # Both bullish → risk-on alignment
        if spx_bullish and btc_bullish:
            return "SUPPORTIVE", "BULLISH"
        
        # Both bearish → risk-off alignment
        if spx_bearish and btc_bearish:
            return "SUPPORTIVE", "BEARISH"
        
        # CONTRARY: Opposite directions (breaks correlation)
        if spx_bullish and btc_bearish:
            return "CONTRARY", "BULLISH"  # SPX says risk-on, BTC disagrees
        
        if spx_bearish and btc_bullish:
            return "CONTRARY", "BEARISH"  # SPX says risk-off, BTC disagrees
        
        return "MIXED", "NEUTRAL"
    
    def _compute_strength(
        self,
        spx: AssetFractalContext,
        btc: AssetFractalContext,
    ) -> float:
        """
        Compute bridge strength.
        
        Formula: 0.45 * spx.strength + 0.40 * btc.strength + 0.15 * min_conf
        """
        min_conf = min(spx.confidence, btc.confidence)
        
        strength = (
            0.45 * spx.strength +
            0.40 * btc.strength +
            0.15 * min_conf
        )
        
        return max(0.0, min(1.0, strength))
    
    def _compute_confidence(
        self,
        spx: AssetFractalContext,
        btc: AssetFractalContext,
    ) -> float:
        """Compute bridge confidence."""
        return (spx.confidence + btc.confidence) / 2
    
    def _generate_reason(
        self,
        spx: AssetFractalContext,
        btc: AssetFractalContext,
        alignment: AlignmentType,
        influence_direction: InfluenceDirection,
    ) -> str:
        """Generate human-readable explanation."""
        
        spx_desc = spx.direction.lower()
        btc_desc = btc.direction.lower()
        
        if alignment == "SUPPORTIVE":
            if influence_direction == "BULLISH":
                return f"bullish spx risk-on regime aligns with bullish btc fractal"
            else:
                return f"bearish spx risk-off regime aligns with bearish btc fractal"
        
        if alignment == "CONTRARY":
            return f"spx {spx_desc} and btc {btc_desc} diverge - risk appetite correlation broken"
        
        if alignment == "MIXED":
            return f"spx {spx_desc} with partial btc {btc_desc} alignment"
        
        return f"neutral cross-asset signal between spx and btc"


# Singleton
_bridge: Optional[SpxBtcBridge] = None

def get_spx_btc_bridge() -> SpxBtcBridge:
    global _bridge
    if _bridge is None:
        _bridge = SpxBtcBridge()
    return _bridge
