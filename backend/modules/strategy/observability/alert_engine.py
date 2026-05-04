"""
Alert Engine
============

Phase 2.8: Core alert evaluation logic.

Architecture:
  1. Fetch performance data
  2. Fetch feature performance data
  3. Fetch calibration state
  4. Fetch constraint history
  5. Run all alert rules
  6. Store alerts (with anti-spam)

Execution Model:
  - Background worker (60s interval)
  - Called via `evaluate_alerts()`
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from .alert_rules import AlertRules
from .alert_storage import AlertStorage

logger = logging.getLogger(__name__)


class AlertEngine:
    """
    Core alert evaluation engine.
    
    Coordinates data fetching, rule evaluation, and alert storage.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.storage = AlertStorage(db)
        self.rules = AlertRules()
    
    async def evaluate_alerts(self, experiment_id: str = "market_dynamic") -> Dict[str, Any]:
        """
        Main evaluation loop.
        
        Steps:
          1. Fetch all required data
          2. Run all alert rules
          3. Store new alerts (with anti-spam)
          4. Return summary
        
        Args:
            experiment_id: Experiment to evaluate
        
        Returns:
            {
                "ok": True,
                "alerts_generated": 3,
                "alerts_skipped": 1,
                "new_alerts": [...]
            }
        """
        logger.info(f"[AlertEngine] Starting evaluation for {experiment_id}")
        
        # Step 1: Fetch data
        performance = await self._fetch_performance(experiment_id)
        features = await self._fetch_features(experiment_id)
        calibration_state = await self._fetch_calibration_state(experiment_id)
        constraint_history = await self._fetch_constraint_history(experiment_id)
        
        # Step 2: Run all rule checks
        all_alerts = []
        
        # A. Performance Degradation (24h horizon)
        all_alerts.extend(
            self.rules.check_performance_degradation(performance, horizon="24h")
        )
        
        # B. Feature Breakdown (24h horizon)
        all_alerts.extend(
            self.rules.check_feature_breakdown(features, horizon="24h")
        )
        
        # C. Directional Bias (24h horizon)
        all_alerts.extend(
            self.rules.check_directional_bias(features, horizon="24h")
        )
        
        # D. Calibration Drift
        all_alerts.extend(
            self.rules.check_calibration_drift(calibration_state, features, horizon="24h")
        )
        
        # E. Constraint Instability
        all_alerts.extend(
            self.rules.check_constraint_instability(constraint_history)
        )
        
        # Step 3: Store alerts (with anti-spam)
        alerts_generated = 0
        alerts_skipped = 0
        new_alerts = []
        
        for alert in all_alerts:
            alert_id = await self.storage.store_alert(
                experiment_id=experiment_id,
                alert_type=alert["type"],
                severity=alert["severity"],
                message=alert["message"],
                context=alert["context"]
            )
            
            if alert_id:
                alerts_generated += 1
                new_alerts.append({
                    "id": alert_id,
                    **alert
                })
            else:
                alerts_skipped += 1
        
        logger.info(
            f"[AlertEngine] Evaluation complete: "
            f"{alerts_generated} new, {alerts_skipped} skipped (duplicate)"
        )
        
        return {
            "ok": True,
            "experiment_id": experiment_id,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "alerts_generated": alerts_generated,
            "alerts_skipped": alerts_skipped,
            "new_alerts": new_alerts
        }
    
    async def _fetch_performance(self, experiment_id: str) -> Dict[str, Any]:
        """
        Fetch performance data from shadow_trades.
        
        Uses same aggregation as /performance endpoint.
        """
        try:
            horizon = "24h"
            
            pipeline_overall = [
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
            
            results = await self.db.shadow_trades.aggregate(pipeline_overall).to_list(length=1)
            
            if results:
                return {
                    "overall": results[0]
                }
            
            return {}
        
        except Exception as e:
            logger.error(f"[AlertEngine] Failed to fetch performance: {e}")
            return {}
    
    async def _fetch_features(self, experiment_id: str) -> Dict[str, Any]:
        """
        Fetch feature performance data.
        
        Uses FeaturePerformanceService (same as /features endpoint).
        """
        try:
            from modules.strategy.feature_performance_service import get_feature_performance_service
            
            service = get_feature_performance_service(self.db)
            result = await service.get_feature_performance(experiment_id=experiment_id)
            
            return result
        
        except Exception as e:
            logger.error(f"[AlertEngine] Failed to fetch features: {e}")
            return {}
    
    async def _fetch_calibration_state(self, experiment_id: str) -> Dict[str, Any]:
        """
        Fetch current calibration state.
        
        Returns:
            {
                "experiment_id": "market_dynamic",
                "updated_at": datetime,
                "buckets": {
                    "0.6": {"count": 15, "winrate": 0.6, "adjustment": 0.02},
                    ...
                }
            }
        """
        try:
            state = await self.db.score_calibration_state.find_one(
                {"experiment_id": experiment_id}
            )
            
            return state if state else {}
        
        except Exception as e:
            logger.error(f"[AlertEngine] Failed to fetch calibration state: {e}")
            return {}
    
    async def _fetch_constraint_history(self, experiment_id: str) -> List[Dict[str, Any]]:
        """
        Fetch recent constraint state history (last 24h).
        
        NOTE: This requires storing constraint state changes.
              For MVP, we return empty list (no jitter detection yet).
        
        Returns:
            [
                {"mode": "neutral", "timestamp": datetime, "max_positions": 3},
                {"mode": "defensive", "timestamp": datetime, "max_positions": 2},
                ...
            ]
        """
        try:
            # TODO: Implement constraint_state_history collection
            # For now, return empty (skips jitter detection)
            return []
        
        except Exception as e:
            logger.error(f"[AlertEngine] Failed to fetch constraint history: {e}")
            return []


# Global singleton
_alert_engine = None


def get_alert_engine(db: AsyncIOMotorDatabase) -> AlertEngine:
    """Get or create alert engine."""
    global _alert_engine
    if _alert_engine is None:
        _alert_engine = AlertEngine(db)
    return _alert_engine
