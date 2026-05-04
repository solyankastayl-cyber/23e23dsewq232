"""
PHASE 22.4 — Asset Correlation Engine
=====================================
Calculates correlation between assets (BTC, ETH, ALTS).

Uses volatility regime to estimate correlation when real correlations unavailable.
"""

from typing import Dict, Any, Optional, List
from .correlation_types import VOLATILITY_CORRELATION_MAP


class AssetCorrelationEngine:
    """
    Calculates asset-level correlation.
    
    In high volatility / crisis regimes, all assets tend to correlate.
    This is "correlation breakdown" - diversification fails.
    """
    
    def __init__(self):
        self.volatility_map = VOLATILITY_CORRELATION_MAP
    
    def calculate(
        self,
        asset_allocations: Optional[Dict[str, float]] = None,
        cluster_allocations: Optional[Dict[str, float]] = None,
        volatility_state: str = "NORMAL",
        real_correlations: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate asset correlation.
        
        Args:
            asset_allocations: Dict of asset -> weight
            cluster_allocations: Dict of cluster -> weight
            volatility_state: Current volatility regime
            real_correlations: Optional real correlation values
            
        Returns:
            Asset correlation metrics
        """
        # Use real correlations if provided
        if real_correlations and len(real_correlations) > 0:
            avg_corr = sum(real_correlations.values()) / len(real_correlations)
            return {
                "asset_correlation": max(0, min(1, avg_corr)),
                "source": "real",
                "volatility_state": volatility_state,
                "correlations": real_correlations,
            }
        
        # Rule-based correlation from volatility state
        base_correlation = self.volatility_map.get(volatility_state.upper(), 0.45)
        
        # Adjust based on concentration
        concentration_adjustment = 0.0
        
        if asset_allocations:
            # Higher concentration = higher effective correlation
            max_weight = max(asset_allocations.values()) if asset_allocations else 0
            if max_weight > 0.5:
                concentration_adjustment = 0.10
            elif max_weight > 0.35:
                concentration_adjustment = 0.05
        
        if cluster_allocations:
            # Cluster concentration
            max_cluster = max(cluster_allocations.values()) if cluster_allocations else 0
            if max_cluster > 0.4:
                concentration_adjustment += 0.08
        
        asset_correlation = min(1.0, base_correlation + concentration_adjustment)
        
        # Estimate individual correlations
        estimated_correlations = {
            "BTC_ETH": round(min(1.0, asset_correlation * 0.95), 4),
            "BTC_ALTS": round(min(1.0, asset_correlation * 0.85), 4),
            "ETH_ALTS": round(min(1.0, asset_correlation * 0.90), 4),
        }
        
        return {
            "asset_correlation": round(asset_correlation, 4),
            "source": "rule_based",
            "volatility_state": volatility_state,
            "correlations": estimated_correlations,
            "concentration_adjustment": round(concentration_adjustment, 4),
        }
    
    def get_crisis_correlation(self, volatility_state: str) -> float:
        """Get correlation during crisis regime."""
        if volatility_state.upper() in ["EXTREME", "CRISIS"]:
            return 0.85
        elif volatility_state.upper() in ["HIGH", "EXPANDING"]:
            return 0.65
        return self.volatility_map.get(volatility_state.upper(), 0.45)
