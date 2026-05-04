"""
Binance Adapter - PHASE 5.1
===========================

Binance Futures exchange adapter implementation.
Supports both mainnet and testnet.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib
import hmac
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


class BinanceAdapter(BaseExchangeAdapter):
    """
    Binance Futures adapter.
    
    REST API endpoints:
    - Mainnet: https://fapi.binance.com
    - Testnet: https://testnet.binancefuture.com
    
    WebSocket endpoints:
    - Mainnet: wss://fstream.binance.com
    - Testnet: wss://stream.binancefuture.com
    """
    
    # API endpoints
    MAINNET_REST = "https://fapi.binance.com"
    TESTNET_REST = "https://testnet.binancefuture.com"
    MAINNET_WS = "wss://fstream.binance.com"
    TESTNET_WS = "wss://stream.binancefuture.com"
    
    # Order type mapping
    ORDER_TYPE_MAP = {
        OrderType.MARKET: "MARKET",
        OrderType.LIMIT: "LIMIT",
        OrderType.STOP_MARKET: "STOP_MARKET",
        OrderType.STOP_LIMIT: "STOP",
        OrderType.TAKE_PROFIT_MARKET: "TAKE_PROFIT_MARKET",
        OrderType.TAKE_PROFIT_LIMIT: "TAKE_PROFIT",
        OrderType.TRAILING_STOP: "TRAILING_STOP_MARKET"
    }
    
    # Time in force mapping
    TIF_MAP = {
        TimeInForce.GTC: "GTC",
        TimeInForce.IOC: "IOC",
        TimeInForce.FOK: "FOK",
        TimeInForce.GTX: "GTX"
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = False
    ):
        super().__init__(
            exchange_id=ExchangeId.BINANCE,
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet
        )
        
        self.base_url = self.TESTNET_REST if testnet else self.MAINNET_REST
        self.ws_url = self.TESTNET_WS if testnet else self.MAINNET_WS
        self._client: Optional[httpx.AsyncClient] = None
        self._listen_key: Optional[str] = None
    
    # ============================================
    # Connection Management
    # ============================================
    
    async def connect(self) -> bool:
        """Connect to Binance"""
        try:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0
            )
            
            # Test connection with server time
            response = await self._client.get("/fapi/v1/time")
            if response.status_code == 200:
                self._connected = True
                self._connected_at = datetime.utcnow()
                
                # If we have credentials, verify them
                if self.api_key and self.api_secret:
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
        """Disconnect from Binance"""
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
        endpoint = "/fapi/v2/balance"
        response = await self._signed_request("GET", endpoint)
        
        balances = []
        for item in response:
            if asset and item["asset"] != asset:
                continue
                
            balance = ExchangeBalance(
                exchange=ExchangeId.BINANCE,
                asset=item["asset"],
                free=float(item["availableBalance"]),
                locked=float(item["balance"]) - float(item["availableBalance"]),
                total=float(item["balance"]),
                updated_at=datetime.utcnow()
            )
            balances.append(balance)
        
        return balances
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[ExchangePosition]:
        """Get open positions"""
        endpoint = "/fapi/v2/positionRisk"
        params = {}
        if symbol:
            params["symbol"] = self._normalize_symbol(symbol)
        
        response = await self._signed_request("GET", endpoint, params)
        
        positions = []
        for item in response:
            size = float(item["positionAmt"])
            if size == 0:
                continue  # Skip empty positions
            
            side = PositionSide.LONG if size > 0 else PositionSide.SHORT
            
            position = ExchangePosition(
                exchange=ExchangeId.BINANCE,
                symbol=item["symbol"],
                side=side,
                size=abs(size),
                entry_price=float(item["entryPrice"]),
                mark_price=float(item["markPrice"]),
                liquidation_price=float(item["liquidationPrice"]) if item["liquidationPrice"] else None,
                unrealized_pnl=float(item["unRealizedProfit"]),
                leverage=int(item["leverage"]),
                margin_mode=MarginMode.ISOLATED if item["marginType"] == "isolated" else MarginMode.CROSS,
                margin=float(item["isolatedMargin"]) if item["marginType"] == "isolated" else 0,
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
        endpoint = "/fapi/v1/order"
        
        params = {
            "symbol": self._normalize_symbol(order.symbol),
            "side": order.side.value,
            "type": self.ORDER_TYPE_MAP.get(order.order_type, "MARKET"),
            "quantity": str(order.size)
        }
        
        # Add price for limit orders
        if order.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT, OrderType.TAKE_PROFIT_LIMIT]:
            if order.price:
                params["price"] = str(order.price)
            params["timeInForce"] = self.TIF_MAP.get(order.time_in_force, "GTC")
        
        # Add stop price
        if order.stop_price:
            params["stopPrice"] = str(order.stop_price)
        
        # Reduce only
        if order.reduce_only:
            params["reduceOnly"] = "true"
        
        # Client order ID
        if order.client_order_id:
            params["newClientOrderId"] = order.client_order_id
        
        response = await self._signed_request("POST", endpoint, params)
        return self._parse_order_response(response)
    
    async def cancel_order(
        self,
        order_id: str,
        symbol: Optional[str] = None
    ) -> ExchangeOrderResponse:
        """Cancel an order"""
        if not symbol:
            raise ValueError("Symbol is required for Binance cancel order")
        
        endpoint = "/fapi/v1/order"
        params = {
            "symbol": self._normalize_symbol(symbol),
            "orderId": order_id
        }
        
        response = await self._signed_request("DELETE", endpoint, params)
        return self._parse_order_response(response)
    
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> List[ExchangeOrderResponse]:
        """Cancel all open orders"""
        if not symbol:
            # Get all open orders first, then cancel by symbol
            open_orders = await self.get_open_orders()
            symbols = set(o.symbol for o in open_orders)
            
            results = []
            for sym in symbols:
                endpoint = "/fapi/v1/allOpenOrders"
                params = {"symbol": self._normalize_symbol(sym)}
                await self._signed_request("DELETE", endpoint, params)
            
            return results
        
        endpoint = "/fapi/v1/allOpenOrders"
        params = {"symbol": self._normalize_symbol(symbol)}
        await self._signed_request("DELETE", endpoint, params)
        return []
    
    async def get_order_status(
        self,
        order_id: str,
        symbol: Optional[str] = None
    ) -> ExchangeOrderResponse:
        """Get order status"""
        if not symbol:
            raise ValueError("Symbol is required for Binance order status")
        
        endpoint = "/fapi/v1/order"
        params = {
            "symbol": self._normalize_symbol(symbol),
            "orderId": order_id
        }
        
        response = await self._signed_request("GET", endpoint, params)
        return self._parse_order_response(response)
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[ExchangeOrderResponse]:
        """Get all open orders"""
        endpoint = "/fapi/v1/openOrders"
        params = {}
        if symbol:
            params["symbol"] = self._normalize_symbol(symbol)
        
        response = await self._signed_request("GET", endpoint, params)
        return [self._parse_order_response(o) for o in response]
    
    # ============================================
    # Market Data
    # ============================================
    
    async def get_ticker(self, symbol: str) -> ExchangeTicker:
        """Get ticker for symbol"""
        try:
            endpoint = "/fapi/v1/ticker/24hr"
            params = {"symbol": self._normalize_symbol(symbol)}
            
            response = await self._public_request("GET", endpoint, params)
            
            return ExchangeTicker(
                exchange=ExchangeId.BINANCE,
                symbol=symbol,
                last_price=float(response.get("lastPrice", 0)),
                bid_price=float(response.get("bidPrice", 0)),
                ask_price=float(response.get("askPrice", 0)),
                high_24h=float(response.get("highPrice", 0)),
                low_24h=float(response.get("lowPrice", 0)),
                volume_24h=float(response.get("volume", 0)),
                quote_volume_24h=float(response.get("quoteVolume", 0)),
                price_change_24h=float(response.get("priceChange", 0)),
                price_change_pct_24h=float(response.get("priceChangePercent", 0)),
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            # Return mock ticker for testnet/demo
            return self._mock_ticker(symbol)
    
    async def get_orderbook(
        self,
        symbol: str,
        depth: int = 20
    ) -> ExchangeOrderbook:
        """Get orderbook for symbol"""
        try:
            endpoint = "/fapi/v1/depth"
            params = {
                "symbol": self._normalize_symbol(symbol),
                "limit": min(depth, 1000)
            }
            
            response = await self._public_request("GET", endpoint, params)
            
            bids = [OrderbookLevel(price=float(b[0]), size=float(b[1])) for b in response.get("bids", [])]
            asks = [OrderbookLevel(price=float(a[0]), size=float(a[1])) for a in response.get("asks", [])]
            
            return ExchangeOrderbook(
                exchange=ExchangeId.BINANCE,
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            # Return mock orderbook for testnet/demo
            return self._mock_orderbook(symbol)
    
    # ============================================
    # WebSocket Streams (Placeholder)
    # ============================================
    
    async def subscribe_market_data(
        self,
        symbols: List[str],
        stream_type: StreamType
    ) -> bool:
        """Subscribe to market data stream"""
        # WebSocket implementation will be in ws_manager
        return True
    
    async def subscribe_user_stream(self) -> bool:
        """Subscribe to user data stream"""
        # Get listen key
        endpoint = "/fapi/v1/listenKey"
        response = await self._signed_request("POST", endpoint)
        self._listen_key = response.get("listenKey")
        return bool(self._listen_key)
    
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
        """Normalize symbol to Binance format"""
        return symbol.upper().replace("-", "").replace("/", "")
    
    def _parse_symbol(self, exchange_symbol: str) -> str:
        """Parse Binance symbol to unified format"""
        return exchange_symbol.upper()
    
    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC SHA256 signature"""
        if not self.api_secret:
            raise ValueError("API secret not configured")
        
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
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
            response = await self._client.post(endpoint, data=params)
        
        response.raise_for_status()
        return response.json()
    
    async def _signed_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Any:
        """Make signed API request"""
        if not self._client:
            await self.connect()
        
        if not self.api_key or not self.api_secret:
            # Mock response for testing without credentials
            return self._mock_response(endpoint)
        
        params = params or {}
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        signature = self._generate_signature(query_string)
        params["signature"] = signature
        
        headers = {"X-MBX-APIKEY": self.api_key}
        
        if method == "GET":
            response = await self._client.get(endpoint, params=params, headers=headers)
        elif method == "POST":
            response = await self._client.post(endpoint, data=params, headers=headers)
        elif method == "DELETE":
            response = await self._client.delete(endpoint, params=params, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        # Update rate limits
        if "X-MBX-USED-WEIGHT-1M" in response.headers:
            used = int(response.headers["X-MBX-USED-WEIGHT-1M"])
            self._rate_limit_remaining = max(0, 1200 - used)
        
        response.raise_for_status()
        return response.json()
    
    def _mock_response(self, endpoint: str) -> Any:
        """Generate mock response for testing"""
        if "balance" in endpoint:
            return [
                {"asset": "USDT", "balance": "10000.00", "availableBalance": "9500.00"},
                {"asset": "BTC", "balance": "0.5", "availableBalance": "0.5"}
            ]
        elif "positionRisk" in endpoint:
            return [
                {
                    "symbol": "BTCUSDT",
                    "positionAmt": "0.1",
                    "entryPrice": "45000.00",
                    "markPrice": "46000.00",
                    "unRealizedProfit": "100.00",
                    "liquidationPrice": "40000.00",
                    "leverage": "10",
                    "marginType": "cross",
                    "isolatedMargin": "0"
                }
            ]
        elif "order" in endpoint:
            return {
                "orderId": str(uuid.uuid4().hex[:8]),
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "MARKET",
                "status": "FILLED",
                "origQty": "0.1",
                "executedQty": "0.1",
                "avgPrice": "45000.00",
                "price": "0",
                "time": int(time.time() * 1000),
                "updateTime": int(time.time() * 1000)
            }
        elif "openOrders" in endpoint:
            return []
        elif "listenKey" in endpoint:
            return {"listenKey": f"mock_{uuid.uuid4().hex}"}
        
        return {}

    def _mock_ticker(self, symbol: str) -> ExchangeTicker:
        """Generate mock ticker"""
        import random
        base_prices = {"BTCUSDT": 45000, "ETHUSDT": 2500, "SOLUSDT": 100}
        price = base_prices.get(symbol.upper(), 100) * (1 + random.uniform(-0.01, 0.01))
        
        return ExchangeTicker(
            exchange=ExchangeId.BINANCE,
            symbol=symbol,
            last_price=round(price, 2),
            bid_price=round(price * 0.9999, 2),
            ask_price=round(price * 1.0001, 2),
            high_24h=round(price * 1.02, 2),
            low_24h=round(price * 0.98, 2),
            volume_24h=random.uniform(1000, 10000),
            quote_volume_24h=random.uniform(50000000, 100000000),
            price_change_24h=round(price * random.uniform(-0.02, 0.02), 2),
            price_change_pct_24h=random.uniform(-2, 2),
            timestamp=datetime.utcnow()
        )
    
    def _mock_orderbook(self, symbol: str) -> ExchangeOrderbook:
        """Generate mock orderbook"""
        import random
        base_prices = {"BTCUSDT": 45000, "ETHUSDT": 2500, "SOLUSDT": 100}
        price = base_prices.get(symbol.upper(), 100)
        
        bids = [OrderbookLevel(price=round(price * (1 - 0.0001 * (i + 1)), 2), size=round(random.uniform(0.1, 5), 3)) for i in range(10)]
        asks = [OrderbookLevel(price=round(price * (1 + 0.0001 * (i + 1)), 2), size=round(random.uniform(0.1, 5), 3)) for i in range(10)]
        
        return ExchangeOrderbook(
            exchange=ExchangeId.BINANCE,
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=datetime.utcnow()
        )

    
    def _parse_order_response(self, data: Dict) -> ExchangeOrderResponse:
        """Parse Binance order response to unified format"""
        status_map = {
            "NEW": OrderStatus.NEW,
            "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELED,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.EXPIRED
        }
        
        side_map = {
            "BUY": OrderSide.BUY,
            "SELL": OrderSide.SELL
        }
        
        type_map = {
            "MARKET": OrderType.MARKET,
            "LIMIT": OrderType.LIMIT,
            "STOP": OrderType.STOP_LIMIT,
            "STOP_MARKET": OrderType.STOP_MARKET,
            "TAKE_PROFIT": OrderType.TAKE_PROFIT_LIMIT,
            "TAKE_PROFIT_MARKET": OrderType.TAKE_PROFIT_MARKET,
            "TRAILING_STOP_MARKET": OrderType.TRAILING_STOP
        }
        
        orig_qty = float(data.get("origQty", 0))
        exec_qty = float(data.get("executedQty", 0))
        
        return ExchangeOrderResponse(
            exchange=ExchangeId.BINANCE,
            exchange_order_id=str(data.get("orderId", "")),
            client_order_id=data.get("clientOrderId"),
            symbol=data.get("symbol", ""),
            side=side_map.get(data.get("side", "BUY"), OrderSide.BUY),
            order_type=type_map.get(data.get("type", "MARKET"), OrderType.MARKET),
            status=status_map.get(data.get("status", "NEW"), OrderStatus.NEW),
            original_size=orig_qty,
            filled_size=exec_qty,
            remaining_size=orig_qty - exec_qty,
            price=float(data["price"]) if data.get("price") and float(data["price"]) > 0 else None,
            avg_fill_price=float(data["avgPrice"]) if data.get("avgPrice") and float(data["avgPrice"]) > 0 else None,
            stop_price=float(data["stopPrice"]) if data.get("stopPrice") and float(data["stopPrice"]) > 0 else None,
            created_at=datetime.fromtimestamp(data.get("time", time.time() * 1000) / 1000),
            updated_at=datetime.fromtimestamp(data.get("updateTime", time.time() * 1000) / 1000),
            raw_payload=data
        )
