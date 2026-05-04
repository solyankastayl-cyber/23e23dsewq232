"""
PHASE 19.3 — Strategy Regime Switch Tests
=========================================
Tests for Strategy Regime Switch Engine.

Test scenarios:
1. Trend regime → trend strategies primary
2. Range regime → mean reversion primary
3. Vol expansion → breakout priority
4. Squeeze regime → liquidation_capture
5. Strategy priority correct
6. Confidence modifier applied
7. Capital modifier applied
8. Inactive strategies penalized
9. API output correct
10. Regime confidence correct
"""

import pytest
from datetime import datetime, timezone

from modules.strategy_brain.regime_switch.strategy_regime_types import (
    PRIORITY_MODIFIERS,
    REGIME_CONFIDENCE_WEIGHTS,
)
from modules.strategy_brain.regime_switch.strategy_regime_map import (
    REGIME_STRATEGY_MAP,
    get_regime_config,
    get_strategies_for_regime,
    get_all_regimes,
)
from modules.strategy_brain.regime_switch.strategy_priority_engine import (
    get_priority_engine,
)
from modules.strategy_brain.regime_switch.strategy_regime_switch_engine import (
    get_regime_switch_engine,
)


class TestRegimeMap:
    """Tests for regime-strategy mapping."""
    
    def test_trend_up_strategies(self):
        """TEST 1: Trend regime should have trend strategies primary."""
        config = get_regime_config("TREND_UP")
        
        assert config is not None
        assert "trend_following" in config.primary_strategies
        assert "mean_reversion" in config.anti_strategies
    
    def test_trend_down_strategies(self):
        """Trend down should match trend up strategies."""
        config = get_regime_config("TREND_DOWN")
        
        assert config is not None
        assert "trend_following" in config.primary_strategies
    
    def test_range_strategies(self):
        """TEST 2: Range regime should have mean reversion primary."""
        config = get_regime_config("RANGE")
        
        assert config is not None
        assert "mean_reversion" in config.primary_strategies
        assert "trend_following" in config.anti_strategies
    
    def test_vol_expansion_strategies(self):
        """TEST 3: Vol expansion should have breakout priority."""
        config = get_regime_config("VOL_EXPANSION")
        
        assert config is not None
        assert "breakout" in config.primary_strategies or "volatility_expansion" in config.primary_strategies
    
    def test_squeeze_strategies(self):
        """TEST 4: Squeeze regime should have liquidation_capture primary."""
        config = get_regime_config("SQUEEZE")
        
        assert config is not None
        assert "liquidation_capture" in config.primary_strategies
    
    def test_all_regimes_defined(self):
        """All expected regimes should be defined."""
        regimes = get_all_regimes()
        
        assert "TREND_UP" in regimes
        assert "RANGE" in regimes
        assert "SQUEEZE" in regimes


class TestPriorityEngine:
    """Tests for strategy priority engine."""
    
    def test_compute_priorities_trend(self):
        """Priority computation for trend regime."""
        engine = get_priority_engine()
        
        priority = engine.compute_priorities("TREND_UP", 0.8)
        
        assert priority.primary_strategy == "trend_following"
        assert "breakout" in priority.secondary_strategies or "flow_following" in priority.secondary_strategies
    
    def test_compute_priorities_range(self):
        """Priority computation for range regime."""
        engine = get_priority_engine()
        
        priority = engine.compute_priorities("RANGE", 0.75)
        
        assert priority.primary_strategy == "mean_reversion"
    
    def test_priority_correct(self):
        """TEST 5: Strategy priority should be correct."""
        engine = get_priority_engine()
        
        priority = engine.compute_priorities("SQUEEZE", 0.85)
        
        assert priority.primary_strategy == "liquidation_capture"
        assert len(priority.secondary_strategies) > 0
        assert len(priority.inactive_strategies) > 0
    
    def test_modifiers_applied(self):
        """TEST 6 & 7: Modifiers should be applied."""
        engine = get_priority_engine()
        
        priority = engine.compute_priorities("TREND_UP", 0.8)
        
        # Primary should have boost
        primary_mods = priority.strategy_modifiers["trend_following"]
        assert primary_mods["confidence_modifier"] == PRIORITY_MODIFIERS["primary"]["confidence_modifier"]
        assert primary_mods["capital_modifier"] == PRIORITY_MODIFIERS["primary"]["capital_modifier"]
    
    def test_inactive_penalized(self):
        """TEST 8: Inactive strategies should be penalized."""
        engine = get_priority_engine()
        
        priority = engine.compute_priorities("TREND_UP", 0.8)
        
        # Mean reversion should be inactive in trend
        if "mean_reversion" in priority.inactive_strategies:
            mr_mods = priority.strategy_modifiers["mean_reversion"]
            assert mr_mods["confidence_modifier"] == PRIORITY_MODIFIERS["inactive"]["confidence_modifier"]
            assert mr_mods["capital_modifier"] == PRIORITY_MODIFIERS["inactive"]["capital_modifier"]


class TestPriorityModifiers:
    """Tests for priority modifiers."""
    
    def test_primary_boost(self):
        """Primary should have boost modifiers."""
        mods = PRIORITY_MODIFIERS["primary"]
        
        assert mods["confidence_modifier"] > 1.0
        assert mods["capital_modifier"] > 1.0
    
    def test_secondary_boost(self):
        """Secondary should have slight boost."""
        mods = PRIORITY_MODIFIERS["secondary"]
        
        assert mods["confidence_modifier"] >= 1.0
        assert mods["capital_modifier"] >= 1.0
    
    def test_inactive_penalty(self):
        """Inactive should have penalty modifiers."""
        mods = PRIORITY_MODIFIERS["inactive"]
        
        assert mods["confidence_modifier"] < 1.0
        assert mods["capital_modifier"] < 1.0


class TestRegimeSwitchEngine:
    """Tests for regime switch engine."""
    
    def test_compute_regime_priority(self):
        """Should compute regime priority for symbol."""
        engine = get_regime_switch_engine()
        
        priority = engine.compute_regime_priority("BTC")
        
        assert priority.market_regime is not None
        assert priority.primary_strategy is not None
        assert priority.regime_confidence >= 0.0
    
    def test_get_primary_strategy(self):
        """Should get primary strategy."""
        engine = get_regime_switch_engine()
        
        primary = engine.get_primary_strategy("BTC")
        
        assert primary in [
            "trend_following", "mean_reversion", "breakout",
            "liquidation_capture", "flow_following", "volatility_expansion",
            "funding_arb", "structure_reversal",
        ]
    
    def test_regime_confidence_correct(self):
        """TEST 10: Regime confidence should be correct."""
        engine = get_regime_switch_engine()
        
        priority = engine.compute_regime_priority("BTC")
        
        # Confidence should be 0-1
        assert 0.0 <= priority.regime_confidence <= 1.0
        
        # Should have breakdown scores
        assert priority.regime_score >= 0.0
        assert priority.volatility_score >= 0.0
    
    def test_compute_summary(self):
        """Should compute summary across symbols."""
        engine = get_regime_switch_engine()
        
        summary = engine.compute_summary(["BTC", "ETH"])
        
        assert summary.dominant_regime is not None
        assert len(summary.symbols_analyzed) == 2
    
    def test_api_output_correct(self):
        """TEST 9: API output should be correct."""
        engine = get_regime_switch_engine()
        
        priority = engine.compute_regime_priority("BTC")
        d = priority.to_dict()
        
        assert "market_regime" in d
        assert "primary_strategy" in d
        assert "secondary_strategies" in d
        assert "inactive_strategies" in d
        assert "strategy_modifiers" in d
        assert "breakdown" in d


class TestRegimeConfidenceWeights:
    """Tests for regime confidence weights."""
    
    def test_weights_sum_to_one(self):
        """Weights should sum to 1.0."""
        total = sum(REGIME_CONFIDENCE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001
    
    def test_weights_structure(self):
        """Should have all expected weights."""
        assert "regime" in REGIME_CONFIDENCE_WEIGHTS
        assert "volatility" in REGIME_CONFIDENCE_WEIGHTS
        assert "breadth" in REGIME_CONFIDENCE_WEIGHTS
        assert "interaction" in REGIME_CONFIDENCE_WEIGHTS
        assert "ecology" in REGIME_CONFIDENCE_WEIGHTS


class TestIntegrationScenarios:
    """Integration test scenarios."""
    
    def test_trend_regime_workflow(self):
        """Full workflow for trend regime."""
        engine = get_regime_switch_engine()
        
        # Simulate trend regime
        priority = engine.compute_regime_for_regime_name("TREND_UP", 0.85)
        
        assert priority.primary_strategy == "trend_following"
        assert priority.regime_confidence == 0.85
    
    def test_squeeze_regime_workflow(self):
        """Full workflow for squeeze regime."""
        engine = get_regime_switch_engine()
        
        priority = engine.compute_regime_for_regime_name("SQUEEZE", 0.9)
        
        assert priority.primary_strategy == "liquidation_capture"


# ══════════════════════════════════════════════════════════════
# RUN TESTS
# ══════════════════════════════════════════════════════════════

def run_tests():
    """Run all tests and print results."""
    print("\n" + "=" * 60)
    print("PHASE 19.3 — Strategy Regime Switch Tests")
    print("=" * 60 + "\n")
    
    test_classes = [
        TestRegimeMap,
        TestPriorityEngine,
        TestPriorityModifiers,
        TestRegimeSwitchEngine,
        TestRegimeConfidenceWeights,
        TestIntegrationScenarios,
    ]
    
    total_passed = 0
    total_failed = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}")
        print("-" * 40)
        
        instance = test_class()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        
        for method_name in methods:
            try:
                method = getattr(instance, method_name)
                method()
                print(f"  [PASS] {method_name}")
                total_passed += 1
            except AssertionError as e:
                print(f"  [FAIL] {method_name}: {e}")
                total_failed += 1
            except Exception as e:
                print(f"  [ERROR] {method_name}: {e}")
                total_failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {total_passed} passed, {total_failed} failed")
    print("=" * 60 + "\n")
    
    return total_failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
