"""Exchange Service — Unified interface для PAPER/TESTNET/REAL modes

Единая точка входа для всех exchange operations:
- Mode switching (PAPER ↔ TESTNET)
- Adapter factory
- Safe limits enforcement
- User binding

Usage:
    service = ExchangeService(user_id, db)
    await service.set_mode("TESTNET", api_key, api_secret)
    result = await service.place_order(...)  # Adapter auto-selected
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from modules.exchange.paper_adapter import PaperExchangeAdapter
from modules.exchange.binance_testnet_adapter import BinanceTestnetAdapter
from .encryption_helper import encrypt_api_key, decrypt_api_key

logger = logging.getLogger(__name__)


# Safe limits (TESTNET protection)
SAFE_LIMITS = {
    "MAX_NOTIONAL_PER_ORDER": 100.0,  # USDT
    "MAX_OPEN_POSITIONS": 3,
    "ALLOWED_SYMBOLS": ["BTCUSDT", "ETHUSDT"],
    "ALLOWED_ORDER_TYPES": ["MARKET"],
}


class ExchangeService:
    """Unified exchange service with mode switching.
    
    Handles:
    - Mode: PAPER, TESTNET (future: MAINNET)
    - Adapter selection
    - API key management
    - Safe limits enforcement
    """
    
    def __init__(self, user_id: str, db, db_client):
        """Initialize exchange service.
        
        Args:
            user_id: User identifier
            db: MongoDB database handle
            db_client: MongoDB client (for adapters)
        """
        self.user_id = user_id
        self.db = db
        self.db_client = db_client
        
        self.mode: Optional[str] = None
        self.adapter = None
        self.connected = False
    
    async def initialize(self):
        """Initialize service from stored connection."""
        # Load user's exchange connection
        connection = await self.db.exchange_connections.find_one({
            "user_id": self.user_id,
            "is_active": True
        })
        
        if connection:
            mode = connection.get("mode", "PAPER")
            
            if mode == "TESTNET":
                # Decrypt keys
                api_key = decrypt_api_key(connection["api_key"])
                api_secret = decrypt_api_key(connection["api_secret"])
                
                await self.set_mode("TESTNET", api_key, api_secret)
            else:
                await self.set_mode("PAPER")
            
            logger.info(f"[ExchangeService] Initialized for user {self.user_id} in {mode} mode")
        else:
            # Default to PAPER
            await self.set_mode("PAPER")
            logger.info(f"[ExchangeService] Initialized for user {self.user_id} in PAPER mode (default)")
    
    async def set_mode(
        self,
        mode: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None
    ):
        """Set exchange mode and create adapter.
        
        Args:
            mode: "PAPER" or "TESTNET"
            api_key: Binance API key (for TESTNET)
            api_secret: Binance API secret (for TESTNET)
        """
        self.mode = mode
        
        # Disconnect old adapter
        if self.adapter:
            try:
                if hasattr(self.adapter, 'disconnect'):
                    await self.adapter.disconnect()
            except Exception as e:
                logger.warning(f"[ExchangeService] Error disconnecting old adapter: {e}")
        
        # Create new adapter
        if mode == "PAPER":
            config = {
                "account_id": f"paper_{self.user_id}",
                "initial_balance": 10000.0,
            }
            self.adapter = PaperExchangeAdapter(config, self.db_client)
            await self.adapter.connect()
            self.connected = True
            
            logger.info(f"[ExchangeService] Switched to PAPER mode")
        
        elif mode == "TESTNET":
            if not api_key or not api_secret:
                raise ValueError("API keys required for TESTNET mode")
            
            self.adapter = BinanceTestnetAdapter(api_key, api_secret)
            self.connected = await self.adapter.connect()
            
            if self.connected:
                logger.info(f"[ExchangeService] Switched to TESTNET mode")
            else:
                logger.error(f"[ExchangeService] TESTNET connection failed")
                raise Exception("Failed to connect to Binance Testnet")
        
        else:
            raise ValueError(f"Unsupported mode: {mode}")
        
        # Save connection to DB
        await self._save_connection(mode, api_key, api_secret)
    
    async def _save_connection(
        self,
        mode: str,
        api_key: Optional[str],
        api_secret: Optional[str]
    ):
        """Save exchange connection to database.
        
        Args:
            mode: Exchange mode
            api_key: API key (encrypted before saving)
            api_secret: API secret (encrypted before saving)
        """
        # Deactivate old connections
        await self.db.exchange_connections.update_many(
            {"user_id": self.user_id},
            {"$set": {"is_active": False}}
        )
        
        # Create new connection
        connection = {
            "user_id": self.user_id,
            "exchange": "BINANCE" if mode == "TESTNET" else "PAPER",
            "mode": mode,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        if mode == "TESTNET":
            # Encrypt keys before saving
            connection["api_key"] = encrypt_api_key(api_key)
            connection["api_secret"] = encrypt_api_key(api_secret)
        
        await self.db.exchange_connections.insert_one(connection)
    
    async def get_status(self) -> Dict[str, Any]:
        """Get exchange connection status.
        
        Returns:
            Status dict with mode, connected, balance, etc.
        """
        status = {
            "mode": self.mode or "PAPER",
            "connected": self.connected,
            "exchange": "BINANCE" if self.mode == "TESTNET" else "PAPER",
        }
        
        if self.connected and self.adapter:
            try:
                if self.mode == "PAPER":
                    account = await self.adapter.get_account_info()
                    status["balance"] = account.balance
                
                elif self.mode == "TESTNET":
                    account = await self.adapter.get_account_info()
                    balances = account.get("balances", [])
                    
                    # Get USDT balance
                    usdt_balance = next(
                        (float(b.get("free", 0)) for b in balances if b.get("asset") == "USDT"),
                        0.0
                    )
                    status["balance"] = usdt_balance
                    status["last_sync"] = datetime.now(timezone.utc).isoformat()
            
            except Exception as e:
                logger.error(f"[ExchangeService] Error getting status: {e}")
                status["error"] = str(e)
        
        return status
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        client_order_id: str
    ) -> dict:
        """Place order через активный adapter.
        
        Validates against safe limits before submission.
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Order quantity
            client_order_id: Unique client order ID
        
        Returns:
            Order response
        
        Raises:
            Exception: If validation fails or order rejected
        """
        if not self.connected or not self.adapter:
            raise Exception("Exchange not connected")
        
        # Get current price estimate
        from modules.market_data.price_service import get_price_service
        price_service = await get_price_service()
        
        try:
            mark_price = await price_service.get_mark_price(symbol)
        except Exception as e:
            raise Exception(f"Failed to get price for {symbol}: {e}")
        
        notional = quantity * mark_price
        
        # Safe limits validation
        if symbol not in SAFE_LIMITS["ALLOWED_SYMBOLS"]:
            raise Exception(f"Symbol {symbol} not in allowed list: {SAFE_LIMITS['ALLOWED_SYMBOLS']}")
        
        if notional > SAFE_LIMITS["MAX_NOTIONAL_PER_ORDER"]:
            raise Exception(
                f"Notional ${notional:.2f} exceeds max ${SAFE_LIMITS['MAX_NOTIONAL_PER_ORDER']}"
            )
        
        # Place order
        if self.mode == "PAPER":
            from modules.exchange.models import OrderRequest
            
            order_request = OrderRequest(
                symbol=symbol,
                side=side,
                order_type="MARKET",
                quantity=quantity,
                client_order_id=client_order_id,
            )
            
            result = await self.adapter.place_order(order_request)
            return result.raw if result.raw else {}
        
        elif self.mode == "TESTNET":
            result = await self.adapter.place_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                client_order_id=client_order_id
            )
            return result
        
        else:
            raise Exception(f"Unsupported mode: {self.mode}")


# Global instance (initialized per user)
_exchange_services: Dict[str, ExchangeService] = {}


async def get_exchange_service(user_id: str, db, db_client) -> ExchangeService:
    """Get or create exchange service for user.
    
    Args:
        user_id: User identifier
        db: MongoDB database
        db_client: MongoDB client
    
    Returns:
        ExchangeService instance
    """
    if user_id not in _exchange_services:
        service = ExchangeService(user_id, db, db_client)
        await service.initialize()
        _exchange_services[user_id] = service
    
    return _exchange_services[user_id]
