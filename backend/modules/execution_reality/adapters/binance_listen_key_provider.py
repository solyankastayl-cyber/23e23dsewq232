"""Binance Listen Key Provider

Управляет listenKey для Binance User Data Stream.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BinanceListenKeyProvider:
    """Получение и поддержание listenKey для user stream"""

    def __init__(self, rest_adapter):
        """
        Args:
            rest_adapter: Binance REST adapter с методами create_listen_key, keepalive_listen_key
        """
        self.rest_adapter = rest_adapter
        self._current_key: Optional[str] = None

    async def get_listen_key(self) -> str:
        """Получить listenKey (создать новый или вернуть кешированный)"""
        if not self._current_key:
            self._current_key = await self.rest_adapter.create_listen_key()
            logger.info(f"Created new listenKey: {self._current_key[:8]}...")
        return self._current_key

    async def keepalive(self, listen_key: str) -> bool:
        """
        Продлить listenKey (должен вызываться каждые 30-60 мин).
        
        Returns:
            True если успешно, False если нужно пересоздать
        """
        try:
            success = await self.rest_adapter.keepalive_listen_key(listen_key)
            if success:
                logger.debug(f"Keepalive successful for listenKey: {listen_key[:8]}...")
                return True
            else:
                logger.warning(f"Keepalive failed, will recreate listenKey")
                self._current_key = None
                return False
        except Exception as e:
            logger.error(f"Keepalive error: {e}")
            self._current_key = None
            return False

    def invalidate(self):
        """Инвалидировать текущий listenKey (форсировать пересоздание)"""
        self._current_key = None
        logger.info("ListenKey invalidated")
