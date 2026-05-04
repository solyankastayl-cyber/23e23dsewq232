"""
PHASE 24.2 — Fractal Interaction Engine

Engine that integrates Fractal Intelligence into Alpha Interaction Layer.

Key Principles:
1. Fractal does NOT change final direction (TA + Alpha Engine set direction)
2. Fractal only modifies: confidence, capital, interaction_state
3. BLOCKED fractal is ignored
4. NEUTRAL fractal has no effect

Patterns:
- ta_fractal_alignment: +0.05 conf, +0.05 cap
- exchange_fractal_alignment: +0.04 conf, +0.03 cap  
- fractal_conflict: -0.07 conf, -0.06 cap
- phase_direction_support: +0.04 conf
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_interactions.fractal_interaction_types import (
    FractalInputForInteraction,
    FractalInteractionResult,
    FractalInteractionState,
    DominantSignal,
    TA_FRACTAL_ALIGNMENT_CONFIG,
    EXCHANGE_FRACTAL_ALIGNMENT_CONFIG,
    FRACTAL_CONFLICT_CONFIG,
    PHASE_DIRECTION_SUPPORT_CONFIG,
    MODIFIER_BOUNDS,
)

from modules.alpha_interactions.alpha_interaction_types import (
    TAInputForInteraction,
    ExchangeInputForInteraction,
)


class FractalInteractionEngine:
    """
    Fractal Interaction Engine — PHASE 24.2
    
    Integrates Fractal Intelligence as third signal leg:
    - TA Intelligence (direction, conviction)
    - Exchange Intelligence (bias, confidence)
    - Fractal Intelligence (direction, phase, strength)
    
    Key Principle:
        Fractal NEVER changes direction.
        It only modifies confidence and capital allocation.
    """
    
    # Direction mapping
    DIRECTION_NUMERIC = {
        "LONG": 1.0,
        "BULLISH": 1.0,
        "SHORT": -1.0,
        "BEARISH": -1.0,
        "HOLD": 0.0,
        "NEUTRAL": 0.0,
    }
    
    def __init__(self):
        # Lazy load fractal context engine
        self._fractal_engine = None
    
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
    
    def analyze(
        self,
        symbol: str,
        ta_input: TAInputForInteraction,
        exchange_input: ExchangeInputForInteraction,
        fractal_input: Optional[FractalInputForInteraction] = None,
        base_confidence: float = 0.5,
    ) -> FractalInteractionResult:
        """
        Analyze three-leg interaction with Fractal.
        
        Args:
            symbol: Trading symbol
            ta_input: TA hypothesis input
            exchange_input: Exchange context input
            fractal_input: Fractal context input (optional, will fetch if None)
            base_confidence: Base confidence from upstream
            
        Returns:
            FractalInteractionResult with modifiers
        """
        now = datetime.now(timezone.utc)
        
        # Get fractal input if not provided
        if fractal_input is None:
            fractal_input = self._get_fractal_input(symbol)
        
        # Calculate support scores
        ta_support = self._calculate_ta_support(ta_input)
        exchange_support = self._calculate_exchange_support(exchange_input)
        fractal_support = self._calculate_fractal_support(fractal_input)
        
        # Final direction is from TA (NOT fractal)
        final_direction = ta_input.direction
        
        # Initialize modifiers
        confidence_modifier = 1.0
        capital_modifier = 1.0
        patterns_detected = []
        
        # Only apply fractal patterns if fractal is active
        if self._is_fractal_active(fractal_input):
            
            # Pattern 1: TA ↔ Fractal Alignment
            if self._check_ta_fractal_alignment(ta_input, fractal_input):
                confidence_modifier += TA_FRACTAL_ALIGNMENT_CONFIG["confidence_bonus"]
                capital_modifier += TA_FRACTAL_ALIGNMENT_CONFIG["capital_bonus"]
                patterns_detected.append("ta_fractal_alignment")
            
            # Pattern 2: Exchange ↔ Fractal Alignment
            if self._check_exchange_fractal_alignment(exchange_input, fractal_input):
                confidence_modifier += EXCHANGE_FRACTAL_ALIGNMENT_CONFIG["confidence_bonus"]
                capital_modifier += EXCHANGE_FRACTAL_ALIGNMENT_CONFIG["capital_bonus"]
                patterns_detected.append("exchange_fractal_alignment")
            
            # Pattern 3: Fractal Conflict
            if self._check_fractal_conflict(ta_input, fractal_input):
                confidence_modifier += FRACTAL_CONFLICT_CONFIG["confidence_penalty"]
                capital_modifier += FRACTAL_CONFLICT_CONFIG["capital_penalty"]
                patterns_detected.append("fractal_conflict")
            
            # Pattern 4: Phase Direction Support
            if self._check_phase_direction_support(ta_input, fractal_input):
                confidence_modifier += PHASE_DIRECTION_SUPPORT_CONFIG["confidence_bonus"]
                capital_modifier += PHASE_DIRECTION_SUPPORT_CONFIG["capital_bonus"]
                patterns_detected.append("phase_direction_support")
        
        # Clamp modifiers to bounds
        confidence_modifier = self._clamp(
            confidence_modifier,
            MODIFIER_BOUNDS["confidence_min"],
            MODIFIER_BOUNDS["confidence_max"],
        )
        capital_modifier = self._clamp(
            capital_modifier,
            MODIFIER_BOUNDS["capital_min"],
            MODIFIER_BOUNDS["capital_max"],
        )
        
        # Determine interaction state
        interaction_state = self._determine_interaction_state(
            ta_input, exchange_input, fractal_input, patterns_detected
        )
        
        # Determine dominant signal
        dominant_signal = self._determine_dominant_signal(
            ta_support, exchange_support, fractal_support
        )
        
        # Build drivers
        drivers = self._build_drivers(
            ta_input, exchange_input, fractal_input,
            patterns_detected, confidence_modifier, capital_modifier
        )
        
        return FractalInteractionResult(
            symbol=symbol,
            timestamp=now,
            final_direction=final_direction,
            ta_support=ta_support,
            exchange_support=exchange_support,
            fractal_support=fractal_support,
            base_confidence=base_confidence,
            confidence_modifier=confidence_modifier,
            capital_modifier=capital_modifier,
            interaction_state=interaction_state,
            dominant_signal=dominant_signal,
            patterns_detected=patterns_detected,
            fractal_direction=fractal_input.direction,
            fractal_phase=fractal_input.phase,
            fractal_context_state=fractal_input.context_state,
            drivers=drivers,
        )
    
    # ═══════════════════════════════════════════════════════════
    # SUPPORT CALCULATION
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_ta_support(self, ta_input: TAInputForInteraction) -> float:
        """Calculate TA support score."""
        # Weighted average of conviction, trend_strength, setup_quality
        return (
            0.50 * ta_input.conviction +
            0.30 * ta_input.trend_strength +
            0.20 * ta_input.setup_quality
        )
    
    def _calculate_exchange_support(self, exchange_input: ExchangeInputForInteraction) -> float:
        """Calculate Exchange support score."""
        # Confidence adjusted by conflict ratio
        base = exchange_input.confidence
        conflict_penalty = exchange_input.conflict_ratio * 0.3
        return max(0.0, base - conflict_penalty)
    
    def _calculate_fractal_support(self, fractal_input: FractalInputForInteraction) -> float:
        """Calculate Fractal support score."""
        if fractal_input.context_state == "BLOCKED":
            return 0.0
        
        if fractal_input.context_state == "SUPPORTIVE":
            return fractal_input.fractal_strength
        
        if fractal_input.context_state == "CONFLICTED":
            return fractal_input.fractal_strength * 0.5
        
        # NEUTRAL
        return fractal_input.fractal_strength * 0.7
    
    # ═══════════════════════════════════════════════════════════
    # PATTERN CHECKS
    # ═══════════════════════════════════════════════════════════
    
    def _is_fractal_active(self, fractal_input: FractalInputForInteraction) -> bool:
        """Check if fractal should influence interaction."""
        # BLOCKED = ignore
        if fractal_input.context_state == "BLOCKED":
            return False
        
        # HOLD with NEUTRAL = no effect
        if fractal_input.direction == "HOLD" and fractal_input.context_state == "NEUTRAL":
            return False
        
        return True
    
    def _check_ta_fractal_alignment(
        self,
        ta_input: TAInputForInteraction,
        fractal_input: FractalInputForInteraction,
    ) -> bool:
        """
        Pattern 1: TA ↔ Fractal Alignment
        
        Conditions:
        - TA direction == Fractal direction
        - Fractal context_state == SUPPORTIVE
        """
        if fractal_input.context_state != TA_FRACTAL_ALIGNMENT_CONFIG["required_fractal_state"]:
            return False
        
        ta_dir = self.DIRECTION_NUMERIC.get(ta_input.direction, 0)
        fractal_dir = self.DIRECTION_NUMERIC.get(fractal_input.direction, 0)
        
        # Both must be directional and same sign
        if ta_dir == 0 or fractal_dir == 0:
            return False
        
        return ta_dir == fractal_dir
    
    def _check_exchange_fractal_alignment(
        self,
        exchange_input: ExchangeInputForInteraction,
        fractal_input: FractalInputForInteraction,
    ) -> bool:
        """
        Pattern 2: Exchange ↔ Fractal Alignment
        
        Conditions:
        - Exchange bias == Fractal direction
        - Fractal strength > 0.55
        """
        if fractal_input.fractal_strength < EXCHANGE_FRACTAL_ALIGNMENT_CONFIG["min_fractal_strength"]:
            return False
        
        exchange_dir = self.DIRECTION_NUMERIC.get(exchange_input.bias, 0)
        fractal_dir = self.DIRECTION_NUMERIC.get(fractal_input.direction, 0)
        
        if exchange_dir == 0 or fractal_dir == 0:
            return False
        
        return exchange_dir == fractal_dir
    
    def _check_fractal_conflict(
        self,
        ta_input: TAInputForInteraction,
        fractal_input: FractalInputForInteraction,
    ) -> bool:
        """
        Pattern 3: Fractal Conflict
        
        Conditions:
        - TA direction != Fractal direction (opposite)
        - Fractal strength >= 0.60
        """
        if fractal_input.fractal_strength < FRACTAL_CONFLICT_CONFIG["min_fractal_strength"]:
            return False
        
        ta_dir = self.DIRECTION_NUMERIC.get(ta_input.direction, 0)
        fractal_dir = self.DIRECTION_NUMERIC.get(fractal_input.direction, 0)
        
        # Both must be directional and opposite signs
        if ta_dir == 0 or fractal_dir == 0:
            return False
        
        return ta_dir == -fractal_dir
    
    def _check_phase_direction_support(
        self,
        ta_input: TAInputForInteraction,
        fractal_input: FractalInputForInteraction,
    ) -> bool:
        """
        Pattern 4: Phase Direction Support
        
        Conditions:
        - Fractal phase supports direction (MARKUP→LONG, MARKDOWN→SHORT)
        - Fractal strength >= 0.50
        """
        if fractal_input.fractal_strength < PHASE_DIRECTION_SUPPORT_CONFIG["min_fractal_strength"]:
            return False
        
        if fractal_input.phase is None:
            return False
        
        phase_map = PHASE_DIRECTION_SUPPORT_CONFIG["phase_direction_map"]
        expected_direction = phase_map.get(fractal_input.phase)
        
        if expected_direction is None:
            return False
        
        return ta_input.direction == expected_direction
    
    # ═══════════════════════════════════════════════════════════
    # STATE & SIGNAL DETERMINATION
    # ═══════════════════════════════════════════════════════════
    
    def _determine_interaction_state(
        self,
        ta_input: TAInputForInteraction,
        exchange_input: ExchangeInputForInteraction,
        fractal_input: FractalInputForInteraction,
        patterns_detected: List[str],
    ) -> FractalInteractionState:
        """Determine overall interaction state."""
        
        # Check if all three agree
        ta_dir = self.DIRECTION_NUMERIC.get(ta_input.direction, 0)
        exchange_dir = self.DIRECTION_NUMERIC.get(exchange_input.bias, 0)
        fractal_dir = self.DIRECTION_NUMERIC.get(fractal_input.direction, 0)
        
        # All directional and same sign = ALIGNED
        if ta_dir != 0 and exchange_dir != 0 and fractal_dir != 0:
            if ta_dir == exchange_dir == fractal_dir:
                return FractalInteractionState.ALIGNED
        
        # Any conflict pattern = CONFLICTED
        if "fractal_conflict" in patterns_detected:
            return FractalInteractionState.CONFLICTED
        
        # Some alignment = MIXED
        alignment_patterns = ["ta_fractal_alignment", "exchange_fractal_alignment", "phase_direction_support"]
        if any(p in patterns_detected for p in alignment_patterns):
            return FractalInteractionState.MIXED
        
        # Check signal strength
        strengths = [
            ta_input.conviction,
            exchange_input.confidence,
            fractal_input.fractal_strength if fractal_input.context_state != "BLOCKED" else 0,
        ]
        
        if all(s < 0.4 for s in strengths):
            return FractalInteractionState.WEAK
        
        return FractalInteractionState.MIXED
    
    def _determine_dominant_signal(
        self,
        ta_support: float,
        exchange_support: float,
        fractal_support: float,
    ) -> DominantSignal:
        """Determine which signal source dominates."""
        
        supports = {
            "TA": ta_support,
            "EXCHANGE": exchange_support,
            "FRACTAL": fractal_support,
        }
        
        # Find max
        max_support = max(supports.values())
        max_sources = [k for k, v in supports.items() if v == max_support]
        
        if len(max_sources) > 1:
            return DominantSignal.MIXED
        
        return DominantSignal[max_sources[0]]
    
    # ═══════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════
    
    def _get_fractal_input(self, symbol: str) -> FractalInputForInteraction:
        """Get FractalInputForInteraction from FractalContextEngine."""
        if self.fractal_engine is None:
            return FractalInputForInteraction()  # Default blocked
        
        try:
            import asyncio
            
            # Run async method
            loop = asyncio.new_event_loop()
            try:
                context = loop.run_until_complete(
                    self.fractal_engine.build_context(symbol)
                )
            finally:
                loop.close()
            
            return FractalInputForInteraction(
                direction=context.direction,
                confidence=context.confidence,
                reliability=context.reliability,
                phase=context.phase,
                context_state=context.context_state,
                fractal_strength=context.fractal_strength,
                dominant_horizon=context.dominant_horizon,
                expected_return=context.expected_return,
            )
        except Exception:
            return FractalInputForInteraction()  # Default blocked
    
    def _clamp(self, value: float, min_val: float, max_val: float) -> float:
        """Clamp value to range."""
        return max(min_val, min(max_val, value))
    
    def _build_drivers(
        self,
        ta_input: TAInputForInteraction,
        exchange_input: ExchangeInputForInteraction,
        fractal_input: FractalInputForInteraction,
        patterns_detected: List[str],
        confidence_modifier: float,
        capital_modifier: float,
    ) -> Dict[str, Any]:
        """Build explainability drivers."""
        return {
            "ta_direction": ta_input.direction,
            "exchange_bias": exchange_input.bias,
            "fractal_direction": fractal_input.direction,
            "fractal_phase": fractal_input.phase,
            "fractal_context_state": fractal_input.context_state,
            "fractal_strength": round(fractal_input.fractal_strength, 4),
            "patterns_detected": patterns_detected,
            "pattern_count": len(patterns_detected),
            "confidence_modifier": round(confidence_modifier, 4),
            "capital_modifier": round(capital_modifier, 4),
            "fractal_active": self._is_fractal_active(fractal_input),
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[FractalInteractionEngine] = None


def get_fractal_interaction_engine() -> FractalInteractionEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FractalInteractionEngine()
    return _engine
