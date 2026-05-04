"""
PHASE 18.1 — Cluster Exposure Engine
=====================================
Asset cluster analysis.

Calculates exposure by asset clusters:
- btc_cluster
- eth_cluster  
- majors_cluster
- alts_cluster

Example output:
{
  "btc_cluster": 0.80,
  "majors_cluster": 0.55,
  "alts_cluster": 0.72
}
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

from modules.portfolio.portfolio_intelligence.portfolio_intelligence_types import (
    Position,
    ClusterType,
    CLUSTER_CONCENTRATION_THRESHOLD,
)


# ══════════════════════════════════════════════════════════════
# CLUSTER CLASSIFICATION
# ══════════════════════════════════════════════════════════════

# BTC cluster
BTC_CLUSTER_SYMBOLS = {
    "BTCUSDT", "BTCUSD", "XBTUSD", "BTC", "BTCPERP", "BTC-PERP",
    # BTC-correlated symbols
    "MSTRSTOCK",  # MicroStrategy proxy
}

# ETH cluster (ETH and ETH ecosystem)
ETH_CLUSTER_SYMBOLS = {
    "ETHUSDT", "ETHUSD", "ETH", "ETHPERP", "ETH-PERP",
    # ETH L2s and ecosystem
    "OPUSDT", "ARBUSDT", "MATICUSDT", "STXUSDT",
}

# Majors cluster (top coins by market cap, high correlation)
MAJORS_CLUSTER_SYMBOLS = {
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT",
}

# Everything else goes to alts


def classify_cluster(symbol: str) -> List[str]:
    """
    Classify symbol into cluster(s).
    
    A symbol can belong to multiple clusters.
    For example, BTCUSDT is in both btc_cluster and majors_cluster.
    """
    clusters = []
    symbol_upper = symbol.upper()
    
    # Check BTC cluster
    if symbol_upper in BTC_CLUSTER_SYMBOLS or symbol_upper.startswith("BTC"):
        clusters.append(ClusterType.BTC_CLUSTER.value)
    
    # Check ETH cluster
    if symbol_upper in ETH_CLUSTER_SYMBOLS or symbol_upper.startswith("ETH"):
        clusters.append(ClusterType.ETH_CLUSTER.value)
    
    # Check majors cluster
    if symbol_upper in MAJORS_CLUSTER_SYMBOLS:
        clusters.append(ClusterType.MAJORS_CLUSTER.value)
    else:
        # If not a major, it's an alt
        clusters.append(ClusterType.ALTS_CLUSTER.value)
    
    return clusters


# ══════════════════════════════════════════════════════════════
# CLUSTER EXPOSURE ENGINE
# ══════════════════════════════════════════════════════════════

class ClusterExposureEngine:
    """
    Cluster Exposure Engine - PHASE 18.1 STEP 6
    
    Calculates cluster exposure across the portfolio.
    
    Clusters represent correlation groups - assets that tend
    to move together.
    """
    
    def calculate_cluster_exposure(self, positions: List[Position]) -> Dict[str, float]:
        """
        Calculate cluster exposure.
        
        Args:
            positions: List of portfolio positions
        
        Returns:
            Dict mapping cluster to exposure (0-1)
        """
        cluster_weights = defaultdict(float)
        total_exposure = sum(pos.position_size for pos in positions)
        
        for pos in positions:
            clusters = classify_cluster(pos.symbol)
            
            # Distribute position size across clusters
            # If symbol is in multiple clusters, split the exposure
            weight_per_cluster = pos.position_size / len(clusters) if clusters else 0
            
            for cluster in clusters:
                cluster_weights[cluster] += weight_per_cluster
        
        # Normalize to 0-1
        if total_exposure > 0:
            cluster_exposure = {
                k: min(v / total_exposure, 1.0)
                for k, v in cluster_weights.items()
            }
        else:
            cluster_exposure = {}
        
        # Ensure all cluster types are present
        for cluster_type in ClusterType:
            if cluster_type.value not in cluster_exposure:
                cluster_exposure[cluster_type.value] = 0.0
        
        return cluster_exposure
    
    def calculate_cluster_exposure_raw(self, positions: List[Position]) -> Dict[str, float]:
        """
        Calculate raw (non-normalized) cluster exposure.
        
        Useful for understanding absolute exposure levels.
        """
        cluster_weights = defaultdict(float)
        
        for pos in positions:
            clusters = classify_cluster(pos.symbol)
            
            # Full position size to each cluster (not split)
            for cluster in clusters:
                cluster_weights[cluster] += pos.position_size
        
        return dict(cluster_weights)
    
    def get_cluster_breakdown(self, positions: List[Position]) -> Dict[str, Dict]:
        """
        Get detailed cluster breakdown.
        
        Returns:
            Dict with cluster breakdown including positions per cluster
        """
        breakdown = defaultdict(lambda: {
            "exposure": 0.0,
            "positions": [],
            "count": 0,
            "total_size": 0.0,
        })
        
        total_exposure = sum(pos.position_size for pos in positions)
        
        for pos in positions:
            clusters = classify_cluster(pos.symbol)
            weight_per_cluster = pos.position_size / len(clusters) if clusters else 0
            
            for cluster in clusters:
                breakdown[cluster]["positions"].append({
                    "symbol": pos.symbol,
                    "size": pos.position_size,
                    "direction": pos.direction.value,
                    "weight": weight_per_cluster,
                })
                breakdown[cluster]["count"] += 1
                breakdown[cluster]["total_size"] += weight_per_cluster
        
        # Calculate normalized exposure
        for cluster in breakdown:
            if total_exposure > 0:
                breakdown[cluster]["exposure"] = min(
                    breakdown[cluster]["total_size"] / total_exposure, 1.0
                )
        
        return dict(breakdown)
    
    def detect_cluster_overload(
        self,
        cluster_exposure: Dict[str, float],
        threshold: float = CLUSTER_CONCENTRATION_THRESHOLD
    ) -> Dict:
        """
        Detect if any cluster is overloaded.
        
        Args:
            cluster_exposure: Cluster exposure dict
            threshold: Concentration threshold
        
        Returns:
            Dict with overload detection results
        """
        overloaded_clusters = []
        max_cluster = None
        max_exposure = 0.0
        
        for cluster, exposure in cluster_exposure.items():
            if exposure > threshold:
                overloaded_clusters.append({
                    "cluster": cluster,
                    "exposure": exposure,
                    "threshold": threshold,
                })
            if exposure > max_exposure:
                max_cluster = cluster
                max_exposure = exposure
        
        return {
            "is_overloaded": len(overloaded_clusters) > 0,
            "overloaded_clusters": overloaded_clusters,
            "max_cluster": max_cluster,
            "max_exposure": max_exposure,
            "threshold": threshold,
        }


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[ClusterExposureEngine] = None


def get_cluster_exposure_engine() -> ClusterExposureEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = ClusterExposureEngine()
    return _engine
