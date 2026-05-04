"""
PHASE 3.3 — Rollback Engine

Handles state rollback with auto-rollback on degradation.
Critical for system recovery.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from .state_snapshot import StateSnapshot
from .snapshot_repository import SnapshotRepository
from .diff_engine import DiffEngine


class RollbackReason(Enum):
    """Reasons for rollback."""
    MANUAL = "manual"
    PERFORMANCE_DROP = "performance_drop"
    ERROR_SPIKE = "error_spike"
    EMERGENCY = "emergency"
    SCHEDULED = "scheduled"


@dataclass
class RollbackResult:
    """Result of rollback operation."""
    success: bool
    reason: RollbackReason
    from_version: int
    to_version: int
    snapshot_hash: str
    diff: Dict
    timestamp: str


class RollbackEngine:
    """
    Manages rollback operations.
    
    Features:
    - Manual rollback
    - Auto-rollback on performance degradation
    - Rollback history
    - Safety checks
    """
    
    def __init__(self, db=None):
        self.snapshot_engine = StateSnapshot()
        self.repository = SnapshotRepository(db)
        self.diff_engine = DiffEngine()
        self._rollback_history: List[Dict] = []
        
        # Auto-rollback thresholds
        self.performance_drop_threshold = 0.3  # 30% drop triggers rollback
        self.error_spike_threshold = 0.5  # 50% error rate triggers rollback
    
    def rollback_to_snapshot(
        self,
        snapshot: Dict,
        current_state: Dict,
        reason: RollbackReason = RollbackReason.MANUAL
    ) -> RollbackResult:
        """
        Rollback to a specific snapshot.
        
        Args:
            snapshot: Snapshot to rollback to
            current_state: Current adaptive state
            reason: Why rollback is happening
        
        Returns:
            RollbackResult with details
        """
        # Verify snapshot integrity
        if not self.snapshot_engine.verify_integrity(snapshot):
            return RollbackResult(
                success=False,
                reason=reason,
                from_version=current_state.get("version", 0),
                to_version=0,
                snapshot_hash="",
                diff={},
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        # Compute diff for audit
        diff = self.diff_engine.compute_diff(current_state, snapshot["state"])
        
        # Create result
        result = RollbackResult(
            success=True,
            reason=reason,
            from_version=current_state.get("version", 0),
            to_version=snapshot["state"].get("version", 0),
            snapshot_hash=snapshot.get("hash", ""),
            diff=diff,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Record rollback
        self._record_rollback(result, snapshot)
        
        return result
    
    def rollback_to_previous(self, current_state: Dict) -> Tuple[Optional[Dict], RollbackResult]:
        """
        Rollback to previous version.
        
        Returns:
            (restored_state, result)
        """
        current_version = current_state.get("version", 0)
        
        # Find previous snapshot
        previous = self.repository.get_previous(current_version)
        
        if previous is None:
            return None, RollbackResult(
                success=False,
                reason=RollbackReason.MANUAL,
                from_version=current_version,
                to_version=0,
                snapshot_hash="",
                diff={"error": "No previous snapshot found"},
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        result = self.rollback_to_snapshot(previous, current_state, RollbackReason.MANUAL)
        
        if result.success:
            return previous["state"], result
        
        return None, result
    
    def check_auto_rollback(
        self,
        current_metrics: Dict,
        previous_metrics: Dict,
        current_state: Dict
    ) -> Tuple[bool, Optional[RollbackReason]]:
        """
        Check if auto-rollback should be triggered.
        
        Args:
            current_metrics: Current performance metrics
            previous_metrics: Previous performance metrics
            current_state: Current adaptive state
        
        Returns:
            (should_rollback, reason)
        """
        # Check performance drop
        current_sharpe = current_metrics.get("sharpe", 0)
        previous_sharpe = previous_metrics.get("sharpe", 0)
        
        if previous_sharpe > 0:
            sharpe_drop = (previous_sharpe - current_sharpe) / previous_sharpe
            if sharpe_drop > self.performance_drop_threshold:
                return True, RollbackReason.PERFORMANCE_DROP
        
        # Check win rate drop
        current_wr = current_metrics.get("win_rate", 0)
        previous_wr = previous_metrics.get("win_rate", 0)
        
        if previous_wr > 0:
            wr_drop = (previous_wr - current_wr) / previous_wr
            if wr_drop > self.performance_drop_threshold:
                return True, RollbackReason.PERFORMANCE_DROP
        
        # Check error rate spike
        current_error_rate = current_metrics.get("error_rate", 0)
        if current_error_rate > self.error_spike_threshold:
            return True, RollbackReason.ERROR_SPIKE
        
        # Check max drawdown increase
        current_dd = current_metrics.get("max_drawdown", 0)
        previous_dd = previous_metrics.get("max_drawdown", 0)
        
        if current_dd > previous_dd * 2 and current_dd > 0.15:  # >2x and >15%
            return True, RollbackReason.PERFORMANCE_DROP
        
        return False, None
    
    def auto_rollback(
        self,
        current_metrics: Dict,
        previous_metrics: Dict,
        current_state: Dict
    ) -> Tuple[Optional[Dict], Optional[RollbackResult]]:
        """
        Perform auto-rollback if needed.
        
        Returns:
            (restored_state, result) or (None, None) if no rollback needed
        """
        should_rollback, reason = self.check_auto_rollback(
            current_metrics, previous_metrics, current_state
        )
        
        if not should_rollback:
            return None, None
        
        # Get previous snapshot
        restored_state, result = self.rollback_to_previous(current_state)
        
        if result.success:
            result.reason = reason
        
        return restored_state, result
    
    def _record_rollback(self, result: RollbackResult, snapshot: Dict):
        """Record rollback in history."""
        record = {
            "timestamp": result.timestamp,
            "success": result.success,
            "reason": result.reason.value,
            "from_version": result.from_version,
            "to_version": result.to_version,
            "snapshot_hash": result.snapshot_hash,
            "changes_summary": result.diff.get("summary", {})
        }
        
        self._rollback_history.append(record)
        
        # Trim history
        if len(self._rollback_history) > 50:
            self._rollback_history = self._rollback_history[-50:]
    
    def get_rollback_history(self, limit: int = 20) -> List[Dict]:
        """Get rollback history."""
        return self._rollback_history[-limit:]
    
    def get_available_rollback_points(self, limit: int = 10) -> List[Dict]:
        """Get available snapshots for rollback."""
        snapshots = self.repository.get_history(limit=limit)
        
        return [
            {
                "hash": s.get("hash"),
                "timestamp": s.get("timestamp"),
                "version": s.get("version"),
                "trigger": s.get("trigger"),
                "reason": s.get("reason")
            }
            for s in snapshots
        ]
    
    def create_safety_snapshot(self, state: Dict, reason: str = "pre_change") -> str:
        """Create a safety snapshot before making changes."""
        snapshot = self.snapshot_engine.create_snapshot(
            state=state,
            trigger="safety",
            reason=reason
        )
        
        return self.repository.save(snapshot)
