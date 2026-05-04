"""
PHASE 22.5 — Crisis Registry
============================
Registry for tracking and persisting crisis exposure states.

Provides:
- Current state caching
- Historical state tracking
- State persistence
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from collections import deque

from .crisis_types import CrisisExposureState, CrisisHistoryEntry


class CrisisRegistry:
    """
    Registry for crisis exposure states.
    
    Caches current state and maintains history.
    """
    
    def __init__(self, max_history: int = 100):
        self._current_state: Optional[CrisisExposureState] = None
        self._history: deque = deque(maxlen=max_history)
        self._last_update: Optional[datetime] = None
    
    def update(self, state: CrisisExposureState) -> None:
        """Update current state and add to history."""
        self._current_state = state
        self._last_update = datetime.now(timezone.utc)
        
        # Add to history
        entry = CrisisHistoryEntry(
            crisis_state=state.crisis_state,
            crisis_score=state.crisis_score,
            strongest_risk=state.strongest_risk,
            recommended_action=state.recommended_action,
            timestamp=state.timestamp,
        )
        self._history.append(entry)
    
    def get_current(self) -> Optional[CrisisExposureState]:
        """Get current crisis state."""
        return self._current_state
    
    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent history entries."""
        entries = list(self._history)[-limit:]
        return [e.to_dict() for e in reversed(entries)]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        if not self._current_state:
            return {
                "has_state": False,
                "history_count": len(self._history),
            }
        
        return {
            "has_state": True,
            "current_state": self._current_state.crisis_state.value,
            "current_score": round(self._current_state.crisis_score, 4),
            "strongest_risk": self._current_state.strongest_risk,
            "history_count": len(self._history),
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }
    
    def clear(self) -> None:
        """Clear registry state."""
        self._current_state = None
        self._history.clear()
        self._last_update = None


# Singleton registry instance
_registry = CrisisRegistry()


def get_crisis_registry() -> CrisisRegistry:
    """Get crisis registry singleton."""
    return _registry
