"""
PHASE 21.3 — Capital Allocation Registry
========================================
Registry for tracking layer state history.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from modules.capital_allocation_v2.aggregator.capital_allocation_layer_types import (
    AllocationState,
    CapitalAllocationLayerState,
    LayerHistoryEntry,
)


class CapitalAllocationRegistry:
    """
    Registry for tracking capital allocation layer state and history.
    """
    
    def __init__(self):
        """Initialize registry."""
        self._history: List[LayerHistoryEntry] = []
        self._current_state: Optional[CapitalAllocationLayerState] = None
        self._stats: Dict[str, Any] = {
            "total_recomputes": 0,
            "state_transitions": 0,
            "last_optimal": None,
            "last_stressed": None,
        }
    
    # ═══════════════════════════════════════════════════════════
    # READ OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def get_current_state(self) -> Optional[CapitalAllocationLayerState]:
        """Get current layer state."""
        return self._current_state
    
    def get_history(self, limit: int = 20) -> List[LayerHistoryEntry]:
        """Get state history."""
        return self._history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        state_counts = {state.value: 0 for state in AllocationState}
        for entry in self._history:
            state_counts[entry.allocation_state.value] += 1
        
        avg_efficiency = 0.0
        if self._history:
            avg_efficiency = sum(e.capital_efficiency for e in self._history) / len(self._history)
        
        return {
            "total_recomputes": self._stats["total_recomputes"],
            "state_transitions": self._stats["state_transitions"],
            "history_length": len(self._history),
            "state_distribution": state_counts,
            "average_efficiency": round(avg_efficiency, 4),
            "last_optimal": self._stats["last_optimal"],
            "last_stressed": self._stats["last_stressed"],
            "current_state": self._current_state.allocation_state.value if self._current_state else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    # ═══════════════════════════════════════════════════════════
    # WRITE OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def record_state(self, state: CapitalAllocationLayerState):
        """Record new layer state."""
        # Track state transition
        if self._current_state is not None:
            if self._current_state.allocation_state != state.allocation_state:
                self._stats["state_transitions"] += 1
        
        # Update current state
        self._current_state = state
        
        # Add to history
        entry = LayerHistoryEntry(
            allocation_state=state.allocation_state,
            budget_state=state.budget_state,
            capital_efficiency=state.capital_efficiency,
            deployable_capital=state.deployable_capital,
        )
        self._history.append(entry)
        
        # Update stats
        self._stats["total_recomputes"] += 1
        
        if state.allocation_state == AllocationState.OPTIMAL:
            self._stats["last_optimal"] = datetime.now(timezone.utc).isoformat()
        elif state.allocation_state == AllocationState.STRESSED:
            self._stats["last_stressed"] = datetime.now(timezone.utc).isoformat()
        
        # Trim history if too long
        if len(self._history) > 100:
            self._history = self._history[-100:]
    
    def clear_history(self):
        """Clear history but keep current state."""
        self._history.clear()
        self._stats = {
            "total_recomputes": 0,
            "state_transitions": 0,
            "last_optimal": None,
            "last_stressed": None,
        }


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_registry: Optional[CapitalAllocationRegistry] = None


def get_capital_allocation_registry() -> CapitalAllocationRegistry:
    """Get singleton registry instance."""
    global _registry
    if _registry is None:
        _registry = CapitalAllocationRegistry()
    return _registry
