"""
PHASE 2.9 — Calibration Layer

Self-analyzing system that:
- Finds where edge exists
- Detects where edge disappears
- Understands why trades fail
- Provides actionable recommendations

Modules:
- calibration_matrix: Multi-dimensional performance matrix
- failure_map: Error type breakdown
- degradation_engine: Edge decay detection
- edge_classifier: Edge strength classification
- calibration_actions: Actionable recommendations
"""

from .calibration_matrix import CalibrationMatrix
from .failure_map import FailureMap
from .degradation_engine import DegradationEngine
from .edge_classifier import EdgeClassifier
from .calibration_actions import CalibrationActions

__all__ = [
    "CalibrationMatrix",
    "FailureMap",
    "DegradationEngine",
    "EdgeClassifier",
    "CalibrationActions",
]
