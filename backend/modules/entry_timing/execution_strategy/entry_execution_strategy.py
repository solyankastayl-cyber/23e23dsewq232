"""
PHASE 4.3 — Entry Execution Strategy Engine

Main orchestrator that selects execution strategy based on entry mode.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from .execution_strategy_types import (
    ExecutionStrategy,
    EXECUTION_STRATEGIES,
    STRATEGY_DESCRIPTIONS,
    MODE_TO_STRATEGY,
    get_strategy_info
)
from .execution_splitter import ExecutionSplitter


class EntryExecutionStrategy:
    """
    Selects and configures execution strategy.
    
    Flow:
    Entry Mode → Execution Strategy → Order Legs
    """
    
    def __init__(self):
        self.splitter = ExecutionSplitter()
        self._history: List[Dict] = []
    
    def select(self, data: Dict) -> Dict:
        """
        Select execution strategy based on entry mode and context.
        
        Args:
            data: {
                "entry_mode": "WAIT_RETEST",
                "prediction": {"direction": "LONG", "confidence": 0.78},
                "setup": {"entry": 62410, "stop_loss": 61820, "target": 63750},
                "context": {"extension_atr": 0.7, "retest_level": 62150, ...}
            }
        
        Returns:
            Execution strategy with order legs
        """
        entry_mode = data.get("entry_mode", {})
        mode = entry_mode.get("entry_mode") if isinstance(entry_mode, dict) else entry_mode
        
        prediction = data.get("prediction", {})
        setup = data.get("setup", {})
        ctx = data.get("context", {})
        
        # Skip modes
        if mode in ["SKIP_LATE_ENTRY", "SKIP_CONFLICTED"]:
            return self._result("SKIP_ENTRY", False, mode.lower(), setup, prediction, [])
        
        # Get base strategy from mode
        base_strategy = MODE_TO_STRATEGY.get(mode, "FULL_ENTRY_NOW")
        
        # Apply modifiers based on context
        strategy, reason = self._apply_modifiers(base_strategy, mode, prediction, ctx)
        
        # Generate order legs
        direction = prediction.get("direction", "LONG")
        retest_level = ctx.get("retest_level")
        legs = self.splitter.split(strategy, setup, direction, retest_level)
        
        result = self._result(strategy, True, reason, setup, prediction, legs.get("legs", []))
        result["execution_type"] = legs.get("execution_type", "unknown")
        result["total_legs"] = legs.get("total_legs", 0)
        
        # Record in history
        self._history.append({
            "strategy": strategy,
            "mode": mode,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return result
    
    def _apply_modifiers(
        self,
        base_strategy: str,
        mode: str,
        prediction: Dict,
        ctx: Dict
    ) -> tuple:
        """Apply context-based modifiers to strategy."""
        confidence = prediction.get("confidence", 0.5)
        extension = ctx.get("extension_atr", 0)
        
        # High confidence + low extension → upgrade to full now
        if mode == "ENTER_NOW" and confidence > 0.85 and extension < 0.8:
            return "FULL_ENTRY_NOW", "high_conf_clean_entry"
        
        # Medium confidence ENTER_NOW → split for safety
        if mode == "ENTER_NOW" and confidence < 0.75:
            return "PARTIAL_NOW_PARTIAL_RETEST", "medium_conf_split_entry"
        
        # High extension even in ENTER_NOW → downgrade to pullback
        if mode == "ENTER_NOW" and extension > 1.2:
            return "WAIT_PULLBACK_LIMIT", "extension_override"
        
        return base_strategy, f"mode_{mode.lower()}"
    
    def _result(
        self,
        strategy: str,
        valid: bool,
        reason: str,
        setup: Dict,
        prediction: Dict,
        legs: List[Dict]
    ) -> Dict:
        """Build result object."""
        return {
            "execution_strategy": strategy,
            "valid": valid,
            "reason": reason,
            "description": STRATEGY_DESCRIPTIONS.get(strategy, ""),
            "legs": legs,
            "setup_entry": setup.get("entry"),
            "setup_sl": setup.get("stop_loss"),
            "setup_tp": setup.get("target"),
            "direction": prediction.get("direction"),
            "selected_at": datetime.now(timezone.utc).isoformat()
        }
    
    def get_strategy_types(self) -> Dict:
        """Get all execution strategy types."""
        return {
            "strategies": EXECUTION_STRATEGIES,
            "descriptions": STRATEGY_DESCRIPTIONS,
            "mode_mapping": MODE_TO_STRATEGY
        }
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """Get recent selection history."""
        return self._history[-limit:]
    
    def health_check(self) -> Dict:
        """Health check."""
        return {
            "ok": True,
            "module": "entry_execution_strategy",
            "version": "4.3",
            "strategies_count": len(EXECUTION_STRATEGIES),
            "history_count": len(self._history),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Singleton
_engine: Optional[EntryExecutionStrategy] = None


def get_execution_strategy_engine() -> EntryExecutionStrategy:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = EntryExecutionStrategy()
    return _engine
