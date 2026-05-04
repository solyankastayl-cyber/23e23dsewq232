"""Trade Ledger

Реестр всех сделок, построенный из событий.
Источник правды для PnL.

КРИТИЧНО: НЕ брать данные из позиций напрямую.
Только из FILL_PARTIAL / FILL_FULL событий.
"""

from typing import List, Dict, Any
import logging
from ..events.execution_event_types import ExecutionEvent, EXECUTION_EVENT_TYPES

logger = logging.getLogger(__name__)


class TradeLedger:
    """Реестр сделок (только из FILL событий)"""

    def __init__(self):
        self.trades: List[Dict[str, Any]] = []

    def apply(self, event: ExecutionEvent) -> None:
        """
        Применить событие к ledger.
        Только FILL_PARTIAL / FILL_FULL / ORDER_FILL_RECORDED (легаси).
        """
        if event.event_type not in [
            EXECUTION_EVENT_TYPES["FILL_PARTIAL"],
            EXECUTION_EVENT_TYPES["FILL_FULL"],
            EXECUTION_EVENT_TYPES["ORDER_FILL_RECORDED"]  # legacy manual fill
        ]:
            return

        p = event.payload

        # Normalized trade record
        trade = {
            "symbol": event.symbol,
            "side": p.get("side", "BUY"),
            "qty": p.get("fill_qty", 0.0),
            "price": p.get("fill_price", 0.0),
            "fee": p.get("fee", 0.0),
            "fee_asset": p.get("fee_asset"),
            "timestamp": event.timestamp,
            "client_order_id": event.client_order_id,
            "exchange_order_id": event.exchange_order_id,
            "event_id": event.event_id  # для трейсинга
        }

        self.trades.append(trade)
        logger.debug(f"Trade recorded: {event.symbol} {p.get('side')} {p.get('fill_qty')} @ {p.get('fill_price')}")

    def get_trades_for_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """Получить все сделки для символа"""
        return [t for t in self.trades if t["symbol"] == symbol]

    def get_all_trades(self) -> List[Dict[str, Any]]:
        """Получить все сделки"""
        return self.trades
