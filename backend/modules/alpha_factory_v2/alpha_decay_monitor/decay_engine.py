"""
Alpha Decay Monitor — Engine

Core logic for detecting alpha decay.

Features:
- Alpha drift calculation
- Decay rate calculation
- State classification (STABLE, DECAYING, CRITICAL)
- Action recommendation (KEEP, REDUCE, DEPRECATE)
- Modifier computation
"""

from typing import List, Optional, Dict
from datetime import datetime

from .decay_types import (
    AlphaDecayState,
    DecayState,
    RecommendedAction,
    DecaySummary,
    DRIFT_STABLE_MAX,
    DRIFT_DECAYING_MAX,
    DECAY_RATE_STABLE_MAX,
    DECAY_RATE_DECAYING_MAX,
    MODIFIERS,
)
from ..alpha_registry import AlphaRegistry, get_alpha_registry, RegistryAlphaFactor


class AlphaDecayEngine:
    """
    Alpha Decay Engine.
    
    Detects degradation in alpha factors and recommends actions.
    
    Classification rules:
    - STABLE: drift < 0.10 AND decay_rate < 0.10
    - DECAYING: 0.10 ≤ drift < 0.20 OR 0.10 ≤ decay_rate < 0.25
    - CRITICAL: drift ≥ 0.20 OR decay_rate ≥ 0.25
    """
    
    def __init__(self, registry: Optional[AlphaRegistry] = None):
        self._registry = registry or get_alpha_registry()
        self._previous_scores: Dict[str, float] = {}  # factor_id -> previous_alpha_score
        self._decay_states: Dict[str, AlphaDecayState] = {}
    
    # ═══════════════════════════════════════════════════════════
    # Core Metrics
    # ═══════════════════════════════════════════════════════════
    
    def calculate_alpha_drift(
        self,
        current_score: float,
        previous_score: float,
    ) -> float:
        """
        Calculate alpha drift.
        
        Formula: |current_alpha_score - previous_alpha_score|
        """
        return abs(current_score - previous_score)
    
    def calculate_decay_rate(
        self,
        current_score: float,
        previous_score: float,
    ) -> float:
        """
        Calculate decay rate.
        
        Formula: (previous - current) / previous
        Returns 0 if alpha is improving (current >= previous)
        """
        if previous_score <= 0:
            return 0.0
        
        if current_score >= previous_score:
            return 0.0  # Alpha improving, no decay
        
        decay = (previous_score - current_score) / previous_score
        return round(decay, 4)
    
    # ═══════════════════════════════════════════════════════════
    # Classification
    # ═══════════════════════════════════════════════════════════
    
    def classify_decay_state(
        self,
        alpha_drift: float,
        decay_rate: float,
    ) -> DecayState:
        """
        Classify decay state based on drift and rate.
        
        Rules:
        - CRITICAL: drift ≥ 0.20 OR decay_rate ≥ 0.25
        - DECAYING: 0.10 ≤ drift < 0.20 OR 0.10 ≤ decay_rate < 0.25
        - STABLE: drift < 0.10 AND decay_rate < 0.10
        """
        # Check CRITICAL first
        if alpha_drift >= DRIFT_DECAYING_MAX or decay_rate >= DECAY_RATE_DECAYING_MAX:
            return "CRITICAL"
        
        # Check DECAYING
        if alpha_drift >= DRIFT_STABLE_MAX or decay_rate >= DECAY_RATE_STABLE_MAX:
            return "DECAYING"
        
        # Default STABLE
        return "STABLE"
    
    def get_recommended_action(
        self,
        decay_state: DecayState,
    ) -> RecommendedAction:
        """
        Get recommended action based on decay state.
        
        STABLE → KEEP
        DECAYING → REDUCE
        CRITICAL → DEPRECATE
        """
        if decay_state == "STABLE":
            return "KEEP"
        elif decay_state == "DECAYING":
            return "REDUCE"
        else:
            return "DEPRECATE"
    
    def get_modifiers(
        self,
        decay_state: DecayState,
    ) -> Dict[str, float]:
        """
        Get confidence and capital modifiers for decay state.
        """
        return MODIFIERS.get(decay_state, MODIFIERS["STABLE"])
    
    # ═══════════════════════════════════════════════════════════
    # Reason Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_reason(
        self,
        decay_state: DecayState,
        alpha_drift: float,
        decay_rate: float,
    ) -> str:
        """Generate human-readable reason for decay state."""
        if decay_state == "STABLE":
            return "alpha factor is stable with minimal drift"
        
        elif decay_state == "DECAYING":
            parts = []
            if alpha_drift >= DRIFT_STABLE_MAX:
                parts.append(f"drift {alpha_drift:.2%}")
            if decay_rate >= DECAY_RATE_STABLE_MAX:
                parts.append(f"decay rate {decay_rate:.2%}")
            return f"alpha factor losing strength ({', '.join(parts)}) and approaching critical decay threshold"
        
        else:  # CRITICAL
            parts = []
            if alpha_drift >= DRIFT_DECAYING_MAX:
                parts.append(f"extreme drift {alpha_drift:.2%}")
            if decay_rate >= DECAY_RATE_DECAYING_MAX:
                parts.append(f"high decay rate {decay_rate:.2%}")
            return f"alpha factor in critical decay ({', '.join(parts)}) - immediate deprecation recommended"
    
    # ═══════════════════════════════════════════════════════════
    # Single Factor Analysis
    # ═══════════════════════════════════════════════════════════
    
    def analyze_factor(
        self,
        factor_id: str,
        factor_name: str,
        current_score: float,
        previous_score: float,
    ) -> AlphaDecayState:
        """
        Analyze decay for a single factor.
        
        Returns AlphaDecayState with full classification.
        """
        # Calculate metrics
        alpha_drift = self.calculate_alpha_drift(current_score, previous_score)
        decay_rate = self.calculate_decay_rate(current_score, previous_score)
        
        # Classify
        decay_state = self.classify_decay_state(alpha_drift, decay_rate)
        action = self.get_recommended_action(decay_state)
        modifiers = self.get_modifiers(decay_state)
        reason = self.generate_reason(decay_state, alpha_drift, decay_rate)
        
        return AlphaDecayState(
            factor_id=factor_id,
            factor_name=factor_name,
            current_alpha_score=round(current_score, 4),
            previous_alpha_score=round(previous_score, 4),
            alpha_drift=round(alpha_drift, 4),
            decay_rate=round(decay_rate, 4),
            decay_state=decay_state,
            recommended_action=action,
            confidence_modifier=modifiers["confidence_modifier"],
            capital_modifier=modifiers["capital_modifier"],
            reason=reason,
        )
    
    # ═══════════════════════════════════════════════════════════
    # Bulk Analysis
    # ═══════════════════════════════════════════════════════════
    
    async def compute_all_decay(self) -> List[AlphaDecayState]:
        """
        Compute decay for all factors in registry.
        
        Uses previous scores from last computation or registry history.
        """
        all_factors = await self._registry.get_all_factors()
        
        results = []
        
        for factor in all_factors:
            # Get previous score
            if factor.factor_id in self._previous_scores:
                previous_score = self._previous_scores[factor.factor_id]
            else:
                # First time seeing this factor, use current as previous
                previous_score = factor.alpha_score
            
            decay_state = self.analyze_factor(
                factor_id=factor.factor_id,
                factor_name=factor.name,
                current_score=factor.alpha_score,
                previous_score=previous_score,
            )
            
            results.append(decay_state)
            self._decay_states[factor.factor_id] = decay_state
        
        # Update previous scores for next computation
        self._previous_scores = {
            f.factor_id: f.alpha_score for f in all_factors
        }
        
        return results
    
    async def recompute_decay(self) -> List[AlphaDecayState]:
        """
        Force recompute of all decay states.
        
        Same as compute_all_decay but explicitly clears cache first.
        """
        return await self.compute_all_decay()
    
    # ═══════════════════════════════════════════════════════════
    # Retrieval
    # ═══════════════════════════════════════════════════════════
    
    def get_decay_state(
        self,
        factor_id: str,
    ) -> Optional[AlphaDecayState]:
        """Get decay state for a specific factor."""
        return self._decay_states.get(factor_id)
    
    def get_all_decay_states(self) -> List[AlphaDecayState]:
        """Get all computed decay states."""
        return list(self._decay_states.values())
    
    def get_critical_factors(self) -> List[AlphaDecayState]:
        """Get all factors in CRITICAL state."""
        return [
            s for s in self._decay_states.values()
            if s.decay_state == "CRITICAL"
        ]
    
    def get_decaying_factors(self) -> List[AlphaDecayState]:
        """Get all factors in DECAYING state."""
        return [
            s for s in self._decay_states.values()
            if s.decay_state == "DECAYING"
        ]
    
    def get_stable_factors(self) -> List[AlphaDecayState]:
        """Get all factors in STABLE state."""
        return [
            s for s in self._decay_states.values()
            if s.decay_state == "STABLE"
        ]
    
    # ═══════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(self) -> DecaySummary:
        """Get decay summary statistics."""
        states = self.get_all_decay_states()
        
        if not states:
            return DecaySummary(
                total_factors=0,
                stable_count=0,
                decaying_count=0,
                critical_count=0,
                average_decay_rate=0.0,
                max_decay_rate=0.0,
                critical_factors=[],
            )
        
        stable = [s for s in states if s.decay_state == "STABLE"]
        decaying = [s for s in states if s.decay_state == "DECAYING"]
        critical = [s for s in states if s.decay_state == "CRITICAL"]
        
        decay_rates = [s.decay_rate for s in states]
        avg_decay = sum(decay_rates) / len(decay_rates) if decay_rates else 0.0
        max_decay = max(decay_rates) if decay_rates else 0.0
        
        return DecaySummary(
            total_factors=len(states),
            stable_count=len(stable),
            decaying_count=len(decaying),
            critical_count=len(critical),
            average_decay_rate=round(avg_decay, 4),
            max_decay_rate=round(max_decay, 4),
            critical_factors=[s.factor_id for s in critical],
        )
    
    # ═══════════════════════════════════════════════════════════
    # Manual Control
    # ═══════════════════════════════════════════════════════════
    
    def set_previous_scores(
        self,
        scores: Dict[str, float],
    ) -> None:
        """Set previous scores manually (for testing)."""
        self._previous_scores = scores.copy()


# Singleton
_engine: Optional[AlphaDecayEngine] = None


def get_alpha_decay_engine() -> AlphaDecayEngine:
    """Get singleton instance of AlphaDecayEngine."""
    global _engine
    if _engine is None:
        _engine = AlphaDecayEngine(registry=get_alpha_registry())
    return _engine
