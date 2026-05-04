"""
PHASE 22.1 — VaR Engine Tests
==============================
Comprehensive tests for VaR Engine.

Tests:
1.  low vol portfolio → NORMAL
2.  normal regime moderate exposure → ELEVATED
3.  high vol + high exposure → HIGH
4.  crisis / expanding vol → CRITICAL
5.  var_95 computed correctly
6.  var_99 computed correctly
7.  expected shortfall computed correctly
8.  risk state classification correct
9.  recommended action correct
10. modifiers bounded
11. tail risk ratio correct
12. override bump works
13. history recording
14. aggregator summary
15. aggregator state info
"""

import pytest
from datetime import datetime, timezone

from modules.institutional_risk.var_engine.var_types import (
    VaRState,
    VaRHistoryEntry,
    RiskState,
    RecommendedAction,
    RISK_STATE_THRESHOLDS,
    VOLATILITY_MULTIPLIERS,
    REGIME_MULTIPLIERS,
    RISK_STATE_MODIFIERS,
)
from modules.institutional_risk.var_engine.portfolio_var_engine import PortfolioVaREngine
from modules.institutional_risk.var_engine.expected_shortfall_engine import ExpectedShortfallEngine
from modules.institutional_risk.var_engine.risk_state_engine import RiskStateEngine
from modules.institutional_risk.var_engine.var_aggregator import VaRAggregator


# ══════════════════════════════════════════════════════════════
# TEST 1: Low vol portfolio → NORMAL
# ══════════════════════════════════════════════════════════════

def test_low_vol_portfolio_normal():
    """Low volatility + low exposure → NORMAL risk state."""
    agg = VaRAggregator()
    state = agg.compute_var_state(
        gross_exposure=0.2,
        net_exposure=0.15,
        deployable_capital=0.57,
        volatility_state="LOW",
        regime="TREND",
        position_concentration=0.2,
    )
    assert state.risk_state == RiskState.NORMAL
    assert state.recommended_action == RecommendedAction.HOLD
    assert state.var_ratio < 0.10


# ══════════════════════════════════════════════════════════════
# TEST 2: Normal regime moderate exposure → ELEVATED
# ══════════════════════════════════════════════════════════════

def test_normal_regime_moderate_exposure_elevated():
    """Normal regime with moderate exposure → ELEVATED."""
    agg = VaRAggregator()
    # Need gross_exposure high enough to push var_ratio into 0.10-0.18
    # var_95 = gross * vol_mult * regime_mult * conc_mult * 0.08
    # With NORMAL vol=1.0, MIXED regime=1.1, conc=0.3 → conc_mult=1.09
    # var_95 = gross * 1.0 * 1.1 * 1.09 * 0.08
    # var_ratio = var_95 / 0.57
    # For ELEVATED: 0.10 <= var_ratio < 0.18
    # var_95 needs to be 0.057 to 0.1026
    # gross = var_95 / (1.0 * 1.1 * 1.09 * 0.08) = var_95 / 0.09592
    # gross for 0.057 → 0.594, for 0.1026 → 1.07
    state = agg.compute_var_state(
        gross_exposure=0.7,
        net_exposure=0.5,
        deployable_capital=0.57,
        volatility_state="NORMAL",
        regime="MIXED",
        position_concentration=0.3,
    )
    assert state.risk_state == RiskState.ELEVATED
    assert state.recommended_action == RecommendedAction.REDUCE_RISK


# ══════════════════════════════════════════════════════════════
# TEST 3: High vol + high exposure → HIGH
# ══════════════════════════════════════════════════════════════

def test_high_vol_high_exposure():
    """High volatility + high exposure → HIGH risk state."""
    agg = VaRAggregator()
    state = agg.compute_var_state(
        gross_exposure=0.8,
        net_exposure=0.6,
        deployable_capital=0.57,
        volatility_state="HIGH",
        regime="MIXED",
        position_concentration=0.4,
    )
    assert state.risk_state in [RiskState.HIGH, RiskState.CRITICAL]
    assert state.recommended_action in [RecommendedAction.DELEVER, RecommendedAction.EMERGENCY_CUT]


# ══════════════════════════════════════════════════════════════
# TEST 4: Crisis / expanding vol → CRITICAL
# ══════════════════════════════════════════════════════════════

def test_crisis_expanding_vol_critical():
    """Crisis regime + expanding volatility → CRITICAL."""
    agg = VaRAggregator()
    state = agg.compute_var_state(
        gross_exposure=0.9,
        net_exposure=0.7,
        deployable_capital=0.40,
        volatility_state="EXTREME",
        regime="CRISIS",
        position_concentration=0.5,
    )
    assert state.risk_state == RiskState.CRITICAL
    assert state.recommended_action == RecommendedAction.EMERGENCY_CUT


# ══════════════════════════════════════════════════════════════
# TEST 5: VaR 95 computed correctly
# ══════════════════════════════════════════════════════════════

def test_var_95_computation():
    """Portfolio VaR 95 formula: gross × vol_mult × regime_mult × conc_mult × 0.08."""
    engine = PortfolioVaREngine()
    result = engine.compute_var(
        gross_exposure=0.5,
        volatility_state="NORMAL",
        regime="RANGE",
        position_concentration=0.3,
    )
    # vol_mult=1.0, regime_mult=1.0, conc_mult=1.0+(0.3*0.3)=1.09
    expected = 0.5 * 1.0 * 1.0 * 1.09 * 0.08
    assert abs(result["portfolio_var_95"] - expected) < 0.0001


# ══════════════════════════════════════════════════════════════
# TEST 6: VaR 99 computed correctly
# ══════════════════════════════════════════════════════════════

def test_var_99_computation():
    """Portfolio VaR 99 = VaR 95 × 1.35."""
    engine = PortfolioVaREngine()
    result = engine.compute_var(
        gross_exposure=0.5,
        volatility_state="NORMAL",
        regime="RANGE",
        position_concentration=0.3,
    )
    expected_95 = 0.5 * 1.0 * 1.0 * 1.09 * 0.08
    expected_99 = expected_95 * 1.35
    assert abs(result["portfolio_var_99"] - expected_99) < 0.0001


# ══════════════════════════════════════════════════════════════
# TEST 7: Expected Shortfall computed correctly
# ══════════════════════════════════════════════════════════════

def test_expected_shortfall_computation():
    """ES_95 = VaR_95 × 1.20, ES_99 = VaR_99 × 1.25 (base case)."""
    engine = ExpectedShortfallEngine()
    result = engine.compute_expected_shortfall(
        portfolio_var_95=0.10,
        portfolio_var_99=0.135,
        volatility_state="NORMAL",
        tail_risk_elevated=False,
    )
    expected_es_95 = 0.10 * 1.20
    expected_es_99 = 0.135 * 1.25
    assert abs(result["expected_shortfall_95"] - expected_es_95) < 0.0001
    assert abs(result["expected_shortfall_99"] - expected_es_99) < 0.0001


# ══════════════════════════════════════════════════════════════
# TEST 8: Risk state classification correct
# ══════════════════════════════════════════════════════════════

def test_risk_state_classification():
    """Risk state thresholds: <0.10 NORMAL, 0.10-0.18 ELEVATED, 0.18-0.28 HIGH, >0.28 CRITICAL."""
    engine = RiskStateEngine()

    r1 = engine.determine_risk_state(var_ratio=0.05)
    assert r1["risk_state"] == RiskState.NORMAL

    r2 = engine.determine_risk_state(var_ratio=0.12)
    assert r2["risk_state"] == RiskState.ELEVATED

    r3 = engine.determine_risk_state(var_ratio=0.22)
    assert r3["risk_state"] == RiskState.HIGH

    r4 = engine.determine_risk_state(var_ratio=0.35)
    assert r4["risk_state"] == RiskState.CRITICAL


# ══════════════════════════════════════════════════════════════
# TEST 9: Recommended action correct
# ══════════════════════════════════════════════════════════════

def test_recommended_action():
    """Recommended action maps correctly to risk state."""
    engine = RiskStateEngine()

    r1 = engine.determine_risk_state(var_ratio=0.05)
    assert r1["recommended_action"] == RecommendedAction.HOLD

    r2 = engine.determine_risk_state(var_ratio=0.12)
    assert r2["recommended_action"] == RecommendedAction.REDUCE_RISK

    r3 = engine.determine_risk_state(var_ratio=0.22)
    assert r3["recommended_action"] == RecommendedAction.DELEVER

    r4 = engine.determine_risk_state(var_ratio=0.35)
    assert r4["recommended_action"] == RecommendedAction.EMERGENCY_CUT


# ══════════════════════════════════════════════════════════════
# TEST 10: Modifiers bounded
# ══════════════════════════════════════════════════════════════

def test_modifiers_bounded():
    """Confidence and capital modifiers are bounded [0.50, 1.00]."""
    for risk_state in RiskState:
        mods = RISK_STATE_MODIFIERS[risk_state]
        assert 0.50 <= mods["confidence_modifier"] <= 1.00
        assert 0.50 <= mods["capital_modifier"] <= 1.00


# ══════════════════════════════════════════════════════════════
# TEST 11: Tail risk ratio correct
# ══════════════════════════════════════════════════════════════

def test_tail_risk_ratio():
    """tail_risk_ratio = ES_95 / VaR_95."""
    engine = ExpectedShortfallEngine()
    result = engine.compute_expected_shortfall(
        portfolio_var_95=0.10,
        portfolio_var_99=0.135,
        volatility_state="NORMAL",
        tail_risk_elevated=False,
    )
    expected_ratio = result["expected_shortfall_95"] / 0.10
    assert abs(result["tail_risk_ratio"] - expected_ratio) < 0.0001


# ══════════════════════════════════════════════════════════════
# TEST 12: Override bump works (expanding vol + high tail risk)
# ══════════════════════════════════════════════════════════════

def test_override_bump():
    """Expanding vol + high tail risk bumps risk state up one level."""
    engine = RiskStateEngine()
    # var_ratio=0.05 → base NORMAL, but with expanding vol + high tail → ELEVATED
    result = engine.determine_risk_state(
        var_ratio=0.05,
        tail_risk_ratio=1.30,
        volatility_state="EXPANDING",
    )
    assert result["risk_state"] == RiskState.ELEVATED
    assert result["override_applied"] is True


# ══════════════════════════════════════════════════════════════
# TEST 13: History recording
# ══════════════════════════════════════════════════════════════

def test_history_recording():
    """Recompute records to history."""
    agg = VaRAggregator()
    assert len(agg.get_history()) == 0
    agg.recompute()
    assert len(agg.get_history()) == 1
    agg.recompute()
    assert len(agg.get_history()) == 2


# ══════════════════════════════════════════════════════════════
# TEST 14: Aggregator summary
# ══════════════════════════════════════════════════════════════

def test_aggregator_summary():
    """Summary contains required keys."""
    agg = VaRAggregator()
    summary = agg.get_summary()
    required_keys = [
        "portfolio_var_95",
        "var_ratio",
        "risk_state",
        "recommended_action",
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
    agg = VaRAggregator()
    info = agg.get_state_info()
    assert "risk_state" in info
    assert "recommended_action" in info
    assert "is_action_required" in info
    assert "is_emergency" in info
    assert isinstance(info["is_action_required"], bool)
    assert isinstance(info["is_emergency"], bool)


# ══════════════════════════════════════════════════════════════
# TEST 16: VaRState serialization
# ══════════════════════════════════════════════════════════════

def test_var_state_serialization():
    """VaRState to_dict and to_full_dict work correctly."""
    agg = VaRAggregator()
    state = agg.compute_var_state()
    d = state.to_dict()
    assert "portfolio_var_95" in d
    assert "risk_state" in d
    assert "timestamp" in d

    full = state.to_full_dict()
    assert "inputs" in full
    assert "gross_exposure" in full["inputs"]


# ══════════════════════════════════════════════════════════════
# TEST 17: ES elevated by high volatility
# ══════════════════════════════════════════════════════════════

def test_es_elevated_by_high_vol():
    """High volatility increases ES multipliers."""
    engine = ExpectedShortfallEngine()
    normal = engine.compute_expected_shortfall(
        portfolio_var_95=0.10,
        portfolio_var_99=0.135,
        volatility_state="NORMAL",
        tail_risk_elevated=False,
    )
    high = engine.compute_expected_shortfall(
        portfolio_var_95=0.10,
        portfolio_var_99=0.135,
        volatility_state="HIGH",
        tail_risk_elevated=True,
    )
    assert high["expected_shortfall_95"] > normal["expected_shortfall_95"]
    assert high["expected_shortfall_99"] > normal["expected_shortfall_99"]


# ══════════════════════════════════════════════════════════════
# TEST 18: Tail severity classification
# ══════════════════════════════════════════════════════════════

def test_tail_severity():
    """Tail severity: NORMAL < ELEVATED < HIGH < CRITICAL."""
    engine = ExpectedShortfallEngine()
    assert engine.get_tail_severity(1.10) == "NORMAL"
    assert engine.get_tail_severity(1.25) == "ELEVATED"
    assert engine.get_tail_severity(1.35) == "HIGH"
    assert engine.get_tail_severity(1.45) == "CRITICAL"


# ══════════════════════════════════════════════════════════════
# TEST 19: VaR breakdown
# ══════════════════════════════════════════════════════════════

def test_var_breakdown():
    """VaR breakdown returns component contributions."""
    engine = PortfolioVaREngine()
    result = engine.compute_var(gross_exposure=0.5, volatility_state="NORMAL", regime="RANGE")
    breakdown = engine.get_var_breakdown(result)
    assert "exposure_contribution" in breakdown
    assert "volatility_contribution" in breakdown
    assert "regime_contribution" in breakdown
    assert "concentration_contribution" in breakdown


# ══════════════════════════════════════════════════════════════
# TEST 20: Volatility multipliers are all positive
# ══════════════════════════════════════════════════════════════

def test_volatility_multipliers_positive():
    """All volatility multipliers must be > 0."""
    for key, val in VOLATILITY_MULTIPLIERS.items():
        assert val > 0, f"Volatility multiplier {key} is not positive: {val}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
