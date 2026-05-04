"""
State Reconciliation Layer
Critical module for syncing internal state with exchange reality.

Protects against:
- Ghost positions (internal record but no exchange position)
- Ghost orders (internal order but not on exchange)
- Partial fills desync
- Balance drift
- OMS divergence

Components:
- recon_types.py: Data models for reconciliation
- recon_service.py: Core reconciliation logic
- recon_repository.py: MongoDB persistence
- exchange_adapter.py: Exchange state fetcher
- recon_routes.py: API endpoints
"""

from .recon_types import (
    ReconciliationRun,
    ReconciliationResult,
    ReconciliationMismatch,
    MismatchType,
    MismatchSeverity,
    ReconciliationStatus,
    ExchangeState
)
from .recon_service import ReconciliationService
from .recon_routes import router as reconciliation_router

__all__ = [
    "ReconciliationRun",
    "ReconciliationResult",
    "ReconciliationMismatch",
    "MismatchType",
    "MismatchSeverity",
    "ReconciliationStatus",
    "ExchangeState",
    "ReconciliationService",
    "reconciliation_router"
]
