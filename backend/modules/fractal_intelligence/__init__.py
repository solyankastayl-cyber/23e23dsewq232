"""
PHASE 24.1 — Fractal Intelligence Module

Isolated internal module that provides fractal-based market intelligence
as a third signal leg alongside TA and Exchange intelligence.

Architecture principle:
- Self-contained, no imports from TA/Exchange internals
- System interacts only via FractalContext contract
- Implementation is replaceable without modifying core system
"""

from .fractal_context_types import (
    FractalContext,
    FractalContextSummary,
    FractalHealthStatus,
    HorizonBias,
)
from .fractal_context_engine import FractalContextEngine
from .fractal_context_adapter import FractalContextAdapter
from .fractal_context_client import FractalClient

__all__ = [
    "FractalContext",
    "FractalContextSummary",
    "FractalHealthStatus",
    "HorizonBias",
    "FractalContextEngine",
    "FractalContextAdapter",
    "FractalClient",
]
