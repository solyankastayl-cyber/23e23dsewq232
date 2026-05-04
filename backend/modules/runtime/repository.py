"""
Pending Decision Repository
"""

import time
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pymongo import ASCENDING, DESCENDING

logger = logging.getLogger(__name__)


class PendingDecisionRepository:
    """Repository for pending decisions (SEMI_AUTO mode)."""
    
    def __init__(self, db):
        self.db = db
        self.col = db.pending_decisions
        self._ensure_indexes()
        logger.info("[PendingDecisionRepository] Initialized")
    
    def _ensure_indexes(self) -> None:
        """Create indexes for pending_decisions collection."""
        self.col.create_index([("decision_id", ASCENDING)], unique=True)
        self.col.create_index([("status", ASCENDING)])
        self.col.create_index([("created_at", DESCENDING)])
        self.col.create_index([("expires_at", ASCENDING)])
    
    async def create(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new pending decision."""
        doc = decision.copy()
        if "decision_id" not in doc:
            doc["decision_id"] = f"dec_{uuid4().hex[:12]}"
        
        now = int(time.time())
        doc.setdefault("created_at", now)
        doc.setdefault("expires_at", now + 1800)  # 30 minutes
        doc.setdefault("status", "PENDING")
        
        await self.col.insert_one(doc)
        logger.info(f"[PendingDecisionRepository] Created decision {doc['decision_id']}")
        
        # Remove MongoDB _id to avoid FastAPI serialization error
        if "_id" in doc:
            del doc["_id"]
        return doc
    
    async def get_pending(self) -> List[Dict[str, Any]]:
        """Get all pending decisions."""
        cursor = self.col.find({"status": "PENDING"}).sort("created_at", DESCENDING)
        docs = await cursor.to_list(length=100)
        
        # Remove MongoDB _id from all documents
        for doc in docs:
            if "_id" in doc:
                del doc["_id"]
        return docs
    
    async def get_by_id(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Get decision by ID."""
        doc = await self.col.find_one({"decision_id": decision_id})
        if doc and "_id" in doc:
            del doc["_id"]
        return doc
    
    async def approve(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Approve a pending decision."""
        await self.col.update_one(
            {"decision_id": decision_id, "status": "PENDING"},
            {"$set": {"status": "APPROVED", "approved_at": int(time.time())}}
        )
        logger.info(f"[PendingDecisionRepository] Approved {decision_id}")
        return await self.get_by_id(decision_id)
    
    async def reject(self, decision_id: str, reason: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Reject a pending decision."""
        update = {
            "status": "REJECTED",
            "rejected_at": int(time.time())
        }
        if reason:
            update["reject_reason"] = reason
        
        await self.col.update_one(
            {"decision_id": decision_id, "status": "PENDING"},
            {"$set": update}
        )
        logger.info(f"[PendingDecisionRepository] Rejected {decision_id}")
        return await self.get_by_id(decision_id)
    
    async def mark_executed(
        self,
        decision_id: str,
        order_id: Optional[str] = None,
        exchange_order_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Mark decision as executed."""
        update = {
            "status": "EXECUTED",
            "executed_at": int(time.time())
        }
        if order_id:
            update["order_id"] = order_id
        if exchange_order_id:
            update["exchange_order_id"] = exchange_order_id
        
        await self.col.update_one(
            {"decision_id": decision_id},
            {"$set": update}
        )
        logger.info(f"[PendingDecisionRepository] Executed {decision_id}")
        return await self.get_by_id(decision_id)
    
    async def expire_old(self) -> int:
        """Expire old pending decisions."""
        now = int(time.time())
        result = await self.col.update_many(
            {"status": "PENDING", "expires_at": {"$lt": now}},
            {"$set": {"status": "EXPIRED", "expired_at": now}}
        )
        if result.modified_count > 0:
            logger.info(f"[PendingDecisionRepository] Expired {result.modified_count} decisions")
        return result.modified_count
