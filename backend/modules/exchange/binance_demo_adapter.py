"""
Binance Demo Adapter — Real Execution on Binance Futures Testnet

CRITICAL:
- Uses Binance FUTURES TESTNET (paper funds, real execution logic)
- Supports FUTURES trading (perpetual contracts)
- All orders are REAL (but on testnet)
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from binance.client import Client
from binance.exceptions import BinanceAPIException

from .base import ExchangeAdapter
from .models import AccountInfo, Balance, Position, Order, Fill

logger = logging.getLogger(__name__)


class BinanceDemoAdapter(ExchangeAdapter):
    """
    Binance Futures Testnet adapter.
    
    Environment:
    - BINANCE_TESTNET_API_KEY
    - BINANCE_TESTNET_API_SECRET
    """
    
    def __init__(self, config: dict, db_client=None):
        """
        Args:
            config: {
                "api_key": "...",
                "api_secret": "...",
                "account_id": "binance_testnet_default",
                "proxy": "http://user:pass@host:port" (optional)
            }
        """
        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")
        self.account_id = config.get("account_id", "binance_futures_testnet")
        self.proxy = config.get("proxy")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("Binance API key/secret required")
        
        # Build Client kwargs for Futures Testnet
        client_kwargs = {}
        
        # Add proxy via requests_params if configured
        if self.proxy:
            client_kwargs["requests_params"] = {
                "proxies": {
                    "http": self.proxy,
                    "https": self.proxy
                },
                "timeout": 30
            }
            logger.info(f"[BinanceDemoAdapter] Using proxy for connection")
        
        # Create Futures client with testnet base URL
        self.client = Client(
            self.api_key,
            self.api_secret,
            **client_kwargs
        )
        
        # Override base URL for Futures Testnet
        self.client.API_URL = 'https://testnet.binancefuture.com'
        self.client.FUTURES_URL = 'https://testnet.binancefuture.com'
        
        self.connected = False
        
        logger.info(f"[BinanceDemoAdapter] Initialized for FUTURES Testnet (account_id={self.account_id})")
    
    async def connect(self) -> bool:
        """
        Connect to Binance Futures Testnet and verify credentials.
        """
        try:
            # Test connection via futures_account
            account = self.client.futures_account()
            
            if not account:
                raise RuntimeError("Failed to retrieve futures account info")
            
            self.connected = True
            logger.info(f"[BinanceDemoAdapter] Connected to Binance Futures Testnet")
            logger.info(f"[BinanceDemoAdapter] Balance: {account.get('totalWalletBalance', 0)} USDT")
            
            return True
        
        except BinanceAPIException as e:
            logger.error(f"[BinanceDemoAdapter] Connection failed: {e.message}")
            self.connected = False
            return False
        
        except Exception as e:
            logger.error(f"[BinanceDemoAdapter] Connection failed: {e}")
            self.connected = False
            return False
    
    async def get_account_info(self) -> AccountInfo:
        """
        Get normalized account info.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        account = self.client.futures_account()
        
        return AccountInfo(
            account_id=self.account_id,
            exchange="binance_futures_testnet",
            account_type="FUTURES",
            status="ACTIVE" if account.get("canTrade", False) else "RESTRICTED",
            can_trade=account.get("canTrade", False),
            can_withdraw=account.get("canWithdraw", False),
            can_deposit=account.get("canDeposit", False),
            created_at=datetime.now(timezone.utc),
        )
    
    async def get_balances(self) -> List[Balance]:
        """
        Get normalized balances.
        
        Returns only non-zero balances.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        account = self.client.get_account()
        balances = []
        
        for b in account["balances"]:
            free = float(b["free"])
            locked = float(b["locked"])
            total = free + locked
            
            if total > 0:
                balances.append(Balance(
                    asset=b["asset"],
                    free=free,
                    locked=locked,
                    total=total,
                ))
        
        return balances
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """
        Get normalized positions.
        
        For SPOT, positions = non-USDT balances.
        (This is a simplification; real futures would use /fapi/v2/positionRisk)
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        balances = await self.get_balances()
        positions = []
        
        for balance in balances:
            # Skip stablecoins (they are cash, not positions)
            if balance.asset in ["USDT", "USDC", "BUSD"]:
                continue
            
            # Construct position from balance
            # (This assumes all non-stablecoin balances are positions)
            
            # Get current mark price
            symbol_name = f"{balance.asset}USDT"
            
            if symbol and symbol_name != symbol:
                continue
            
            try:
                mark_price = await self.get_mark_price(symbol_name)
            except:
                logger.warning(f"[BinanceDemoAdapter] Failed to get mark price for {symbol_name}, skipping")
                continue
            
            # We don't have entry price in SPOT (no position tracking)
            # So we just use current price as entry (for simplicity)
            # In real system, you'd track this in TradingCase
            
            positions.append(Position(
                symbol=symbol_name,
                side="LONG",
                qty=balance.total,
                entry_price=mark_price,  # Approximation
                mark_price=mark_price,
                unrealized_pnl=0.0,  # Can't calculate without entry price
                unrealized_pnl_pct=0.0,
                realized_pnl=0.0,
                leverage=1.0,
                status="OPEN",
                opened_at=datetime.now(timezone.utc),
            ))
        
        return positions
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """
        Get normalized open orders.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        # Get open orders
        if symbol:
            orders = self.client.get_open_orders(symbol=symbol)
        else:
            orders = self.client.get_open_orders()
        
        return [self._normalize_order(o) for o in orders]
    
    async def get_order_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[Order]:
        """
        Get normalized order history.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        if not symbol:
            logger.warning("[BinanceDemoAdapter] get_order_history requires symbol on Binance")
            return []
        
        orders = self.client.get_all_orders(symbol=symbol, limit=limit)
        
        return [self._normalize_order(o) for o in orders]
    
    async def get_fills(self, symbol: Optional[str] = None, limit: int = 100) -> List[Fill]:
        """
        Get normalized fills (trades).
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        if not symbol:
            logger.warning("[BinanceDemoAdapter] get_fills requires symbol on Binance")
            return []
        
        trades = self.client.get_my_trades(symbol=symbol, limit=limit)
        
        return [self._normalize_fill(t) for t in trades]
    
    async def place_order(self, order_request: Dict[str, Any]) -> Order:
        """
        Place order on Binance Testnet.
        
        Args:
            order_request: {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "MARKET",
                "quantity": 0.001,
                "price": None (for MARKET)
            }
        
        Returns:
            Normalized Order
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        symbol = order_request["symbol"]
        side = order_request["side"]
        order_type = order_request["type"]
        quantity = order_request["quantity"]
        
        logger.info(f"[BinanceDemoAdapter] Placing order: {side} {quantity} {symbol} ({order_type})")
        
        try:
            # Submit order to Binance
            if order_type == "MARKET":
                result = self.client.order_market(
                    symbol=symbol,
                    side=side,
                    quantity=quantity
                )
            elif order_type == "LIMIT":
                price = order_request.get("price")
                if not price:
                    raise ValueError("LIMIT order requires price")
                
                result = self.client.order_limit(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=str(price)
                )
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
            
            logger.info(f"[BinanceDemoAdapter] Order placed: orderId={result['orderId']}, status={result['status']}")
            
            return self._normalize_order(result)
        
        except BinanceAPIException as e:
            logger.error(f"[BinanceDemoAdapter] Order failed: {e.message}")
            raise RuntimeError(f"Binance API error: {e.message}")
        
        except Exception as e:
            logger.error(f"[BinanceDemoAdapter] Order failed: {e}")
            raise
    
    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """
        Cancel order.
        
        NOTE: Binance requires symbol for cancellation.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        if not symbol:
            raise ValueError("Binance cancel_order requires symbol")
        
        try:
            self.client.cancel_order(symbol=symbol, orderId=order_id)
            logger.info(f"[BinanceDemoAdapter] Order {order_id} canceled")
            return True
        except BinanceAPIException as e:
            logger.error(f"[BinanceDemoAdapter] Cancel failed: {e.message}")
            return False
    
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """
        Cancel all open orders.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        if not symbol:
            raise ValueError("Binance cancel_all_orders requires symbol")
        
        try:
            result = self.client.cancel_open_orders(symbol=symbol)
            count = len(result) if isinstance(result, list) else 1
            logger.info(f"[BinanceDemoAdapter] Canceled {count} orders")
            return count
        except BinanceAPIException as e:
            logger.error(f"[BinanceDemoAdapter] Cancel all failed: {e.message}")
            return 0
    
    async def get_mark_price(self, symbol: str) -> float:
        """
        Get current mark price.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])
    
    async def sync_state(self) -> Dict[str, Any]:
        """
        Sync exchange state (balances, positions, orders).
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        balances = await self.get_balances()
        positions = await self.get_positions()
        open_orders = await self.get_open_orders()
        
        return {
            "balances": [b.dict() for b in balances],
            "positions": [p.dict() for p in positions],
            "open_orders": [o.dict() for o in open_orders],
        }
    
    # Helper methods
    
    def _normalize_order(self, order_data: dict) -> Order:
        """Convert Binance order to normalized Order model."""
        return Order(
            order_id=str(order_data["orderId"]),
            client_order_id=order_data.get("clientOrderId"),
            symbol=order_data["symbol"],
            side=order_data["side"],
            type=order_data["type"],
            price=float(order_data.get("price", 0)) if order_data.get("price") else None,
            stop_price=float(order_data.get("stopPrice", 0)) if order_data.get("stopPrice") else None,
            qty=float(order_data["origQty"]),
            filled_qty=float(order_data.get("executedQty", 0)),
            remaining_qty=float(order_data["origQty"]) - float(order_data.get("executedQty", 0)),
            status=order_data["status"],
            time_in_force=order_data.get("timeInForce", "GTC"),
            reduce_only=False,
            created_at=datetime.fromtimestamp(order_data["time"] / 1000, tz=timezone.utc) if "time" in order_data else datetime.now(timezone.utc),
            updated_at=datetime.fromtimestamp(order_data.get("updateTime", order_data.get("time", 0)) / 1000, tz=timezone.utc) if order_data.get("updateTime") or order_data.get("time") else datetime.now(timezone.utc),
        )
    
    def _normalize_fill(self, trade_data: dict) -> Fill:
        """Convert Binance trade to normalized Fill model."""
        return Fill(
            fill_id=str(trade_data["id"]),
            order_id=str(trade_data["orderId"]),
            symbol=trade_data["symbol"],
            side="BUY" if trade_data["isBuyer"] else "SELL",
            price=float(trade_data["price"]),
            qty=float(trade_data["qty"]),
            quote_qty=float(trade_data["quoteQty"]),
            fee=float(trade_data["commission"]),
            fee_asset=trade_data["commissionAsset"],
            is_maker=trade_data["isMaker"],
            timestamp=datetime.fromtimestamp(trade_data["time"] / 1000, tz=timezone.utc),
        )
