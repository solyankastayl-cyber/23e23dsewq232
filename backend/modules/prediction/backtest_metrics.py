"""
Backtest Metrics

Compute accuracy and performance metrics from backtest results.
"""

from typing import Dict, Any, List


def compute_backtest_metrics(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute metrics from backtest results.
    
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
            "target_hit_rate": 0.0,
            "wrong_early_rate": 0.0,
        }
    
    correct = sum(1 for x in items if x.get("resolution", {}).get("result") == "correct")
    partial = sum(1 for x in items if x.get("resolution", {}).get("result") == "partial")
    wrong = sum(1 for x in items if x.get("resolution", {}).get("result") == "wrong")
    
    target_hit = sum(1 for x in items if x.get("resolution", {}).get("resolution_type") == "target_hit")
    wrong_early = sum(1 for x in items if x.get("resolution", {}).get("resolution_type") == "wrong_early")
    
    avg_error = sum(
        float(x.get("resolution", {}).get("error_pct", 0))
        for x in items
    ) / total
    
    # Confidence vs accuracy analysis
    high_conf = [x for x in items if float(x.get("prediction_payload", {}).get("confidence", {}).get("value", 0)) >= 0.7]
    high_conf_correct = sum(1 for x in high_conf if x.get("resolution", {}).get("result") == "correct")
    high_conf_accuracy = high_conf_correct / len(high_conf) if high_conf else 0
    
    return {
        "total": total,
        "accuracy": round(correct / total, 4),
        "partial_rate": round(partial / total, 4),
        "wrong_rate": round(wrong / total, 4),
        "avg_error": round(avg_error, 4),
        "target_hit_rate": round(target_hit / total, 4),
        "wrong_early_rate": round(wrong_early / total, 4),
        "high_conf_count": len(high_conf),
        "high_conf_accuracy": round(high_conf_accuracy, 4),
    }


def group_by_field(items: List[Dict[str, Any]], field: str) -> Dict[str, Dict[str, Any]]:
    """
    Group results by field and compute metrics for each group.
    
    Args:
        items: List of backtest results
        field: Field to group by (regime, model, symbol)
    
    Returns:
        Dict mapping field values to their metrics
    """
    buckets = {}
    
    for item in items:
        key = item.get(field)
        if not key:
            continue
        buckets.setdefault(key, []).append(item)
    
    return {k: compute_backtest_metrics(v) for k, v in buckets.items()}


def compare_backtest_to_live(backtest_metrics: Dict, live_metrics: Dict) -> Dict[str, Any]:
    """
    Compare backtest metrics to live metrics.
    
    Detects potential leakage or drift.
    """
    comparison = {}
    
    for key in ["accuracy", "partial_rate", "wrong_rate", "avg_error"]:
        bt = backtest_metrics.get(key, 0)
        live = live_metrics.get(key, 0)
        diff = bt - live
        
        comparison[key] = {
            "backtest": bt,
            "live": live,
            "diff": round(diff, 4),
            "status": "ok" if abs(diff) < 0.1 else ("warning" if abs(diff) < 0.2 else "alert")
        }
    
    return comparison
