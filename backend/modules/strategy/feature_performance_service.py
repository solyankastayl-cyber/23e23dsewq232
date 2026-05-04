"""
Feature Performance Service
===========================

Phase 2.7C: Feature Validation Layer

CRITICAL: This is an OBSERVATION-ONLY layer.
It aggregates shadow trade outcomes to validate which features yield alpha.

NO AUTO-ADAPTATION. NO SYSTEM MODIFICATION.
Pure analytics for human insight.

Architecture:
  - Read from shadow_trades collection
  - Aggregate by: cluster, alignment, timeframe, score bucket, side, horizon
  - Return statistics: count, winrate, avg_pnl
  - Flag statistically insignificant results (count < min_sample_size)
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Minimum sample size for valid statistics (anti-noise)
MIN_SAMPLE_SIZE = 10

# Score bucket boundaries (validate DECISIONS, not components)
SCORE_BOUNDARIES = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

# All horizons to analyze
HORIZONS = ["24h", "48h", "7d"]


class FeaturePerformanceService:
    """
    Analyzes which features (cluster, alignment, timeframe, score, side)
    yield alpha vs noise.
    
    Returns horizon-separated aggregations with validity flags.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.shadow_trades
    
    async def get_feature_performance(
        self,
        experiment_id: str = "market_dynamic",
        days: int = None
    ) -> Dict[str, Any]:
        """
        Get feature performance across all dimensions.
        
        Args:
            experiment_id: Which experiment to analyze (default: market_dynamic)
            days: Optional time filter (e.g., last 7 days). None = all history.
        
        Returns:
            {
                "horizons": {
                    "24h": {
                        "by_cluster": [...],
                        "by_alignment": [...],
                        "by_timeframe": [...],
                        "by_score_bucket": [...],
                        "by_side": [...]
                    },
                    ...
                },
                "meta": {
                    "min_sample_size": 10,
                    "total_trades": 120,
                    "experiment_id": "market_dynamic",
                    "generated_at": "2024-01-01T00:00:00Z"
                }
            }
        """
        # Build base match filter
        base_match = {"experiment_id": experiment_id}
        
        if days is not None:
            cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
            base_match["entry_time"] = {"$gte": datetime.fromtimestamp(cutoff, tz=timezone.utc)}
        
        # Count total trades
        total_trades = await self.collection.count_documents(base_match)
        
        # Aggregate for each horizon
        horizons_data = {}
        
        for horizon in HORIZONS:
            logger.info(f"[FeaturePerformance] Aggregating horizon={horizon}")
            
            horizons_data[horizon] = {
                "by_cluster": await self._aggregate_by_cluster(base_match, horizon),
                "by_alignment": await self._aggregate_by_alignment(base_match, horizon),
                "by_timeframe": await self._aggregate_by_timeframe(base_match, horizon),
                "by_score_bucket": await self._aggregate_by_score_bucket(base_match, horizon),
                "by_side": await self._aggregate_by_side(base_match, horizon),
            }
        
        return {
            "horizons": horizons_data,
            "meta": {
                "min_sample_size": MIN_SAMPLE_SIZE,
                "total_trades": total_trades,
                "experiment_id": experiment_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        }
    
    async def _aggregate_by_cluster(
        self,
        base_match: Dict[str, Any],
        horizon: str
    ) -> List[Dict[str, Any]]:
        """
        Aggregate performance by asset cluster (majors/alts/stable).
        
        Returns:
            [
                {
                    "cluster": "majors",
                    "count": 45,
                    "winrate": 0.62,
                    "avg_pnl": 0.012,
                    "valid": true
                },
                ...
            ]
        """
        pipeline = [
            {"$unwind": "$horizons"},
            {"$match": {
                **base_match,
                "horizons.name": horizon,
                "horizons.resolved": True
            }},
            {"$group": {
                "_id": "$features.cluster",
                "count": {"$sum": 1},
                "winrate": {
                    "$avg": {"$cond": [{"$gt": ["$horizons.pnl", 0]}, 1.0, 0.0]}
                },
                "avg_pnl": {"$avg": "$horizons.pnl"},
                "total_pnl": {"$sum": "$horizons.pnl"},
            }},
            {"$sort": {"count": -1}}
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(length=100)
        
        return [
            {
                "cluster": r["_id"] or "unknown",
                "count": r["count"],
                "winrate": round(r["winrate"], 4),
                "avg_pnl": round(r["avg_pnl"], 6),
                "total_pnl": round(r["total_pnl"], 6),
                "valid": r["count"] >= MIN_SAMPLE_SIZE
            }
            for r in results
        ]
    
    async def _aggregate_by_alignment(
        self,
        base_match: Dict[str, Any],
        horizon: str
    ) -> List[Dict[str, Any]]:
        """
        Aggregate performance by market structure alignment.
        
        Returns whether aligned vs misaligned trades perform better.
        """
        pipeline = [
            {"$unwind": "$horizons"},
            {"$match": {
                **base_match,
                "horizons.name": horizon,
                "horizons.resolved": True
            }},
            {"$group": {
                "_id": "$features.market_structure.alignment",
                "count": {"$sum": 1},
                "winrate": {
                    "$avg": {"$cond": [{"$gt": ["$horizons.pnl", 0]}, 1.0, 0.0]}
                },
                "avg_pnl": {"$avg": "$horizons.pnl"},
                "total_pnl": {"$sum": "$horizons.pnl"},
            }},
            {"$sort": {"count": -1}}
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(length=100)
        
        return [
            {
                "alignment": r["_id"] or "unknown",
                "count": r["count"],
                "winrate": round(r["winrate"], 4),
                "avg_pnl": round(r["avg_pnl"], 6),
                "total_pnl": round(r["total_pnl"], 6),
                "valid": r["count"] >= MIN_SAMPLE_SIZE
            }
            for r in results
        ]
    
    async def _aggregate_by_timeframe(
        self,
        base_match: Dict[str, Any],
        horizon: str
    ) -> List[Dict[str, Any]]:
        """
        Aggregate performance by timeframe (1h/4h/1d).
        
        Critical dimension: does 4h signal quality differ from 1h?
        """
        pipeline = [
            {"$unwind": "$horizons"},
            {"$match": {
                **base_match,
                "horizons.name": horizon,
                "horizons.resolved": True
            }},
            {"$group": {
                "_id": "$timeframe",
                "count": {"$sum": 1},
                "winrate": {
                    "$avg": {"$cond": [{"$gt": ["$horizons.pnl", 0]}, 1.0, 0.0]}
                },
                "avg_pnl": {"$avg": "$horizons.pnl"},
                "total_pnl": {"$sum": "$horizons.pnl"},
            }},
            {"$sort": {"count": -1}}
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(length=100)
        
        return [
            {
                "timeframe": r["_id"] or "unknown",
                "count": r["count"],
                "winrate": round(r["winrate"], 4),
                "avg_pnl": round(r["avg_pnl"], 6),
                "total_pnl": round(r["total_pnl"], 6),
                "valid": r["count"] >= MIN_SAMPLE_SIZE
            }
            for r in results
        ]
    
    async def _aggregate_by_score_bucket(
        self,
        base_match: Dict[str, Any],
        horizon: str
    ) -> List[Dict[str, Any]]:
        """
        Aggregate performance by score bucket.
        
        CRITICAL: Validates the DECISION (final score), not confidence.
        
        Buckets:
            - 0.3-0.4: Low
            - 0.4-0.5: Below Average
            - 0.5-0.6: Average
            - 0.6-0.7: Above Average
            - 0.7-0.8: Good
            - 0.8-0.9: Very Good
            - 0.9-1.0: Excellent
        """
        pipeline = [
            {"$unwind": "$horizons"},
            {"$match": {
                **base_match,
                "horizons.name": horizon,
                "horizons.resolved": True
            }},
            {"$bucket": {
                "groupBy": "$features.score",
                "boundaries": SCORE_BOUNDARIES,
                "default": "other",
                "output": {
                    "count": {"$sum": 1},
                    "winrate": {
                        "$avg": {"$cond": [{"$gt": ["$horizons.pnl", 0]}, 1.0, 0.0]}
                    },
                    "avg_pnl": {"$avg": "$horizons.pnl"},
                    "total_pnl": {"$sum": "$horizons.pnl"},
                }
            }}
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(length=100)
        
        # Format bucket labels
        bucket_labels = {
            0.3: "0.3-0.4",
            0.4: "0.4-0.5",
            0.5: "0.5-0.6",
            0.6: "0.6-0.7",
            0.7: "0.7-0.8",
            0.8: "0.8-0.9",
            0.9: "0.9-1.0",
        }
        
        return [
            {
                "score_bucket": bucket_labels.get(r["_id"], str(r["_id"])),
                "count": r["count"],
                "winrate": round(r["winrate"], 4),
                "avg_pnl": round(r["avg_pnl"], 6),
                "total_pnl": round(r["total_pnl"], 6),
                "valid": r["count"] >= MIN_SAMPLE_SIZE
            }
            for r in results
        ]
    
    async def _aggregate_by_side(
        self,
        base_match: Dict[str, Any],
        horizon: str
    ) -> List[Dict[str, Any]]:
        """
        Aggregate performance by trade side (LONG/SHORT).
        
        CRITICAL dimension: system may be biased toward one direction.
        
        Example insight:
            LONG: 65% winrate
            SHORT: 42% winrate
            → System has directional bias, needs calibration
        """
        pipeline = [
            {"$unwind": "$horizons"},
            {"$match": {
                **base_match,
                "horizons.name": horizon,
                "horizons.resolved": True
            }},
            {"$group": {
                "_id": "$side",
                "count": {"$sum": 1},
                "winrate": {
                    "$avg": {"$cond": [{"$gt": ["$horizons.pnl", 0]}, 1.0, 0.0]}
                },
                "avg_pnl": {"$avg": "$horizons.pnl"},
                "total_pnl": {"$sum": "$horizons.pnl"},
            }},
            {"$sort": {"count": -1}}
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(length=100)
        
        return [
            {
                "side": r["_id"] or "unknown",
                "count": r["count"],
                "winrate": round(r["winrate"], 4),
                "avg_pnl": round(r["avg_pnl"], 6),
                "total_pnl": round(r["total_pnl"], 6),
                "valid": r["count"] >= MIN_SAMPLE_SIZE
            }
            for r in results
        ]


# Global singleton
_feature_performance_service = None


def get_feature_performance_service(db: AsyncIOMotorDatabase) -> FeaturePerformanceService:
    """Get or create feature performance service."""
    global _feature_performance_service
    if _feature_performance_service is None:
        _feature_performance_service = FeaturePerformanceService(db)
    return _feature_performance_service
