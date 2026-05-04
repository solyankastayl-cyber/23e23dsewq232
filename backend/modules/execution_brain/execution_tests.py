"""
Execution Brain Tests

PHASE 37 — Execution Brain

Minimum 40 tests as per requirements.
"""

import pytest
from datetime import datetime, timezone

from .execution_types import (
    ExecutionPlan,
    ExecutionSummary,
    RISK_MODIFIERS,
    STOP_MULTIPLIERS,
    MIN_CONFIDENCE_THRESHOLD,
)
from .execution_engine import ExecutionBrainEngine
from .execution_router import ExecutionRouter


@pytest.fixture
def engine():
    return ExecutionBrainEngine()


@pytest.fixture
def router():
    return ExecutionRouter()


# ══════════════════════════════════════════════════════════════
# 1. Execution Plan Generation Tests
# ══════════════════════════════════════════════════════════════

def test_generate_plan_returns_valid(engine):
    """Test plan generation returns valid plan."""
    plan = engine.generate_plan(
        symbol="BTC",
        hypothesis_type="BULLISH_CONTINUATION",
        direction="LONG",
        confidence=0.70,
        reliability=0.75,
    )
    
    assert isinstance(plan, ExecutionPlan)
    assert plan.symbol == "BTC"
    assert plan.direction == "LONG"


def test_generate_plan_short(engine):
    """Test SHORT direction plan."""
    plan = engine.generate_plan(
        symbol="ETH",
        hypothesis_type="BEARISH_CONTINUATION",
        direction="SHORT",
        confidence=0.65,
        reliability=0.70,
    )
    
    assert plan.direction == "SHORT"
    assert plan.stop_loss > plan.entry_price  # Stop above entry for short


def test_generate_plan_multiple_symbols(engine):
    """Test plan generation for multiple symbols."""
    symbols = ["BTC", "ETH", "SOL"]
    for symbol in symbols:
        plan = engine.generate_plan(
            symbol=symbol,
            hypothesis_type="BULLISH_CONTINUATION",
            direction="LONG",
            confidence=0.70,
            reliability=0.75,
        )
        assert plan.symbol == symbol


# ══════════════════════════════════════════════════════════════
# 2. Position Size Calculation Tests
# ══════════════════════════════════════════════════════════════

def test_position_size_calculation(engine):
    """Test position size calculation."""
    size = engine.calculate_position_size(100000, 0.10, 1.0)
    assert size == 10000


def test_position_size_with_risk_modifier(engine):
    """Test position size with risk modifier."""
    size = engine.calculate_position_size(100000, 0.10, 0.7)
    assert size == 7000


def test_position_size_extreme_risk(engine):
    """Test position size with extreme risk."""
    size = engine.calculate_position_size(100000, 0.10, 0.0)
    assert size == 0


def test_position_size_large_capital(engine):
    """Test position size with large capital."""
    size = engine.calculate_position_size(1000000, 0.20, 1.0)
    assert size == 200000


# ══════════════════════════════════════════════════════════════
# 3. Risk Modifier Tests
# ══════════════════════════════════════════════════════════════

def test_risk_modifier_values():
    """Test risk modifier values."""
    assert RISK_MODIFIERS["LOW"] == 1.0
    assert RISK_MODIFIERS["MEDIUM"] == 0.7
    assert RISK_MODIFIERS["HIGH"] == 0.4
    assert RISK_MODIFIERS["EXTREME"] == 0.0


def test_get_risk_modifier_low(engine):
    """Test get risk modifier for LOW."""
    mod = engine.get_risk_modifier("LOW")
    assert mod == 1.0


def test_get_risk_modifier_unknown(engine):
    """Test get risk modifier for unknown."""
    mod = engine.get_risk_modifier("UNKNOWN")
    assert mod == 0.7  # Default


# ══════════════════════════════════════════════════════════════
# 4. Stop Loss Calculation Tests
# ══════════════════════════════════════════════════════════════

def test_stop_loss_long(engine):
    """Test stop loss for LONG."""
    stop = engine.calculate_stop_loss(100, "LONG", 2.0, "NORMAL")
    assert stop == 96  # 100 - 2*2


def test_stop_loss_short(engine):
    """Test stop loss for SHORT."""
    stop = engine.calculate_stop_loss(100, "SHORT", 2.0, "NORMAL")
    assert stop == 104  # 100 + 2*2


def test_stop_loss_tight(engine):
    """Test tight stop loss."""
    stop = engine.calculate_stop_loss(100, "LONG", 2.0, "TIGHT")
    assert stop == 97  # 100 - 2*1.5


def test_stop_loss_wide(engine):
    """Test wide stop loss."""
    stop = engine.calculate_stop_loss(100, "LONG", 2.0, "WIDE")
    assert stop == 94  # 100 - 2*3


def test_stop_multiplier_values():
    """Test stop multiplier values."""
    assert STOP_MULTIPLIERS["TIGHT"] == 1.5
    assert STOP_MULTIPLIERS["NORMAL"] == 2.0
    assert STOP_MULTIPLIERS["WIDE"] == 3.0


# ══════════════════════════════════════════════════════════════
# 5. Take Profit Calculation Tests
# ══════════════════════════════════════════════════════════════

def test_take_profit_long(engine):
    """Test take profit for LONG."""
    tp = engine.calculate_take_profit(100, "LONG", 5.0)
    assert tp == 105  # 100 + 5%


def test_take_profit_short(engine):
    """Test take profit for SHORT."""
    tp = engine.calculate_take_profit(100, "SHORT", 5.0)
    assert tp == 95  # 100 - 5%


def test_take_profit_large_move(engine):
    """Test take profit with large expected move."""
    tp = engine.calculate_take_profit(100, "LONG", 10.0)
    assert tp == 110


# ══════════════════════════════════════════════════════════════
# 6. Risk Level Classification Tests
# ══════════════════════════════════════════════════════════════

def test_risk_level_low(engine):
    """Test LOW risk classification."""
    level = engine.classify_risk_level(0.80, 0.75)
    assert level == "LOW"


def test_risk_level_medium(engine):
    """Test MEDIUM risk classification."""
    level = engine.classify_risk_level(0.60, 0.55)
    assert level == "MEDIUM"


def test_risk_level_high(engine):
    """Test HIGH risk classification."""
    level = engine.classify_risk_level(0.45, 0.40)
    assert level == "HIGH"


def test_risk_level_extreme(engine):
    """Test EXTREME risk classification."""
    level = engine.classify_risk_level(0.30, 0.30)
    assert level == "EXTREME"


def test_risk_level_unstable_regime(engine):
    """Test risk adjustment for unstable regime."""
    level_stable = engine.classify_risk_level(0.70, 0.70, "STABLE")
    level_unstable = engine.classify_risk_level(0.70, 0.70, "UNSTABLE")
    
    # Unstable should be higher risk
    risk_order = ["LOW", "MEDIUM", "HIGH", "EXTREME"]
    assert risk_order.index(level_unstable) >= risk_order.index(level_stable)


# ══════════════════════════════════════════════════════════════
# 7. Risk Reward Calculation Tests
# ══════════════════════════════════════════════════════════════

def test_risk_reward_long(engine):
    """Test risk/reward for LONG."""
    rr = engine.calculate_risk_reward(100, 95, 110, "LONG")
    # Risk = 5, Reward = 10, RR = 2.0
    assert rr == 2.0


def test_risk_reward_short(engine):
    """Test risk/reward for SHORT."""
    rr = engine.calculate_risk_reward(100, 105, 90, "SHORT")
    # Risk = 5, Reward = 10, RR = 2.0
    assert rr == 2.0


def test_risk_reward_zero_risk(engine):
    """Test risk/reward with zero risk."""
    rr = engine.calculate_risk_reward(100, 100, 110, "LONG")
    assert rr == 0.0


# ══════════════════════════════════════════════════════════════
# 8. Risk Gate Tests
# ══════════════════════════════════════════════════════════════

def test_risk_gate_passed(engine):
    """Test risk gate passed."""
    passed, reason = engine.apply_risk_gate("LOW", 0.70)
    assert passed is True


def test_risk_gate_extreme_blocked(engine):
    """Test risk gate blocks EXTREME."""
    passed, reason = engine.apply_risk_gate("EXTREME", 0.70)
    assert passed is False
    assert "EXTREME" in reason


def test_risk_gate_low_confidence_blocked(engine):
    """Test risk gate blocks low confidence."""
    passed, reason = engine.apply_risk_gate("LOW", 0.40)
    assert passed is False
    assert "confidence" in reason.lower()


def test_min_confidence_threshold():
    """Test minimum confidence threshold."""
    assert MIN_CONFIDENCE_THRESHOLD == 0.45


# ══════════════════════════════════════════════════════════════
# 9. Execution Router Tests
# ══════════════════════════════════════════════════════════════

def test_router_market_order(router):
    """Test MARKET order routing."""
    exec_type = router.route_execution("DEEP", 50000, "LOW_IMPACT", "BTC")
    assert exec_type == "MARKET"


def test_router_limit_order(router):
    """Test LIMIT order routing."""
    exec_type = router.route_execution("NORMAL", 100000, "MANAGEABLE", "BTC")
    assert exec_type == "LIMIT"


def test_router_twap_order(router):
    """Test TWAP order routing."""
    exec_type = router.route_execution("THIN", 100000, "HIGH_IMPACT", "BTC")
    assert exec_type == "TWAP"


def test_router_iceberg_order(router):
    """Test ICEBERG order routing."""
    exec_type = router.route_execution("FRAGILE", 100000, "UNTRADEABLE", "BTC")
    assert exec_type == "ICEBERG"


def test_router_large_order(router):
    """Test routing for large order."""
    exec_type = router.route_execution("DEEP", 1000000, "LOW_IMPACT", "BTC")
    assert exec_type == "ICEBERG"


def test_router_split_recommendation_market(router):
    """Test split recommendation for MARKET."""
    rec = router.get_order_split_recommendation("MARKET", 100000)
    assert rec["split_required"] is False
    assert rec["num_slices"] == 1


def test_router_split_recommendation_twap(router):
    """Test split recommendation for TWAP."""
    rec = router.get_order_split_recommendation("TWAP", 100000)
    assert rec["split_required"] is True
    assert rec["num_slices"] > 1


# ══════════════════════════════════════════════════════════════
# 10. Strategy Mapping Tests
# ══════════════════════════════════════════════════════════════

def test_strategy_mapping_bullish(engine):
    """Test strategy mapping for bullish."""
    strategy = engine.map_strategy("BULLISH_CONTINUATION")
    assert strategy == "MOMENTUM_TRADING"


def test_strategy_mapping_breakout(engine):
    """Test strategy mapping for breakout."""
    strategy = engine.map_strategy("BREAKOUT_FORMING")
    assert strategy == "BREAKOUT_TRADING"


def test_strategy_mapping_range(engine):
    """Test strategy mapping for range."""
    strategy = engine.map_strategy("RANGE_MEAN_REVERSION")
    assert strategy == "RANGE_TRADING"


# ══════════════════════════════════════════════════════════════
# 11. Integration Tests
# ══════════════════════════════════════════════════════════════

def test_plan_includes_impact_adjustment(engine):
    """Test plan includes impact adjustment."""
    plan = engine.generate_plan(
        symbol="BTC",
        hypothesis_type="BULLISH_CONTINUATION",
        direction="LONG",
        confidence=0.70,
        reliability=0.75,
    )
    
    # Impact adjustment fields should exist
    assert hasattr(plan, "impact_adjusted")
    assert hasattr(plan, "size_reduction_pct")


def test_plan_blocked_for_extreme_risk(engine):
    """Test plan blocked for extreme risk."""
    plan = engine.generate_plan(
        symbol="BTC",
        hypothesis_type="BULLISH_CONTINUATION",
        direction="LONG",
        confidence=0.30,  # Very low
        reliability=0.30,
    )
    
    assert plan.status == "BLOCKED"


def test_plan_approved_for_good_hypothesis(engine):
    """Test plan approved for good hypothesis."""
    plan = engine.generate_plan(
        symbol="BTC",
        hypothesis_type="BULLISH_CONTINUATION",
        direction="LONG",
        confidence=0.75,
        reliability=0.80,
    )
    
    assert plan.status == "APPROVED"


# ══════════════════════════════════════════════════════════════
# 12. Cache and History Tests
# ══════════════════════════════════════════════════════════════

def test_plan_cached(engine):
    """Test plan is cached."""
    plan = engine.generate_plan(
        symbol="BTC",
        hypothesis_type="BULLISH_CONTINUATION",
        direction="LONG",
        confidence=0.70,
        reliability=0.75,
    )
    
    cached = engine.get_active_plan("BTC")
    assert cached is not None
    assert cached.symbol == plan.symbol


def test_history_stored(engine):
    """Test history is stored."""
    engine.generate_plan("BTC", "BULLISH_CONTINUATION", "LONG", 0.70, 0.75)
    engine.generate_plan("BTC", "BEARISH_CONTINUATION", "SHORT", 0.65, 0.70)
    
    history = engine.get_history("BTC")
    assert len(history) >= 2


def test_summary_generation(engine):
    """Test summary generation."""
    engine.generate_plan("BTC", "BULLISH_CONTINUATION", "LONG", 0.70, 0.75)
    
    summary = engine.generate_summary("BTC")
    
    assert summary.symbol == "BTC"
    assert summary.total_plans >= 1


# ══════════════════════════════════════════════════════════════
# 13. Edge Cases
# ══════════════════════════════════════════════════════════════

def test_deterministic_output(engine):
    """Test deterministic output."""
    plan1 = engine.generate_plan("BTC", "BULLISH_CONTINUATION", "LONG", 0.70, 0.75)
    plan2 = engine.generate_plan("BTC", "BULLISH_CONTINUATION", "LONG", 0.70, 0.75)
    
    assert plan1.risk_level == plan2.risk_level


def test_missing_data_safe(engine):
    """Test handling of missing data."""
    plan = engine.generate_plan(
        symbol="UNKNOWN",
        hypothesis_type="BULLISH_CONTINUATION",
        direction="LONG",
        confidence=0.70,
        reliability=0.75,
    )
    
    assert plan is not None
    assert plan.symbol == "UNKNOWN"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
