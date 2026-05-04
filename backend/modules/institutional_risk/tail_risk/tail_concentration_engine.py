"""
PHASE 22.2 — Tail Concentration Engine
======================================
Sub-engine for measuring tail risk concentration.

Evaluates how concentrated the tail risk is across
assets, clusters, and factors.
"""

from typing import Dict, Optional, Any, List


class TailConcentrationEngine:
    """
    Tail Concentration Sub-Engine.
    
    Calculates tail_concentration as max exposure
    across asset, cluster, and factor dimensions.
    Normalized to 0..1.
    """

    def compute_tail_concentration(
        self,
        asset_exposure: float = 0.35,
        cluster_exposure: float = 0.30,
        factor_exposure: float = 0.25,
    ) -> Dict[str, Any]:
        """
        Compute tail concentration.
        
        Formula:
        tail_concentration = max(asset_exposure, cluster_exposure, factor_exposure)
        Normalized to 0..1.
        
        Returns:
            {
                "tail_concentration": float,
                "dominant_dimension": str,
                "exposures": dict,
            }
        """
        exposures = {
            "asset": asset_exposure,
            "cluster": cluster_exposure,
            "factor": factor_exposure,
        }

        # Max across dimensions
        max_exposure = max(asset_exposure, cluster_exposure, factor_exposure)

        # Normalize to 0..1
        tail_concentration = min(max_exposure, 1.0)

        # Determine dominant dimension
        dominant = max(exposures, key=exposures.get)

        return {
            "tail_concentration": tail_concentration,
            "dominant_dimension": dominant,
            "exposures": exposures,
        }

    def is_concentrated(self, tail_concentration: float, threshold: float = 0.50) -> bool:
        """Check if tail risk is concentrated."""
        return tail_concentration > threshold


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[TailConcentrationEngine] = None


def get_tail_concentration_engine() -> TailConcentrationEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = TailConcentrationEngine()
    return _engine
