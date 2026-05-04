"""
Metrics by Regime/Model

Computes accuracy and error metrics grouped by regime and model.
"""

from typing import Dict, Any, List


def compute_bucket(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute metrics for a bucket of resolved predictions.
    
    Returns:
        Dict with total, accuracy, partial_rate, wrong_rate, avg_error
    """
    total = len(items)
    if total == 0:
        return {
            "total": 0,
            "accuracy": 0.0,
            "partial_rate": 0.0,
            "wrong_rate": 0.0,
            "avg_error": 0.0,
            "avg_confidence": 0.0,
        }
    
    correct = sum(1 for x in items if x.get("resolution", {}).get("result") == "correct")
    partial = sum(1 for x in items if x.get("resolution", {}).get("result") == "partial")
    wrong = sum(1 for x in items if x.get("resolution", {}).get("result") == "wrong")
    
    # Average error
    errors = [
        float(x.get("resolution", {}).get("error_pct", 0))
        for x in items
        if x.get("resolution", {}).get("error_pct") is not None
    ]
    avg_error = sum(errors) / len(errors) if errors else 0.0
    
    # Average confidence
    confs = [
        float(x.get("prediction_payload", {}).get("confidence", {}).get("value", 0))
        for x in items
    ]
    avg_conf = sum(confs) / len(confs) if confs else 0.0
    
    return {
        "total": total,
        "accuracy": round(correct / total, 4),
        "partial_rate": round(partial / total, 4),
        "wrong_rate": round(wrong / total, 4),
        "avg_error": round(avg_error, 4),
        "avg_confidence": round(avg_conf, 4),
    }


def group_by_field(items: List[Dict[str, Any]], field: str) -> Dict[str, Dict[str, Any]]:
    """
    Group items by field and compute metrics for each group.
    
    Args:
        items: List of resolved predictions
        field: Field to group by (e.g., "regime", "model")
    
    Returns:
        Dict mapping field values to their metrics
    """
    grouped = {}
    for item in items:
        # Field can be at top level or in prediction_payload
        key = item.get(field) or item.get("prediction_payload", {}).get(field)
        if not key:
            continue
        grouped.setdefault(key, []).append(item)
    
    return {k: compute_bucket(v) for k, v in grouped.items()}


def compute_global_metrics(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute global metrics across all predictions."""
    return compute_bucket(items)


def compute_confidence_vs_accuracy(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze confidence vs actual hit rate.
    
    Buckets predictions by confidence level and checks accuracy.
    """
    buckets = {
        "high_conf": [],    # >= 0.75
        "medium_conf": [],  # 0.55-0.75
        "low_conf": [],     # < 0.55
    }
    
    for item in items:
        conf = float(item.get("prediction_payload", {}).get("confidence", {}).get("value", 0))
        if conf >= 0.75:
            buckets["high_conf"].append(item)
        elif conf >= 0.55:
            buckets["medium_conf"].append(item)
        else:
            buckets["low_conf"].append(item)
    
    result = {}
    for bucket_name, bucket_items in buckets.items():
        metrics = compute_bucket(bucket_items)
        result[bucket_name] = {
            "total": metrics["total"],
            "accuracy": metrics["accuracy"],
            "avg_confidence": metrics["avg_confidence"],
            # Confidence calibration: is confidence aligned with accuracy?
            "calibration_gap": round(metrics["avg_confidence"] - metrics["accuracy"], 4)
        }
    
    return result
