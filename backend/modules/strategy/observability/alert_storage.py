"""
Alert Storage
=============

Phase 2.8: MongoDB storage for alerts with anti-spam mechanism.

Schema:
  {
    "_id": "...",
    "experiment_id": "market_dynamic",
    "type": "performance_degradation",
    "severity": "critical",
    "message": "Winrate dropped below 0.5",
    "context": {...},
    "dedup_key": "performance_degradation_winrate_0.47",
    "created_at": datetime,
    "resolved": false
  }

Anti-Spam:
  - Deduplication by dedup_key
  - Skip if same alert triggered within last 30 minutes
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Anti-spam window (30 minutes)
DEDUP_WINDOW_SECONDS = 30 * 60


class AlertStorage:
    """
    Manages alert persistence with anti-spam.
    
    Features:
      - MongoDB storage
      - Deduplication (30min window)
      - Resolution tracking
      - Query by experiment/severity/type
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.feature_alerts
    
    async def store_alert(
        self,
        experiment_id: str,
        alert_type: str,
        severity: str,
        message: str,
        context: Dict[str, Any],
        dedup_key: Optional[str] = None
    ) -> Optional[str]:
        """
        Store alert with anti-spam check.
        
        Args:
            experiment_id: Experiment identifier
            alert_type: Alert type (e.g., "performance_degradation")
            severity: "info" | "warning" | "critical"
            message: Human-readable message
            context: Additional context data
            dedup_key: Deduplication key (auto-generated if None)
        
        Returns:
            Alert ID if stored, None if skipped (duplicate)
        """
        # Generate dedup key if not provided
        if dedup_key is None:
            dedup_key = self._generate_dedup_key(alert_type, context)
        
        # Check for recent duplicate
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=DEDUP_WINDOW_SECONDS)
        
        existing = await self.collection.find_one({
            "experiment_id": experiment_id,
            "dedup_key": dedup_key,
            "created_at": {"$gte": cutoff},
            "resolved": False
        })
        
        if existing:
            # Calculate time since last alert
            last_created = existing['created_at']
            if not isinstance(last_created, datetime):
                # Handle string datetime
                from dateutil import parser
                last_created = parser.parse(last_created)
            
            # Ensure timezone-aware
            if last_created.tzinfo is None:
                last_created = last_created.replace(tzinfo=timezone.utc)
            
            time_since = (datetime.now(timezone.utc) - last_created).total_seconds()
            
            logger.debug(
                f"[AlertStorage] Skipped duplicate alert: {dedup_key} "
                f"(last triggered {time_since:.0f}s ago)"
            )
            return None
        
        # Store new alert
        alert = {
            "experiment_id": experiment_id,
            "type": alert_type,
            "severity": severity,
            "message": message,
            "context": context,
            "dedup_key": dedup_key,
            "created_at": datetime.now(timezone.utc),
            "resolved": False,
        }
        
        result = await self.collection.insert_one(alert)
        alert_id = str(result.inserted_id)
        
        logger.info(
            f"[AlertStorage] Stored {severity} alert: {message} "
            f"(id={alert_id}, dedup_key={dedup_key})"
        )
        
        return alert_id
    
    def _generate_dedup_key(self, alert_type: str, context: Dict[str, Any]) -> str:
        """
        Generate deduplication key from alert type and context.
        
        Examples:
            performance_degradation_winrate_0.47
            cluster_degradation_alts_0.42
            calibration_drift_0.6-0.7_worse
        """
        # Extract key context values
        key_parts = [alert_type]
        
        # Common context fields
        for field in ["dimension", "cluster", "timeframe", "side", "bucket"]:
            if field in context:
                key_parts.append(str(context[field]))
        
        # Numeric threshold (rounded)
        for field in ["winrate", "avg_pnl", "threshold"]:
            if field in context:
                value = context[field]
                if isinstance(value, (int, float)):
                    key_parts.append(f"{value:.2f}")
        
        return "_".join(key_parts)
    
    async def get_active_alerts(
        self,
        experiment_id: str,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get active (unresolved) alerts.
        
        Args:
            experiment_id: Experiment to query
            severity: Optional severity filter
            alert_type: Optional type filter
        
        Returns:
            List of active alerts (sorted by created_at desc)
        """
        query = {
            "experiment_id": experiment_id,
            "resolved": False
        }
        
        if severity:
            query["severity"] = severity
        
        if alert_type:
            query["type"] = alert_type
        
        cursor = self.collection.find(query).sort("created_at", -1)
        alerts = await cursor.to_list(length=100)
        
        # Convert _id to string
        for alert in alerts:
            alert["_id"] = str(alert["_id"])
        
        return alerts
    
    async def get_alert_history(
        self,
        experiment_id: str,
        hours: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get alert history (including resolved).
        
        Args:
            experiment_id: Experiment to query
            hours: Lookback window in hours
            limit: Maximum alerts to return
        
        Returns:
            List of alerts (sorted by created_at desc)
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        query = {
            "experiment_id": experiment_id,
            "created_at": {"$gte": cutoff}
        }
        
        cursor = self.collection.find(query).sort("created_at", -1).limit(limit)
        alerts = await cursor.to_list(length=limit)
        
        # Convert _id to string
        for alert in alerts:
            alert["_id"] = str(alert["_id"])
        
        return alerts
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """
        Mark alert as resolved.
        
        Args:
            alert_id: Alert ID to resolve
        
        Returns:
            True if resolved, False if not found
        """
        from bson import ObjectId
        
        result = await self.collection.update_one(
            {"_id": ObjectId(alert_id)},
            {"$set": {"resolved": True, "resolved_at": datetime.now(timezone.utc)}}
        )
        
        if result.modified_count > 0:
            logger.info(f"[AlertStorage] Resolved alert: {alert_id}")
            return True
        
        return False
    
    async def get_alert_counts(self, experiment_id: str) -> Dict[str, int]:
        """
        Get alert counts by severity.
        
        Returns:
            {"info": 2, "warning": 5, "critical": 1}
        """
        pipeline = [
            {"$match": {
                "experiment_id": experiment_id,
                "resolved": False
            }},
            {"$group": {
                "_id": "$severity",
                "count": {"$sum": 1}
            }}
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(length=10)
        
        counts = {
            "info": 0,
            "warning": 0,
            "critical": 0
        }
        
        for result in results:
            severity = result["_id"]
            if severity in counts:
                counts[severity] = result["count"]
        
        return counts


async def create_indexes(db: AsyncIOMotorDatabase):
    """Create indexes for feature_alerts collection."""
    await db.feature_alerts.create_index(
        [("experiment_id", 1), ("created_at", -1)]
    )
    await db.feature_alerts.create_index(
        [("experiment_id", 1), ("resolved", 1), ("severity", 1)]
    )
    await db.feature_alerts.create_index(
        [("dedup_key", 1), ("created_at", -1)]
    )
    
    logger.info("[AlertStorage] Indexes created")
