"""
Signal Explanation Engine — PHASE 51

Explains WHY a signal was generated.
Transforms black-box system into transparent research platform.

Features:
- Confidence breakdown by intelligence layer
- Driver analysis
- Conflict detection
- Narrative generation
"""

from .explainer import SignalExplainer, get_signal_explainer
from .models import (
    SignalExplanation,
    ConfidenceBreakdown,
    SignalDriver,
    SignalConflict,
)
from .routes import signal_explanation_router

__all__ = [
    "SignalExplainer",
    "get_signal_explainer",
    "SignalExplanation",
    "ConfidenceBreakdown",
    "SignalDriver",
    "SignalConflict",
    "signal_explanation_router",
]
