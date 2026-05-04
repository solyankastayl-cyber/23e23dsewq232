"""
Metrics Engine

Computes and stores prediction metrics snapshots.
"""

import time
from typing import Dict, Any, Optional

from .metrics_by_regime import (
    compute_global_metrics,
    group_by_field,
    compute_confidence_vs_accuracy,
)


def compute_prediction_metrics_snapshot(db) -> Dict[str, Any]:
    """
    Compute full metrics snapshot from resolved predictions.
    
    Stores in prediction_metrics_snapshots collection.
    
    Returns:
        Metrics snapshot dict
    """
    # Get all resolved predictions
    try:
        resolved = list(db.prediction_snapshots.find({"status": "resolved"}))
    except Exception:
        resolved = []
    
    if not resolved:
        return {
            "created_at": int(time.time()),
            "global": {"total": 0},
            "by_regime": {},
            "by_model": {},
            "confidence_calibration": {},
        }
    
    snapshot = {
        "created_at": int(time.time()),
        "global": compute_global_metrics(resolved),
        "by_regime": group_by_field(resolved, "regime"),
        "by_model": group_by_field(resolved, "model"),
        "confidence_calibration": compute_confidence_vs_accuracy(resolved),
    }
    
    # Store snapshot
    try:
        db.prediction_metrics_snapshots.insert_one(snapshot.copy())
    except Exception as e:
        print(f"[MetricsEngine] Error storing snapshot: {e}")
    
    return snapshot


def get_latest_metrics_snapshot(db) -> Optional[Dict[str, Any]]:
    """Get most recent metrics snapshot."""
    try:
        snap = db.prediction_metrics_snapshots.find_one(
            sort=[("created_at", -1)]
        )
        if snap:
            snap.pop("_id", None)
        return snap
    except Exception:
        return None


def get_metrics_by_regime(db) -> Dict[str, Dict[str, Any]]:
    """Get latest metrics grouped by regime."""
    snap = get_latest_metrics_snapshot(db)
    return (snap or {}).get("by_regime", {})


def get_metrics_by_model(db) -> Dict[str, Dict[str, Any]]:
    """Get latest metrics grouped by model."""
    snap = get_latest_metrics_snapshot(db)
    return (snap or {}).get("by_model", {})
