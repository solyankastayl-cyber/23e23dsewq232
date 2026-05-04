"""
PHASE 22.4 — Correlation Spike Engine
======================================
Detects correlation regime shifts when diversification breaks down.

Modules:
- correlation_types: Type definitions
- asset_correlation_engine: Asset-level correlation
- strategy_correlation_engine: Strategy-level correlation  
- factor_correlation_engine: Factor-level correlation
- correlation_spike_engine: Correlation spike detection
- correlation_aggregator: Combined correlation state
"""

from .correlation_types import (
    CorrelationState,
    CorrelationAction,
    CorrelationSpikeState,
    CORRELATION_THRESHOLDS,
    CORRELATION_MODIFIERS,
)

__all__ = [
    "CorrelationState",
    "CorrelationAction", 
    "CorrelationSpikeState",
    "CORRELATION_THRESHOLDS",
    "CORRELATION_MODIFIERS",
]
