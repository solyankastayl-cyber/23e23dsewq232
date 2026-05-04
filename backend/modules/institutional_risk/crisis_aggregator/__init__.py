"""
PHASE 22.5 — Crisis Exposure Aggregator
=======================================
Unifies all institutional risk modules into a single crisis exposure state.

Combines:
- VaR Engine (22.1)
- Tail Risk Engine (22.2)
- Cluster Contagion (22.3)
- Correlation Spike (22.4)

Provides top-level institutional risk overlay for the platform.
"""

from .crisis_types import (
    CrisisState,
    CrisisAction,
    CrisisExposureState,
    CRISIS_THRESHOLDS,
    CRISIS_MODIFIERS,
    STATE_SCORES,
)

from .crisis_exposure_engine import CrisisExposureEngine

__all__ = [
    "CrisisState",
    "CrisisAction",
    "CrisisExposureState",
    "CrisisExposureEngine",
    "CRISIS_THRESHOLDS",
    "CRISIS_MODIFIERS",
    "STATE_SCORES",
]
