"""
TT5 - Control Repository
========================
In-memory storage for control state, pending actions, and overrides.
"""

import uuid
from typing import List, Optional
from .control_models import ControlState, PendingAction, OverrideRule, utc_now


class ControlRepository:
    """In-memory storage for control layer data"""
    
    def __init__(self):
        self.state = ControlState(
            trading_enabled=True,
            new_entries_enabled=True,
            position_management_enabled=True,
            alpha_mode="MANUAL",
            system_state="ACTIVE",
            emergency=False,
            soft_kill=False,
            hard_kill=False,
            last_state_change=utc_now(),
        )
        self.pending_actions: List[PendingAction] = []
        self.overrides: List[OverrideRule] = []
        self.action_history: List[PendingAction] = []  # Resolved actions

    # === State Management ===
    
    def get_state(self) -> ControlState:
        return self.state

    def save_state(self, state: ControlState) -> ControlState:
        state.last_state_change = utc_now()
        self.state = state
        return state

    def update_state(self, **kwargs) -> ControlState:
        """Update specific state fields"""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
        self.state.last_state_change = utc_now()
        return self.state

    # === Pending Actions ===
    
    def add_pending_action(self, action_dict: dict) -> PendingAction:
        """Add new pending action"""
        item = PendingAction(
            pending_id=str(uuid.uuid4()),
            scope=action_dict.get("scope", "unknown"),
            scope_key=action_dict.get("scope_key", "unknown"),
            action=action_dict.get("action", "KEEP"),
            magnitude=float(action_dict.get("magnitude", 0.0)),
            reason=action_dict.get("reason", ""),
            source=action_dict.get("source", "alpha_factory"),
            confidence=float(action_dict.get("confidence", 0.0)),
            auto_apply=bool(action_dict.get("auto_apply", False)),
            status="PENDING",
            created_at=utc_now(),
        )
        self.pending_actions.append(item)
        return item

    def list_pending_actions(self, status: str = "PENDING") -> List[PendingAction]:
        """List actions by status"""
        return [x for x in self.pending_actions if x.status == status]

    def get_pending_action(self, pending_id: str) -> Optional[PendingAction]:
        """Get specific pending action"""
        for item in self.pending_actions:
            if item.pending_id == pending_id:
                return item
        return None

    def resolve_action(self, pending_id: str, status: str, resolved_by: str = "operator") -> Optional[PendingAction]:
        """Mark action as resolved (APPROVED/REJECTED/APPLIED)"""
        item = self.get_pending_action(pending_id)
        if item:
            item.status = status
            item.resolved_at = utc_now()
            item.resolved_by = resolved_by
            # Move to history
            self.action_history.append(item)
            self.pending_actions = [x for x in self.pending_actions if x.pending_id != pending_id]
        return item

    def get_action_history(self, limit: int = 50) -> List[PendingAction]:
        """Get resolved actions history"""
        return sorted(self.action_history, key=lambda x: x.resolved_at or "", reverse=True)[:limit]

    # === Overrides ===
    
    def add_override(self, override_type: str, scope_key: str, value: bool, reason: str) -> OverrideRule:
        """Add operator override rule"""
        rule = OverrideRule(
            rule_id=str(uuid.uuid4()),
            override_type=override_type,
            scope_key=scope_key,
            value=value,
            reason=reason,
            created_at=utc_now(),
            active=True,
        )
        self.overrides.append(rule)
        return rule

    def list_overrides(self, active_only: bool = True) -> List[OverrideRule]:
        """List override rules"""
        if active_only:
            return [x for x in self.overrides if x.active]
        return self.overrides

    def remove_override(self, rule_id: str) -> bool:
        """Deactivate override rule"""
        for rule in self.overrides:
            if rule.rule_id == rule_id:
                rule.active = False
                return True
        return False

    def get_override_for_symbol(self, symbol: str) -> Optional[OverrideRule]:
        """Get active override for symbol"""
        for rule in self.overrides:
            if rule.active and rule.scope_key.upper() == symbol.upper():
                return rule
        return None

    # === Summary ===
    
    def get_summary(self) -> dict:
        """Get control summary for UI"""
        return {
            "system_state": self.state.system_state,
            "alpha_mode": self.state.alpha_mode,
            "trading_enabled": self.state.trading_enabled,
            "new_entries_enabled": self.state.new_entries_enabled,
            "position_management_enabled": self.state.position_management_enabled,
            "soft_kill": self.state.soft_kill,
            "hard_kill": self.state.hard_kill,
            "emergency": self.state.emergency,
            "pending_actions_count": len(self.list_pending_actions()),
            "active_overrides_count": len(self.list_overrides(active_only=True)),
            "last_state_change": self.state.last_state_change,
        }

    def reset(self):
        """Reset to defaults"""
        self.__init__()
