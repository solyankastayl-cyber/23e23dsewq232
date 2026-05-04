"""
TT5 - Control Engine
====================
Main control engine orchestrating system state and alpha actions flow.
"""

from typing import Dict, Any, List, Optional
from .control_models import utc_now
from .control_repository import ControlRepository
from .control_policy import ControlPolicy
from .pending_actions_queue import PendingActionsQueue


class ControlEngine:
    """
    Main control layer orchestrator.
    
    Handles:
    - System state transitions (pause/resume/kill)
    - Alpha mode management
    - Action ingestion from Alpha Factory
    - Approval workflow
    - Override management
    """
    
    def __init__(self, repo: ControlRepository):
        self.repo = repo
        self.policy = ControlPolicy()
        self.queue = PendingActionsQueue()

    # === State Queries ===
    
    def get_state(self) -> Dict[str, Any]:
        """Get current control state"""
        return self.repo.get_state().to_dict()

    def get_summary(self) -> Dict[str, Any]:
        """Get control summary for UI"""
        summary = self.repo.get_summary()
        summary["status"] = self.policy.get_system_status(self.get_state())
        return summary

    # === System State Controls ===
    
    def pause(self) -> Dict[str, Any]:
        """Pause system - stop new trades, observe only"""
        state = self.repo.get_state()
        state.system_state = "PAUSED"
        state.new_entries_enabled = False
        return self.repo.save_state(state).to_dict()

    def resume(self) -> Dict[str, Any]:
        """Resume normal operation"""
        state = self.repo.get_state()
        state.system_state = "ACTIVE"
        state.trading_enabled = True
        state.new_entries_enabled = True
        state.position_management_enabled = True
        state.soft_kill = False
        state.hard_kill = False
        state.emergency = False
        return self.repo.save_state(state).to_dict()

    def soft_kill(self) -> Dict[str, Any]:
        """Soft kill - no new entries, manage existing positions"""
        state = self.repo.get_state()
        state.system_state = "SOFT_KILL"
        state.soft_kill = True
        state.new_entries_enabled = False
        return self.repo.save_state(state).to_dict()

    def hard_kill(self) -> Dict[str, Any]:
        """Hard kill - stop all trading immediately"""
        state = self.repo.get_state()
        state.system_state = "HARD_KILL"
        state.hard_kill = True
        state.trading_enabled = False
        state.new_entries_enabled = False
        return self.repo.save_state(state).to_dict()

    def emergency_stop(self) -> Dict[str, Any]:
        """Emergency stop - halt everything with alerting"""
        state = self.repo.get_state()
        state.system_state = "EMERGENCY"
        state.emergency = True
        state.hard_kill = True
        state.trading_enabled = False
        state.new_entries_enabled = False
        state.position_management_enabled = False
        return self.repo.save_state(state).to_dict()

    # === Alpha Mode Controls ===
    
    def set_alpha_mode(self, mode: str) -> Dict[str, Any]:
        """Set alpha factory mode: AUTO / MANUAL / OFF"""
        if mode not in {"AUTO", "MANUAL", "OFF"}:
            raise ValueError(f"Invalid alpha mode: {mode}")
        
        state = self.repo.get_state()
        state.alpha_mode = mode
        return self.repo.save_state(state).to_dict()

    # === Alpha Actions Flow ===
    
    def ingest_alpha_actions(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ingest actions from Alpha Factory.
        
        Based on alpha_mode:
        - OFF: Actions ignored
        - MANUAL: Actions queued for approval
        - AUTO: Actions may auto-apply if conditions met
        """
        state = self.get_state()
        mode = self.policy.get_alpha_mode(state)
        
        if mode == "OFF":
            return {
                "status": "ignored",
                "reason": "alpha_mode_off",
                "queued": 0,
                "auto_applied": 0
            }
        
        queued = []
        auto_apply = []
        
        for action in actions:
            # Skip KEEP actions - nothing to do
            if action.get("action") == "KEEP":
                continue
                
            if mode == "AUTO" and self.policy.should_auto_apply(state, action):
                auto_apply.append(action)
            else:
                # Queue for manual approval
                pending = self.repo.add_pending_action(action)
                queued.append(pending.to_dict())
        
        result = {
            "status": "processed",
            "mode": mode,
            "queued": len(queued),
            "auto_applied": len(auto_apply),
        }
        
        if queued:
            result["pending_items"] = queued
        if auto_apply:
            result["auto_apply_items"] = auto_apply
            
        return result

    # === Approval Workflow ===
    
    def pending_actions(self) -> List[Dict[str, Any]]:
        """Get all pending actions"""
        return [x.to_dict() for x in self.repo.list_pending_actions()]

    def approve_action(self, pending_id: str) -> Dict[str, Any]:
        """Approve a pending action"""
        item = self.repo.get_pending_action(pending_id)
        if not item:
            raise ValueError("Pending action not found")
        
        self.queue.approve(item)
        self.repo.resolve_action(pending_id, "APPROVED", "operator")
        
        return {
            "status": "approved",
            "action": item.to_dict()
        }

    def reject_action(self, pending_id: str, reason: str = "") -> Dict[str, Any]:
        """Reject a pending action"""
        item = self.repo.get_pending_action(pending_id)
        if not item:
            raise ValueError("Pending action not found")
        
        self.queue.reject(item)
        self.repo.resolve_action(pending_id, "REJECTED", "operator")
        
        return {
            "status": "rejected",
            "action": item.to_dict(),
            "reason": reason
        }

    def approve_all(self) -> Dict[str, Any]:
        """Approve all pending actions"""
        pending = self.repo.list_pending_actions()
        approved = []
        
        for item in pending:
            self.queue.approve(item)
            self.repo.resolve_action(item.pending_id, "APPROVED", "operator")
            approved.append(item.pending_id)
        
        return {
            "status": "approved_all",
            "count": len(approved),
            "ids": approved
        }

    def reject_all(self) -> Dict[str, Any]:
        """Reject all pending actions"""
        pending = self.repo.list_pending_actions()
        rejected = []
        
        for item in pending:
            self.queue.reject(item)
            self.repo.resolve_action(item.pending_id, "REJECTED", "operator")
            rejected.append(item.pending_id)
        
        return {
            "status": "rejected_all",
            "count": len(rejected),
            "ids": rejected
        }

    # === Overrides ===
    
    def add_override(self, override_type: str, scope_key: str, reason: str = "") -> Dict[str, Any]:
        """Add operator override rule"""
        rule = self.repo.add_override(override_type, scope_key, True, reason)
        return rule.to_dict()

    def remove_override(self, rule_id: str) -> Dict[str, Any]:
        """Remove override rule"""
        success = self.repo.remove_override(rule_id)
        return {"success": success, "rule_id": rule_id}

    def list_overrides(self) -> List[Dict[str, Any]]:
        """List active overrides"""
        return [x.to_dict() for x in self.repo.list_overrides(active_only=True)]

    # === Permission Checks ===
    
    def can_trade(self) -> bool:
        """Check if trading is allowed"""
        return self.policy.can_trade(self.get_state())

    def can_open_entry(self) -> bool:
        """Check if new entries are allowed"""
        return self.policy.can_open_new_entries(self.get_state())

    def can_manage_positions(self) -> bool:
        """Check if position management is allowed"""
        return self.policy.can_manage_positions(self.get_state())

    # === History ===
    
    def get_action_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get resolved actions history"""
        return [x.to_dict() for x in self.repo.get_action_history(limit)]
