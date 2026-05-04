"""Execution Audit Repository

Immutable log of ALL execution events.
Append-only, survives restarts.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class ExecutionAuditRepository:
    """
    Execution Audit Repository
    
    Logs every execution event for full traceability:
    - ORDER_SUBMIT_REQUESTED
    - ORDER_ACKNOWLEDGED
    - ORDER_REJECTED
    - ORDER_FILL_RECORDED
    - RECONCILIATION_MISMATCH
    """
    
    def __init__(self, col):
        """
        Initialize with MongoDB collection.
        
        Args:
            col: Motor async collection instance
        """
        self.col = col
        logger.info("ExecutionAuditRepository initialized")
    
    async def ensure_indexes(self):
        """Create indexes for efficient queries"""
        try:
            await self.col.create_index("timestamp")
            await self.col.create_index("event_type")
            await self.col.create_index("client_order_id")
            await self.col.create_index("symbol")
            await self.col.create_index("trace_id")  # P0.7+: Causal graph lookup
            logger.info("✅ ExecutionAuditRepository indexes created (P0.7+)")
        except Exception as e:
            logger.error(f"Failed to create execution audit indexes: {e}")
    
    async def insert(self, event: Dict[str, Any]) -> None:
        """
        Insert execution event into audit log.
        
        CRITICAL: This MUST NOT fail and block execution.
        If audit fails, log error but continue trading.
        
        Args:
            event: Execution event to audit
        """
        try:
            # Ensure timestamp
            if "timestamp" not in event:
                event["timestamp"] = datetime.now(timezone.utc)
            
            await self.col.insert_one(event)
            logger.debug(f"Execution audit logged: {event.get('event_type')}")
        except Exception as e:
            # CRITICAL: Audit failure MUST NOT break execution
            logger.error(f"❌ Execution audit failed (non-blocking): {e}")
    
    async def list(self, limit: int = 100, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List execution audit records.
        
        Args:
            limit: Max records to return
            symbol: Filter by symbol (optional)
        
        Returns:
            List of execution audit records (newest first)
        """
        query = {}
        if symbol:
            query["symbol"] = symbol
        
        cursor = self.col.find(query).sort("timestamp", -1).limit(limit)
        records = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        for record in records:
            if "_id" in record:
                record["_id"] = str(record["_id"])
        
        return records
    
    async def count(self) -> int:
        """Count total execution audit records"""
        return await self.col.count_documents({})
    
    async def get_by_trace_id(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        Get all execution events for a trace_id (P0.7+).
        
        Args:
            trace_id: Trace identifier
        
        Returns:
            List of execution events (chronological order)
        """
        cursor = self.col.find({"trace_id": trace_id}).sort("timestamp", 1)
        records = await cursor.to_list(length=None)
        
        for record in records:
            if "_id" in record:
                record["_id"] = str(record["_id"])
        
        return records
