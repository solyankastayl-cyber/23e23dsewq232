"""
Position Sync Service
Sprint A5: Syncs real exchange positions → portfolio_positions DB
Sprint WS-2: Broadcasts position state changes via WebSocket
"""

import time
import logging
import json
import hashlib

logger = logging.getLogger(__name__)


class PositionSyncService:
    """
    Syncs positions from exchange adapter to portfolio_positions collection.
    
    Source of truth: Exchange adapter (Binance Futures)
    
    WS-2: Broadcasts snapshot only when state changes (hash-based debounce).
    """
    
    def __init__(self, adapter, db):
        self.adapter = adapter
        self.db = db
        self.col = db.portfolio_positions
        self._last_positions_hash = None  # WS-2: Debounce via hash
        logger.info("[PositionSyncService] Initialized")
    
    async def sync_positions(self):
        """
        Sync positions from exchange → DB.
        
        Returns:
            {"ok": bool, "count": int}
        """
        try:
            # Get positions from exchange
            positions = await self.adapter.get_positions()
            
            now_ms = int(time.time() * 1000)
            
            seen_symbols = set()
            
            # Update/insert open positions
            for pos in positions:
                # Convert Position Pydantic model to dict
                pos_dict = {
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "qty": pos.qty,
                    "entry_price": pos.entry_price,
                    "mark_price": pos.mark_price,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                    "leverage": pos.leverage,
                    "liquidation_price": pos.liquidation_price,
                }
                
                symbol = pos_dict["symbol"]
                seen_symbols.add(symbol)
                
                await self.col.update_one(
                    {"symbol": symbol},
                    {
                        "$set": {
                            **pos_dict,
                            "status": "OPEN",
                            "updated_at": now_ms,
                        },
                        "$setOnInsert": {
                            "created_at": now_ms,
                        },
                    },
                    upsert=True,
                )
            
            # Mark positions that disappeared as CLOSED
            # Skip destructive sync when exchange returns 0 positions (adapter restart/no data)
            if seen_symbols:
                cursor = self.col.find({"status": "OPEN"})
                existing = await cursor.to_list(length=100)
                
                for row in existing:
                    if row["symbol"] not in seen_symbols:
                        await self.col.update_one(
                            {"_id": row["_id"]},
                            {
                                "$set": {
                                    "status": "CLOSED",
                                    "closed_at": now_ms,
                                }
                            },
                        )
                        logger.info(f"[PositionSyncService] Position closed: {row['symbol']}")
            
            logger.info(f"[PositionSyncService] Sync complete: {len(positions)} open positions")
            
            # WS-2: Broadcast snapshot ONLY if state changed
            try:
                from modules.ws_hub.service_locator import get_ws_broadcaster
                
                broadcaster = get_ws_broadcaster()
                
                # Get clean snapshot for broadcast
                rows = await self.col.find({"status": "OPEN"}).to_list(length=100)
                for r in rows:
                    r.pop("_id", None)
                
                # Hash-based debounce: only broadcast if changed
                new_hash = hashlib.md5(
                    json.dumps(rows, sort_keys=True).encode()
                ).hexdigest()
                
                if new_hash != self._last_positions_hash:
                    self._last_positions_hash = new_hash
                    await broadcaster.broadcast_snapshot("positions.state", rows)
                    logger.debug(f"[WS-2] positions.state broadcast (hash={new_hash[:8]})")
                
            except Exception as e:
                logger.debug(f"[WS-2] positions broadcast failed (non-critical): {e}")
            
            return {"ok": True, "count": len(positions)}
        
        except Exception as e:
            logger.error(f"[PositionSyncService] Sync failed: {e}")
            return {"ok": False, "error": str(e)}
