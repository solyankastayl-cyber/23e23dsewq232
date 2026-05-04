"""
Regime Context — Engine

Unified engine that combines:
- MarketRegime
- StrategyRegimeMapping
- RegimeTransitionState

into a single RegimeContext for execution decisions.
"""

from typing import Optional
from datetime import datetime

from .regime_context_types import (
    RegimeContext,
    RegimeContextSummary,
    ContextState,
)
from .regime_types import MarketRegime
from .regime_detection_engine import RegimeDetectionEngine, get_regime_detection_engine
from .strategy_regime_mapping_engine import (
    StrategyRegimeMappingEngine,
    get_strategy_regime_mapping_engine,
)
from .strategy_regime_types import RegimeStrategySummary
from .regime_transition_engine import (
    RegimeTransitionEngine,
    get_regime_transition_engine,
)
from .regime_transition_types import RegimeTransitionState, TRANSITION_MODIFIERS


class RegimeContextEngine:
    """
    Regime Context Engine.
    
    Combines all regime intelligence components into unified context.
    
    Components:
    - MarketRegime: Current market state
    - StrategyRegimeMapping: Strategy suitability
    - RegimeTransitionState: Transition risk
    """
    
    def __init__(
        self,
        regime_engine: Optional[RegimeDetectionEngine] = None,
        strategy_engine: Optional[StrategyRegimeMappingEngine] = None,
        transition_engine: Optional[RegimeTransitionEngine] = None,
    ):
        self._regime_engine = regime_engine or get_regime_detection_engine()
        self._strategy_engine = strategy_engine or get_strategy_regime_mapping_engine()
        self._transition_engine = transition_engine or get_regime_transition_engine()
        self._current_context: Optional[RegimeContext] = None
    
    # ═══════════════════════════════════════════════════════════
    # Modifiers from Transition State
    # ═══════════════════════════════════════════════════════════
    
    def get_modifiers_from_transition(
        self,
        transition_state: str,
    ) -> dict:
        """
        Get modifiers based on transition state.
        
        STABLE: 1.00/1.00
        EARLY_SHIFT: 0.97/0.95
        ACTIVE_TRANSITION: 0.92/0.88
        UNSTABLE: 0.85/0.75
        """
        return TRANSITION_MODIFIERS.get(transition_state, TRANSITION_MODIFIERS["STABLE"])
    
    # ═══════════════════════════════════════════════════════════
    # Context State Determination
    # ═══════════════════════════════════════════════════════════
    
    def determine_context_state(
        self,
        regime_context_state: str,
        transition_state: str,
        favored_count: int,
        disfavored_count: int,
    ) -> ContextState:
        """
        Determine unified context state.
        
        SUPPORTIVE: regime supportive AND transition stable/early
        CONFLICTED: transition active/unstable OR regime conflicted
        NEUTRAL: otherwise
        """
        # Check for CONFLICTED first
        if transition_state in ["ACTIVE_TRANSITION", "UNSTABLE"]:
            return "CONFLICTED"
        
        if regime_context_state == "CONFLICTED":
            return "CONFLICTED"
        
        # Check for SUPPORTIVE
        if regime_context_state == "SUPPORTIVE" and transition_state in ["STABLE", "EARLY_SHIFT"]:
            return "SUPPORTIVE"
        
        # Check for mixed strategy suitability
        if favored_count > 0 and disfavored_count > 0:
            # Mixed signals
            if favored_count > disfavored_count * 2:
                return "SUPPORTIVE"
            elif disfavored_count > favored_count * 2:
                return "CONFLICTED"
        
        # Default NEUTRAL
        return "NEUTRAL"
    
    # ═══════════════════════════════════════════════════════════
    # Reason Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_reason(
        self,
        current_regime: str,
        next_candidate: str,
        transition_state: str,
        context_state: str,
        favored_count: int,
    ) -> str:
        """Generate human-readable reason for context state."""
        regime_lower = current_regime.lower()
        
        if context_state == "SUPPORTIVE":
            return f"market remains in {regime_lower} regime with clear favored strategies and no critical transition risk"
        
        elif context_state == "NEUTRAL":
            if favored_count == 0:
                return f"current {regime_lower} regime is stable but strategy suitability is mixed across the active set"
            return f"{regime_lower} regime active with balanced strategy allocation and moderate transition risk"
        
        else:  # CONFLICTED
            if transition_state in ["ACTIVE_TRANSITION", "UNSTABLE"]:
                next_lower = next_candidate.lower() if next_candidate != "NONE" else "unknown"
                return f"{regime_lower} regime is destabilizing with high transition risk toward {next_lower}, current favored strategies may soon lose suitability"
            return f"regime signals are conflicting and strategy suitability is uncertain in current {regime_lower} conditions"
    
    # ═══════════════════════════════════════════════════════════
    # Main Build
    # ═══════════════════════════════════════════════════════════
    
    def build_context(
        self,
        regime: MarketRegime,
        strategy_summary: RegimeStrategySummary,
        transition: RegimeTransitionState,
    ) -> RegimeContext:
        """
        Build unified RegimeContext from components.
        
        Combines MarketRegime + StrategyMapping + TransitionState.
        """
        # Get modifiers from transition state
        modifiers = self.get_modifiers_from_transition(transition.transition_state)
        
        # Determine unified context state
        context_state = self.determine_context_state(
            regime.context_state,
            transition.transition_state,
            len(strategy_summary.favored_strategies),
            len(strategy_summary.disfavored_strategies),
        )
        
        # Generate reason
        reason = self.generate_reason(
            regime.regime_type,
            transition.next_regime_candidate,
            transition.transition_state,
            context_state,
            len(strategy_summary.favored_strategies),
        )
        
        context = RegimeContext(
            # From MarketRegime
            current_regime=regime.regime_type,
            regime_confidence=regime.regime_confidence,
            dominant_driver=regime.dominant_driver,
            
            # From TransitionState
            next_regime_candidate=transition.next_regime_candidate,
            transition_probability=transition.transition_probability,
            transition_state=transition.transition_state,
            
            # From StrategyMapping
            favored_strategies=strategy_summary.favored_strategies,
            neutral_strategies=strategy_summary.neutral_strategies,
            disfavored_strategies=strategy_summary.disfavored_strategies,
            
            # Computed
            confidence_modifier=modifiers["confidence_modifier"],
            capital_modifier=modifiers["capital_modifier"],
            context_state=context_state,
            reason=reason,
            
            # Metadata
            symbol=regime.symbol,
            timeframe=regime.timeframe,
        )
        
        self._current_context = context
        return context
    
    # ═══════════════════════════════════════════════════════════
    # Full Computation
    # ═══════════════════════════════════════════════════════════
    
    async def compute_context(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "1H",
    ) -> RegimeContext:
        """
        Compute full regime context.
        
        1. Detect current regime
        2. Map strategies to regime
        3. Detect transitions
        4. Build unified context
        """
        # 1. Detect current regime
        regime = self._regime_engine.detect_regime_simulated(symbol, timeframe)
        
        # 2. Map strategies
        self._strategy_engine.map_all_strategies(regime)
        strategy_summary = self._strategy_engine.get_summary(regime)
        
        # 3. Detect transitions
        transition = await self._transition_engine.detect_transition_from_history(
            symbol,
            timeframe,
        )
        
        # 4. Build context
        return self.build_context(regime, strategy_summary, transition)
    
    # ═══════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(self) -> Optional[RegimeContextSummary]:
        """Get summary of current context."""
        if not self._current_context:
            return None
        
        ctx = self._current_context
        
        return RegimeContextSummary(
            current_regime=ctx.current_regime,
            regime_confidence=ctx.regime_confidence,
            transition_state=ctx.transition_state,
            transition_probability=ctx.transition_probability,
            context_state=ctx.context_state,
            total_favored=len(ctx.favored_strategies),
            total_neutral=len(ctx.neutral_strategies),
            total_disfavored=len(ctx.disfavored_strategies),
            confidence_modifier=ctx.confidence_modifier,
            capital_modifier=ctx.capital_modifier,
        )
    
    # ═══════════════════════════════════════════════════════════
    # Accessors
    # ═══════════════════════════════════════════════════════════
    
    @property
    def current_context(self) -> Optional[RegimeContext]:
        """Get current context."""
        return self._current_context


# Singleton
_engine: Optional[RegimeContextEngine] = None


def get_regime_context_engine() -> RegimeContextEngine:
    """Get singleton instance of RegimeContextEngine."""
    global _engine
    if _engine is None:
        _engine = RegimeContextEngine()
    return _engine
