"""
PHASE 25.5 — Execution Context Engine

Core engine that computes execution modifiers from macro-fractal intelligence.

Key principle: 
This engine modifies ONLY confidence and capital parameters.
It does NOT change strategy, direction, or signal.

Weight model:
- fractal_weight = 0.16
- macro_weight = 0.02
"""

from typing import Optional
from datetime import datetime

from .execution_context_types import (
    ExecutionContext,
    ExecutionContextSummary,
    ExecutionContextHealthStatus,
    ContextBiasType,
    ContextStateType,
    FRACTAL_WEIGHT,
    MACRO_WEIGHT,
    CONFIDENCE_MIN,
    CONFIDENCE_MAX,
    CAPITAL_MIN,
    CAPITAL_MAX,
    CAPITAL_FRACTAL_WEIGHT,
    CAPITAL_CROSS_ASSET_WEIGHT,
    CAPITAL_MACRO_WEIGHT,
    CONFLICT_CONFIDENCE_PENALTY,
    CONFLICT_CAPITAL_PENALTY,
)

from modules.macro_fractal_brain.macro_fractal_types import MacroFractalContext
from modules.fractal_intelligence.fractal_context_types import FractalContext
from modules.cross_asset_intelligence.cross_asset_types import CrossAssetAlignment


class ExecutionContextEngine:
    """
    Engine that computes execution context modifiers.
    
    Inputs:
    - MacroFractalContext (from macro_fractal_brain)
    - FractalContext (from fractal_intelligence)
    - CrossAssetAlignment (from cross_asset_intelligence)
    
    Outputs:
    - ExecutionContext with confidence_modifier and capital_modifier
    
    Key constraints:
    - Does NOT change strategy
    - Does NOT change direction
    - Does NOT change signal
    """
    
    def __init__(self):
        self._last_context: Optional[ExecutionContext] = None
    
    def compute(
        self,
        macro_fractal: MacroFractalContext,
        fractal: FractalContext,
        cross_asset: CrossAssetAlignment,
    ) -> ExecutionContext:
        """
        Compute execution context.
        
        Args:
            macro_fractal: MacroFractalContext from macro_fractal_brain
            fractal: FractalContext from fractal_intelligence
            cross_asset: CrossAssetAlignment from cross_asset_intelligence
        
        Returns:
            ExecutionContext with modifiers
        """
        
        # Extract strengths
        fractal_strength = fractal.fractal_strength
        macro_strength = macro_fractal.final_confidence * 0.5  # Scale macro contribution
        cross_asset_strength = cross_asset.alignment_score
        
        # Get context state from macro_fractal
        context_state = macro_fractal.context_state
        
        # Compute base confidence modifier
        # Formula: 1 + fractal_strength * 0.16 + macro_strength * 0.02
        confidence_modifier = self._compute_confidence_modifier(
            fractal_strength, macro_strength
        )
        
        # Compute base capital modifier
        # Formula: 1 + fractal_strength * 0.12 + cross_asset_strength * 0.05 + macro_strength * 0.02
        capital_modifier = self._compute_capital_modifier(
            fractal_strength, cross_asset_strength, macro_strength
        )
        
        # Apply conflict penalty if context is CONFLICTED
        if context_state == "CONFLICTED":
            confidence_modifier *= CONFLICT_CONFIDENCE_PENALTY
            capital_modifier *= CONFLICT_CAPITAL_PENALTY
        
        # Clamp to bounds
        confidence_modifier = self._clamp(
            confidence_modifier, CONFIDENCE_MIN, CONFIDENCE_MAX
        )
        capital_modifier = self._clamp(
            capital_modifier, CAPITAL_MIN, CAPITAL_MAX
        )
        
        # Get bias directly from macro_fractal
        context_bias = self._map_bias(macro_fractal.final_bias)
        
        # Generate reason
        reason = self._generate_reason(
            context_bias, context_state,
            fractal_strength, macro_strength, cross_asset_strength
        )
        
        context = ExecutionContext(
            context_bias=context_bias,
            fractal_strength=round(fractal_strength, 4),
            macro_strength=round(macro_strength, 4),
            cross_asset_strength=round(cross_asset_strength, 4),
            confidence_modifier=round(confidence_modifier, 4),
            capital_modifier=round(capital_modifier, 4),
            context_state=context_state,
            reason=reason,
            timestamp=datetime.utcnow(),
        )
        
        self._last_context = context
        return context
    
    # ═══════════════════════════════════════════════════════════
    # Confidence Modifier
    # ═══════════════════════════════════════════════════════════
    
    def _compute_confidence_modifier(
        self,
        fractal_strength: float,
        macro_strength: float,
    ) -> float:
        """
        Compute confidence modifier.
        
        Formula:
        1 + fractal_strength * 0.16 + macro_strength * 0.02
        
        Bounds: [0.90, 1.18]
        """
        return 1.0 + (fractal_strength * FRACTAL_WEIGHT) + (macro_strength * MACRO_WEIGHT)
    
    # ═══════════════════════════════════════════════════════════
    # Capital Modifier
    # ═══════════════════════════════════════════════════════════
    
    def _compute_capital_modifier(
        self,
        fractal_strength: float,
        cross_asset_strength: float,
        macro_strength: float,
    ) -> float:
        """
        Compute capital modifier.
        
        Formula:
        1 + fractal_strength * 0.12 + cross_asset_strength * 0.05 + macro_strength * 0.02
        
        Bounds: [0.85, 1.20]
        """
        return (
            1.0 +
            (fractal_strength * CAPITAL_FRACTAL_WEIGHT) +
            (cross_asset_strength * CAPITAL_CROSS_ASSET_WEIGHT) +
            (macro_strength * CAPITAL_MACRO_WEIGHT)
        )
    
    # ═══════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════
    
    def _clamp(self, value: float, min_val: float, max_val: float) -> float:
        """Clamp value to [min_val, max_val]."""
        return max(min_val, min(max_val, value))
    
    def _map_bias(self, final_bias: str) -> ContextBiasType:
        """Map MacroFractalContext.final_bias to ContextBiasType."""
        mapping = {
            "BULLISH": "BULLISH",
            "BEARISH": "BEARISH",
            "MIXED": "MIXED",
            "NEUTRAL": "NEUTRAL",
        }
        return mapping.get(final_bias, "NEUTRAL")
    
    # ═══════════════════════════════════════════════════════════
    # Reason Generation
    # ═══════════════════════════════════════════════════════════
    
    def _generate_reason(
        self,
        context_bias: ContextBiasType,
        context_state: ContextStateType,
        fractal_strength: float,
        macro_strength: float,
        cross_asset_strength: float,
    ) -> str:
        """Generate human-readable explanation."""
        
        # BULLISH
        if context_bias == "BULLISH":
            if context_state == "SUPPORTIVE":
                return "bullish fractal regime supported by macro liquidity conditions"
            elif context_state == "CONFLICTED":
                return "bullish fractal with conflicting macro signals reduces execution confidence"
            else:
                return "bullish fractal regime with neutral macro context"
        
        # BEARISH
        if context_bias == "BEARISH":
            if context_state == "SUPPORTIVE":
                return "macro tightening and bearish fractal alignment reduce execution confidence"
            elif context_state == "CONFLICTED":
                return "bearish bias with macro conflict reduces capital allocation"
            else:
                return "bearish fractal regime with tightening macro conditions"
        
        # MIXED
        if context_bias == "MIXED":
            return "macro and fractal signals conflict reducing reliability"
        
        # NEUTRAL
        if fractal_strength < 0.3 and macro_strength < 0.3:
            return "weak fractal and macro signals suggest neutral execution context"
        
        return "neutral macro-fractal context with standard execution parameters"
    
    # ═══════════════════════════════════════════════════════════
    # Summary & Health
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(self, context: ExecutionContext) -> ExecutionContextSummary:
        """Get compact summary."""
        return ExecutionContextSummary(
            context_bias=context.context_bias,
            confidence_modifier=context.confidence_modifier,
            capital_modifier=context.capital_modifier,
            context_state=context.context_state,
        )
    
    def get_health(self) -> ExecutionContextHealthStatus:
        """Get health status."""
        if self._last_context is None:
            return ExecutionContextHealthStatus(
                status="ERROR",
                has_macro_fractal=False,
                has_fractal=False,
                has_cross_asset=False,
                context_state="BLOCKED",
                last_update=None,
            )
        
        ctx = self._last_context
        
        has_macro_fractal = ctx.macro_strength > 0.0
        has_fractal = ctx.fractal_strength > 0.0
        has_cross_asset = ctx.cross_asset_strength > 0.0
        
        all_available = all([has_macro_fractal, has_fractal, has_cross_asset])
        some_available = any([has_macro_fractal, has_fractal, has_cross_asset])
        
        if all_available:
            status = "OK"
        elif some_available:
            status = "DEGRADED"
        else:
            status = "ERROR"
        
        return ExecutionContextHealthStatus(
            status=status,
            has_macro_fractal=has_macro_fractal,
            has_fractal=has_fractal,
            has_cross_asset=has_cross_asset,
            context_state=ctx.context_state,
            last_update=ctx.timestamp,
        )


# Singleton
_engine: Optional[ExecutionContextEngine] = None


def get_execution_context_engine() -> ExecutionContextEngine:
    """Get singleton instance of ExecutionContextEngine."""
    global _engine
    if _engine is None:
        _engine = ExecutionContextEngine()
    return _engine
