"""
Paper Decision Repository
=========================

Phase 3.0A: CRUD for paper_decisions collection.

Schema:
  {
    "_id": "...",
    "experiment_id": "market_dynamic",
    "snapshot_id": "...",
    "symbol": "BTCUSDT",
    "timeframe": "4h",
    "side": "LONG",
    "score": 0.71,
    "confidence": 0.50,
    "features": {...},
    "readiness_state": "ready",
    "readiness_reason": "...",
    "paper_status": "EXECUTED",
    "created_at": datetime,
    "executed_at": datetime,
    "rejection_reason": null
  }
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from .config import PaperDecisionStatus

logger = logging.getLogger(__name__)


class PaperDecisionRepository:
    """
    Manages paper_decisions collection.
    
    Responsibilities:
      - Create paper decisions
      - Check for duplicates (dedup key)
      - Update decision status
      - Query decisions
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.paper_decisions
    
    async def create_decision(
        self,
        experiment_id: str,
        snapshot_id: str,
        symbol: str,
        timeframe: str,
        side: str,
        score: float,
        confidence: float,
        features: Dict[str, Any],
        readiness_state: str,
        readiness_reason: str
    ) -> str:
        """
        Create paper decision.
        
        Args:
            experiment_id: Experiment ID
            snapshot_id: Snapshot ID
            symbol: Trading symbol
            timeframe: Signal timeframe
            side: LONG or SHORT
            score: Signal score
            confidence: Signal confidence
            features: Signal features
            readiness_state: Current readiness state
            readiness_reason: Reason for readiness state
        
        Returns:
            Decision ID
        """
        decision = {
            "experiment_id": experiment_id,
            "snapshot_id": snapshot_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "side": side,
            "score": score,
            "confidence": confidence,
            "features": features,
            "readiness_state": readiness_state,
            "readiness_reason": readiness_reason,
            "paper_status": PaperDecisionStatus.CREATED,
            "created_at": datetime.now(timezone.utc),
            "executed_at": None,
            "rejection_reason": None
        }
        
        result = await self.collection.insert_one(decision)
        decision_id = str(result.inserted_id)
        
        logger.info(
            f"[PaperDecision] Created: {symbol} {side} "
            f"(score={score:.2f}, readiness={readiness_state})"
        )
        
        return decision_id
    
    async def check_duplicate(
        self,
        experiment_id: str,
        snapshot_id: str,
        symbol: str,
        timeframe: str
    ) -> bool:
        """
        Check if decision already exists for this snapshot+symbol+timeframe.
        
        Args:
            experiment_id: Experiment ID
            snapshot_id: Snapshot ID
            symbol: Trading symbol
            timeframe: Signal timeframe
        
        Returns:
            True if duplicate exists, False otherwise
        """
        existing = await self.collection.find_one({
            "experiment_id": experiment_id,
            "snapshot_id": snapshot_id,
            "symbol": symbol,
            "timeframe": timeframe
        })
        
        return existing is not None
    
    async def update_status(
        self,
        decision_id: str,
        status: str,
        executed_at: Optional[datetime] = None,
        rejection_reason: Optional[str] = None
    ) -> bool:
        """
        Update decision status.
        
        Args:
            decision_id: Decision ID
            status: New status
            executed_at: Execution timestamp (if EXECUTED)
            rejection_reason: Rejection reason (if REJECTED)
        
        Returns:
            True if updated, False if not found
        """
        from bson import ObjectId
        
        update_fields = {
            "paper_status": status
        }
        
        if executed_at:
            update_fields["executed_at"] = executed_at
        
        if rejection_reason:
            update_fields["rejection_reason"] = rejection_reason
        
        result = await self.collection.update_one(
            {"_id": ObjectId(decision_id)},
            {"$set": update_fields}
        )
        
        return result.modified_count > 0
    
    async def get_decisions(
        self,
        experiment_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get paper decisions.
        
        Args:
            experiment_id: Experiment ID
            status: Optional status filter
            limit: Max decisions to return
        
        Returns:
            List of decisions
        """
        query = {"experiment_id": experiment_id}
        
        if status:
            query["paper_status"] = status
        
        cursor = self.collection.find(query).sort("created_at", -1).limit(limit)
        decisions = await cursor.to_list(length=limit)
        
        # Convert _id to string
        for decision in decisions:
            decision["_id"] = str(decision["_id"])
        
        return decisions
    
    async def get_decision_by_id(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Get decision by ID."""
        from bson import ObjectId
        
        decision = await self.collection.find_one({"_id": ObjectId(decision_id)})
        
        if decision:
            decision["_id"] = str(decision["_id"])
        
        return decision
    
    async def exists_by_dedup_key(
        self,
        experiment_id: str,
        snapshot_id: str,
        symbol: str,
        timeframe: str
    ) -> bool:
        """
        Check if decision exists (for deduplication).
        
        Returns:
            True if exists, False otherwise
        """
        found = await self.collection.find_one({
            "experiment_id": experiment_id,
            "snapshot_id": snapshot_id,
            "symbol": symbol,
            "timeframe": timeframe
        }, {"_id": 1})
        
        return found is not None
    
    async def list_decisions(
        self,
        experiment_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List decisions with filters.
        
        Args:
            experiment_id: Experiment ID
            status: Optional status filter
            symbol: Optional symbol filter
            limit: Max results
        
        Returns:
            List of decisions
        """
        query = {"experiment_id": experiment_id}
        
        if status:
            query["paper_status"] = status.upper()
        
        if symbol:
            query["symbol"] = symbol.upper()
        
        cursor = self.collection.find(query).sort("created_at", -1).limit(limit)
        items = []
        
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            if "snapshot_id" in doc and hasattr(doc["snapshot_id"], "__str__"):
                doc["snapshot_id"] = str(doc["snapshot_id"])
            items.append(doc)
        
        return items


async def create_indexes(db: AsyncIOMotorDatabase):
    """Create indexes for paper_decisions collection."""
    await db.paper_decisions.create_index(
        [("experiment_id", 1), ("created_at", -1)]
    )
    await db.paper_decisions.create_index(
        [("experiment_id", 1), ("paper_status", 1)]
    )
    # Dedup index (unique)
    await db.paper_decisions.create_index(
        [("experiment_id", 1), ("snapshot_id", 1), ("symbol", 1), ("timeframe", 1)],
        unique=True,
        name="uniq_paper_decision_dedup"
    )
    
    logger.info("[PaperDecisionRepository] Indexes created")
