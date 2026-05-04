"""
PHASE 25.3 — Macro → DXY Bridge

Bridge 1: How macro regime influences DXY (US Dollar Index).

Causality:
- TIGHTENING / RISK_OFF / STAGFLATION → Bullish USD → Long DXY
- EASING / RISK_ON → Bearish USD → Short DXY
"""

from typing import Optional

from .cross_asset_types import (
    CrossAssetBridge,
    AlignmentType,
    InfluenceDirection,
    ALIGNMENT_MULTIPLIERS,
)
from modules.macro_context.macro_context_types import MacroContext
from modules.fractal_intelligence.asset_fractal_types import AssetFractalContext


class MacroDxyBridge:
    """
    Bridge engine for Macro → DXY causality.
    
    Macro regime (rates, inflation, liquidity) directly affects USD strength.
    """
    
    # Macro states that support bullish USD
    USD_BULLISH_STATES = {"TIGHTENING", "RISK_OFF", "STAGFLATION"}
    
    # Macro states that support bearish USD
    USD_BEARISH_STATES = {"EASING", "RISK_ON"}
    
    def compute(
        self,
        macro: MacroContext,
        dxy: AssetFractalContext,
    ) -> CrossAssetBridge:
        """
        Compute Macro → DXY bridge.
        
        Args:
            macro: MacroContext from macro_context module
            dxy: DXY AssetFractalContext
        
        Returns:
            CrossAssetBridge with alignment and strength
        """
        
        # Determine expected DXY direction from macro
        macro_usd_bullish = (
            macro.macro_state in self.USD_BULLISH_STATES or
            macro.usd_bias == "BULLISH"
        )
        macro_usd_bearish = (
            macro.macro_state in self.USD_BEARISH_STATES or
            macro.usd_bias == "BEARISH"
        )
        
        # DXY fractal direction
        dxy_bullish = dxy.direction == "LONG"
        dxy_bearish = dxy.direction == "SHORT"
        dxy_neutral = dxy.direction == "HOLD"
        
        # Determine alignment
        alignment, influence_direction = self._compute_alignment(
            macro_usd_bullish, macro_usd_bearish,
            dxy_bullish, dxy_bearish, dxy_neutral,
            macro.context_state, dxy.context_state,
        )
        
        # Compute strength
        strength = self._compute_strength(macro, dxy)
        
        # Compute confidence
        confidence = self._compute_confidence(macro, dxy)
        
        # Effective strength with alignment penalty
        multiplier = ALIGNMENT_MULTIPLIERS.get(alignment, 0.5)
        effective_strength = round(strength * multiplier, 4)
        
        # Generate reason
        reason = self._generate_reason(
            macro, dxy, alignment, influence_direction
        )
        
        return CrossAssetBridge(
            source="MACRO",
            target="DXY",
            alignment=alignment,
            influence_direction=influence_direction,
            strength=round(strength, 4),
            confidence=round(confidence, 4),
            effective_strength=effective_strength,
            reason=reason,
        )
    
    def _compute_alignment(
        self,
        macro_usd_bullish: bool,
        macro_usd_bearish: bool,
        dxy_bullish: bool,
        dxy_bearish: bool,
        dxy_neutral: bool,
        macro_state: str,
        dxy_state: str,
    ) -> tuple[AlignmentType, InfluenceDirection]:
        """Compute alignment and influence direction."""
        
        # Handle blocked/neutral states
        if macro_state == "BLOCKED" or dxy_state == "BLOCKED":
            return "NEUTRAL", "NEUTRAL"
        
        if dxy_neutral:
            if macro_usd_bullish:
                return "NEUTRAL", "BULLISH"
            elif macro_usd_bearish:
                return "NEUTRAL", "BEARISH"
            return "NEUTRAL", "NEUTRAL"
        
        # SUPPORTIVE: Macro and DXY agree
        if macro_usd_bullish and dxy_bullish:
            return "SUPPORTIVE", "BULLISH"
        
        if macro_usd_bearish and dxy_bearish:
            return "SUPPORTIVE", "BEARISH"
        
        # CONTRARY: Macro and DXY disagree
        if macro_usd_bullish and dxy_bearish:
            return "CONTRARY", "BULLISH"  # Macro says bullish but DXY is bearish
        
        if macro_usd_bearish and dxy_bullish:
            return "CONTRARY", "BEARISH"  # Macro says bearish but DXY is bullish
        
        # MIXED: Partial signals
        if macro_usd_bullish or dxy_bullish:
            return "MIXED", "BULLISH"
        
        if macro_usd_bearish or dxy_bearish:
            return "MIXED", "BEARISH"
        
        return "NEUTRAL", "NEUTRAL"
    
    def _compute_strength(
        self,
        macro: MacroContext,
        dxy: AssetFractalContext,
    ) -> float:
        """
        Compute bridge strength.
        
        Formula: 0.45 * macro.macro_strength + 0.35 * dxy.strength + 0.20 * min_conf
        """
        min_conf = min(macro.confidence, dxy.confidence)
        
        strength = (
            0.45 * macro.macro_strength +
            0.35 * dxy.strength +
            0.20 * min_conf
        )
        
        return max(0.0, min(1.0, strength))
    
    def _compute_confidence(
        self,
        macro: MacroContext,
        dxy: AssetFractalContext,
    ) -> float:
        """Compute bridge confidence."""
        return (macro.confidence + dxy.confidence) / 2
    
    def _generate_reason(
        self,
        macro: MacroContext,
        dxy: AssetFractalContext,
        alignment: AlignmentType,
        influence_direction: InfluenceDirection,
    ) -> str:
        """Generate human-readable explanation."""
        
        macro_desc = macro.macro_state.lower().replace("_", " ")
        usd_desc = macro.usd_bias.lower()
        dxy_desc = dxy.direction.lower()
        
        if alignment == "SUPPORTIVE":
            return f"{macro_desc} macro supports {usd_desc} dollar and dxy fractal confirms with {dxy_desc} signal"
        
        if alignment == "CONTRARY":
            return f"{macro_desc} macro suggests {usd_desc} dollar but dxy fractal shows {dxy_desc} - signals conflict"
        
        if alignment == "MIXED":
            return f"{macro_desc} macro with {usd_desc} usd bias partially aligns with dxy {dxy_desc}"
        
        return f"macro {macro_desc} with neutral dxy fractal signal"


# Singleton
_bridge: Optional[MacroDxyBridge] = None

def get_macro_dxy_bridge() -> MacroDxyBridge:
    global _bridge
    if _bridge is None:
        _bridge = MacroDxyBridge()
    return _bridge
