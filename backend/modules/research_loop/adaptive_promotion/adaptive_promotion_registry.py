"""
PHASE 20.3 — Adaptive Promotion Registry
========================================
Tracks lifecycle history for factors.

Stores:
- Current state
- Previous state
- Transition history
- Timestamps
- Reasons
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field

from modules.research_loop.adaptive_promotion.adaptive_promotion_types import (
    LifecycleState,
    TransitionAction,
    TransitionStrength,
    AdaptivePromotionDecision,
)


@dataclass
class LifecycleTransition:
    """Single lifecycle transition record."""
    factor_name: str
    from_state: LifecycleState
    to_state: LifecycleState
    action: TransitionAction
    strength: TransitionStrength
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_name": self.factor_name,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "action": self.action.value,
            "strength": self.strength.value,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class FactorLifecycleState:
    """Current lifecycle state for a factor."""
    factor_name: str
    current_state: LifecycleState
    previous_state: Optional[LifecycleState]
    transitions: List[LifecycleTransition] = field(default_factory=list)
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_name": self.factor_name,
            "current_state": self.current_state.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "transition_count": len(self.transitions),
            "last_updated": self.last_updated.isoformat(),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["transitions"] = [t.to_dict() for t in self.transitions[-10:]]  # Last 10
        return result


class AdaptivePromotionRegistry:
    """
    Registry for tracking factor lifecycle states and history.
    """
    
    def __init__(self):
        """Initialize registry."""
        self._factors: Dict[str, FactorLifecycleState] = {}
        self._initialize_sample_factors()
    
    def _initialize_sample_factors(self):
        """Initialize with sample factors."""
        sample_factors = [
            ("trend_breakout_factor", LifecycleState.LIVE),
            ("mean_reversion_factor", LifecycleState.LIVE),
            ("breakout_factor", LifecycleState.CANDIDATE),
            ("flow_factor", LifecycleState.LIVE),
            ("funding_factor", LifecycleState.SHADOW),
            ("structure_factor", LifecycleState.REDUCED),
            ("volatility_factor", LifecycleState.CANDIDATE),
            ("momentum_factor", LifecycleState.LIVE),
            ("liquidation_factor", LifecycleState.SHADOW),
            ("correlation_factor", LifecycleState.LIVE),
        ]
        
        for name, state in sample_factors:
            self._factors[name] = FactorLifecycleState(
                factor_name=name,
                current_state=state,
                previous_state=None,
            )
    
    # ═══════════════════════════════════════════════════════════
    # READ OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def get_factor_state(self, factor_name: str) -> Optional[FactorLifecycleState]:
        """Get current state for a factor."""
        return self._factors.get(factor_name)
    
    def get_current_state(self, factor_name: str) -> Optional[LifecycleState]:
        """Get just the lifecycle state."""
        factor = self._factors.get(factor_name)
        return factor.current_state if factor else None
    
    def get_all_factors(self) -> Dict[str, FactorLifecycleState]:
        """Get all factor states."""
        return self._factors.copy()
    
    def get_factor_names(self) -> List[str]:
        """Get all factor names."""
        return list(self._factors.keys())
    
    def get_factors_by_state(self, state: LifecycleState) -> List[str]:
        """Get factors in a specific state."""
        return [
            name for name, factor in self._factors.items()
            if factor.current_state == state
        ]
    
    def get_transition_history(
        self,
        factor_name: str,
        limit: int = 10,
    ) -> List[LifecycleTransition]:
        """Get transition history for a factor."""
        factor = self._factors.get(factor_name)
        if factor is None:
            return []
        return factor.transitions[-limit:]
    
    # ═══════════════════════════════════════════════════════════
    # WRITE OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def record_transition(
        self,
        decision: AdaptivePromotionDecision,
    ) -> bool:
        """
        Record a lifecycle transition.
        
        Returns True if transition was recorded.
        """
        factor_name = decision.factor_name
        
        # Get or create factor state
        if factor_name not in self._factors:
            self._factors[factor_name] = FactorLifecycleState(
                factor_name=factor_name,
                current_state=decision.current_state,
                previous_state=None,
            )
        
        factor = self._factors[factor_name]
        
        # Only record if action is not HOLD
        if decision.transition_action == TransitionAction.HOLD:
            return False
        
        # Create transition record
        transition = LifecycleTransition(
            factor_name=factor_name,
            from_state=decision.current_state,
            to_state=decision.recommended_state,
            action=decision.transition_action,
            strength=decision.transition_strength,
            reason=decision.reason,
        )
        
        # Update factor state
        factor.previous_state = factor.current_state
        factor.current_state = decision.recommended_state
        factor.transitions.append(transition)
        factor.last_updated = datetime.now(timezone.utc)
        
        return True
    
    def set_state(
        self,
        factor_name: str,
        state: LifecycleState,
        reason: str = "manual override",
    ):
        """Manually set a factor's state."""
        if factor_name not in self._factors:
            self._factors[factor_name] = FactorLifecycleState(
                factor_name=factor_name,
                current_state=state,
                previous_state=None,
            )
        else:
            factor = self._factors[factor_name]
            factor.previous_state = factor.current_state
            factor.current_state = state
            factor.last_updated = datetime.now(timezone.utc)
            
            # Record transition
            transition = LifecycleTransition(
                factor_name=factor_name,
                from_state=factor.previous_state if factor.previous_state else state,
                to_state=state,
                action=TransitionAction.HOLD,
                strength=TransitionStrength.LOW,
                reason=reason,
            )
            factor.transitions.append(transition)
    
    # ═══════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════
    
    def get_state_distribution(self) -> Dict[str, int]:
        """Get count of factors by state."""
        distribution = {state.value: 0 for state in LifecycleState}
        for factor in self._factors.values():
            distribution[factor.current_state.value] += 1
        return distribution
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        distribution = self.get_state_distribution()
        total_transitions = sum(
            len(f.transitions) for f in self._factors.values()
        )
        
        return {
            "total_factors": len(self._factors),
            "state_distribution": distribution,
            "total_transitions": total_transitions,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_registry: Optional[AdaptivePromotionRegistry] = None


def get_adaptive_promotion_registry() -> AdaptivePromotionRegistry:
    """Get singleton registry instance."""
    global _registry
    if _registry is None:
        _registry = AdaptivePromotionRegistry()
    return _registry
