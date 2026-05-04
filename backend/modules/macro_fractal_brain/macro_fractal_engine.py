"""
PHASE 25.4 — Macro-Fractal Brain Engine

Core engine that combines:
- MacroContext
- AssetFractalContext (BTC, SPX, DXY)
- CrossAssetAlignment

Into unified MacroFractalContext.
"""

from typing import Optional, Dict, Tuple
from datetime import datetime

from .macro_fractal_types import (
    MacroFractalContext,
    MacroFractalSummary,
    MacroFractalDrivers,
    MacroFractalHealthStatus,
    FinalBiasType,
    ContextStateType,
    DriverType,
    CONFIDENCE_WEIGHTS,
    RELIABILITY_WEIGHTS,
    SUPPORTIVE_CONFIDENCE_THRESHOLD,
    SUPPORTIVE_RELIABILITY_THRESHOLD,
    CONFLICTED_RELIABILITY_THRESHOLD,
    BLOCKED_ALIGNMENT_THRESHOLD,
)

from modules.macro_context.macro_context_types import MacroContext
from modules.fractal_intelligence.asset_fractal_types import AssetFractalContext
from modules.cross_asset_intelligence.cross_asset_types import CrossAssetAlignment


class MacroFractalEngine:
    """
    Brain that unifies all macro-fractal intelligence.
    
    Key principles:
    - Does NOT change direction directly
    - Does NOT replace TA / Exchange
    - Provides high-level intelligence: bias, confidence, reliability, context
    """
    
    def __init__(self):
        self._last_context: Optional[MacroFractalContext] = None
    
    def compute(
        self,
        macro: MacroContext,
        btc: AssetFractalContext,
        spx: AssetFractalContext,
        dxy: AssetFractalContext,
        cross_asset: CrossAssetAlignment,
    ) -> MacroFractalContext:
        """
        Compute unified MacroFractalContext.
        
        Args:
            macro: MacroContext from macro_context module
            btc: BTC AssetFractalContext
            spx: SPX AssetFractalContext
            dxy: DXY AssetFractalContext
            cross_asset: CrossAssetAlignment from cross_asset_intelligence
        
        Returns:
            MacroFractalContext with unified assessment
        """
        
        # Extract cross_asset_strength
        cross_asset_strength = cross_asset.alignment_score
        
        # Compute final bias
        final_bias = self._compute_final_bias(macro, btc, cross_asset)
        
        # Compute final confidence
        final_confidence = self._compute_final_confidence(
            macro, btc, spx, dxy, cross_asset_strength
        )
        
        # Compute final reliability
        final_reliability = self._compute_final_reliability(
            macro, btc, spx, dxy, cross_asset_strength
        )
        
        # Determine context state
        context_state = self._determine_context_state(
            macro, btc, spx, dxy, cross_asset,
            final_bias, final_confidence, final_reliability
        )
        
        # Find dominant and weakest drivers
        dominant_driver, weakest_driver = self._find_drivers(
            macro, btc, spx, dxy, cross_asset_strength
        )
        
        # Generate reason
        reason = self._generate_reason(
            macro, btc, cross_asset,
            final_bias, context_state,
            dominant_driver
        )
        
        context = MacroFractalContext(
            # Macro
            macro_state=macro.macro_state,
            
            # Directions
            btc_direction=btc.direction,
            spx_direction=spx.direction,
            dxy_direction=dxy.direction,
            
            # Phases
            btc_phase=btc.phase,
            spx_phase=spx.phase,
            dxy_phase=dxy.phase,
            
            # Alignments
            macro_dxy_alignment=cross_asset.macro_dxy.alignment,
            dxy_spx_alignment=cross_asset.dxy_spx.alignment,
            spx_btc_alignment=cross_asset.spx_btc.alignment,
            cross_asset_strength=round(cross_asset_strength, 4),
            
            # Final assessment
            final_bias=final_bias,
            final_confidence=round(final_confidence, 4),
            final_reliability=round(final_reliability, 4),
            
            # Context
            context_state=context_state,
            
            # Drivers
            dominant_driver=dominant_driver,
            weakest_driver=weakest_driver,
            
            # Reason
            reason=reason,
            
            timestamp=datetime.utcnow(),
        )
        
        self._last_context = context
        return context
    
    # ═══════════════════════════════════════════════════════════
    # Final Bias Computation
    # ═══════════════════════════════════════════════════════════
    
    def _compute_final_bias(
        self,
        macro: MacroContext,
        btc: AssetFractalContext,
        cross_asset: CrossAssetAlignment,
    ) -> FinalBiasType:
        """
        Compute final directional bias.
        
        Rules:
        - BULLISH: cross_asset BULLISH + BTC not bearish + macro not RISK_OFF
        - BEARISH: cross_asset BEARISH + BTC not bullish + macro not RISK_ON
        - MIXED: conflicting signals
        - NEUTRAL: weak signals
        """
        
        ca_bias = cross_asset.final_bias
        btc_bullish = btc.direction == "LONG"
        btc_bearish = btc.direction == "SHORT"
        macro_risk_on = macro.macro_state == "RISK_ON"
        macro_risk_off = macro.macro_state == "RISK_OFF"
        
        # BULLISH
        if ca_bias == "BULLISH" and not btc_bearish and not macro_risk_off:
            return "BULLISH"
        
        # BEARISH
        if ca_bias == "BEARISH" and not btc_bullish and not macro_risk_on:
            return "BEARISH"
        
        # MIXED: conflicting signals
        if ca_bias in ["BULLISH", "BEARISH"]:
            # Check for conflicts
            if ca_bias == "BULLISH" and (btc_bearish or macro_risk_off):
                return "MIXED"
            if ca_bias == "BEARISH" and (btc_bullish or macro_risk_on):
                return "MIXED"
        
        # MIXED if cross_asset is MIXED
        if ca_bias == "MIXED":
            return "MIXED"
        
        # NEUTRAL for weak/unknown signals
        return "NEUTRAL"
    
    # ═══════════════════════════════════════════════════════════
    # Confidence Computation
    # ═══════════════════════════════════════════════════════════
    
    def _compute_final_confidence(
        self,
        macro: MacroContext,
        btc: AssetFractalContext,
        spx: AssetFractalContext,
        dxy: AssetFractalContext,
        cross_asset_strength: float,
    ) -> float:
        """
        Compute final confidence.
        
        Formula:
        0.25 * macro.confidence
        + 0.20 * btc.confidence
        + 0.15 * spx.confidence
        + 0.10 * dxy.confidence
        + 0.30 * cross_asset_strength
        """
        confidence = (
            CONFIDENCE_WEIGHTS["macro"] * macro.confidence +
            CONFIDENCE_WEIGHTS["btc"] * btc.confidence +
            CONFIDENCE_WEIGHTS["spx"] * spx.confidence +
            CONFIDENCE_WEIGHTS["dxy"] * dxy.confidence +
            CONFIDENCE_WEIGHTS["cross_asset"] * cross_asset_strength
        )
        
        return max(0.0, min(1.0, confidence))
    
    # ═══════════════════════════════════════════════════════════
    # Reliability Computation
    # ═══════════════════════════════════════════════════════════
    
    def _compute_final_reliability(
        self,
        macro: MacroContext,
        btc: AssetFractalContext,
        spx: AssetFractalContext,
        dxy: AssetFractalContext,
        cross_asset_strength: float,
    ) -> float:
        """
        Compute final reliability.
        
        Formula:
        0.30 * macro.reliability
        + 0.20 * btc.reliability
        + 0.15 * spx.reliability
        + 0.10 * dxy.reliability
        + 0.25 * alignment_score
        """
        reliability = (
            RELIABILITY_WEIGHTS["macro"] * macro.reliability +
            RELIABILITY_WEIGHTS["btc"] * btc.reliability +
            RELIABILITY_WEIGHTS["spx"] * spx.reliability +
            RELIABILITY_WEIGHTS["dxy"] * dxy.reliability +
            RELIABILITY_WEIGHTS["cross_asset"] * cross_asset_strength
        )
        
        return max(0.0, min(1.0, reliability))
    
    # ═══════════════════════════════════════════════════════════
    # Context State
    # ═══════════════════════════════════════════════════════════
    
    def _determine_context_state(
        self,
        macro: MacroContext,
        btc: AssetFractalContext,
        spx: AssetFractalContext,
        dxy: AssetFractalContext,
        cross_asset: CrossAssetAlignment,
        final_bias: FinalBiasType,
        final_confidence: float,
        final_reliability: float,
    ) -> ContextStateType:
        """
        Determine context state.
        
        BLOCKED: macro blocked + all assets neutral + low alignment
        SUPPORTIVE: directional bias + high confidence + high reliability
        CONFLICTED: mixed bias or low reliability
        MIXED: everything else
        """
        
        # BLOCKED
        all_neutral = all(
            ctx.context_state in ["BLOCKED", "NEUTRAL"]
            for ctx in [btc, spx, dxy]
        )
        
        if (
            macro.context_state == "BLOCKED" and
            all_neutral and
            cross_asset.alignment_score < BLOCKED_ALIGNMENT_THRESHOLD
        ):
            return "BLOCKED"
        
        # SUPPORTIVE
        if (
            final_bias in ["BULLISH", "BEARISH"] and
            final_confidence >= SUPPORTIVE_CONFIDENCE_THRESHOLD and
            final_reliability >= SUPPORTIVE_RELIABILITY_THRESHOLD and
            cross_asset.alignment_state in ["STRONG", "MODERATE"]
        ):
            return "SUPPORTIVE"
        
        # CONFLICTED
        is_conflicted = (
            final_bias == "MIXED" or
            (final_confidence >= 0.50 and final_reliability < CONFLICTED_RELIABILITY_THRESHOLD) or
            cross_asset.alignment_state == "CONFLICTED"
        )
        
        if is_conflicted:
            return "CONFLICTED"
        
        # MIXED
        return "MIXED"
    
    # ═══════════════════════════════════════════════════════════
    # Driver Analysis
    # ═══════════════════════════════════════════════════════════
    
    def _find_drivers(
        self,
        macro: MacroContext,
        btc: AssetFractalContext,
        spx: AssetFractalContext,
        dxy: AssetFractalContext,
        cross_asset_strength: float,
    ) -> Tuple[DriverType, DriverType]:
        """
        Find dominant and weakest drivers.
        
        Evaluates 5 drivers:
        - MACRO: macro_strength
        - BTC: btc.strength
        - SPX: spx.strength
        - DXY: dxy.strength
        - CROSS_ASSET: alignment_score
        
        If top-2 difference < 0.05, dominant = MIXED
        """
        
        drivers: Dict[DriverType, float] = {
            "MACRO": macro.macro_strength,
            "BTC": btc.strength,
            "SPX": spx.strength,
            "DXY": dxy.strength,
            "CROSS_ASSET": cross_asset_strength,
        }
        
        sorted_drivers = sorted(drivers.items(), key=lambda x: x[1], reverse=True)
        
        dominant = sorted_drivers[0][0]
        dominant_strength = sorted_drivers[0][1]
        second_strength = sorted_drivers[1][1]
        weakest = sorted_drivers[-1][0]
        
        # If top-2 are very close, mark as MIXED
        if dominant_strength - second_strength < 0.05:
            dominant = "MIXED"
        
        return dominant, weakest
    
    def get_drivers(
        self,
        macro: MacroContext,
        btc: AssetFractalContext,
        spx: AssetFractalContext,
        dxy: AssetFractalContext,
        cross_asset_strength: float,
    ) -> MacroFractalDrivers:
        """Get detailed driver analysis."""
        
        drivers = {
            "MACRO": round(macro.macro_strength, 4),
            "BTC": round(btc.strength, 4),
            "SPX": round(spx.strength, 4),
            "DXY": round(dxy.strength, 4),
            "CROSS_ASSET": round(cross_asset_strength, 4),
        }
        
        dominant, weakest = self._find_drivers(
            macro, btc, spx, dxy, cross_asset_strength
        )
        
        return MacroFractalDrivers(
            drivers=drivers,
            dominant_driver=dominant,
            weakest_driver=weakest,
        )
    
    # ═══════════════════════════════════════════════════════════
    # Reason Generation
    # ═══════════════════════════════════════════════════════════
    
    def _generate_reason(
        self,
        macro: MacroContext,
        btc: AssetFractalContext,
        cross_asset: CrossAssetAlignment,
        final_bias: FinalBiasType,
        context_state: ContextStateType,
        dominant_driver: DriverType,
    ) -> str:
        """Generate human-readable explanation."""
        
        macro_desc = macro.macro_state.lower().replace("_", " ")
        btc_desc = btc.direction.lower()
        ca_state = cross_asset.alignment_state.lower()
        
        if context_state == "BLOCKED":
            return "insufficient macro-fractal inputs or cross-asset alignment too weak"
        
        if context_state == "SUPPORTIVE":
            if final_bias == "BULLISH":
                return f"easing/risk-on macro with {ca_state} cross-asset chain creates bullish macro-fractal context"
            elif final_bias == "BEARISH":
                return f"{macro_desc} macro with {ca_state} bearish cross-asset chain forms coherent bearish macro-fractal context"
        
        if context_state == "CONFLICTED":
            return f"macro context ({macro_desc}) and cross-asset chain disagree with btc ({btc_desc}), reducing reliability"
        
        # MIXED
        return f"{macro_desc} macro with {ca_state} alignment and {btc_desc} btc creates mixed macro-fractal context"
    
    # ═══════════════════════════════════════════════════════════
    # Summary & Health
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(self, context: MacroFractalContext) -> MacroFractalSummary:
        """Extract compact summary."""
        return MacroFractalSummary(
            final_bias=context.final_bias,
            final_confidence=context.final_confidence,
            final_reliability=context.final_reliability,
            context_state=context.context_state,
            macro_state=context.macro_state,
            cross_asset_strength=context.cross_asset_strength,
        )
    
    def get_health(self) -> MacroFractalHealthStatus:
        """Get health status."""
        if self._last_context is None:
            return MacroFractalHealthStatus(
                status="ERROR",
                has_macro=False,
                has_btc=False,
                has_spx=False,
                has_dxy=False,
                has_cross_asset=False,
                context_state="BLOCKED",
                last_update=None,
            )
        
        ctx = self._last_context
        
        has_macro = ctx.macro_state != "UNKNOWN"
        has_btc = ctx.btc_direction != "HOLD" or ctx.btc_phase is not None
        has_spx = ctx.spx_direction != "HOLD" or ctx.spx_phase is not None
        has_dxy = ctx.dxy_direction != "HOLD" or ctx.dxy_phase is not None
        has_cross_asset = ctx.cross_asset_strength > 0.1
        
        all_available = all([has_macro, has_btc, has_spx, has_dxy, has_cross_asset])
        some_available = any([has_macro, has_btc, has_spx, has_dxy, has_cross_asset])
        
        if all_available:
            status = "OK"
        elif some_available:
            status = "DEGRADED"
        else:
            status = "ERROR"
        
        return MacroFractalHealthStatus(
            status=status,
            has_macro=has_macro,
            has_btc=has_btc,
            has_spx=has_spx,
            has_dxy=has_dxy,
            has_cross_asset=has_cross_asset,
            context_state=ctx.context_state,
            last_update=ctx.timestamp,
        )


# Singleton
_engine: Optional[MacroFractalEngine] = None

def get_macro_fractal_engine() -> MacroFractalEngine:
    global _engine
    if _engine is None:
        _engine = MacroFractalEngine()
    return _engine
