"""
PHASE 4.2 — Entry Mode Engine

Main orchestrator for entry mode selection.
Integrates with Phase 4.1 diagnostics for self-correction.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from .entry_mode_selector import EntryModeSelector
from .entry_mode_types import ENTRY_MODES, MODE_DESCRIPTIONS, get_mode_info


class EntryModeEngine:
    """
    Main engine for entry mode selection.
    
    Integrates with:
    - Phase 4.1: Wrong Early Diagnostics (learns from mistakes)
    - Prediction Engine (reads prediction)
    - Trade Setup (reads setup)
    
    Does NOT modify:
    - Direction
    - Signal strength
    - Tradeable flag
    
    Only outputs: HOW to enter
    """
    
    def __init__(self):
        self.selector = EntryModeSelector()
        self._selection_history: List[Dict] = []
        self._diagnostics_cache: Optional[Dict] = None
        self._last_sync: Optional[datetime] = None
    
    def select(self, data: Dict) -> Dict:
        """
        Select entry mode for a trade.
        
        Args:
            data: Full trade context
        
        Returns:
            Entry mode decision with reasoning
        """
        # Add diagnostics from cache if not provided
        if "diagnostics" not in data and self._diagnostics_cache:
            data["diagnostics"] = {
                "top_wrong_early_reasons": self._diagnostics_cache.get("top_reasons", [])
            }
        
        result = self.selector.select(data)
        
        # Record in history
        self._record_selection(result)
        
        return result
    
    def select_batch(self, data_list: List[Dict]) -> List[Dict]:
        """Select modes for multiple trades."""
        return [self.select(data) for data in data_list]
    
    def sync_with_diagnostics(self):
        """
        Sync with Phase 4.1 diagnostics to update rules.
        
        This should be called periodically to adapt to recent patterns.
        """
        try:
            from ..diagnostics import get_wrong_early_engine
            
            diag_engine = get_wrong_early_engine()
            summary = diag_engine.get_summary(limit=200)
            
            # Cache top reasons
            top_issues = summary.get("top_issues", [])
            self._diagnostics_cache = {
                "top_reasons": [issue["reason"] for issue in top_issues[:5]],
                "distribution": summary.get("distribution", {}),
                "unknown_rate": summary.get("unknown_rate", 0)
            }
            
            # Update selector thresholds
            self.selector.update_from_diagnostics(summary)
            
            self._last_sync = datetime.now(timezone.utc)
            
            return {
                "ok": True,
                "synced_at": self._last_sync.isoformat(),
                "top_reasons": self._diagnostics_cache["top_reasons"],
                "unknown_rate": self._diagnostics_cache["unknown_rate"]
            }
            
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def get_mode_types(self) -> Dict:
        """Get all available entry mode types."""
        return {
            "modes": ENTRY_MODES,
            "descriptions": MODE_DESCRIPTIONS,
            "details": {mode: get_mode_info(mode) for mode in ENTRY_MODES}
        }
    
    def get_recommendation_for_reason(self, wrong_early_reason: str) -> Dict:
        """Get recommended mode to prevent a specific wrong early reason."""
        mode = self.selector.get_mode_for_reason(wrong_early_reason)
        
        return {
            "wrong_early_reason": wrong_early_reason,
            "recommended_mode": mode,
            "mode_info": get_mode_info(mode)
        }
    
    def simulate_scenario(self, scenario: str) -> Dict:
        """Run a simulated scenario for testing."""
        return self.selector.simulate_selection(scenario)
    
    def get_selection_history(self, limit: int = 50) -> List[Dict]:
        """Get recent selection history."""
        return self._selection_history[-limit:]
    
    def get_selection_stats(self) -> Dict:
        """Get statistics on recent selections."""
        if not self._selection_history:
            return {"total": 0, "by_mode": {}, "by_reason": {}}
        
        total = len(self._selection_history)
        by_mode: Dict[str, int] = {}
        by_reason: Dict[str, int] = {}
        allows_entry_count = 0
        
        for sel in self._selection_history:
            mode = sel.get("entry_mode", "unknown")
            reason = sel.get("reason", "unknown")
            
            by_mode[mode] = by_mode.get(mode, 0) + 1
            by_reason[reason] = by_reason.get(reason, 0) + 1
            
            if sel.get("allows_entry", True):
                allows_entry_count += 1
        
        return {
            "total": total,
            "by_mode": by_mode,
            "by_reason": by_reason,
            "entry_rate": round(allows_entry_count / total, 4) if total > 0 else 0,
            "skip_rate": round((total - allows_entry_count) / total, 4) if total > 0 else 0
        }
    
    def health_check(self) -> Dict:
        """Health check for the engine."""
        return {
            "ok": True,
            "module": "entry_mode_selector",
            "version": "4.2",
            "modes_count": len(ENTRY_MODES),
            "selection_history_count": len(self._selection_history),
            "diagnostics_synced": self._last_sync.isoformat() if self._last_sync else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def clear_history(self):
        """Clear selection history (for testing)."""
        self._selection_history = []
    
    def _record_selection(self, result: Dict):
        """Record selection in history."""
        record = {
            "entry_mode": result.get("entry_mode"),
            "reason": result.get("reason"),
            "confidence": result.get("confidence"),
            "allows_entry": result.get("allows_entry"),
            "selected_at": result.get("selected_at")
        }
        
        self._selection_history.append(record)
        
        # Trim history
        if len(self._selection_history) > 500:
            self._selection_history = self._selection_history[-250:]


# Singleton instance
_engine: Optional[EntryModeEngine] = None


def get_entry_mode_engine() -> EntryModeEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = EntryModeEngine()
    return _engine
