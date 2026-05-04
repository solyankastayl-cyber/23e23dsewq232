"""PnL Engine

Основной движок PnL.
Рассчитывает:
- realized pnl
- unrealized pnl
- avg entry
- total pnl
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class PnLEngine:
    """Расчёт PnL по списку сделок"""

    def compute_position_pnl(
        self,
        trades: List[Dict[str, Any]],
        current_price: float
    ) -> Dict[str, Any]:
        """
        Рассчитать PnL для символа по списку сделок.
        
        Логика (FIFO accounting):
        - BUY: увеличиваем position, обновляем avg cost
        - SELL: закрываем position, realized pnl = (sell_price - avg) * qty
        
        Args:
            trades: список trade records (из TradeLedger)
            current_price: текущая цена для unrealized pnl
        
        Returns:
            {
                "position_qty": float,
                "avg_entry": float,
                "realized_pnl": float,
                "unrealized_pnl": float,
                "total_pnl": float
            }
        """
        position = 0.0
        cost = 0.0
        realized = 0.0

        for t in trades:
            qty = t["qty"]
            price = t["price"]
            side = t["side"]

            if side == "BUY":
                # Увеличиваем позицию
                new_cost = cost + qty * price
                new_qty = position + qty

                cost = new_cost
                position = new_qty

            else:  # SELL
                if position == 0:
                    # Нет позиции для закрытия (не должно случаться, но защита)
                    logger.warning(f"SELL without position: {t}")
                    continue

                avg = cost / position
                # Realized PnL = (sell_price - avg) * qty
                realized += qty * (price - avg)

                # Уменьшаем позицию
                position -= qty
                cost -= avg * qty

        # Unrealized PnL
        unrealized = 0.0
        avg_entry = 0.0
        if position > 0:
            avg_entry = cost / position
            unrealized = position * (current_price - avg_entry)

        return {
            "position_qty": position,
            "avg_entry": avg_entry,
            "realized_pnl": realized,
            "unrealized_pnl": unrealized,
            "total_pnl": realized + unrealized
        }
