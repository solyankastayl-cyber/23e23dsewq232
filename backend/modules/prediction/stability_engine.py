"""
Stability Engine

Combines all stability checks: regime instability, model health, calibration guard.
"""

import time
from typing import Dict, Any, Optional

from .regime_instability import compute_regime_instability
from .model_health import build_model_health
from .calibration_guard import build_calibration_guard


def build_stability_document(
    predictions: list,
    prev_doc: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build comprehensive stability document.
    
    Includes:
    - Regime instability scores
    - Model health status and penalties
    - Calibration guard status
    
    Returns:
        Stability document
    """
    regime_instability = compute_regime_instability(predictions)
    model_health, model_penalties = build_model_health(predictions)
    calibration_guard = build_calibration_guard(predictions, prev_doc)
    
    return {
        "_id": "global",
        "updated_at": int(time.time()),
        "regime_instability": regime_instability,
        "model_health": model_health,
        "model_penalties": model_penalties,
        "calibration_guard": calibration_guard,
    }


def rebuild_stability(db) -> Dict[str, Any]:
    """
    Rebuild stability document from resolved predictions.
    
    Should be run after recalibration.
    
    Returns:
        New stability document
    """
    try:
        predictions = list(db.prediction_snapshots.find({"status": "resolved"}))
    except Exception:
        predictions = []
    
    try:
        prev = db.prediction_stability.find_one({"_id": "global"})
    except Exception:
        prev = None
    
    doc = build_stability_document(predictions, prev)
    
    try:
        db.prediction_stability.update_one(
            {"_id": "global"},
            {"$set": doc},
            upsert=True
        )
    except Exception as e:
        print(f"[StabilityEngine] Error storing stability: {e}")
    
    return doc


def get_stability_status(db) -> Dict[str, Any]:
    """Get current stability status."""
    try:
        doc = db.prediction_stability.find_one({"_id": "global"})
        if doc:
            doc.pop("_id", None)
        return doc or {}
    except Exception:
        return {}
