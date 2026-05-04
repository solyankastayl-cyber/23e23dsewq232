"""Fee Engine

Нормализует комиссии в USDT.

Проблема: Binance даёт fee в разных валютах:
- USDT
- BNB
- base asset (BTC для BTCUSDT)

Нужно нормализовать всё к USDT для сравнения.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class FeeEngine:
    """Нормализация комиссий в USDT"""

    def normalize_fee(
        self,
        trade: Dict[str, Any],
        price_map: Dict[str, float] | None = None
    ) -> float:
        """
        Нормализовать комиссию в USDT.
        
        Args:
            trade: trade record из TradeLedger
            price_map: dict {symbol: price_usdt} для конвертации BNB/base asset
        
        Returns:
            fee_usdt (нормализованная комиссия в USDT)
        """
        fee = trade.get("fee", 0.0)
        fee_asset = trade.get("fee_asset")
        
        if fee == 0.0 or not fee_asset:
            return 0.0

        price_map = price_map or {}

        # Если комиссия уже в USDT
        if fee_asset == "USDT":
            return fee

        # Если комиссия в BNB
        if fee_asset == "BNB":
            bnb_price = price_map.get("BNBUSDT", 0.0)
            if bnb_price > 0:
                return fee * bnb_price
            else:
                logger.warning(f"BNBUSDT price not available in price_map, fee ignored")
                return 0.0

        # Если комиссия в base asset (например BTC для BTCUSDT)
        symbol = trade.get("symbol", "")
        if symbol.endswith("USDT"):
            base_asset = symbol[:-4]  # BTCUSDT -> BTC
            if fee_asset == base_asset:
                # Комиссия в BTC, конвертируем по цене сделки
                trade_price = trade.get("price", 0.0)
                if trade_price > 0:
                    return fee * trade_price

        # Неизвестный fee_asset
        logger.warning(f"Unknown fee_asset: {fee_asset}, fee ignored")
        return 0.0
