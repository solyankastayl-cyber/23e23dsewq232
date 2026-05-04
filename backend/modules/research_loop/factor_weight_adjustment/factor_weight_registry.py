"""
PHASE 20.2 — Factor Weight Registry
===================================
Registry for storing factor weights and adjustment history.

Provides:
- Weight storage
- History tracking
- Persistence
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field

from modules.research_loop.factor_weight_adjustment.factor_weight_adjustment_types import (
    FactorWeightState,
    FactorWeightAdjustment,
    AdjustmentAction,
)


# ══════════════════════════════════════════════════════════════
# DEFAULT FACTOR WEIGHTS
# ══════════════════════════════════════════════════════════════

DEFAULT_FACTOR_WEIGHTS = {
    "trend_breakout_factor": 0.15,
    "trend_following_factor": 0.15,
    "mean_reversion_factor": 0.12,
    "breakout_factor": 0.12,
    "flow_factor": 0.10,
    "liquidation_factor": 0.10,
    "funding_factor": 0.10,
    "structure_factor": 0.08,
    "volatility_factor": 0.08,
}

DEFAULT_DEPLOYMENT_STATES = {
    "trend_breakout_factor": "LIVE",
    "trend_following_factor": "LIVE",
    "mean_reversion_factor": "LIVE",
    "breakout_factor": "LIVE",
    "flow_factor": "LIVE",
    "liquidation_factor": "LIVE",
    "funding_factor": "LIVE",
    "structure_factor": "LIVE",
    "volatility_factor": "SHADOW",
}

DEFAULT_GOVERNANCE_STATES = {
    "trend_breakout_factor": "STABLE",
    "trend_following_factor": "STABLE",
    "mean_reversion_factor": "STABLE",
    "breakout_factor": "STABLE",
    "flow_factor": "STABLE",
    "liquidation_factor": "WATCHLIST",
    "funding_factor": "ELITE",
    "structure_factor": "WATCHLIST",
    "volatility_factor": "CANDIDATE",
}


@dataclass
class AdjustmentHistoryEntry:
    """Single entry in adjustment history."""
    timestamp: datetime
    previous_weight: float
    new_weight: float
    action: AdjustmentAction
    reason: str


class FactorWeightRegistry:
    """
    Registry for factor weights.
    
    Stores current weights, previous weights, and adjustment history.
    """
    
    def __init__(self):
        """Initialize registry."""
        self._weights: Dict[str, FactorWeightState] = {}
        self._history: Dict[str, List[AdjustmentHistoryEntry]] = {}
        self._initialized = False
    
    def initialize_defaults(self):
        """Initialize with default weights."""
        if self._initialized:
            return
        
        now = datetime.now(timezone.utc)
        
        for factor_name, weight in DEFAULT_FACTOR_WEIGHTS.items():
            self._weights[factor_name] = FactorWeightState(
                factor_name=factor_name,
                current_weight=weight,
                previous_weight=weight,
                deployment_state=DEFAULT_DEPLOYMENT_STATES.get(factor_name, "LIVE"),
                governance_state=DEFAULT_GOVERNANCE_STATES.get(factor_name, "STABLE"),
                last_updated=now,
            )
            self._history[factor_name] = []
        
        self._initialized = True
    
    def get_weight(self, factor_name: str) -> Optional[FactorWeightState]:
        """Get weight state for factor."""
        return self._weights.get(factor_name)
    
    def get_all_weights(self) -> List[FactorWeightState]:
        """Get all weight states."""
        return list(self._weights.values())
    
    def get_factor_names(self) -> List[str]:
        """Get all factor names."""
        return list(self._weights.keys())
    
    def update_weight(
        self,
        factor_name: str,
        new_weight: float,
        action: AdjustmentAction,
        reason: str,
    ):
        """
        Update factor weight.
        
        Stores history and updates state.
        """
        now = datetime.now(timezone.utc)
        
        if factor_name not in self._weights:
            # Create new entry
            self._weights[factor_name] = FactorWeightState(
                factor_name=factor_name,
                current_weight=new_weight,
                previous_weight=new_weight,
                deployment_state="LIVE",
                governance_state="STABLE",
                last_updated=now,
            )
            self._history[factor_name] = []
            return
        
        state = self._weights[factor_name]
        
        # Record history
        history_entry = AdjustmentHistoryEntry(
            timestamp=now,
            previous_weight=state.current_weight,
            new_weight=new_weight,
            action=action,
            reason=reason,
        )
        
        if factor_name not in self._history:
            self._history[factor_name] = []
        self._history[factor_name].append(history_entry)
        
        # Update state
        state.previous_weight = state.current_weight
        state.current_weight = new_weight
        state.last_updated = now
    
    def get_history(self, factor_name: str) -> List[AdjustmentHistoryEntry]:
        """Get adjustment history for factor."""
        return self._history.get(factor_name, [])
    
    def get_recent_adjustments(
        self,
        factor_name: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get recent adjustments as dicts."""
        history = self.get_history(factor_name)
        recent = history[-limit:] if history else []
        
        return [
            {
                "timestamp": h.timestamp.isoformat(),
                "previous_weight": round(h.previous_weight, 4),
                "new_weight": round(h.new_weight, 4),
                "action": h.action.value,
                "reason": h.reason,
            }
            for h in recent
        ]
    
    def set_deployment_state(self, factor_name: str, state: str):
        """Set deployment state for factor."""
        if factor_name in self._weights:
            self._weights[factor_name].deployment_state = state
    
    def set_governance_state(self, factor_name: str, state: str):
        """Set governance state for factor."""
        if factor_name in self._weights:
            self._weights[factor_name].governance_state = state
    
    def get_registry_summary(self) -> Dict[str, Any]:
        """Get registry summary."""
        weights = self.get_all_weights()
        
        total_weight = sum(w.current_weight for w in weights)
        
        return {
            "total_factors": len(weights),
            "total_weight": round(total_weight, 4),
            "factors": [
                {
                    "name": w.factor_name,
                    "weight": round(w.current_weight, 4),
                    "deployment": w.deployment_state,
                    "governance": w.governance_state,
                }
                for w in weights
            ],
        }
    
    def clear(self):
        """Clear registry."""
        self._weights.clear()
        self._history.clear()
        self._initialized = False


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_registry: Optional[FactorWeightRegistry] = None


def get_factor_weight_registry() -> FactorWeightRegistry:
    """Get singleton registry instance."""
    global _registry
    if _registry is None:
        _registry = FactorWeightRegistry()
        _registry.initialize_defaults()
    return _registry
