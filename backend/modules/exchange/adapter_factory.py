"""Adapter Factory — Week 3 + Binance Demo Integration"""

import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient

from .base_adapter import BaseExchangeAdapter
from .paper_adapter import PaperExchangeAdapter
from .binance_demo_adapter import BinanceDemoAdapter

logger = logging.getLogger(__name__)


def get_exchange_adapter(
    mode: str,
    db_client: AsyncIOMotorClient,
    config: dict = None
) -> BaseExchangeAdapter:
    """Factory to get exchange adapter based on mode.
    
    Args:
        mode: PAPER, BINANCE_TESTNET, BYBIT_DEMO
        db_client: MongoDB client
        config: Additional configuration
    
    Returns:
        Exchange adapter instance
    """
    config = config or {}
    
    if mode == "PAPER":
        logger.info("[AdapterFactory] Creating PAPER adapter")
        return PaperExchangeAdapter(config, db_client)
    
    elif mode == "BINANCE_TESTNET":
        logger.info("[AdapterFactory] Creating BINANCE_TESTNET adapter")
        return BinanceDemoAdapter(config, db_client)
    
    elif mode == "BYBIT_DEMO":
        logger.info("[AdapterFactory] Creating BYBIT_DEMO adapter")
        # TODO: Implement BybitDemoAdapter
        raise NotImplementedError("BYBIT_DEMO adapter not yet implemented")
    
    else:
        raise ValueError(
            f"Unsupported EXECUTION_MODE: {mode}. "
            f"Supported modes: PAPER, BINANCE_TESTNET, BYBIT_DEMO"
        )

