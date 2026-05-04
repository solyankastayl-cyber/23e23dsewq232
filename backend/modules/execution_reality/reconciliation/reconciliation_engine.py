"""Reconciliation Engine

Сравнивает локальные projections с exchange snapshots и находит mismatches.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ReconciliationEngine:
    """Движок reconciliation (сравнение локального и биржевого состояния)"""

    def reconcile_orders(
        self,
        local_orders: List[Dict[str, Any]],
        exchange_orders: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Сравнить локальные ордера с биржевыми.
        
        Returns:
            Список mismatches
        """
        mismatches = []

        # Создаём индексы
        local_by_exchange_id = {
            str(o.get("exchange_order_id")): o
            for o in local_orders
            if o.get("exchange_order_id")
        }

        exchange_ids = {str(o.get("orderId")) for o in exchange_orders}

        # Проверяем: есть ли локальные ордера, которых нет на бирже
        for ex_id, local in local_by_exchange_id.items():
            if ex_id not in exchange_ids and local.get("status") not in ["FILLED", "CANCELED", "REJECTED"]:
                # Локальный ордер ACK/PARTIAL, но его нет на бирже
                mismatches.append({
                    "type": "ORDER_MISSING_ON_EXCHANGE",
                    "exchange_order_id": ex_id,
                    "client_order_id": local.get("client_order_id"),
                    "local_status": local.get("status"),
                    "severity": "WARNING"
                })
                logger.warning(f"Mismatch: order {ex_id} missing on exchange, local status={local.get('status')}")

        # Проверяем: есть ли ордера на бирже, которых нет локально
        for ex_order in exchange_orders:
            ex_id = str(ex_order.get("orderId"))
            if ex_id not in local_by_exchange_id:
                # Ордер на бирже, но нет локально (возможно manual order)
                mismatches.append({
                    "type": "ORDER_UNKNOWN_LOCAL",
                    "exchange_order_id": ex_id,
                    "symbol": ex_order.get("symbol"),
                    "side": ex_order.get("side"),
                    "severity": "INFO"
                })
                logger.info(f"Mismatch: unknown order {ex_id} on exchange")

        return mismatches

    def reconcile_positions(
        self,
        local_positions: List[Dict[str, Any]],
        exchange_positions: List[Dict[str, Any]],
        qty_tolerance: float = 1e-8
    ) -> List[Dict[str, Any]]:
        """
        Сравнить локальные позиции с биржевыми.
        
        Args:
            qty_tolerance: толерантность к разнице в qty
        
        Returns:
            Список mismatches
        """
        mismatches = []

        # Индекс биржевых позиций
        ex_by_symbol = {
            p.get("symbol"): float(p.get("positionAmt", p.get("free", 0.0)) or 0.0)
            for p in exchange_positions
        }

        # Сравниваем
        for local in local_positions:
            symbol = local.get("symbol")
            local_qty = float(local.get("qty", local.get("size", 0.0)) or 0.0)
            ex_qty = ex_by_symbol.get(symbol, 0.0)

            if abs(local_qty - ex_qty) > qty_tolerance:
                severity = "CRITICAL" if abs(local_qty - ex_qty) > 0.01 else "WARNING"
                mismatches.append({
                    "type": "POSITION_QTY_MISMATCH",
                    "symbol": symbol,
                    "local_qty": local_qty,
                    "exchange_qty": ex_qty,
                    "diff": local_qty - ex_qty,
                    "severity": severity
                })
                logger.warning(
                    f"Mismatch: position {symbol} local={local_qty} exchange={ex_qty} diff={local_qty - ex_qty}"
                )

        return mismatches
