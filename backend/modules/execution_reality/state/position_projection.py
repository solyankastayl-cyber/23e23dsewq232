"""Position Projection

Локальное состояние позиций = проекция из ORDER_FILL_RECORDED событий.
Проекция не «додумывает» состояние — только apply(event).
"""

from typing import Dict, Optional, List
from pydantic import BaseModel
from ..events.execution_event_types import ExecutionEvent, EXECUTION_EVENT_TYPES
import logging

logger = logging.getLogger(__name__)


class Position(BaseModel):
    """Проекция позиции (состояние = результат replay fill events)"""
    symbol: str
    qty: float  # положительный = LONG, отрицательный = SHORT
    avg_entry_price: float
    exchange: str


class PositionProjection:
    """Проекция состояния позиций"""

    def __init__(self):
        self._positions: Dict[str, Position] = {}  # symbol -> Position

    def apply(self, event: ExecutionEvent) -> None:
        """Применить событие к проекции"""
        # Поддерживаем как старый ORDER_FILL_RECORDED, так и новые FILL_PARTIAL/FILL_FULL
        if event.event_type in [
            EXECUTION_EVENT_TYPES["ORDER_FILL_RECORDED"],
            EXECUTION_EVENT_TYPES["FILL_PARTIAL"],
            EXECUTION_EVENT_TYPES["FILL_FULL"]
        ]:
            symbol = event.symbol
            side = event.payload.get("side", "BUY")
            fill_qty = event.payload.get("fill_qty", 0.0)
            fill_price = event.payload.get("fill_price", 0.0)

            # Определяем знаковый qty
            signed_qty = fill_qty if side == "BUY" else -fill_qty

            if symbol not in self._positions:
                # Новая позиция
                self._positions[symbol] = Position(
                    symbol=symbol,
                    qty=signed_qty,
                    avg_entry_price=fill_price,
                    exchange=event.exchange
                )
                logger.info(f"Position projection: NEW | {symbol} | qty={signed_qty}")
            else:
                # Обновляем существующую позицию
                pos = self._positions[symbol]
                old_qty = pos.qty
                new_qty = old_qty + signed_qty

                # Пересчёт avg_entry_price
                if new_qty != 0 and old_qty * signed_qty >= 0:  # увеличиваем позицию
                    pos.avg_entry_price = (
                        (pos.avg_entry_price * abs(old_qty) + fill_price * abs(signed_qty)) / abs(new_qty)
                    )
                elif new_qty * old_qty < 0:  # разворот
                    pos.avg_entry_price = fill_price

                pos.qty = new_qty
                logger.info(f"Position projection: UPDATE | {symbol} | qty={pos.qty}")

    def get_position(self, symbol: str) -> Optional[Position]:
        """Получить позицию по symbol"""
        return self._positions.get(symbol)

    def list_positions(self) -> List[Position]:
        """Список всех позиций"""
        return list(self._positions.values())
