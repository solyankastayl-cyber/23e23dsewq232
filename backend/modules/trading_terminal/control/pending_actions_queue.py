"""
TT5 - Pending Actions Queue
===========================
Queue management for alpha actions awaiting approval.
"""

from typing import List, Dict, Any, Optional
from .control_models import PendingAction, utc_now


class PendingActionsQueue:
    """Manages pending actions queue with approval/rejection workflow"""
    
    def approve(self, item: PendingAction, resolved_by: str = "operator") -> PendingAction:
        """Approve a pending action"""
        item.status = "APPROVED"
        item.resolved_at = utc_now()
        item.resolved_by = resolved_by
        return item

    def reject(self, item: PendingAction, resolved_by: str = "operator") -> PendingAction:
        """Reject a pending action"""
        item.status = "REJECTED"
        item.resolved_at = utc_now()
        item.resolved_by = resolved_by
        return item

    def mark_applied(self, item: PendingAction) -> PendingAction:
        """Mark action as successfully applied"""
        item.status = "APPLIED"
        item.resolved_at = utc_now()
        item.resolved_by = "system"
        return item

    def mark_expired(self, item: PendingAction) -> PendingAction:
        """Mark action as expired (not acted upon in time)"""
        item.status = "EXPIRED"
        item.resolved_at = utc_now()
        item.resolved_by = "system"
        return item

    def filter_actionable(self, items: List[PendingAction]) -> List[PendingAction]:
        """Get only pending items that can be acted upon"""
        return [x for x in items if x.status == "PENDING"]

    def filter_by_scope(self, items: List[PendingAction], scope: str) -> List[PendingAction]:
        """Filter pending actions by scope"""
        return [x for x in items if x.scope == scope]

    def get_summary(self, items: List[PendingAction]) -> Dict[str, Any]:
        """Get summary of pending actions"""
        by_action = {}
        by_scope = {}
        
        for item in items:
            if item.status == "PENDING":
                by_action[item.action] = by_action.get(item.action, 0) + 1
                by_scope[item.scope] = by_scope.get(item.scope, 0) + 1
        
        return {
            "total_pending": len([x for x in items if x.status == "PENDING"]),
            "by_action": by_action,
            "by_scope": by_scope,
        }
