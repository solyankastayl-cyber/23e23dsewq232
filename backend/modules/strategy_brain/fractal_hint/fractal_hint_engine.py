"""
PHASE 24.3 — Fractal Hint Engine

Engine that provides fractal-based hints to Strategy Brain.

Key Principles:
1. Fractal influence is LIMITED to ≤10% of regime score
2. Fractal does NOT override strategy selection
3. Fractal only provides a "hint" that slightly adjusts suitability
4. If fractal is BLOCKED/UNKNOWN, it has NO effect (neutral)
"""

from typing import Dict, Optional, Any, List
from datetime import datetime, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.strategy_brain.fractal_hint.fractal_hint_types import (
    FractalHintInput,
    FractalHintScore,
    FractalPhase,
    FRACTAL_PHASE_STRATEGY_MAP,
)


class FractalHintEngine:
    """
    Fractal Hint Engine — PHASE 24.3
    
    Provides fractal-based hints to Strategy Brain with LIMITED influence.
    
    Scoring:
    - Base score: 0.5 (neutral)
    - Supported strategy bonus: +0.25 * strength
    - Anti strategy penalty: -0.25 * strength
    - Direction alignment bonus: +0.10 * strength
    - Phase confidence factor: scales all effects
    
    Max influence: ≤10% of regime score
    """
    
    # Lazy load fractal engine
    _fractal_engine = None
    
    @property
    def fractal_engine(self):
        """Lazy load FractalContextEngine."""
        if self._fractal_engine is None:
            try:
                from modules.fractal_intelligence.fractal_context_engine import FractalContextEngine
                self._fractal_engine = FractalContextEngine()
            except ImportError:
                pass
        return self._fractal_engine
    
    def get_fractal_hint(self, symbol: str = "BTC") -> FractalHintInput:
        """
        Get fractal hint input from FractalContext.
        
        Args:
            symbol: Symbol to analyze
            
        Returns:
            FractalHintInput with phase and confidence
        """
        if self.fractal_engine is None:
            return FractalHintInput()  # Default blocked
        
        try:
            import asyncio
            
            loop = asyncio.new_event_loop()
            try:
                context = loop.run_until_complete(
                    self.fractal_engine.build_context(symbol)
                )
            finally:
                loop.close()
            
            # Map phase string to enum
            phase = self._map_phase(context.phase)
            
            return FractalHintInput(
                phase=phase,
                phase_confidence=context.phase_confidence,
                fractal_strength=context.fractal_strength,
                context_state=context.context_state,
                direction=context.direction,
            )
        except Exception:
            return FractalHintInput()  # Default blocked
    
    def compute_hint_score(
        self,
        strategy_name: str,
        fractal_hint: FractalHintInput,
        strategy_direction: str = "LONG",
    ) -> FractalHintScore:
        """
        Compute fractal hint score for a strategy.
        
        Args:
            strategy_name: Strategy to score
            fractal_hint: Fractal hint input
            strategy_direction: Expected direction of strategy
            
        Returns:
            FractalHintScore with computed score
        """
        # If fractal not active, return neutral
        if not fractal_hint.is_active():
            return FractalHintScore(
                strategy_name=strategy_name,
                fractal_score=0.5,  # Neutral
                phase=fractal_hint.phase.value,
            )
        
        # Base score
        base_score = 0.5
        
        # Check if strategy is supported by phase
        supported = fractal_hint.get_supported_strategies()
        anti = fractal_hint.get_anti_strategies()
        
        is_supported = strategy_name in supported
        is_anti = strategy_name in anti
        
        # Phase alignment score
        phase_alignment = 0.0
        if is_supported:
            phase_alignment = 0.25 * fractal_hint.fractal_strength
        elif is_anti:
            phase_alignment = -0.25 * fractal_hint.fractal_strength
        
        # Direction alignment score
        direction_alignment = 0.0
        if fractal_hint.direction != "HOLD":
            # Check if fractal direction matches strategy expectation
            fractal_is_long = fractal_hint.direction == "LONG"
            strategy_is_long = strategy_direction == "LONG"
            
            if fractal_is_long == strategy_is_long:
                direction_alignment = 0.10 * fractal_hint.fractal_strength
            else:
                direction_alignment = -0.05 * fractal_hint.fractal_strength
        
        # Strength factor (higher strength = more confident hint)
        strength_factor = fractal_hint.fractal_strength * fractal_hint.phase_confidence
        
        # Final score
        fractal_score = base_score + phase_alignment + direction_alignment
        fractal_score = max(0.0, min(1.0, fractal_score))
        
        return FractalHintScore(
            strategy_name=strategy_name,
            fractal_score=fractal_score,
            phase_alignment=phase_alignment,
            direction_alignment=direction_alignment,
            strength_factor=strength_factor,
            phase=fractal_hint.phase.value,
            is_supported=is_supported,
            is_anti=is_anti,
        )
    
    def compute_all_strategy_hints(
        self,
        fractal_hint: FractalHintInput,
        strategies: Optional[List[str]] = None,
    ) -> Dict[str, FractalHintScore]:
        """
        Compute fractal hints for all strategies.
        
        Args:
            fractal_hint: Fractal hint input
            strategies: List of strategy names (default: all registered)
            
        Returns:
            Dict mapping strategy_name -> FractalHintScore
        """
        if strategies is None:
            strategies = [
                "trend_following",
                "mean_reversion",
                "breakout",
                "liquidation_capture",
                "flow_following",
                "volatility_expansion",
                "funding_arb",
                "structure_reversal",
            ]
        
        results = {}
        for strategy in strategies:
            score = self.compute_hint_score(strategy, fractal_hint)
            results[strategy] = score
        
        return results
    
    def get_regime_hint(self, symbol: str = "BTC") -> Dict[str, Any]:
        """
        Get regime hint for Strategy Brain integration.
        
        Returns dict compatible with regime confidence scoring.
        """
        fractal_hint = self.get_fractal_hint(symbol)
        
        if not fractal_hint.is_active():
            return {
                "fractal_score": 0.5,  # Neutral
                "fractal_active": False,
                "phase": "UNKNOWN",
                "regime_hint": "undefined",
            }
        
        # Score for regime confidence
        # Higher score = more confident regime detection
        fractal_score = self._compute_regime_fractal_score(fractal_hint)
        
        return {
            "fractal_score": fractal_score,
            "fractal_active": True,
            "phase": fractal_hint.phase.value,
            "regime_hint": fractal_hint.get_regime_hint(),
            "phase_confidence": fractal_hint.phase_confidence,
            "fractal_strength": fractal_hint.fractal_strength,
        }
    
    def _compute_regime_fractal_score(self, fractal_hint: FractalHintInput) -> float:
        """
        Compute fractal score for regime confidence.
        
        Clear phases (MARKUP/MARKDOWN) give higher scores.
        Transition phases (ACCUMULATION/DISTRIBUTION) give moderate scores.
        """
        phase_scores = {
            FractalPhase.MARKUP: 0.85,
            FractalPhase.MARKDOWN: 0.85,
            FractalPhase.RECOVERY: 0.75,
            FractalPhase.CAPITULATION: 0.70,
            FractalPhase.ACCUMULATION: 0.65,
            FractalPhase.DISTRIBUTION: 0.60,
            FractalPhase.UNKNOWN: 0.50,
        }
        
        base_score = phase_scores.get(fractal_hint.phase, 0.50)
        
        # Adjust by strength and confidence
        adjustment = (fractal_hint.fractal_strength - 0.5) * 0.2
        
        return max(0.0, min(1.0, base_score + adjustment))
    
    def _map_phase(self, phase_str: Optional[str]) -> FractalPhase:
        """Map phase string to FractalPhase enum."""
        if phase_str is None:
            return FractalPhase.UNKNOWN
        
        phase_upper = phase_str.upper()
        
        try:
            return FractalPhase(phase_upper)
        except ValueError:
            return FractalPhase.UNKNOWN


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[FractalHintEngine] = None


def get_fractal_hint_engine() -> FractalHintEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FractalHintEngine()
    return _engine
