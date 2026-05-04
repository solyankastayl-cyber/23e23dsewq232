"""
PHASE 3.1 — Action History

Audit trail for all calibration actions.
Records what changed, why, and when.

Provides:
- Full action history
- Rollback capability
- Compliance/audit support
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import json


@dataclass
class ActionRecord:
    """Single action record."""
    timestamp: str
    action_type: str
    target_type: str
    target_id: str
    reason: str
    confidence: float
    status: str  # "applied", "rejected", "rolled_back"
    source_metrics: Optional[Dict] = None
    validation_result: Optional[Dict] = None
    state_before: Optional[Dict] = None
    state_after: Optional[Dict] = None


class ActionHistory:
    """
    Manages action history for audit and rollback.
    
    Stores records in MongoDB for persistence.
    """
    
    def __init__(self, db=None, max_records: int = 1000):
        self.db = db
        self._ensure_db()
        self.max_records = max_records
        self._in_memory_records: List[Dict] = []
    
    def _ensure_db(self):
        """Ensure database connection."""
        if self.db is None:
            try:
                from core.database import get_database
                self.db = get_database()
            except Exception:
                self.db = None
    
    def record(
        self,
        action: Dict,
        status: str,
        validation_result: Optional[Dict] = None,
        state_before: Optional[Dict] = None,
        state_after: Optional[Dict] = None
    ):
        """
        Record an action to history.
        
        Args:
            action: Action dict
            status: "applied", "rejected", "rolled_back"
            validation_result: Validation details
            state_before: State before action
            state_after: State after action
        """
        record = ActionRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type=action.get("action", "unknown"),
            target_type=action.get("target_type", "unknown"),
            target_id=action.get("target_id", "unknown"),
            reason=action.get("reason", ""),
            confidence=action.get("confidence", 0.0),
            status=status,
            source_metrics=action.get("source_metrics"),
            validation_result=validation_result,
            state_before=self._minimize_state(state_before),
            state_after=self._minimize_state(state_after)
        )
        
        record_dict = asdict(record)
        
        # Store in memory
        self._in_memory_records.append(record_dict)
        
        # Trim if too many
        if len(self._in_memory_records) > self.max_records:
            self._in_memory_records = self._in_memory_records[-self.max_records:]
        
        # Store in DB
        self._save_record(record_dict)
    
    def get_history(
        self,
        limit: int = 100,
        status: Optional[str] = None,
        target_id: Optional[str] = None,
        action_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Get action history with filters.
        
        Args:
            limit: Max records to return
            status: Filter by status
            target_id: Filter by target
            action_type: Filter by action type
        
        Returns:
            List of action records
        """
        records = self._load_records(limit * 2)  # Load extra for filtering
        
        # Apply filters
        if status:
            records = [r for r in records if r.get("status") == status]
        
        if target_id:
            records = [r for r in records if r.get("target_id") == target_id]
        
        if action_type:
            records = [r for r in records if r.get("action_type") == action_type]
        
        return records[:limit]
    
    def get_recent_for_target(self, target_id: str, limit: int = 10) -> List[Dict]:
        """Get recent actions for a specific target."""
        return self.get_history(limit=limit, target_id=target_id)
    
    def get_applied_count(self, since_hours: int = 24) -> int:
        """Get count of applied actions in time period."""
        records = self.get_history(limit=1000, status="applied")
        cutoff = datetime.now(timezone.utc).timestamp() - (since_hours * 3600)
        
        count = 0
        for r in records:
            try:
                ts = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
                if ts.timestamp() > cutoff:
                    count += 1
            except:
                pass
        
        return count
    
    def get_summary(self) -> Dict:
        """Get summary of action history."""
        records = self._load_records(1000)
        
        status_counts = {"applied": 0, "rejected": 0, "rolled_back": 0}
        action_counts = {}
        target_counts = {}
        
        for r in records:
            status = r.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            
            action_type = r.get("action_type", "unknown")
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
            
            target_id = r.get("target_id", "unknown")
            target_counts[target_id] = target_counts.get(target_id, 0) + 1
        
        # Top targets
        top_targets = sorted(target_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_records": len(records),
            "by_status": status_counts,
            "by_action_type": action_counts,
            "top_targets": [{"target": t[0], "count": t[1]} for t in top_targets],
            "applied_last_24h": self.get_applied_count(24),
            "applied_last_7d": self.get_applied_count(168)
        }
    
    def clear(self):
        """Clear all history (use with caution)."""
        self._in_memory_records = []
        
        if self.db:
            try:
                self.db.action_history.delete_many({})
            except Exception as e:
                print(f"[ActionHistory] Clear error: {e}")
    
    def _minimize_state(self, state: Optional[Dict]) -> Optional[Dict]:
        """Minimize state for storage (remove large fields)."""
        if state is None:
            return None
        
        # Only keep key fields
        return {
            "enabled_assets": state.get("enabled_assets", []),
            "disabled_assets": state.get("disabled_assets", []),
            "version": state.get("version", 0)
        }
    
    def _save_record(self, record: Dict):
        """Save record to database."""
        if self.db is None:
            return
        
        try:
            self.db.action_history.insert_one(record)
            
            # Cleanup old records
            count = self.db.action_history.count_documents({})
            if count > self.max_records:
                oldest = self.db.action_history.find().sort("timestamp", 1).limit(count - self.max_records)
                ids = [doc["_id"] for doc in oldest]
                self.db.action_history.delete_many({"_id": {"$in": ids}})
        except Exception as e:
            print(f"[ActionHistory] Save error: {e}")
    
    def _load_records(self, limit: int) -> List[Dict]:
        """Load records from database."""
        if self.db is None:
            return self._in_memory_records[-limit:]
        
        try:
            records = list(
                self.db.action_history.find({}, {"_id": 0})
                .sort("timestamp", -1)
                .limit(limit)
            )
            return records
        except Exception as e:
            print(f"[ActionHistory] Load error: {e}")
            return self._in_memory_records[-limit:]
