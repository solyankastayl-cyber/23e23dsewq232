"""
Exchange Service — Unified Facade

Manages exchange adapter lifecycle and provides unified interface.
Supports multiple adapters: Paper, Binance Testnet, Bybit Demo.
"""

import logging
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient

from .base import ExchangeAdapter
from .paper_adapter_v2 import PaperExchangeAdapter
from .binance_futures_adapter import BinanceFuturesAdapter

logger = logging.getLogger(__name__)


class ExchangeService:
    """
    Exchange service facade.
    
    Manages adapter lifecycle and provides unified interface to all workspaces.
    """
    
    def __init__(self, db_client: AsyncIOMotorClient):
        self.db_client = db_client
        self.adapter: Optional[ExchangeAdapter] = None
        self.current_mode: Optional[str] = None
    
    async def connect(self, mode: str, config: Dict[str, Any] = None) -> bool:
        """
        Connect to exchange.
        
        Args:
            mode: "PAPER", "BINANCE_TESTNET", "BYBIT_DEMO"
            config: adapter-specific config
        
        Returns:
            bool: True if connected successfully
        """
        if config is None:
            config = {}
        
        logger.info(f"[ExchangeService] Connecting to {mode}")
        
        # Disconnect existing adapter
        if self.adapter:
            await self.disconnect()
        
        # Create adapter
        if mode == "PAPER":
            self.adapter = PaperExchangeAdapter(config, self.db_client)
        
        elif mode == "BINANCE_TESTNET":
            api_key = config.get("api_key")
            api_secret = config.get("api_secret")
            if not api_key or not api_secret:
                raise ValueError("Binance Testnet requires api_key and api_secret")
            self.adapter = BinanceFuturesAdapter(config, self.db_client)
        
        elif mode == "BYBIT_DEMO":
            # TODO: implement
            raise NotImplementedError("Bybit Demo adapter not yet implemented")
            # api_key = config.get("api_key")
            # api_secret = config.get("api_secret")
            # if not api_key or not api_secret:
            #     raise ValueError("Bybit Demo requires api_key and api_secret")
            # self.adapter = BybitAdapter(api_key, api_secret, demo=True)
        
        else:
            raise ValueError(f"Unknown exchange mode: {mode}")
        
        # Connect
        success = await self.adapter.connect()
        
        if success:
            self.current_mode = mode
            logger.info(f"[ExchangeService] Connected to {mode}")
        else:
            logger.error(f"[ExchangeService] Failed to connect to {mode}")
            self.adapter = None
        
        return success
    
    async def disconnect(self) -> bool:
        """Disconnect from exchange."""
        if self.adapter:
            # Adapters don't need explicit disconnect for now
            self.adapter = None
            self.current_mode = None
            logger.info("[ExchangeService] Disconnected")
            return True
        return False
    
    def get_adapter(self) -> ExchangeAdapter:
        """
        Get current adapter.
        
        Raises:
            RuntimeError: if not connected
        """
        if not self.adapter:
            raise RuntimeError("No exchange adapter connected. Call connect() first.")
        return self.adapter
    
    def is_connected(self) -> bool:
        """Check if connected."""
        return self.adapter is not None
    
    def get_mode(self) -> Optional[str]:
        """Get current exchange mode."""
        return self.current_mode


# Singleton instance
_exchange_service: Optional[ExchangeService] = None


def init_exchange_service(db_client: AsyncIOMotorClient):
    """Initialize exchange service singleton."""
    global _exchange_service
    _exchange_service = ExchangeService(db_client)
    logger.info("[ExchangeService] Initialized")


def get_exchange_service() -> ExchangeService:
    """
    Get exchange service singleton.
    
    Raises:
        RuntimeError: if not initialized
    """
    if _exchange_service is None:
        raise RuntimeError("ExchangeService not initialized. Call init_exchange_service() first.")
    return _exchange_service
