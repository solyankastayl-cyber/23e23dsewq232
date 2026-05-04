"""
Health Service
==============

Phase 2.8: System health status aggregation.

Endpoint: GET /api/experiments/market_dynamic/health

Response:
  {
    "status": "healthy" | "warning" | "critical",
    "summary": {...},
    "alerts": [...],
    "constraints": {...},
    "calibration": {...}
  }
"""

import logging
from typing import Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from .alert_storage import AlertStorage

logger = logging.getLogger(__name__)


class HealthService:
    """
    Aggregates system health status.
    
    Combines:
      - Active alerts
      - Performance summary
      - Constraint state
      - Calibration state
    
    Returns overall health status (healthy/warning/critical).
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.alert_storage = AlertStorage(db)
    
    async def get_health_status(self, experiment_id: str = "market_dynamic") -> Dict[str, Any]:
        """
        Get comprehensive health status.
        
        Args:
            experiment_id: Experiment to check
        
        Returns:
            {
                "status": "healthy" | "warning" | "critical",
                "summary": {
                    "winrate": 0.52,
                    "avg_pnl": 0.004,
                    "total_trades": 120
                },
                "alerts": [
                    {
                        "type": "cluster_degradation",
                        "severity": "warning",
                        "message": "Alts underperforming (winrate 0.42)"
                    }
                ],
                "alert_counts": {
                    "info": 0,
                    "warning": 2,
                    "critical": 1
                },
                "constraints": {
                    "mode": "defensive",
                    "max_positions": 2
                },
                "calibration": {
                    "active": true,
                    "last_updated": "..."
                }
            }
        """
        # Fetch all components
        alerts = await self._fetch_active_alerts(experiment_id)
        alert_counts = await self.alert_storage.get_alert_counts(experiment_id)
        summary = await self._fetch_performance_summary(experiment_id)
        constraints = await self._fetch_constraints_state(experiment_id)
        calibration = await self._fetch_calibration_summary(experiment_id)
        
        # Determine overall status
        status = self._determine_status(alert_counts)
        
        return {
            "status": status,
            "summary": summary,
            "alerts": alerts,
            "alert_counts": alert_counts,
            "constraints": constraints,
            "calibration": calibration,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _determine_status(self, alert_counts: Dict[str, int]) -> str:
        """
        Determine overall health status from alert counts.
        
        Logic:
          - Any critical alert → "critical"
          - 3+ warnings → "warning"
          - Otherwise → "healthy"
        
        Args:
            alert_counts: {"info": 0, "warning": 2, "critical": 1}
        
        Returns:
            "healthy" | "warning" | "critical"
        """
        if alert_counts.get("critical", 0) > 0:
            return "critical"
        
        if alert_counts.get("warning", 0) >= 3:
            return "warning"
        
        return "healthy"
    
    async def _fetch_active_alerts(self, experiment_id: str) -> list:
        """
        Fetch active alerts (simplified view).
        
        Returns only essential fields for health endpoint.
        """
        alerts = await self.alert_storage.get_active_alerts(experiment_id)
        
        # Simplify for health endpoint
        simplified = []
        for alert in alerts:
            simplified.append({
                "type": alert["type"],
                "severity": alert["severity"],
                "message": alert["message"],
                "created_at": alert["created_at"].isoformat() if isinstance(alert["created_at"], datetime) else alert["created_at"]
            })
        
        return simplified
    
    async def _fetch_performance_summary(self, experiment_id: str) -> Dict[str, Any]:
        """
        Fetch performance summary (24h horizon).
        
        Returns:
            {
                "winrate": 0.52,
                "avg_pnl": 0.004,
                "total_trades": 120
            }
        """
        try:
            horizon = "24h"
            
            pipeline = [
                {"$unwind": "$horizons"},
                {"$match": {
                    "experiment_id": experiment_id,
                    "horizons.name": horizon,
                    "horizons.resolved": True
                }},
                {"$group": {
                    "_id": None,
                    "total_trades": {"$sum": 1},
                    "winrate": {
                        "$avg": {"$cond": [{"$gt": ["$horizons.pnl", 0]}, 1.0, 0.0]}
                    },
                    "avg_pnl": {"$avg": "$horizons.pnl"},
                }}
            ]
            
            results = await self.db.shadow_trades.aggregate(pipeline).to_list(length=1)
            
            if results:
                r = results[0]
                return {
                    "winrate": round(r.get("winrate", 0), 4),
                    "avg_pnl": round(r.get("avg_pnl", 0), 6),
                    "total_trades": r.get("total_trades", 0)
                }
            
            return {
                "winrate": 0,
                "avg_pnl": 0,
                "total_trades": 0
            }
        
        except Exception as e:
            logger.error(f"[HealthService] Failed to fetch performance summary: {e}")
            return {
                "winrate": 0,
                "avg_pnl": 0,
                "total_trades": 0
            }
    
    async def _fetch_constraints_state(self, experiment_id: str) -> Dict[str, Any]:
        """
        Fetch current dynamic constraints state.
        
        Returns:
            {
                "mode": "defensive",
                "max_positions": 2
            }
        """
        try:
            # Get latest snapshot (has constraints info)
            snapshot = await self.db.market_dynamic_snapshots.find_one(
                {"experiment_id": experiment_id},
                sort=[("created_at", -1)]
            )
            
            if snapshot and "constraints" in snapshot:
                constraints = snapshot["constraints"]
                return {
                    "mode": constraints.get("mode", "neutral"),
                    "max_positions": constraints.get("max_positions", 3)
                }
            
            return {
                "mode": "neutral",
                "max_positions": 3
            }
        
        except Exception as e:
            logger.error(f"[HealthService] Failed to fetch constraints state: {e}")
            return {
                "mode": "unknown",
                "max_positions": 3
            }
    
    async def _fetch_calibration_summary(self, experiment_id: str) -> Dict[str, Any]:
        """
        Fetch calibration summary.
        
        Returns:
            {
                "active": true,
                "last_updated": "2024-01-01T00:00:00Z"
            }
        """
        try:
            state = await self.db.score_calibration_state.find_one(
                {"experiment_id": experiment_id}
            )
            
            if state:
                updated_at = state.get("updated_at")
                return {
                    "active": True,
                    "last_updated": updated_at.isoformat() if isinstance(updated_at, datetime) else str(updated_at)
                }
            
            return {
                "active": False,
                "last_updated": None
            }
        
        except Exception as e:
            logger.error(f"[HealthService] Failed to fetch calibration summary: {e}")
            return {
                "active": False,
                "last_updated": None
            }


# Global singleton
_health_service = None


def get_health_service(db: AsyncIOMotorDatabase) -> HealthService:
    """Get or create health service."""
    global _health_service
    if _health_service is None:
        _health_service = HealthService(db)
    return _health_service
