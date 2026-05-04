"""
OKX Adapter - PHASE 5.1
=======================

OKX exchange adapter implementation.
Supports both mainnet and testnet (demo trading).
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib
import hmac
import base64
import time
import uuid
import httpx

from .base_exchange_adapter import BaseExchangeAdapter
from .exchange_types import (
    ExchangeId,
    ExchangeOrderRequest,
    ExchangeOrderResponse,
    ExchangePosition,
    ExchangeBalance,
    ExchangeTicker,
    ExchangeOrderbook,
    OrderbookLevel,
    OrderSide,
    OrderType,
    OrderStatus,
    PositionSide,
    MarginMode,
    TimeInForce,
    StreamType
)


class OKXAdapter(BaseExchangeAdapter):
    """
    OKX adapter.
    
    REST API endpoints:
    - Mainnet: https://www.okx.com
    - Demo: https://www.okx.com (with x-simulated-trading header)
    
    WebSocket endpoints:
    - Mainnet: wss://ws.okx.com:8443/ws/v5
    - Demo: wss://wspap.okx.com:8443/ws/v5
    """
    
    # API endpoints
    REST_URL = "https://www.okx.com"
    MAINNET_WS = "wss://ws.okx.com:8443/ws/v5/public"
    DEMO_WS = "wss://wspap.okx.com:8443/ws/v5/public"
    
    # Order type mapping
    ORDER_TYPE_MAP = {
        OrderType.MARKET: "market",
        OrderType.LIMIT: "limit",
        OrderType.STOP_MARKET: "trigger",
        OrderType.STOP_LIMIT: "trigger"
    }
    
    # Time in force mapping
    TIF_MAP = {
        TimeInForce.GTC: "GTC",
        TimeInForce.IOC: "IOC",
        TimeInForce.FOK: "FOK",
        TimeInForce.GTX: "post_only"
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        testnet: bool = False
    ):
        super().__init__(
            exchange_id=ExchangeId.OKX,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            testnet=testnet
        )
        
        self.base_url = self.REST_URL
        self.ws_url = self.DEMO_WS if testnet else self.MAINNET_WS
        self._client: Optional[httpx.AsyncClient] = None
    
    # ============================================
    # Connection Management
    # ============================================
    
    async def connect(self) -> bool:
        """Connect to OKX"""
        try:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0
            )
            
            # Test connection with server time
            response = await self._client.get("/api/v5/public/time")
            if response.status_code == 200:
                self._connected = True
                self._connected_at = datetime.utcnow()
                
                # If we have credentials, verify them
                if self.api_key and self.api_secret and self.passphrase:
                    try:
                        await self.get_balance()
                        self._authenticated = True
                    except Exception as e:
                        self._record_error(f"Authentication failed: {e}")
                        self._authenticated = False
                
                self._clear_error()
                return True
            else:
                self._record_error(f"Connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            self._record_error(str(e))
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from OKX"""
        try:
            if self._client:
                await self._client.aclose()
                self._client = None
            
            self._connected = False
            self._authenticated = False
            return True
            
        except Exception as e:
            self._record_error(str(e))
            return False
    
    # ============================================
    # Account Operations
    # ============================================
    
    async def get_balance(self, asset: Optional[str] = None) -> List[ExchangeBalance]:
        """Get account balances"""
        endpoint = "/api/v5/account/balance"
        params = {}
        if asset:
            params["ccy"] = asset
        
        response = await self._signed_request("GET", endpoint, params)
        
        balances = []
        if response.get("data"):
            for account in response["data"]:
                for detail in account.get("details", []):
                    balance = ExchangeBalance(
                        exchange=ExchangeId.OKX,
                        asset=detail["ccy"],
                        free=float(detail.get("availBal", 0)),
                        locked=float(detail.get("frozenBal", 0)),
                        total=float(detail.get("cashBal", 0)),
                        usd_value=float(detail.get("eqUsd", 0)) if detail.get("eqUsd") else None,
                        updated_at=datetime.utcnow()
                    )
                    balances.append(balance)
        
        return balances
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[ExchangePosition]:
        """Get open positions"""
        endpoint = "/api/v5/account/positions"
        params = {"instType": "SWAP"}
        if symbol:
            params["instId"] = self._normalize_symbol(symbol)
        
        response = await self._signed_request("GET", endpoint, params)
        
        positions = []
        if response.get("data"):
            for item in response["data"]:
                size = float(item.get("pos", 0))
                if size == 0:
                    continue
                
                side = PositionSide.LONG if item.get("posSide") == "long" else PositionSide.SHORT
                
                position = ExchangePosition(
                    exchange=ExchangeId.OKX,
                    symbol=self._parse_symbol(item["instId"]),
                    side=side,
                    size=abs(size),
                    entry_price=float(item.get("avgPx", 0)),
                    mark_price=float(item.get("markPx", 0)),
                    liquidation_price=float(item.get("liqPx", 0)) if item.get("liqPx") else None,
                    unrealized_pnl=float(item.get("upl", 0)),
                    leverage=int(item.get("lever", 1)),
                    margin_mode=MarginMode.ISOLATED if item.get("mgnMode") == "isolated" else MarginMode.CROSS,
                    margin=float(item.get("imr", 0)),
                    updated_at=datetime.utcnow(),
                    raw_payload=item
                )
                positions.append(position)
        
        return positions
    
    # ============================================
    # Order Operations
    # ============================================
    
    async def create_order(self, order: ExchangeOrderRequest) -> ExchangeOrderResponse:
        """Create a new order"""
        endpoint = "/api/v5/trade/order"
        
        params = {
            "instId": self._normalize_symbol(order.symbol),
            "tdMode": "cross",  # cross margin
            "side": "buy" if order.side == OrderSide.BUY else "sell",
            "ordType": self.ORDER_TYPE_MAP.get(order.order_type, "market"),
            "sz": str(order.size)
        }
        
        # Add price for limit orders
        if order.order_type == OrderType.LIMIT and order.price:
            params["px"] = str(order.price)
        
        # Reduce only
        if order.reduce_only:
            params["reduceOnly"] = True
        
        # Client order ID
        if order.client_order_id:
            params["clOrdId"] = order.client_order_id
        
        response = await self._signed_request("POST", endpoint, None, params)
        
        if response.get("data"):
            return self._parse_order_response(response["data"][0])
        
        raise ValueError(f"Order creation failed: {response}")
    
    async def cancel_order(
        self,
        order_id: str,
        symbol: Optional[str] = None
    ) -> ExchangeOrderResponse:
        """Cancel an order"""
        if not symbol:
            raise ValueError("Symbol is required for OKX cancel order")
        
        endpoint = "/api/v5/trade/cancel-order"
        body = {
            "instId": self._normalize_symbol(symbol),
            "ordId": order_id
        }
        
        response = await self._signed_request("POST", endpoint, None, body)
        
        if response.get("data"):
            return self._parse_order_response(response["data"][0])
        
        raise ValueError(f"Order cancellation failed: {response}")
    
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> List[ExchangeOrderResponse]:
        """Cancel all open orders"""
        # OKX doesn't have batch cancel, cancel one by one
        open_orders = await self.get_open_orders(symbol)
        
        results = []
        for order in open_orders:
            try:
                result = await self.cancel_order(order.exchange_order_id, order.symbol)
                results.append(result)
            except Exception:
                pass
        
        return results
    
    async def get_order_status(
        self,
        order_id: str,
        symbol: Optional[str] = None
    ) -> ExchangeOrderResponse:
        """Get order status"""
        if not symbol:
            raise ValueError("Symbol is required for OKX order status")
        
        endpoint = "/api/v5/trade/order"
        params = {
            "instId": self._normalize_symbol(symbol),
            "ordId": order_id
        }
        
        response = await self._signed_request("GET", endpoint, params)
        
        if response.get("data"):
            return self._parse_order_response(response["data"][0])
        
        raise ValueError(f"Order {order_id} not found")
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[ExchangeOrderResponse]:
        """Get all open orders"""
        endpoint = "/api/v5/trade/orders-pending"
        params = {"instType": "SWAP"}
        if symbol:
            params["instId"] = self._normalize_symbol(symbol)
        
        response = await self._signed_request("GET", endpoint, params)
        
        orders = []
        if response.get("data"):
            for item in response["data"]:
                orders.append(self._parse_order_response(item))
        
        return orders
    
    # ============================================
    # Market Data
    # ============================================
    
    async def get_ticker(self, symbol: str) -> ExchangeTicker:
        """Get ticker for symbol"""
        endpoint = "/api/v5/market/ticker"
        params = {"instId": self._normalize_symbol(symbol)}
        
        response = await self._public_request("GET", endpoint, params)
        
        if response.get("data"):
            item = response["data"][0]
            
            return ExchangeTicker(
                exchange=ExchangeId.OKX,
                symbol=symbol,
                last_price=float(item.get("last", 0)),
                bid_price=float(item.get("bidPx", 0)),
                ask_price=float(item.get("askPx", 0)),
                bid_size=float(item.get("bidSz", 0)),
                ask_size=float(item.get("askSz", 0)),
                high_24h=float(item.get("high24h", 0)),
                low_24h=float(item.get("low24h", 0)),
                volume_24h=float(item.get("vol24h", 0)),
                quote_volume_24h=float(item.get("volCcy24h", 0)),
                timestamp=datetime.utcnow()
            )
        
        raise ValueError(f"Ticker not found for {symbol}")
    
    async def get_orderbook(
        self,
        symbol: str,
        depth: int = 20
    ) -> ExchangeOrderbook:
        """Get orderbook for symbol"""
        endpoint = "/api/v5/market/books"
        params = {
            "instId": self._normalize_symbol(symbol),
            "sz": str(min(depth, 400))
        }
        
        response = await self._public_request("GET", endpoint, params)
        
        if response.get("data"):
            result = response["data"][0]
            
            bids = [OrderbookLevel(price=float(b[0]), size=float(b[1])) for b in result.get("bids", [])]
            asks = [OrderbookLevel(price=float(a[0]), size=float(a[1])) for a in result.get("asks", [])]
            
            return ExchangeOrderbook(
                exchange=ExchangeId.OKX,
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=datetime.utcnow()
            )
        
        raise ValueError(f"Orderbook not found for {symbol}")
    
    # ============================================
    # WebSocket Streams (Placeholder)
    # ============================================
    
    async def subscribe_market_data(
        self,
        symbols: List[str],
        stream_type: StreamType
    ) -> bool:
        """Subscribe to market data stream"""
        return True
    
    async def subscribe_user_stream(self) -> bool:
        """Subscribe to user data stream"""
        return True
    
    async def unsubscribe(
        self,
        symbols: List[str],
        stream_type: StreamType
    ) -> bool:
        """Unsubscribe from stream"""
        return True
    
    # ============================================
    # Private Helper Methods
    # ============================================
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol to OKX format (e.g., BTCUSDT -> BTC-USDT-SWAP)"""
        symbol = symbol.upper().replace("-", "").replace("/", "")
        
        # Extract base and quote
        if symbol.endswith("USDT"):
            base = symbol[:-4]
            quote = "USDT"
        elif symbol.endswith("USD"):
            base = symbol[:-3]
            quote = "USD"
        else:
            base = symbol[:3]
            quote = symbol[3:]
        
        return f"{base}-{quote}-SWAP"
    
    def _parse_symbol(self, exchange_symbol: str) -> str:
        """Parse OKX symbol to unified format (e.g., BTC-USDT-SWAP -> BTCUSDT)"""
        parts = exchange_symbol.split("-")
        if len(parts) >= 2:
            return f"{parts[0]}{parts[1]}"
        return exchange_symbol
    
    def _generate_signature(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """Generate HMAC SHA256 signature"""
        if not self.api_secret:
            raise ValueError("API secret not configured")
        
        prehash = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            prehash.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    
    async def _public_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Any:
        """Make public API request"""
        if not self._client:
            await self.connect()
        
        if method == "GET":
            response = await self._client.get(endpoint, params=params)
        else:
            response = await self._client.post(endpoint, json=params)
        
        response.raise_for_status()
        return response.json()
    
    async def _signed_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        body: Optional[Dict] = None
    ) -> Any:
        """Make signed API request"""
        if not self._client:
            await self.connect()
        
        if not self.api_key or not self.api_secret or not self.passphrase:
            # Mock response for testing without credentials
            return self._mock_response(endpoint)
        
        timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
        
        # Build path with query string
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            path = f"{endpoint}?{query}"
        else:
            path = endpoint
        
        # Generate signature
        import json
        body_str = json.dumps(body) if body else ""
        signature = self._generate_signature(timestamp, method, path, body_str)
        
        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json"
        }
        
        # Add demo trading header if testnet
        if self.testnet:
            headers["x-simulated-trading"] = "1"
        
        if method == "GET":
            response = await self._client.get(endpoint, params=params, headers=headers)
        else:
            response = await self._client.post(endpoint, json=body, headers=headers)
        
        response.raise_for_status()
        return response.json()
    
    def _mock_response(self, endpoint: str) -> Any:
        """Generate mock response for testing"""
        if "balance" in endpoint:
            return {
                "data": [{
                    "details": [
                        {"ccy": "USDT", "cashBal": "10000.00", "availBal": "9500.00", "frozenBal": "500.00", "eqUsd": "10000.00"},
                        {"ccy": "BTC", "cashBal": "0.5", "availBal": "0.5", "frozenBal": "0", "eqUsd": "23000.00"}
                    ]
                }]
            }
        elif "positions" in endpoint:
            return {
                "data": [{
                    "instId": "BTC-USDT-SWAP",
                    "posSide": "long",
                    "pos": "0.1",
                    "avgPx": "45000.00",
                    "markPx": "46000.00",
                    "upl": "100.00",
                    "liqPx": "40000.00",
                    "lever": "10",
                    "mgnMode": "cross",
                    "imr": "450.00"
                }]
            }
        elif "trade/order" in endpoint:
            return {
                "data": [{
                    "ordId": str(uuid.uuid4().hex[:8]),
                    "clOrdId": "",
                    "instId": "BTC-USDT-SWAP",
                    "side": "buy",
                    "ordType": "market",
                    "state": "filled",
                    "sz": "0.1",
                    "fillSz": "0.1",
                    "avgPx": "45000.00",
                    "px": "0",
                    "cTime": str(int(time.time() * 1000)),
                    "uTime": str(int(time.time() * 1000))
                }]
            }
        elif "orders-pending" in endpoint:
            return {"data": []}
        
        return {"data": []}
    
    def _parse_order_response(self, data: Dict) -> ExchangeOrderResponse:
        """Parse OKX order response to unified format"""
        status_map = {
            "live": OrderStatus.NEW,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "filled": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELED
        }
        
        side_map = {
            "buy": OrderSide.BUY,
            "sell": OrderSide.SELL
        }
        
        type_map = {
            "market": OrderType.MARKET,
            "limit": OrderType.LIMIT,
            "trigger": OrderType.STOP_MARKET
        }
        
        orig_qty = float(data.get("sz", 0))
        exec_qty = float(data.get("fillSz", 0)) if data.get("fillSz") else 0
        
        return ExchangeOrderResponse(
            exchange=ExchangeId.OKX,
            exchange_order_id=str(data.get("ordId", "")),
            client_order_id=data.get("clOrdId"),
            symbol=self._parse_symbol(data.get("instId", "")),
            side=side_map.get(data.get("side", "buy"), OrderSide.BUY),
            order_type=type_map.get(data.get("ordType", "market"), OrderType.MARKET),
            status=status_map.get(data.get("state", "live"), OrderStatus.NEW),
            original_size=orig_qty,
            filled_size=exec_qty,
            remaining_size=orig_qty - exec_qty,
            price=float(data["px"]) if data.get("px") and float(data["px"]) > 0 else None,
            avg_fill_price=float(data["avgPx"]) if data.get("avgPx") and float(data["avgPx"]) > 0 else None,
            created_at=datetime.fromtimestamp(int(data.get("cTime", time.time() * 1000)) / 1000) if data.get("cTime") else datetime.utcnow(),
            updated_at=datetime.fromtimestamp(int(data.get("uTime", time.time() * 1000)) / 1000) if data.get("uTime") else datetime.utcnow(),
            raw_payload=data
        )
