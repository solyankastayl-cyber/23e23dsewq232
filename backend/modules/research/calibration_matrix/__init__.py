"""
PHASE 2.1 - Strategy Calibration Matrix
========================================

Builds performance matrix for:
- strategy x symbol x timeframe x regime

Metrics:
- win_rate
- profit_factor  
- expectancy
- max_drawdown
- average_trade
- sample_size
- block_rate
"""

from .calibration_types import (
    CalibrationConfig,
    CalibrationResult,
    CalibrationMetrics,
    CalibrationMatrix,
    CalibrationRun
)
from .calibration_metrics import CalibrationMetricsCalculator
from .calibration_repository import calibration_repository
from .calibration_engine import calibration_engine
from .calibration_runner import calibration_runner

__all__ = [
    'CalibrationConfig',
    'CalibrationResult',
    'CalibrationMetrics',
    'CalibrationMatrix',
    'CalibrationRun',
    'CalibrationMetricsCalculator',
    'calibration_repository',
    'calibration_engine',
    'calibration_runner'
]
