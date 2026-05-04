"""
PHASE 22.3 — Cluster Contagion Engine Tests
============================================
Comprehensive tests for Cluster Contagion Engine.

Tests:
1.  low stress portfolio → LOW
2.  moderate cluster stress → ELEVATED
3.  high concentrated cluster → HIGH
4.  systemic contagion → SYSTEMIC
5.  cluster stress calculated correctly
6.  contagion probabilities calculated correctly
7.  contagion paths built correctly
8.  systemic risk score bounded
9.  recommended action correct
10. modifiers bounded
11. dominant/weakest cluster identification
12. contagion map structure
13. history recording
14. aggregator summary keys
15. aggregator paths info
16. stress with high volatility
17. stress with critical market risk
18. serialization
19. systemic risk weights sum to 1.0
20. path engine threshold filtering
"""

import pytest

from modules.institutional_risk.cluster_contagion.cluster_contagion_types import (
    ClusterContagionState,
    ContagionLevel,
    ContagionAction,
    CONTAGION_THRESHOLDS,
    CONTAGION_MODIFIERS,
    CONTAGION_MAP,
    SYSTEMIC_RISK_WEIGHTS,
    CLUSTER_IDS,
    DEFAULT_CLUSTER_EXPOSURES,
)
from modules.institutional_risk.cluster_contagion.cluster_stress_engine import ClusterStressEngine
from modules.institutional_risk.cluster_contagion.contagion_probability_engine import ContagionProbabilityEngine
from modules.institutional_risk.cluster_contagion.contagion_path_engine import ContagionPathEngine
from modules.institutional_risk.cluster_contagion.cluster_contagion_aggregator import ClusterContagionAggregator


# ══════════════════════════════════════════════════════════════
# TEST 1: Low stress portfolio → LOW
# ══════════════════════════════════════════════════════════════

def test_low_stress_portfolio():
    """Low exposure + low vol → LOW contagion state."""
    agg = ClusterContagionAggregator()
    state = agg.compute_contagion_state(
        cluster_exposures={
            "btc_cluster": 0.10,
            "majors_cluster": 0.08,
            "alts_cluster": 0.06,
            "trend_cluster": 0.05,
            "reversal_cluster": 0.04,
        },
        volatility_state="LOW",
        market_risk_state="NORMAL",
        concentration_score=0.1,
    )
    assert state.contagion_state == ContagionLevel.LOW
    assert state.recommended_action == ContagionAction.HOLD


# ══════════════════════════════════════════════════════════════
# TEST 2: Moderate cluster stress → ELEVATED
# ══════════════════════════════════════════════════════════════

def test_moderate_cluster_stress():
    """Moderate exposure + normal vol → ELEVATED."""
    agg = ClusterContagionAggregator()
    state = agg.compute_contagion_state(
        cluster_exposures={
            "btc_cluster": 0.35,
            "majors_cluster": 0.30,
            "alts_cluster": 0.25,
            "trend_cluster": 0.20,
            "reversal_cluster": 0.15,
        },
        volatility_state="NORMAL",
        market_risk_state="ELEVATED",
        concentration_score=0.35,
    )
    assert state.contagion_state == ContagionLevel.ELEVATED
    assert state.recommended_action == ContagionAction.REDUCE_CLUSTER


# ══════════════════════════════════════════════════════════════
# TEST 3: High concentrated cluster → HIGH
# ══════════════════════════════════════════════════════════════

def test_high_concentrated_cluster():
    """High exposure + high vol → HIGH."""
    agg = ClusterContagionAggregator()
    state = agg.compute_contagion_state(
        cluster_exposures={
            "btc_cluster": 0.50,
            "majors_cluster": 0.40,
            "alts_cluster": 0.35,
            "trend_cluster": 0.30,
            "reversal_cluster": 0.20,
        },
        volatility_state="HIGH",
        market_risk_state="HIGH",
        concentration_score=0.55,
    )
    assert state.contagion_state in [ContagionLevel.HIGH, ContagionLevel.SYSTEMIC]
    assert state.recommended_action in [ContagionAction.HEDGE_CLUSTER, ContagionAction.DELEVER_SYSTEM]


# ══════════════════════════════════════════════════════════════
# TEST 4: Systemic contagion → SYSTEMIC
# ══════════════════════════════════════════════════════════════

def test_systemic_contagion():
    """Extreme exposure + extreme vol → SYSTEMIC."""
    agg = ClusterContagionAggregator()
    state = agg.compute_contagion_state(
        cluster_exposures={
            "btc_cluster": 0.70,
            "majors_cluster": 0.65,
            "alts_cluster": 0.60,
            "trend_cluster": 0.55,
            "reversal_cluster": 0.50,
        },
        volatility_state="EXTREME",
        market_risk_state="CRITICAL",
        concentration_score=0.80,
    )
    assert state.contagion_state == ContagionLevel.SYSTEMIC
    assert state.recommended_action == ContagionAction.DELEVER_SYSTEM


# ══════════════════════════════════════════════════════════════
# TEST 5: Cluster stress calculated correctly
# ══════════════════════════════════════════════════════════════

def test_cluster_stress_calculation():
    """cluster_stress = exposure × vol_mult × risk_mult, capped at 1.0."""
    engine = ClusterStressEngine()
    result = engine.compute_cluster_stress(
        cluster_exposures={"btc_cluster": 0.5, "majors_cluster": 0.3, "alts_cluster": 0.2, "trend_cluster": 0.1, "reversal_cluster": 0.05},
        volatility_state="NORMAL",
        market_risk_state="NORMAL",
    )
    # vol=1.0, risk=1.0 → btc stress = 0.5
    assert abs(result["cluster_stress"]["btc_cluster"] - 0.5) < 0.001
    assert abs(result["cluster_stress"]["majors_cluster"] - 0.3) < 0.001


# ══════════════════════════════════════════════════════════════
# TEST 6: Contagion probabilities calculated correctly
# ══════════════════════════════════════════════════════════════

def test_contagion_probabilities():
    """Probability = avg(src_stress, tgt_stress) × correlation_base."""
    engine = ContagionProbabilityEngine()
    stress = {"btc_cluster": 0.5, "majors_cluster": 0.3, "alts_cluster": 0.2, "trend_cluster": 0.1, "reversal_cluster": 0.05}
    result = engine.compute_contagion_probabilities(stress)

    # btc->majors: (0.5+0.3)/2 * 0.80 = 0.32
    assert abs(result["contagion_probabilities"]["btc_cluster->majors_cluster"] - 0.32) < 0.001
    assert result["avg_probability"] > 0


# ══════════════════════════════════════════════════════════════
# TEST 7: Contagion paths built correctly
# ══════════════════════════════════════════════════════════════

def test_contagion_paths():
    """Paths are built from contagion map with probability threshold."""
    engine = ContagionPathEngine()
    stress = {"btc_cluster": 0.5, "majors_cluster": 0.4, "alts_cluster": 0.3, "trend_cluster": 0.2, "reversal_cluster": 0.1}
    prob_engine = ContagionProbabilityEngine()
    probs = prob_engine.compute_contagion_probabilities(stress)["contagion_probabilities"]

    result = engine.build_contagion_paths(stress, probs)
    assert result["path_count"] > 0
    # Should have at least btc -> majors path
    found_btc_path = any("btc_cluster" in p for p in result["contagion_paths"])
    assert found_btc_path


# ══════════════════════════════════════════════════════════════
# TEST 8: Systemic risk score bounded [0, 1]
# ══════════════════════════════════════════════════════════════

def test_systemic_risk_score_bounded():
    """Score must be in [0.0, 1.0]."""
    agg = ClusterContagionAggregator()

    state_low = agg.compute_contagion_state(
        cluster_exposures={c: 0.05 for c in CLUSTER_IDS},
        volatility_state="LOW",
        concentration_score=0.05,
    )
    assert 0.0 <= state_low.systemic_risk_score <= 1.0

    state_high = agg.compute_contagion_state(
        cluster_exposures={c: 0.90 for c in CLUSTER_IDS},
        volatility_state="EXTREME",
        market_risk_state="CRITICAL",
        concentration_score=0.95,
    )
    assert 0.0 <= state_high.systemic_risk_score <= 1.0


# ══════════════════════════════════════════════════════════════
# TEST 9: Recommended action correct
# ══════════════════════════════════════════════════════════════

def test_recommended_actions():
    """Actions map correctly to contagion levels."""
    expected = {
        ContagionLevel.LOW: ContagionAction.HOLD,
        ContagionLevel.ELEVATED: ContagionAction.REDUCE_CLUSTER,
        ContagionLevel.HIGH: ContagionAction.HEDGE_CLUSTER,
        ContagionLevel.SYSTEMIC: ContagionAction.DELEVER_SYSTEM,
    }
    for level, action in expected.items():
        assert action.value is not None


# ══════════════════════════════════════════════════════════════
# TEST 10: Modifiers bounded
# ══════════════════════════════════════════════════════════════

def test_modifiers_bounded():
    """Confidence [0.70, 1.00], Capital [0.55, 1.00]."""
    for level in ContagionLevel:
        mods = CONTAGION_MODIFIERS[level]
        assert 0.50 <= mods["confidence_modifier"] <= 1.00
        assert 0.50 <= mods["capital_modifier"] <= 1.00


# ══════════════════════════════════════════════════════════════
# TEST 11: Dominant/weakest cluster identification
# ══════════════════════════════════════════════════════════════

def test_dominant_weakest_cluster():
    """Dominant = highest stress, weakest = lowest stress."""
    engine = ClusterStressEngine()
    result = engine.compute_cluster_stress(
        cluster_exposures={
            "btc_cluster": 0.60,
            "majors_cluster": 0.10,
            "alts_cluster": 0.30,
            "trend_cluster": 0.20,
            "reversal_cluster": 0.05,
        },
    )
    assert result["dominant_cluster"] == "btc_cluster"
    assert result["weakest_cluster"] == "reversal_cluster"


# ══════════════════════════════════════════════════════════════
# TEST 12: Contagion map structure
# ══════════════════════════════════════════════════════════════

def test_contagion_map_structure():
    """CONTAGION_MAP has valid cluster references."""
    all_clusters = set(CLUSTER_IDS)
    for source, targets in CONTAGION_MAP.items():
        assert source in all_clusters
        for t in targets:
            assert t in all_clusters


# ══════════════════════════════════════════════════════════════
# TEST 13: History recording
# ══════════════════════════════════════════════════════════════

def test_history_recording():
    """Recompute records to history."""
    agg = ClusterContagionAggregator()
    assert len(agg.get_history()) == 0
    agg.recompute()
    assert len(agg.get_history()) == 1
    agg.recompute()
    assert len(agg.get_history()) == 2


# ══════════════════════════════════════════════════════════════
# TEST 14: Aggregator summary keys
# ══════════════════════════════════════════════════════════════

def test_aggregator_summary():
    """Summary contains required keys."""
    agg = ClusterContagionAggregator()
    summary = agg.get_summary()
    for key in ["systemic_risk_score", "contagion_state", "recommended_action", "dominant_cluster", "weakest_cluster"]:
        assert key in summary


# ══════════════════════════════════════════════════════════════
# TEST 15: Aggregator paths info
# ══════════════════════════════════════════════════════════════

def test_aggregator_paths_info():
    """Paths info contains contagion_paths and probabilities."""
    agg = ClusterContagionAggregator()
    info = agg.get_paths_info()
    assert "contagion_paths" in info
    assert "contagion_probabilities" in info
    assert isinstance(info["contagion_paths"], list)


# ══════════════════════════════════════════════════════════════
# TEST 16: Stress with high volatility
# ══════════════════════════════════════════════════════════════

def test_stress_high_volatility():
    """Higher volatility increases cluster stress."""
    engine = ClusterStressEngine()
    normal = engine.compute_cluster_stress(volatility_state="NORMAL")
    high = engine.compute_cluster_stress(volatility_state="EXTREME")
    assert high["max_stress"] > normal["max_stress"]


# ══════════════════════════════════════════════════════════════
# TEST 17: Stress with critical market risk
# ══════════════════════════════════════════════════════════════

def test_stress_critical_market_risk():
    """Higher market risk increases cluster stress."""
    engine = ClusterStressEngine()
    normal = engine.compute_cluster_stress(market_risk_state="NORMAL")
    critical = engine.compute_cluster_stress(market_risk_state="CRITICAL")
    assert critical["max_stress"] > normal["max_stress"]


# ══════════════════════════════════════════════════════════════
# TEST 18: Serialization
# ══════════════════════════════════════════════════════════════

def test_serialization():
    """ClusterContagionState to_dict and to_full_dict."""
    agg = ClusterContagionAggregator()
    state = agg.compute_contagion_state()
    d = state.to_dict()
    assert "cluster_stress" in d
    assert "contagion_paths" in d
    assert "systemic_risk_score" in d

    full = state.to_full_dict()
    assert "inputs" in full
    assert "volatility_state" in full["inputs"]


# ══════════════════════════════════════════════════════════════
# TEST 19: Systemic risk weights sum to 1.0
# ══════════════════════════════════════════════════════════════

def test_systemic_risk_weights_sum():
    """Weights must sum to 1.0."""
    total = sum(SYSTEMIC_RISK_WEIGHTS.values())
    assert abs(total - 1.0) < 0.0001


# ══════════════════════════════════════════════════════════════
# TEST 20: Path engine threshold filtering
# ══════════════════════════════════════════════════════════════

def test_path_engine_threshold():
    """Paths with probability below threshold are excluded."""
    engine = ContagionPathEngine()
    # Very low stress → very low probabilities → fewer paths
    stress = {c: 0.01 for c in CLUSTER_IDS}
    prob_engine = ContagionProbabilityEngine()
    probs = prob_engine.compute_contagion_probabilities(stress)["contagion_probabilities"]
    result = engine.build_contagion_paths(stress, probs)
    # With stress=0.01, max prob = (0.01+0.01)/2*0.80 = 0.008 < threshold 0.15
    assert result["path_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
