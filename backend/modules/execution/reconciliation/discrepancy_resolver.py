"""
Discrepancy Resolver
====================

PHASE 4.2 - Applies correction strategies for detected discrepancies.
"""

import time
import uuid
from typing import Dict, List, Tuple

from .reconciliation_types import (
    Discrepancy,
    DiscrepancyType,
    DiscrepancySeverity,
    ResolutionStrategy,
    ResolutionStatus,
    ReconciliationEvent,
    ExchangePosition,
    ExchangeOrder,
    ExchangeBalance
)
from .position_reconciler import PositionReconciler
from .order_reconciler import OrderReconciler
from .balance_reconciler import BalanceReconciler


class DiscrepancyResolver:
    """
    Resolves detected discrepancies by applying correction strategies:
    - SOFT_SYNC: update internal state to match exchange
    - HARD_SYNC: close/reset positions
    - ORDER_RECOVERY: re-track lost orders
    - BALANCE_REFRESH: refresh balance from exchange
    - MANUAL: flag for operator
    - IGNORE: below threshold
    """

    def __init__(self):
        self._auto_resolve_enabled = True
        self._max_auto_corrections_per_run = 20
        self._resolution_log: List[ReconciliationEvent] = []
        print("[DiscrepancyResolver] Initialized (PHASE 4.2)")

    def resolve_all(
        self,
        discrepancies: List[Discrepancy],
        position_reconciler: PositionReconciler,
        order_reconciler: OrderReconciler,
        balance_reconciler: BalanceReconciler,
        run_id: str = ""
    ) -> Tuple[int, int, List[ReconciliationEvent]]:
        """
        Resolve all discrepancies.
        Returns (resolved_count, failed_count, events).
        """
        resolved = 0
        failed = 0
        events = []

        for i, disc in enumerate(discrepancies):
            if i >= self._max_auto_corrections_per_run:
                disc.resolution_status = ResolutionStatus.SKIPPED
                disc.resolution_details = "Max auto-corrections reached"
                events.append(self._create_event("RESOLUTION_SKIPPED", run_id, disc))
                continue

            if disc.resolution_strategy == ResolutionStrategy.MANUAL:
                disc.resolution_status = ResolutionStatus.PENDING
                disc.resolution_details = "Requires manual intervention"
                events.append(self._create_event("RESOLUTION_MANUAL_REQUIRED", run_id, disc))
                continue

            if disc.resolution_strategy == ResolutionStrategy.IGNORE:
                disc.resolution_status = ResolutionStatus.SKIPPED
                disc.resolution_details = "Below threshold, ignored"
                events.append(self._create_event("RESOLUTION_IGNORED", run_id, disc))
                continue

            success, detail = self._apply_resolution(
                disc, position_reconciler, order_reconciler, balance_reconciler
            )

            if success:
                disc.resolution_status = ResolutionStatus.RESOLVED
                disc.resolution_details = detail
                disc.resolved_at = int(time.time() * 1000)
                resolved += 1
                events.append(self._create_event("RECONCILIATION_CORRECTED", run_id, disc))
            else:
                disc.resolution_status = ResolutionStatus.FAILED
                disc.resolution_details = detail
                failed += 1
                events.append(self._create_event("RECONCILIATION_FAILED", run_id, disc))

        self._resolution_log.extend(events)
        return resolved, failed, events

    def _apply_resolution(
        self,
        disc: Discrepancy,
        pos_recon: PositionReconciler,
        ord_recon: OrderReconciler,
        bal_recon: BalanceReconciler
    ) -> Tuple[bool, str]:
        """Apply a single resolution. Returns (success, detail)."""

        strategy = disc.resolution_strategy
        dtype = disc.discrepancy_type

        if strategy == ResolutionStrategy.SOFT_SYNC:
            return self._soft_sync(disc, pos_recon, ord_recon, bal_recon)
        elif strategy == ResolutionStrategy.HARD_SYNC:
            return self._hard_sync(disc, pos_recon)
        elif strategy == ResolutionStrategy.ORDER_RECOVERY:
            return self._order_recovery(disc, ord_recon)
        elif strategy == ResolutionStrategy.BALANCE_REFRESH:
            return self._balance_refresh(disc, bal_recon)
        else:
            return False, f"Unknown strategy: {strategy}"

    def _soft_sync(self, disc, pos_recon, ord_recon, bal_recon) -> Tuple[bool, str]:
        dtype = disc.discrepancy_type

        if dtype == DiscrepancyType.GHOST_POSITION:
            ex_data = disc.exchange_value
            if isinstance(ex_data, dict):
                ex_pos = ExchangePosition(
                    symbol=ex_data.get("symbol", disc.symbol),
                    side=ex_data.get("side", "LONG"),
                    size=ex_data.get("size", 0),
                    entry_price=ex_data.get("entryPrice", 0)
                )
                pos_recon.sync_position(ex_pos)
                return True, f"Synced ghost position {disc.symbol} to internal state"
            return False, "Missing exchange data for ghost position"

        elif dtype == DiscrepancyType.MISSING_POSITION:
            pos_recon.remove_position(disc.symbol)
            return True, f"Removed missing position {disc.symbol} from internal state"

        elif dtype == DiscrepancyType.POSITION_SIZE_MISMATCH:
            details = disc.details
            ex_size = details.get("exchangeSize", 0)
            positions = pos_recon.get_positions()
            for p in positions:
                if p.symbol == disc.symbol:
                    p.size = ex_size
                    p.updated_at = int(time.time() * 1000)
                    return True, f"Updated {disc.symbol} size to {ex_size}"
            return False, f"Position {disc.symbol} not found for size update"

        elif dtype in (DiscrepancyType.ORDER_STATE_MISMATCH, DiscrepancyType.MISSING_ORDER):
            details = disc.details
            oid = details.get("orderId", "")
            if dtype == DiscrepancyType.MISSING_ORDER:
                ord_recon.remove_order(oid)
                return True, f"Removed missing order {oid} from internal state"
            else:
                ex_status = disc.exchange_value
                orders = ord_recon.get_orders()
                if oid in orders:
                    orders[oid]["status"] = ex_status
                    return True, f"Updated order {oid} status to {ex_status}"
                return False, f"Order {oid} not found for status update"

        return False, f"Soft sync not implemented for {disc.discrepancy_type}"

    def _hard_sync(self, disc, pos_recon) -> Tuple[bool, str]:
        if disc.discrepancy_type == DiscrepancyType.POSITION_SIDE_MISMATCH:
            pos_recon.remove_position(disc.symbol)
            ex_data = disc.exchange_value
            if isinstance(ex_data, dict):
                ex_pos = ExchangePosition(
                    symbol=disc.symbol,
                    side=ex_data if isinstance(ex_data, str) else ex_data.get("side", "LONG"),
                    size=disc.details.get("exchangeSize", 0),
                    entry_price=0
                )
                pos_recon.sync_position(ex_pos)
                return True, f"Hard synced {disc.symbol}: removed and re-created from exchange"
            pos_recon.remove_position(disc.symbol)
            return True, f"Hard synced {disc.symbol}: removed stale position"
        return False, "Hard sync: unsupported discrepancy type"

    def _order_recovery(self, disc, ord_recon) -> Tuple[bool, str]:
        if disc.discrepancy_type == DiscrepancyType.GHOST_ORDER:
            ex_data = disc.exchange_value
            if isinstance(ex_data, dict):
                from .reconciliation_types import ExchangeOrder
                ex_order = ExchangeOrder(
                    order_id=ex_data.get("orderId", ""),
                    symbol=ex_data.get("symbol", disc.symbol),
                    side=ex_data.get("side", ""),
                    order_type=ex_data.get("type", ""),
                    status=ex_data.get("status", ""),
                    quantity=ex_data.get("quantity", 0),
                    filled_quantity=ex_data.get("filledQuantity", 0),
                    price=ex_data.get("price", 0)
                )
                ord_recon.sync_order(ex_order)
                return True, f"Recovered ghost order {ex_data.get('orderId', '')}"
            return False, "Missing exchange data for order recovery"

        elif disc.discrepancy_type == DiscrepancyType.ORDER_FILL_MISMATCH:
            details = disc.details
            oid = details.get("orderId", "")
            ex_filled = disc.exchange_value
            orders = ord_recon.get_orders()
            if oid in orders:
                orders[oid]["filled_quantity"] = ex_filled
                return True, f"Updated order {oid} filled quantity to {ex_filled}"
            return False, f"Order {oid} not found for fill update"

        return False, "Order recovery: unsupported discrepancy type"

    def _balance_refresh(self, disc, bal_recon) -> Tuple[bool, str]:
        ex_val = disc.exchange_value
        asset = disc.symbol

        if isinstance(ex_val, (int, float)):
            from .reconciliation_types import ExchangeBalance
            ex_bal = ExchangeBalance(
                asset=asset,
                total=float(ex_val),
                available=float(ex_val),
                locked=0,
                updated_at=int(time.time() * 1000)
            )
            bal_recon.sync_balance(ex_bal)
            return True, f"Refreshed balance for {asset} to {ex_val}"

        return True, f"Balance refresh flagged for {asset}"

    def _create_event(self, event_type: str, run_id: str, disc: Discrepancy) -> ReconciliationEvent:
        return ReconciliationEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            run_id=run_id,
            discrepancy_id=disc.discrepancy_id,
            details={
                "type": disc.discrepancy_type.value,
                "severity": disc.severity.value,
                "symbol": disc.symbol,
                "strategy": disc.resolution_strategy.value,
                "status": disc.resolution_status.value,
                "details": disc.resolution_details
            },
            timestamp=int(time.time() * 1000)
        )

    def get_resolution_log(self, limit: int = 50) -> List[ReconciliationEvent]:
        return self._resolution_log[-limit:]

    def clear(self):
        self._resolution_log.clear()

    def get_health(self) -> Dict:
        return {
            "engine": "DiscrepancyResolver",
            "version": "1.0.0",
            "phase": "4.2",
            "status": "active",
            "autoResolveEnabled": self._auto_resolve_enabled,
            "maxCorrectionsPerRun": self._max_auto_corrections_per_run,
            "totalResolutions": len(self._resolution_log),
            "timestamp": int(time.time() * 1000)
        }


discrepancy_resolver = DiscrepancyResolver()
