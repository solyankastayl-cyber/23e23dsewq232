"""
Calibration Guard

Prevents calibration from degrading the system.
"""

from typing import Dict, Any, Optional

from .rolling_metrics import compute_accuracy


def build_calibration_guard(
    predictions: list,
    prev_snapshot: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build calibration guard status.
    
    Tracks accuracy over time and freezes calibration if it's hurting.
    
    Returns:
        Guard dict with status, accuracy tracking, freeze flag
    """
    current_acc = compute_accuracy(predictions)
    
    if not prev_snapshot:
        return {
            "status": "active",
            "last_accuracy": round(current_acc, 4),
            "current_accuracy": round(current_acc, 4),
            "freeze": False,
            "reason": "Initial state"
        }
    
    prev_guard = prev_snapshot.get("calibration_guard", {})
    last_accuracy = float(prev_guard.get("current_accuracy", current_acc))
    
    freeze = False
    status = "active"
    reason = "Calibration active"
    
    # If accuracy dropped significantly, freeze calibration
    if current_acc < last_accuracy - 0.05:
        freeze = True
        status = "frozen"
        reason = f"Accuracy dropped from {last_accuracy:.0%} to {current_acc:.0%}"
    
    # If accuracy dropped slightly, monitor
    elif current_acc < last_accuracy - 0.02:
        status = "warning"
        reason = f"Accuracy declining: {last_accuracy:.0%} → {current_acc:.0%}"
    
    return {
        "status": status,
        "last_accuracy": round(last_accuracy, 4),
        "current_accuracy": round(current_acc, 4),
        "freeze": freeze,
        "reason": reason
    }
