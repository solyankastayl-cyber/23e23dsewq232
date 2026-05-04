"""
Execution Quality Service
==========================

Phase 3.1: Aggregate matched pairs → compute metrics → evaluate gates.

Flow:
  1. ExecutionComparator → matched pairs
  2. Aggregate friction metrics
  3. Compute execution quality
  4. ExecutionQualityRules → verdict

Output:
  {
    "summary": {
      "matched_pairs": 25,
      "shadow_trades": 30,
      "paper_positions": 28,
      "match_coverage": 0.83,
      "execution_quality": 0.0015,
      "shadow_winrate": 0.60,
      "paper_winrate": 0.56,
      "winrate_delta": -0.04
    },
    "frictions": {
      "policy_rejection_rate": 0.20,
      "cooldown_miss_rate": 0.10,
      "avg_entry_delay_pct": 0.0018,
      "max_entry_delay_pct": 0.0045
    },
    "verdict": {
      "state": "ready",
      "reason": "All gates passed",
      "gates_passed": ["gate1", "gate2", ...],
      "gates_failed": []
    },
    "thresholds": {...}
  }
"""

import logging
from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from .execution_comparator import ExecutionComparator
from .execution_quality_rules import ExecutionQualityRules

logger = logging.getLogger(__name__)


class ExecutionQualityService:
    """
    Aggregates execution quality metrics and evaluates gates.
    
    Responsibilities:
      - Fetch matched pairs (via comparator)
      - Calculate aggregate metrics
      - Compute frictions (policy rejection, cooldown miss)
      - Evaluate verdict via rules
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.comparator = ExecutionComparator(db)
        self.rules = ExecutionQualityRules()
        
        # Collections
        self.shadow_collection = db.shadow_trades
        self.paper_decisions_collection = db.paper_decisions
        self.paper_positions_collection = db.paper_positions
    
    async def get_execution_quality(
        self,
        experiment_id: str = "market_dynamic",
        horizon: str = "24h"
    ) -> Dict[str, Any]:
        """
        Get complete execution quality report.
        
        Args:
            experiment_id: Experiment ID
            horizon: Time horizon (24h)
        
        Returns:
            {
              "summary": {...},
              "frictions": {...},
              "verdict": {...},
              "thresholds": {...}
            }
        """
        logger.info(f"[ExecutionQuality] Computing report for {experiment_id}, horizon={horizon}")
        
        # 1. Get matched pairs
        matched_pairs = await self.comparator.get_matched_pairs(
            experiment_id=experiment_id,
            horizon=horizon
        )
        
        # 2. Get counts for coverage
        shadow_count = await self._count_shadow_trades(experiment_id, horizon)
        paper_count = await self._count_paper_positions(experiment_id)
        
        # 3. Calculate summary metrics
        summary = self._calculate_summary(
            matched_pairs=matched_pairs,
            shadow_count=shadow_count,
            paper_count=paper_count
        )
        
        # 4. Calculate frictions
        frictions = await self._calculate_frictions(
            experiment_id=experiment_id,
            matched_pairs=matched_pairs,
            shadow_count=shadow_count
        )
        
        # 5. Build metrics payload
        metrics = {
            "summary": summary,
            "frictions": frictions
        }
        
        # 6. Evaluate verdict
        verdict = self.rules.evaluate_verdict(metrics)
        
        # 7. Get thresholds
        thresholds = self.rules.get_thresholds()
        
        return {
            "summary": summary,
            "frictions": frictions,
            "verdict": verdict,
            "thresholds": thresholds
        }
    
    def _calculate_summary(
        self,
        matched_pairs: list,
        shadow_count: int,
        paper_count: int
    ) -> Dict[str, Any]:
        """
        Calculate summary metrics from matched pairs.
        
        Args:
            matched_pairs: List of matched pairs
            shadow_count: Total shadow trades
            paper_count: Total paper positions
        
        Returns:
            {
              "matched_pairs": 25,
              "shadow_trades": 30,
              "paper_positions": 28,
              "match_coverage": 0.83,
              "execution_quality": 0.0015,
              "shadow_winrate": 0.60,
              "paper_winrate": 0.56,
              "winrate_delta": -0.04
            }
        """
        n_pairs = len(matched_pairs)
        
        if n_pairs == 0:
            return {
                "matched_pairs": 0,
                "shadow_trades": shadow_count,
                "paper_positions": paper_count,
                "match_coverage": 0.0,
                "execution_quality": 0.0,
                "shadow_winrate": 0.0,
                "paper_winrate": 0.0,
                "winrate_delta": 0.0
            }
        
        # Match coverage: matched / shadow
        match_coverage = n_pairs / shadow_count if shadow_count > 0 else 0.0
        
        # Execution quality: avg(paper_pnl - shadow_pnl)
        execution_deltas = [pair["execution_delta"] for pair in matched_pairs]
        execution_quality = sum(execution_deltas) / len(execution_deltas)
        
        # Shadow winrate
        shadow_wins = sum(1 for pair in matched_pairs if pair["shadow_pnl"] > 0)
        shadow_winrate = shadow_wins / n_pairs
        
        # Paper winrate
        paper_wins = sum(1 for pair in matched_pairs if pair["paper_pnl"] > 0)
        paper_winrate = paper_wins / n_pairs
        
        # Winrate delta
        winrate_delta = paper_winrate - shadow_winrate
        
        return {
            "matched_pairs": n_pairs,
            "shadow_trades": shadow_count,
            "paper_positions": paper_count,
            "match_coverage": round(match_coverage, 4),
            "execution_quality": round(execution_quality, 6),
            "shadow_winrate": round(shadow_winrate, 4),
            "paper_winrate": round(paper_winrate, 4),
            "winrate_delta": round(winrate_delta, 4)
        }
    
    async def _calculate_frictions(
        self,
        experiment_id: str,
        matched_pairs: list,
        shadow_count: int
    ) -> Dict[str, Any]:
        """
        Calculate friction metrics.
        
        Frictions:
          - policy_rejection_rate: REJECTED decisions / total decisions
          - cooldown_miss_rate: (shadow - matched) / shadow
          - avg_entry_delay_pct: avg slippage from matched pairs
          - max_entry_delay_pct: max slippage from matched pairs
        
        Args:
            experiment_id: Experiment ID
            matched_pairs: List of matched pairs
            shadow_count: Total shadow trades
        
        Returns:
            {
              "policy_rejection_rate": 0.20,
              "cooldown_miss_rate": 0.10,
              "avg_entry_delay_pct": 0.0018,
              "max_entry_delay_pct": 0.0045
            }
        """
        # 1. Policy rejection rate
        total_decisions = await self.paper_decisions_collection.count_documents({
            "experiment_id": experiment_id
        })
        rejected_decisions = await self.paper_decisions_collection.count_documents({
            "experiment_id": experiment_id,
            "paper_status": "REJECTED"
        })
        
        policy_rejection_rate = (
            rejected_decisions / total_decisions if total_decisions > 0 else 0.0
        )
        
        # 2. Cooldown miss rate: (shadow - matched) / shadow
        n_matched = len(matched_pairs)
        cooldown_miss_rate = (
            (shadow_count - n_matched) / shadow_count if shadow_count > 0 else 0.0
        )
        
        # 3. Entry delay (slippage)
        if n_matched > 0:
            entry_delays = [abs(pair["entry_delay_pct"]) for pair in matched_pairs]
            avg_entry_delay = sum(entry_delays) / len(entry_delays)
            max_entry_delay = max(entry_delays)
        else:
            avg_entry_delay = 0.0
            max_entry_delay = 0.0
        
        return {
            "policy_rejection_rate": round(policy_rejection_rate, 4),
            "cooldown_miss_rate": round(cooldown_miss_rate, 4),
            "avg_entry_delay_pct": round(avg_entry_delay, 6),
            "max_entry_delay_pct": round(max_entry_delay, 6)
        }
    
    async def _count_shadow_trades(
        self,
        experiment_id: str,
        horizon: str
    ) -> int:
        """
        Count shadow trades with resolved horizon.
        
        Args:
            experiment_id: Experiment ID
            horizon: Time horizon (24h)
        
        Returns:
            Count of shadow trades
        """
        pipeline = [
            {"$unwind": "$horizons"},
            {"$match": {
                "experiment_id": experiment_id,
                "horizons.name": horizon,
                "horizons.resolved": True
            }},
            {"$count": "total"}
        ]
        
        result = await self.shadow_collection.aggregate(pipeline).to_list(length=1)
        
        return result[0]["total"] if result else 0
    
    async def _count_paper_positions(self, experiment_id: str) -> int:
        """
        Count closed paper positions.
        
        Args:
            experiment_id: Experiment ID
        
        Returns:
            Count of closed positions
        """
        count = await self.paper_positions_collection.count_documents({
            "experiment_id": experiment_id,
            "status": "CLOSED"
        })
        
        return count
