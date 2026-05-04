"""
Prediction Metrics Worker

Computes and stores prediction metrics snapshots.
"""

from typing import Dict, Any

from modules.prediction.metrics_engine import compute_prediction_metrics_snapshot


def run_prediction_metrics_worker(db) -> Dict[str, Any]:
    """
    Compute and store prediction metrics snapshot.
    
    Should be run periodically (e.g., every 6 hours).
    
    Returns:
        Computed metrics snapshot
    """
    return compute_prediction_metrics_snapshot(db)
