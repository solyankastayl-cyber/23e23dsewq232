"""
Binance Testnet Futures Adapter

Production-ready adapter for Binance USDT-M Futures Testnet.
Returns normalized models, no raw JSON.
"""

import time
import hmac
import hashlib
from urllib.parse import urlencode
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx
import logging

from .base import ExchangeAdapter
from .models import AccountInfo, Balance, Position, Order, Fill

logger = logging.getLogger(__name__)


class BinanceAdapter(ExchangeAdapter):
    """Binance USDT-M Futures Testnet adapter."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        
        # CRITICAL: Use futures testnet, NOT spot
        if testnet:
            self.base_url = "https://testnet.binancefuture.com"
        else:
            self.base_url = "https://fapi.binance.com"
        
        self.client = httpx.AsyncClient(timeout=10.0)

    # ======================
    # INTERNAL HELPERS
    # ======================

    def _sign(self, params: dict) -> str:
        """Generate HMAC SHA256 signature."""
        query = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode(),
            query.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{query}&signature={signature}"

    async def _request(self, method: str, path: str, params: dict = None, signed: bool = False) -> Any:
        """Make HTTP request to Binance API."""
        if params is None:
            params = {}

        headers = {
            "X-MBX-APIKEY": self.api_key
        }

        if signed:
            # Add timestamp (must be within 5 sec of server time)
            params["timestamp"] = int(time.time() * 1000)
            query = self._sign(params)
        else:
            query = urlencode(params)

        url = f"{self.base_url}{path}"
        
        if query:
            url = f"{url}?{query}"

        try:
            if method == "GET":
                res = await self.client.get(url, headers=headers)
            elif method == "POST":
                res = await self.client.post(url, headers=headers)
            elif method == "DELETE":
                res = await self.client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if res.status_code != 200:
                logger.error(f"[BinanceAdapter] Error {res.status_code}: {res.text}")
                raise Exception(f"Binance API error: {res.text}")

            return res.json()
        
        except httpx.RequestError as e:
            logger.error(f"[BinanceAdapter] Request error: {e}")
            raise

    # ======================
    # CORE PROTOCOL METHODS
    # ======================

    async def connect(self) -> bool:
        """Test connection to Binance."""
        try:
            data = await self._request("GET", "/fapi/v2/account", signed=True)
            logger.info("[BinanceAdapter] Connected to Binance Testnet")
            return data is not None
        except Exception as e:
            logger.error(f"[BinanceAdapter] Connection failed: {e}")
            return False

    async def get_account_info(self) -> AccountInfo:
        """Get normalized account info."""
        data = await self._request("GET", "/fapi/v2/account", signed=True)

        return AccountInfo(
            account_id="binance_testnet",
            exchange="binance_testnet",
            account_type="FUTURES",
            status="ACTIVE",
            can_trade=data.get("canTrade", False),
            can_withdraw=data.get("canWithdraw", False),
            can_deposit=data.get("canDeposit", False),
        )

    async def get_balances(self) -> List[Balance]:
        """Get normalized balances."""
        data = await self._request("GET", "/fapi/v2/balance", signed=True)

        balances = []
        for b in data:
            total = float(b["balance"])
            free = float(b["availableBalance"])

            # Only include non-zero balances
            if total > 0:
                balances.append(
                    Balance(
                        asset=b["asset"],
                        free=free,
                        locked=total - free,
                        total=total
                    )
                )

        return balances

    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get normalized positions."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        data = await self._request("GET", "/fapi/v2/positionRisk", params, signed=True)

        positions = []

        for p in data:
            qty = float(p["positionAmt"])

            # Skip empty positions
            if qty == 0:
                continue

            side = "LONG" if qty > 0 else "SHORT"
            entry_price = float(p["entryPrice"])
            mark_price = float(p["markPrice"])
            unrealized_pnl = float(p["unRealizedProfit"])
            
            # Calculate unrealized PnL %
            if entry_price > 0:
                unrealized_pnl_pct = (unrealized_pnl / (abs(qty) * entry_price)) * 100
            else:
                unrealized_pnl_pct = 0.0

            positions.append(
                Position(
                    symbol=p["symbol"],
                    side=side,
                    qty=abs(qty),  # CRITICAL: normalize to positive
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    realized_pnl=0.0,  # TODO: track separately
                    leverage=float(p["leverage"]),
                    status="OPEN",
                    liquidation_price=float(p.get("liquidationPrice", 0)),
                )
            )

        return positions

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get normalized open orders."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        data = await self._request("GET", "/fapi/v1/openOrders", params, signed=True)

        orders = []
        for o in data:
            orders.append(self._normalize_order(o))

        return orders

    async def get_order_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[Order]:
        """Get normalized order history."""
        if not symbol:
            # Binance requires symbol for allOrders
            # Return empty for now, or implement multi-symbol fetch
            return []
        
        params = {
            "symbol": symbol,
            "limit": limit
        }
        
        data = await self._request("GET", "/fapi/v1/allOrders", params, signed=True)

        orders = []
        for o in data:
            orders.append(self._normalize_order(o))

        return orders

    async def get_fills(self, symbol: Optional[str] = None, limit: int = 100) -> List[Fill]:
        """Get normalized fills."""
        if not symbol:
            # Binance requires symbol for userTrades
            return []
        
        params = {
            "symbol": symbol,
            "limit": limit
        }

        data = await self._request("GET", "/fapi/v1/userTrades", params, signed=True)

        fills = []

        for f in data:
            fills.append(
                Fill(
                    fill_id=str(f["id"]),
                    order_id=str(f["orderId"]),
                    symbol=f["symbol"],
                    side=f["side"],
                    price=float(f["price"]),
                    qty=float(f["qty"]),
                    quote_qty=float(f["quoteQty"]),
                    fee=float(f["commission"]),
                    fee_asset=f["commissionAsset"],
                    is_maker=f["maker"],
                    timestamp=datetime.fromtimestamp(f["time"] / 1000)
                )
            )

        return fills

    async def place_order(self, order_request: Dict[str, Any]) -> Order:
        """Place a new order."""
        params = {
            "symbol": order_request["symbol"],
            "side": order_request["side"],
            "type": order_request["type"],
            "quantity": order_request["quantity"],
        }

        # LIMIT order requires price & timeInForce
        if order_request["type"] == "LIMIT":
            params["price"] = order_request["price"]
            params["timeInForce"] = order_request.get("time_in_force", "GTC")
        
        # STOP orders
        if "stop_price" in order_request:
            params["stopPrice"] = order_request["stop_price"]
        
        # Reduce only
        if order_request.get("reduce_only"):
            params["reduceOnly"] = "true"
        
        # Client order ID
        if order_request.get("client_order_id"):
            params["newClientOrderId"] = order_request["client_order_id"]

        data = await self._request("POST", "/fapi/v1/order", params, signed=True)

        return self._normalize_order(data)

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """Cancel an order."""
        if not symbol:
            raise ValueError("Binance requires symbol to cancel order")
        
        params = {
            "symbol": symbol,
            "orderId": order_id
        }

        try:
            await self._request("DELETE", "/fapi/v1/order", params, signed=True)
            return True
        except Exception as e:
            logger.error(f"[BinanceAdapter] Cancel order failed: {e}")
            return False

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """Cancel all open orders."""
        if not symbol:
            raise ValueError("Binance requires symbol to cancel all orders")
        
        params = {"symbol": symbol}

        try:
            data = await self._request("DELETE", "/fapi/v1/allOpenOrders", params, signed=True)
            return data.get("code", 0)  # TODO: parse actual count
        except Exception as e:
            logger.error(f"[BinanceAdapter] Cancel all orders failed: {e}")
            return 0

    async def get_mark_price(self, symbol: str) -> float:
        """Get current mark price."""
        params = {"symbol": symbol}
        
        data = await self._request("GET", "/fapi/v1/premiumIndex", params, signed=False)
        
        return float(data["markPrice"])

    async def sync_state(self) -> Dict[str, Any]:
        """Sync exchange state."""
        balances = await self.get_balances()
        positions = await self.get_positions()
        open_orders = await self.get_open_orders()
        
        return {
            "balances": [b.dict() for b in balances],
            "positions": [p.dict() for p in positions],
            "open_orders": [o.dict() for o in open_orders],
        }

    # ======================
    # HELPERS
    # ======================

    def _normalize_order(self, order_data: dict) -> Order:
        """Convert Binance order to normalized Order model."""
        return Order(
            order_id=str(order_data["orderId"]),
            client_order_id=order_data.get("clientOrderId"),
            symbol=order_data["symbol"],
            side=order_data["side"],
            type=order_data["type"],
            price=float(order_data.get("price", 0)),
            stop_price=float(order_data.get("stopPrice", 0)) if order_data.get("stopPrice") else None,
            qty=float(order_data["origQty"]),
            filled_qty=float(order_data.get("executedQty", 0)),
            remaining_qty=float(order_data["origQty"]) - float(order_data.get("executedQty", 0)),
            status=order_data["status"],
            time_in_force=order_data.get("timeInForce"),
            reduce_only=order_data.get("reduceOnly", False),
            created_at=datetime.fromtimestamp(order_data["time"] / 1000),
            updated_at=datetime.fromtimestamp(order_data.get("updateTime", order_data["time"]) / 1000),
        )
