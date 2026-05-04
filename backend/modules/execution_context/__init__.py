"""
PHASE 25.5 — Execution Context Module

Macro-Fractal Execution Context Layer.

This module provides execution-level modifiers based on
macro-fractal intelligence WITHOUT changing:
- strategy
- direction  
- signal

Only modifies:
- confidence_modifier
- capital_modifier

Weight limits:
- Fractal: 16%
- Macro: 2%
"""

from .execution_context_types import (
    ExecutionContext,
    ExecutionContextSummary,
    ExecutionContextHealthStatus,
)
from .execution_context_engine import (
    ExecutionContextEngine,
    get_execution_context_engine,
)

__all__ = [
    "ExecutionContext",
    "ExecutionContextSummary", 
    "ExecutionContextHealthStatus",
    "ExecutionContextEngine",
    "get_execution_context_engine",
]
