"""
Order Reconciler
================

PHASE 4.2 - Reconciles orders between system and exchange.
Detects ghost orders, missing orders, state mismatches, fill mismatches.
"""

import time
import uuid
from typing import Dict, List, Optional

from .reconciliation_types import (
    ExchangeOrder,
    Discrepancy,
    DiscrepancyType,
    DiscrepancySeverity,
    ResolutionStrategy
)


class OrderReconciler:
    """
    Reconciles orders:
    - Ghost orders (exchange only)
    - Missing orders (system only)
    - State mismatches
    - Fill quantity mismatches
    """

    def __init__(self):
        self._fill_tolerance_pct = 0.5
        self._internal_orders: Dict[str, Dict] = {}
        print("[OrderReconciler] Initialized (PHASE 4.2)")

    def reconcile(
        self,
        exchange_orders: List[ExchangeOrder],
        exchange: str = "BINANCE"
    ) -> List[Discrepancy]:
        discrepancies = []
        now = int(time.time() * 1000)

        exchange_by_id = {o.order_id: o for o in exchange_orders}
        internal_by_id = dict(self._internal_orders)

        # Ghost orders (exchange has, system doesn't)
        for oid, ex_order in exchange_by_id.items():
            if oid not in internal_by_id:
                discrepancies.append(Discrepancy(
                    discrepancy_id=f"disc_{uuid.uuid4().hex[:8]}",
                    discrepancy_type=DiscrepancyType.GHOST_ORDER,
                    severity=DiscrepancySeverity.HIGH,
                    exchange=exchange,
                    symbol=ex_order.symbol,
                    internal_value=None,
                    exchange_value=ex_order.to_dict(),
                    description=f"Ghost order: {oid} {ex_order.symbol} {ex_order.side} {ex_order.quantity} not tracked",
                    details={
                        "orderId": oid,
                        "symbol": ex_order.symbol,
                        "side": ex_order.side,
                        "status": ex_order.status,
                        "quantity": ex_order.quantity
                    },
                    resolution_strategy=ResolutionStrategy.ORDER_RECOVERY,
                    detected_at=now
                ))

        # Missing orders (system has, exchange doesn't)
        for oid, int_order in internal_by_id.items():
            if oid not in exchange_by_id:
                discrepancies.append(Discrepancy(
                    discrepancy_id=f"disc_{uuid.uuid4().hex[:8]}",
                    discrepancy_type=DiscrepancyType.MISSING_ORDER,
                    severity=DiscrepancySeverity.HIGH,
                    exchange=exchange,
                    symbol=int_order.get("symbol", ""),
                    internal_value=int_order,
                    exchange_value=None,
                    description=f"Missing order: {oid} {int_order.get('symbol', '')} not on exchange",
                    details={
                        "orderId": oid,
                        "symbol": int_order.get("symbol", ""),
                        "side": int_order.get("side", ""),
                        "status": int_order.get("status", "")
                    },
                    resolution_strategy=ResolutionStrategy.SOFT_SYNC,
                    detected_at=now
                ))

        # Matched orders — check state and fill mismatches
        for oid in set(exchange_by_id.keys()) & set(internal_by_id.keys()):
            ex_order = exchange_by_id[oid]
            int_order = internal_by_id[oid]

            # State mismatch
            int_status = int_order.get("status", "").upper()
            ex_status = ex_order.status.upper()
            if int_status != ex_status:
                severity = DiscrepancySeverity.CRITICAL if ex_status == "FILLED" and int_status != "FILLED" else DiscrepancySeverity.WARNING
                discrepancies.append(Discrepancy(
                    discrepancy_id=f"disc_{uuid.uuid4().hex[:8]}",
                    discrepancy_type=DiscrepancyType.ORDER_STATE_MISMATCH,
                    severity=severity,
                    exchange=exchange,
                    symbol=ex_order.symbol,
                    internal_value=int_status,
                    exchange_value=ex_status,
                    description=f"Order state mismatch: {oid} internal={int_status} exchange={ex_status}",
                    details={
                        "orderId": oid,
                        "internalStatus": int_status,
                        "exchangeStatus": ex_status
                    },
                    resolution_strategy=ResolutionStrategy.SOFT_SYNC,
                    detected_at=now
                ))

            # Fill mismatch
            int_filled = float(int_order.get("filled_quantity", 0))
            ex_filled = ex_order.filled_quantity
            if int_filled > 0 or ex_filled > 0:
                fill_diff = abs(ex_filled - int_filled)
                base = max(int_filled, ex_filled, 0.0001)
                fill_diff_pct = (fill_diff / base) * 100

                if fill_diff_pct > self._fill_tolerance_pct:
                    discrepancies.append(Discrepancy(
                        discrepancy_id=f"disc_{uuid.uuid4().hex[:8]}",
                        discrepancy_type=DiscrepancyType.ORDER_FILL_MISMATCH,
                        severity=DiscrepancySeverity.CRITICAL if fill_diff_pct > 10 else DiscrepancySeverity.HIGH,
                        exchange=exchange,
                        symbol=ex_order.symbol,
                        internal_value=int_filled,
                        exchange_value=ex_filled,
                        difference=fill_diff,
                        difference_pct=fill_diff_pct,
                        description=f"Fill mismatch: {oid} internal={int_filled} exchange={ex_filled}",
                        details={
                            "orderId": oid,
                            "internalFilled": int_filled,
                            "exchangeFilled": ex_filled
                        },
                        resolution_strategy=ResolutionStrategy.ORDER_RECOVERY,
                        detected_at=now
                    ))

        return discrepancies

    def add_order(self, order_id: str, order_data: Dict):
        self._internal_orders[order_id] = order_data

    def remove_order(self, order_id: str):
        self._internal_orders.pop(order_id, None)

    def get_orders(self) -> Dict[str, Dict]:
        return dict(self._internal_orders)

    def sync_order(self, exchange_order: ExchangeOrder):
        self._internal_orders[exchange_order.order_id] = {
            "order_id": exchange_order.order_id,
            "symbol": exchange_order.symbol,
            "side": exchange_order.side,
            "type": exchange_order.order_type,
            "status": exchange_order.status,
            "quantity": exchange_order.quantity,
            "filled_quantity": exchange_order.filled_quantity,
            "price": exchange_order.price,
            "synced": True
        }

    def clear(self):
        self._internal_orders.clear()

    def get_health(self) -> Dict:
        return {
            "engine": "OrderReconciler",
            "version": "1.0.0",
            "phase": "4.2",
            "status": "active",
            "trackedOrders": len(self._internal_orders),
            "fillTolerance": self._fill_tolerance_pct,
            "timestamp": int(time.time() * 1000)
        }


order_reconciler = OrderReconciler()
