"""
Execution Event Repository
Simple read-only repository for execution_events collection.

Used by Analytics Service to query execution events.
"""

from typing import List, Dict, Any


class ExecutionEventRepository:
    """
    Read-only repository for execution_events collection.
    
    Provides simple queries for analytics aggregations.
    """
    
    def __init__(self, db):
        """
        Initialize repository.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db.execution_events
    
    async def find_by_type(self, event_type: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Find events by type.
        
        Args:
            event_type: Event type (e.g., "DYNAMIC_RISK_APPROVED", "ORDER_FILLED")
            limit: Maximum number of events to return
        
        Returns:
            List of event documents
        """
        cursor = self.collection.find({"type": event_type}).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def find_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find recent events (all types).
        
        Args:
            limit: Maximum number of events to return
        
        Returns:
            List of event documents sorted by timestamp descending
        """
        cursor = self.collection.find({}).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)
