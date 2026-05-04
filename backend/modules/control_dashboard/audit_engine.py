"""
Audit Engine

PHASE 40.3 — Alerts + Audit Engine

Records all user actions for compliance and tracking.

Audit categories:
- APPROVAL: Order approve/reject/reduce/override
- CONFIG: Mode changes, settings
- ALERT: Alert acknowledgements
- SYSTEM: Automatic actions
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta

from .dashboard_types import DashboardAuditLog


# ══════════════════════════════════════════════════════════════
# Audit Engine
# ══════════════════════════════════════════════════════════════

class AuditEngine:
    """
    Audit Engine — PHASE 40.3
    
    Records all user actions for compliance.
    """
    
    def __init__(self, retention_days: int = 90):
        self._logs: List[DashboardAuditLog] = []
        self._retention_days = retention_days
    
    # ═══════════════════════════════════════════════════════════
    # 1. Log Actions
    # ═══════════════════════════════════════════════════════════
    
    def log_action(
        self,
        action: str,
        action_type: str,
        user: str = "operator",
        symbol: Optional[str] = None,
        order_id: Optional[str] = None,
        pending_id: Optional[str] = None,
        previous_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        previous_size: Optional[float] = None,
        new_size: Optional[float] = None,
        execution_mode: str = "PAPER",
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> DashboardAuditLog:
        """Log user action."""
        log = DashboardAuditLog(
            action=action,
            action_type=action_type,
            user=user,
            symbol=symbol,
            order_id=order_id,
            pending_id=pending_id,
            previous_value=previous_value,
            new_value=new_value,
            previous_size=previous_size,
            new_size=new_size,
            execution_mode=execution_mode,
            success=success,
            error_message=error_message,
            ip_address=ip_address,
        )
        
        self._logs.append(log)
        
        # Also save to database
        self._save_to_db(log)
        
        return log
    
    def _save_to_db(self, log: DashboardAuditLog):
        """Save log to MongoDB."""
        try:
            from core.database import get_database
            db = get_database()
            if db is not None:
                db.dashboard_audit_log.insert_one({
                    "audit_id": log.audit_id,
                    "action": log.action,
                    "action_type": log.action_type,
                    "user": log.user,
                    "symbol": log.symbol,
                    "order_id": log.order_id,
                    "pending_id": log.pending_id,
                    "previous_value": log.previous_value,
                    "new_value": log.new_value,
                    "previous_size": log.previous_size,
                    "new_size": log.new_size,
                    "execution_mode": log.execution_mode,
                    "success": log.success,
                    "error_message": log.error_message,
                    "ip_address": log.ip_address,
                    "timestamp": log.timestamp,
                })
        except Exception:
            pass
    
    # ═══════════════════════════════════════════════════════════
    # 2. Convenience Methods
    # ═══════════════════════════════════════════════════════════
    
    def log_approval(
        self,
        action: str,  # APPROVE, REJECT, REDUCE, OVERRIDE
        pending_id: str,
        symbol: str,
        user: str = "operator",
        previous_size: Optional[float] = None,
        new_size: Optional[float] = None,
        order_id: Optional[str] = None,
        note: Optional[str] = None,
    ) -> DashboardAuditLog:
        """Log approval action."""
        return self.log_action(
            action=action,
            action_type="APPROVAL",
            user=user,
            symbol=symbol,
            pending_id=pending_id,
            order_id=order_id,
            previous_size=previous_size,
            new_size=new_size,
            new_value={"note": note} if note else None,
        )
    
    def log_config_change(
        self,
        setting: str,
        previous_value: Any,
        new_value: Any,
        user: str = "operator",
    ) -> DashboardAuditLog:
        """Log configuration change."""
        return self.log_action(
            action=f"CONFIG_CHANGE:{setting}",
            action_type="CONFIG",
            user=user,
            previous_value={setting: previous_value},
            new_value={setting: new_value},
        )
    
    def log_mode_change(
        self,
        previous_mode: str,
        new_mode: str,
        user: str = "operator",
    ) -> DashboardAuditLog:
        """Log execution mode change."""
        return self.log_action(
            action="MODE_CHANGE",
            action_type="CONFIG",
            user=user,
            execution_mode=new_mode,
            previous_value={"mode": previous_mode},
            new_value={"mode": new_mode},
        )
    
    def log_alert_acknowledgement(
        self,
        alert_id: str,
        user: str = "operator",
    ) -> DashboardAuditLog:
        """Log alert acknowledgement."""
        return self.log_action(
            action="ALERT_ACKNOWLEDGED",
            action_type="ALERT",
            user=user,
            new_value={"alert_id": alert_id},
        )
    
    # ═══════════════════════════════════════════════════════════
    # 3. Query Logs
    # ═══════════════════════════════════════════════════════════
    
    def get_logs(
        self,
        action_type: Optional[str] = None,
        user: Optional[str] = None,
        symbol: Optional[str] = None,
        hours_back: Optional[int] = None,
        limit: int = 100,
    ) -> List[DashboardAuditLog]:
        """Get audit logs with filters."""
        logs = self._logs.copy()
        
        # Filter
        if action_type:
            logs = [l for l in logs if l.action_type == action_type]
        if user:
            logs = [l for l in logs if l.user == user]
        if symbol:
            logs = [l for l in logs if l.symbol == symbol]
        if hours_back:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            logs = [l for l in logs if l.timestamp >= cutoff]
        
        # Sort by timestamp descending
        logs.sort(key=lambda l: l.timestamp, reverse=True)
        
        return logs[:limit]
    
    def get_logs_from_db(
        self,
        action_type: Optional[str] = None,
        user: Optional[str] = None,
        symbol: Optional[str] = None,
        hours_back: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Get logs from MongoDB."""
        try:
            from core.database import get_database
            db = get_database()
            if db is None:
                return []
            
            query = {}
            if action_type:
                query["action_type"] = action_type
            if user:
                query["user"] = user
            if symbol:
                query["symbol"] = symbol
            if hours_back:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
                query["timestamp"] = {"$gte": cutoff}
            
            return list(
                db.dashboard_audit_log.find(query, {"_id": 0})
                .sort("timestamp", -1)
                .limit(limit)
            )
        except Exception:
            return []
    
    def get_log(self, audit_id: str) -> Optional[DashboardAuditLog]:
        """Get specific log by ID."""
        for log in self._logs:
            if log.audit_id == audit_id:
                return log
        return None
    
    # ═══════════════════════════════════════════════════════════
    # 4. Statistics
    # ═══════════════════════════════════════════════════════════
    
    def get_statistics(self, hours_back: int = 24) -> Dict:
        """Get audit statistics."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        recent = [l for l in self._logs if l.timestamp >= cutoff]
        
        by_action_type = {}
        by_user = {}
        by_action = {}
        
        for log in recent:
            by_action_type[log.action_type] = by_action_type.get(log.action_type, 0) + 1
            by_user[log.user] = by_user.get(log.user, 0) + 1
            by_action[log.action] = by_action.get(log.action, 0) + 1
        
        return {
            "total_actions": len(recent),
            "period_hours": hours_back,
            "by_action_type": by_action_type,
            "by_user": by_user,
            "by_action": by_action,
            "success_count": sum(1 for l in recent if l.success),
            "failure_count": sum(1 for l in recent if not l.success),
        }
    
    def get_user_activity(self, user: str, hours_back: int = 24) -> Dict:
        """Get activity for specific user."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        user_logs = [l for l in self._logs if l.user == user and l.timestamp >= cutoff]
        
        return {
            "user": user,
            "action_count": len(user_logs),
            "period_hours": hours_back,
            "actions": [
                {
                    "action": l.action,
                    "action_type": l.action_type,
                    "symbol": l.symbol,
                    "timestamp": l.timestamp.isoformat(),
                }
                for l in user_logs[:20]
            ],
        }
    
    # ═══════════════════════════════════════════════════════════
    # 5. Cleanup
    # ═══════════════════════════════════════════════════════════
    
    def cleanup_old_logs(self):
        """Remove logs older than retention period."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        self._logs = [l for l in self._logs if l.timestamp >= cutoff]
    
    def get_log_count(self) -> int:
        """Get total log count."""
        return len(self._logs)


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_audit_engine: Optional[AuditEngine] = None


def get_audit_engine() -> AuditEngine:
    """Get singleton instance."""
    global _audit_engine
    if _audit_engine is None:
        _audit_engine = AuditEngine()
    return _audit_engine
