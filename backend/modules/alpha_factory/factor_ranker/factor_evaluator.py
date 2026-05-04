"""
PHASE 13.4 - Factor Evaluator
==============================
Evaluates factors using simulated/historical data.

For production: would use real market data
For demo: uses synthetic data with realistic distributions
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import random
import math

from .factor_metrics import FactorMetrics, MetricsResult


class FactorEvaluator:
    """
    Evaluates factors and computes metrics.
    
    Uses factor characteristics to generate realistic performance metrics.
    In production, this would use real market data.
    """
    
    # Family base performance (IC expectations)
    FAMILY_BASE_IC = {
        "trend": 0.035,
        "momentum": 0.032,
        "breakout": 0.038,
        "reversal": 0.028,
        "regime": 0.030,
        "liquidity": 0.042,
        "correlation": 0.025,
        "microstructure": 0.045,
        "macro": 0.022,
        "volatility": 0.033,
        "volume": 0.030,
        "structure": 0.036
    }
    
    # Template complexity bonus
    TEMPLATE_COMPLEXITY_BONUS = {
        "single_feature": 0.0,
        "pair_feature": 0.005,
        "triple_feature": 0.008,
        "ratio_feature": 0.003,
        "difference_feature": 0.002,
        "conditional_feature": 0.010,
        "regime_conditioned": 0.012,
        "interaction_feature": 0.006
    }
    
    # Regimes for evaluation
    REGIMES = ["TRENDING_UP", "TRENDING_DOWN", "RANGE", "HIGH_VOL", "LOW_VOL"]
    
    def __init__(self, seed: int = None):
        """
        Initialize evaluator.
        
        Args:
            seed: Random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
        self.metrics_calculator = FactorMetrics()
    
    def _generate_factor_performance(
        self,
        factor: Dict,
        n_samples: int = 500
    ) -> Tuple[List[float], List[float]]:
        """
        Generate synthetic factor values and returns.
        
        Uses factor characteristics to create realistic performance.
        """
        family = factor.get("family", "momentum")
        template = factor.get("template", "single_feature")
        complexity = factor.get("complexity", 1)
        tags = factor.get("tags", [])
        
        # Base IC from family
        base_ic = self.FAMILY_BASE_IC.get(family, 0.03)
        
        # Template bonus
        template_bonus = self.TEMPLATE_COMPLEXITY_BONUS.get(template, 0.0)
        
        # Complexity adjustment
        complexity_factor = 1.0 + (complexity - 1) * 0.05
        
        # Tag quality bonus
        quality_tags = ["momentum", "strength", "zscore", "percentile", "breakout"]
        tag_bonus = sum(0.003 for tag in tags if tag in quality_tags)
        
        # Final expected IC
        expected_ic = (base_ic + template_bonus + tag_bonus) * complexity_factor
        
        # Add randomness
        noise_factor = random.gauss(1.0, 0.25)
        actual_ic = expected_ic * noise_factor
        
        # Generate correlated factor values and returns
        factor_values = []
        future_returns = []
        
        for i in range(n_samples):
            # Factor value (standardized)
            f_val = random.gauss(0, 1)
            factor_values.append(f_val)
            
            # Return correlated with factor (based on IC)
            noise = random.gauss(0, 1)
            r_val = actual_ic * f_val + math.sqrt(1 - actual_ic**2) * noise
            future_returns.append(r_val * 0.01)  # Scale to realistic returns
        
        return factor_values, future_returns
    
    def _generate_regime_ic(
        self,
        factor: Dict,
        base_ic: float
    ) -> Dict[str, float]:
        """
        Generate IC by regime.
        """
        family = factor.get("family", "momentum")
        regime_dependency = factor.get("regime_dependency", [])
        
        ic_by_regime = {}
        
        for regime in self.REGIMES:
            # Base performance
            regime_ic = base_ic
            
            # Bonus if factor is designed for this regime
            if regime in regime_dependency:
                regime_ic *= 1.3
            
            # Family-regime affinity
            affinities = {
                ("trend", "TRENDING_UP"): 1.2,
                ("trend", "TRENDING_DOWN"): 1.2,
                ("breakout", "HIGH_VOL"): 1.15,
                ("breakout", "RANGE"): 0.8,
                ("reversal", "RANGE"): 1.25,
                ("momentum", "TRENDING_UP"): 1.1,
                ("momentum", "TRENDING_DOWN"): 1.1,
                ("volatility", "HIGH_VOL"): 1.2,
                ("regime", "HIGH_VOL"): 1.15,
                ("regime", "LOW_VOL"): 1.15,
            }
            
            affinity = affinities.get((family, regime), 1.0)
            regime_ic *= affinity
            
            # Add noise
            regime_ic *= random.gauss(1.0, 0.15)
            
            ic_by_regime[regime] = round(regime_ic, 4)
        
        return ic_by_regime
    
    def evaluate_factor(self, factor: Dict, n_samples: int = 500) -> MetricsResult:
        """
        Evaluate a single factor.
        
        Args:
            factor: Factor dictionary
            n_samples: Number of samples for evaluation
        
        Returns:
            MetricsResult with all metrics
        """
        factor_id = factor.get("factor_id", "unknown")
        
        # Generate synthetic performance data
        factor_values, future_returns = self._generate_factor_performance(
            factor, n_samples
        )
        
        # Calculate IC
        ic = self.metrics_calculator.calculate_ic(
            factor_values, future_returns, lag=1
        )
        
        # Calculate rolling IC
        rolling_ic = self.metrics_calculator.calculate_rolling_ic(
            factor_values, future_returns, window=60, lag=1
        )
        
        # Calculate Sharpe
        # Simulate factor returns based on IC
        factor_returns = []
        for i in range(1, len(factor_values)):
            # Return = IC * factor_signal + noise
            signal_return = ic * factor_values[i-1] * 0.01
            factor_returns.append(signal_return)
        
        sharpe = self.metrics_calculator.sharpe_ratio(factor_returns)
        
        # Calculate rolling Sharpe
        rolling_sharpe = []
        window = 60
        for i in range(window, len(factor_returns)):
            window_returns = factor_returns[i-window:i]
            rs = self.metrics_calculator.sharpe_ratio(window_returns)
            rolling_sharpe.append(rs)
        
        # Calculate Stability
        stability = self.metrics_calculator.calculate_stability(rolling_ic)
        
        # Calculate Decay
        decay_score, ic_decay_curve = self.metrics_calculator.calculate_decay(
            factor_values, future_returns
        )
        
        # Calculate Regime IC
        ic_by_regime = self._generate_regime_ic(factor, ic)
        
        # Calculate Regime Consistency
        regime_consistency = self.metrics_calculator.calculate_regime_consistency(
            ic_by_regime
        )
        
        # Calculate Composite Score
        composite_score = self.metrics_calculator.calculate_composite_score(
            ic, sharpe, stability, regime_consistency, decay_score
        )
        
        # Determine Verdict
        verdict, approved = self.metrics_calculator.determine_verdict(
            ic, sharpe, stability, composite_score
        )
        
        return MetricsResult(
            factor_id=factor_id,
            ic=round(ic, 4),
            sharpe=round(sharpe, 2),
            stability=round(stability, 2),
            decay_score=round(decay_score, 2),
            regime_consistency=round(regime_consistency, 2),
            composite_score=round(composite_score, 3),
            verdict=verdict,
            approved=approved,
            ic_by_regime=ic_by_regime,
            ic_decay_curve=[round(x, 4) for x in ic_decay_curve],
            rolling_ic=[round(x, 4) for x in rolling_ic[-20:]],
            rolling_sharpe=[round(x, 2) for x in rolling_sharpe[-20:]],
            evaluated_at=datetime.now(timezone.utc),
            samples_used=n_samples
        )
    
    def evaluate_batch(
        self,
        factors: List[Dict],
        n_samples: int = 500
    ) -> List[MetricsResult]:
        """
        Evaluate multiple factors.
        """
        results = []
        for factor in factors:
            result = self.evaluate_factor(factor, n_samples)
            results.append(result)
        return results
