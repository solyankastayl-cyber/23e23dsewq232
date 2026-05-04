"""
Rolling Metrics

Utilities for computing metrics over rolling windows.
"""

from typing import Dict, Any, List


def take_last(items: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    """Take last N items sorted by created_at."""
    if len(items) <= n:
        return items
    sorted_items = sorted(items, key=lambda x: x.get("created_at", 0))
    return sorted_items[-n:]


def compute_accuracy(items: List[Dict[str, Any]]) -> float:
    """Compute accuracy from resolved predictions."""
    total = len(items)
    if total == 0:
        return 0.0
    correct = sum(
        1 for x in items 
        if x.get("resolution", {}).get("result") == "correct"
    )
    return correct / total


def compute_avg_error(items: List[Dict[str, Any]]) -> float:
    """Compute average error from resolved predictions."""
    total = len(items)
    if total == 0:
        return 1.0
    return sum(
        float(x.get("resolution", {}).get("error_pct", 0))
        for x in items
    ) / total
