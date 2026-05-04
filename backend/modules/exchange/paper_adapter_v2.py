"""
Paper Exchange Adapter — Unified Protocol Version

Simulates exchange execution with production-grade realism.
Implements unified ExchangeAdapter protocol.
"""

import uuid
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging

from motor.motor_asyncio import AsyncIOMotorClient

from .base import ExchangeAdapter
from .models import (
    AccountInfo,
    Balance,
    Position,
    Order,
    Fill,
    OrderRequest,
)

logger = logging.getLogger(__name__)


class PaperExchangeAdapter(ExchangeAdapter):
    """Paper trading adapter (simulated execution)."""

    def __init__(self, config: dict, db_client: AsyncIOMotorClient):
        self.db = db_client.trading_db
        self.account_id = config.get("account_id", "paper_default")
        self.initial_balance = config.get("initial_balance", 10000.0)
        self.connected = False
        
        # CRITICAL: Position tracking
        self.positions: Dict[str, Position] = {}  # key = symbol

    async def connect(self) -> bool:
        """Initialize paper account."""
        account = await self.db.exchange_accounts.find_one({"account_id": self.account_id})
        
        if not account:
            await self.db.exchange_accounts.insert_one({
                "account_id": self.account_id,
                "exchange": "PAPER",
                "account_type": "SPOT",
                "balance_usdt": self.initial_balance,
                "equity": self.initial_balance,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })
            logger.info(f"[PaperAdapter] Created account {self.account_id} with ${self.initial_balance}")
        
        self.connected = True
        
        # Load persisted positions from DB into in-memory dict
        try:
            db_positions = await self.db.exchange_positions.find(
                {"account_id": self.account_id, "status": "OPEN"}
            ).to_list(length=100)
            for p in db_positions:
                symbol = p.get("symbol")
                if symbol and symbol not in self.positions:
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        side=p.get("side", "LONG"),
                        qty=p.get("qty", p.get("size", 0)),
                        entry_price=p.get("entry_price", 0),
                        mark_price=p.get("mark_price", p.get("entry_price", 0)),
                        unrealized_pnl=p.get("unrealized_pnl", 0),
                        unrealized_pnl_pct=p.get("unrealized_pnl_pct", 0),
                        realized_pnl=p.get("realized_pnl", 0),
                        leverage=p.get("leverage", 1),
                        status="OPEN",
                        liquidation_price=p.get("liquidation_price"),
                        opened_at=p.get("opened_at"),
                    )
            if self.positions:
                logger.info(f"[PaperAdapter] Loaded {len(self.positions)} positions from DB")
        except Exception as e:
            logger.warning(f"[PaperAdapter] Failed to load positions from DB: {e}")
        
        return True

    async def get_account_info(self) -> AccountInfo:
        """Get normalized account info."""
        account = await self.db.exchange_accounts.find_one({"account_id": self.account_id})
        
        if not account:
            raise ValueError(f"Account {self.account_id} not found")
        
        return AccountInfo(
            account_id=self.account_id,
            exchange="paper",
            account_type="SPOT",
            status="ACTIVE",
            can_trade=True,
            can_withdraw=False,
            can_deposit=False,
            created_at=account.get("created_at"),
        )

    async def get_balances(self) -> List[Balance]:
        """Get normalized balances."""
        account = await self.db.exchange_accounts.find_one({"account_id": self.account_id})
        
        if not account:
            return []
        
        return [
            Balance(
                asset="USDT",
                free=account["balance_usdt"],
                locked=0.0,
                total=account["balance_usdt"],
            )
        ]

    async def _persist_position(self, pos: Position):
        """Persist position state to DB for restart recovery."""
        try:
            await self.db.exchange_positions.update_one(
                {"account_id": self.account_id, "symbol": pos.symbol},
                {"$set": {
                    "account_id": self.account_id,
                    "symbol": pos.symbol, "side": pos.side,
                    "qty": pos.qty, "entry_price": pos.entry_price,
                    "mark_price": pos.mark_price,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                    "realized_pnl": pos.realized_pnl,
                    "leverage": pos.leverage, "status": pos.status,
                    "liquidation_price": pos.liquidation_price,
                }},
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"[PaperAdapter] Failed to persist position {pos.symbol}: {e}")

    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get normalized positions."""
        positions = list(self.positions.values())
        
        if symbol:
            positions = [p for p in positions if p.symbol == symbol]
        
        return positions

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get normalized open orders."""
        query = {
            "account_id": self.account_id,
            "status": {"$in": ["NEW", "PARTIALLY_FILLED"]}
        }
        
        if symbol:
            query["symbol"] = symbol
        
        orders = await self.db.exchange_orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(length=100)
        
        return [self._normalize_order(order) for order in orders]

    async def get_order_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[Order]:
        """Get normalized order history."""
        query = {"account_id": self.account_id}
        
        if symbol:
            query["symbol"] = symbol
        
        orders = await self.db.exchange_orders.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(length=limit)
        
        return [self._normalize_order(order) for order in orders]

    async def get_fills(self, symbol: Optional[str] = None, limit: int = 100) -> List[Fill]:
        """Get normalized fills."""
        query = {"account_id": self.account_id}
        
        if symbol:
            query["symbol"] = symbol
        
        fills = await self.db.exchange_fills.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(length=limit)
        
        return [self._normalize_fill(fill) for fill in fills]

    async def place_order(self, order_request: Dict[str, Any]) -> Order:
        """
        Place a new order (simulated execution with position tracking).
        """
        order_id = f"paper-{uuid.uuid4().hex[:12]}"
        client_order_id = order_request.get("client_order_id", order_id)
        
        symbol = order_request["symbol"]
        side = order_request["side"]
        qty = order_request["quantity"]
        
        # Get current price (mock for now)
        price = order_request.get("price", await self.get_mark_price(symbol))
        
        # Create order document
        order_doc = {
            "account_id": self.account_id,
            "order_id": order_id,
            "client_order_id": client_order_id,
            "symbol": symbol,
            "side": side,
            "type": order_request["type"],
            "price": price,
            "qty": qty,
            "filled_qty": qty if order_request["type"] == "MARKET" else 0.0,
            "remaining_qty": 0.0 if order_request["type"] == "MARKET" else qty,
            "status": "FILLED" if order_request["type"] == "MARKET" else "NEW",
            "time_in_force": order_request.get("time_in_force", "GTC"),
            "reduce_only": order_request.get("reduce_only", False),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        await self.db.exchange_orders.insert_one(order_doc.copy())
        
        # Create fill if market order
        if order_request["type"] == "MARKET":
            fill_doc = {
                "account_id": self.account_id,
                "fill_id": f"fill-{uuid.uuid4().hex[:12]}",
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "price": price,
                "qty": qty,
                "quote_qty": price * qty,
                "fee": (price * qty) * 0.001,  # 0.1% fee
                "fee_asset": "USDT",
                "is_maker": False,
                "timestamp": datetime.now(timezone.utc),
            }
            
            await self.db.exchange_fills.insert_one(fill_doc)
            
            # CRITICAL: Update positions
            await self._update_position(symbol, side, qty, price)
        
        order_doc.pop("_id", None)
        return self._normalize_order(order_doc)
    
    async def _update_position(self, symbol: str, side: str, qty: float, price: float):
        """
        Update position tracking.
        
        BUY → increase/create LONG position
        SELL → decrease/close LONG position (or create SHORT)
        """
        logger.info(f"[PaperAdapter] Updating position: {symbol} {side} {qty} @ ${price}")
        
        if side == "BUY":
            # Open or add to LONG position
            if symbol in self.positions:
                pos = self.positions[symbol]
                
                # Calculate new average entry price
                total_qty = pos.qty + qty
                new_entry_price = ((pos.entry_price * pos.qty) + (price * qty)) / total_qty
                
                pos.qty = total_qty
                pos.entry_price = new_entry_price
                pos.mark_price = price
                
                # Recalculate PnL
                pos.unrealized_pnl = (pos.mark_price - pos.entry_price) * pos.qty
                pos.unrealized_pnl_pct = (pos.unrealized_pnl / (pos.entry_price * pos.qty)) * 100
                
                logger.info(f"[PaperAdapter] Increased LONG position: {symbol} qty={pos.qty} avg_entry=${pos.entry_price:.2f}")
            else:
                # Create new LONG position
                self.positions[symbol] = Position(
                    symbol=symbol,
                    side="LONG",
                    qty=qty,
                    entry_price=price,
                    mark_price=price,
                    unrealized_pnl=0.0,
                    unrealized_pnl_pct=0.0,
                    realized_pnl=0.0,
                    leverage=1.0,
                    status="OPEN",
                    opened_at=datetime.now(timezone.utc),
                )
                logger.info(f"[PaperAdapter] Created LONG position: {symbol} qty={qty} entry=${price}")
                await self._persist_position(self.positions[symbol])
        
        elif side == "SELL":
            # Reduce or close LONG position
            if symbol in self.positions:
                pos = self.positions[symbol]
                
                if pos.side == "LONG":
                    # Calculate realized PnL before closing
                    realized_pnl_partial = (price - pos.entry_price) * min(qty, pos.qty)
                    pos.realized_pnl += realized_pnl_partial
                    
                    # Reduce position
                    pos.qty -= qty
                    
                    if pos.qty <= 0:
                        # Position fully closed
                        logger.info(f"[PaperAdapter] Closed LONG position: {symbol} realized_pnl=${pos.realized_pnl:.2f}")
                        try:
                            await self.db.exchange_positions.update_one(
                                {"account_id": self.account_id, "symbol": symbol},
                                {"$set": {"status": "CLOSED"}},
                            )
                        except Exception:
                            pass
                        del self.positions[symbol]
                    else:
                        # Position partially closed
                        pos.mark_price = price
                        pos.unrealized_pnl = (pos.mark_price - pos.entry_price) * pos.qty
                        pos.unrealized_pnl_pct = (pos.unrealized_pnl / (pos.entry_price * pos.qty)) * 100
                        logger.info(f"[PaperAdapter] Reduced LONG position: {symbol} qty={pos.qty} unrealized_pnl=${pos.unrealized_pnl:.2f}")
                        await self._persist_position(pos)
                else:
                    # TODO: Handle SHORT position (add to SHORT)
                    logger.warning(f"[PaperAdapter] SHORT position handling not implemented yet")
            else:
                # TODO: Create SHORT position
                logger.warning(f"[PaperAdapter] Opening SHORT position not implemented yet")

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """Cancel an order."""
        query = {
            "account_id": self.account_id,
            "order_id": order_id,
        }
        
        if symbol:
            query["symbol"] = symbol
        
        result = await self.db.exchange_orders.update_one(
            query,
            {"$set": {
                "status": "CANCELED",
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        return result.modified_count > 0

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """Cancel all open orders."""
        query = {
            "account_id": self.account_id,
            "status": {"$in": ["NEW", "PARTIALLY_FILLED"]}
        }
        
        if symbol:
            query["symbol"] = symbol
        
        result = await self.db.exchange_orders.update_many(
            query,
            {"$set": {
                "status": "CANCELED",
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        return result.modified_count

    def _symbol_to_coinbase(self, symbol: str) -> str:
        """Convert BTCUSDT → BTC-USD for Coinbase API."""
        mapping = {
            "BTCUSDT": "BTC-USD", "ETHUSDT": "ETH-USD", "SOLUSDT": "SOL-USD",
            "BNBUSDT": "BNB-USD", "XRPUSDT": "XRP-USD", "ADAUSDT": "ADA-USD",
            "AVAXUSDT": "AVAX-USD", "LINKUSDT": "LINK-USD", "DOGEUSDT": "DOGE-USD",
        }
        return mapping.get(symbol, symbol.replace("USDT", "-USD"))

    async def get_mark_price(self, symbol: str) -> float:
        """
        Get current mark price from Coinbase (real market price).
        Falls back to position mark_price or cached price if API fails.
        """
        # Try Coinbase first for REAL price
        try:
            from modules.data.coinbase_provider import CoinbaseProvider
            provider = CoinbaseProvider()
            coinbase_symbol = self._symbol_to_coinbase(symbol)
            ticker = await provider.get_ticker(coinbase_symbol)
            if ticker and ticker.get("price", 0) > 0:
                return float(ticker["price"])
        except Exception as e:
            logger.debug(f"[PaperAdapter] Coinbase price failed for {symbol}: {e}")
        
        # Fallback: use position's last mark price
        if symbol in self.positions:
            return self.positions[symbol].mark_price
        
        # Last resort: try PriceService (simulated)
        try:
            from modules.market_data.price_service import get_price_service
            svc = await get_price_service()
            return await svc.get_mark_price(symbol)
        except Exception:
            pass
        
        return 0.0
    
    async def update_mark_prices(self):
        """
        Update mark prices for all open positions using REAL Coinbase prices.
        """
        # Batch fetch real prices for all position symbols
        real_prices = {}
        try:
            from modules.data.coinbase_provider import CoinbaseProvider
            provider = CoinbaseProvider()
            for symbol in list(self.positions.keys()):
                try:
                    coinbase_symbol = self._symbol_to_coinbase(symbol)
                    ticker = await provider.get_ticker(coinbase_symbol)
                    if ticker and ticker.get("price", 0) > 0:
                        real_prices[symbol] = float(ticker["price"])
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"[PaperAdapter] Failed to fetch Coinbase prices: {e}")
        
        for symbol, pos in self.positions.items():
            if symbol in real_prices:
                pos.mark_price = real_prices[symbol]
            
            # Recalculate unrealized PnL
            if pos.side == "LONG":
                pos.unrealized_pnl = (pos.mark_price - pos.entry_price) * pos.qty
            elif pos.side == "SHORT":
                pos.unrealized_pnl = (pos.entry_price - pos.mark_price) * pos.qty
            
            # Calculate unrealized PnL %
            if pos.entry_price > 0:
                pos.unrealized_pnl_pct = (pos.unrealized_pnl / (pos.entry_price * pos.qty)) * 100
            
            # Persist updated position
            await self._persist_position(pos)
            
            logger.debug(f"[PaperAdapter] Updated {symbol}: mark=${pos.mark_price:.2f} pnl=${pos.unrealized_pnl:.2f}")

    async def sync_state(self) -> Dict[str, Any]:
        """
        Sync exchange state.
        
        Updates mark prices and PnL for all positions.
        """
        # Update mark prices for all positions
        await self.update_mark_prices()
        
        balances = await self.get_balances()
        positions = await self.get_positions()
        open_orders = await self.get_open_orders()
        
        return {
            "balances": [b.dict() for b in balances],
            "positions": [p.dict() for p in positions],
            "open_orders": [o.dict() for o in open_orders],
        }

    # Helper methods
    
    def _normalize_order(self, order_doc: dict) -> Order:
        """Convert DB order document to normalized Order model."""
        return Order(
            order_id=order_doc["order_id"],
            client_order_id=order_doc.get("client_order_id"),
            symbol=order_doc["symbol"],
            side=order_doc["side"],
            type=order_doc["type"],
            price=order_doc["price"],
            stop_price=order_doc.get("stop_price"),
            qty=order_doc["qty"],
            filled_qty=order_doc["filled_qty"],
            remaining_qty=order_doc["remaining_qty"],
            status=order_doc["status"],
            time_in_force=order_doc.get("time_in_force", "GTC"),
            reduce_only=order_doc.get("reduce_only", False),
            created_at=order_doc["created_at"],
            updated_at=order_doc.get("updated_at"),
        )
    
    def _normalize_fill(self, fill_doc: dict) -> Fill:
        """Convert DB fill document to normalized Fill model."""
        return Fill(
            fill_id=fill_doc["fill_id"],
            order_id=fill_doc["order_id"],
            symbol=fill_doc["symbol"],
            side=fill_doc["side"],
            price=fill_doc["price"],
            qty=fill_doc["qty"],
            quote_qty=fill_doc.get("quote_qty", fill_doc["price"] * fill_doc["qty"]),
            fee=fill_doc["fee"],
            fee_asset=fill_doc.get("fee_asset", "USDT"),
            is_maker=fill_doc.get("is_maker", False),
            timestamp=fill_doc["timestamp"],
        )
