"""
Paper Position Repository
=========================

Phase 3.0A: CRUD for paper_positions collection.

Schema:
  {
    "_id": "...",
    "experiment_id": "market_dynamic",
    "paper_decision_id": "...",
    "snapshot_id": "...",
    "symbol": "BTCUSDT",
    "timeframe": "4h",
    "side": "LONG",
    "entry_price": 74910.71,
    "entry_time": datetime,
    "size_usd": 100,
    "qty": 0.00133,
    "status": "OPEN",
    "close_after": datetime,
    "exit_price": null,
    "exit_time": null,
    "pnl_pct": null,
    "pnl_usd": null
  }
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from .config import PaperPositionStatus, PAPER_CONFIG

logger = logging.getLogger(__name__)


class PaperPositionRepository:
    """
    Manages paper_positions collection.
    
    Responsibilities:
      - Create paper positions
      - Check for open positions
      - Update position (close)
      - Query positions
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.paper_positions
    
    async def create_position(
        self,
        experiment_id: str,
        paper_decision_id: str,
        snapshot_id: str,
        symbol: str,
        timeframe: str,
        side: str,
        entry_price: float,
        size_usd: float
    ) -> str:
        """
        Create paper position.
        
        Args:
            experiment_id: Experiment ID
            paper_decision_id: Paper decision ID
            snapshot_id: Snapshot ID
            symbol: Trading symbol
            timeframe: Signal timeframe
            side: LONG or SHORT
            entry_price: Entry price
            size_usd: Position size in USD
        
        Returns:
            Position ID
        """
        entry_time = datetime.now(timezone.utc)
        qty = size_usd / entry_price
        close_after = entry_time + timedelta(hours=PAPER_CONFIG["close_after_hours"])
        
        position = {
            "experiment_id": experiment_id,
            "paper_decision_id": paper_decision_id,
            "snapshot_id": snapshot_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "side": side,
            "entry_price": entry_price,
            "entry_time": entry_time,
            "size_usd": size_usd,
            "qty": qty,
            "status": PaperPositionStatus.OPEN,
            "close_after": close_after,
            "exit_price": None,
            "exit_time": None,
            "pnl_pct": None,
            "pnl_usd": None
        }
        
        result = await self.collection.insert_one(position)
        position_id = str(result.inserted_id)
        
        logger.info(
            f"[PaperPosition] Opened: {symbol} {side} "
            f"entry=${entry_price:.2f}, size=${size_usd:.2f}, qty={qty:.6f}"
        )
        
        return position_id
    
    async def check_open_position(
        self,
        experiment_id: str,
        symbol: str,
        cooldown_hours: int
    ) -> bool:
        """
        Check if there's an open position within cooldown period.
        
        Args:
            experiment_id: Experiment ID
            symbol: Trading symbol
            cooldown_hours: Cooldown period in hours
        
        Returns:
            True if open position exists within cooldown, False otherwise
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)
        
        existing = await self.collection.find_one({
            "experiment_id": experiment_id,
            "symbol": symbol,
            "status": PaperPositionStatus.OPEN,
            "entry_time": {"$gte": cutoff}
        })
        
        return existing is not None
    
    async def count_open_positions(self, experiment_id: str) -> int:
        """
        Count total open positions.
        
        Args:
            experiment_id: Experiment ID
        
        Returns:
            Count of open positions
        """
        count = await self.collection.count_documents({
            "experiment_id": experiment_id,
            "status": PaperPositionStatus.OPEN
        })
        
        return count
    
    async def close_position(
        self,
        position_id: str,
        exit_price: float,
        exit_time: Optional[datetime] = None
    ) -> bool:
        """
        Close position and calculate PnL.
        
        Args:
            position_id: Position ID
            exit_price: Exit price
            exit_time: Exit timestamp (default: now)
        
        Returns:
            True if closed, False if not found
        """
        from bson import ObjectId
        
        if exit_time is None:
            exit_time = datetime.now(timezone.utc)
        
        # Get position
        position = await self.collection.find_one({"_id": ObjectId(position_id)})
        
        if not position:
            return False
        
        # Calculate PnL
        entry_price = position["entry_price"]
        side = position["side"]
        qty = position["qty"]
        
        if side == "LONG":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:  # SHORT
            pnl_pct = (entry_price - exit_price) / entry_price
        
        pnl_usd = pnl_pct * position["size_usd"]
        
        # Update position
        result = await self.collection.update_one(
            {"_id": ObjectId(position_id)},
            {
                "$set": {
                    "status": PaperPositionStatus.CLOSED,
                    "exit_price": exit_price,
                    "exit_time": exit_time,
                    "pnl_pct": pnl_pct,
                    "pnl_usd": pnl_usd
                }
            }
        )
        
        logger.info(
            f"[PaperPosition] Closed: {position['symbol']} {side} "
            f"entry=${entry_price:.2f} exit=${exit_price:.2f} "
            f"pnl={pnl_pct:.2%} (${pnl_usd:.2f})"
        )
        
        return result.modified_count > 0
    
    async def get_positions(
        self,
        experiment_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get paper positions.
        
        Args:
            experiment_id: Experiment ID
            status: Optional status filter
            limit: Max positions to return
        
        Returns:
            List of positions
        """
        query = {"experiment_id": experiment_id}
        
        if status:
            query["status"] = status
        
        cursor = self.collection.find(query).sort("entry_time", -1).limit(limit)
        positions = await cursor.to_list(length=limit)
        
        # Convert _id to string
        for position in positions:
            position["_id"] = str(position["_id"])
        
        return positions
    
    async def get_positions_to_close(self, experiment_id: str) -> List[Dict[str, Any]]:
        """
        Get positions that should be closed (close_after <= now).
        
        Args:
            experiment_id: Experiment ID
        
        Returns:
            List of positions ready to close
        """
        now = datetime.now(timezone.utc)
        
        cursor = self.collection.find({
            "experiment_id": experiment_id,
            "status": PaperPositionStatus.OPEN,
            "close_after": {"$lte": now}
        })
        
        positions = await cursor.to_list(length=100)
        
        # Convert _id to string
        for position in positions:
            position["_id"] = str(position["_id"])
        
        return positions
    
    async def has_open_position_for_symbol(
        self,
        experiment_id: str,
        symbol: str
    ) -> bool:
        """
        Check if there's any open position for symbol.
        
        Args:
            experiment_id: Experiment ID
            symbol: Trading symbol
        
        Returns:
            True if open position exists, False otherwise
        """
        found = await self.collection.find_one({
            "experiment_id": experiment_id,
            "symbol": symbol,
            "status": PaperPositionStatus.OPEN
        }, {"_id": 1})
        
        return found is not None
    
    async def get_latest_closed_position(
        self,
        experiment_id: str,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest closed position for symbol.
        
        Args:
            experiment_id: Experiment ID
            symbol: Trading symbol
        
        Returns:
            Latest closed position or None
        """
        position = await self.collection.find_one(
            {
                "experiment_id": experiment_id,
                "symbol": symbol,
                "status": PaperPositionStatus.CLOSED
            },
            sort=[("exit_time", -1)]
        )
        
        if position:
            position["_id"] = str(position["_id"])
        
        return position
    
    async def list_positions(
        self,
        experiment_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List positions with filters.
        
        Args:
            experiment_id: Experiment ID
            status: Optional status filter
            symbol: Optional symbol filter
            limit: Max results
        
        Returns:
            List of positions
        """
        query = {"experiment_id": experiment_id}
        
        if status:
            query["status"] = status.upper()
        
        if symbol:
            query["symbol"] = symbol.upper()
        
        cursor = self.collection.find(query).sort("entry_time", -1).limit(limit)
        items = []
        
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            if "paper_decision_id" in doc:
                doc["paper_decision_id"] = str(doc["paper_decision_id"])
            items.append(doc)
        
        return items
    
    async def get_performance(self, experiment_id: str) -> Dict[str, Any]:
        """
        Get performance summary.
        
        Args:
            experiment_id: Experiment ID
        
        Returns:
            {
                "total_positions": 25,
                "open_positions": 5,
                "closed_positions": 20,
                "winrate": 0.55,
                "avg_pnl": 0.012
            }
        """
        total = await self.collection.count_documents({"experiment_id": experiment_id})
        open_count = await self.collection.count_documents({
            "experiment_id": experiment_id,
            "status": PaperPositionStatus.OPEN
        })
        closed_count = await self.collection.count_documents({
            "experiment_id": experiment_id,
            "status": PaperPositionStatus.CLOSED
        })
        
        # Aggregate closed positions for winrate/avg_pnl
        pipeline = [
            {"$match": {
                "experiment_id": experiment_id,
                "status": PaperPositionStatus.CLOSED
            }},
            {"$group": {
                "_id": None,
                "avg_pnl": {"$avg": "$pnl_pct"},
                "winrate": {
                    "$avg": {
                        "$cond": [{"$gt": ["$pnl_pct", 0]}, 1.0, 0.0]
                    }
                }
            }}
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(length=1)
        agg = results[0] if results else {}
        
        return {
            "total_positions": total,
            "open_positions": open_count,
            "closed_positions": closed_count,
            "winrate": round(agg.get("winrate", 0), 4),
            "avg_pnl": round(agg.get("avg_pnl", 0), 6)
        }


async def create_indexes(db: AsyncIOMotorDatabase):
    """Create indexes for paper_positions collection."""
    await db.paper_positions.create_index(
        [("experiment_id", 1), ("entry_time", -1)]
    )
    await db.paper_positions.create_index(
        [("experiment_id", 1), ("status", 1)]
    )
    await db.paper_positions.create_index(
        [("experiment_id", 1), ("symbol", 1), ("status", 1), ("entry_time", -1)]
    )
    # Close worker index
    await db.paper_positions.create_index(
        [("experiment_id", 1), ("status", 1), ("close_after", 1)]
    )
    
    logger.info("[PaperPositionRepository] Indexes created")
