"""
Execution Comparator
====================

Phase 3.1: Match shadow_trades ↔ paper_positions.

Matching key:
  experiment_id + snapshot_id + symbol + timeframe + side

Output:
  List of matched pairs with per-trade deltas.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class ExecutionComparator:
    """
    Matches shadow trades with paper positions.
    
    Returns matched pairs with execution deltas.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.shadow_collection = db.shadow_trades
        self.paper_collection = db.paper_positions
    
    async def get_matched_pairs(
        self,
        experiment_id: str = "market_dynamic",
        horizon: str = "24h"
    ) -> List[Dict[str, Any]]:
        """
        Get matched pairs of shadow trades and paper positions.
        
        Matching key:
          experiment_id + snapshot_id + symbol + timeframe + side
        
        Args:
            experiment_id: Experiment ID
            horizon: Time horizon for comparison (default: 24h)
        
        Returns:
            List of matched pairs:
            [
                {
                    "experiment_id": "market_dynamic",
                    "snapshot_id": "...",
                    "symbol": "BTCUSDT",
                    "timeframe": "4h",
                    "side": "LONG",
                    "shadow_entry_price": 74200.0,
                    "shadow_pnl_24h": 0.012,
                    "paper_entry_price": 74310.0,
                    "paper_pnl_pct": 0.009,
                    "execution_delta": -0.003,
                    "entry_delay_pct": 0.0015
                },
                ...
            ]
        """
        logger.info(f"[ExecutionComparator] Matching pairs for {experiment_id}, horizon={horizon}")
        
        # Get all shadow trades with resolved horizon
        shadow_trades = await self._get_shadow_trades(experiment_id, horizon)
        
        # Get all closed paper positions
        paper_positions = await self._get_paper_positions(experiment_id)
        
        # Build index for paper positions
        paper_index = self._build_paper_index(paper_positions)
        
        # Match and calculate deltas
        matched_pairs = []
        
        for shadow in shadow_trades:
            # Build match key
            match_key = self._build_match_key(
                snapshot_id=shadow.get("snapshot_id"),
                symbol=shadow["symbol"],
                timeframe=shadow["timeframe"],
                side=shadow["side"]
            )
            
            # Find matching paper position
            paper = paper_index.get(match_key)
            
            if not paper:
                continue  # No match found
            
            # Calculate deltas
            pair = self._calculate_pair_deltas(shadow, paper, horizon)
            
            if pair:
                matched_pairs.append(pair)
        
        logger.info(
            f"[ExecutionComparator] Matched {len(matched_pairs)} pairs "
            f"(shadow: {len(shadow_trades)}, paper: {len(paper_positions)})"
        )
        
        return matched_pairs
    
    async def _get_shadow_trades(
        self,
        experiment_id: str,
        horizon: str
    ) -> List[Dict[str, Any]]:
        """
        Get shadow trades with resolved horizon.
        
        Args:
            experiment_id: Experiment ID
            horizon: Time horizon (24h)
        
        Returns:
            List of shadow trades
        """
        pipeline = [
            {"$unwind": "$horizons"},
            {"$match": {
                "experiment_id": experiment_id,
                "horizons.name": horizon,
                "horizons.resolved": True
            }},
            {"$project": {
                "_id": 1,
                "experiment_id": 1,
                "snapshot_id": 1,
                "symbol": 1,
                "timeframe": 1,
                "side": 1,
                "entry_price": 1,
                "entry_time": 1,
                "pnl": "$horizons.pnl",
                "exit_price": "$horizons.exit_price"
            }}
        ]
        
        trades = await self.shadow_collection.aggregate(pipeline).to_list(length=1000)
        
        return trades
    
    async def _get_paper_positions(
        self,
        experiment_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get closed paper positions.
        
        Args:
            experiment_id: Experiment ID
        
        Returns:
            List of paper positions
        """
        cursor = self.paper_collection.find({
            "experiment_id": experiment_id,
            "status": "CLOSED"
        })
        
        positions = await cursor.to_list(length=1000)
        
        return positions
    
    def _build_paper_index(
        self,
        paper_positions: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Build index of paper positions by match key.
        
        Args:
            paper_positions: List of paper positions
        
        Returns:
            Dictionary: {match_key: position}
        """
        index = {}
        
        for position in paper_positions:
            match_key = self._build_match_key(
                snapshot_id=position.get("snapshot_id"),
                symbol=position["symbol"],
                timeframe=position["timeframe"],
                side=position["side"]
            )
            
            # Store first match (in case of duplicates)
            if match_key not in index:
                index[match_key] = position
        
        return index
    
    def _build_match_key(
        self,
        snapshot_id: Optional[str],
        symbol: str,
        timeframe: str,
        side: str
    ) -> str:
        """
        Build match key for shadow ↔ paper matching.
        
        Key: snapshot_id + symbol + timeframe + side
        
        Args:
            snapshot_id: Snapshot ID
            symbol: Trading symbol
            timeframe: Timeframe
            side: Side (LONG/SHORT)
        
        Returns:
            Match key string
        """
        # Convert snapshot_id to string if ObjectId
        snapshot_str = str(snapshot_id) if snapshot_id else "unknown"
        
        return f"{snapshot_str}_{symbol}_{timeframe}_{side}"
    
    def _calculate_pair_deltas(
        self,
        shadow: Dict[str, Any],
        paper: Dict[str, Any],
        horizon: str
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate execution deltas for matched pair.
        
        Args:
            shadow: Shadow trade data
            paper: Paper position data
            horizon: Time horizon
        
        Returns:
            Matched pair with deltas or None if invalid
        """
        try:
            shadow_entry = shadow["entry_price"]
            shadow_pnl = shadow["pnl"]
            
            paper_entry = paper["entry_price"]
            paper_pnl = paper.get("pnl_pct", 0)
            
            side = shadow["side"]
            
            # Calculate execution delta
            execution_delta = paper_pnl - shadow_pnl
            
            # Calculate entry delay impact
            if side == "LONG":
                entry_delay_pct = (paper_entry - shadow_entry) / shadow_entry
            else:  # SHORT
                entry_delay_pct = (shadow_entry - paper_entry) / shadow_entry
            
            return {
                "experiment_id": shadow["experiment_id"],
                "snapshot_id": str(shadow.get("snapshot_id", "")),
                "symbol": shadow["symbol"],
                "timeframe": shadow["timeframe"],
                "side": side,
                "shadow_entry_price": shadow_entry,
                "shadow_pnl": shadow_pnl,
                "paper_entry_price": paper_entry,
                "paper_pnl": paper_pnl,
                "execution_delta": execution_delta,
                "entry_delay_pct": entry_delay_pct
            }
        
        except Exception as e:
            logger.error(f"[ExecutionComparator] Error calculating deltas: {e}")
            return None
