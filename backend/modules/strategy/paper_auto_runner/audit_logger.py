"""
Simple Audit Logger
====================

Phase 3.0B: Lightweight audit logger for auto-runner decisions.

Logs to MongoDB collection: auto_runner_audit
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Simple audit logger for auto-runner decisions.
    
    Logs all auto-run decisions:
      - AUTO_RUN_EXECUTED
      - AUTO_RUN_SKIPPED
      - AUTO_RUN_ERROR
      - AUTO_RUN_LOOP_ERROR
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize audit logger.
        
        Args:
            db: MongoDB database
        """
        self.db = db
        self.collection = db.auto_runner_audit
    
    async def log(self, event: Dict[str, Any]):
        """
        Log audit event.
        
        Args:
            event: Event data to log
        """
        try:
            # Ensure timestamp
            if "timestamp" not in event:
                event["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            await self.collection.insert_one(event)
            
            logger.debug(f"[AuditLogger] Logged: {event.get('decision', 'UNKNOWN')}")
        
        except Exception as e:
            logger.error(f"[AuditLogger] Failed to log event: {e}")
    
    async def get_recent_logs(
        self,
        experiment_id: str = "market_dynamic",
        limit: int = 50
    ) -> list:
        """
        Get recent audit logs.
        
        Args:
            experiment_id: Experiment ID
            limit: Max logs to return
        
        Returns:
            List of audit log entries
        """
        cursor = self.collection.find(
            {"experiment_id": experiment_id}
        ).sort("timestamp", -1).limit(limit)
        
        logs = await cursor.to_list(length=limit)
        
        # Convert _id to string
        for log in logs:
            log["_id"] = str(log["_id"])
        
        return logs
