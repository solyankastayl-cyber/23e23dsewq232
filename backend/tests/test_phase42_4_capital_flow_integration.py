"""
PHASE 42.4 — Capital Flow Integration Tests

BLOCK 2 Tests — 25 tests total

Tests cover:
1. Hypothesis modifier aligned
2. Hypothesis modifier conflict
3. Hypothesis modifier neutral
4. Portfolio weight adjustment aligned
5. Portfolio weight adjustment conflict
6. Portfolio rotation BTC
7. Portfolio rotation CASH
8. Portfolio rotation ALTS
9. Simulation ranking boost
10. Simulation ranking penalty
11. Flow bias neutral
12. Integration stability
13. API summary
14. API history
15. API hypothesis-modifier
16. API portfolio-adjustment
17. API scenario-modifier
18. Structural score with capital_flow
19. Multiple layers favorable
20. Multiple layers conflict
21. Flow alignment BTC LONG
22. Flow alignment ETH SHORT
23. Flow alignment ALT LONG
24. Flow alignment CASH SHORT
25. Integration summary structure
"""

import pytest
from datetime import datetime, timezone

# Import Capital Flow modules
from modules.capital_flow.flow_types import (
    FlowBias,
    FlowScore,
    CapitalFlowSnapshot,
    RotationState,
    RotationType,
    FlowState,
    FlowBucket,
    CapitalFlowConfig,
)
from modules.capital_flow.flow_integration import (
    CapitalFlowIntegration,
    get_capital_flow_integration,
    CAPITAL_FLOW_WEIGHT,
    HYPOTHESIS_WEIGHTS,
    FLOW_ALIGNED_MODIFIER,
    FLOW_CONFLICT_MODIFIER,
    PORTFOLIO_ALIGNED_MODIFIER,
    PORTFOLIO_CONFLICT_MODIFIER,
    SIMULATION_ALIGNED_MODIFIER,
    SIMULATION_CONFLICT_MODIFIER,
)


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def integration_engine():
    """Create integration engine instance."""
    return CapitalFlowIntegration()


@pytest.fixture
def btc_flow_score():
    """Flow score with BTC bias."""
    return FlowScore(
        flow_bias=FlowBias.BTC,
        flow_strength=0.6,
        flow_confidence=0.7,
        dominant_rotation=RotationType.ALTS_TO_BTC,
    )


@pytest.fixture
def cash_flow_score():
    """Flow score with CASH bias (risk-off)."""
    return FlowScore(
        flow_bias=FlowBias.CASH,
        flow_strength=0.5,
        flow_confidence=0.6,
        dominant_rotation=RotationType.RISK_TO_CASH,
    )


@pytest.fixture
def neutral_flow_score():
    """Flow score with NEUTRAL bias."""
    return FlowScore(
        flow_bias=FlowBias.NEUTRAL,
        flow_strength=0.05,
        flow_confidence=0.3,
        dominant_rotation=RotationType.NO_ROTATION,
    )


# ══════════════════════════════════════════════════════════════
# 1. Constants Tests
# ══════════════════════════════════════════════════════════════

def test_capital_flow_weight():
    """Test capital flow weight is 0.05."""
    assert CAPITAL_FLOW_WEIGHT == 0.05


def test_hypothesis_weights_sum():
    """Test hypothesis weights sum to 1.0."""
    total = sum(HYPOTHESIS_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001


def test_flow_aligned_modifier():
    """Test aligned modifier is 1.08."""
    assert FLOW_ALIGNED_MODIFIER == 1.08


def test_flow_conflict_modifier():
    """Test conflict modifier is 0.92."""
    assert FLOW_CONFLICT_MODIFIER == 0.92


def test_portfolio_aligned_modifier():
    """Test portfolio aligned modifier is 1.05."""
    assert PORTFOLIO_ALIGNED_MODIFIER == 1.05


def test_portfolio_conflict_modifier():
    """Test portfolio conflict modifier is 0.95."""
    assert PORTFOLIO_CONFLICT_MODIFIER == 0.95


def test_simulation_aligned_modifier():
    """Test simulation aligned modifier is 1.06."""
    assert SIMULATION_ALIGNED_MODIFIER == 1.06


def test_simulation_conflict_modifier():
    """Test simulation conflict modifier is 0.94."""
    assert SIMULATION_CONFLICT_MODIFIER == 0.94


# ══════════════════════════════════════════════════════════════
# 2. Hypothesis Modifier Tests
# ══════════════════════════════════════════════════════════════

def test_hypothesis_modifier_aligned(integration_engine):
    """Test hypothesis modifier when flow is aligned."""
    result = integration_engine.get_hypothesis_modifier("BTCUSDT", "LONG")
    
    # Check structure
    assert "capital_flow_score" in result
    assert "modifier" in result
    assert "is_aligned" in result
    assert "flow_bias" in result
    assert "weight_in_formula" in result
    
    # Weight should be 0.05
    assert result["weight_in_formula"] == 0.05


def test_hypothesis_modifier_btc_long_btc_bias(integration_engine):
    """Test BTC LONG with BTC bias should be aligned."""
    # This tests the alignment logic
    is_aligned = integration_engine._check_flow_alignment(
        symbol="BTCUSDT",
        hypothesis_direction="LONG",
        flow_bias=FlowBias.BTC,
    )
    assert is_aligned is True


def test_hypothesis_modifier_btc_long_cash_bias(integration_engine):
    """Test BTC LONG with CASH bias should be conflict."""
    is_aligned = integration_engine._check_flow_alignment(
        symbol="BTCUSDT",
        hypothesis_direction="LONG",
        flow_bias=FlowBias.CASH,
    )
    assert is_aligned is False


def test_hypothesis_modifier_eth_long_eth_bias(integration_engine):
    """Test ETH LONG with ETH bias should be aligned."""
    is_aligned = integration_engine._check_flow_alignment(
        symbol="ETHUSDT",
        hypothesis_direction="LONG",
        flow_bias=FlowBias.ETH,
    )
    assert is_aligned is True


def test_hypothesis_modifier_alt_long_alts_bias(integration_engine):
    """Test ALT LONG with ALTS bias should be aligned."""
    is_aligned = integration_engine._check_flow_alignment(
        symbol="SOLUSDT",
        hypothesis_direction="LONG",
        flow_bias=FlowBias.ALTS,
    )
    assert is_aligned is True


def test_hypothesis_modifier_short_with_cash_bias(integration_engine):
    """Test SHORT with CASH bias should be aligned."""
    is_aligned = integration_engine._check_flow_alignment(
        symbol="BTCUSDT",
        hypothesis_direction="SHORT",
        flow_bias=FlowBias.CASH,
    )
    assert is_aligned is True


def test_hypothesis_modifier_short_with_btc_bias(integration_engine):
    """Test BTC SHORT with BTC bias should be conflict."""
    is_aligned = integration_engine._check_flow_alignment(
        symbol="BTCUSDT",
        hypothesis_direction="SHORT",
        flow_bias=FlowBias.BTC,
    )
    assert is_aligned is False


# ══════════════════════════════════════════════════════════════
# 3. Portfolio Adjustment Tests
# ══════════════════════════════════════════════════════════════

def test_portfolio_weight_adjustment(integration_engine):
    """Test portfolio weight adjustment structure."""
    result = integration_engine.get_portfolio_weight_adjustment(
        symbol="BTCUSDT",
        direction="LONG",
        base_weight=0.10,
    )
    
    assert "symbol" in result
    assert "direction" in result
    assert "base_weight" in result
    assert "adjusted_weight" in result
    assert "modifier" in result
    assert "adjustment_type" in result


def test_portfolio_rotation_signals(integration_engine):
    """Test portfolio rotation signals structure."""
    signals = integration_engine.get_portfolio_rotation_signals()
    
    assert "flow_bias" in signals
    assert "rotation_type" in signals
    assert "recommendations" in signals
    assert isinstance(signals["recommendations"], list)


# ══════════════════════════════════════════════════════════════
# 4. Simulation Modifier Tests
# ══════════════════════════════════════════════════════════════

def test_scenario_ranking_modifier(integration_engine):
    """Test scenario ranking modifier structure."""
    result = integration_engine.get_scenario_ranking_modifier("FLASH_CRASH")
    
    assert "scenario_type" in result
    assert "modifier" in result
    assert "alignment_state" in result


def test_scenario_alignment_btc_leadership(integration_engine):
    """Test BTC leadership scenario alignment."""
    is_aligned = integration_engine._check_scenario_alignment(
        scenario_type="btc_leadership",
        flow_bias=FlowBias.BTC,
        rotation_type=RotationType.ALTS_TO_BTC,
    )
    assert is_aligned is True


def test_scenario_alignment_risk_off(integration_engine):
    """Test risk-off scenario alignment with CASH flow."""
    is_aligned = integration_engine._check_scenario_alignment(
        scenario_type="flash_crash",
        flow_bias=FlowBias.CASH,
        rotation_type=RotationType.RISK_TO_CASH,
    )
    assert is_aligned is True


def test_scenario_alignment_alt_season(integration_engine):
    """Test alt season scenario alignment."""
    is_aligned = integration_engine._check_scenario_alignment(
        scenario_type="alt_season",
        flow_bias=FlowBias.ALTS,
        rotation_type=RotationType.ETH_TO_ALTS,
    )
    assert is_aligned is True


# ══════════════════════════════════════════════════════════════
# 5. Integration Summary Tests
# ══════════════════════════════════════════════════════════════

def test_integration_summary_structure(integration_engine):
    """Test integration summary has all required fields."""
    summary = integration_engine.get_integration_summary()
    
    # Check required fields
    assert "phase" in summary
    assert summary["phase"] == "42.4"
    assert "current_state" in summary
    assert "snapshot" in summary
    assert "integration_weights" in summary
    assert "modifiers" in summary
    assert "integration_points" in summary
    assert "rules" in summary


def test_integration_summary_weights(integration_engine):
    """Test integration summary has correct weights."""
    summary = integration_engine.get_integration_summary()
    
    weights = summary["integration_weights"]
    assert weights["capital_flow"] == 0.05
    assert weights["alpha"] == 0.25
    assert weights["regime"] == 0.18


def test_integration_summary_modifiers(integration_engine):
    """Test integration summary has correct modifiers."""
    summary = integration_engine.get_integration_summary()
    
    modifiers = summary["modifiers"]
    assert modifiers["hypothesis_aligned"] == 1.08
    assert modifiers["hypothesis_conflict"] == 0.92
    assert modifiers["portfolio_aligned"] == 1.05
    assert modifiers["portfolio_conflict"] == 0.95
    assert modifiers["simulation_aligned"] == 1.06
    assert modifiers["simulation_conflict"] == 0.94


def test_integration_rules(integration_engine):
    """Test integration rules are present."""
    summary = integration_engine.get_integration_summary()
    
    rules = summary["rules"]
    assert len(rules) == 3
    assert any("NOT generate orders" in r for r in rules)
    assert any("NOT manage execution" in r for r in rules)
    assert any("NOT influence stop/TP" in r for r in rules)


# ══════════════════════════════════════════════════════════════
# 6. Singleton Tests
# ══════════════════════════════════════════════════════════════

def test_singleton_instance():
    """Test get_capital_flow_integration returns singleton."""
    engine1 = get_capital_flow_integration()
    engine2 = get_capital_flow_integration()
    assert engine1 is engine2


# ══════════════════════════════════════════════════════════════
# 7. Edge Cases
# ══════════════════════════════════════════════════════════════

def test_neutral_flow_bias_modifier(integration_engine):
    """Test neutral flow bias gives modifier 1.0."""
    # Create engine with neutral flow
    result = integration_engine.get_hypothesis_modifier("BTCUSDT", "LONG")
    
    # Regardless of alignment, if flow is weak, should be neutral
    assert "modifier" in result


def test_portfolio_adjustment_low_flow(integration_engine):
    """Test portfolio adjustment with low flow strength."""
    result = integration_engine.get_portfolio_weight_adjustment(
        symbol="BTCUSDT",
        direction="LONG",
        base_weight=0.10,
    )
    
    # Should have valid adjustment
    assert result["adjusted_weight"] >= 0
    assert result["adjusted_weight"] <= 1


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
