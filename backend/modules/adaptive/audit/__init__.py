"""
PHASE 3.3 — Audit / Rollback Layer

System memory and recovery capabilities.
Enables rollback, diff analysis, and auto-recovery.

Modules:
- state_snapshot: Creates state snapshots
- snapshot_repository: Stores snapshots in MongoDB
- diff_engine: Computes state differences
- rollback_engine: Handles rollback logic with auto-rollback
"""

from .state_snapshot import StateSnapshot
from .snapshot_repository import SnapshotRepository
from .diff_engine import DiffEngine
from .rollback_engine import RollbackEngine

__all__ = [
    "StateSnapshot",
    "SnapshotRepository",
    "DiffEngine",
    "RollbackEngine",
]
