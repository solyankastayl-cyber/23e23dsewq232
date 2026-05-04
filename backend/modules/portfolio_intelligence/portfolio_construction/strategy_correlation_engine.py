"""
PHASE 10 - Strategy Correlation Engine
=======================================
Controls correlation between strategies.

If two strategies are highly correlated:
  capital allocation ↓

Goal: maximize diversification benefit.
"""

import math
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

from .portfolio_types import (
    StrategyMetrics, CorrelationMatrix, CorrelationLevel,
    DEFAULT_PORTFOLIO_CONFIG
)


class StrategyCorrelationEngine:
    """
    Strategy Correlation Engine
    
    Monitors and controls correlation between strategies
    to maximize diversification benefits.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_PORTFOLIO_CONFIG
        self.history: List[CorrelationMatrix] = []
        self.max_history = 50
        self.return_history: Dict[str, List[float]] = {}  # strategy_id -> returns
    
    def calculate_correlation_matrix(
        self,
        strategies: List[StrategyMetrics],
        strategy_returns: Optional[Dict[str, List[float]]] = None
    ) -> CorrelationMatrix:
        """
        Calculate correlation matrix between strategies.
        
        Args:
            strategies: List of strategy metrics
            strategy_returns: Optional dict of strategy returns for calculation
            
        Returns:
            CorrelationMatrix with correlations and recommendations
        """
        now = datetime.now(timezone.utc)
        
        if not strategies:
            return self._empty_matrix(now)
        
        # Update return history if provided
        if strategy_returns:
            for sid, returns in strategy_returns.items():
                self.return_history[sid] = returns[-50:]  # Keep last 50 periods
        
        # Calculate correlations
        matrix = self._compute_correlations(strategies)
        
        # Calculate summary metrics
        correlations = []
        for i, si in enumerate(strategies):
            for j, sj in enumerate(strategies):
                if i < j:  # Only count each pair once
                    corr = matrix.get(si.strategy_id, {}).get(sj.strategy_id, 0)
                    correlations.append(corr)
        
        if correlations:
            avg_correlation = sum(correlations) / len(correlations)
            max_correlation = max(correlations)
            min_correlation = min(correlations)
        else:
            avg_correlation = 0
            max_correlation = 0
            min_correlation = 0
        
        # Find high correlation pairs
        high_corr_pairs = self._find_high_correlation_pairs(
            strategies, matrix
        )
        
        # Calculate diversification ratio
        diversification_ratio = self._calculate_diversification_ratio(
            strategies, matrix
        )
        
        result = CorrelationMatrix(
            timestamp=now,
            matrix=matrix,
            avg_correlation=avg_correlation,
            max_correlation=max_correlation,
            min_correlation=min_correlation,
            high_corr_pairs=high_corr_pairs,
            diversification_ratio=diversification_ratio
        )
        
        self._add_to_history(result)
        
        return result
    
    def _compute_correlations(
        self,
        strategies: List[StrategyMetrics]
    ) -> Dict[str, Dict[str, float]]:
        """Compute correlation matrix using return history."""
        matrix = {}
        
        for si in strategies:
            matrix[si.strategy_id] = {}
            
            for sj in strategies:
                if si.strategy_id == sj.strategy_id:
                    matrix[si.strategy_id][sj.strategy_id] = 1.0
                else:
                    corr = self._calculate_pair_correlation(
                        si.strategy_id, sj.strategy_id
                    )
                    matrix[si.strategy_id][sj.strategy_id] = corr
        
        return matrix
    
    def _calculate_pair_correlation(
        self,
        strategy_a: str,
        strategy_b: str
    ) -> float:
        """Calculate correlation between two strategies."""
        returns_a = self.return_history.get(strategy_a, [])
        returns_b = self.return_history.get(strategy_b, [])
        
        if not returns_a or not returns_b:
            # Use mock correlation based on strategy similarity
            return self._mock_correlation(strategy_a, strategy_b)
        
        # Align returns
        min_len = min(len(returns_a), len(returns_b))
        if min_len < 5:
            return 0.0
        
        ra = returns_a[-min_len:]
        rb = returns_b[-min_len:]
        
        # Calculate correlation
        mean_a = sum(ra) / len(ra)
        mean_b = sum(rb) / len(rb)
        
        cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(ra, rb)) / len(ra)
        std_a = math.sqrt(sum((a - mean_a) ** 2 for a in ra) / len(ra))
        std_b = math.sqrt(sum((b - mean_b) ** 2 for b in rb) / len(rb))
        
        if std_a > 0 and std_b > 0:
            correlation = cov / (std_a * std_b)
        else:
            correlation = 0.0
        
        return max(-1.0, min(1.0, correlation))
    
    def _mock_correlation(self, strategy_a: str, strategy_b: str) -> float:
        """Generate mock correlation when no return data available."""
        import random
        
        # Use strategy IDs to generate consistent but varied correlations
        combined = strategy_a + strategy_b
        seed = sum(ord(c) for c in combined)
        random.seed(seed)
        
        # Most strategies have positive correlation
        base_corr = random.uniform(0.1, 0.5)
        
        # Add some variation
        variation = random.gauss(0, 0.15)
        
        return max(-0.3, min(0.85, base_corr + variation))
    
    def _find_high_correlation_pairs(
        self,
        strategies: List[StrategyMetrics],
        matrix: Dict[str, Dict[str, float]]
    ) -> List[Tuple[str, str, float]]:
        """Find pairs with correlation above threshold."""
        threshold = self.config["correlation_threshold"]
        pairs = []
        
        for i, si in enumerate(strategies):
            for j, sj in enumerate(strategies):
                if i < j:
                    corr = matrix.get(si.strategy_id, {}).get(sj.strategy_id, 0)
                    if abs(corr) >= threshold:
                        pairs.append((si.strategy_id, sj.strategy_id, corr))
        
        # Sort by absolute correlation (highest first)
        pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        
        return pairs[:10]  # Return top 10
    
    def _calculate_diversification_ratio(
        self,
        strategies: List[StrategyMetrics],
        matrix: Dict[str, Dict[str, float]]
    ) -> float:
        """
        Calculate diversification ratio.
        
        DR = sum(w_i * vol_i) / portfolio_vol
        
        DR > 1 means we get diversification benefit.
        """
        if not strategies:
            return 1.0
        
        n = len(strategies)
        weights = {s.strategy_id: 1.0 / n for s in strategies}  # Equal weights
        
        # Sum of weighted individual volatilities
        weighted_vols = sum(
            weights[s.strategy_id] * s.volatility for s in strategies
        )
        
        # Portfolio volatility
        port_var = 0.0
        for si in strategies:
            wi = weights[si.strategy_id]
            for sj in strategies:
                wj = weights[sj.strategy_id]
                corr = matrix.get(si.strategy_id, {}).get(sj.strategy_id, 0)
                if si.strategy_id == sj.strategy_id:
                    corr = 1.0
                
                port_var += wi * wj * si.volatility * sj.volatility * corr
        
        port_vol = math.sqrt(max(0, port_var))
        
        if port_vol > 0:
            return weighted_vols / port_vol
        
        return 1.0
    
    def get_correlation_level(self, correlation: float) -> CorrelationLevel:
        """Determine correlation level."""
        if correlation < -0.2:
            return CorrelationLevel.NEGATIVE
        elif correlation < 0.3:
            return CorrelationLevel.LOW
        elif correlation < 0.6:
            return CorrelationLevel.MODERATE
        elif correlation < 0.8:
            return CorrelationLevel.HIGH
        else:
            return CorrelationLevel.VERY_HIGH
    
    def get_allocation_adjustment(
        self,
        base_allocations: Dict[str, float],
        correlation_matrix: CorrelationMatrix
    ) -> Dict[str, float]:
        """
        Adjust allocations based on correlations.
        
        Strategies in highly correlated pairs get reduced weight.
        """
        adjusted = base_allocations.copy()
        
        # Penalize strategies in high correlation pairs
        for pair in correlation_matrix.high_corr_pairs:
            strat1, strat2, corr = pair
            
            # Reduce both by correlation penalty
            penalty = (abs(corr) - self.config["correlation_threshold"]) * 0.5
            
            if strat1 in adjusted:
                adjusted[strat1] *= (1 - penalty)
            if strat2 in adjusted:
                adjusted[strat2] *= (1 - penalty)
        
        # Renormalize
        total = sum(adjusted.values())
        if total > 0:
            adjusted = {k: v / total for k, v in adjusted.items()}
        
        return adjusted
    
    def _empty_matrix(self, timestamp: datetime) -> CorrelationMatrix:
        """Return empty correlation matrix."""
        return CorrelationMatrix(
            timestamp=timestamp,
            matrix={},
            avg_correlation=0,
            max_correlation=0,
            min_correlation=0,
            high_corr_pairs=[],
            diversification_ratio=1.0
        )
    
    def _add_to_history(self, result: CorrelationMatrix):
        """Add result to history."""
        self.history.append(result)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_correlation_summary(self) -> Dict:
        """Get summary of correlation analysis."""
        if not self.history:
            return {"summary": "NO_HISTORY"}
        
        recent = self.history[-1]
        
        # Determine overall correlation assessment
        if recent.avg_correlation < 0.3:
            assessment = "WELL_DIVERSIFIED"
        elif recent.avg_correlation < 0.5:
            assessment = "MODERATELY_DIVERSIFIED"
        elif recent.avg_correlation < 0.7:
            assessment = "CONCENTRATED"
        else:
            assessment = "HIGHLY_CONCENTRATED"
        
        return {
            "assessment": assessment,
            "avg_correlation": round(recent.avg_correlation, 4),
            "max_correlation": round(recent.max_correlation, 4),
            "diversification_ratio": round(recent.diversification_ratio, 4),
            "high_corr_pairs_count": len(recent.high_corr_pairs),
            "high_corr_pairs": [
                {"pair": f"{p[0]}-{p[1]}", "correlation": round(p[2], 4)}
                for p in recent.high_corr_pairs[:5]
            ]
        }
