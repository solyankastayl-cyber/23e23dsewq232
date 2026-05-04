"""
PHASE 23.4 — Resilience Registry
================================
Registry for tracking and persisting portfolio resilience states.

Provides:
- Current state caching
- Historical state tracking
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from collections import deque

from .resilience_types import PortfolioResilienceState, ResilienceHistoryEntry


class ResilienceRegistry:
    """
    Registry for portfolio resilience states.
    
    Caches current state and maintains history.
    """
    
    def __init__(self, max_history: int = 100):
        self._current_state: Optional[PortfolioResilienceState] = None
        self._history: deque = deque(maxlen=max_history)
        self._last_update: Optional[datetime] = None
    
    def update(self, state: PortfolioResilienceState) -> None:
        """Update current state and add to history."""
        self._current_state = state
        self._last_update = datetime.now(timezone.utc)
        
        # Add to history
        entry = ResilienceHistoryEntry(
            resilience_state=state.resilience_state,
            resilience_score=state.resilience_score,
            weakest_component=state.weakest_component,
            recommended_action=state.recommended_action,
            timestamp=state.timestamp,
        )
        self._history.append(entry)
    
    def get_current(self) -> Optional[PortfolioResilienceState]:
        """Get current resilience state."""
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
            "current_state": self._current_state.resilience_state.value,
            "current_score": round(self._current_state.resilience_score, 4),
            "weakest_component": self._current_state.weakest_component,
            "history_count": len(self._history),
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }
    
    def clear(self) -> None:
        """Clear registry state."""
        self._current_state = None
        self._history.clear()
        self._last_update = None


# Singleton registry instance
_registry = ResilienceRegistry()


def get_resilience_registry() -> ResilienceRegistry:
    """Get resilience registry singleton."""
    return _registry
