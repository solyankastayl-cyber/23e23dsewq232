"""
Prediction Stability Worker

Rebuilds stability document and anti-drift checks.
"""

from typing import Dict, Any

from modules.prediction.stability_engine import rebuild_stability


def run_prediction_stability_worker(db) -> Dict[str, Any]:
    """
    Rebuild stability document.
    
    Should be run after recalibration.
    
    Returns:
        New stability document
    """
    return rebuild_stability(db)
