"""Exchange Service — Week 3

Manages exchange connection lifecycle and provides unified API.
"""

import os
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient

from .adapter_factory import get_exchange_adapter
from .base_adapter import BaseExchangeAdapter

logger = logging.getLogger(__name__)


class ExchangeService:
    """Singleton service for exchange adapter management."""
    
    _instance: Optional['ExchangeService'] = None
    _adapter: Optional[BaseExchangeAdapter] = None
    _mode: Optional[str] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, db_client: AsyncIOMotorClient):
        """Initialize service with DB client."""
        self.db_client = db_client
        self._mode = os.getenv("EXECUTION_MODE", "PAPER")
        logger.info(f"[ExchangeService] Initialized with mode: {self._mode}")
    
    async def connect(self, mode: Optional[str] = None, config: dict = None) -> bool:
        """Connect to exchange.
        
        Args:
            mode: Override default execution mode
            config: Additional configuration
        
        Returns:
            True if connected successfully
        """
        if mode:
            self._mode = mode
        
        if not self._mode:
            raise ValueError("EXECUTION_MODE not set")
        
        # Create adapter
        self._adapter = get_exchange_adapter(self._mode, self.db_client, config or {})
        
        # Connect
        result = await self._adapter.connect()
        
        if result:
            logger.info(f"[ExchangeService] Connected to {self._mode}")
        else:
            logger.error(f"[ExchangeService] Failed to connect to {self._mode}")
        
        return result
    
    async def disconnect(self) -> bool:
        """Disconnect from exchange."""
        if self._adapter:
            result = await self._adapter.disconnect()
            self._adapter = None
            logger.info(f"[ExchangeService] Disconnected from {self._mode}")
            return result
        return True
    
    def get_adapter(self) -> BaseExchangeAdapter:
        """Get current adapter instance.
        
        Raises:
            ValueError: If not connected
        """
        if not self._adapter:
            raise ValueError("Exchange not connected. Call connect() first.")
        return self._adapter
    
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._adapter is not None and self._adapter.connected
    
    def get_mode(self) -> Optional[str]:
        """Get current execution mode."""
        return self._mode


# Global instance
exchange_service = ExchangeService()
