"""
Alpha Decay Engine

PHASE 43.8 — Alpha Decay Engine

Manages signal aging and decay.

Pipeline position:
Market Intelligence → Hypothesis Engine → Alpha Decay → Portfolio Manager → Execution

Key effects:
- ↓ Reduces unnecessary trades
- ↓ Reduces noise trades
- ↑ Improves timing
- ↑ Increases Sharpe

Formula:
    decay_factor = exp(-age_minutes / half_life)
    adjusted_confidence = initial_confidence × decay_factor

Dynamic half-lives:
    TREND: 120 min
    BREAKOUT: 90 min
    MEAN_REVERSION: 30 min
    FRACTAL: 180 min
    CAPITAL_FLOW: 240 min
    REGIME: 360 min
    DEFAULT: 60 min
"""

from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
import math

from .decay_types import (
    DecayStage,
    SignalType,
    AlphaDecayState,
    AlphaDecayConfig,
    DecayComputeResult,
    DecaySummary,
    SIGNAL_HALF_LIVES,
    DECAY_STAGE_THRESHOLDS,
)


class AlphaDecayEngine:
    """
    Alpha Decay Engine — PHASE 43.8
    
    Tracks signal aging and adjusts confidence/execution eligibility.
    
    Key responsibilities:
    1. Track signal age
    2. Compute decay factor
    3. Adjust confidence
    4. Block expired signals
    5. Integrate with Hypothesis/Portfolio/Execution
    """
    
    def __init__(self, config: Optional[AlphaDecayConfig] = None):
        self._config = config or AlphaDecayConfig()
        
        # In-memory cache of decay states
        self._decay_states: Dict[str, AlphaDecayState] = {}
        
        # Statistics
        self._total_created: int = 0
        self._total_expired: int = 0
        self._total_blocked: int = 0
    
    # ═══════════════════════════════════════════════════════════
    # 1. Core Decay Operations
    # ═══════════════════════════════════════════════════════════
    
    def create_decay_state(
        self,
        hypothesis_id: str,
        symbol: str,
        initial_confidence: float,
        signal_type: SignalType = SignalType.DEFAULT,
        source: str = "hypothesis_engine",
        metadata: Optional[Dict] = None,
    ) -> AlphaDecayState:
        """
        Create a new decay state for a signal/hypothesis.
        
        Called when a new hypothesis is generated.
        """
        # Get half-life for signal type
        half_life = self._get_half_life(signal_type)
        
        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=half_life * 4)
        
        state = AlphaDecayState(
            hypothesis_id=hypothesis_id,
            symbol=symbol,
            signal_type=signal_type,
            initial_confidence=initial_confidence,
            decay_factor=1.0,
            adjusted_confidence=initial_confidence,
            half_life_minutes=half_life,
            decay_stage=DecayStage.FRESH,
            expires_at=expires_at,
            source=source,
            metadata=metadata or {},
        )
        
        # Store in cache
        self._decay_states[hypothesis_id] = state
        self._total_created += 1
        
        return state
    
    def compute_decay(self, hypothesis_id: str) -> Optional[DecayComputeResult]:
        """
        Compute decay for a specific hypothesis.
        
        Returns the current decay state.
        """
        state = self._decay_states.get(hypothesis_id)
        if not state:
            return None
        
        # Recompute decay
        state.compute_decay()
        
        # Check if should be blocked
        if state.is_expired and not state.execution_blocked:
            state.execution_blocked = True
            self._total_blocked += 1
        
        return DecayComputeResult(
            hypothesis_id=state.hypothesis_id,
            symbol=state.symbol,
            age_minutes=state.age_minutes,
            decay_factor=round(state.decay_factor, 4),
            adjusted_confidence=round(state.adjusted_confidence, 4),
            decay_stage=state.decay_stage.value,
            is_expired=state.is_expired,
            execution_blocked=state.execution_blocked,
            half_life_used=state.half_life_minutes,
            message=self._get_decay_message(state),
        )
    
    def recompute_all(self) -> List[DecayComputeResult]:
        """Recompute decay for all active states."""
        results = []
        
        for hypothesis_id in list(self._decay_states.keys()):
            result = self.compute_decay(hypothesis_id)
            if result:
                results.append(result)
        
        return results
    
    def expire_old_signals(self, max_age_hours: Optional[int] = None) -> int:
        """
        Expire signals that are too old.
        
        Returns count of expired signals.
        """
        max_age = max_age_hours or self._config.max_age_hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age)
        
        expired_count = 0
        
        for hypothesis_id, state in list(self._decay_states.items()):
            if state.created_at < cutoff or state.decay_factor < self._config.expiration_threshold:
                state.is_expired = True
                state.execution_blocked = True
                state.decay_stage = DecayStage.EXPIRED
                expired_count += 1
                self._total_expired += 1
        
        return expired_count
    
    def remove_expired(self) -> int:
        """Remove expired states from cache."""
        removed = 0
        
        for hypothesis_id in list(self._decay_states.keys()):
            state = self._decay_states[hypothesis_id]
            if state.is_expired:
                del self._decay_states[hypothesis_id]
                removed += 1
        
        return removed
    
    # ═══════════════════════════════════════════════════════════
    # 2. Integration Methods
    # ═══════════════════════════════════════════════════════════
    
    def get_confidence_modifier(
        self,
        hypothesis_id: str,
        original_confidence: float,
    ) -> Dict:
        """
        Get decay-adjusted confidence for Hypothesis Engine integration.
        
        Returns:
            Dict with adjusted_confidence and decay info
        """
        state = self._decay_states.get(hypothesis_id)
        
        if not state:
            # No decay tracking — return original
            return {
                "original_confidence": original_confidence,
                "adjusted_confidence": original_confidence,
                "decay_factor": 1.0,
                "decay_stage": "FRESH",
                "has_decay_state": False,
            }
        
        # Recompute
        state.compute_decay()
        
        return {
            "original_confidence": original_confidence,
            "adjusted_confidence": round(state.adjusted_confidence, 4),
            "decay_factor": round(state.decay_factor, 4),
            "decay_stage": state.decay_stage.value,
            "age_minutes": state.age_minutes,
            "is_expired": state.is_expired,
            "execution_blocked": state.execution_blocked,
            "has_decay_state": True,
        }
    
    def get_position_size_modifier(
        self,
        hypothesis_id: str,
        base_size: float,
    ) -> Dict:
        """
        Get decay-adjusted position size for Portfolio Manager integration.
        
        position_size = base_size × decay_factor
        """
        state = self._decay_states.get(hypothesis_id)
        
        if not state:
            return {
                "base_size": base_size,
                "adjusted_size": base_size,
                "decay_factor": 1.0,
                "size_reduction_pct": 0.0,
                "has_decay_state": False,
            }
        
        state.compute_decay()
        
        adjusted_size = base_size * state.decay_factor
        reduction_pct = (1 - state.decay_factor) * 100
        
        return {
            "base_size": base_size,
            "adjusted_size": round(adjusted_size, 4),
            "decay_factor": round(state.decay_factor, 4),
            "size_reduction_pct": round(reduction_pct, 2),
            "decay_stage": state.decay_stage.value,
            "is_expired": state.is_expired,
            "has_decay_state": True,
        }
    
    def check_execution_eligibility(self, hypothesis_id: str) -> Dict:
        """
        Check if signal is eligible for execution.
        
        For Execution Brain integration.
        """
        state = self._decay_states.get(hypothesis_id)
        
        if not state:
            return {
                "eligible": True,
                "reason": "No decay tracking",
                "decay_stage": "UNKNOWN",
                "has_decay_state": False,
            }
        
        state.compute_decay()
        
        if state.execution_blocked or state.is_expired:
            return {
                "eligible": False,
                "reason": f"Signal expired (decay_factor={state.decay_factor:.4f} < {self._config.expiration_threshold})",
                "decay_stage": state.decay_stage.value,
                "decay_factor": round(state.decay_factor, 4),
                "age_minutes": state.age_minutes,
                "has_decay_state": True,
            }
        
        return {
            "eligible": True,
            "reason": f"Signal active ({state.decay_stage.value})",
            "decay_stage": state.decay_stage.value,
            "decay_factor": round(state.decay_factor, 4),
            "age_minutes": state.age_minutes,
            "has_decay_state": True,
        }
    
    # ═══════════════════════════════════════════════════════════
    # 3. Getters
    # ═══════════════════════════════════════════════════════════
    
    def get_state(self, hypothesis_id: str) -> Optional[AlphaDecayState]:
        """Get decay state for a hypothesis."""
        state = self._decay_states.get(hypothesis_id)
        if state:
            state.compute_decay()
        return state
    
    def get_all_states(self) -> Dict[str, AlphaDecayState]:
        """Get all decay states."""
        return self._decay_states.copy()
    
    def get_summary(self, symbol: Optional[str] = None) -> DecaySummary:
        """
        Get summary of all decay states.
        
        Optionally filter by symbol.
        """
        # Recompute all
        states = list(self._decay_states.values())
        if symbol:
            states = [s for s in states if s.symbol == symbol]
        
        # Compute each
        for state in states:
            state.compute_decay()
        
        # Aggregate
        summary = DecaySummary(
            total_signals=len(states),
            fresh_count=sum(1 for s in states if s.decay_stage == DecayStage.FRESH),
            active_count=sum(1 for s in states if s.decay_stage == DecayStage.ACTIVE),
            weakening_count=sum(1 for s in states if s.decay_stage == DecayStage.WEAKENING),
            expired_count=sum(1 for s in states if s.decay_stage == DecayStage.EXPIRED),
            blocked_count=sum(1 for s in states if s.execution_blocked),
            avg_decay_factor=sum(s.decay_factor for s in states) / len(states) if states else 0.0,
            avg_age_minutes=sum(s.age_minutes for s in states) / len(states) if states else 0.0,
            signals=[
                DecayComputeResult(
                    hypothesis_id=s.hypothesis_id,
                    symbol=s.symbol,
                    age_minutes=s.age_minutes,
                    decay_factor=round(s.decay_factor, 4),
                    adjusted_confidence=round(s.adjusted_confidence, 4),
                    decay_stage=s.decay_stage.value,
                    is_expired=s.is_expired,
                    execution_blocked=s.execution_blocked,
                    half_life_used=s.half_life_minutes,
                )
                for s in states
            ],
        )
        
        return summary
    
    def get_config(self) -> AlphaDecayConfig:
        """Get engine configuration."""
        return self._config
    
    def update_config(self, config: AlphaDecayConfig):
        """Update engine configuration."""
        self._config = config
    
    # ═══════════════════════════════════════════════════════════
    # 4. Helper Methods
    # ═══════════════════════════════════════════════════════════
    
    def _get_half_life(self, signal_type: SignalType) -> int:
        """Get half-life for signal type."""
        if self._config.use_dynamic_half_life:
            return SIGNAL_HALF_LIVES.get(signal_type, self._config.default_half_life_minutes)
        return self._config.default_half_life_minutes
    
    def _get_decay_message(self, state: AlphaDecayState) -> str:
        """Generate human-readable decay message."""
        if state.decay_stage == DecayStage.FRESH:
            return f"Signal fresh ({state.age_minutes}min old, {state.decay_factor:.2%} strength)"
        elif state.decay_stage == DecayStage.ACTIVE:
            return f"Signal active ({state.age_minutes}min old, {state.decay_factor:.2%} strength)"
        elif state.decay_stage == DecayStage.WEAKENING:
            return f"Signal weakening ({state.age_minutes}min old, {state.decay_factor:.2%} strength)"
        else:
            return f"Signal EXPIRED ({state.age_minutes}min old, execution blocked)"
    
    def get_statistics(self) -> Dict:
        """Get engine statistics."""
        return {
            "phase": "43.8",
            "total_created": self._total_created,
            "total_expired": self._total_expired,
            "total_blocked": self._total_blocked,
            "active_states": len(self._decay_states),
            "config": {
                "default_half_life": self._config.default_half_life_minutes,
                "dynamic_half_life": self._config.use_dynamic_half_life,
                "expiration_threshold": self._config.expiration_threshold,
                "auto_expire_enabled": self._config.auto_expire_enabled,
            },
            "half_lives": {st.value: hl for st, hl in SIGNAL_HALF_LIVES.items()},
        }


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_decay_engine: Optional[AlphaDecayEngine] = None


def get_alpha_decay_engine() -> AlphaDecayEngine:
    """Get singleton instance."""
    global _decay_engine
    if _decay_engine is None:
        _decay_engine = AlphaDecayEngine()
    return _decay_engine
