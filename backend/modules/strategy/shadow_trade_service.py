"""
Shadow Trade Service
====================

Creates virtual trades for selected signals.
Tracks multiple time horizons (24h, 48h, 7d).

Architecture:
  Decision (snapshot) → Shadow Trades → Outcome Resolution → Learning
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


# Multiple horizons for each trade (labels for ML)
HORIZONS = [
    ("24h", timedelta(hours=24)),
    ("48h", timedelta(hours=48)),
    ("7d", timedelta(days=7)),
]


class ShadowTradeService:
    """
    Manages shadow (virtual) trades for market_dynamic.
    
    Each selected signal creates ONE shadow trade with MULTIPLE horizons.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.shadow_trades
    
    async def create_from_snapshot(self, snapshot: Dict[str, Any]) -> List[str]:
        """
        Create shadow trades for all selected signals in snapshot.
        
        Args:
            snapshot: Saved snapshot document (must have _id)
            
        Returns:
            List of created shadow trade IDs
        """
        now = datetime.now(timezone.utc)
        
        trades = []
        
        for signal in snapshot.get("selected_signals", []):
            # Create horizons for this trade
            horizons = []
            for name, delta in HORIZONS:
                horizons.append({
                    "name": name,
                    "resolve_at": now + delta,
                    "resolved": False,
                    "exit_price": None,
                    "pnl": None,
                    "mfe": None,  # Max favorable excursion
                    "mae": None,  # Max adverse excursion
                })
            
            trade = {
                "experiment_id": snapshot["experiment_id"],
                "snapshot_id": snapshot["_id"],  # Link to snapshot
                
                # Trade details
                "symbol": signal["symbol"],
                "timeframe": signal["timeframe"],
                "side": signal["side"],
                
                # Entry
                "entry_price": signal["price"],
                "entry_time": now,
                
                # Features (for ML)
                "features": {
                    "score": signal.get("score", 0.5),
                    "confidence": signal.get("confidence", 0.5),
                    "cluster": signal.get("cluster", "unknown"),
                    "market_bias": snapshot.get("market_bias", "neutral"),
                    "market_structure": snapshot.get("market_structure", {}),
                },
                
                # Multiple horizons
                "horizons": horizons,
                
                # Timestamps
                "created_at": now,
                "updated_at": now,
            }
            
            trades.append(trade)
        
        if not trades:
            logger.debug("[ShadowTrade] No trades to create (no selected signals)")
            return []
        
        result = await self.collection.insert_many(trades)
        trade_ids = [str(tid) for tid in result.inserted_ids]
        
        logger.info(
            f"[ShadowTrade] Created {len(trades)} shadow trades "
            f"(snapshot={snapshot['_id']}, horizons={len(HORIZONS)})"
        )
        
        return trade_ids
    
    async def get_unresolved_trades(self) -> List[Dict[str, Any]]:
        """Get trades with at least one unresolved horizon."""
        cursor = self.collection.find({
            "horizons": {
                "$elemMatch": {
                    "resolved": False,
                    "resolve_at": {"$lte": datetime.now(timezone.utc)}
                }
            }
        })
        
        return await cursor.to_list(length=1000)


async def create_indexes(db: AsyncIOMotorDatabase):
    """Create indexes for shadow_trades collection."""
    await db.shadow_trades.create_index(
        [("experiment_id", 1), ("entry_time", -1)]
    )
    await db.shadow_trades.create_index(
        [("horizons.resolve_at", 1), ("horizons.resolved", 1)]
    )
    await db.shadow_trades.create_index([("snapshot_id", 1)])
    
    logger.info("[ShadowTrade] Indexes created")
