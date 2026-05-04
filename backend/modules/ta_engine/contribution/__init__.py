"""
Contribution Engine
===================
Unified TA Context - собирает вклад от ВСЕХ источников TA.

Каждый источник возвращает:
- signal: bullish/bearish/neutral
- score: -1.0 to +1.0
- confidence: 0.0 to 1.0
- contribution_weight: вес в общем решении
- render_type: overlay/pane/background/informational
- used_in_decision: bool
"""

from .contribution_engine import (
    ContributionEngine,
    get_contribution_engine,
    Contribution,
    UnifiedTAContext,
)

__all__ = [
    "ContributionEngine",
    "get_contribution_engine",
    "Contribution",
    "UnifiedTAContext",
]
