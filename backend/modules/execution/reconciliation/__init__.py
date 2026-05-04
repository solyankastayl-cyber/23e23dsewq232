"""
PHASE 4.2 - Execution Reconciliation
=====================================

Ensures system state always matches exchange state.

Modules:
- reconciliation_engine.py - Core reconciliation logic
- position_reconciler.py - Position synchronization
- order_reconciler.py - Order synchronization
- balance_reconciler.py - Balance verification
- discrepancy_resolver.py - Auto-correction logic
- reconciliation_repository.py - Data persistence
- reconciliation_routes.py - API endpoints

Reconciliation Flow:
Fetch Exchange State -> Compare Internal -> Detect Discrepancies -> Resolve -> Log
"""

from .reconciliation_engine import ReconciliationEngine, reconciliation_engine
from .position_reconciler import PositionReconciler, position_reconciler
from .order_reconciler import OrderReconciler, order_reconciler
from .balance_reconciler import BalanceReconciler, balance_reconciler
from .discrepancy_resolver import DiscrepancyResolver, discrepancy_resolver
from .reconciliation_repository import reconciliation_repository

__all__ = [
    "ReconciliationEngine",
    "reconciliation_engine",
    "PositionReconciler",
    "position_reconciler",
    "OrderReconciler",
    "order_reconciler",
    "BalanceReconciler",
    "balance_reconciler",
    "DiscrepancyResolver",
    "discrepancy_resolver",
    "reconciliation_repository"
]
