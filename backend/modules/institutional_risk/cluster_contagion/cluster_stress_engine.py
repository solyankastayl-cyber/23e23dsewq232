"""
PHASE 22.3 — Cluster Stress Engine
==================================
Sub-engine for calculating per-cluster stress scores.

Computes stress for each cluster based on exposure,
volatility, and market risk.
"""

from typing import Dict, Optional, Any

from modules.institutional_risk.cluster_contagion.cluster_contagion_types import (
    CLUSTER_IDS,
    DEFAULT_CLUSTER_EXPOSURES,
    CLUSTER_VOLATILITY_MULTIPLIERS,
    MARKET_RISK_MULTIPLIERS,
)


class ClusterStressEngine:
    """
    Cluster Stress Sub-Engine.
    
    Calculates stress score for each cluster:
    cluster_stress = cluster_exposure × vol_mult × market_risk_mult
    Capped at 1.0.
    """

    def compute_cluster_stress(
        self,
        cluster_exposures: Optional[Dict[str, float]] = None,
        volatility_state: str = "NORMAL",
        market_risk_state: str = "NORMAL",
    ) -> Dict[str, Any]:
        """
        Compute stress score for each cluster.
        
        Returns:
            {
                "cluster_stress": {cluster_id: stress_score},
                "max_stress": float,
                "dominant_cluster": str,
                "weakest_cluster": str,
            }
        """
        exposures = cluster_exposures or DEFAULT_CLUSTER_EXPOSURES.copy()

        vol_mult = CLUSTER_VOLATILITY_MULTIPLIERS.get(volatility_state.upper(), 1.0)
        risk_mult = MARKET_RISK_MULTIPLIERS.get(market_risk_state.upper(), 1.0)

        stress = {}
        for cid in CLUSTER_IDS:
            exp = exposures.get(cid, 0.0)
            raw = exp * vol_mult * risk_mult
            stress[cid] = min(raw, 1.0)

        # Dominant = highest stress, weakest = lowest stress (most vulnerable to contagion)
        dominant = max(stress, key=stress.get)
        weakest = min(stress, key=stress.get)

        return {
            "cluster_stress": stress,
            "max_stress": max(stress.values()),
            "dominant_cluster": dominant,
            "weakest_cluster": weakest,
        }


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[ClusterStressEngine] = None


def get_cluster_stress_engine() -> ClusterStressEngine:
    global _engine
    if _engine is None:
        _engine = ClusterStressEngine()
    return _engine
