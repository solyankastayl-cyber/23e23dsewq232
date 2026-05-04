"""
PHASE 23.4 — Portfolio Resilience Aggregator
============================================
Final resilience overlay combining Stress Grid and Strategy Survival Matrix.

Answers the key question:
"How resilient is the entire platform as a portfolio + strategy set?"

Components:
- resilience_types: Type definitions
- portfolio_resilience_engine: Calculates combined resilience
- resilience_registry: State caching
"""

from .resilience_types import (
    ResilienceStateEnum,
    ResilienceAction,
    PortfolioResilienceState,
    RESILIENCE_THRESHOLDS,
    RESILIENCE_MODIFIERS,
)

from .portfolio_resilience_engine import PortfolioResilienceEngine

__all__ = [
    "ResilienceStateEnum",
    "ResilienceAction",
    "PortfolioResilienceState",
    "RESILIENCE_THRESHOLDS",
    "RESILIENCE_MODIFIERS",
    "PortfolioResilienceEngine",
]
