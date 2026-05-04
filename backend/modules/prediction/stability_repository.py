"""
Stability Repository

Load and apply stability adjustments to predictions.
"""

from typing import Dict, Any


def load_stability(db) -> Dict[str, Any]:
    """
    Load current stability document from database.
    
    Returns empty/neutral stability if none exists.
    """
    try:
        doc = db.prediction_stability.find_one({"_id": "global"})
        if doc:
            return doc
    except Exception:
        pass
    
    return {
        "regime_instability": {},
        "model_health": {},
        "model_penalties": {},
        "calibration_guard": {
            "status": "active",
            "freeze": False
        }
    }


def apply_stability(
    pred: Dict[str, Any],
    stability_doc: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Apply stability-based adjustments to prediction.
    
    Penalizes:
    - Predictions in unstable regimes
    - Predictions from degrading models
    - All predictions when calibration is frozen
    
    Returns:
        Modified prediction dict
    """
    regime = pred.get("regime", "")
    model = pred.get("model", "")
    
    # Get stability values
    regime_instability = float(
        stability_doc.get("regime_instability", {}).get(regime, 0.0)
    )
    model_penalty = float(
        stability_doc.get("model_penalties", {}).get(model, 1.0)
    )
    guard = stability_doc.get("calibration_guard", {})
    
    # Start with current confidence
    conf = float(pred.get("confidence", {}).get("value", 0))
    
    # Apply regime instability penalty
    if regime_instability > 0.20:
        conf *= 0.88
    elif regime_instability > 0.10:
        conf *= 0.94
    
    # Apply model degradation penalty
    conf *= model_penalty
    
    # Apply calibration freeze penalty (conservative mode)
    if guard.get("freeze", False):
        conf *= 0.92
    
    # Clamp
    conf = max(0.0, min(conf, 0.90))
    pred["confidence"]["value"] = round(conf, 3)
    
    # Add stability metadata
    pred["stability_applied"] = {
        "regime_instability": regime_instability,
        "model_penalty": model_penalty,
        "calibration_freeze": guard.get("freeze", False),
        "model_health": stability_doc.get("model_health", {}).get(model, "unknown")
    }
    
    return pred
