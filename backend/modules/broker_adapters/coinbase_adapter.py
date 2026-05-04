"""
Coinbase Broker Adapter
========================

Adapter for Coinbase Exchange API.
Supports spot trading via public and authenticated endpoints.

Usage:
    from modules.broker_adapters.coinbase_adapter import CoinbaseAdapter
    from modules.broker_adapters.base_adapter import BrokerCredentials
    
    creds = BrokerCredentials(api_key="...", api_secret="...", passphrase="...")
    adapter = CoinbaseAdapter(creds)
    await adapter.connect()
"""

import asyncio
import hashlib
import hmac
import time
import base64
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

try:
    import httpx
    HTTPX_OK = True
except ImportError:
    HTTPX_OK = False

from .base_adapter import (
    BaseBrokerAdapter, BrokerCredentials, BrokerStatus,
    Balance, Position, Order, Ticker,
    OrderSide, OrderType, OrderStatus, TimeInForce,
    BrokerError, AuthenticationError, OrderError
)


class CoinbaseAdapter(BaseBrokerAdapter):
    """
    Coinbase Exchange (Pro) Adapter.
    
    Supports:
    - Spot trading
    - Market and Limit orders
    - Account balances
    - Market data (tickers, candles)
    
    Requires:
    - API Key
    - API Secret
    - Passphrase (Coinbase-specific)
    """
    
    BASE_URL = "https://api.exchange.coinbase.com"
    SANDBOX_URL = "https://api-public.sandbox.exchange.coinbase.com"
    
    def __init__(self, credentials: BrokerCredentials):
        super().__init__(credentials)
        self._client: Optional[httpx.AsyncClient] = None
        self._base_url = self.SANDBOX_URL if credentials.testnet else self.BASE_URL
    
    @property
    def broker_name(self) -> str:
        return "coinbase"
    
    @property
    def supports_futures(self) -> bool:
        return False
    
    @property
    def supports_margin(self) -> bool:
        return False
    
    # ===========================================
    # Authentication
    # ===========================================
    
    def _get_auth_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """Generate authentication headers for Coinbase API."""
        timestamp = str(int(time.time()))
        message = timestamp + method.upper() + path + body
        
        # Decode base64 secret
        try:
            secret = base64.b64decode(self.credentials.api_secret)
        except Exception:
            secret = self.credentials.api_secret.encode()
        
        signature = hmac.new(
            secret,
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        signature_b64 = base64.b64encode(signature).decode()
        
        headers = {
            "CB-ACCESS-KEY": self.credentials.api_key,
            "CB-ACCESS-SIGN": signature_b64,
            "CB-ACCESS-TIMESTAMP": timestamp,
            "CB-ACCESS-PASSPHRASE": self.credentials.passphrase or "",
            "Content-Type": "application/json",
        }
        
        return headers
    
    async def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict] = None,
        auth: bool = True
    ) -> Dict[str, Any]:
        """Make authenticated request to Coinbase API."""
        if not HTTPX_OK:
            raise BrokerError("httpx not installed")
        
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        
        url = f"{self._base_url}{path}"
        body_str = ""
        
        if body:
            import json
            body_str = json.dumps(body)
        
        headers = {}
        if auth:
            headers = self._get_auth_headers(method, path, body_str)
        else:
            headers = {"Content-Type": "application/json"}
        
        self._increment_request_count()
        
        try:
            if method.upper() == "GET":
                response = await self._client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await self._client.post(url, headers=headers, content=body_str)
            elif method.upper() == "DELETE":
                response = await self._client.delete(url, headers=headers)
            else:
                raise BrokerError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json() if response.text else {}
            
        except httpx.HTTPStatusError as e:
            error_msg = str(e)
            try:
                error_data = e.response.json()
                error_msg = error_data.get("message", str(e))
            except Exception:
                pass
            raise BrokerError(f"HTTP {e.response.status_code}: {error_msg}")
        except Exception as e:
            raise BrokerError(str(e))
    
    # ===========================================
    # Connection
    # ===========================================
    
    async def connect(self) -> bool:
        """Connect and verify credentials."""
        try:
            self.status = BrokerStatus.CONNECTING
            
            # Test connection with accounts endpoint
            await self._request("GET", "/accounts")
            
            self.status = BrokerStatus.CONNECTED
            self.connected_at = datetime.now(timezone.utc)
            self.last_error = None
            return True
            
        except Exception as e:
            self.status = BrokerStatus.ERROR
            self.last_error = str(e)
            raise AuthenticationError(f"Failed to connect: {e}")
    
    async def disconnect(self) -> bool:
        """Close connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.status = BrokerStatus.DISCONNECTED
        return True
    
    async def is_connected(self) -> bool:
        """Check connection status."""
        return self.status == BrokerStatus.CONNECTED
    
    # ===========================================
    # Account
    # ===========================================
    
    async def get_balance(self, asset: Optional[str] = None) -> List[Balance]:
        """Get account balances."""
        data = await self._request("GET", "/accounts")
        
        balances = []
        for acc in data:
            currency = acc.get("currency", "")
            if asset and currency.upper() != asset.upper():
                continue
            
            available = float(acc.get("available", 0))
            hold = float(acc.get("hold", 0))
            
            balances.append(Balance(
                asset=currency,
                free=available,
                locked=hold,
                total=available + hold
            ))
        
        return balances
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """
        Get open positions.
        
        Note: Coinbase spot doesn't have traditional positions.
        Returns balances as pseudo-positions for non-quote currencies.
        """
        balances = await self.get_balance()
        
        positions = []
        for bal in balances:
            if bal.total <= 0:
                continue
            if bal.asset in ["USD", "USDT", "USDC", "EUR"]:
                continue
            if symbol and bal.asset.upper() not in symbol.upper():
                continue
            
            # Get current price
            product_id = f"{bal.asset}-USD"
            try:
                ticker = await self.get_ticker(product_id)
                current_price = ticker.last
            except Exception:
                current_price = 0.0
            
            positions.append(Position(
                symbol=product_id,
                side="LONG",
                size=bal.total,
                entry_price=current_price,  # Unknown for spot
                current_price=current_price,
                unrealized_pnl=0.0
            ))
        
        return positions
    
    # ===========================================
    # Market Data
    # ===========================================
    
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get current ticker for product."""
        product_id = self._normalize_symbol(symbol)
        
        data = await self._request("GET", f"/products/{product_id}/ticker", auth=False)
        
        return Ticker(
            symbol=product_id,
            bid=float(data.get("bid", 0)),
            ask=float(data.get("ask", 0)),
            last=float(data.get("price", 0)),
            volume_24h=float(data.get("volume", 0))
        )
    
    async def get_tickers(self, symbols: Optional[List[str]] = None) -> List[Ticker]:
        """Get tickers for multiple products."""
        # Get all products if no symbols specified
        if not symbols:
            products = await self._request("GET", "/products", auth=False)
            symbols = [p["id"] for p in products if p.get("status") == "online"]
        
        tickers = []
        for sym in symbols[:20]:  # Limit to avoid rate limiting
            try:
                ticker = await self.get_ticker(sym)
                tickers.append(ticker)
                await asyncio.sleep(0.1)  # Rate limit
            except Exception:
                continue
        
        return tickers
    
    async def get_candles(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 300,
        start_time: int = None,
        end_time: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get OHLCV candles with pagination support for full history.
        
        Timeframes: 1m, 5m, 15m, 1h, 6h, 1d
        
        For large requests (limit > 300), automatically paginates
        to fetch all historical data.
        """
        product_id = self._normalize_symbol(symbol)
        
        granularity_map = {
            "1m": 60, "5m": 300, "15m": 900,
            "1h": 3600, "6h": 21600, "1d": 86400
        }
        granularity = granularity_map.get(timeframe, 86400)
        
        all_candles = []
        max_per_request = 300  # Coinbase limit
        
        # If limit <= 300, single request
        if limit <= max_per_request:
            url = f"/products/{product_id}/candles?granularity={granularity}"
            if start_time:
                url += f"&start={start_time}"
            if end_time:
                url += f"&end={end_time}"
            
            data = await self._request("GET", url, auth=False)
            
            for row in data[:limit]:
                if len(row) >= 6:
                    all_candles.append({
                        "timestamp": row[0] * 1000,
                        "open": float(row[3]),
                        "high": float(row[2]),
                        "low": float(row[1]),
                        "close": float(row[4]),
                        "volume": float(row[5]),
                        "timeframe": timeframe,
                        "source": "coinbase"
                    })
        else:
            # Pagination: fetch in chunks going backwards in time
            import time
            current_end = end_time or int(time.time())
            remaining = limit
            
            while remaining > 0:
                chunk_size = min(remaining, max_per_request)
                
                # Calculate start time for this chunk
                chunk_start = current_end - (chunk_size * granularity)
                
                url = f"/products/{product_id}/candles?granularity={granularity}&start={chunk_start}&end={current_end}"
                
                try:
                    data = await self._request("GET", url, auth=False)
                    
                    if not data:
                        break
                    
                    chunk_candles = []
                    for row in data:
                        if len(row) >= 6:
                            chunk_candles.append({
                                "timestamp": row[0] * 1000,
                                "open": float(row[3]),
                                "high": float(row[2]),
                                "low": float(row[1]),
                                "close": float(row[4]),
                                "volume": float(row[5]),
                                "timeframe": timeframe,
                                "source": "coinbase"
                            })
                    
                    all_candles.extend(chunk_candles)
                    remaining -= len(chunk_candles)
                    
                    # Move end time back for next chunk
                    if chunk_candles:
                        oldest_ts = min(c["timestamp"] for c in chunk_candles) // 1000
                        current_end = oldest_ts - 1
                    else:
                        break
                    
                    # Rate limiting
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    print(f"[Coinbase] Pagination error: {e}")
                    break
        
        # Sort by timestamp ascending
        all_candles.sort(key=lambda x: x["timestamp"])
        return all_candles
    
    # ===========================================
    # Orders
    # ===========================================
    
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.GTC,
        client_order_id: Optional[str] = None
    ) -> Order:
        """Place a new order."""
        product_id = self._normalize_symbol(symbol)
        
        # Build order request
        body: Dict[str, Any] = {
            "product_id": product_id,
            "side": side.value.lower(),
            "size": str(quantity)
        }
        
        if client_order_id:
            body["client_oid"] = client_order_id
        
        if order_type == OrderType.MARKET:
            body["type"] = "market"
        elif order_type == OrderType.LIMIT:
            body["type"] = "limit"
            body["price"] = str(price)
            body["time_in_force"] = time_in_force.value
        elif order_type in [OrderType.STOP_LOSS, OrderType.STOP_LIMIT]:
            body["type"] = "stop"
            body["stop_price"] = str(stop_price)
            if price:
                body["price"] = str(price)
        else:
            raise OrderError(f"Unsupported order type: {order_type}")
        
        data = await self._request("POST", "/orders", body)
        
        return self._parse_order(data)
    
    async def cancel_order(
        self,
        symbol: str,
        order_id: Optional[str] = None,
        client_order_id: Optional[str] = None
    ) -> Order:
        """Cancel an existing order."""
        if order_id:
            path = f"/orders/{order_id}"
        elif client_order_id:
            path = f"/orders/client:{client_order_id}"
        else:
            raise OrderError("Either order_id or client_order_id required")
        
        # Get order details first
        order = await self.get_order(symbol, order_id, client_order_id)
        
        # Cancel
        await self._request("DELETE", path)
        
        order.status = OrderStatus.CANCELED
        return order
    
    async def get_order(
        self,
        symbol: str,
        order_id: Optional[str] = None,
        client_order_id: Optional[str] = None
    ) -> Order:
        """Get order details."""
        if order_id:
            path = f"/orders/{order_id}"
        elif client_order_id:
            path = f"/orders/client:{client_order_id}"
        else:
            raise OrderError("Either order_id or client_order_id required")
        
        data = await self._request("GET", path)
        return self._parse_order(data)
    
    async def get_orders(
        self,
        symbol: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        limit: int = 100
    ) -> List[Order]:
        """Get list of orders."""
        params = []
        if symbol:
            product_id = self._normalize_symbol(symbol)
            params.append(f"product_id={product_id}")
        
        # Coinbase status filter
        if status:
            if status in [OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED]:
                params.append("status=open")
            elif status == OrderStatus.FILLED:
                params.append("status=done")
            elif status == OrderStatus.CANCELED:
                params.append("status=done")
        
        path = "/orders"
        if params:
            path += "?" + "&".join(params)
        
        data = await self._request("GET", path)
        
        orders = []
        for item in data[:limit]:
            orders.append(self._parse_order(item))
        
        return orders
    
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Cancel all open orders."""
        params = ""
        if symbol:
            product_id = self._normalize_symbol(symbol)
            params = f"?product_id={product_id}"
        
        # Get open orders first
        open_orders = await self.get_orders(symbol, OrderStatus.NEW)
        
        # Cancel all
        await self._request("DELETE", f"/orders{params}")
        
        # Update status
        for order in open_orders:
            order.status = OrderStatus.CANCELED
        
        return open_orders
    
    # ===========================================
    # Helpers
    # ===========================================
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Convert symbol to Coinbase format (BTC-USD)."""
        symbol = symbol.upper()
        
        # Already in correct format
        if "-" in symbol:
            return symbol
        
        # Convert BTCUSDT -> BTC-USD
        for quote in ["USDT", "USD", "USDC", "EUR"]:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return f"{base}-{quote}"
        
        # Default to USD
        return f"{symbol}-USD"
    
    def _parse_order(self, data: Dict[str, Any]) -> Order:
        """Parse Coinbase order response to Order object."""
        status_map = {
            "pending": OrderStatus.PENDING,
            "open": OrderStatus.NEW,
            "active": OrderStatus.PARTIALLY_FILLED,
            "done": OrderStatus.FILLED,
            "rejected": OrderStatus.REJECTED,
        }
        
        coinbase_status = data.get("status", "pending")
        if data.get("done_reason") == "canceled":
            status = OrderStatus.CANCELED
        else:
            status = status_map.get(coinbase_status, OrderStatus.PENDING)
        
        order_type_map = {
            "market": OrderType.MARKET,
            "limit": OrderType.LIMIT,
            "stop": OrderType.STOP_LOSS,
        }
        
        return Order(
            broker_order_id=data.get("id"),
            symbol=data.get("product_id", ""),
            side=OrderSide.BUY if data.get("side") == "buy" else OrderSide.SELL,
            order_type=order_type_map.get(data.get("type"), OrderType.MARKET),
            quantity=float(data.get("size", 0)),
            price=float(data.get("price")) if data.get("price") else None,
            stop_price=float(data.get("stop_price")) if data.get("stop_price") else None,
            time_in_force=TimeInForce.GTC,
            status=status,
            filled_quantity=float(data.get("filled_size", 0)),
            avg_fill_price=float(data.get("executed_value", 0)) / float(data.get("filled_size", 1)) if float(data.get("filled_size", 0)) > 0 else 0,
            commission=float(data.get("fill_fees", 0)),
        )
