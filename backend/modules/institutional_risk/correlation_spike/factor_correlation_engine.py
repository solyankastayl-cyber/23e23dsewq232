"""
PHASE 22.4 — Factor Correlation Engine
======================================
Calculates correlation between factor exposures.

When factor overlap is high, diversification breaks down at factor level.
"""

from typing import Dict, Any, Optional, List
from .correlation_types import FACTOR_OVERLAP_WEIGHTS


class FactorCorrelationEngine:
    """
    Calculates factor-level correlation.
    
    Measures overlap between active factors.
    High overlap = pseudo-diversification.
    """
    
    def __init__(self):
        self.overlap_weights = FACTOR_OVERLAP_WEIGHTS
        
        # Default factors
        self.default_factors = [
            "trend_factor",
            "momentum_factor",
            "volatility_factor",
            "flow_factor",
            "volume_factor",
            "regime_factor",
        ]
    
    def calculate(
        self,
        factor_allocations: Optional[Dict[str, float]] = None,
        active_factors: Optional[List[str]] = None,
        volatility_state: str = "NORMAL",
    ) -> Dict[str, Any]:
        """
        Calculate factor correlation.
        
        Args:
            factor_allocations: Dict of factor -> weight
            active_factors: List of active factor names
            volatility_state: Current volatility regime
            
        Returns:
            Factor correlation metrics
        """
        if not factor_allocations and not active_factors:
            # Default to balanced factors
            factor_allocations = {f: 1.0 / len(self.default_factors) for f in self.default_factors}
        
        if active_factors and not factor_allocations:
            factor_allocations = {f: 1.0 / len(active_factors) for f in active_factors}
        
        if not factor_allocations:
            return {
                "factor_correlation": 0.3,
                "concentration_score": 0.0,
                "overlap_pairs": {},
                "reason": "no_factors",
            }
        
        # Calculate concentration
        weights = list(factor_allocations.values())
        max_weight = max(weights) if weights else 0
        concentration_score = max_weight  # HHI-like
        
        # Calculate overlap correlation
        total_overlap = 0.0
        pair_count = 0
        overlap_pairs = {}
        
        factors = list(factor_allocations.keys())
        for i, f1 in enumerate(factors):
            for f2 in factors[i + 1:]:
                w1 = factor_allocations.get(f1, 0)
                w2 = factor_allocations.get(f2, 0)
                
                # Look up overlap
                key = (f1, f2) if (f1, f2) in self.overlap_weights else (f2, f1)
                overlap = self.overlap_weights.get(key, 0.30)
                
                weighted_overlap = overlap * (w1 + w2) / 2
                total_overlap += weighted_overlap
                pair_count += 1
                overlap_pairs[f"{f1}_{f2}"] = round(overlap, 4)
        
        factor_correlation = total_overlap / max(pair_count, 1)
        
        # Adjust for concentration
        if concentration_score > 0.5:
            factor_correlation = min(1.0, factor_correlation + 0.15)
        elif concentration_score > 0.35:
            factor_correlation = min(1.0, factor_correlation + 0.08)
        
        # Volatility adjustment
        if volatility_state.upper() in ["HIGH", "EXPANDING", "EXTREME", "CRISIS"]:
            factor_correlation = min(1.0, factor_correlation * 1.15)
        
        return {
            "factor_correlation": round(min(1.0, max(0, factor_correlation)), 4),
            "concentration_score": round(concentration_score, 4),
            "factor_count": len(factor_allocations),
            "overlap_pairs": overlap_pairs,
            "top_factor": max(factor_allocations, key=factor_allocations.get) if factor_allocations else None,
            "volatility_state": volatility_state,
        }
    
    def get_factor_diversity(self, factor_allocations: Dict[str, float]) -> float:
        """
        Calculate factor diversity score.
        
        1.0 = perfectly diversified
        0.0 = single factor dominance
        """
        if not factor_allocations:
            return 1.0
        
        weights = list(factor_allocations.values())
        n = len(weights)
        
        if n <= 1:
            return 0.0
        
        # Gini coefficient inverse
        total = sum(weights)
        if total == 0:
            return 1.0
        
        normalized = [w / total for w in weights]
        hhi = sum(w ** 2 for w in normalized)
        
        # 1/n = perfect diversity, 1 = single factor
        diversity = 1.0 - (hhi - 1/n) / (1 - 1/n) if n > 1 else 0
        
        return max(0, min(1, diversity))
