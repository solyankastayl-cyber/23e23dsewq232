"""
Calibration Statistics

Computes statistics needed for calibration from resolved predictions.
"""

from typing import Dict, Any, List


def compute_bucket_stats(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute detailed stats for a bucket of predictions.
    
    Used for calibration weight calculations.
    """
    total = len(items)
    if total == 0:
        return {
            "count": 0,
            "accuracy": 0.0,
            "partial_rate": 0.0,
            "wrong_rate": 0.0,
            "avg_error": 1.0,
            "avg_confidence": 0.0,
        }
    
    correct = sum(1 for x in items if x.get("resolution", {}).get("result") == "correct")
    partial = sum(1 for x in items if x.get("resolution", {}).get("result") == "partial")
    wrong = sum(1 for x in items if x.get("resolution", {}).get("result") == "wrong")
    
    avg_error = sum(
        float(x.get("resolution", {}).get("error_pct", 0)) 
        for x in items
    ) / total
    
    avg_conf = sum(
        float(x.get("prediction_payload", {}).get("confidence", {}).get("value", 0))
        for x in items
    ) / total
    
    return {
        "count": total,
        "accuracy": round(correct / total, 4),
        "partial_rate": round(partial / total, 4),
        "wrong_rate": round(wrong / total, 4),
        "avg_error": round(avg_error, 4),
        "avg_confidence": round(avg_conf, 4),
    }


def build_stats_by_field(
    predictions: List[Dict[str, Any]],
    field: str
) -> Dict[str, Dict[str, Any]]:
    """
    Build stats grouped by field (regime or model).
    """
    buckets = {}
    
    for p in predictions:
        # Field can be at top level or in prediction_payload
        key = p.get(field) or p.get("prediction_payload", {}).get(field)
        if not key:
            continue
        buckets.setdefault(key, []).append(p)
    
    return {k: compute_bucket_stats(v) for k, v in buckets.items()}
