"""
Exchange Sync Engine

PHASE 43.2 — Order + Position Sync Engine

Exchange is the source of truth.

Sync pipeline:
Exchange API → Sync Engine → Database → Portfolio Manager update

Key features:
- Periodic sync (every 10-15 seconds)
- Position reconciliation
- Balance tracking
- Order state management
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
import os

from .sync_types import (
    SyncStatus,
    SyncType,
    SyncState,
    SyncConfig,
    ExchangePositionSync,
    ExchangeBalanceSync,
    ExchangeOrderSync,
    ExchangeFillSync,
)


class ExchangeSyncEngine:
    """
    Exchange Sync Engine — PHASE 43.2
    
    Maintains synchronized state between system and exchanges.
    Exchange is always the source of truth.
    """
    
    def __init__(self, config: Optional[SyncConfig] = None):
        self._config = config or SyncConfig()
        
        # State per exchange
        self._sync_states: Dict[str, SyncState] = {}
        
        # Cached data
        self._positions: Dict[str, List[ExchangePositionSync]] = {}
        self._balances: Dict[str, List[ExchangeBalanceSync]] = {}
        self._open_orders: Dict[str, List[ExchangeOrderSync]] = {}
        self._recent_fills: Dict[str, List[ExchangeFillSync]] = {}
        
        # Background tasks
        self._sync_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        
        # Initialize states
        for exchange in self._config.enabled_exchanges:
            self._sync_states[exchange] = SyncState(
                exchange=exchange,
                sync_interval_seconds=self._config.positions_interval_seconds,
            )
            self._positions[exchange] = []
            self._balances[exchange] = []
            self._open_orders[exchange] = []
            self._recent_fills[exchange] = []
    
    # ═══════════════════════════════════════════════════════════
    # 1. Start/Stop
    # ═══════════════════════════════════════════════════════════
    
    async def start(self):
        """Start sync engine."""
        if self._running:
            return
        
        self._running = True
        
        # Start sync tasks for each exchange
        for exchange in self._config.enabled_exchanges:
            task = asyncio.create_task(self._sync_loop(exchange))
            self._sync_tasks[exchange] = task
    
    async def stop(self):
        """Stop sync engine."""
        self._running = False
        
        # Cancel all tasks
        for task in self._sync_tasks.values():
            task.cancel()
        
        self._sync_tasks.clear()
    
    async def _sync_loop(self, exchange: str):
        """Main sync loop for an exchange."""
        while self._running:
            try:
                await self._sync_all(exchange)
            except asyncio.CancelledError:
                break
            except Exception as e:
                state = self._sync_states.get(exchange)
                if state:
                    state.last_error = str(e)
                    state.error_count += 1
            
            await asyncio.sleep(self._config.positions_interval_seconds)
    
    # ═══════════════════════════════════════════════════════════
    # 2. Sync Operations
    # ═══════════════════════════════════════════════════════════
    
    async def _sync_all(self, exchange: str):
        """Sync all data types for an exchange."""
        await self.sync_positions(exchange)
        await self.sync_balances(exchange)
        await self.sync_orders(exchange)
        await self.sync_fills(exchange)
    
    async def sync_positions(self, exchange: str) -> List[ExchangePositionSync]:
        """
        Sync positions from exchange.
        
        Exchange → System positions update.
        """
        state = self._sync_states.get(exchange)
        if not state:
            return []
        
        state.positions_status = SyncStatus.SYNCING
        
        try:
            # Get exchange adapter
            adapter = await self._get_adapter(exchange)
            if not adapter:
                state.positions_status = SyncStatus.ERROR
                state.last_error = f"Adapter not available: {exchange}"
                return []
            
            # Fetch positions
            exchange_positions = await adapter.get_positions()
            
            # Convert to sync format
            synced_positions = []
            for pos in exchange_positions:
                synced = ExchangePositionSync(
                    exchange=exchange,
                    symbol=pos.symbol.replace("USDT", ""),
                    exchange_symbol=pos.symbol,
                    side=pos.side.value,
                    size=pos.size,
                    size_usd=pos.size * pos.mark_price,
                    entry_price=pos.entry_price,
                    mark_price=pos.mark_price,
                    liquidation_price=pos.liquidation_price,
                    unrealized_pnl=pos.unrealized_pnl,
                    unrealized_pnl_pct=(pos.unrealized_pnl / (pos.size * pos.entry_price) * 100) if pos.size > 0 and pos.entry_price > 0 else 0,
                    leverage=pos.leverage,
                    margin_mode=pos.margin_mode.value,
                    margin_used=pos.margin,
                )
                synced_positions.append(synced)
            
            # Update cache
            self._positions[exchange] = synced_positions
            
            # Update state
            state.positions_status = SyncStatus.SYNCED
            state.positions_last_sync = datetime.now(timezone.utc)
            state.positions_count = len(synced_positions)
            state.updated_at = datetime.now(timezone.utc)
            
            # Persist to DB if enabled
            if self._config.persist_to_db:
                await self._persist_positions(exchange, synced_positions)
            
            # Update Portfolio Manager
            await self._update_portfolio_positions(exchange, synced_positions)
            
            return synced_positions
            
        except Exception as e:
            state.positions_status = SyncStatus.ERROR
            state.last_error = str(e)
            state.error_count += 1
            return []
    
    async def sync_balances(self, exchange: str) -> List[ExchangeBalanceSync]:
        """Sync balances from exchange."""
        state = self._sync_states.get(exchange)
        if not state:
            return []
        
        state.balances_status = SyncStatus.SYNCING
        
        try:
            adapter = await self._get_adapter(exchange)
            if not adapter:
                state.balances_status = SyncStatus.ERROR
                return []
            
            # Fetch balances
            exchange_balances = await adapter.get_balance()
            
            # Convert to sync format
            synced_balances = []
            for bal in exchange_balances:
                if bal.total > 0:  # Only non-zero balances
                    synced = ExchangeBalanceSync(
                        exchange=exchange,
                        asset=bal.asset,
                        total=bal.total,
                        available=bal.free,
                        locked=bal.locked,
                        usd_value=bal.usd_value,
                    )
                    synced_balances.append(synced)
            
            # Update cache
            self._balances[exchange] = synced_balances
            
            # Update state
            state.balances_status = SyncStatus.SYNCED
            state.balances_last_sync = datetime.now(timezone.utc)
            state.balances_count = len(synced_balances)
            
            # Persist
            if self._config.persist_to_db:
                await self._persist_balances(exchange, synced_balances)
            
            return synced_balances
            
        except Exception as e:
            state.balances_status = SyncStatus.ERROR
            state.last_error = str(e)
            return []
    
    async def sync_orders(self, exchange: str) -> List[ExchangeOrderSync]:
        """Sync open orders from exchange."""
        state = self._sync_states.get(exchange)
        if not state:
            return []
        
        state.orders_status = SyncStatus.SYNCING
        
        try:
            adapter = await self._get_adapter(exchange)
            if not adapter:
                state.orders_status = SyncStatus.ERROR
                return []
            
            # Fetch open orders
            exchange_orders = await adapter.get_open_orders()
            
            # Convert to sync format
            synced_orders = []
            for ord in exchange_orders:
                synced = ExchangeOrderSync(
                    exchange=exchange,
                    exchange_order_id=ord.exchange_order_id,
                    client_order_id=ord.client_order_id,
                    symbol=ord.symbol,
                    side=ord.side.value,
                    order_type=ord.order_type.value,
                    status=ord.status.value,
                    original_size=ord.original_size,
                    filled_size=ord.filled_size,
                    remaining_size=ord.remaining_size,
                    price=ord.price,
                    avg_fill_price=ord.avg_fill_price,
                    stop_price=ord.stop_price,
                    created_at=ord.created_at,
                    updated_at=ord.updated_at,
                )
                synced_orders.append(synced)
            
            # Update cache
            self._open_orders[exchange] = synced_orders
            
            # Update state
            state.orders_status = SyncStatus.SYNCED
            state.orders_last_sync = datetime.now(timezone.utc)
            state.open_orders_count = len(synced_orders)
            
            # Persist
            if self._config.persist_to_db:
                await self._persist_orders(exchange, synced_orders)
            
            return synced_orders
            
        except Exception as e:
            state.orders_status = SyncStatus.ERROR
            state.last_error = str(e)
            return []
    
    async def sync_fills(self, exchange: str) -> List[ExchangeFillSync]:
        """Sync recent fills from exchange."""
        state = self._sync_states.get(exchange)
        if not state:
            return []
        
        state.fills_status = SyncStatus.SYNCING
        
        try:
            # For fills we need to implement get_trades in adapters
            # For now return empty
            
            state.fills_status = SyncStatus.SYNCED
            state.fills_last_sync = datetime.now(timezone.utc)
            
            return []
            
        except Exception as e:
            state.fills_status = SyncStatus.ERROR
            state.last_error = str(e)
            return []
    
    # ═══════════════════════════════════════════════════════════
    # 3. Getters
    # ═══════════════════════════════════════════════════════════
    
    def get_positions(self, exchange: Optional[str] = None) -> List[ExchangePositionSync]:
        """Get cached positions."""
        if exchange:
            return self._positions.get(exchange, [])
        
        # All exchanges
        all_positions = []
        for positions in self._positions.values():
            all_positions.extend(positions)
        return all_positions
    
    def get_balances(self, exchange: Optional[str] = None) -> List[ExchangeBalanceSync]:
        """Get cached balances."""
        if exchange:
            return self._balances.get(exchange, [])
        
        all_balances = []
        for balances in self._balances.values():
            all_balances.extend(balances)
        return all_balances
    
    def get_open_orders(self, exchange: Optional[str] = None) -> List[ExchangeOrderSync]:
        """Get cached open orders."""
        if exchange:
            return self._open_orders.get(exchange, [])
        
        all_orders = []
        for orders in self._open_orders.values():
            all_orders.extend(orders)
        return all_orders
    
    def get_sync_state(self, exchange: str) -> Optional[SyncState]:
        """Get sync state for exchange."""
        return self._sync_states.get(exchange)
    
    def get_all_sync_states(self) -> Dict[str, SyncState]:
        """Get all sync states."""
        return self._sync_states.copy()
    
    # ═══════════════════════════════════════════════════════════
    # 4. Helper Methods
    # ═══════════════════════════════════════════════════════════
    
    async def _get_adapter(self, exchange: str):
        """Get exchange adapter."""
        try:
            from modules.exchanges import ExchangeRouter, ExchangeId
            
            router = ExchangeRouter()
            exchange_id = ExchangeId(exchange.upper())
            
            adapter = router.get_or_create_adapter(
                exchange_id=exchange_id,
                testnet=True,  # Default to testnet
            )
            
            if not adapter._connected:
                await adapter.connect()
            
            return adapter
        except Exception:
            return None
    
    async def _persist_positions(self, exchange: str, positions: List[ExchangePositionSync]):
        """Persist positions to MongoDB."""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "fomo_trading")
            
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            
            # Upsert positions
            for pos in positions:
                await db.exchange_positions.update_one(
                    {"exchange": exchange, "symbol": pos.symbol},
                    {"$set": pos.model_dump()},
                    upsert=True,
                )
            
            client.close()
        except Exception:
            pass  # Silently fail for now
    
    async def _persist_balances(self, exchange: str, balances: List[ExchangeBalanceSync]):
        """Persist balances to MongoDB."""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "fomo_trading")
            
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            
            for bal in balances:
                await db.exchange_balances.update_one(
                    {"exchange": exchange, "asset": bal.asset},
                    {"$set": bal.model_dump()},
                    upsert=True,
                )
            
            client.close()
        except Exception:
            pass
    
    async def _persist_orders(self, exchange: str, orders: List[ExchangeOrderSync]):
        """Persist orders to MongoDB."""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "fomo_trading")
            
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            
            for ord in orders:
                await db.exchange_orders.update_one(
                    {"exchange": exchange, "exchange_order_id": ord.exchange_order_id},
                    {"$set": ord.model_dump()},
                    upsert=True,
                )
            
            client.close()
        except Exception:
            pass
    
    async def _update_portfolio_positions(self, exchange: str, positions: List[ExchangePositionSync]):
        """Update Portfolio Manager with synced positions."""
        try:
            from modules.portfolio_manager import get_portfolio_engine
            
            engine = get_portfolio_engine()
            
            # Convert to portfolio format and update
            for pos in positions:
                engine.update_position_from_exchange(
                    symbol=pos.symbol,
                    exchange=exchange,
                    size=pos.size,
                    side=pos.side,
                    entry_price=pos.entry_price,
                    unrealized_pnl=pos.unrealized_pnl,
                )
        except Exception:
            pass  # Silently fail if portfolio manager not available
    
    def is_stale(self, exchange: str) -> bool:
        """Check if sync data is stale."""
        state = self._sync_states.get(exchange)
        if not state or not state.positions_last_sync:
            return True
        
        age = (datetime.now(timezone.utc) - state.positions_last_sync).total_seconds()
        return age > self._config.stale_threshold_seconds
    
    def get_summary(self) -> Dict:
        """Get sync summary."""
        summary = {
            "running": self._running,
            "exchanges": {},
            "total_positions": 0,
            "total_balances": 0,
            "total_open_orders": 0,
        }
        
        for exchange, state in self._sync_states.items():
            summary["exchanges"][exchange] = {
                "positions_status": state.positions_status.value,
                "balances_status": state.balances_status.value,
                "orders_status": state.orders_status.value,
                "positions_count": state.positions_count,
                "balances_count": state.balances_count,
                "open_orders_count": state.open_orders_count,
                "last_sync": state.positions_last_sync.isoformat() if state.positions_last_sync else None,
                "is_stale": self.is_stale(exchange),
                "error_count": state.error_count,
                "last_error": state.last_error,
            }
            
            summary["total_positions"] += state.positions_count
            summary["total_balances"] += state.balances_count
            summary["total_open_orders"] += state.open_orders_count
        
        return summary


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_sync_engine: Optional[ExchangeSyncEngine] = None


def get_exchange_sync_engine() -> ExchangeSyncEngine:
    """Get singleton instance."""
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = ExchangeSyncEngine()
    return _sync_engine
