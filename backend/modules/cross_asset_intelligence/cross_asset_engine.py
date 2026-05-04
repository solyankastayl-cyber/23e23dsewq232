"""
PHASE 25.3 — Cross-Asset Engine

Aggregates all three bridges into unified CrossAssetAlignment.
Computes alignment score, final bias, and dominant/weakest bridges.
"""

from typing import Optional
from datetime import datetime

from .cross_asset_types import (
    CrossAssetBridge,
    CrossAssetAlignment,
    CrossAssetSummary,
    CrossAssetHealthStatus,
    AlignmentStateType,
    FinalBiasType,
    ALIGNMENT_STATE_THRESHOLDS,
    BRIDGE_WEIGHTS,
)
from .macro_dxy_bridge import MacroDxyBridge, get_macro_dxy_bridge
from .dxy_spx_bridge import DxySpxBridge, get_dxy_spx_bridge
from .spx_btc_bridge import SpxBtcBridge, get_spx_btc_bridge

from modules.macro_context.macro_context_types import MacroContext
from modules.fractal_intelligence.asset_fractal_types import AssetFractalContext


class CrossAssetEngine:
    """
    Engine that aggregates all cross-asset bridges.
    
    Computes the full Macro → DXY → SPX → BTC chain alignment.
    """
    
    def __init__(self):
        self.macro_dxy_bridge = get_macro_dxy_bridge()
        self.dxy_spx_bridge = get_dxy_spx_bridge()
        self.spx_btc_bridge = get_spx_btc_bridge()
        
        self._last_alignment: Optional[CrossAssetAlignment] = None
    
    def compute_alignment(
        self,
        macro: MacroContext,
        dxy: AssetFractalContext,
        spx: AssetFractalContext,
        btc: AssetFractalContext,
    ) -> CrossAssetAlignment:
        """
        Compute full cross-asset alignment.
        
        Args:
            macro: MacroContext
            dxy: DXY AssetFractalContext
            spx: SPX AssetFractalContext
            btc: BTC AssetFractalContext
        
        Returns:
            CrossAssetAlignment with aggregate assessment
        """
        
        # Compute individual bridges
        macro_dxy = self.macro_dxy_bridge.compute(macro, dxy)
        dxy_spx = self.dxy_spx_bridge.compute(dxy, spx)
        spx_btc = self.spx_btc_bridge.compute(spx, btc)
        
        # Compute aggregate alignment score
        alignment_score = self._compute_alignment_score(macro_dxy, dxy_spx, spx_btc)
        
        # Determine alignment state
        alignment_state = self._determine_alignment_state(alignment_score)
        
        # Find dominant and weakest bridges
        dominant_bridge, weakest_bridge = self._find_dominant_weakest(
            macro_dxy, dxy_spx, spx_btc
        )
        
        # Compute final bias
        final_bias = self._compute_final_bias(macro_dxy, dxy_spx, spx_btc)
        
        # Generate reason
        reason = self._generate_reason(
            macro_dxy, dxy_spx, spx_btc,
            alignment_state, final_bias,
            dominant_bridge, weakest_bridge,
        )
        
        alignment = CrossAssetAlignment(
            macro_dxy=macro_dxy,
            dxy_spx=dxy_spx,
            spx_btc=spx_btc,
            alignment_score=round(alignment_score, 4),
            alignment_state=alignment_state,
            dominant_bridge=dominant_bridge,
            weakest_bridge=weakest_bridge,
            final_bias=final_bias,
            reason=reason,
            timestamp=datetime.utcnow(),
        )
        
        self._last_alignment = alignment
        return alignment
    
    def _compute_alignment_score(
        self,
        macro_dxy: CrossAssetBridge,
        dxy_spx: CrossAssetBridge,
        spx_btc: CrossAssetBridge,
    ) -> float:
        """
        Compute weighted aggregate alignment score.
        
        Uses effective_strength (strength * alignment_multiplier) for each bridge.
        
        Score = 0.30 * macro_dxy + 0.30 * dxy_spx + 0.40 * spx_btc
        """
        score = (
            BRIDGE_WEIGHTS["macro_dxy"] * macro_dxy.effective_strength +
            BRIDGE_WEIGHTS["dxy_spx"] * dxy_spx.effective_strength +
            BRIDGE_WEIGHTS["spx_btc"] * spx_btc.effective_strength
        )
        
        return max(0.0, min(1.0, score))
    
    def _determine_alignment_state(self, score: float) -> AlignmentStateType:
        """
        Determine alignment state from score.
        
        >= 0.70 → STRONG
        0.50–0.70 → MODERATE
        0.30–0.50 → WEAK
        < 0.30 → CONFLICTED
        """
        if score >= ALIGNMENT_STATE_THRESHOLDS["STRONG"]:
            return "STRONG"
        elif score >= ALIGNMENT_STATE_THRESHOLDS["MODERATE"]:
            return "MODERATE"
        elif score >= ALIGNMENT_STATE_THRESHOLDS["WEAK"]:
            return "WEAK"
        else:
            return "CONFLICTED"
    
    def _find_dominant_weakest(
        self,
        macro_dxy: CrossAssetBridge,
        dxy_spx: CrossAssetBridge,
        spx_btc: CrossAssetBridge,
    ) -> tuple[str, str]:
        """Find dominant and weakest bridges by effective strength."""
        
        bridges = {
            "macro_dxy": macro_dxy.effective_strength,
            "dxy_spx": dxy_spx.effective_strength,
            "spx_btc": spx_btc.effective_strength,
        }
        
        sorted_bridges = sorted(bridges.items(), key=lambda x: x[1], reverse=True)
        
        dominant = sorted_bridges[0][0]
        weakest = sorted_bridges[-1][0]
        
        return dominant, weakest
    
    def _compute_final_bias(
        self,
        macro_dxy: CrossAssetBridge,
        dxy_spx: CrossAssetBridge,
        spx_btc: CrossAssetBridge,
    ) -> FinalBiasType:
        """
        Compute final directional bias for BTC.
        
        Rules:
        - BULLISH: At least 2 of 3 bridges bullish supportive AND spx_btc bullish supportive
        - BEARISH: At least 2 of 3 bridges bearish supportive AND spx_btc bearish supportive
        - MIXED: Some supportive but directions mixed
        - NEUTRAL: All weak/hold
        """
        
        # Count supportive bullish/bearish
        bullish_supportive = 0
        bearish_supportive = 0
        
        for bridge in [macro_dxy, dxy_spx, spx_btc]:
            if bridge.alignment == "SUPPORTIVE":
                if bridge.influence_direction == "BULLISH":
                    bullish_supportive += 1
                elif bridge.influence_direction == "BEARISH":
                    bearish_supportive += 1
        
        # Check final bridge (spx_btc) direction
        spx_btc_bullish = (
            spx_btc.alignment == "SUPPORTIVE" and
            spx_btc.influence_direction == "BULLISH"
        )
        spx_btc_bearish = (
            spx_btc.alignment == "SUPPORTIVE" and
            spx_btc.influence_direction == "BEARISH"
        )
        
        # BULLISH: Majority bullish AND BTC-facing bridge bullish
        if bullish_supportive >= 2 and spx_btc_bullish:
            return "BULLISH"
        
        # BEARISH: Majority bearish AND BTC-facing bridge bearish
        if bearish_supportive >= 2 and spx_btc_bearish:
            return "BEARISH"
        
        # MIXED: Some supportive but not aligned
        if bullish_supportive > 0 or bearish_supportive > 0:
            return "MIXED"
        
        return "NEUTRAL"
    
    def _generate_reason(
        self,
        macro_dxy: CrossAssetBridge,
        dxy_spx: CrossAssetBridge,
        spx_btc: CrossAssetBridge,
        alignment_state: AlignmentStateType,
        final_bias: FinalBiasType,
        dominant_bridge: str,
        weakest_bridge: str,
    ) -> str:
        """Generate human-readable explanation."""
        
        # Count alignments
        supportive_count = sum(
            1 for b in [macro_dxy, dxy_spx, spx_btc]
            if b.alignment == "SUPPORTIVE"
        )
        contrary_count = sum(
            1 for b in [macro_dxy, dxy_spx, spx_btc]
            if b.alignment == "CONTRARY"
        )
        
        if alignment_state == "STRONG":
            return f"macro to btc chain strongly aligned ({supportive_count}/3 supportive) with {final_bias.lower()} final bias"
        
        if alignment_state == "MODERATE":
            return f"macro to btc chain moderately aligned through {dominant_bridge} with {final_bias.lower()} bias"
        
        if alignment_state == "WEAK":
            return f"macro to btc chain weakly aligned - {weakest_bridge} is the weakest link"
        
        # CONFLICTED
        return f"macro to btc chain conflicted ({contrary_count}/3 contrary) - signals disagree"
    
    def get_summary(self, alignment: CrossAssetAlignment) -> CrossAssetSummary:
        """Extract compact summary."""
        return CrossAssetSummary(
            alignment_score=alignment.alignment_score,
            alignment_state=alignment.alignment_state,
            final_bias=alignment.final_bias,
            dominant_bridge=alignment.dominant_bridge,
            weakest_bridge=alignment.weakest_bridge,
        )
    
    def get_health(self) -> CrossAssetHealthStatus:
        """Get health status."""
        if self._last_alignment is None:
            return CrossAssetHealthStatus(
                status="ERROR",
                macro_available=False,
                dxy_available=False,
                spx_available=False,
                btc_available=False,
                bridges_computed=0,
                last_update=None,
            )
        
        # Check each bridge
        macro_ok = self._last_alignment.macro_dxy.alignment != "NEUTRAL"
        dxy_ok = True  # Part of macro_dxy bridge
        spx_ok = self._last_alignment.dxy_spx.alignment != "NEUTRAL"
        btc_ok = self._last_alignment.spx_btc.alignment != "NEUTRAL"
        
        bridges = 3
        status = "OK" if all([macro_ok, spx_ok, btc_ok]) else "DEGRADED"
        if self._last_alignment.alignment_state == "CONFLICTED":
            status = "DEGRADED"
        
        return CrossAssetHealthStatus(
            status=status,
            macro_available=macro_ok,
            dxy_available=dxy_ok,
            spx_available=spx_ok,
            btc_available=btc_ok,
            bridges_computed=bridges,
            last_update=self._last_alignment.timestamp,
        )


# Singleton
_engine: Optional[CrossAssetEngine] = None

def get_cross_asset_engine() -> CrossAssetEngine:
    global _engine
    if _engine is None:
        _engine = CrossAssetEngine()
    return _engine
