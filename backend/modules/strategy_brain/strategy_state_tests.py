"""
PHASE 19.1 — Strategy Brain Tests
=================================
Tests for Strategy Registry & State Engine.

Test scenarios:
1. Trend regime activates trend strategy
2. Range regime activates mean reversion
3. Weak breadth reduces trend strategy
4. Expanding vol supports breakout
5. Squeeze regime activates liquidation_capture
6. Unsuitable regime disables strategy
7. Modifiers correct
8. Summary output correct
"""

import pytest
from datetime import datetime, timezone

from modules.strategy_brain.strategy_state_engine import get_strategy_state_engine
from modules.strategy_brain.strategy_registry import (
    STRATEGY_REGISTRY,
    get_strategy_config,
    get_all_strategies,
    get_strategies_for_regime,
    get_registry_summary,
)
from modules.strategy_brain.strategy_types import (
    StrategyType,
    StrategyStateEnum,
    STATE_THRESHOLDS,
    STATE_MODIFIERS,
)


class TestStrategyRegistry:
    """Tests for strategy registry."""
    
    def test_registry_has_strategies(self):
        """Registry should have all expected strategies."""
        strategies = get_all_strategies()
        
        assert len(strategies) >= 6
        assert "trend_following" in strategies
        assert "mean_reversion" in strategies
        assert "breakout" in strategies
        assert "liquidation_capture" in strategies
    
    def test_get_strategy_config(self):
        """Should get strategy config by name."""
        config = get_strategy_config("trend_following")
        
        assert config is not None
        assert config.strategy_type == StrategyType.TREND_FOLLOWING
        assert "TREND_UP" in config.preferred_regimes
        assert "RANGE" in config.anti_regimes
    
    def test_registry_summary(self):
        """Should get registry summary."""
        summary = get_registry_summary()
        
        assert "total_strategies" in summary
        assert summary["total_strategies"] >= 6
        assert "by_risk_profile" in summary
    
    def test_strategies_for_regime(self):
        """Should get strategies suitable for regime."""
        trend_strategies = get_strategies_for_regime("TREND_UP")
        range_strategies = get_strategies_for_regime("RANGE")
        
        assert "trend_following" in trend_strategies
        assert "mean_reversion" in range_strategies


class TestSuitabilityCalculation:
    """Tests for suitability score calculation."""
    
    def test_regime_score_preferred(self):
        """TEST 1: Trend regime should give high score to trend strategy."""
        engine = get_strategy_state_engine()
        config = get_strategy_config("trend_following")
        
        context = {"combined_state": "TREND_UP", "trend_state": "TREND_UP"}
        score = engine._compute_regime_score(config, context)
        
        assert score >= 0.85
    
    def test_regime_score_anti(self):
        """TEST 6: Anti-regime should give low score."""
        engine = get_strategy_state_engine()
        config = get_strategy_config("trend_following")
        
        context = {"combined_state": "RANGE", "trend_state": "RANGE"}
        score = engine._compute_regime_score(config, context)
        
        assert score <= 0.3
    
    def test_mean_reversion_in_range(self):
        """TEST 2: Range regime should give high score to mean reversion."""
        engine = get_strategy_state_engine()
        config = get_strategy_config("mean_reversion")
        
        context = {"combined_state": "RANGE", "trend_state": "RANGE"}
        score = engine._compute_regime_score(config, context)
        
        assert score >= 0.85
    
    def test_volatility_score(self):
        """TEST 4: Expanding vol should support breakout."""
        engine = get_strategy_state_engine()
        config = get_strategy_config("breakout")
        
        context = {"volatility_state": "EXPANDING"}
        score = engine._compute_volatility_score(config, context)
        
        assert score >= 0.85
    
    def test_breadth_score_weak(self):
        """TEST 3: Weak breadth should reduce trend strategy."""
        engine = get_strategy_state_engine()
        config = get_strategy_config("trend_following")
        
        # Trend following requires MIXED breadth minimum
        context = {"breadth_state": "WEAK"}
        score = engine._compute_breadth_score(config, context)
        
        assert score <= 0.30


class TestStrategyState:
    """Tests for strategy state determination."""
    
    def test_active_threshold(self):
        """TEST 7: High suitability should be ACTIVE."""
        engine = get_strategy_state_engine()
        
        state = engine._determine_state(0.75)
        assert state == StrategyStateEnum.ACTIVE
    
    def test_reduced_threshold(self):
        """Mid suitability should be REDUCED."""
        engine = get_strategy_state_engine()
        
        state = engine._determine_state(0.55)
        assert state == StrategyStateEnum.REDUCED
    
    def test_disabled_threshold(self):
        """TEST 6: Low suitability should be DISABLED."""
        engine = get_strategy_state_engine()
        
        state = engine._determine_state(0.30)
        assert state == StrategyStateEnum.DISABLED
    
    def test_modifiers_active(self):
        """TEST 7: ACTIVE should have boost modifiers."""
        modifiers = STATE_MODIFIERS[StrategyStateEnum.ACTIVE]
        
        assert modifiers["confidence_modifier"] >= 1.0
        assert modifiers["capital_modifier"] >= 1.0
    
    def test_modifiers_disabled(self):
        """DISABLED should have zero capital modifier."""
        modifiers = STATE_MODIFIERS[StrategyStateEnum.DISABLED]
        
        assert modifiers["capital_modifier"] == 0.0


class TestStrategyStateEngine:
    """Tests for full strategy state computation."""
    
    def test_compute_strategy_state(self):
        """Should compute state for strategy."""
        engine = get_strategy_state_engine()
        
        state = engine.compute_strategy_state("trend_following", "BTC")
        
        assert state.strategy_name == "trend_following"
        assert state.strategy_type == StrategyType.TREND_FOLLOWING
        assert state.strategy_state in StrategyStateEnum
        assert 0.0 <= state.suitability_score <= 1.0
    
    def test_compute_all_strategies(self):
        """Should compute state for all strategies."""
        engine = get_strategy_state_engine()
        
        states = engine.compute_all_strategies("BTC")
        
        assert len(states) == len(STRATEGY_REGISTRY)
        
        for state in states:
            assert state.strategy_name in STRATEGY_REGISTRY
    
    def test_compute_summary(self):
        """TEST 8: Summary should have correct structure."""
        engine = get_strategy_state_engine()
        
        summary = engine.compute_summary("BTC")
        
        assert summary.strategy_count == len(STRATEGY_REGISTRY)
        assert len(summary.active_strategies) + len(summary.reduced_strategies) + len(summary.disabled_strategies) == summary.strategy_count
        assert summary.active_count == len(summary.active_strategies)
        assert summary.reduced_count == len(summary.reduced_strategies)
        assert summary.disabled_count == len(summary.disabled_strategies)
    
    def test_summary_to_dict(self):
        """Summary should convert to dict correctly."""
        engine = get_strategy_state_engine()
        
        summary = engine.compute_summary("BTC")
        d = summary.to_dict()
        
        assert "market_regime" in d
        assert "active_strategies" in d
        assert "reduced_strategies" in d
        assert "disabled_strategies" in d
        assert "counts" in d


class TestLiquidationCapture:
    """Test liquidation capture strategy logic."""
    
    def test_squeeze_regime_activates(self):
        """TEST 5: Squeeze regime should activate liquidation_capture."""
        engine = get_strategy_state_engine()
        config = get_strategy_config("liquidation_capture")
        
        context = {
            "combined_state": "SQUEEZE_SETUP_LONG",
            "volatility_state": "HIGH",
        }
        
        regime_score = engine._compute_regime_score(config, context)
        vol_score = engine._compute_volatility_score(config, context)
        
        assert regime_score >= 0.85
        assert vol_score >= 0.85


class TestIntegrationWithMarketData:
    """Integration tests with actual market data."""
    
    def test_full_integration(self):
        """Full integration test with market data."""
        engine = get_strategy_state_engine()
        
        # Compute for BTC
        summary = engine.compute_summary("BTC")
        
        # Should have some result
        assert summary.strategy_count > 0
        assert summary.market_regime is not None
        
        # At least one strategy should be active or reduced
        assert summary.active_count + summary.reduced_count > 0
    
    def test_state_output_format(self):
        """State output should have correct format."""
        engine = get_strategy_state_engine()
        
        state = engine.compute_strategy_state("trend_following", "BTC")
        d = state.to_dict()
        
        assert "strategy_name" in d
        assert "strategy_state" in d
        assert "suitability_score" in d
        assert "confidence_modifier" in d
        assert "capital_modifier" in d
        assert "breakdown" in d


# ══════════════════════════════════════════════════════════════
# RUN TESTS
# ══════════════════════════════════════════════════════════════

def run_tests():
    """Run all tests and print results."""
    print("\n" + "=" * 60)
    print("PHASE 19.1 — Strategy Brain Tests")
    print("=" * 60 + "\n")
    
    test_classes = [
        TestStrategyRegistry,
        TestSuitabilityCalculation,
        TestStrategyState,
        TestStrategyStateEngine,
        TestLiquidationCapture,
        TestIntegrationWithMarketData,
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
