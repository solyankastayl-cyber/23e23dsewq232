"""Mismatch Event Emitter

Превращает mismatch в RECONCILIATION_MISMATCH event.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any
from ..events.execution_event_types import create_event, EXECUTION_EVENT_TYPES

logger = logging.getLogger(__name__)


async def emit_mismatch(
    event_store,
    event_bus,
    mismatch: Dict[str, Any]
) -> None:
    """
    Записать mismatch как RECONCILIATION_MISMATCH event.
    
    Args:
        event_store: ExecutionEventStore
        event_bus: ExecutionEventBus
        mismatch: dict с полями type, severity, symbol, etc.
    """
    # Генерируем детерминированный event_id
    mismatch_type = mismatch.get("type", "UNKNOWN")
    symbol = mismatch.get("symbol", mismatch.get("exchange_order_id", "unknown"))
    event_id = f"evt-recon-{mismatch_type}-{symbol}-{int(datetime.now(timezone.utc).timestamp())}"

    event = create_event(
        event_type=EXECUTION_EVENT_TYPES["RECONCILIATION_MISMATCH"],
        exchange="binance",
        symbol=mismatch.get("symbol"),
        client_order_id=mismatch.get("client_order_id"),
        exchange_order_id=mismatch.get("exchange_order_id"),
        payload=mismatch
    )
    # Переписываем event_id
    event.event_id = event_id

    await event_store.append(event)
    await event_bus.publish(event)

    logger.warning(
        f"⚠️ RECONCILIATION_MISMATCH: {mismatch_type} | severity={mismatch.get('severity')} | {symbol}"
    )
