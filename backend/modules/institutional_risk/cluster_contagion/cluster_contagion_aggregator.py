"""
PHASE 22.3 — Cluster Contagion Aggregator
=========================================
Main aggregator for Cluster Contagion Engine.

Combines:
- Cluster Stress Engine
- Contagion Probability Engine
- Contagion Path Engine

Into unified Cluster Contagion state.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from modules.institutional_risk.cluster_contagion.cluster_contagion_types import (
    ClusterContagionState,
    ContagionHistoryEntry,
    ContagionLevel,
    ContagionAction,
    CONTAGION_THRESHOLDS,
    CONTAGION_MODIFIERS,
    SYSTEMIC_RISK_WEIGHTS,
    DEFAULT_CLUSTER_EXPOSURES,
)
from modules.institutional_risk.cluster_contagion.cluster_stress_engine import (
    get_cluster_stress_engine,
)
from modules.institutional_risk.cluster_contagion.contagion_probability_engine import (
    get_contagion_probability_engine,
)
from modules.institutional_risk.cluster_contagion.contagion_path_engine import (
    get_contagion_path_engine,
)


class ClusterContagionAggregator:
    """
    Cluster Contagion Aggregator - PHASE 22.3
    
    Unified Cluster Contagion Engine combining all sub-engines.
    """

    def __init__(self):
        self.stress_engine = get_cluster_stress_engine()
        self.probability_engine = get_contagion_probability_engine()
        self.path_engine = get_contagion_path_engine()
        self._history: List[ContagionHistoryEntry] = []

    # ═══════════════════════════════════════════════════════════
    # MAIN API
    # ═══════════════════════════════════════════════════════════

    def compute_contagion_state(
        self,
        cluster_exposures: Optional[Dict[str, float]] = None,
        volatility_state: str = "NORMAL",
        market_risk_state: str = "NORMAL",
        concentration_score: float = 0.3,
    ) -> ClusterContagionState:
        """Compute unified cluster contagion state."""
        now = datetime.now(timezone.utc)

        # 1. Cluster Stress
        stress_result = self.stress_engine.compute_cluster_stress(
            cluster_exposures=cluster_exposures,
            volatility_state=volatility_state,
            market_risk_state=market_risk_state,
        )
        cluster_stress = stress_result["cluster_stress"]
        dominant_cluster = stress_result["dominant_cluster"]
        weakest_cluster = stress_result["weakest_cluster"]
        max_stress = stress_result["max_stress"]

        # 2. Contagion Probabilities
        prob_result = self.probability_engine.compute_contagion_probabilities(
            cluster_stress=cluster_stress,
        )
        contagion_probabilities = prob_result["contagion_probabilities"]
        avg_prob = prob_result["avg_probability"]

        # 3. Contagion Paths
        path_result = self.path_engine.build_contagion_paths(
            cluster_stress=cluster_stress,
            contagion_probabilities=contagion_probabilities,
        )
        contagion_paths = path_result["contagion_paths"]

        # 4. Systemic Risk Score
        w = SYSTEMIC_RISK_WEIGHTS
        systemic_risk_score = (
            w["max_cluster_stress"] * max_stress
            + w["avg_contagion_prob"] * avg_prob
            + w["concentration_score"] * min(concentration_score, 1.0)
        )
        systemic_risk_score = min(max(systemic_risk_score, 0.0), 1.0)

        # 5. Classify state
        contagion_level = self._classify_contagion(systemic_risk_score)

        # 6. Recommended action
        action_map = {
            ContagionLevel.LOW: ContagionAction.HOLD,
            ContagionLevel.ELEVATED: ContagionAction.REDUCE_CLUSTER,
            ContagionLevel.HIGH: ContagionAction.HEDGE_CLUSTER,
            ContagionLevel.SYSTEMIC: ContagionAction.DELEVER_SYSTEM,
        }
        recommended_action = action_map[contagion_level]

        # 7. Modifiers
        modifiers = CONTAGION_MODIFIERS[contagion_level]
        confidence_modifier = modifiers["confidence_modifier"]
        capital_modifier = modifiers["capital_modifier"]

        # 8. Reason
        reason = self._build_reason(
            contagion_level=contagion_level,
            dominant_cluster=dominant_cluster,
            weakest_cluster=weakest_cluster,
            max_stress=max_stress,
            contagion_paths=contagion_paths,
            volatility_state=volatility_state,
        )

        return ClusterContagionState(
            cluster_stress=cluster_stress,
            contagion_probabilities=contagion_probabilities,
            contagion_paths=contagion_paths,
            systemic_risk_score=systemic_risk_score,
            contagion_state=contagion_level,
            recommended_action=recommended_action,
            confidence_modifier=confidence_modifier,
            capital_modifier=capital_modifier,
            dominant_cluster=dominant_cluster,
            weakest_cluster=weakest_cluster,
            reason=reason,
            volatility_state=volatility_state,
            market_risk_state=market_risk_state,
            concentration_score=concentration_score,
            timestamp=now,
        )

    def recompute(self) -> ClusterContagionState:
        state = self.compute_contagion_state()
        self._record_history(state)
        return state

    def get_summary(self) -> Dict[str, Any]:
        state = self.compute_contagion_state()
        return state.to_summary()

    def get_stress_info(self) -> Dict[str, Any]:
        state = self.compute_contagion_state()
        return {
            "cluster_stress": {k: round(v, 4) for k, v in state.cluster_stress.items()},
            "dominant_cluster": state.dominant_cluster,
            "weakest_cluster": state.weakest_cluster,
            "contagion_state": state.contagion_state.value,
        }

    def get_paths_info(self) -> Dict[str, Any]:
        state = self.compute_contagion_state()
        return {
            "contagion_paths": state.contagion_paths,
            "contagion_probabilities": {k: round(v, 4) for k, v in state.contagion_probabilities.items()},
            "systemic_risk_score": round(state.systemic_risk_score, 4),
            "contagion_state": state.contagion_state.value,
        }

    def get_history(self, limit: int = 20) -> List[ContagionHistoryEntry]:
        return self._history[-limit:]

    # ═══════════════════════════════════════════════════════════
    # INTERNAL METHODS
    # ═══════════════════════════════════════════════════════════

    def _classify_contagion(self, score: float) -> ContagionLevel:
        if score < CONTAGION_THRESHOLDS[ContagionLevel.LOW]:
            return ContagionLevel.LOW
        elif score < CONTAGION_THRESHOLDS[ContagionLevel.ELEVATED]:
            return ContagionLevel.ELEVATED
        elif score < CONTAGION_THRESHOLDS[ContagionLevel.HIGH]:
            return ContagionLevel.HIGH
        else:
            return ContagionLevel.SYSTEMIC

    def _record_history(self, state: ClusterContagionState):
        entry = ContagionHistoryEntry(
            contagion_state=state.contagion_state,
            systemic_risk_score=state.systemic_risk_score,
            dominant_cluster=state.dominant_cluster,
            recommended_action=state.recommended_action,
        )
        self._history.append(entry)
        if len(self._history) > 100:
            self._history = self._history[-100:]

    def _build_reason(
        self,
        contagion_level: ContagionLevel,
        dominant_cluster: str,
        weakest_cluster: str,
        max_stress: float,
        contagion_paths: List[str],
        volatility_state: str,
    ) -> str:
        parts = []

        level_text = {
            ContagionLevel.LOW: "low contagion risk",
            ContagionLevel.ELEVATED: "elevated cluster contagion",
            ContagionLevel.HIGH: "high cluster contagion",
            ContagionLevel.SYSTEMIC: "systemic cluster contagion",
        }
        parts.append(level_text[contagion_level])

        # Dominant cluster
        clean_name = dominant_cluster.replace("_cluster", "")
        parts.append(f"{clean_name} cluster stress dominant")

        # Path context
        if contagion_paths:
            parts.append(f"spillover via {len(contagion_paths)} paths")

        vol_upper = volatility_state.upper()
        if vol_upper in ["HIGH", "EXPANDING", "EXTREME"]:
            parts.append(f"{vol_upper.lower()} volatility")

        return " under ".join(parts[:3])


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_aggregator: Optional[ClusterContagionAggregator] = None


def get_cluster_contagion_aggregator() -> ClusterContagionAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = ClusterContagionAggregator()
    return _aggregator
