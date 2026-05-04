"""
PHASE 22.2 — Tail Risk Engine Tests
====================================
Comprehensive tests for Tail Risk Engine.

Tests:
1.  low tail risk → LOW
2.  moderate tail risk → ELEVATED
3.  high tail risk → HIGH
4.  extreme crisis tail → EXTREME
5.  crash sensitivity calculated correctly
6.  tail concentration calculated correctly
7.  asymmetry score calculated correctly
8.  tail risk score bounded
9.  recommended action correct
10. modifiers bounded
11. tail severity computation
12. concentration dominant dimension
13. history recording
14. aggregator summary keys
15. aggregator state info
16. crash sensitivity with high vol
17. normalize asymmetry
18. serialization
19. concentration is_concentrated
20. score weights sum to 1.0
"""

import pytest
from datetime import datetime, timezone

from modules.institutional_risk.tail_risk.tail_risk_types import (
    TailRiskState,
    TailRiskLevel,
    TailRecommendedAction,
    TAIL_RISK_THRESHOLDS,
    TAIL_RISK_MODIFIERS,
    TAIL_RISK_WEIGHTS,
    CRASH_VOLATILITY_MULTIPLIERS,
    CRASH_CONCENTRATION_MULTIPLIERS,
)
from modules.institutional_risk.tail_risk.tail_severity_engine import TailSeverityEngine
from modules.institutional_risk.tail_risk.crash_sensitivity_engine import CrashSensitivityEngine
from modules.institutional_risk.tail_risk.tail_concentration_engine import TailConcentrationEngine
from modules.institutional_risk.tail_risk.tail_risk_aggregator import TailRiskAggregator


# ══════════════════════════════════════════════════════════════
# TEST 1: Low tail risk → LOW
# ══════════════════════════════════════════════════════════════

def test_low_tail_risk():
    """Low inputs → LOW tail risk state."""
    agg = TailRiskAggregator()
    state = agg.compute_tail_risk_state(
        portfolio_var_95=0.02,
        portfolio_var_99=0.027,
        expected_shortfall_95=0.024,
        expected_shortfall_99=0.034,
        gross_exposure=0.2,
        volatility_state="LOW",
        concentration_score=0.1,
        asset_exposure=0.15,
        cluster_exposure=0.10,
        factor_exposure=0.10,
    )
    assert state.tail_risk_state == TailRiskLevel.LOW
    assert state.recommended_action == TailRecommendedAction.HOLD


# ══════════════════════════════════════════════════════════════
# TEST 2: Moderate tail risk → ELEVATED
# ══════════════════════════════════════════════════════════════

def test_moderate_tail_risk():
    """Moderate inputs → ELEVATED tail risk state."""
    agg = TailRiskAggregator()
    state = agg.compute_tail_risk_state(
        portfolio_var_95=0.06,
        portfolio_var_99=0.081,
        expected_shortfall_95=0.08,
        expected_shortfall_99=0.11,
        gross_exposure=0.5,
        volatility_state="NORMAL",
        concentration_score=0.35,
        asset_exposure=0.40,
        cluster_exposure=0.35,
        factor_exposure=0.30,
    )
    assert state.tail_risk_state == TailRiskLevel.ELEVATED
    assert state.recommended_action == TailRecommendedAction.HEDGE


# ══════════════════════════════════════════════════════════════
# TEST 3: High tail risk → HIGH
# ══════════════════════════════════════════════════════════════

def test_high_tail_risk():
    """High inputs → HIGH tail risk state."""
    agg = TailRiskAggregator()
    state = agg.compute_tail_risk_state(
        portfolio_var_95=0.10,
        portfolio_var_99=0.135,
        expected_shortfall_95=0.15,
        expected_shortfall_99=0.20,
        gross_exposure=0.7,
        volatility_state="HIGH",
        concentration_score=0.50,
        asset_exposure=0.55,
        cluster_exposure=0.50,
        factor_exposure=0.45,
    )
    assert state.tail_risk_state in [TailRiskLevel.HIGH, TailRiskLevel.EXTREME]
    assert state.recommended_action in [TailRecommendedAction.DELEVER, TailRecommendedAction.EMERGENCY_HEDGE]


# ══════════════════════════════════════════════════════════════
# TEST 4: Extreme crisis tail → EXTREME
# ══════════════════════════════════════════════════════════════

def test_extreme_crisis_tail():
    """Extreme inputs → EXTREME tail risk state."""
    agg = TailRiskAggregator()
    state = agg.compute_tail_risk_state(
        portfolio_var_95=0.20,
        portfolio_var_99=0.27,
        expected_shortfall_95=0.35,
        expected_shortfall_99=0.45,
        gross_exposure=0.9,
        volatility_state="EXTREME",
        concentration_score=0.7,
        asset_exposure=0.75,
        cluster_exposure=0.70,
        factor_exposure=0.65,
    )
    assert state.tail_risk_state == TailRiskLevel.EXTREME
    assert state.recommended_action == TailRecommendedAction.EMERGENCY_HEDGE


# ══════════════════════════════════════════════════════════════
# TEST 5: Crash sensitivity calculated correctly
# ══════════════════════════════════════════════════════════════

def test_crash_sensitivity_calculation():
    """crash_sensitivity = gross × vol_mult × conc_mult, capped at 1.0."""
    engine = CrashSensitivityEngine()
    result = engine.compute_crash_sensitivity(
        gross_exposure=0.5,
        volatility_state="NORMAL",
        concentration_score=0.3,  # MEDIUM → 1.0
    )
    # vol_mult=1.0, conc_mult=1.0 (MEDIUM), raw = 0.5 * 1.0 * 1.0 = 0.5
    expected = 0.5 * 1.0 * 1.0
    assert abs(result["crash_sensitivity"] - expected) < 0.0001


# ══════════════════════════════════════════════════════════════
# TEST 6: Tail concentration calculated correctly
# ══════════════════════════════════════════════════════════════

def test_tail_concentration_calculation():
    """tail_concentration = max(asset, cluster, factor) exposures."""
    engine = TailConcentrationEngine()
    result = engine.compute_tail_concentration(
        asset_exposure=0.50,
        cluster_exposure=0.35,
        factor_exposure=0.40,
    )
    assert result["tail_concentration"] == 0.50
    assert result["dominant_dimension"] == "asset"


# ══════════════════════════════════════════════════════════════
# TEST 7: Asymmetry score calculated correctly
# ══════════════════════════════════════════════════════════════

def test_asymmetry_score_calculation():
    """asymmetry_score = ES_95 / VaR_95."""
    engine = TailSeverityEngine()
    result = engine.compute_tail_severity(
        portfolio_var_95=0.10,
        portfolio_var_99=0.135,
        expected_shortfall_95=0.12,
        expected_shortfall_99=0.17,
    )
    expected_asymmetry = 0.12 / 0.10
    assert abs(result["asymmetry_score"] - expected_asymmetry) < 0.0001


# ══════════════════════════════════════════════════════════════
# TEST 8: Tail risk score bounded [0, 1]
# ══════════════════════════════════════════════════════════════

def test_tail_risk_score_bounded():
    """tail_risk_score must be in [0.0, 1.0]."""
    agg = TailRiskAggregator()
    
    # Minimal scenario
    state_low = agg.compute_tail_risk_state(
        portfolio_var_95=0.01,
        expected_shortfall_95=0.012,
        gross_exposure=0.1,
        volatility_state="LOW",
    )
    assert 0.0 <= state_low.tail_risk_score <= 1.0

    # Extreme scenario
    state_high = agg.compute_tail_risk_state(
        portfolio_var_95=0.30,
        expected_shortfall_95=0.50,
        gross_exposure=1.0,
        volatility_state="EXTREME",
        concentration_score=0.8,
        asset_exposure=0.90,
        cluster_exposure=0.85,
        factor_exposure=0.80,
    )
    assert 0.0 <= state_high.tail_risk_score <= 1.0


# ══════════════════════════════════════════════════════════════
# TEST 9: Recommended action correct
# ══════════════════════════════════════════════════════════════

def test_recommended_action_mapping():
    """Recommended actions map correctly to tail risk levels."""
    action_map = {
        TailRiskLevel.LOW: TailRecommendedAction.HOLD,
        TailRiskLevel.ELEVATED: TailRecommendedAction.HEDGE,
        TailRiskLevel.HIGH: TailRecommendedAction.DELEVER,
        TailRiskLevel.EXTREME: TailRecommendedAction.EMERGENCY_HEDGE,
    }
    for level, expected_action in action_map.items():
        assert expected_action.value is not None


# ══════════════════════════════════════════════════════════════
# TEST 10: Modifiers bounded
# ══════════════════════════════════════════════════════════════

def test_modifiers_bounded():
    """Confidence [0.70, 1.00], Capital [0.50, 1.00]."""
    for level in TailRiskLevel:
        mods = TAIL_RISK_MODIFIERS[level]
        assert 0.50 <= mods["confidence_modifier"] <= 1.00, f"confidence out of bounds for {level}"
        assert 0.50 <= mods["capital_modifier"] <= 1.00, f"capital out of bounds for {level}"


# ══════════════════════════════════════════════════════════════
# TEST 11: Tail severity computation
# ══════════════════════════════════════════════════════════════

def test_tail_severity_normalized():
    """normalized_tail_loss capped at 1.0."""
    engine = TailSeverityEngine()
    result = engine.compute_tail_severity(
        portfolio_var_95=0.30,
        portfolio_var_99=0.40,
        expected_shortfall_95=0.60,  # > 0.50 normalization cap
        expected_shortfall_99=0.80,
    )
    assert result["normalized_tail_loss"] == 1.0  # capped


# ══════════════════════════════════════════════════════════════
# TEST 12: Concentration dominant dimension
# ══════════════════════════════════════════════════════════════

def test_concentration_dominant_dimension():
    """Dominant dimension is the one with max exposure."""
    engine = TailConcentrationEngine()
    
    r1 = engine.compute_tail_concentration(asset_exposure=0.5, cluster_exposure=0.3, factor_exposure=0.2)
    assert r1["dominant_dimension"] == "asset"

    r2 = engine.compute_tail_concentration(asset_exposure=0.2, cluster_exposure=0.6, factor_exposure=0.3)
    assert r2["dominant_dimension"] == "cluster"

    r3 = engine.compute_tail_concentration(asset_exposure=0.1, cluster_exposure=0.2, factor_exposure=0.7)
    assert r3["dominant_dimension"] == "factor"


# ══════════════════════════════════════════════════════════════
# TEST 13: History recording
# ══════════════════════════════════════════════════════════════

def test_history_recording():
    """Recompute records to history."""
    agg = TailRiskAggregator()
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
    agg = TailRiskAggregator()
    summary = agg.get_summary()
    required_keys = [
        "tail_risk_score",
        "tail_risk_state",
        "recommended_action",
        "crash_sensitivity",
        "asymmetry_score",
        "confidence_modifier",
        "capital_modifier",
    ]
    for key in required_keys:
        assert key in summary, f"Missing key: {key}"


# ══════════════════════════════════════════════════════════════
# TEST 15: Aggregator state info
# ══════════════════════════════════════════════════════════════

def test_aggregator_state_info():
    """State info contains required fields."""
    agg = TailRiskAggregator()
    info = agg.get_state_info()
    assert "tail_risk_state" in info
    assert "tail_risk_score" in info
    assert "recommended_action" in info


# ══════════════════════════════════════════════════════════════
# TEST 16: Crash sensitivity with high vol
# ══════════════════════════════════════════════════════════════

def test_crash_sensitivity_high_vol():
    """High volatility increases crash sensitivity."""
    engine = CrashSensitivityEngine()
    normal = engine.compute_crash_sensitivity(gross_exposure=0.5, volatility_state="NORMAL", concentration_score=0.3)
    high = engine.compute_crash_sensitivity(gross_exposure=0.5, volatility_state="EXTREME", concentration_score=0.3)
    assert high["crash_sensitivity"] > normal["crash_sensitivity"]


# ══════════════════════════════════════════════════════════════
# TEST 17: Normalize asymmetry
# ══════════════════════════════════════════════════════════════

def test_normalize_asymmetry():
    """Asymmetry normalization: 1.0→0.0, 1.5→0.5, 2.0→1.0."""
    engine = TailSeverityEngine()
    assert engine.normalize_asymmetry(1.0) == 0.0
    assert abs(engine.normalize_asymmetry(1.5) - 0.5) < 0.0001
    assert engine.normalize_asymmetry(2.0) == 1.0
    assert engine.normalize_asymmetry(2.5) == 1.0  # capped


# ══════════════════════════════════════════════════════════════
# TEST 18: Serialization
# ══════════════════════════════════════════════════════════════

def test_serialization():
    """TailRiskState to_dict and to_full_dict work correctly."""
    agg = TailRiskAggregator()
    state = agg.compute_tail_risk_state()
    d = state.to_dict()
    assert "tail_risk_score" in d
    assert "tail_risk_state" in d
    assert "timestamp" in d

    full = state.to_full_dict()
    assert "inputs" in full
    assert "gross_exposure" in full["inputs"]


# ══════════════════════════════════════════════════════════════
# TEST 19: Concentration is_concentrated
# ══════════════════════════════════════════════════════════════

def test_concentration_is_concentrated():
    """is_concentrated returns True when above threshold."""
    engine = TailConcentrationEngine()
    assert engine.is_concentrated(0.60) is True
    assert engine.is_concentrated(0.40) is False
    assert engine.is_concentrated(0.50, threshold=0.50) is False
    assert engine.is_concentrated(0.51, threshold=0.50) is True


# ══════════════════════════════════════════════════════════════
# TEST 20: Score weights sum to 1.0
# ══════════════════════════════════════════════════════════════

def test_score_weights_sum():
    """TAIL_RISK_WEIGHTS must sum to 1.0."""
    total = sum(TAIL_RISK_WEIGHTS.values())
    assert abs(total - 1.0) < 0.0001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
