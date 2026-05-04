"""
PHASE 13.3 - Factor Generator
==============================
Automatic factor generation from Feature Library.

Converts 308 features → 1000+ candidate factors.

Components:
- Factor Templates (8 types)
- Feature Selector (category compatibility)
- Factor Combinator (pair, triple, ratio, etc.)
- Factor Transformer (zscore, rank, etc.)
- Factor Constraints (anti-duplication, complexity limits)
"""

from .factor_types import (
    Factor, FactorFamily, FactorTemplate, FactorStatus,
    FactorBatchRun, BatchRunStatus
)
from .factor_generator import FactorGenerator, get_factor_generator
from .factor_repository import FactorRepository

__all__ = [
    "Factor",
    "FactorFamily",
    "FactorTemplate",
    "FactorStatus",
    "FactorBatchRun",
    "BatchRunStatus",
    "FactorGenerator",
    "get_factor_generator",
    "FactorRepository"
]
