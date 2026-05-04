"""
OPS2 - Position Lifecycle
=========================

Complete temporal history of positions from signal to close.

Provides:
- Timeline of all position events
- Lifecycle phases (ENTRY, ACTIVE, ADJUSTMENT, EXIT, CLOSED)
- MAE/MFE analytics
- State reconstruction from Event Ledger
"""

from .lifecycle_types import (
    PositionLifecycle,
    LifecycleEvent,
    LifecyclePhase,
    LifecycleStats
)
from .lifecycle_service import lifecycle_service

__all__ = [
    'PositionLifecycle',
    'LifecycleEvent',
    'LifecyclePhase',
    'LifecycleStats',
    'lifecycle_service'
]
