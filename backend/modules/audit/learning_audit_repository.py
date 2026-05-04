"""Learning Audit Repository

Immutable log of ALL learning cycles.
Every AF6 learning action is traceable.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class LearningAuditRepository:
    """
    Learning Audit Repository
    
    Logs every AF6 learning cycle:
    - Metrics snapshot
    - Actions generated
    - Actions applied
    - Outcomes
    """
    
    def __init__(self, col):
        """
        Initialize with MongoDB collection.
        
        Args:
            col: Motor async collection instance
        """
        self.col = col
        logger.info("LearningAuditRepository initialized")
    
    async def ensure_indexes(self):
        """Create indexes for efficient queries"""
        try:
            await self.col.create_index("timestamp")
            await self.col.create_index("trace_id")  # P0.7+: Causal graph lookup
            logger.info("✅ LearningAuditRepository indexes created (P0.7+)")
        except Exception as e:
            logger.error(f"Failed to create learning audit indexes: {e}")
    
    async def insert(self, record: Dict[str, Any]) -> None:
        """
        Insert learning audit record.
        
        CRITICAL: This MUST NOT fail and block learning.
        
        Args:
            record: Learning cycle record
        """
        try:
            # Ensure timestamp
            if "timestamp" not in record:
                record["timestamp"] = datetime.now(timezone.utc)
            
            await self.col.insert_one(record)
            logger.debug("Learning audit logged")
        except Exception as e:
            # CRITICAL: Audit failure MUST NOT break learning
            logger.error(f"❌ Learning audit failed (non-blocking): {e}")
    
    async def list(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List learning audit records.
        
        Args:
            limit: Max records to return
        
        Returns:
            List of learning audit records (newest first)
        """
        cursor = self.col.find().sort("timestamp", -1).limit(limit)
        records = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for record in records:
            if "_id" in record:
                record["_id"] = str(record["_id"])
        
        return records
    
    async def count(self) -> int:
        """Count total learning audit records"""
        return await self.col.count_documents({})
    
    async def get_by_trace_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Get learning audit by trace_id (P0.7+).
        
        Args:
            trace_id: Trace identifier
        
        Returns:
            Learning audit record or None
        """
        record = await self.col.find_one({"trace_id": trace_id})
        if record and "_id" in record:
            record["_id"] = str(record["_id"])
        return record
