"""
Calibration Engine V2

Builds and updates calibration document from resolved predictions.
"""

import time
from typing import Dict, Any, Optional

from .calibration_stats import build_stats_by_field
from .calibration_rules import (
    stats_to_weight,
    stats_to_target_multiplier,
    stats_to_confidence_bias,
)


def build_calibration_document(predictions: list) -> Dict[str, Any]:
    """
    Build calibration document from resolved predictions.
    
    Returns:
        Calibration document with weights, multipliers, biases
    """
    regime_stats = build_stats_by_field(predictions, "regime")
    model_stats = build_stats_by_field(predictions, "model")
    
    # Convert stats to calibration values
    regime_weights = {k: stats_to_weight(v) for k, v in regime_stats.items()}
    model_weights = {k: stats_to_weight(v) for k, v in model_stats.items()}
    target_multipliers = {k: stats_to_target_multiplier(v) for k, v in regime_stats.items()}
    confidence_bias = {k: stats_to_confidence_bias(v) for k, v in regime_stats.items()}
    
    return {
        "_id": "global",
        "updated_at": int(time.time()),
        "regime_weights": regime_weights,
        "model_weights": model_weights,
        "target_multipliers": target_multipliers,
        "confidence_bias": confidence_bias,
        "regime_stats": regime_stats,
        "model_stats": model_stats,
    }


def recalibrate(db) -> Dict[str, Any]:
    """
    Recalibrate prediction system based on resolved outcomes.
    
    Loads resolved predictions, computes new calibration, stores it.
    
    Returns:
        New calibration document
    """
    try:
        predictions = list(db.prediction_snapshots.find({"status": "resolved"}))
    except Exception:
        predictions = []
    
    doc = build_calibration_document(predictions)
    
    # Upsert calibration document
    try:
        db.prediction_calibration.update_one(
            {"_id": "global"},
            {"$set": doc},
            upsert=True
        )
    except Exception as e:
        print(f"[CalibrationEngine] Error storing calibration: {e}")
    
    return doc


def get_calibration_status(db) -> Dict[str, Any]:
    """Get current calibration status."""
    try:
        doc = db.prediction_calibration.find_one({"_id": "global"})
        if doc:
            doc.pop("_id", None)
        return doc or {}
    except Exception:
        return {}
