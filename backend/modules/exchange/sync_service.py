"""
Exchange Sync Service — Position Truth Layer

Synchronizes exchange state → MongoDB (source of truth).

CRITICAL:
- Positions come from EXCHANGE, not local memory
- Sync runs every 5-10 seconds
- Detects discrepancies
"""

import logging
from typing import Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ExchangeSyncService:
    """
    Sync service for exchange state.
    
    Ensures:
    - Positions in DB match exchange positions
    - Balances are up-to-date
    - Order statuses are tracked
    """
    
    def __init__(self, exchange_adapter, db):
        """
        Args:
            exchange_adapter: ExchangeAdapter instance
            db: MongoDB database instance
        """
        self.adapter = exchange_adapter
        self.db = db
        
        self.positions_collection = db.exchange_positions
        self.balances_collection = db.exchange_balances
        self.sync_logs_collection = db.exchange_sync_logs
        
        logger.info("[ExchangeSyncService] Initialized")
    
    async def sync(self) -> Dict[str, Any]:
        """
        Full sync: balances + positions.
        
        Returns:
            Sync result with counts
        """
        if not self.adapter.connected:
            logger.warning("[ExchangeSyncService] Skipping sync (adapter not connected)")
            return {
                "ok": False,
                "reason": "Exchange adapter not connected",
                "timestamp": int(datetime.now(timezone.utc).timestamp())
            }
        
        try:
            # 1. Sync balances
            balances = await self.adapter.get_balances()
            await self._sync_balances(balances)
            
            # 2. Sync positions
            positions = await self.adapter.get_positions()
            await self._sync_positions(positions)
            
            # 3. Log sync
            sync_log = {
                "timestamp": datetime.now(timezone.utc),
                "balances_count": len(balances),
                "positions_count": len(positions),
                "status": "SUCCESS",
            }
            
            await self.sync_logs_collection.insert_one(sync_log)
            
            logger.info(f"[ExchangeSyncService] Sync complete: {len(balances)} balances, {len(positions)} positions")
            
            return {
                "ok": True,
                "balances_count": len(balances),
                "positions_count": len(positions),
                "timestamp": int(datetime.now(timezone.utc).timestamp())
            }
        
        except Exception as e:
            logger.error(f"[ExchangeSyncService] Sync failed: {e}")
            
            # Log failure
            sync_log = {
                "timestamp": datetime.now(timezone.utc),
                "status": "FAILED",
                "error": str(e),
            }
            
            await self.sync_logs_collection.insert_one(sync_log)
            
            return {
                "ok": False,
                "reason": str(e),
                "timestamp": int(datetime.now(timezone.utc).timestamp())
            }
    
    async def _sync_balances(self, balances):
        """
        Sync balances to DB.
        
        Strategy: DELETE ALL + INSERT (simple truth replacement)
        """
        # Clear existing balances
        await self.balances_collection.delete_many({})
        
        # Insert new balances
        if balances:
            balance_docs = []
            for b in balances:
                balance_docs.append({
                    "asset": b.asset,
                    "free": b.free,
                    "locked": b.locked,
                    "total": b.total,
                    "updated_at": datetime.now(timezone.utc),
                })
            
            await self.balances_collection.insert_many(balance_docs)
            logger.debug(f"[ExchangeSyncService] Synced {len(balances)} balances")
    
    async def _sync_positions(self, positions):
        """
        Sync positions to DB.
        
        Strategy: DELETE ALL + INSERT (simple truth replacement)
        """
        # Clear existing positions
        await self.positions_collection.delete_many({})
        
        # Insert new positions
        if positions:
            position_docs = []
            for p in positions:
                position_docs.append({
                    "symbol": p.symbol,
                    "side": p.side,
                    "qty": p.qty,
                    "entry_price": p.entry_price,
                    "mark_price": p.mark_price,
                    "unrealized_pnl": p.unrealized_pnl,
                    "unrealized_pnl_pct": p.unrealized_pnl_pct,
                    "realized_pnl": p.realized_pnl,
                    "leverage": p.leverage,
                    "status": p.status,
                    "opened_at": p.opened_at,
                    "updated_at": datetime.now(timezone.utc),
                })
            
            await self.positions_collection.insert_many(position_docs)
            logger.debug(f"[ExchangeSyncService] Synced {len(positions)} positions")
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """
        Get last sync status.
        """
        last_sync = await self.sync_logs_collection.find_one(
            {},
            {"_id": 0},
            sort=[("timestamp", -1)]
        )
        
        if not last_sync:
            return {
                "status": "NEVER_SYNCED",
                "last_sync_at": None,
            }
        
        return {
            "status": last_sync.get("status", "UNKNOWN"),
            "last_sync_at": int(last_sync["timestamp"].timestamp()),
            "balances_count": last_sync.get("balances_count"),
            "positions_count": last_sync.get("positions_count"),
            "error": last_sync.get("error"),
        }


# Singleton instance
_sync_service = None


def init_sync_service(exchange_adapter, db):
    """Initialize sync service singleton."""
    global _sync_service
    _sync_service = ExchangeSyncService(exchange_adapter, db)
    logger.info("[ExchangeSyncService] Singleton initialized")


def get_sync_service() -> ExchangeSyncService:
    """Get sync service singleton."""
    if _sync_service is None:
        raise RuntimeError("ExchangeSyncService not initialized. Call init_sync_service() first.")
    return _sync_service
