"""
Model Health Detector

Detects when models are degrading based on recent performance.
"""

from typing import Dict, Any, List, Tuple

from .rolling_metrics import take_last, compute_accuracy, compute_avg_error


def detect_model_health(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detect health status of a model.
    
    Compares recent performance (last 20) to full history.
    
    Returns:
        Dict with status ("healthy", "weak", "degrading", "insufficient")
        and penalty multiplier
    """
    if len(items) < 20:
        return {
            "status": "insufficient",
            "penalty": 1.0,
            "details": "Not enough data"
        }
    
    last_20 = take_last(items, 20)
    
    full_acc = compute_accuracy(items)
    last_acc = compute_accuracy(last_20)
    
    full_err = compute_avg_error(items)
    last_err = compute_avg_error(last_20)
    
    # Detect degradation
    if last_acc < full_acc - 0.10 or last_err > full_err + 0.03:
        return {
            "status": "degrading",
            "penalty": 0.88,
            "details": f"Recent accuracy {last_acc:.0%} vs historical {full_acc:.0%}"
        }
    
    if last_acc < full_acc - 0.05:
        return {
            "status": "weak",
            "penalty": 0.94,
            "details": f"Slight accuracy drop: {last_acc:.0%} vs {full_acc:.0%}"
        }
    
    return {
        "status": "healthy",
        "penalty": 1.0,
        "details": f"Accuracy stable at {last_acc:.0%}"
    }


def build_model_health(
    predictions: List[Dict[str, Any]]
) -> Tuple[Dict[str, str], Dict[str, float]]:
    """
    Build health status and penalties for all models.
    
    Returns:
        (model_health dict, model_penalties dict)
    """
    buckets = {}
    
    for p in predictions:
        model = p.get("model") or p.get("prediction_payload", {}).get("model")
        if not model:
            continue
        buckets.setdefault(model, []).append(p)
    
    health = {}
    penalties = {}
    
    for model, items in buckets.items():
        h = detect_model_health(items)
        health[model] = h["status"]
        penalties[model] = h["penalty"]
    
    return health, penalties
