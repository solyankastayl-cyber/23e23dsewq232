"""Snapshot Poller

Периодически получает снимки состояния с Binance (REST).
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class SnapshotPoller:
    """Поллер для получения snapshots с Binance"""

    def __init__(self, rest_adapter):
        """
        Args:
            rest_adapter: Binance REST adapter с методами get_open_orders, get_positions, get_account
        """
        self.adapter = rest_adapter

    async def fetch(self) -> Dict[str, Any]:
        """
        Получить полный snapshot состояния.
        
        Returns:
            {
                "orders": [...],
                "positions": [...],
                "balances": [...]
            }
        """
        try:
            # Получаем открытые ордера
            orders = await self.adapter.get_open_orders()
            
            # Получаем позиции (для futures) или балансы (для spot)
            positions = await self.adapter.get_positions()
            
            # Получаем снимок аккаунта
            account = await self.adapter.get_account_snapshot()
            
            balances = account.get("balances", [])
            
            logger.debug(f"Snapshot fetched: {len(orders)} orders, {len(positions)} positions, {len(balances)} balances")
            
            return {
                "orders": orders,
                "positions": positions,
                "balances": balances
            }
        except Exception as e:
            logger.error(f"Failed to fetch snapshot: {e}")
            return {
                "orders": [],
                "positions": [],
                "balances": []
            }
