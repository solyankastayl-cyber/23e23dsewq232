"""
Monte Carlo Distribution Analyzer (S5)
======================================

Analyzes Monte Carlo simulation results.

Features:
- Return distribution statistics
- VaR (Value at Risk) calculation
- CVaR (Conditional VaR / Expected Shortfall)
- Tail risk analysis
- Scenario classification
"""

import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .mc_types import (
    MonteCarloPath,
    MonteCarloDistribution,
    TailRiskMetrics,
    ScenarioSummary
)
from .mc_simulation_engine import mc_repository


class MonteCarloDistributionAnalyzer:
    """
    Analyzes Monte Carlo simulation results.
    
    Calculates distribution statistics, VaR, CVaR, and tail risk.
    """
    
    # ===========================================
    # Distribution Analysis
    # ===========================================
    
    def calculate_distribution(
        self,
        experiment_id: str
    ) -> Optional[MonteCarloDistribution]:
        """
        Calculate return distribution from Monte Carlo paths.
        """
        paths = mc_repository.get_paths(experiment_id)
        if not paths:
            return None
        
        # Extract returns
        returns = [p.total_return_pct for p in paths]
        max_dds = [p.max_drawdown_pct for p in paths]
        sharpes = [p.sharpe_ratio for p in paths]
        
        # Sort returns
        sorted_returns = sorted(returns)
        n = len(sorted_returns)
        
        # Basic statistics
        mean_return = sum(returns) / n
        median_return = sorted_returns[n // 2]
        std_return = self._calculate_std(returns)
        
        # Percentiles
        percentile_5 = sorted_returns[int(n * 0.05)]
        percentile_10 = sorted_returns[int(n * 0.10)]
        percentile_25 = sorted_returns[int(n * 0.25)]
        percentile_75 = sorted_returns[int(n * 0.75)]
        percentile_90 = sorted_returns[int(n * 0.90)]
        percentile_95 = sorted_returns[int(n * 0.95)]
        
        # Drawdown stats
        sorted_dds = sorted(max_dds, reverse=True)  # Higher DD is worse
        mean_max_dd = sum(max_dds) / n
        median_max_dd = sorted_dds[n // 2]
        worst_max_dd = sorted_dds[0]
        
        # Sharpe stats
        mean_sharpe = sum(sharpes) / n
        sorted_sharpes = sorted(sharpes)
        median_sharpe = sorted_sharpes[n // 2]
        
        # Count profitable paths
        profitable_paths = sum(1 for r in returns if r > 0)
        crash_paths = sum(1 for p in paths if p.had_crash)
        
        return MonteCarloDistribution(
            experiment_id=experiment_id,
            mean_return_pct=mean_return,
            median_return_pct=median_return,
            std_return_pct=std_return,
            min_return_pct=sorted_returns[0],
            max_return_pct=sorted_returns[-1],
            percentile_5=percentile_5,
            percentile_10=percentile_10,
            percentile_25=percentile_25,
            percentile_75=percentile_75,
            percentile_90=percentile_90,
            percentile_95=percentile_95,
            mean_max_dd_pct=mean_max_dd,
            median_max_dd_pct=median_max_dd,
            worst_max_dd_pct=worst_max_dd,
            mean_sharpe=mean_sharpe,
            median_sharpe=median_sharpe,
            total_paths=n,
            profitable_paths=profitable_paths,
            crash_paths=crash_paths
        )
    
    # ===========================================
    # Tail Risk Analysis
    # ===========================================
    
    def calculate_tail_risk(
        self,
        experiment_id: str,
        reference_capital: float = 100000.0
    ) -> Optional[TailRiskMetrics]:
        """
        Calculate tail risk metrics: VaR, CVaR, probability of ruin.
        
        VaR = Maximum loss at confidence level
        CVaR = Expected loss in worst cases (Expected Shortfall)
        """
        paths = mc_repository.get_paths(experiment_id)
        if not paths:
            return None
        
        # Extract returns and sort (ascending for tail risk)
        returns = sorted([p.total_return_pct for p in paths])
        n = len(returns)
        
        # VaR at different confidence levels
        # VaR 90% = 10th percentile of losses
        var_90_idx = int(n * 0.10)
        var_95_idx = int(n * 0.05)
        var_99_idx = int(n * 0.01)
        
        var_90 = returns[var_90_idx]
        var_95 = returns[var_95_idx]
        var_99 = returns[var_99_idx]
        
        # CVaR = average of returns below VaR
        cvar_90 = sum(returns[:var_90_idx + 1]) / (var_90_idx + 1) if var_90_idx > 0 else var_90
        cvar_95 = sum(returns[:var_95_idx + 1]) / (var_95_idx + 1) if var_95_idx > 0 else var_95
        cvar_99 = sum(returns[:var_99_idx + 1]) / (var_99_idx + 1) if var_99_idx > 0 else var_99
        
        # USD impact
        var_95_usd = reference_capital * abs(var_95)
        cvar_95_usd = reference_capital * abs(cvar_95)
        
        # Maximum observed loss
        max_loss_pct = returns[0]  # Worst return
        max_loss_usd = reference_capital * abs(max_loss_pct)
        
        # Probability of ruin
        prob_ruin_50 = sum(1 for r in returns if r < -0.50) / n
        prob_ruin_75 = sum(1 for r in returns if r < -0.75) / n
        
        # Find worst path
        worst_path = min(paths, key=lambda p: p.total_return_pct)
        
        return TailRiskMetrics(
            experiment_id=experiment_id,
            var_90_pct=var_90,
            var_95_pct=var_95,
            var_99_pct=var_99,
            cvar_90_pct=cvar_90,
            cvar_95_pct=cvar_95,
            cvar_99_pct=cvar_99,
            reference_capital=reference_capital,
            var_95_usd=var_95_usd,
            cvar_95_usd=cvar_95_usd,
            max_loss_pct=max_loss_pct,
            max_loss_usd=max_loss_usd,
            prob_ruin_50=prob_ruin_50,
            prob_ruin_75=prob_ruin_75,
            worst_path_id=worst_path.path_id,
            worst_path_return_pct=worst_path.total_return_pct,
            worst_path_max_dd_pct=worst_path.max_drawdown_pct
        )
    
    # ===========================================
    # Scenario Classification
    # ===========================================
    
    def classify_scenarios(
        self,
        experiment_id: str
    ) -> Optional[ScenarioSummary]:
        """
        Classify paths into scenario buckets.
        
        Best case: Top 10%
        Good case: 10-50%
        Median case: 40-60%
        Bad case: 50-90%
        Worst case: Bottom 10%
        """
        paths = mc_repository.get_paths(experiment_id)
        if not paths:
            return None
        
        # Sort by return
        sorted_paths = sorted(paths, key=lambda p: p.total_return_pct, reverse=True)
        n = len(sorted_paths)
        
        # Classify
        best_cutoff = int(n * 0.10)
        good_cutoff = int(n * 0.50)
        median_upper = int(n * 0.60)
        median_lower = int(n * 0.40)
        bad_cutoff = int(n * 0.90)
        
        best_case_count = best_cutoff
        good_case_count = good_cutoff - best_cutoff
        median_case_count = median_upper - median_lower
        bad_case_count = bad_cutoff - good_cutoff
        worst_case_count = n - bad_cutoff
        
        # Representative paths
        best_case_path = sorted_paths[0]
        median_case_path = sorted_paths[n // 2]
        worst_case_path = sorted_paths[-1]
        
        return ScenarioSummary(
            experiment_id=experiment_id,
            best_case_count=best_case_count,
            good_case_count=good_case_count,
            median_case_count=median_case_count,
            bad_case_count=bad_case_count,
            worst_case_count=worst_case_count,
            best_case_path_id=best_case_path.path_id,
            median_case_path_id=median_case_path.path_id,
            worst_case_path_id=worst_case_path.path_id,
            best_case_return_pct=best_case_path.total_return_pct,
            median_case_return_pct=median_case_path.total_return_pct,
            worst_case_return_pct=worst_case_path.total_return_pct
        )
    
    # ===========================================
    # Full Analysis
    # ===========================================
    
    def analyze(
        self,
        experiment_id: str,
        reference_capital: float = 100000.0
    ) -> Dict[str, Any]:
        """
        Perform complete Monte Carlo analysis.
        
        Returns distribution, tail risk, and scenario summary.
        """
        distribution = self.calculate_distribution(experiment_id)
        tail_risk = self.calculate_tail_risk(experiment_id, reference_capital)
        scenarios = self.classify_scenarios(experiment_id)
        
        return {
            "distribution": distribution.to_dict() if distribution else None,
            "tail_risk": tail_risk.to_dict() if tail_risk else None,
            "scenarios": scenarios.to_dict() if scenarios else None
        }
    
    # ===========================================
    # Utilities
    # ===========================================
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    
    def get_percentile(
        self,
        experiment_id: str,
        percentile: float
    ) -> Optional[float]:
        """Get return at specific percentile"""
        paths = mc_repository.get_paths(experiment_id)
        if not paths:
            return None
        
        returns = sorted([p.total_return_pct for p in paths])
        idx = int(len(returns) * (percentile / 100))
        return returns[min(idx, len(returns) - 1)]
    
    def get_path_by_percentile(
        self,
        experiment_id: str,
        percentile: float
    ) -> Optional[MonteCarloPath]:
        """Get representative path at percentile"""
        paths = mc_repository.get_paths(experiment_id)
        if not paths:
            return None
        
        sorted_paths = sorted(paths, key=lambda p: p.total_return_pct)
        idx = int(len(sorted_paths) * (percentile / 100))
        return sorted_paths[min(idx, len(sorted_paths) - 1)]


# Global instance
mc_distribution_analyzer = MonteCarloDistributionAnalyzer()
