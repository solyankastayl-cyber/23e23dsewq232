"""
PHASE 2.4 - Selection Validation
================================

Validates strategy selection accuracy:
- Compares chosen strategy vs best possible
- Calculates selection accuracy
- Measures performance gap
- Identifies misclassifications
"""

from .selection_types import (
    SelectionValidationConfig,
    SelectionValidationRun,
    SelectionComparison,
    SelectionMetrics,
    SelectionMistake
)
from .strategy_comparator import strategy_comparator
from .selection_validator import selection_validator
from .selection_metrics import selection_metrics_engine
from .selection_repository import selection_repository

__all__ = [
    'SelectionValidationConfig',
    'SelectionValidationRun',
    'SelectionComparison',
    'SelectionMetrics',
    'SelectionMistake',
    'strategy_comparator',
    'selection_validator',
    'selection_metrics_engine',
    'selection_repository'
]
