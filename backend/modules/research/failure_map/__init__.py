"""
PHASE 2.2 - Failure Map
=======================

Detects and tracks strategy failures:
- False Signals
- Regime Mismatch
- Strategy Degradation
- Selection Errors
"""

from .failure_types import (
    FailureType,
    FalseSignal,
    RegimeMismatch,
    StrategyDegradation,
    SelectionError,
    FailureSummary,
    FailureScan
)
from .false_signal_engine import false_signal_engine
from .regime_mismatch_engine import regime_mismatch_engine
from .strategy_degradation_engine import strategy_degradation_engine
from .selection_error_engine import selection_error_engine
from .failure_detector import failure_detector
from .failure_repository import failure_repository

__all__ = [
    'FailureType',
    'FalseSignal',
    'RegimeMismatch',
    'StrategyDegradation',
    'SelectionError',
    'FailureSummary',
    'FailureScan',
    'false_signal_engine',
    'regime_mismatch_engine',
    'strategy_degradation_engine',
    'selection_error_engine',
    'failure_detector',
    'failure_repository'
]
