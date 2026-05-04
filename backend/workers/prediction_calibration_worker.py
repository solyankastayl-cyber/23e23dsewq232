"""
Prediction Calibration Worker

Recalibrates prediction system based on resolved outcomes.
"""

from typing import Dict, Any

from modules.prediction.calibration_engine_v2 import recalibrate


def run_prediction_calibration_worker(db) -> Dict[str, Any]:
    """
    Recalibrate prediction system.
    
    Should be run:
    - Every 6 hours, or
    - After every 50 new resolved predictions
    
    Returns:
        New calibration document
    """
    return recalibrate(db)
