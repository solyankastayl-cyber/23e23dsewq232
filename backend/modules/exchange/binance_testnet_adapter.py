"""Binance Testnet Adapter — Production-Ready

Real exchange integration с правильным signing, idempotency, error handling.

Usage:
    adapter = BinanceTestnetAdapter(api_key, api_secret)
    await adapter.connect()
    result = await adapter.place_order(...)
"""

import time
import hmac
import hashlib
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)


class BinanceTestnetAdapter:
    """Binance Testnet Adapter для real exchange integration."""
    
    BASE_URL = "https://testnet.binance.vision"
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.connected = False
        self.session: Optional[aiohttp.ClientSession] = None
    
    def _sign(self, params: dict) -> dict:
        """Sign request with HMAC SHA256.
        
        Args:
            params: Request parameters
        
        Returns:
            Parameters with signature added
        """
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        params["signature"] = signature
        return params
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        signed: bool = False
    ) -> dict:
        """Make HTTP request to Binance API.
        
        Args:
            method: HTTP method (GET, POST)
            path: API endpoint path
            params: Request parameters
            signed: Whether request needs signature
        
        Returns:
            Response JSON
        
        Raises:
            Exception: If request fails
        """
        url = f"{self.BASE_URL}{path}"
        
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        if params is None:
            params = {}
        
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params = self._sign(params)
        
        session = await self._get_session()
        
        try:
            if method == "GET":
                async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    
                    if resp.status != 200:
                        logger.error(f"[BinanceTestnet] Request failed: {resp.status} {data}")
                        raise Exception(f"Binance API error: {resp.status} {data}")
                    
                    return data
            
            elif method == "POST":
                async with session.post(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    
                    if resp.status != 200:
                        logger.error(f"[BinanceTestnet] Request failed: {resp.status} {data}")
                        raise Exception(f"Binance API error: {resp.status} {data}")
                    
                    return data
            
            else:
                raise ValueError(f"Unsupported method: {method}")
        
        except aiohttp.ClientError as e:
            logger.error(f"[BinanceTestnet] Network error: {e}")
            raise
    
    async def connect(self) -> bool:
        """Connect to Binance Testnet and verify credentials.
        
        Returns:
            True if connected successfully
        """
        try:
            data = await self._request("GET", "/api/v3/account", signed=True)
            
            if "balances" in data:
                self.connected = True
                logger.info(f"[BinanceTestnet] Connected successfully")
                return True
            else:
                logger.error(f"[BinanceTestnet] Invalid account response: {data}")
                return False
        
        except Exception as e:
            logger.error(f"[BinanceTestnet] Connection failed: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Close session and disconnect."""
        if self.session and not self.session.closed:
            await self.session.close()
        self.connected = False
        logger.info("[BinanceTestnet] Disconnected")
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        client_order_id: str,
        order_type: str = "MARKET"
    ) -> dict:
        """Place order on Binance Testnet.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            side: Order side ("BUY" or "SELL")
            quantity: Order quantity
            client_order_id: Unique client order ID (idempotency key)
            order_type: Order type (default "MARKET")
        
        Returns:
            Order response from Binance
        
        Raises:
            Exception: If order fails
        """
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type,
            "quantity": str(quantity),
            "newClientOrderId": client_order_id,
        }
        
        logger.info(
            f"[BinanceTestnet] Placing order: {symbol} {side} {quantity} "
            f"(clientOrderId={client_order_id})"
        )
        
        try:
            result = await self._request(
                "POST",
                "/api/v3/order",
                params,
                signed=True
            )
            
            logger.info(
                f"[BinanceTestnet] Order placed: orderId={result.get('orderId')}, "
                f"status={result.get('status')}"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"[BinanceTestnet] Order failed: {e}")
            raise
    
    async def get_order(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        client_order_id: Optional[str] = None
    ) -> dict:
        """Get order status.
        
        Args:
            symbol: Trading pair
            order_id: Exchange order ID (optional)
            client_order_id: Client order ID (optional)
        
        Returns:
            Order details
        """
        params = {"symbol": symbol}
        
        if order_id:
            params["orderId"] = order_id
        elif client_order_id:
            params["origClientOrderId"] = client_order_id
        else:
            raise ValueError("Either order_id or client_order_id must be provided")
        
        return await self._request("GET", "/api/v3/order", params, signed=True)
    
    async def get_recent_fills(
        self,
        symbol: str,
        limit: int = 50
    ) -> List[dict]:
        """Get recent trade fills for symbol.
        
        Args:
            symbol: Trading pair
            limit: Max number of fills to return
        
        Returns:
            List of trade fills
        """
        params = {
            "symbol": symbol,
            "limit": limit,
        }
        
        return await self._request(
            "GET",
            "/api/v3/myTrades",
            params,
            signed=True
        )
    
    async def get_account_info(self) -> dict:
        """Get account information including balances.
        
        Returns:
            Account info dict
        """
        return await self._request("GET", "/api/v3/account", signed=True)
