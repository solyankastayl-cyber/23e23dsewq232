"""
Strategy Comparator (S2.3)
==========================

Compares strategies within an experiment.

Responsibilities:
1. Collect metrics for all runs
2. Build StrategyScorecard for each
3. Normalize metrics
4. Generate warnings
5. Output ComparableStrategy list
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import threading

from .experiment_types import (
    StrategyScorecard,
    ComparableStrategy
)

from .metrics_normalizer import (
    MetricsNormalizer,
    POSITIVE_METRICS,
    NEGATIVE_METRICS
)


# Warning thresholds
WARNINGS_CONFIG = {
    "LOW_TRADES_THRESHOLD": 20,
    "HIGH_DRAWDOWN_THRESHOLD": 0.25,  # 25%
    "NEGATIVE_EXPECTANCY_THRESHOLD": 0,
    "LOW_WIN_RATE_THRESHOLD": 0.30,  # 30%
    "LOW_SHARPE_THRESHOLD": 0.5,
    "HIGH_VOLATILITY_THRESHOLD": 0.50  # 50% annual
}


class StrategyComparator:
    """
    Compares strategies and generates scorecards.
    
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
        
        self._normalizer = MetricsNormalizer()
        self._initialized = True
        print("[StrategyComparator] Initialized")
    
    # ===========================================
    # Compare Strategies
    # ===========================================
    
    def compare_experiment(
        self,
        experiment_id: str
    ) -> List[ComparableStrategy]:
        """
        Compare all strategies in an experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            List of ComparableStrategy with normalized metrics
        """
        # Collect scorecards
        scorecards = self.collect_scorecards(experiment_id)
        
        if not scorecards:
            return []
        
        # Extract raw metrics for normalization
        raw_metrics_list = [
            self._scorecard_to_raw_metrics(sc)
            for sc in scorecards
        ]
        
        # Normalize
        self._normalizer.compute_ranges(raw_metrics_list)
        
        # Build comparable strategies
        comparables = []
        for i, sc in enumerate(scorecards):
            raw = raw_metrics_list[i]
            normalized = self._normalizer.normalize_all(raw)
            warnings = self._generate_warnings(sc)
            
            comparable = ComparableStrategy(
                strategy_id=sc.strategy_id,
                experiment_id=sc.experiment_id,
                normalized_metrics=normalized,
                raw_metrics=raw,
                warnings=warnings
            )
            comparables.append(comparable)
        
        return comparables
    
    # ===========================================
    # Collect Scorecards
    # ===========================================
    
    def collect_scorecards(
        self,
        experiment_id: str
    ) -> List[StrategyScorecard]:
        """
        Collect StrategyScorecard for all runs in experiment.
        """
        scorecards = []
        
        try:
            from .experiment_manager import experiment_manager
            from ..simulation.metrics.metrics_store import metrics_store_service
            
            # Get experiment runs
            runs = experiment_manager.get_experiment_runs(experiment_id)
            
            for run in runs:
                # Get metrics snapshot
                snapshot = metrics_store_service.get_snapshot(run.simulation_run_id)
                
                if snapshot and snapshot.is_valid:
                    scorecard = self._snapshot_to_scorecard(
                        snapshot,
                        experiment_id,
                        run.strategy_id,
                        run.simulation_run_id
                    )
                    scorecards.append(scorecard)
                else:
                    # Create placeholder scorecard for invalid/missing data
                    scorecard = StrategyScorecard(
                        experiment_id=experiment_id,
                        strategy_id=run.strategy_id,
                        simulation_run_id=run.simulation_run_id,
                        is_valid=False,
                        warnings=["NO_METRICS_DATA"]
                    )
                    scorecards.append(scorecard)
                    
        except Exception as e:
            print(f"[StrategyComparator] Error collecting scorecards: {e}")
        
        return scorecards
    
    def _snapshot_to_scorecard(
        self,
        snapshot,
        experiment_id: str,
        strategy_id: str,
        simulation_run_id: str
    ) -> StrategyScorecard:
        """
        Convert MetricsSnapshot to StrategyScorecard.
        """
        return StrategyScorecard(
            experiment_id=experiment_id,
            strategy_id=strategy_id,
            simulation_run_id=simulation_run_id,
            
            # Performance
            sharpe_ratio=snapshot.sharpe_ratio,
            sortino_ratio=snapshot.sortino_ratio,
            profit_factor=snapshot.profit_factor,
            expectancy=snapshot.expectancy,
            
            # Returns
            total_return_pct=snapshot.total_return_pct,
            annual_return_pct=snapshot.annual_return_pct,
            
            # Risk
            max_drawdown_pct=snapshot.max_drawdown_pct,
            calmar_ratio=snapshot.calmar_ratio,
            recovery_factor=snapshot.recovery_factor,
            
            # Trade Stats
            win_rate=snapshot.win_rate,
            volatility_annual=snapshot.volatility_annual,
            trades_count=snapshot.trades_count,
            
            is_valid=True
        )
    
    # ===========================================
    # Helpers
    # ===========================================
    
    def _scorecard_to_raw_metrics(self, sc: StrategyScorecard) -> Dict[str, float]:
        """Extract raw metrics dict from scorecard"""
        return {
            "sharpe_ratio": sc.sharpe_ratio,
            "sortino_ratio": sc.sortino_ratio,
            "profit_factor": sc.profit_factor,
            "expectancy": sc.expectancy,
            "total_return_pct": sc.total_return_pct,
            "annual_return_pct": sc.annual_return_pct,
            "max_drawdown_pct": sc.max_drawdown_pct,
            "calmar_ratio": sc.calmar_ratio,
            "recovery_factor": sc.recovery_factor,
            "win_rate": sc.win_rate,
            "volatility_annual": sc.volatility_annual
        }
    
    def _generate_warnings(self, sc: StrategyScorecard) -> List[str]:
        """
        Generate warnings for anomalies.
        """
        warnings = []
        
        if not sc.is_valid:
            warnings.append("INVALID_METRICS")
            return warnings
        
        # Check thresholds
        if sc.trades_count < WARNINGS_CONFIG["LOW_TRADES_THRESHOLD"]:
            warnings.append("LOW_SAMPLE_SIZE")
        
        if sc.max_drawdown_pct > WARNINGS_CONFIG["HIGH_DRAWDOWN_THRESHOLD"] * 100:
            warnings.append("HIGH_DRAWDOWN")
        
        if sc.expectancy < WARNINGS_CONFIG["NEGATIVE_EXPECTANCY_THRESHOLD"]:
            warnings.append("NEGATIVE_EXPECTANCY")
        
        if sc.win_rate < WARNINGS_CONFIG["LOW_WIN_RATE_THRESHOLD"]:
            warnings.append("LOW_WIN_RATE")
        
        if sc.sharpe_ratio < WARNINGS_CONFIG["LOW_SHARPE_THRESHOLD"]:
            warnings.append("LOW_SHARPE")
        
        if sc.volatility_annual > WARNINGS_CONFIG["HIGH_VOLATILITY_THRESHOLD"]:
            warnings.append("HIGH_VOLATILITY")
        
        return warnings
    
    # ===========================================
    # Get Comparison Results
    # ===========================================
    
    def get_dominance_map(
        self,
        comparables: List[ComparableStrategy]
    ) -> Dict[str, List[str]]:
        """
        Build dominance map: which strategy dominates which.
        
        Strategy A dominates B if A is better in all metrics.
        
        Returns:
            Dict of strategy_id -> list of dominated strategies
        """
        dominance = {s.strategy_id: [] for s in comparables}
        
        for a in comparables:
            for b in comparables:
                if a.strategy_id == b.strategy_id:
                    continue
                
                # Check if A dominates B
                if self._dominates(a, b):
                    dominance[a.strategy_id].append(b.strategy_id)
        
        return dominance
    
    def _dominates(
        self,
        a: ComparableStrategy,
        b: ComparableStrategy
    ) -> bool:
        """
        Check if A dominates B (better in all normalized metrics).
        """
        for metric in a.normalized_metrics:
            if metric not in b.normalized_metrics:
                continue
            if a.normalized_metrics[metric] <= b.normalized_metrics[metric]:
                return False
        return True


# Global singleton
strategy_comparator = StrategyComparator()
