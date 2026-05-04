"""Binance Response Mapper

Маппит ответы Binance в канонические ExecutionEvent.
"""

from typing import Dict, Any
from ..events.execution_event_types import ExecutionEvent, EXECUTION_EVENT_TYPES, create_event
import logging

logger = logging.getLogger(__name__)


class BinanceMapper:
    """Mapper для Binance REST responses"""

    @staticmethod
    def map_order_response_to_event(
        binance_response: Dict[str, Any],
        client_order_id: str
    ) -> ExecutionEvent:
        """Маппит Binance order response в ORDER_ACKNOWLEDGED или ORDER_REJECTED"""
        status = binance_response.get("status")
        symbol = binance_response.get("symbol")
        exchange_order_id = str(binance_response.get("orderId", ""))

        # Простая логика: если status == "NEW" → ACK, иначе → REJECTED
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
            logger.info(f"Mapped Binance response to ORDER_ACKNOWLEDGED | {client_order_id}")
            return event
        else:
            # REJECTED
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
            logger.info(f"Mapped Binance response to ORDER_REJECTED | {client_order_id}")
            return event
