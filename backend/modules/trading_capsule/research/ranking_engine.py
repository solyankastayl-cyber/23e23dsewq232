"""
Ranking Engine (S2.4)
=====================

Ranks strategies using weighted composite score.

Default weights (configurable):
- sharpe_ratio: 0.20
- sortino_ratio: 0.15
- profit_factor: 0.15
- annual_return_pct: 0.10
- expectancy: 0.10
- calmar_ratio: 0.15
- recovery_factor: 0.10
- win_rate: 0.05

Penalties:
- Low trades: -0.10
- High drawdown: -0.15
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import threading

from .experiment_types import (
    StrategyRankingEntry,
    StrategyLeaderboard,
    ComparableStrategy
)

from .strategy_comparator import strategy_comparator


# Default ranking policy
DEFAULT_WEIGHTS = {
    "sharpe_ratio": 0.20,
    "sortino_ratio": 0.15,
    "profit_factor": 0.15,
    "annual_return_pct": 0.10,
    "expectancy": 0.10,
    "calmar_ratio": 0.15,
    "recovery_factor": 0.10,
    "win_rate": 0.05
}

# Penalty configuration
DEFAULT_PENALTIES = {
    "LOW_SAMPLE_SIZE": 0.10,
    "HIGH_DRAWDOWN": 0.15,
    "NEGATIVE_EXPECTANCY": 0.20,
    "LOW_WIN_RATE": 0.05,
    "LOW_SHARPE": 0.05,
    "HIGH_VOLATILITY": 0.05,
    "INVALID_METRICS": 0.50,
    "NO_METRICS_DATA": 0.50
}


class RankingEngine:
    """
    Ranks strategies using multi-metric composite score.
    
    Thread-safe singleton.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Configurable weights and penalties
        self.weights = DEFAULT_WEIGHTS.copy()
        self.penalties = DEFAULT_PENALTIES.copy()
        
        # Cached leaderboards
        self._leaderboards: Dict[str, StrategyLeaderboard] = {}
        
        self._initialized = True
        print("[RankingEngine] Initialized")
    
    # ===========================================
    # Configure Weights
    # ===========================================
    
    def set_weights(self, weights: Dict[str, float]):
        """Set custom weights"""
        self.weights.update(weights)
    
    def set_penalties(self, penalties: Dict[str, float]):
        """Set custom penalties"""
        self.penalties.update(penalties)
    
    def reset_policy(self):
        """Reset to default policy"""
        self.weights = DEFAULT_WEIGHTS.copy()
        self.penalties = DEFAULT_PENALTIES.copy()
    
    # ===========================================
    # Rank Experiment
    # ===========================================
    
    def rank_experiment(
        self,
        experiment_id: str,
        policy: str = "default"
    ) -> StrategyLeaderboard:
        """
        Rank all strategies in an experiment.
        
        Args:
            experiment_id: Experiment ID
            policy: Ranking policy name (for future extensibility)
            
        Returns:
            StrategyLeaderboard with ranked entries
        """
        # Get comparable strategies from comparator
        comparables = strategy_comparator.compare_experiment(experiment_id)
        
        if not comparables:
            return StrategyLeaderboard(
                experiment_id=experiment_id,
                generated_at=datetime.now(timezone.utc).isoformat(),
                ranking_policy=policy
            )
        
        # Calculate composite scores
        entries = []
        for comp in comparables:
            entry = self._calculate_ranking_entry(
                comp,
                experiment_id
            )
            entries.append(entry)
        
        # Sort by composite score (descending)
        entries.sort(key=lambda e: e.composite_score, reverse=True)
        
        # Assign ranks
        for i, entry in enumerate(entries):
            entry.rank = i + 1
        
        # Build leaderboard
        leaderboard = StrategyLeaderboard(
            experiment_id=experiment_id,
            entries=entries,
            winner_strategy_id=entries[0].strategy_id if entries else "",
            winner_score=entries[0].composite_score if entries else 0.0,
            total_strategies=len(comparables),
            valid_strategies=sum(1 for c in comparables if not c.warnings or "INVALID_METRICS" not in c.warnings),
            ranking_policy=policy,
            generated_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Cache
        self._leaderboards[experiment_id] = leaderboard
        
        print(f"[RankingEngine] Ranked {len(entries)} strategies for experiment: {experiment_id}")
        if leaderboard.winner_strategy_id:
            print(f"[RankingEngine] Winner: {leaderboard.winner_strategy_id} (score: {leaderboard.winner_score:.4f})")
        
        return leaderboard
    
    def _calculate_ranking_entry(
        self,
        comparable: ComparableStrategy,
        experiment_id: str
    ) -> StrategyRankingEntry:
        """
        Calculate ranking entry with composite score.
        """
        # Calculate base score from weighted metrics
        score_breakdown = {}
        base_score = 0.0
        
        for metric, weight in self.weights.items():
            normalized_value = comparable.normalized_metrics.get(metric, 0.5)
            contribution = normalized_value * weight
            score_breakdown[metric] = contribution
            base_score += contribution
        
        # Apply penalties
        penalties_applied = {}
        total_penalty = 0.0
        
        for warning in comparable.warnings:
            if warning in self.penalties:
                penalty = self.penalties[warning]
                penalties_applied[warning] = penalty
                total_penalty += penalty
        
        # Final composite score
        composite_score = max(0.0, base_score - total_penalty)
        
        return StrategyRankingEntry(
            experiment_id=experiment_id,
            strategy_id=comparable.strategy_id,
            simulation_run_id="",  # Would come from experiment run
            composite_score=composite_score,
            score_breakdown=score_breakdown,
            penalties=penalties_applied,
            total_penalty=total_penalty,
            normalized_metrics=comparable.normalized_metrics,
            raw_metrics=comparable.raw_metrics,
            warnings=comparable.warnings
        )
    
    # ===========================================
    # Get Results
    # ===========================================
    
    def get_leaderboard(
        self,
        experiment_id: str
    ) -> Optional[StrategyLeaderboard]:
        """
        Get cached leaderboard or calculate if not available.
        """
        if experiment_id in self._leaderboards:
            return self._leaderboards[experiment_id]
        
        return self.rank_experiment(experiment_id)
    
    def get_winner(
        self,
        experiment_id: str
    ) -> Optional[StrategyRankingEntry]:
        """
        Get the winning strategy for an experiment.
        """
        leaderboard = self.get_leaderboard(experiment_id)
        if leaderboard and leaderboard.entries:
            return leaderboard.entries[0]
        return None
    
    def get_top_strategies(
        self,
        experiment_id: str,
        count: int = 3
    ) -> List[StrategyRankingEntry]:
        """
        Get top N strategies.
        """
        leaderboard = self.get_leaderboard(experiment_id)
        if leaderboard:
            return leaderboard.entries[:count]
        return []
    
    # ===========================================
    # Analysis
    # ===========================================
    
    def get_ranking_breakdown(
        self,
        experiment_id: str,
        strategy_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed breakdown of a strategy's ranking.
        """
        leaderboard = self.get_leaderboard(experiment_id)
        if not leaderboard:
            return None
        
        for entry in leaderboard.entries:
            if entry.strategy_id == strategy_id:
                return {
                    "rank": entry.rank,
                    "total_strategies": leaderboard.total_strategies,
                    "composite_score": entry.composite_score,
                    "score_breakdown": entry.score_breakdown,
                    "penalties": entry.penalties,
                    "total_penalty": entry.total_penalty,
                    "warnings": entry.warnings,
                    "weights_used": self.weights
                }
        
        return None
    
    def compare_two_strategies(
        self,
        experiment_id: str,
        strategy_a: str,
        strategy_b: str
    ) -> Dict[str, Any]:
        """
        Direct comparison of two strategies.
        """
        leaderboard = self.get_leaderboard(experiment_id)
        if not leaderboard:
            return {"error": "Leaderboard not found"}
        
        entry_a = None
        entry_b = None
        
        for entry in leaderboard.entries:
            if entry.strategy_id == strategy_a:
                entry_a = entry
            elif entry.strategy_id == strategy_b:
                entry_b = entry
        
        if not entry_a or not entry_b:
            return {"error": "Strategy not found"}
        
        # Build comparison
        metrics_comparison = {}
        for metric in self.weights.keys():
            a_val = entry_a.normalized_metrics.get(metric, 0)
            b_val = entry_b.normalized_metrics.get(metric, 0)
            metrics_comparison[metric] = {
                "strategy_a": round(a_val, 4),
                "strategy_b": round(b_val, 4),
                "winner": strategy_a if a_val > b_val else (strategy_b if b_val > a_val else "tie")
            }
        
        return {
            "strategy_a": {
                "id": strategy_a,
                "rank": entry_a.rank,
                "score": entry_a.composite_score
            },
            "strategy_b": {
                "id": strategy_b,
                "rank": entry_b.rank,
                "score": entry_b.composite_score
            },
            "overall_winner": strategy_a if entry_a.composite_score > entry_b.composite_score else strategy_b,
            "metrics_comparison": metrics_comparison
        }
    
    # ===========================================
    # Cache Management
    # ===========================================
    
    def invalidate_cache(self, experiment_id: str):
        """Invalidate cached leaderboard"""
        self._leaderboards.pop(experiment_id, None)
    
    def clear_cache(self) -> int:
        """Clear all cached leaderboards"""
        count = len(self._leaderboards)
        self._leaderboards.clear()
        return count


# Global singleton
ranking_engine = RankingEngine()
