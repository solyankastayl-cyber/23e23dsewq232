"""Decision Audit Repository

Immutable log of ALL FinalGate decisions.
Every decision is traceable with full context.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class DecisionAuditRepository:
    """
    Decision Audit Repository
    
    Logs every FinalGate decision with:
    - Raw decision from strategy
    - Enforced decision after all layers
    - Reason chain (why modified)
    - Portfolio state
    - Meta state
    - System health state
    """
    
    def __init__(self, col):
        """
        Initialize with MongoDB collection.
        
        Args:
            col: Motor async collection instance
        """
        self.col = col
        logger.info("DecisionAuditRepository initialized")
    
    async def ensure_indexes(self):
        """Create indexes for efficient queries"""
        try:
            await self.col.create_index("timestamp")
            await self.col.create_index("symbol")
            await self.col.create_index("final_action")
            await self.col.create_index("trace_id")  # P0.7+: Causal graph lookup
            logger.info("✅ DecisionAuditRepository indexes created (P0.7+)")
        except Exception as e:
            logger.error(f"Failed to create decision audit indexes: {e}")
    
    async def insert(self, record: Dict[str, Any]) -> None:
        """
        Insert decision audit record.
        
        CRITICAL: This MUST NOT fail and block decision flow.
        
        Args:
            record: Decision audit record
        """
        try:
            # Ensure timestamp
            if "timestamp" not in record:
                record["timestamp"] = datetime.now(timezone.utc)
            
            await self.col.insert_one(record)
            logger.debug(f"Decision audit logged: {record.get('final_action')} for {record.get('symbol')}")
        except Exception as e:
            # CRITICAL: Audit failure MUST NOT break trading
            logger.error(f"❌ Decision audit failed (non-blocking): {e}")
    
    async def list(self, limit: int = 50, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List decision audit records.
        
        Args:
            limit: Max records to return
            symbol: Filter by symbol (optional)
        
        Returns:
            List of decision audit records (newest first)
        """
        query = {}
        if symbol:
            query["symbol"] = symbol
        
        cursor = self.col.find(query).sort("timestamp", -1).limit(limit)
        records = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for record in records:
            if "_id" in record:
                record["_id"] = str(record["_id"])
        
        return records
    
    async def count(self) -> int:
        """Count total decision audit records"""
        return await self.col.count_documents({})
    
    async def get_by_trace_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Get decision audit by trace_id (P0.7+).
        
        Args:
            trace_id: Trace identifier
        
        Returns:
            Decision audit record or None
        """
        record = await self.col.find_one({"trace_id": trace_id})
        if record and "_id" in record:
            record["_id"] = str(record["_id"])
        return record
