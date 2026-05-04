"""
PHASE 3.3 — Audit Routes

API endpoints for audit and rollback:
- POST /api/adaptive/audit/snapshot — Create snapshot
- GET /api/adaptive/audit/snapshots — List snapshots
- GET /api/adaptive/audit/snapshot/{hash} — Get specific snapshot
- GET /api/adaptive/audit/diff — Compare two snapshots
- POST /api/adaptive/audit/rollback — Rollback to snapshot
- POST /api/adaptive/audit/rollback/previous — Rollback to previous version
- GET /api/adaptive/audit/rollback/points — Get available rollback points
- GET /api/adaptive/audit/rollback/history — Get rollback history
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict
from datetime import datetime, timezone
from pydantic import BaseModel

from .state_snapshot import StateSnapshot
from .snapshot_repository import SnapshotRepository
from .diff_engine import DiffEngine
from .rollback_engine import RollbackEngine, RollbackReason


router = APIRouter(prefix="/api/adaptive/audit", tags=["audit"])


# Singletons
_snapshot_engine = StateSnapshot()
_repository = SnapshotRepository()
_diff_engine = DiffEngine()
_rollback_engine = RollbackEngine()


def _get_current_state() -> Dict:
    """Get current adaptive state."""
    try:
        from ..adaptive_state_registry import AdaptiveStateRegistry
        registry = AdaptiveStateRegistry()
        return registry.get_state()
    except Exception as e:
        print(f"[Audit] Get state error: {e}")
        return {}


def _save_state(state: Dict):
    """Save adaptive state."""
    try:
        from ..adaptive_state_registry import AdaptiveStateRegistry
        registry = AdaptiveStateRegistry()
        registry.update(state)
    except Exception as e:
        print(f"[Audit] Save state error: {e}")


class SnapshotRequest(BaseModel):
    """Request to create snapshot."""
    reason: Optional[str] = "manual"
    metadata: Optional[Dict] = None


class RollbackRequest(BaseModel):
    """Request to rollback."""
    snapshot_hash: str
    confirm: bool = False


@router.get("/health")
async def audit_health():
    """Health check for audit module."""
    return {
        "ok": True,
        "module": "audit",
        "version": "3.3",
        "components": [
            "state_snapshot",
            "snapshot_repository",
            "diff_engine",
            "rollback_engine"
        ],
        "snapshot_count": _repository.count(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/snapshot")
async def create_snapshot(request: SnapshotRequest):
    """Create a snapshot of current adaptive state."""
    current_state = _get_current_state()
    
    if not current_state:
        return {"ok": False, "error": "Could not get current state"}
    
    snapshot = _snapshot_engine.create_snapshot(
        state=current_state,
        trigger="manual",
        reason=request.reason,
        metadata=request.metadata
    )
    
    snapshot_id = _repository.save(snapshot)
    
    return {
        "ok": True,
        "snapshot_id": snapshot_id,
        "hash": snapshot["hash"],
        "version": snapshot["version"],
        "timestamp": snapshot["timestamp"]
    }


@router.get("/snapshots")
async def list_snapshots(
    limit: int = Query(20, ge=1, le=100),
    trigger: Optional[str] = Query(None, enum=["manual", "pre_apply", "post_apply", "safety", "scheduled"])
):
    """List available snapshots."""
    snapshots = _repository.get_history(limit=limit, trigger=trigger)
    
    return {
        "ok": True,
        "snapshots": snapshots,
        "count": len(snapshots),
        "total": _repository.count()
    }


@router.get("/snapshot/{snapshot_hash}")
async def get_snapshot(snapshot_hash: str, include_state: bool = Query(False)):
    """Get specific snapshot by hash."""
    snapshot = _repository.get_by_hash(snapshot_hash)
    
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    result = {
        "ok": True,
        "hash": snapshot.get("hash"),
        "timestamp": snapshot.get("timestamp"),
        "version": snapshot.get("version"),
        "trigger": snapshot.get("trigger"),
        "reason": snapshot.get("reason"),
        "metadata": snapshot.get("metadata")
    }
    
    if include_state:
        result["state"] = snapshot.get("state")
        result["summary"] = _snapshot_engine.get_state_summary(snapshot.get("state", {}))
    
    return result


@router.get("/diff")
async def compute_diff(
    old_hash: Optional[str] = None,
    new_hash: Optional[str] = None,
    compare_to_current: bool = Query(False)
):
    """
    Compute diff between two snapshots or snapshot and current state.
    
    If compare_to_current=true, compares old_hash to current state.
    """
    # Get old state
    if old_hash:
        old_snapshot = _repository.get_by_hash(old_hash)
        if old_snapshot is None:
            raise HTTPException(status_code=404, detail="Old snapshot not found")
        old_state = old_snapshot.get("state", {})
    else:
        # Use latest snapshot as old
        latest = _repository.get_latest(1)
        if not latest:
            raise HTTPException(status_code=404, detail="No snapshots available")
        old_state = latest[0].get("state", {})
        old_hash = latest[0].get("hash", "")
    
    # Get new state
    if compare_to_current or not new_hash:
        new_state = _get_current_state()
        new_hash = "current"
    else:
        new_snapshot = _repository.get_by_hash(new_hash)
        if new_snapshot is None:
            raise HTTPException(status_code=404, detail="New snapshot not found")
        new_state = new_snapshot.get("state", {})
    
    # Compute diff
    diff = _diff_engine.compute_diff(old_state, new_state)
    
    return {
        "ok": True,
        "old_hash": old_hash,
        "new_hash": new_hash,
        "diff": diff,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/rollback")
async def rollback_to_snapshot(request: RollbackRequest):
    """
    Rollback to a specific snapshot.
    
    Requires confirm=true in request body.
    """
    if not request.confirm:
        return {
            "ok": False,
            "error": "Confirmation required",
            "message": "Set confirm=true to proceed with rollback"
        }
    
    # Get snapshot
    snapshot = _repository.get_by_hash(request.snapshot_hash)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    current_state = _get_current_state()
    
    # Create safety snapshot before rollback
    _rollback_engine.create_safety_snapshot(current_state, "pre_rollback")
    
    # Perform rollback
    result = _rollback_engine.rollback_to_snapshot(
        snapshot=snapshot,
        current_state=current_state,
        reason=RollbackReason.MANUAL
    )
    
    if result.success:
        # Apply the rolled-back state
        restored_state = snapshot.get("state", {})
        restored_state["last_updated"] = datetime.now(timezone.utc).isoformat()
        restored_state["restored_from"] = request.snapshot_hash
        _save_state(restored_state)
    
    return {
        "ok": result.success,
        "from_version": result.from_version,
        "to_version": result.to_version,
        "snapshot_hash": result.snapshot_hash,
        "changes": result.diff.get("summary", {}),
        "timestamp": result.timestamp
    }


@router.post("/rollback/previous")
async def rollback_to_previous(confirm: bool = Query(False)):
    """Rollback to previous version."""
    if not confirm:
        return {
            "ok": False,
            "error": "Confirmation required",
            "message": "Add ?confirm=true to rollback"
        }
    
    current_state = _get_current_state()
    
    # Create safety snapshot
    _rollback_engine.create_safety_snapshot(current_state, "pre_rollback")
    
    # Perform rollback
    restored_state, result = _rollback_engine.rollback_to_previous(current_state)
    
    if result.success and restored_state:
        restored_state["last_updated"] = datetime.now(timezone.utc).isoformat()
        _save_state(restored_state)
    
    return {
        "ok": result.success,
        "from_version": result.from_version,
        "to_version": result.to_version,
        "changes": result.diff.get("summary", {}) if result.success else result.diff,
        "timestamp": result.timestamp
    }


@router.get("/rollback/points")
async def get_rollback_points(limit: int = Query(10, ge=1, le=50)):
    """Get available rollback points."""
    points = _rollback_engine.get_available_rollback_points(limit)
    
    return {
        "ok": True,
        "rollback_points": points,
        "count": len(points)
    }


@router.get("/rollback/history")
async def get_rollback_history(limit: int = Query(20, ge=1, le=100)):
    """Get rollback history."""
    history = _rollback_engine.get_rollback_history(limit)
    
    return {
        "ok": True,
        "history": history,
        "count": len(history)
    }


@router.post("/auto-rollback-check")
async def check_auto_rollback(
    current_metrics: Dict,
    previous_metrics: Dict
):
    """
    Check if auto-rollback should be triggered.
    
    For testing/monitoring purposes.
    """
    current_state = _get_current_state()
    
    should_rollback, reason = _rollback_engine.check_auto_rollback(
        current_metrics=current_metrics,
        previous_metrics=previous_metrics,
        current_state=current_state
    )
    
    return {
        "ok": True,
        "should_rollback": should_rollback,
        "reason": reason.value if reason else None,
        "thresholds": {
            "performance_drop": _rollback_engine.performance_drop_threshold,
            "error_spike": _rollback_engine.error_spike_threshold
        }
    }


# Integration: Create snapshots before/after action application
@router.post("/snapshot/pre-apply")
async def create_pre_apply_snapshot(reason: str = "pre_apply"):
    """Create snapshot before applying actions."""
    current_state = _get_current_state()
    
    snapshot = _snapshot_engine.create_snapshot(
        state=current_state,
        trigger="pre_apply",
        reason=reason
    )
    
    snapshot_id = _repository.save(snapshot)
    
    return {
        "ok": True,
        "snapshot_id": snapshot_id,
        "hash": snapshot["hash"],
        "for": "pre_apply"
    }


@router.post("/snapshot/post-apply")
async def create_post_apply_snapshot(
    pre_apply_hash: Optional[str] = None,
    reason: str = "post_apply"
):
    """Create snapshot after applying actions and compute diff."""
    current_state = _get_current_state()
    
    snapshot = _snapshot_engine.create_snapshot(
        state=current_state,
        trigger="post_apply",
        reason=reason,
        metadata={"pre_apply_hash": pre_apply_hash} if pre_apply_hash else None
    )
    
    snapshot_id = _repository.save(snapshot)
    
    result = {
        "ok": True,
        "snapshot_id": snapshot_id,
        "hash": snapshot["hash"],
        "for": "post_apply"
    }
    
    # Compute diff if pre_apply hash provided
    if pre_apply_hash:
        pre_snapshot = _repository.get_by_hash(pre_apply_hash)
        if pre_snapshot:
            diff = _diff_engine.compute_diff(
                pre_snapshot.get("state", {}),
                current_state
            )
            result["diff"] = diff
    
    return result
