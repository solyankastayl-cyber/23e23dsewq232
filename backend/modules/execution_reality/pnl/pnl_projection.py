"""PnL Projection

Event-driven проекция PnL.
Работает как order/position projections.
"""

import logging
from typing import Dict, Any, Optional
from .trade_ledger import TradeLedger
from .pnl_engine import PnLEngine
from .fee_engine import FeeEngine
from .slippage_engine import SlippageEngine
from ..events.execution_event_types import ExecutionEvent

logger = logging.getLogger(__name__)


class PnLProjection:
    """Проекция PnL (из событий)"""

    def __init__(self):
        self.ledger = TradeLedger()
        self.pnl_engine = PnLEngine()
        self.fee_engine = FeeEngine()
        self.slippage_engine = SlippageEngine()

    def apply(self, event: ExecutionEvent) -> None:
        """Применить событие к projection"""
        self.ledger.apply(event)

    def get_symbol_pnl(
        self,
        symbol: str,
        current_price: float,
        price_map: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Получить PnL для символа.
        
        Args:
            symbol: BTCUSDT
            current_price: текущая цена для unrealized pnl
            price_map: {symbol: price_usdt} для fee normalization
        
        Returns:
            {
                "symbol": str,
                "position_qty": float,
                "avg_entry": float,
                "realized_pnl": float,
                "unrealized_pnl": float,
                "total_pnl": float,
                "fees_usdt": float,
                "net_pnl": float
            }
        """
        trades = self.ledger.get_trades_for_symbol(symbol)

        if not trades:
            return {
                "symbol": symbol,
                "position_qty": 0.0,
                "avg_entry": 0.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "total_pnl": 0.0,
                "fees_usdt": 0.0,
                "net_pnl": 0.0
            }

        # Gross PnL
        pnl = self.pnl_engine.compute_position_pnl(trades, current_price)

        # Fees
        fees_usdt = sum(self.fee_engine.normalize_fee(t, price_map) for t in trades)

        # Net PnL = gross - fees
        net_pnl = pnl["total_pnl"] - fees_usdt

        return {
            "symbol": symbol,
            "position_qty": pnl["position_qty"],
            "avg_entry": pnl["avg_entry"],
            "realized_pnl": pnl["realized_pnl"],
            "unrealized_pnl": pnl["unrealized_pnl"],
            "total_pnl": pnl["total_pnl"],
            "fees_usdt": fees_usdt,
            "net_pnl": net_pnl
        }

    def get_all_symbols_pnl(
        self,
        price_map: Dict[str, float]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Получить PnL для всех символов.
        
        Args:
            price_map: {symbol: current_price}
        
        Returns:
            {symbol: pnl_dict}
        """
        symbols = set(t["symbol"] for t in self.ledger.get_all_trades())
        return {
            symbol: self.get_symbol_pnl(symbol, price_map.get(symbol, 0.0), price_map)
            for symbol in symbols
        }
