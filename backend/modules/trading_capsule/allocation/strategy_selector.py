"""
Strategy Selector (S3.1)
========================

Selects strategies eligible for capital allocation.

Filters:
1. Walk Forward verdict (reject OVERFIT, UNSTABLE)
2. Ranking score >= threshold
3. Trades count >= minimum
4. Max drawdown <= threshold
5. Sharpe ratio >= threshold

Output: List of EligibleStrategy
"""

from typing import List, Optional, Dict, Any
import threading

from .allocation_types import (
    EligibleStrategy,
    AllocationPolicy,
    SelectionReason
)


# Default policy
DEFAULT_POLICY = AllocationPolicy()


class StrategySelector:
    """
    Selects strategies for allocation based on policy rules.
    
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
        
        self._initialized = True
        print("[StrategySelector] Initialized")
    
    # ===========================================
    # Select Strategies
    # ===========================================
    
    def select_strategies(
        self,
        experiment_id: str,
        walkforward_experiment_id: Optional[str] = None,
        policy: AllocationPolicy = None
    ) -> List[EligibleStrategy]:
        """
        Select eligible strategies from experiment results.
        
        Args:
            experiment_id: Research experiment ID
            walkforward_experiment_id: Optional Walk Forward experiment ID
            policy: Allocation policy (uses default if not provided)
            
        Returns:
            List of EligibleStrategy (both eligible and rejected)
        """
        if policy is None:
            policy = DEFAULT_POLICY
        
        eligible_strategies = []
        
        # Get ranking results
        ranking_data = self._get_ranking_data(experiment_id)
        
        # Get walk forward results if available
        wf_data = {}
        if walkforward_experiment_id:
            wf_data = self._get_walkforward_data(walkforward_experiment_id)
        
        # Process each strategy
        for strategy_id, ranking_entry in ranking_data.items():
            strategy = self._build_eligible_strategy(
                strategy_id,
                experiment_id,
                ranking_entry,
                wf_data.get(strategy_id, {})
            )
            
            # Apply filters
            self._apply_selection_filters(strategy, policy)
            
            eligible_strategies.append(strategy)
        
        # Sort by composite score
        eligible_strategies.sort(
            key=lambda s: s.composite_score,
            reverse=True
        )
        
        selected = sum(1 for s in eligible_strategies if s.is_eligible)
        print(f"[StrategySelector] Selected {selected}/{len(eligible_strategies)} strategies")
        
        return eligible_strategies
    
    def get_eligible_only(
        self,
        experiment_id: str,
        walkforward_experiment_id: Optional[str] = None,
        policy: AllocationPolicy = None
    ) -> List[EligibleStrategy]:
        """
        Get only eligible strategies (filtered).
        """
        all_strategies = self.select_strategies(
            experiment_id,
            walkforward_experiment_id,
            policy
        )
        return [s for s in all_strategies if s.is_eligible]
    
    # ===========================================
    # Data Collection
    # ===========================================
    
    def _get_ranking_data(self, experiment_id: str) -> Dict[str, Dict]:
        """
        Get ranking data from Research Lab.
        """
        try:
            from ..research.ranking_engine import ranking_engine
            
            leaderboard = ranking_engine.get_leaderboard(experiment_id)
            if not leaderboard:
                return {}
            
            result = {}
            for entry in leaderboard.entries:
                result[entry.strategy_id] = {
                    "ranking_score": entry.composite_score,
                    "raw_metrics": entry.raw_metrics,
                    "normalized_metrics": entry.normalized_metrics,
                    "warnings": entry.warnings
                }
            return result
            
        except Exception as e:
            print(f"[StrategySelector] Error getting ranking: {e}")
            return {}
    
    def _get_walkforward_data(self, wf_experiment_id: str) -> Dict[str, Dict]:
        """
        Get Walk Forward results.
        """
        try:
            from ..research.walkforward.robustness_analyzer import robustness_analyzer
            
            results = robustness_analyzer.get_results(wf_experiment_id)
            if not results:
                return {}
            
            wf_data = {}
            for r in results.strategy_results:
                wf_data[r.strategy_id] = {
                    "robustness_score": r.robustness_score,
                    "stability_score": r.stability_score,
                    "verdict": r.verdict.value,
                    "avg_train_sharpe": r.avg_train_sharpe,
                    "avg_test_sharpe": r.avg_test_sharpe,
                    "sharpe_degradation": r.avg_sharpe_degradation
                }
            return wf_data
            
        except Exception as e:
            print(f"[StrategySelector] Error getting WF data: {e}")
            return {}
    
    def _build_eligible_strategy(
        self,
        strategy_id: str,
        experiment_id: str,
        ranking_entry: Dict,
        wf_entry: Dict
    ) -> EligibleStrategy:
        """
        Build EligibleStrategy from ranking and WF data.
        """
        raw = ranking_entry.get("raw_metrics", {})
        
        strategy = EligibleStrategy(
            strategy_id=strategy_id,
            experiment_id=experiment_id,
            
            # Scores
            ranking_score=ranking_entry.get("ranking_score", 0),
            robustness_score=wf_entry.get("robustness_score", 0.5),
            
            # Metrics from ranking
            sharpe_ratio=raw.get("sharpe_ratio", 0),
            sortino_ratio=raw.get("sortino_ratio", 0),
            calmar_ratio=raw.get("calmar_ratio", 0),
            profit_factor=raw.get("profit_factor", 0),
            max_drawdown_pct=raw.get("max_drawdown_pct", 0),
            expectancy=raw.get("expectancy", 0),
            win_rate=raw.get("win_rate", 0),
            
            # Walk Forward
            robustness_verdict=wf_entry.get("verdict", "UNKNOWN"),
            avg_train_sharpe=wf_entry.get("avg_train_sharpe", 0),
            avg_test_sharpe=wf_entry.get("avg_test_sharpe", 0),
            sharpe_degradation=wf_entry.get("sharpe_degradation", 0),
            
            # Warnings from ranking
            warnings=ranking_entry.get("warnings", [])
        )
        
        # Calculate composite score
        strategy.composite_score = (
            strategy.ranking_score * 0.5 +
            strategy.robustness_score * 0.5
        )
        
        return strategy
    
    # ===========================================
    # Selection Filters
    # ===========================================
    
    def _apply_selection_filters(
        self,
        strategy: EligibleStrategy,
        policy: AllocationPolicy
    ):
        """
        Apply selection filters to strategy.
        
        Sets is_eligible and selection_reason.
        """
        # Default: eligible
        strategy.is_eligible = True
        strategy.selection_reason = SelectionReason.SELECTED
        
        # Filter 1: Walk Forward verdict
        if not policy.allow_overfit and strategy.robustness_verdict == "OVERFIT":
            strategy.is_eligible = False
            strategy.selection_reason = SelectionReason.OVERFIT
            return
        
        if not policy.allow_unstable and strategy.robustness_verdict == "UNSTABLE":
            strategy.is_eligible = False
            strategy.selection_reason = SelectionReason.UNSTABLE
            return
        
        if policy.require_robust and strategy.robustness_verdict != "ROBUST":
            strategy.is_eligible = False
            strategy.selection_reason = SelectionReason.LOW_RANKING
            return
        
        # Filter 2: Ranking score
        if strategy.ranking_score < policy.min_ranking_score:
            strategy.is_eligible = False
            strategy.selection_reason = SelectionReason.LOW_RANKING
            return
        
        # Filter 3: Trades count
        if strategy.trades_count > 0 and strategy.trades_count < policy.min_trades_count:
            strategy.is_eligible = False
            strategy.selection_reason = SelectionReason.LOW_TRADES
            return
        
        # Filter 4: Max drawdown
        if strategy.max_drawdown_pct > policy.max_drawdown_threshold * 100:
            strategy.is_eligible = False
            strategy.selection_reason = SelectionReason.HIGH_DRAWDOWN
            return
        
        # Filter 5: Sharpe ratio
        if strategy.sharpe_ratio < policy.min_sharpe_threshold:
            strategy.is_eligible = False
            strategy.selection_reason = SelectionReason.LOW_SHARPE
            return
        
        # Add warnings
        if strategy.robustness_verdict == "WEAK":
            strategy.warnings.append("WEAK_ROBUSTNESS")
        
        if strategy.sharpe_degradation < -0.3:
            strategy.warnings.append("HIGH_DEGRADATION")


# Global singleton
strategy_selector = StrategySelector()
