"""
OPS1 - Deep Position Monitor
============================

First-class operational entity for position management.

Provides complete visibility into each position:
- Identity: exchange, symbol, side, size, entry price
- Market: mark price, pnl, leverage
- Ownership: strategy, profile, config, decision trace
- Lifecycle: status, age, scaled/reduced flags
- Risk: exposure, liquidation distance, stop/TP distance

This transforms positions from simple exchange records into
fully managed operational entities.
"""

from .position_types import (
    DeepPositionState,
    PositionOwnership,
    PositionRiskView,
    PositionStatus,
    PositionSummary
)
from .position_service import position_service

__all__ = [
    'DeepPositionState',
    'PositionOwnership',
    'PositionRiskView',
    'PositionStatus',
    'PositionSummary',
    'position_service'
]
