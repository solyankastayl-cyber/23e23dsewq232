"""
TT5 - Control Query Service
===========================
Query service for control layer data.
"""

from typing import Dict, Any, List
from .control_repository import ControlRepository


class ControlQueryService:
    """Service for querying control layer data"""
    
    def __init__(self, repo: ControlRepository):
        self.repo = repo

    def get_summary(self) -> Dict[str, Any]:
        """Get control summary for UI blocks"""
        return self.repo.get_summary()

    def get_state(self) -> Dict[str, Any]:
        """Get full control state"""
        return self.repo.get_state().to_dict()

    def get_pending_summary(self) -> Dict[str, Any]:
        """Get pending actions summary"""
        pending = self.repo.list_pending_actions()
        
        by_action = {}
        by_scope = {}
        
        for item in pending:
            by_action[item.action] = by_action.get(item.action, 0) + 1
            by_scope[item.scope] = by_scope.get(item.scope, 0) + 1
        
        return {
            "total": len(pending),
            "by_action": by_action,
            "by_scope": by_scope,
        }

    def format_for_terminal_state(self) -> Dict[str, Any]:
        """Format control data for terminal state integration"""
        state = self.repo.get_state()
        summary = self.repo.get_summary()
        pending = self.repo.list_pending_actions()
        
        return {
            "control": {
                "system_state": state.system_state,
                "alpha_mode": state.alpha_mode,
                "trading_enabled": state.trading_enabled,
                "new_entries_enabled": state.new_entries_enabled,
                "soft_kill": state.soft_kill,
                "hard_kill": state.hard_kill,
            },
            "pending_actions_count": len(pending),
            "pending_actions_preview": [p.to_dict() for p in pending[:5]],
        }

    def is_symbol_blocked(self, symbol: str) -> bool:
        """Check if symbol is blocked by override"""
        override = self.repo.get_override_for_symbol(symbol)
        if override and override.override_type == "DISABLE_SYMBOL":
            return True
        return False

    def get_symbol_status(self, symbol: str) -> Dict[str, Any]:
        """Get control status for specific symbol"""
        override = self.repo.get_override_for_symbol(symbol)
        
        return {
            "symbol": symbol,
            "blocked": override is not None and override.override_type == "DISABLE_SYMBOL",
            "override": override.to_dict() if override else None,
        }
