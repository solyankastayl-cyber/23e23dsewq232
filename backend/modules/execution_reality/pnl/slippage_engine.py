"""Slippage Engine

Сравнивает intent_price (requested) vs fill_price (actual).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SlippageEngine:
    """Расчёт slippage"""

    def compute(
        self,
        intent_price: Optional[float],
        fill_price: float,
        side: str
    ) -> float:
        """
        Рассчитать slippage (в долях, не bps).
        
        Args:
            intent_price: цена запроса (limit price из intent)
            fill_price: фактическая цена исполнения
            side: "BUY" | "SELL"
        
        Returns:
            slippage (положительное = ухудшение, отрицательное = улучшение)
        """
        if intent_price is None or intent_price == 0.0:
            # Нет intent_price (например, market order или legacy data)
            return 0.0

        if side == "BUY":
            # BUY: если fill_price > intent_price → slippage положительный (хуже)
            slippage = (fill_price - intent_price) / intent_price
        else:  # SELL
            # SELL: если fill_price < intent_price → slippage положительный (хуже)
            slippage = (intent_price - fill_price) / intent_price

        return slippage

    def slippage_bps(self, slippage: float) -> float:
        """Конвертировать slippage в basis points"""
        return slippage * 10000
