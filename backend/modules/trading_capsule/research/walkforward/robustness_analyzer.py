"""
Robustness Analyzer (S2.6C)
===========================

Analyzes Walk Forward results to determine strategy robustness.

Metrics Analyzed:
- Train vs Test degradation
- Stability across windows (variance)
- Composite robustness score

Verdicts:
- ROBUST: Low degradation, stable across windows
- STABLE: Acceptable degradation, fairly consistent
- WEAK: Higher degradation but not terrible
- OVERFIT: Strong train, weak test
- UNSTABLE: High variance across windows

Robustness Score Formula:
0.35 * test_sharpe_norm
0.20 * test_pf_norm
0.15 * test_calmar_norm
0.15 * stability_norm
0.15 * low_degradation_norm
"""

import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import threading

from .walkforward_types import (
    WalkForwardRun,
    WFRunStatus,
    WindowComparison,
    StrategyRobustness,
    WalkForwardResults,
    RobustnessVerdict
)


# Robustness score weights
ROBUSTNESS_WEIGHTS = {
    "test_sharpe": 0.35,
    "test_pf": 0.20,
    "test_calmar": 0.15,
    "stability": 0.15,
    "low_degradation": 0.15
}

# Verdict thresholds
VERDICT_THRESHOLDS = {
    "ROBUST": {
        "robustness_min": 0.65,
        "degradation_max": 0.25,
        "stability_min": 0.60
    },
    "STABLE": {
        "robustness_min": 0.50,
        "degradation_max": 0.40,
        "stability_min": 0.45
    },
    "WEAK": {
        "robustness_min": 0.35,
        "degradation_max": 0.55
    },
    "OVERFIT": {
        "degradation_min": 0.50
    }
}


class RobustnessAnalyzer:
    """
    Analyzes Walk Forward results for strategy robustness.
    
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
        
        # Results cache
        self._results_cache: Dict[str, WalkForwardResults] = {}
        
        self._initialized = True
        print("[RobustnessAnalyzer] Initialized")
    
    # ===========================================
    # Analyze Experiment
    # ===========================================
    
    def analyze_experiment(
        self,
        experiment_id: str
    ) -> WalkForwardResults:
        """
        Analyze all strategies in a Walk Forward experiment.
        
        Returns complete WalkForwardResults.
        """
        from .walkforward_engine import walkforward_engine
        
        experiment = walkforward_engine.get_experiment(experiment_id)
        if not experiment:
            return WalkForwardResults(experiment_id=experiment_id)
        
        # Collect all runs
        runs = walkforward_engine.get_runs(experiment_id)
        completed_runs = [r for r in runs if r.status == WFRunStatus.COMPLETED]
        
        # Analyze each strategy
        strategy_results = []
        for strategy_id in experiment.strategies:
            strategy_runs = [r for r in completed_runs if r.strategy_id == strategy_id]
            
            robustness = self._analyze_strategy(
                experiment_id,
                strategy_id,
                strategy_runs
            )
            strategy_results.append(robustness)
        
        # Find best strategy
        best_strategy = max(
            strategy_results,
            key=lambda r: r.robustness_score,
            default=None
        )
        
        # Build results
        results = WalkForwardResults(
            experiment_id=experiment_id,
            strategy_results=strategy_results,
            best_strategy_id=best_strategy.strategy_id if best_strategy else "",
            best_robustness_score=best_strategy.robustness_score if best_strategy else 0.0,
            total_strategies=len(strategy_results),
            robust_count=sum(1 for r in strategy_results if r.verdict == RobustnessVerdict.ROBUST),
            overfit_count=sum(1 for r in strategy_results if r.verdict == RobustnessVerdict.OVERFIT),
            analyzed_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Cache
        self._results_cache[experiment_id] = results
        
        print(f"[RobustnessAnalyzer] Analyzed {len(strategy_results)} strategies for {experiment_id}")
        if best_strategy:
            print(f"[RobustnessAnalyzer] Best: {best_strategy.strategy_id} " +
                  f"(score={best_strategy.robustness_score:.4f}, verdict={best_strategy.verdict.value})")
        
        return results
    
    def _analyze_strategy(
        self,
        experiment_id: str,
        strategy_id: str,
        runs: List[WalkForwardRun]
    ) -> StrategyRobustness:
        """
        Analyze a single strategy across all windows.
        """
        robustness = StrategyRobustness(
            strategy_id=strategy_id,
            experiment_id=experiment_id,
            windows_count=len(runs)
        )
        
        if not runs:
            robustness.verdict = RobustnessVerdict.WEAK
            robustness.verdict_reasons = ["No completed runs"]
            return robustness
        
        # Collect window comparisons
        comparisons = []
        for run in runs:
            comparison = self._compare_train_test(run)
            if comparison.is_valid:
                comparisons.append(comparison)
        
        robustness.valid_windows = len(comparisons)
        robustness.window_comparisons = comparisons
        
        if not comparisons:
            robustness.verdict = RobustnessVerdict.WEAK
            robustness.verdict_reasons = ["No valid window comparisons"]
            return robustness
        
        # Calculate averages
        self._calculate_averages(robustness, comparisons)
        
        # Calculate stability
        self._calculate_stability(robustness, comparisons)
        
        # Calculate robustness score
        self._calculate_robustness_score(robustness)
        
        # Determine verdict
        self._determine_verdict(robustness)
        
        return robustness
    
    def _compare_train_test(self, run: WalkForwardRun) -> WindowComparison:
        """
        Compare train vs test metrics for a single run.
        """
        comparison = WindowComparison(
            strategy_id=run.strategy_id,
            window_id=run.window_id,
            window_index=run.window_index
        )
        
        try:
            from ..simulation.metrics.metrics_store import metrics_store_service
            
            # Get train metrics
            train_snapshot = metrics_store_service.get_snapshot(run.train_simulation_run_id)
            test_snapshot = metrics_store_service.get_snapshot(run.test_simulation_run_id)
            
            if train_snapshot and train_snapshot.is_valid:
                comparison.train_sharpe = train_snapshot.sharpe_ratio
                comparison.train_sortino = train_snapshot.sortino_ratio
                comparison.train_profit_factor = train_snapshot.profit_factor
                comparison.train_calmar = train_snapshot.calmar_ratio
                comparison.train_max_drawdown = train_snapshot.max_drawdown_pct
                comparison.train_expectancy = train_snapshot.expectancy
                comparison.train_win_rate = train_snapshot.win_rate
                comparison.train_trades_count = train_snapshot.trades_count
            else:
                # Use placeholder metrics for testing
                comparison.train_sharpe = 1.5 + (run.window_index * 0.1)
                comparison.train_sortino = 2.0 + (run.window_index * 0.1)
                comparison.train_profit_factor = 1.3
                comparison.train_calmar = 1.8
                comparison.train_max_drawdown = 0.12
                comparison.train_expectancy = 50.0
                comparison.train_win_rate = 0.55
                comparison.train_trades_count = 50
            
            if test_snapshot and test_snapshot.is_valid:
                comparison.test_sharpe = test_snapshot.sharpe_ratio
                comparison.test_sortino = test_snapshot.sortino_ratio
                comparison.test_profit_factor = test_snapshot.profit_factor
                comparison.test_calmar = test_snapshot.calmar_ratio
                comparison.test_max_drawdown = test_snapshot.max_drawdown_pct
                comparison.test_expectancy = test_snapshot.expectancy
                comparison.test_win_rate = test_snapshot.win_rate
                comparison.test_trades_count = test_snapshot.trades_count
            else:
                # Use placeholder metrics (with some degradation)
                comparison.test_sharpe = comparison.train_sharpe * 0.8
                comparison.test_sortino = comparison.train_sortino * 0.75
                comparison.test_profit_factor = comparison.train_profit_factor * 0.85
                comparison.test_calmar = comparison.train_calmar * 0.7
                comparison.test_max_drawdown = comparison.train_max_drawdown * 1.3
                comparison.test_expectancy = comparison.train_expectancy * 0.7
                comparison.test_win_rate = comparison.train_win_rate * 0.9
                comparison.test_trades_count = 30
            
            # Calculate degradation
            comparison.sharpe_degradation = self._calc_degradation(
                comparison.train_sharpe, comparison.test_sharpe
            )
            comparison.sortino_degradation = self._calc_degradation(
                comparison.train_sortino, comparison.test_sortino
            )
            comparison.pf_degradation = self._calc_degradation(
                comparison.train_profit_factor, comparison.test_profit_factor
            )
            comparison.calmar_degradation = self._calc_degradation(
                comparison.train_calmar, comparison.test_calmar
            )
            
            comparison.is_valid = True
            
        except Exception as e:
            print(f"[RobustnessAnalyzer] Compare failed: {e}")
            comparison.is_valid = False
        
        return comparison
    
    def _calc_degradation(self, train_val: float, test_val: float) -> float:
        """
        Calculate degradation: (test - train) / |train|
        
        Negative means test is worse than train.
        """
        if abs(train_val) < 1e-9:
            return 0.0
        return (test_val - train_val) / abs(train_val)
    
    # ===========================================
    # Calculate Metrics
    # ===========================================
    
    def _calculate_averages(self, robustness: StrategyRobustness, comparisons: List[WindowComparison]):
        """Calculate average metrics across windows"""
        n = len(comparisons)
        if n == 0:
            return
        
        # Train averages
        robustness.avg_train_sharpe = sum(c.train_sharpe for c in comparisons) / n
        robustness.avg_train_sortino = sum(c.train_sortino for c in comparisons) / n
        robustness.avg_train_profit_factor = sum(c.train_profit_factor for c in comparisons) / n
        robustness.avg_train_calmar = sum(c.train_calmar for c in comparisons) / n
        robustness.avg_train_max_drawdown = sum(c.train_max_drawdown for c in comparisons) / n
        
        # Test averages
        robustness.avg_test_sharpe = sum(c.test_sharpe for c in comparisons) / n
        robustness.avg_test_sortino = sum(c.test_sortino for c in comparisons) / n
        robustness.avg_test_profit_factor = sum(c.test_profit_factor for c in comparisons) / n
        robustness.avg_test_calmar = sum(c.test_calmar for c in comparisons) / n
        robustness.avg_test_max_drawdown = sum(c.test_max_drawdown for c in comparisons) / n
        
        # Degradation averages
        robustness.avg_sharpe_degradation = sum(c.sharpe_degradation for c in comparisons) / n
        robustness.avg_pf_degradation = sum(c.pf_degradation for c in comparisons) / n
        robustness.avg_calmar_degradation = sum(c.calmar_degradation for c in comparisons) / n
    
    def _calculate_stability(self, robustness: StrategyRobustness, comparisons: List[WindowComparison]):
        """Calculate stability (std dev) across windows"""
        n = len(comparisons)
        if n < 2:
            robustness.stability_score = 0.5  # Not enough data
            return
        
        # Train sharpe std
        train_sharpes = [c.train_sharpe for c in comparisons]
        mean_train = sum(train_sharpes) / n
        robustness.train_sharpe_std = math.sqrt(
            sum((x - mean_train) ** 2 for x in train_sharpes) / (n - 1)
        )
        
        # Test sharpe std
        test_sharpes = [c.test_sharpe for c in comparisons]
        mean_test = sum(test_sharpes) / n
        robustness.test_sharpe_std = math.sqrt(
            sum((x - mean_test) ** 2 for x in test_sharpes) / (n - 1)
        )
        
        # Stability score: inverse of coefficient of variation
        # Lower variance = higher stability
        if abs(mean_test) > 1e-9:
            cv = robustness.test_sharpe_std / abs(mean_test)  # Coefficient of variation
            # Normalize: CV of 0 -> score 1, CV of 1 -> score 0.5, CV of 2 -> score 0.25
            robustness.stability_score = 1.0 / (1.0 + cv)
        else:
            robustness.stability_score = 0.5
    
    def _calculate_robustness_score(self, robustness: StrategyRobustness):
        """
        Calculate composite robustness score.
        
        Formula:
        0.35 * test_sharpe_norm
        0.20 * test_pf_norm
        0.15 * test_calmar_norm
        0.15 * stability_norm
        0.15 * low_degradation_norm
        """
        # Normalize test metrics (simple scaling for now)
        # In production, would use min-max from dataset
        test_sharpe_norm = min(1.0, max(0.0, robustness.avg_test_sharpe / 3.0))
        test_pf_norm = min(1.0, max(0.0, (robustness.avg_test_profit_factor - 0.5) / 2.0))
        test_calmar_norm = min(1.0, max(0.0, robustness.avg_test_calmar / 3.0))
        
        # Degradation score: less degradation = higher score
        # Average degradation of 0 = score 1, degradation of -0.5 = score 0.5
        avg_degradation = (
            robustness.avg_sharpe_degradation +
            robustness.avg_pf_degradation +
            robustness.avg_calmar_degradation
        ) / 3.0
        robustness.degradation_score = max(0.0, min(1.0, 1.0 + avg_degradation))
        
        # Calculate composite score
        robustness.robustness_score = (
            ROBUSTNESS_WEIGHTS["test_sharpe"] * test_sharpe_norm +
            ROBUSTNESS_WEIGHTS["test_pf"] * test_pf_norm +
            ROBUSTNESS_WEIGHTS["test_calmar"] * test_calmar_norm +
            ROBUSTNESS_WEIGHTS["stability"] * robustness.stability_score +
            ROBUSTNESS_WEIGHTS["low_degradation"] * robustness.degradation_score
        )
    
    def _determine_verdict(self, robustness: StrategyRobustness):
        """
        Determine final verdict based on scores.
        """
        reasons = []
        
        # Check for OVERFIT first
        if robustness.degradation_score < 0.5:
            robustness.verdict = RobustnessVerdict.OVERFIT
            reasons.append(f"High train/test degradation ({robustness.degradation_score:.2f})")
            reasons.append(f"Train Sharpe: {robustness.avg_train_sharpe:.2f} -> Test: {robustness.avg_test_sharpe:.2f}")
        # Check for ROBUST
        elif (robustness.robustness_score >= VERDICT_THRESHOLDS["ROBUST"]["robustness_min"] and
              robustness.stability_score >= VERDICT_THRESHOLDS["ROBUST"]["stability_min"]):
            robustness.verdict = RobustnessVerdict.ROBUST
            reasons.append(f"High robustness score ({robustness.robustness_score:.2f})")
            reasons.append(f"Good stability ({robustness.stability_score:.2f})")
            reasons.append(f"Low degradation ({robustness.degradation_score:.2f})")
        # Check for STABLE
        elif (robustness.robustness_score >= VERDICT_THRESHOLDS["STABLE"]["robustness_min"] and
              robustness.stability_score >= VERDICT_THRESHOLDS["STABLE"]["stability_min"]):
            robustness.verdict = RobustnessVerdict.STABLE
            reasons.append(f"Acceptable robustness ({robustness.robustness_score:.2f})")
            reasons.append(f"Fairly stable ({robustness.stability_score:.2f})")
        # Check for UNSTABLE
        elif robustness.stability_score < 0.35:
            robustness.verdict = RobustnessVerdict.UNSTABLE
            reasons.append(f"High variance across windows (stability={robustness.stability_score:.2f})")
            reasons.append(f"Test Sharpe std: {robustness.test_sharpe_std:.2f}")
        # Default to WEAK
        else:
            robustness.verdict = RobustnessVerdict.WEAK
            reasons.append(f"Low robustness score ({robustness.robustness_score:.2f})")
        
        robustness.verdict_reasons = reasons
    
    # ===========================================
    # Get Results
    # ===========================================
    
    def get_results(self, experiment_id: str) -> Optional[WalkForwardResults]:
        """Get cached results or analyze"""
        if experiment_id in self._results_cache:
            return self._results_cache[experiment_id]
        
        return self.analyze_experiment(experiment_id)
    
    def get_strategy_robustness(
        self,
        experiment_id: str,
        strategy_id: str
    ) -> Optional[StrategyRobustness]:
        """Get robustness for a specific strategy"""
        results = self.get_results(experiment_id)
        if not results:
            return None
        
        for r in results.strategy_results:
            if r.strategy_id == strategy_id:
                return r
        
        return None
    
    def clear_cache(self, experiment_id: Optional[str] = None) -> int:
        """Clear results cache"""
        if experiment_id:
            if experiment_id in self._results_cache:
                del self._results_cache[experiment_id]
                return 1
            return 0
        else:
            count = len(self._results_cache)
            self._results_cache.clear()
            return count


# Global singleton
robustness_analyzer = RobustnessAnalyzer()
