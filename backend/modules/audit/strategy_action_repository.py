"""Strategy Action Repository

Immutable log of ALL meta-level strategy actions.
Every DISABLE/CAP/BOOST/REDUCE is traceable.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class StrategyActionRepository:
    """
    Strategy Action Repository
    
    Logs every meta-level strategy action:
    - DISABLE_STRATEGY
    - CAP_STRATEGY
    - BOOST_STRATEGY
    - REDUCE_STRATEGY
    
    With timestamp, reason, source, and confidence.
    """
    
    def __init__(self, col):
        """
        Initialize with MongoDB collection.
        
        Args:
            col: Motor async collection instance
        """
        self.col = col
        logger.info("StrategyActionRepository initialized")
    
    async def ensure_indexes(self):
        """Create indexes for efficient queries"""
        try:
            await self.col.create_index("timestamp")
            await self.col.create_index("strategy_id")
            await self.col.create_index("action_type")
            await self.col.create_index("trace_id")  # P0.7+: Causal graph lookup
            logger.info("✅ StrategyActionRepository indexes created (P0.7+)")
        except Exception as e:
            logger.error(f"Failed to create strategy action audit indexes: {e}")
    
    async def insert(self, action: Dict[str, Any]) -> None:
        """
        Insert strategy action into audit log.
        
        CRITICAL: This MUST NOT fail and block meta execution.
        
        Args:
            action: Strategy action to audit
        """
        try:
            # Ensure timestamp
            if "timestamp" not in action:
                action["timestamp"] = datetime.now(timezone.utc)
            
            await self.col.insert_one(action)
            logger.debug(
                f"Strategy action audit logged: {action.get('action_type')} "
                f"for {action.get('strategy_id')}"
            )
        except Exception as e:
            # CRITICAL: Audit failure MUST NOT break meta layer
            logger.error(f"❌ Strategy action audit failed (non-blocking): {e}")
    
    async def list(
        self,
        limit: int = 50,
        strategy_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List strategy action audit records.
        
        Args:
            limit: Max records to return
            strategy_id: Filter by strategy (optional)
        
        Returns:
            List of strategy action records (newest first)
        """
        query = {}
        if strategy_id:
            query["strategy_id"] = strategy_id
        
        cursor = self.col.find(query).sort("timestamp", -1).limit(limit)
        records = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for record in records:
            if "_id" in record:
                record["_id"] = str(record["_id"])
        
        return records
    
    async def count(self) -> int:
        """Count total strategy action audit records"""
        return await self.col.count_documents({})
    
    async def get_by_trace_id(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        Get all strategy actions for a trace_id (P0.7+).
        
        Args:
            trace_id: Trace identifier
        
        Returns:
            List of strategy actions (chronological order)
        """
        cursor = self.col.find({"trace_id": trace_id}).sort("timestamp", 1)
        records = await cursor.to_list(length=None)
        
        for record in records:
            if "_id" in record:
                record["_id"] = str(record["_id"])
        
        return records
