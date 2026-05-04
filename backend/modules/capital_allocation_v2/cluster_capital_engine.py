"""
PHASE 21.1 — Cluster Capital Engine
===================================
Sub-engine for cluster-level capital allocation.

Distributes capital across strategy/asset clusters:
- btc_cluster
- majors_cluster
- alts_cluster
- trend_cluster
- reversal_cluster
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


class ClusterCapitalEngine:
    """
    Cluster Capital Allocation Sub-Engine.
    
    Distributes risk budget across clusters.
    Clusters group related strategies and assets.
    """
    
    def __init__(self):
        """Initialize engine."""
        self._cluster_definitions: Dict[str, Dict[str, Any]] = {}
        self._initialize_clusters()
    
    def _initialize_clusters(self):
        """Initialize cluster definitions."""
        self._cluster_definitions = {
            "btc_cluster": {
                "base_allocation": 0.35,
                "assets": ["BTC"],
                "strategies": ["trend_following", "breakout"],
            },
            "majors_cluster": {
                "base_allocation": 0.25,
                "assets": ["ETH", "SOL"],
                "strategies": ["mean_reversion", "structure_reversal"],
            },
            "alts_cluster": {
                "base_allocation": 0.15,
                "assets": ["ALTS"],
                "strategies": ["liquidation_capture", "flow_following"],
            },
            "trend_cluster": {
                "base_allocation": 0.15,
                "assets": ["BTC", "ETH"],
                "strategies": ["trend_following", "breakout", "momentum"],
            },
            "reversal_cluster": {
                "base_allocation": 0.10,
                "assets": ["ETH", "ALTS"],
                "strategies": ["mean_reversion", "structure_reversal"],
            },
        }
    
    def compute_allocations(
        self,
        strategy_allocations: Dict[str, float],
        asset_allocations: Dict[str, float],
        regime: str = "MIXED",
    ) -> Dict[str, Any]:
        """
        Compute cluster allocations.
        
        Args:
            strategy_allocations: Current strategy allocations
            asset_allocations: Current asset allocations
            regime: Market regime (TREND/RANGE/SQUEEZE/VOL/MIXED)
        
        Returns:
            {
                "allocations": {cluster: allocation},
                "total": float,
                "concentration": float,
            }
        """
        allocations = {}
        
        # Calculate each cluster's allocation
        for cluster_name, cluster_def in self._cluster_definitions.items():
            base = cluster_def["base_allocation"]
            
            # Calculate strategy contribution
            strategy_contrib = 0.0
            for strategy in cluster_def.get("strategies", []):
                strategy_contrib += strategy_allocations.get(strategy, 0)
            strategy_weight = strategy_contrib / len(cluster_def.get("strategies", [1])) if cluster_def.get("strategies") else 0
            
            # Calculate asset contribution
            asset_contrib = 0.0
            for asset in cluster_def.get("assets", []):
                asset_contrib += asset_allocations.get(asset, 0)
            asset_weight = asset_contrib / len(cluster_def.get("assets", [1])) if cluster_def.get("assets") else 0
            
            # Combine: 50% base, 25% strategy, 25% asset
            adjusted = base * 0.5 + strategy_weight * 0.25 + asset_weight * 0.25
            
            # Regime adjustments
            if regime == "TREND":
                if "trend" in cluster_name:
                    adjusted *= 1.15
                elif "reversal" in cluster_name:
                    adjusted *= 0.85
            elif regime == "RANGE":
                if "reversal" in cluster_name:
                    adjusted *= 1.15
                elif "trend" in cluster_name:
                    adjusted *= 0.85
            elif regime == "VOL":
                # Reduce alts in high vol
                if "alts" in cluster_name:
                    adjusted *= 0.75
                if "btc" in cluster_name:
                    adjusted *= 1.10
            
            allocations[cluster_name] = adjusted
        
        # Normalize
        total = sum(allocations.values())
        if total > 0:
            allocations = {k: v / total for k, v in allocations.items()}
        
        # Calculate concentration
        concentration = max(allocations.values()) if allocations else 0.0
        
        return {
            "allocations": allocations,
            "total": 1.0,
            "concentration": concentration,
            "regime": regime,
        }
    
    def get_dominant_cluster(self, allocations: Dict[str, float]) -> str:
        """Get cluster with highest allocation."""
        if not allocations:
            return "none"
        return max(allocations, key=allocations.get)
    
    def detect_cluster_overload(
        self,
        allocations: Dict[str, float],
        threshold: float = 0.45,
    ) -> List[str]:
        """Detect clusters with too much allocation."""
        return [k for k, v in allocations.items() if v > threshold]


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[ClusterCapitalEngine] = None


def get_cluster_capital_engine() -> ClusterCapitalEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = ClusterCapitalEngine()
    return _engine
