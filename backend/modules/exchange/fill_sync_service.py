"""Fill Sync Service — Сердце real exchange integration

Polling fills from exchange → apply to portfolio → emit events.

CRITICAL:
- Deduplication (no duplicate fills)
- Idempotent (safe to run multiple times)
- Restart-safe (persists state in MongoDB)

Usage:
    sync = FillSyncService(adapter, db, portfolio, events)
    await sync.start()  # Background loop
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class FillSyncService:
    """Fill sync service for real exchange integration.
    
    Polls exchange for fills every 3-5s and syncs to portfolio.
    """
    
    def __init__(
        self,
        adapter,
        db,
        portfolio_service,
        events_service,
        sync_interval: float = 3.0
    ):
        """Initialize fill sync service.
        
        Args:
            adapter: Exchange adapter (e.g., BinanceTestnetAdapter)
            db: MongoDB database handle
            portfolio_service: Portfolio service instance
            events_service: Events service instance
            sync_interval: Polling interval in seconds (default 3s)
        """
        self.adapter = adapter
        self.db = db
        self.portfolio = portfolio_service
        self.events = events_service
        self.sync_interval = sync_interval
        
        self.running = False
        self.task = None
        
        # Symbols to sync (from config or dynamic)
        self.symbols = ["BTCUSDT", "ETHUSDT"]
    
    async def start(self):
        """Start fill sync loop in background."""
        if self.running:
            logger.warning("[FillSync] Already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info(f"[FillSync] Started (interval={self.sync_interval}s)")
    
    async def stop(self):
        """Stop fill sync loop."""
        if not self.running:
            return
        
        self.running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("[FillSync] Stopped")
    
    async def _run(self):
        """Main sync loop."""
        while self.running:
            try:
                await self.sync_all_symbols()
            except Exception as e:
                logger.error(f"[FillSync] Sync error: {e}", exc_info=True)
            
            await asyncio.sleep(self.sync_interval)
    
    async def sync_all_symbols(self):
        """Sync fills for all tracked symbols."""
        for symbol in self.symbols:
            try:
                await self.sync_symbol(symbol)
            except Exception as e:
                logger.error(f"[FillSync] Error syncing {symbol}: {e}")
    
    async def sync_symbol(self, symbol: str):
        """Sync fills for single symbol.
        
        Args:
            symbol: Trading pair to sync
        """
        # Get recent fills from exchange
        try:
            trades = await self.adapter.get_recent_fills(symbol, limit=50)
        except Exception as e:
            logger.error(f"[FillSync] Failed to fetch fills for {symbol}: {e}")
            return
        
        if not trades:
            return
        
        logger.debug(f"[FillSync] {symbol}: {len(trades)} fills received")
        
        # Process each fill
        new_fills_count = 0
        
        for trade in trades:
            try:
                is_new = await self._process_fill(trade, symbol)
                if is_new:
                    new_fills_count += 1
            except Exception as e:
                logger.error(f"[FillSync] Error processing fill {trade.get('id')}: {e}")
        
        if new_fills_count > 0:
            logger.info(f"[FillSync] {symbol}: {new_fills_count} new fills applied")
    
    async def _process_fill(self, trade: dict, symbol: str) -> bool:
        """Process single fill.
        
        Args:
            trade: Trade dict from exchange
            symbol: Trading pair
        
        Returns:
            True if new fill, False if duplicate
        """
        trade_id = str(trade["id"])
        
        # DEDUPLICATION (CRITICAL)
        existing = await self.db.exchange_fills.find_one({"trade_id": trade_id})
        
        if existing:
            logger.debug(f"[FillSync] Duplicate fill: {trade_id}, skipping")
            return False
        
        # Build normalized fill record
        fill = {
            "trade_id": trade_id,
            "order_id": str(trade.get("orderId", "")),
            "symbol": symbol,
            "side": "BUY" if trade.get("isBuyer") else "SELL",
            "quantity": float(trade["qty"]),
            "price": float(trade["price"]),
            "commission": float(trade.get("commission", 0)),
            "commission_asset": trade.get("commissionAsset", ""),
            "timestamp": trade.get("time"),
            "synced_at": datetime.now(timezone.utc),
        }
        
        # 1. SAVE to MongoDB
        await self.db.exchange_fills.insert_one(fill.copy())
        
        logger.info(
            f"[FillSync] New fill: {symbol} {fill['side']} "
            f"{fill['quantity']:.6f} @ ${fill['price']:.2f}, "
            f"fee={fill['commission']:.4f}"
        )
        
        # 2. APPLY to portfolio
        try:
            await self._apply_fill_to_portfolio(fill)
        except Exception as e:
            logger.error(f"[FillSync] Failed to apply fill to portfolio: {e}")
        
        # 3. EMIT event
        try:
            await self.events.log_event("ORDER_FILLED_REAL", {
                "symbol": symbol,
                "side": fill["side"],
                "quantity": fill["quantity"],
                "price": fill["price"],
                "fee": fill["commission"],
                "trade_id": trade_id,
            })
        except Exception as e:
            logger.error(f"[FillSync] Failed to log event: {e}")
        
        return True
    
    async def _apply_fill_to_portfolio(self, fill: dict):
        """Apply fill to portfolio (update position).
        
        Args:
            fill: Fill record dict
        """
        symbol = fill["symbol"]
        side = fill["side"]
        qty = fill["quantity"] if side == "BUY" else -fill["quantity"]  # Negative for SELL
        price = fill["price"]
        fee = fill["commission"]
        
        # Find or create position
        position = await self.db.positions.find_one({
            "symbol": symbol,
            "status": "OPEN"
        })
        
        if not position:
            # Create new position
            position = {
                "symbol": symbol,
                "size": 0.0,
                "entry_price": 0.0,
                "entry_fee": 0.0,
                "mark_price": price,
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
                "status": "OPEN",
                "opened_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        
        old_size = position["size"]
        new_size = old_size + qty
        
        # Calculate new average entry price
        if new_size != 0 and abs(new_size) > abs(old_size):
            # Adding to position
            old_entry = position.get("entry_price", price)
            position["entry_price"] = (
                (old_entry * abs(old_size) + price * abs(qty)) / abs(new_size)
            )
        
        position["size"] = new_size
        position["entry_fee"] = position.get("entry_fee", 0) + fee
        position["side"] = "LONG" if new_size > 0 else "SHORT" if new_size < 0 else "FLAT"
        position["updated_at"] = datetime.now(timezone.utc)
        
        # If position closed
        if abs(new_size) < 0.0001:
            position["status"] = "CLOSED"
            position["closed_at"] = datetime.now(timezone.utc)
        
        # Update or insert
        await self.db.positions.update_one(
            {"symbol": symbol, "status": "OPEN"},
            {"$set": position},
            upsert=True
        )
        
        logger.info(
            f"[FillSync] Position updated: {symbol} size={new_size:.6f}, "
            f"entry=${position['entry_price']:.2f}, fee={position['entry_fee']:.4f}"
        )
