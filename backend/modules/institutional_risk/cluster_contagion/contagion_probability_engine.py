"""
PHASE 22.3 — Contagion Probability Engine
=========================================
Sub-engine for calculating contagion probability between clusters.

Estimates how likely stress in one cluster spreads to another.
"""

from typing import Dict, Optional, Any

from modules.institutional_risk.cluster_contagion.cluster_contagion_types import (
    CONTAGION_MAP,
)


class ContagionProbabilityEngine:
    """
    Contagion Probability Sub-Engine.
    
    Calculates probability of stress spreading between linked clusters.
    
    probability = (source_stress + target_stress) / 2 × correlation_base
    correlation_base varies by pair.
    """

    # Base correlation factors between cluster pairs
    CORRELATION_BASE = {
        ("btc_cluster", "majors_cluster"): 0.80,
        ("btc_cluster", "alts_cluster"): 0.65,
        ("majors_cluster", "alts_cluster"): 0.70,
        ("trend_cluster", "majors_cluster"): 0.55,
        ("alts_cluster", "reversal_cluster"): 0.50,
    }

    def compute_contagion_probabilities(
        self,
        cluster_stress: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Compute contagion probability for each linked pair.
        
        Returns:
            {
                "contagion_probabilities": {"src->tgt": probability},
                "avg_probability": float,
                "max_probability": float,
                "max_pair": str,
            }
        """
        probabilities = {}

        for source, targets in CONTAGION_MAP.items():
            src_stress = cluster_stress.get(source, 0.0)
            for target in targets:
                tgt_stress = cluster_stress.get(target, 0.0)
                corr_base = self.CORRELATION_BASE.get(
                    (source, target), 0.50
                )

                # Probability = avg stress of pair × correlation base
                prob = ((src_stress + tgt_stress) / 2.0) * corr_base
                prob = min(prob, 1.0)

                pair_key = f"{source}->{target}"
                probabilities[pair_key] = prob

        avg_prob = (
            sum(probabilities.values()) / len(probabilities)
            if probabilities else 0.0
        )
        max_prob = max(probabilities.values()) if probabilities else 0.0
        max_pair = (
            max(probabilities, key=probabilities.get)
            if probabilities else "none"
        )

        return {
            "contagion_probabilities": probabilities,
            "avg_probability": avg_prob,
            "max_probability": max_prob,
            "max_pair": max_pair,
        }


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[ContagionProbabilityEngine] = None


def get_contagion_probability_engine() -> ContagionProbabilityEngine:
    global _engine
    if _engine is None:
        _engine = ContagionProbabilityEngine()
    return _engine
