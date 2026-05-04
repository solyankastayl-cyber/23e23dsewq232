"""
Strategy Behavior Diagnostics Module (STG4)
===========================================

Explainability layer for strategy decisions.

Provides:
- Decision traces
- Entry explanations
- Exit explanations
- Block explanations
- Hold explanations
"""

from .behavior_types import (
    StrategyDecisionTrace,
    EntryExplanation,
    ExitExplanation,
    BlockExplanation,
    HoldExplanation
)

from .behavior_service import behavior_diagnostics_service

from .behavior_routes import router

__all__ = [
    'StrategyDecisionTrace',
    'EntryExplanation',
    'ExitExplanation',
    'BlockExplanation',
    'HoldExplanation',
    'behavior_diagnostics_service',
    'router'
]
