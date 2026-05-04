"""
Binance Futures Adapter — Real Execution on Binance Futures Testnet

CRITICAL:
- Uses Binance FUTURES TESTNET (paper funds, real execution logic)
- Supports perpetual contracts (BTCUSDT, etc)
- Leverage, short/long, real market execution
"""

import logging
import math
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from binance.um_futures import UMFutures
from binance.error import ClientError

from .base import ExchangeAdapter
from .models import AccountInfo, Balance, Position, Order, Fill

logger = logging.getLogger(__name__)


class BinanceFuturesAdapter(ExchangeAdapter):
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
                "account_id": "binance_futures_testnet",
                "proxy": "http://user:pass@host:port" (optional)
            }
        """
        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")
        self.account_id = config.get("account_id", "binance_futures_testnet")
        self.proxy = config.get("proxy")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("Binance Futures API key/secret required")
        
        # Build UMFutures kwargs
        client_kwargs = {
            "key": self.api_key,
            "secret": self.api_secret,
            "base_url": "https://testnet.binancefuture.com"
        }
        
        # Add proxy if configured
        if self.proxy:
            client_kwargs["proxies"] = {
                "http": self.proxy,
                "https": self.proxy
            }
            client_kwargs["timeout"] = 30
            logger.info(f"[BinanceFuturesAdapter] Using proxy for connection")
        
        self.client = UMFutures(**client_kwargs)
        
        self.connected = False
        
        logger.info(f"[BinanceFuturesAdapter] Initialized for FUTURES Testnet (account_id={self.account_id})")
    
    async def connect(self) -> bool:
        """
        Connect to Binance Futures Testnet and verify credentials.
        """
        try:
            # Test connection via account info
            account = self.client.account()
            
            if not account:
                raise RuntimeError("Failed to retrieve futures account info")
            
            self.connected = True
            
            # Get balance
            total_balance = float(account.get("totalWalletBalance", 0))
            available_balance = float(account.get("availableBalance", 0))
            
            logger.info(f"[BinanceFuturesAdapter] ✅ Connected to Binance Futures Testnet")
            logger.info(f"[BinanceFuturesAdapter] Total Balance: {total_balance} USDT")
            logger.info(f"[BinanceFuturesAdapter] Available Balance: {available_balance} USDT")
            
            return True
        
        except ClientError as e:
            logger.error(f"[BinanceFuturesAdapter] Connection failed: {e.error_message}")
            self.connected = False
            return False
        
        except Exception as e:
            logger.error(f"[BinanceFuturesAdapter] Connection failed: {e}")
            self.connected = False
            return False
    
    async def get_account_info(self) -> AccountInfo:
        """
        Get normalized account info.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        account = self.client.account()
        
        return AccountInfo(
            account_id=self.account_id,
            exchange="binance_futures_testnet",
            account_type="FUTURES",
            status="ACTIVE",
            can_trade=True,
            can_withdraw=account.get("canWithdraw", False),
            can_deposit=account.get("canDeposit", False),
            created_at=datetime.now(timezone.utc),
        )
    
    async def get_balances(self) -> list[Balance]:
        """
        Get account balances.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        account = self.client.account()
        
        balances = []
        for asset_data in account.get("assets", []):
            if float(asset_data.get("walletBalance", 0)) > 0:
                balances.append(Balance(
                    asset=asset_data["asset"],
                    free=float(asset_data.get("availableBalance", 0)),
                    locked=float(asset_data.get("walletBalance", 0)) - float(asset_data.get("availableBalance", 0)),
                    total=float(asset_data.get("walletBalance", 0))
                ))
        
        return balances
    
    async def get_positions(self) -> list[Position]:
        """
        Get open positions.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        positions_data = self.client.get_position_risk()
        
        positions = []
        for pos in positions_data:
            position_amt = float(pos.get("positionAmt", 0))
            if position_amt != 0:
                entry_price = float(pos.get("entryPrice", 0))
                mark_price = float(pos.get("markPrice", 0))
                unrealized_pnl = float(pos.get("unRealizedProfit", 0))
                qty = abs(position_amt)
                
                # Calculate unrealized_pnl_pct
                if entry_price > 0:
                    unrealized_pnl_pct = (unrealized_pnl / (entry_price * qty)) * 100
                else:
                    unrealized_pnl_pct = 0.0
                
                positions.append(Position(
                    symbol=pos["symbol"],
                    side="LONG" if position_amt > 0 else "SHORT",
                    qty=qty,
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    realized_pnl=0.0,  # Binance doesn't provide this in position_risk
                    leverage=int(pos.get("leverage", 1)),
                    status="OPEN",
                    liquidation_price=float(pos.get("liquidationPrice", 0)) if pos.get("liquidationPrice") else None
                ))
        
        return positions
    
    async def place_order(self, order_request: dict) -> dict:
        """
        Place order on Binance Futures.
        
        Args:
            order_request: {
                "symbol": "BTCUSDT",
                "side": "BUY" | "SELL",
                "quantity": 0.001,
                "order_type": "MARKET",
                "price": None (for market orders)
            }
        
        Returns:
            {
                "order_id": "...",
                "exchange_order_id": "...",
                "status": "FILLED",
                "filled_qty": 0.001,
                "avg_price": 70000.0
            }
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        try:
            symbol = order_request["symbol"]
            side = order_request["side"]
            quantity = order_request["quantity"]
            order_type = order_request.get("order_type", "MARKET")
            
            # Round quantity to 3 decimals (Binance precision)
            quantity = round(quantity, 3)
            
            logger.info(f"[BinanceFuturesAdapter] Placing order: {symbol} {side} {quantity} {order_type}")
            
            # Place order
            response = self.client.new_order(
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=quantity
            )
            
            logger.info(f"[BinanceFuturesAdapter] Order placed: {response}")
            
            return {
                "order_id": f"futures_{response['orderId']}",
                "exchange_order_id": str(response["orderId"]),
                "status": response.get("status", "NEW"),
                "filled_qty": float(response.get("executedQty", 0)),
                "avg_price": float(response.get("avgPrice", 0)) if response.get("avgPrice") else 0.0,
                "raw": response
            }
        
        except ClientError as e:
            logger.error(f"[BinanceFuturesAdapter] Order failed: {e.error_message}")
            raise RuntimeError(f"Order failed: {e.error_message}")
        
        except Exception as e:
            logger.error(f"[BinanceFuturesAdapter] Order failed: {e}")
            raise RuntimeError(f"Order failed: {e}")
    
    async def get_order(self, symbol: str, order_id: str) -> Optional[dict]:
        """
        Get order status.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        try:
            response = self.client.query_order(
                symbol=symbol,
                orderId=int(order_id)
            )
            
            return {
                "order_id": str(response["orderId"]),
                "status": response["status"],
                "filled_qty": float(response.get("executedQty", 0)),
                "avg_price": float(response.get("avgPrice", 0)) if response.get("avgPrice") else 0.0
            }
        
        except Exception as e:
            logger.error(f"[BinanceFuturesAdapter] Get order failed: {e}")
            return None
    
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel order.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        try:
            self.client.cancel_order(
                symbol=symbol,
                orderId=int(order_id)
            )
            logger.info(f"[BinanceFuturesAdapter] Order cancelled: {order_id}")
            return True
        
        except Exception as e:
            logger.error(f"[BinanceFuturesAdapter] Cancel order failed: {e}")
            return False
    
    def set_leverage(self, symbol: str, leverage: int = 5) -> bool:
        """
        Set leverage for symbol.
        """
        try:
            self.client.change_leverage(
                symbol=symbol,
                leverage=leverage
            )
            logger.info(f"[BinanceFuturesAdapter] Leverage set: {symbol} = {leverage}x")
            return True
        
        except Exception as e:
            logger.error(f"[BinanceFuturesAdapter] Set leverage failed: {e}")
            return False
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> list[Order]:
        """
        Get open orders.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        try:
            if symbol:
                orders_data = self.client.get_orders(symbol=symbol)
            else:
                orders_data = []
            
            orders = []
            for order in orders_data:
                if order["status"] in ["NEW", "PARTIALLY_FILLED"]:
                    orders.append(Order(
                        order_id=str(order["orderId"]),
                        exchange_order_id=str(order["orderId"]),
                        symbol=order["symbol"],
                        side=order["side"],
                        order_type=order["type"],
                        quantity=float(order["origQty"]),
                        filled_quantity=float(order["executedQty"]),
                        price=float(order["price"]) if order.get("price") else None,
                        avg_price=float(order["avgPrice"]) if order.get("avgPrice") else None,
                        status=order["status"],
                        created_at=datetime.fromtimestamp(order["time"] / 1000, tz=timezone.utc),
                        updated_at=datetime.fromtimestamp(order["updateTime"] / 1000, tz=timezone.utc)
                    ))
            
            return orders
        
        except Exception as e:
            logger.error(f"[BinanceFuturesAdapter] Get open orders failed: {e}")
            return []
    
    async def get_order_history(self, symbol: Optional[str] = None, limit: int = 100) -> list[Order]:
        """
        Get order history.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        # For now, return empty - can implement later if needed
        return []
    
    async def get_fills(self, symbol: Optional[str] = None, limit: int = 100) -> list[Fill]:
        """
        Get recent fills.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        # For now, return empty - can implement later if needed
        return []
    
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """
        Cancel all open orders.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        try:
            if symbol:
                self.client.cancel_open_orders(symbol=symbol)
                logger.info(f"[BinanceFuturesAdapter] All orders cancelled for {symbol}")
                return 1  # Binance API doesn't return count
            else:
                logger.warning("[BinanceFuturesAdapter] Cancel all orders requires symbol")
                return 0
        
        except Exception as e:
            logger.error(f"[BinanceFuturesAdapter] Cancel all orders failed: {e}")
            return 0
    
    async def get_mark_price(self, symbol: str) -> float:
        """
        Get current mark price.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        try:
            ticker = self.client.mark_price(symbol=symbol)
            return float(ticker["markPrice"])
        
        except Exception as e:
            logger.error(f"[BinanceFuturesAdapter] Get mark price failed: {e}")
            return 0.0
    
    async def sync_state(self) -> Dict[str, Any]:
        """
        Sync exchange state.
        """
        if not self.connected:
            raise RuntimeError("Adapter not connected")
        
        try:
            balances = await self.get_balances()
            positions = await self.get_positions()
            open_orders = await self.get_open_orders()
            
            return {
                "balances": [b.__dict__ for b in balances],
                "positions": [p.__dict__ for p in positions],
                "open_orders": [o.__dict__ for o in open_orders]
            }
        
        except Exception as e:
            logger.error(f"[BinanceFuturesAdapter] Sync state failed: {e}")
            return {"balances": [], "positions": [], "open_orders": []}
    
    def close_position(self, symbol: str) -> dict:
        """
        Close position for symbol (MARKET order with reduceOnly).
        
        Returns:
            {"ok": bool, "exchange_order_id": str, "status": str}
        """
        if not self.connected:
            return {"ok": False, "error": "Adapter not connected"}
        
        try:
            # Get current position
            positions_data = self.client.get_position_risk(symbol=symbol)
            
            if not positions_data:
                return {"ok": False, "error": "NO_POSITION_DATA"}
            
            pos = positions_data[0]
            position_amt = float(pos.get("positionAmt", 0))
            
            if position_amt == 0:
                return {"ok": False, "error": "NO_OPEN_POSITION"}
            
            # Determine close side (opposite of position)
            side = "SELL" if position_amt > 0 else "BUY"
            quantity = abs(position_amt)
            
            # Round quantity
            quantity = round(quantity, 3)
            
            logger.info(f"[BinanceFuturesAdapter] Closing position: {symbol} {side} {quantity}")
            
            # Place MARKET order with reduceOnly
            response = self.client.new_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=quantity,
                reduceOnly=True  # CRITICAL: ensures this only closes position
            )
            
            logger.info(f"[BinanceFuturesAdapter] Position closed: {response}")
            
            return {
                "ok": True,
                "exchange_order_id": str(response.get("orderId")),
                "status": response.get("status"),
                "raw": response
            }
        
        except ClientError as e:
            logger.error(f"[BinanceFuturesAdapter] Close position failed: {e.error_message}")
            return {"ok": False, "error": e.error_message}
        
        except Exception as e:
            logger.error(f"[BinanceFuturesAdapter] Close position failed: {e}")
            return {"ok": False, "error": str(e)}
    
    def _get_reduce_side(self, position_side: str) -> str:
        """Helper: get side for closing position"""
        return "SELL" if position_side == "LONG" else "BUY"
    
    def get_position(self, symbol: str) -> Optional[dict]:
        """
        Get single position by symbol (sync method for control operations).
        
        Returns:
            Position dict or None
        """
        try:
            positions_data = self.client.get_position_risk(symbol=symbol)
            
            if not positions_data:
                return None
            
            pos = positions_data[0]
            position_amt = float(pos.get("positionAmt", 0))
            
            if position_amt == 0:
                return None
            
            entry_price = float(pos.get("entryPrice", 0))
            mark_price = float(pos.get("markPrice", 0))
            unrealized_pnl = float(pos.get("unRealizedProfit", 0))
            qty = abs(position_amt)
            
            return {
                "symbol": pos["symbol"],
                "side": "LONG" if position_amt > 0 else "SHORT",
                "qty": qty,
                "entry_price": entry_price,
                "mark_price": mark_price,
                "unrealized_pnl": unrealized_pnl,
                "leverage": int(pos.get("leverage", 1)),
            }
        
        except Exception as e:
            logger.error(f"[BinanceFuturesAdapter] Get position failed: {e}")
            return None
    
    def place_take_profit(self, symbol: str, stop_price: float) -> dict:
        """
        Place Take Profit order (TAKE_PROFIT_MARKET with closePosition).
        
        Args:
            symbol: Trading pair
            stop_price: Price to trigger TP
        
        Returns:
            {"ok": bool, "order_id": str}
        """
        if not self.connected:
            return {"ok": False, "error": "Adapter not connected"}
        
        try:
            pos = self.get_position(symbol)
            if not pos:
                return {"ok": False, "error": "NO_POSITION"}
            
            side = self._get_reduce_side(pos["side"])
            
            logger.info(f"[BinanceFuturesAdapter] Placing TP: {symbol} {side} @ {stop_price}")
            
            response = self.client.new_order(
                symbol=symbol,
                side=side,
                type="TAKE_PROFIT_MARKET",
                stopPrice=stop_price,
                closePosition="true",  # Close entire position
                workingType="MARK_PRICE",  # Use mark price for trigger
                # NOTE: reduceOnly not needed when closePosition=true
            )
            
            logger.info(f"[BinanceFuturesAdapter] TP placed: {response.get('orderId')}")
            
            return {
                "ok": True,
                "order_id": str(response.get("orderId")),
                "raw": response
            }
        
        except ClientError as e:
            logger.error(f"[BinanceFuturesAdapter] Place TP failed: {e.error_message}")
            return {"ok": False, "error": e.error_message}
        
        except Exception as e:
            logger.error(f"[BinanceFuturesAdapter] Place TP failed: {e}")
            return {"ok": False, "error": str(e)}
    
    def place_stop_loss(self, symbol: str, stop_price: float) -> dict:
        """
        Place Stop Loss order (STOP_MARKET with closePosition).
        
        Args:
            symbol: Trading pair
            stop_price: Price to trigger SL
        
        Returns:
            {"ok": bool, "order_id": str}
        """
        if not self.connected:
            return {"ok": False, "error": "Adapter not connected"}
        
        try:
            pos = self.get_position(symbol)
            if not pos:
                return {"ok": False, "error": "NO_POSITION"}
            
            side = self._get_reduce_side(pos["side"])
            
            logger.info(f"[BinanceFuturesAdapter] Placing SL: {symbol} {side} @ {stop_price}")
            
            response = self.client.new_order(
                symbol=symbol,
                side=side,
                type="STOP_MARKET",
                stopPrice=stop_price,
                closePosition="true",  # Close entire position
                workingType="MARK_PRICE",  # Use mark price for trigger
                # NOTE: reduceOnly not needed when closePosition=true
            )
            
            logger.info(f"[BinanceFuturesAdapter] SL placed: {response.get('orderId')}")
            
            return {
                "ok": True,
                "order_id": str(response.get("orderId")),
                "raw": response
            }
        
        except ClientError as e:
            logger.error(f"[BinanceFuturesAdapter] Place SL failed: {e.error_message}")
            return {"ok": False, "error": e.error_message}
        
        except Exception as e:
            logger.error(f"[BinanceFuturesAdapter] Place SL failed: {e}")
            return {"ok": False, "error": str(e)}
    
    def get_open_protective_orders(self, symbol: str) -> list:
        """
        Get open TP/SL orders for symbol.
        
        Returns:
            List of protective orders
        """
        if not self.connected:
            return []
        
        try:
            orders = self.client.get_open_orders(symbol=symbol)
            protective_types = {"STOP_MARKET", "TAKE_PROFIT_MARKET", "STOP", "TAKE_PROFIT"}
            
            protective_orders = [
                o for o in orders
                if o.get("type") in protective_types
            ]
            
            return protective_orders
        
        except Exception as e:
            logger.error(f"[BinanceFuturesAdapter] Get protective orders failed: {e}")
            return []
    
    def cancel_protective_orders(self, symbol: str) -> dict:
        """
        Cancel all TP/SL orders for symbol.
        
        Returns:
            {"ok": bool, "count": int}
        """
        if not self.connected:
            return {"ok": False, "error": "Adapter not connected"}
        
        try:
            orders = self.client.get_open_orders(symbol=symbol)
            protective_types = {"STOP_MARKET", "TAKE_PROFIT_MARKET", "STOP", "TAKE_PROFIT"}
            
            canceled = []
            for o in orders:
                if o.get("type") not in protective_types:
                    continue
                
                res = self.client.cancel_order(
                    symbol=symbol,
                    orderId=o["orderId"]
                )
                canceled.append(res)
                logger.info(f"[BinanceFuturesAdapter] Canceled protective order: {o['orderId']}")
            
            return {"ok": True, "count": len(canceled), "orders": canceled}
        
        except ClientError as e:
            logger.error(f"[BinanceFuturesAdapter] Cancel protective orders failed: {e.error_message}")
            return {"ok": False, "error": e.error_message}
        
        except Exception as e:
            logger.error(f"[BinanceFuturesAdapter] Cancel protective orders failed: {e}")
            return {"ok": False, "error": str(e)}
    
    # ========================================================================
    # A6 — POSITION CONTROL LAYER
    # ========================================================================
    
    def _normalize_qty(self, qty: float, precision: int = 3) -> float:
        """
        Normalize quantity to avoid precision errors.
        
        Args:
            qty: Raw quantity
            precision: Decimal places (default 3 for BTC, ETH)
        
        Returns:
            Normalized quantity
        """
        if qty <= 0:
            return 0.0
        factor = 10 ** precision
        return math.floor(qty * factor) / factor
    
    def open_position(self, symbol: str, side: str, qty: float) -> dict:
        """
        Open new position.
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            side: BUY or SELL
            qty: Absolute quantity
        
        Returns:
            {"ok": bool, "exchange_order_id": str, "status": str}
        """
        if not self.connected:
            return {"ok": False, "error": "Adapter not connected"}
        
        try:
            qty = self._normalize_qty(qty)
            if qty <= 0:
                return {"ok": False, "error": "INVALID_QTY"}
            
            logger.info(f"[A6] Opening position: {symbol} {side} {qty}")
            
            response = self.client.new_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=qty,
            )
            
            logger.info(f"[A6] Position opened: {response.get('orderId')}")
            
            return {
                "ok": True,
                "exchange_order_id": str(response.get("orderId")),
                "status": response.get("status"),
                "raw": response,
            }
        
        except ClientError as e:
            logger.error(f"[A6] open_position error: {e.error_message}")
            return {"ok": False, "error": e.error_message}
        
        except Exception as e:
            logger.error(f"[A6] open_position error: {e}")
            return {"ok": False, "error": str(e)}
    
    def reduce_position(self, symbol: str, percent: float) -> dict:
        """
        Reduce position by percentage.
        
        Args:
            symbol: Trading pair
            percent: Reduction percentage (25, 50, 100)
        
        Returns:
            {"ok": bool, "reduced_qty": float, "exchange_order_id": str}
        """
        if not self.connected:
            return {"ok": False, "error": "Adapter not connected"}
        
        try:
            pos = self.get_position(symbol)
            if not pos:
                return {"ok": False, "error": "NO_POSITION"}
            
            if percent <= 0 or percent > 100:
                return {"ok": False, "error": "INVALID_PERCENT"}
            
            reduce_qty = pos["qty"] * (percent / 100.0)
            reduce_qty = self._normalize_qty(reduce_qty)
            
            if reduce_qty <= 0:
                return {"ok": False, "error": "REDUCE_QTY_TOO_SMALL"}
            
            side = "SELL" if pos["side"] == "LONG" else "BUY"
            
            logger.info(f"[A6] Reducing position: {symbol} by {percent}% ({reduce_qty} {side})")
            
            response = self.client.new_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=reduce_qty,
                reduceOnly=True,
            )
            
            logger.info(f"[A6] Position reduced: {response.get('orderId')}")
            
            return {
                "ok": True,
                "exchange_order_id": str(response.get("orderId")),
                "status": response.get("status"),
                "reduced_qty": reduce_qty,
                "raw": response,
            }
        
        except ClientError as e:
            logger.error(f"[A6] reduce_position error: {e.error_message}")
            return {"ok": False, "error": e.error_message}
        
        except Exception as e:
            logger.error(f"[A6] reduce_position error: {e}")
            return {"ok": False, "error": str(e)}
    
    def reverse_position(self, symbol: str) -> dict:
        """
        Reverse position (close current → open opposite).
        
        CRITICAL: This is done in 2 steps:
        1. Close current position with reduceOnly
        2. Open opposite position
        
        Args:
            symbol: Trading pair
        
        Returns:
            {"ok": bool, "closed": dict, "opened": dict}
        """
        if not self.connected:
            return {"ok": False, "error": "Adapter not connected"}
        
        try:
            pos = self.get_position(symbol)
            if not pos:
                return {"ok": False, "error": "NO_POSITION"}
            
            qty = self._normalize_qty(pos["qty"])
            if qty <= 0:
                return {"ok": False, "error": "INVALID_QTY"}
            
            logger.info(f"[A6] Reversing position: {symbol} {pos['side']} → opposite")
            
            # Step 1: Close current position
            close_side = "SELL" if pos["side"] == "LONG" else "BUY"
            
            close_res = self.client.new_order(
                symbol=symbol,
                side=close_side,
                type="MARKET",
                quantity=qty,
                reduceOnly=True,
            )
            
            logger.info(f"[A6] Closed position: {close_res.get('orderId')}")
            
            # Step 2: Open opposite position
            # LONG → SHORT (open with SELL)
            # SHORT → LONG (open with BUY)
            open_side = "SELL" if pos["side"] == "LONG" else "BUY"
            
            open_res = self.client.new_order(
                symbol=symbol,
                side=open_side,
                type="MARKET",
                quantity=qty,
            )
            
            logger.info(f"[A6] Opened opposite position: {open_res.get('orderId')}")
            
            return {
                "ok": True,
                "closed": close_res,
                "opened": open_res,
            }
        
        except ClientError as e:
            logger.error(f"[A6] reverse_position error: {e.error_message}")
            return {"ok": False, "error": e.error_message}
        
        except Exception as e:
            logger.error(f"[A6] reverse_position error: {e}")
            return {"ok": False, "error": str(e)}
    
    def flatten_all(self) -> dict:
        """
        Close all open positions (PANIC BUTTON).
        
        Returns:
            {"ok": bool, "count": int, "results": list}
        """
        if not self.connected:
            return {"ok": False, "error": "Adapter not connected"}
        
        try:
            # Get positions synchronously via Binance API
            positions_data = self.client.get_position_risk()
            
            # Filter only open positions
            open_positions = []
            for p in positions_data:
                position_amt = float(p.get("positionAmt", 0))
                if position_amt != 0:
                    side = "LONG" if position_amt > 0 else "SHORT"
                    open_positions.append({
                        "symbol": p["symbol"],
                        "side": side,
                        "qty": abs(position_amt)
                    })
            
            results = []
            
            logger.info(f"[A6] Flattening all positions ({len(open_positions)} total)")
            
            for pos in open_positions:
                qty = self._normalize_qty(pos["qty"])
                if qty <= 0:
                    continue
                
                side = "SELL" if pos["side"] == "LONG" else "BUY"
                
                res = self.client.new_order(
                    symbol=pos["symbol"],
                    side=side,
                    type="MARKET",
                    quantity=qty,
                    reduceOnly=True,
                )
                
                results.append({
                    "symbol": pos["symbol"],
                    "response": res,
                })
                
                logger.info(f"[A6] Flattened: {pos['symbol']}")
            
            logger.info(f"[A6] All positions flattened: {len(results)} closed")
            
            return {
                "ok": True,
                "count": len(results),
                "results": results,
            }
        
        except ClientError as e:
            logger.error(f"[A6] flatten_all error: {e.error_message}")
            return {"ok": False, "error": e.error_message}
        
        except Exception as e:
            logger.error(f"[A6] flatten_all error: {e}")
            return {"ok": False, "error": str(e)}
