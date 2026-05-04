"""Binance Response Mapper (Milestone B)

Маппит ответы Binance (REST + WebSocket executionReport) в канонические ExecutionEvent.
Не тащит raw Binance payload дальше по системе — нормализует сразу.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from ..events.execution_event_types import ExecutionEvent, EXECUTION_EVENT_TYPES, create_event
import logging

logger = logging.getLogger(__name__)


class BinanceMapperV2:
    """Mapper для Binance REST + WebSocket responses (Milestone B)"""

    @staticmethod
    def map_execution_report(data: Dict[str, Any]) -> Optional[ExecutionEvent]:
        """
        Маппит Binance execution report (WebSocket user stream) в канонические события.
        
        Binance executionReport содержит:
        - e: "executionReport"
        - x: execution type (NEW, CANCELED, REPLACED, REJECTED, TRADE, EXPIRED)
        - X: order status (NEW, PARTIALLY_FILLED, FILLED, CANCELED, REJECTED)
        - s: symbol
        - c: client order id
        - i: order id (exchange)
        - S: side
        - z: cumulative filled qty
        - l: last executed qty (в текущем trade)
        - L: last executed price
        - n: commission
        - N: commission asset
        - t: trade id (для TRADE events)
        - r: reject reason (для REJECTED)
        """
        exec_type = data.get("x")  # execution type
        order_status = data.get("X")  # order status
        symbol = data.get("s")
        client_order_id = data.get("c")
        exchange_order_id = str(data.get("i")) if data.get("i") is not None else None

        if exec_type == "TRADE":
            # TRADE = частичное или полное исполнение
            last_fill_qty = float(data.get("l", 0.0) or 0.0)  # qty в этом конкретном trade
            last_fill_price = float(data.get("L", 0.0) or 0.0)
            cumulative_qty = float(data.get("z", 0.0) or 0.0)  # cumulative filled qty (истина от биржи)
            trade_id = data.get("t")  # trade id

            # Определяем FILL_FULL vs FILL_PARTIAL
            event_type = (
                EXECUTION_EVENT_TYPES["FILL_FULL"]
                if order_status == "FILLED"
                else EXECUTION_EVENT_TYPES["FILL_PARTIAL"]
            )

            # Генерируем детерминированный event_id (для idempotency)
            event_id = f"evt-trade-{exchange_order_id}-{trade_id}"

            event = create_event(
                event_type=event_type,
                exchange="binance",
                symbol=symbol,
                client_order_id=client_order_id,
                exchange_order_id=exchange_order_id,
                payload={
                    "side": data.get("S"),
                    "fill_qty": last_fill_qty,  # qty в этом trade
                    "fill_price": last_fill_price,
                    "cum_qty": cumulative_qty,  # cumulative истина
                    "order_status": order_status,
                    "fee": float(data.get("n", 0.0) or 0.0),
                    "fee_asset": data.get("N"),
                    "trade_id": trade_id
                }
            )
            # Переписываем event_id на детерминированный
            event.event_id = event_id
            logger.info(f"Mapped TRADE → {event_type} | {client_order_id} | trade={trade_id}")
            return event

        elif exec_type == "CANCELED":
            # Ордер отменён
            event = create_event(
                event_type=EXECUTION_EVENT_TYPES["ORDER_CANCELED"],
                exchange="binance",
                symbol=symbol,
                client_order_id=client_order_id,
                exchange_order_id=exchange_order_id,
                payload={
                    "order_status": order_status,
                    "side": data.get("S")
                }
            )
            # Детерминированный event_id
            event.event_id = f"evt-cancel-{exchange_order_id}"
            logger.info(f"Mapped CANCELED → ORDER_CANCELED | {client_order_id}")
            return event

        elif exec_type == "REJECTED":
            # Ордер отклонён биржей
            event = create_event(
                event_type=EXECUTION_EVENT_TYPES["ORDER_REJECTED"],
                exchange="binance",
                symbol=symbol,
                client_order_id=client_order_id,
                exchange_order_id=exchange_order_id,
                payload={
                    "reason": data.get("r", "Unknown"),
                    "order_status": order_status,
                    "side": data.get("S")
                }
            )
            event.event_id = f"evt-reject-{client_order_id}-{exchange_order_id}"
            logger.info(f"Mapped REJECTED → ORDER_REJECTED | {client_order_id} | reason={data.get('r')}")
            return event

        elif exec_type == "NEW":
            # Ордер принят биржей (это дубликат ORDER_ACKNOWLEDGED из submit flow, можно skip)
            # Но если нужен для reconciliation, можно оставить
            logger.debug(f"Skipping NEW execution report (handled by submit flow) | {client_order_id}")
            return None

        else:
            # Неизвестный exec_type (EXPIRED, REPLACED, etc. — пока не обрабатываем)
            logger.warning(f"Unhandled exec_type: {exec_type} | {client_order_id}")
            return None

    @staticmethod
    def map_balance_update(data: Dict[str, Any]) -> ExecutionEvent:
        """
        Маппит outboundAccountPosition (balance snapshot) в BALANCE_SNAPSHOT event.
        
        Binance outboundAccountPosition:
        - e: "outboundAccountPosition"
        - E: event time
        - u: time of last account update
        - B: balances array [{a: asset, f: free, l: locked}, ...]
        """
        event = create_event(
            event_type=EXECUTION_EVENT_TYPES["BALANCE_SNAPSHOT"],
            exchange="binance",
            symbol=None,  # balance не привязан к symbol
            client_order_id=None,
            exchange_order_id=None,
            payload={
                "balances": data.get("B", []),
                "event_time": data.get("E"),
                "last_update_time": data.get("u")
            }
        )
        # Детерминированный event_id (по времени)
        event.event_id = f"evt-balance-{data.get('E', datetime.now(timezone.utc).timestamp())}"
        logger.info(f"Mapped outboundAccountPosition → BALANCE_SNAPSHOT")
        return event

    @staticmethod
    def map_order_response_to_event(
        binance_response: Dict[str, Any],
        client_order_id: str
    ) -> ExecutionEvent:
        """
        Маппит Binance REST order response (legacy Milestone A) в ORDER_ACKNOWLEDGED или ORDER_REJECTED.
        Оставляем для обратной совместимости.
        """
        status = binance_response.get("status")
        symbol = binance_response.get("symbol")
        exchange_order_id = str(binance_response.get("orderId", ""))

        if status == "NEW":
            event = create_event(
                event_type=EXECUTION_EVENT_TYPES["ORDER_ACKNOWLEDGED"],
                exchange="binance",
                symbol=symbol,
                client_order_id=client_order_id,
                exchange_order_id=exchange_order_id,
                payload={
                    "binance_status": status,
                    "price": binance_response.get("price"),
                    "qty": binance_response.get("origQty"),
                    "side": binance_response.get("side"),
                    "order_type": binance_response.get("type")
                }
            )
            logger.info(f"Mapped REST response to ORDER_ACKNOWLEDGED | {client_order_id}")
            return event
        else:
            event = create_event(
                event_type=EXECUTION_EVENT_TYPES["ORDER_REJECTED"],
                exchange="binance",
                symbol=symbol,
                client_order_id=client_order_id,
                payload={
                    "reason": f"Binance status: {status}",
                    "binance_status": status
                }
            )
            logger.info(f"Mapped REST response to ORDER_REJECTED | {client_order_id}")
            return event
