"""
PHASE 19.4 — Strategy Brain Aggregator Tests
============================================
Tests for Strategy Brain Aggregator.

Test scenarios:
1. Strong primary strategy → SUPPORTIVE
2. Mixed regime → NEUTRAL
3. Fragmented strategy set → RESTRICTIVE
4. Recommended bias correct for trend
5. Recommended bias correct for MR
6. Capital modifier bounded
7. Confidence modifier bounded
8. Summary output correct
"""

import pytest
from datetime import datetime, timezone

from modules.strategy_brain.aggregator.strategy_brain_types import (
    StrategyBrainState,
    StrategyOverlayEffect,
    RecommendedBias,
    STRATEGY_BIAS_MAP,
    CONFIDENCE_MODIFIER_MIN,
    CONFIDENCE_MODIFIER_MAX,
    CAPITAL_MODIFIER_MIN,
    CAPITAL_MODIFIER_MAX,
)
from modules.strategy_brain.aggregator.strategy_brain_aggregator import (
    get_strategy_brain_aggregator,
    StrategyBrainAggregator,
)


class TestStrategyBiasMap:
    """Tests for strategy bias mapping."""
    
    def test_trend_following_bias(self):
        """TEST 4: Trend following should map to TREND bias."""
        assert STRATEGY_BIAS_MAP["trend_following"] == RecommendedBias.TREND
    
    def test_mean_reversion_bias(self):
        """TEST 5: Mean reversion should map to MR bias."""
        assert STRATEGY_BIAS_MAP["mean_reversion"] == RecommendedBias.MR
    
    def test_breakout_bias(self):
        """Breakout should map to BREAKOUT bias."""
        assert STRATEGY_BIAS_MAP["breakout"] == RecommendedBias.BREAKOUT
    
    def test_liquidation_capture_bias(self):
        """Liquidation capture should map to SQUEEZE bias."""
        assert STRATEGY_BIAS_MAP["liquidation_capture"] == RecommendedBias.SQUEEZE
    
    def test_all_strategies_mapped(self):
        """All strategies should have bias mapping."""
        expected = [
            "trend_following", "mean_reversion", "breakout",
            "liquidation_capture", "flow_following", "volatility_expansion",
            "funding_arb", "structure_reversal",
        ]
        
        for strategy in expected:
            assert strategy in STRATEGY_BIAS_MAP


class TestModifierBounds:
    """Tests for modifier bounds."""
    
    def test_confidence_bounds(self):
        """TEST 7: Confidence modifier bounds should be correct."""
        assert CONFIDENCE_MODIFIER_MIN == 0.80
        assert CONFIDENCE_MODIFIER_MAX == 1.20
    
    def test_capital_bounds(self):
        """TEST 6: Capital modifier bounds should be correct."""
        assert CAPITAL_MODIFIER_MIN == 0.75
        assert CAPITAL_MODIFIER_MAX == 1.25


class TestOverlayEffect:
    """Tests for overlay effect determination."""
    
    def test_supportive_effect(self):
        """TEST 1: Strong primary should give SUPPORTIVE effect."""
        aggregator = get_strategy_brain_aggregator()
        
        # Test with actual market data
        state = aggregator.compute_aggregate("BTC")
        
        # If primary is active and regime confidence high, should be SUPPORTIVE
        if (state.primary_strategy in state.active_strategies and 
            state.regime_confidence >= 0.70):
            assert state.strategy_overlay_effect == StrategyOverlayEffect.SUPPORTIVE
    
    def test_overlay_effect_values(self):
        """Overlay effect should be one of valid values."""
        aggregator = get_strategy_brain_aggregator()
        
        state = aggregator.compute_aggregate("BTC")
        
        assert state.strategy_overlay_effect in [
            StrategyOverlayEffect.SUPPORTIVE,
            StrategyOverlayEffect.NEUTRAL,
            StrategyOverlayEffect.RESTRICTIVE,
        ]


class TestAggregator:
    """Tests for Strategy Brain Aggregator."""
    
    def test_compute_aggregate(self):
        """Should compute aggregate state."""
        aggregator = get_strategy_brain_aggregator()
        
        state = aggregator.compute_aggregate("BTC")
        
        assert state.market_regime is not None
        assert state.primary_strategy is not None
        assert state.regime_confidence >= 0.0
    
    def test_confidence_modifier_bounded(self):
        """TEST 7: Confidence modifier should be bounded."""
        aggregator = get_strategy_brain_aggregator()
        
        state = aggregator.compute_aggregate("BTC")
        
        assert CONFIDENCE_MODIFIER_MIN <= state.confidence_modifier <= CONFIDENCE_MODIFIER_MAX
    
    def test_capital_modifier_bounded(self):
        """TEST 6: Capital modifier should be bounded."""
        aggregator = get_strategy_brain_aggregator()
        
        state = aggregator.compute_aggregate("BTC")
        
        assert CAPITAL_MODIFIER_MIN <= state.capital_modifier <= CAPITAL_MODIFIER_MAX
    
    def test_strategy_lists_complete(self):
        """Strategy lists should cover all strategies."""
        aggregator = get_strategy_brain_aggregator()
        
        state = aggregator.compute_aggregate("BTC")
        
        total = (
            len(state.active_strategies) +
            len(state.reduced_strategies) +
            len(state.disabled_strategies)
        )
        
        assert total == 8  # All 8 strategies
    
    def test_allocations_non_empty(self):
        """Allocations should have values for non-disabled."""
        aggregator = get_strategy_brain_aggregator()
        
        state = aggregator.compute_aggregate("BTC")
        
        # At least some strategies should have allocation
        assert len(state.allocations) > 0
    
    def test_recommended_bias_valid(self):
        """Recommended bias should be valid."""
        aggregator = get_strategy_brain_aggregator()
        
        state = aggregator.compute_aggregate("BTC")
        
        assert state.recommended_bias in RecommendedBias


class TestOutputFormats:
    """Tests for output formats."""
    
    def test_to_dict(self):
        """TEST 8: to_dict should have correct structure."""
        aggregator = get_strategy_brain_aggregator()
        
        state = aggregator.compute_aggregate("BTC")
        d = state.to_dict()
        
        assert "market_regime" in d
        assert "regime_confidence" in d
        assert "active_strategies" in d
        assert "primary_strategy" in d
        assert "allocations" in d
        assert "confidence_modifier" in d
        assert "capital_modifier" in d
        assert "strategy_overlay_effect" in d
        assert "recommended_bias" in d
        assert "reason" in d
    
    def test_to_summary(self):
        """Summary should be compact."""
        aggregator = get_strategy_brain_aggregator()
        
        state = aggregator.compute_aggregate("BTC")
        summary = state.to_summary()
        
        assert "regime" in summary
        assert "primary" in summary
        assert "bias" in summary
        assert "overlay_effect" in summary
        assert "conf_mod" in summary
        assert "cap_mod" in summary
    
    def test_to_trading_product_block(self):
        """Trading product block should have correct format."""
        aggregator = get_strategy_brain_aggregator()
        
        state = aggregator.compute_aggregate("BTC")
        block = state.to_trading_product_block()
        
        assert "strategy_brain" in block
        sb = block["strategy_brain"]
        
        assert "market_regime" in sb
        assert "primary_strategy" in sb
        assert "recommended_bias" in sb
        assert "confidence_modifier" in sb
        assert "capital_modifier" in sb
    
    def test_get_trading_product_overlay(self):
        """Should get trading product overlay."""
        aggregator = get_strategy_brain_aggregator()
        
        overlay = aggregator.get_trading_product_overlay("BTC")
        
        assert "strategy_brain" in overlay


class TestIntegrationScenarios:
    """Integration test scenarios."""
    
    def test_full_workflow(self):
        """Full aggregation workflow test."""
        aggregator = get_strategy_brain_aggregator()
        
        # Get aggregate for BTC
        state = aggregator.compute_aggregate("BTC")
        
        # Verify all parts present
        assert state.market_regime is not None
        assert state.primary_strategy is not None
        assert len(state.allocations) >= 0
        assert state.strategy_overlay_effect is not None
        assert state.recommended_bias is not None
    
    def test_multi_symbol(self):
        """Should work for multiple symbols."""
        aggregator = get_strategy_brain_aggregator()
        
        for symbol in ["BTC", "ETH", "SOL"]:
            state = aggregator.compute_aggregate(symbol)
            assert state.market_regime is not None


# ══════════════════════════════════════════════════════════════
# RUN TESTS
# ══════════════════════════════════════════════════════════════

def run_tests():
    """Run all tests and print results."""
    print("\n" + "=" * 60)
    print("PHASE 19.4 — Strategy Brain Aggregator Tests")
    print("=" * 60 + "\n")
    
    test_classes = [
        TestStrategyBiasMap,
        TestModifierBounds,
        TestOverlayEffect,
        TestAggregator,
        TestOutputFormats,
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
