"""
Score Calibrator
================

Phase 2.7B: Empirical score adjustment based on historical performance.

Architecture:
  Online System (fast):
    - Loads calibration state from cache/DB
    - Applies adjustment to base_score
    
  Offline System (slow):
    - Recalculates adjustments from shadow_trades
    - Updates DB (with 6h cooldown)
    - Refreshes cache

This is NOT ML. This is empirical validation of ranking formula.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


# Fixed bucket boundaries
SCORE_BUCKETS = [0.4, 0.5, 0.6, 0.7]

# Adjustment bounds
MAX_ADJUSTMENT = 0.05
MIN_ADJUSTMENT = -0.05

# Minimum samples for calibration
MIN_SAMPLES_FOR_CALIBRATION = 10


def get_bucket(score: float) -> float:
    """
    Map score to fixed bucket.
    
    Args:
        score: Base score (0.0 - 1.0)
        
    Returns:
        Bucket key (0.4, 0.5, 0.6, or 0.7)
    """
    if score < 0.5:
        return 0.4
    elif score < 0.6:
        return 0.5
    elif score < 0.7:
        return 0.6
    else:
        return 0.7


class ScoreCalibrator:
    """
    Online calibration system.
    
    Loads state from DB/cache and applies adjustments during scoring.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.score_calibration_state
        
        # In-memory cache
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_loaded_at: Optional[datetime] = None
    
    async def get_adjustment(
        self,
        base_score: float,
        experiment_id: str = "market_dynamic"
    ) -> Dict[str, Any]:
        """
        Get calibration adjustment for a score.
        
        Args:
            base_score: Base score from ranking formula
            experiment_id: Experiment ID
            
        Returns:
            {
                "adjustment": float,
                "bucket": float,
                "count": int,
                "winrate": float
            }
        """
        # Get bucket
        bucket = get_bucket(base_score)
        
        # Load calibration state
        state = await self._get_state(experiment_id)
        
        if not state or "buckets" not in state:
            # No calibration data yet
            return {
                "adjustment": 0.0,
                "bucket": bucket,
                "count": 0,
                "winrate": 0.0,
                "reason": "no_calibration_data"
            }
        
        bucket_data = state["buckets"].get(str(bucket), {})
        
        if not bucket_data:
            # Bucket not calibrated
            return {
                "adjustment": 0.0,
                "bucket": bucket,
                "count": 0,
                "winrate": 0.0,
                "reason": "bucket_not_calibrated"
            }
        
        # Return adjustment
        return {
            "adjustment": bucket_data.get("adjustment", 0.0),
            "bucket": bucket,
            "count": bucket_data.get("count", 0),
            "winrate": bucket_data.get("winrate", 0.0),
            "reason": "applied"
        }
    
    async def _get_state(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get calibration state (from cache or DB).
        
        Uses cache if fresh (< 10 minutes old).
        """
        now = datetime.now(timezone.utc)
        
        # Check cache
        if self._cache and self._cache_loaded_at:
            cache_age = (now - self._cache_loaded_at).total_seconds()
            if cache_age < 600:  # 10 minutes
                return self._cache
        
        # Load from DB
        state = await self.collection.find_one({"experiment_id": experiment_id})
        
        if state:
            self._cache = state
            self._cache_loaded_at = now
            logger.debug("[ScoreCalibrator] Loaded state from DB (cache refreshed)")
        
        return state
    
    def invalidate_cache(self):
        """Invalidate cache (called after recalibration)."""
        self._cache = None
        self._cache_loaded_at = None


class ScoreCalibrationWorker:
    """
    Offline calibration system.
    
    Background worker that recalculates adjustments from shadow_trades.
    Respects 6h cooldown.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, calibrator: ScoreCalibrator):
        self.db = db
        self.calibrator = calibrator
        self.collection = db.score_calibration_state
    
    async def recalibrate_if_needed(
        self,
        experiment_id: str = "market_dynamic",
        horizon: str = "24h",
        cooldown_hours: int = 6
    ) -> bool:
        """
        Recalculate calibration if cooldown period has passed.
        
        Args:
            experiment_id: Experiment ID
            horizon: Time horizon for performance
            cooldown_hours: Minimum hours between recalibrations
            
        Returns:
            True if recalibration happened
        """
        now = datetime.now(timezone.utc)
        
        # Check last update time
        state = await self.collection.find_one({"experiment_id": experiment_id})
        
        if state and "updated_at" in state:
            last_update = state["updated_at"]
            if isinstance(last_update, str):
                last_update = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            
            time_since_update = now - last_update
            
            if time_since_update < timedelta(hours=cooldown_hours):
                logger.debug(
                    f"[ScoreCalibrator] Cooldown active "
                    f"(last update {time_since_update.total_seconds()/3600:.1f}h ago)"
                )
                return False
        
        # Perform recalibration
        logger.info("[ScoreCalibrator] Starting recalibration...")
        
        try:
            new_state = await self._calculate_calibration(experiment_id, horizon)
            
            # Save to DB
            await self.collection.update_one(
                {"experiment_id": experiment_id},
                {"$set": new_state},
                upsert=True
            )
            
            # Invalidate cache
            self.calibrator.invalidate_cache()
            
            logger.info(
                f"[ScoreCalibrator] Recalibration complete: "
                f"{len(new_state['buckets'])} buckets updated"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"[ScoreCalibrator] Recalibration failed: {e}", exc_info=True)
            return False
    
    async def _calculate_calibration(
        self,
        experiment_id: str,
        horizon: str
    ) -> Dict[str, Any]:
        """
        Calculate new calibration state from shadow_trades.
        
        Returns:
            {
                "experiment_id": str,
                "updated_at": datetime,
                "buckets": {
                    "0.4": {"count": N, "winrate": X, "adjustment": Y},
                    ...
                }
            }
        """
        # Query performance by score bucket
        pipeline = [
            {"$unwind": "$horizons"},
            {"$match": {
                "experiment_id": experiment_id,
                "horizons.name": horizon,
                "horizons.resolved": True
            }},
            {"$project": {
                "score": "$features.score",
                "pnl": "$horizons.pnl"
            }},
            {"$bucket": {
                "groupBy": "$score",
                "boundaries": SCORE_BUCKETS + [1.0],
                "default": "other",
                "output": {
                    "count": {"$sum": 1},
                    "winrate": {
                        "$avg": {"$cond": [{"$gt": ["$pnl", 0]}, 1.0, 0.0]}
                    },
                    "avg_pnl": {"$avg": "$pnl"}
                }
            }}
        ]
        
        results = await self.db.shadow_trades.aggregate(pipeline).to_list(length=10)
        
        # Process results
        buckets = {}
        
        for r in results:
            bucket_key = r["_id"]
            
            if bucket_key == "other":
                continue
            
            count = r["count"]
            winrate = r["winrate"]
            
            # Calculate adjustment
            adjustment = self._calculate_adjustment(count, winrate)
            
            buckets[str(bucket_key)] = {
                "count": count,
                "winrate": round(winrate, 4),
                "avg_pnl": round(r["avg_pnl"], 6),
                "adjustment": round(adjustment, 4)
            }
        
        return {
            "experiment_id": experiment_id,
            "updated_at": datetime.now(timezone.utc),
            "buckets": buckets
        }
    
    def _calculate_adjustment(self, count: int, winrate: float) -> float:
        """
        Calculate adjustment based on performance.
        
        Rules:
        - count < 10 → no adjustment
        - winrate > 0.6 → positive boost
        - winrate < 0.5 → negative penalty
        - else → no adjustment
        
        Bounded to [MIN_ADJUSTMENT, MAX_ADJUSTMENT]
        """
        if count < MIN_SAMPLES_FOR_CALIBRATION:
            return 0.0
        
        if winrate > 0.6:
            adjustment = +0.03
        elif winrate < 0.5:
            adjustment = -0.03
        else:
            adjustment = 0.0
        
        # Apply bounds
        adjustment = max(MIN_ADJUSTMENT, min(MAX_ADJUSTMENT, adjustment))
        
        return adjustment


# Singleton
_score_calibrator: Optional[ScoreCalibrator] = None


def get_score_calibrator(db: AsyncIOMotorDatabase) -> ScoreCalibrator:
    """Get or create singleton calibrator."""
    global _score_calibrator
    
    if _score_calibrator is None:
        _score_calibrator = ScoreCalibrator(db)
    
    return _score_calibrator
