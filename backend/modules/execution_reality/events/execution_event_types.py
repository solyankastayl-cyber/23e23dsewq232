"""Execution Event Types

Минимальный набор канонических типов событий для Milestone A.
Событие = иммутабельная запись о том, что произошло.
"""

from typing import Literal
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid


# Canonical Event Types (Milestone A + B)
EXECUTION_EVENT_TYPES = {
    # Milestone A (submit flow)
    "ORDER_SUBMIT_REQUESTED": "ORDER_SUBMIT_REQUESTED",
    "ORDER_ACKNOWLEDGED": "ORDER_ACKNOWLEDGED",
    "ORDER_REJECTED": "ORDER_REJECTED",
    "ORDER_FILL_RECORDED": "ORDER_FILL_RECORDED",  # manual/legacy
    
    # Milestone B (exchange-driven truth)
    "FILL_PARTIAL": "FILL_PARTIAL",  # частичное исполнение
    "FILL_FULL": "FILL_FULL",        # полное исполнение
    "ORDER_CANCELED": "ORDER_CANCELED",  # отменён
    "BALANCE_SNAPSHOT": "BALANCE_SNAPSHOT",  # снимок баланса
    "RECONCILIATION_MISMATCH": "RECONCILIATION_MISMATCH",  # расхождение с биржей
}


class ExecutionEvent(BaseModel):
    """Базовая модель события исполнения"""
    event_id: str  # UUID события
    event_type: str  # ORDER_SUBMIT_REQUESTED | ORDER_ACKNOWLEDGED | ...
    timestamp: datetime  # UTC время события
    exchange: str  # binance | paper | simulation
    symbol: str | None = None  # BTCUSDT (optional для reconciliation events)
    client_order_id: str | None = None  # внутренний ID ордера (UUID) (optional)
    exchange_order_id: str | None = None  # ID от биржи (приходит в ACK)
    trace_id: str | None = None  # P0.7: audit trace ID for causal graph
    payload: dict  # дополнительные данные события

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


def create_event(
    event_type: str,
    exchange: str,
    symbol: str | None = None,
    client_order_id: str | None = None,
    exchange_order_id: str | None = None,
    trace_id: str | None = None,  # P0.7: audit trace ID
    payload: dict | None = None
) -> ExecutionEvent:
    """Фабрика для создания событий"""
    return ExecutionEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        exchange=exchange,
        symbol=symbol,
        client_order_id=client_order_id,
        exchange_order_id=exchange_order_id,
        trace_id=trace_id,  # P0.7
        payload=payload or {}
    )
