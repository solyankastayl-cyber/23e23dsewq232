"""
PHASE 20.4 — Research Loop Registry
===================================
Registry for tracking research loop state history.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field

from modules.research_loop.aggregator.research_loop_types import (
    LoopState,
    ResearchLoopState,
    ResearchLoopHistoryEntry,
)


class ResearchLoopRegistry:
    """
    Registry for tracking research loop state and history.
    """
    
    def __init__(self):
        """Initialize registry."""
        self._history: List[ResearchLoopHistoryEntry] = []
        self._current_state: Optional[ResearchLoopState] = None
        self._stats: Dict[str, Any] = {
            "total_recomputes": 0,
            "state_transitions": 0,
            "last_healthy": None,
            "last_critical": None,
        }
    
    # ═══════════════════════════════════════════════════════════
    # READ OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def get_current_state(self) -> Optional[ResearchLoopState]:
        """Get current loop state."""
        return self._current_state
    
    def get_history(self, limit: int = 20) -> List[ResearchLoopHistoryEntry]:
        """Get state history."""
        return self._history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        state_counts = {state.value: 0 for state in LoopState}
        for entry in self._history:
            state_counts[entry.loop_state.value] += 1
        
        return {
            "total_recomputes": self._stats["total_recomputes"],
            "state_transitions": self._stats["state_transitions"],
            "history_length": len(self._history),
            "state_distribution": state_counts,
            "last_healthy": self._stats["last_healthy"],
            "last_critical": self._stats["last_critical"],
            "current_state": self._current_state.loop_state.value if self._current_state else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    # ═══════════════════════════════════════════════════════════
    # WRITE OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def record_state(self, state: ResearchLoopState):
        """
        Record new loop state.
        """
        # Track state transition
        if self._current_state is not None:
            if self._current_state.loop_state != state.loop_state:
                self._stats["state_transitions"] += 1
        
        # Update current state
        self._current_state = state
        
        # Add to history
        entry = ResearchLoopHistoryEntry(
            loop_state=state.loop_state,
            loop_score=state.loop_score,
            healthy_factors=state.healthy_factors,
            total_factors=state.total_factors,
            critical_patterns_count=len(state.critical_failure_patterns),
        )
        self._history.append(entry)
        
        # Update stats
        self._stats["total_recomputes"] += 1
        
        if state.loop_state == LoopState.HEALTHY:
            self._stats["last_healthy"] = datetime.now(timezone.utc).isoformat()
        elif state.loop_state == LoopState.CRITICAL:
            self._stats["last_critical"] = datetime.now(timezone.utc).isoformat()
        
        # Trim history if too long
        if len(self._history) > 100:
            self._history = self._history[-100:]
    
    def clear_history(self):
        """Clear history but keep current state."""
        self._history.clear()
        self._stats = {
            "total_recomputes": 0,
            "state_transitions": 0,
            "last_healthy": None,
            "last_critical": None,
        }


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_registry: Optional[ResearchLoopRegistry] = None


def get_research_loop_registry() -> ResearchLoopRegistry:
    """Get singleton registry instance."""
    global _registry
    if _registry is None:
        _registry = ResearchLoopRegistry()
    return _registry
