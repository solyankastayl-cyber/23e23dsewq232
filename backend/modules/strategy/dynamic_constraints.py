"""
Dynamic Constraints
===================

Phase 2.7A: Adaptive position sizing based on market structure and performance.

System adjusts max_open_positions dynamically:
- Aligned + strong performance → Aggressive (5 pos)
- Divergent + weak performance → Defensive (2 pos)
- Default → Neutral (3 pos)

This is NOT ML. This is rule-based adaptation based on empirical outcomes.
"""

import logging
from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class DynamicConstraints:
    """
    Dynamically adjusts allocation constraints based on performance.
    
    Architecture:
      Performance Data → Rules → Adjusted Constraints → Allocator
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def get_constraints(
        self,
        horizon: str = "24h",
        min_samples: int = 10
    ) -> Dict[str, Any]:
        """
        Calculate dynamic constraints based on recent performance.
        
        Args:
            horizon: Time horizon to analyze
            min_samples: Minimum trades needed for adaptation
            
        Returns:
            Constraints dict with max_positions, mode, reason
        """
        # Default constraints (fallback)
        default = {
            "max_open_positions": 3,
            "max_per_cluster": 2,
            "max_per_symbol": 1,
            "max_total_risk": 0.30,
            "mode": "neutral",
            "reason": "default (insufficient data)",
        }
        
        try:
            # Get performance by alignment
            performance = await self._get_performance_by_alignment(horizon)
            
            if not performance:
                logger.debug("[DynamicConstraints] No performance data, using defaults")
                return default
            
            aligned = performance.get("aligned", {})
            divergent = performance.get("divergent", {})
            
            aligned_count = aligned.get("count", 0)
            divergent_count = divergent.get("count", 0)
            
            # Check if we have enough samples
            if aligned_count < min_samples and divergent_count < min_samples:
                logger.debug(
                    f"[DynamicConstraints] Insufficient samples "
                    f"(aligned={aligned_count}, divergent={divergent_count}), "
                    f"using defaults"
                )
                return default
            
            aligned_wr = aligned.get("winrate", 0.0)
            divergent_wr = divergent.get("winrate", 0.0)
            
            # Decision logic
            constraints = self._apply_rules(
                aligned_wr, aligned_count,
                divergent_wr, divergent_count
            )
            
            logger.info(
                f"[DynamicConstraints] Mode: {constraints['mode']}, "
                f"max_positions: {constraints['max_open_positions']}, "
                f"reason: {constraints['reason']}"
            )
            
            return constraints
            
        except Exception as e:
            logger.error(f"[DynamicConstraints] Error: {e}", exc_info=True)
            return default
    
    def _apply_rules(
        self,
        aligned_wr: float,
        aligned_count: int,
        divergent_wr: float,
        divergent_count: int
    ) -> Dict[str, Any]:
        """
        Apply adaptation rules.
        
        Rules:
        1. Aligned + high WR → Aggressive
        2. Divergent + low WR → Defensive
        3. Mixed performance → Neutral
        """
        # Rule 1: Aggressive mode
        if aligned_count >= 10 and aligned_wr > 0.65:
            return {
                "max_open_positions": 5,
                "max_per_cluster": 3,
                "max_per_symbol": 1,
                "max_total_risk": 0.40,
                "mode": "aggressive",
                "reason": f"aligned_wr={aligned_wr:.2f} > 0.65",
            }
        
        # Rule 2: Defensive mode
        if divergent_count >= 10 and divergent_wr < 0.50:
            return {
                "max_open_positions": 2,
                "max_per_cluster": 1,
                "max_per_symbol": 1,
                "max_total_risk": 0.15,
                "mode": "defensive",
                "reason": f"divergent_wr={divergent_wr:.2f} < 0.50",
            }
        
        # Rule 3: Neutral (default)
        return {
            "max_open_positions": 3,
            "max_per_cluster": 2,
            "max_per_symbol": 1,
            "max_total_risk": 0.25,
            "mode": "neutral",
            "reason": f"balanced (aligned_wr={aligned_wr:.2f}, divergent_wr={divergent_wr:.2f})",
        }
    
    async def _get_performance_by_alignment(self, horizon: str) -> Dict[str, Any]:
        """
        Get performance metrics grouped by market alignment.
        
        Returns:
            {
                "aligned": {"count": N, "winrate": X, "avg_pnl": Y},
                "divergent": {"count": M, "winrate": Z, "avg_pnl": W}
            }
        """
        pipeline = [
            {"$unwind": "$horizons"},
            {"$match": {
                "experiment_id": "market_dynamic",
                "horizons.name": horizon,
                "horizons.resolved": True
            }},
            {"$group": {
                "_id": "$features.market_structure.alignment",
                "count": {"$sum": 1},
                "winrate": {
                    "$avg": {"$cond": [{"$gt": ["$horizons.pnl", 0]}, 1.0, 0.0]}
                },
                "avg_pnl": {"$avg": "$horizons.pnl"}
            }}
        ]
        
        results = await self.db.shadow_trades.aggregate(pipeline).to_list(length=10)
        
        # Convert to dict
        performance = {}
        for r in results:
            alignment = r["_id"]
            if alignment:  # Skip None values
                performance[alignment] = {
                    "count": r["count"],
                    "winrate": r["winrate"],
                    "avg_pnl": r["avg_pnl"]
                }
        
        return performance


# Singleton
_dynamic_constraints: Dict[str, DynamicConstraints] = {}


def get_dynamic_constraints(db: AsyncIOMotorDatabase) -> DynamicConstraints:
    """Get or create dynamic constraints instance."""
    global _dynamic_constraints
    
    # Use DB address as key (thread-safe singleton per DB)
    key = str(id(db))
    
    if key not in _dynamic_constraints:
        _dynamic_constraints[key] = DynamicConstraints(db)
    
    return _dynamic_constraints[key]
