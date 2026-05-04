"""
PHASE 15.3 — Alpha Correlation Engine Tests
============================================
Test signal correlation detection.

Test Cases:
1. Independent signals → UNIQUE (LOW correlation)
2. Partially related signals → PARTIAL
3. Almost identical signals → HIGHLY_CORRELATED
4. Uniqueness calculation correct
5. Modifiers applied correctly
6. Engine handles multiple signals
7. Correlation NEVER blocks signal
8. Real data integration
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_ecology.alpha_ecology_types import CorrelationState
from modules.alpha_ecology.alpha_correlation_engine import (
    AlphaCorrelationEngine,
    AlphaCorrelationResult,
    get_alpha_correlation_engine,
    CORRELATION_THRESHOLDS,
    CORRELATION_MODIFIERS,
)


class MockAlphaCorrelationEngine(AlphaCorrelationEngine):
    """Engine with mock correlations for testing."""
    
    def __init__(self):
        self._mock_correlations: dict = {}
    
    def set_mock_correlations(self, correlations: dict):
        """
        Set mock correlations.
        
        Format: {"signal_a:signal_b": correlation_value}
        """
        self._mock_correlations = correlations
    
    def _compute_correlation(
        self,
        symbol: str,
        signal_a: str,
        signal_b: str,
    ) -> float:
        """Return mock correlation."""
        key = f"{signal_a}:{signal_b}"
        reverse_key = f"{signal_b}:{signal_a}"
        
        if key in self._mock_correlations:
            return self._mock_correlations[key]
        if reverse_key in self._mock_correlations:
            return self._mock_correlations[reverse_key]
        
        return 0.0


def test_1_independent_signals():
    """Test 1: Independent signals → UNIQUE (LOW correlation)"""
    engine = MockAlphaCorrelationEngine()
    
    # All correlations low
    engine.set_mock_correlations({
        "trend_breakout:momentum_continuation": 0.15,
        "trend_breakout:mean_reversion": 0.10,
        "trend_breakout:volatility_breakout": 0.18,
        "trend_breakout:support_bounce": 0.12,
        "trend_breakout:resistance_rejection": 0.08,
        "trend_breakout:trend_pullback": 0.22,
        "trend_breakout:channel_breakout": 0.25,
        "trend_breakout:double_bottom": 0.14,
        "trend_breakout:double_top": 0.11,
    })
    
    result = engine.analyze_signal("BTC", "trend_breakout")
    
    # Assertions
    assert result.correlation_state == CorrelationState.UNIQUE, \
        f"Expected UNIQUE, got {result.correlation_state}"
    
    assert result.max_correlation < 0.30, \
        f"Expected max_correlation < 0.30, got {result.max_correlation}"
    
    assert result.uniqueness_score > 0.70, \
        f"Expected uniqueness > 0.70, got {result.uniqueness_score}"
    
    assert result.confidence_modifier == 1.0, \
        f"Expected conf_mod = 1.0, got {result.confidence_modifier}"
    
    print("TEST 1 PASSED: Independent signals detected as UNIQUE")
    print(f"  max_correlation={result.max_correlation:.3f}")
    print(f"  uniqueness_score={result.uniqueness_score:.3f}")
    print(f"  state={result.correlation_state.value}")
    
    return True


def test_2_partially_related_signals():
    """Test 2: Partially related signals → PARTIAL"""
    engine = MockAlphaCorrelationEngine()
    
    # Medium correlations
    engine.set_mock_correlations({
        "trend_breakout:momentum_continuation": 0.42,
        "trend_breakout:mean_reversion": 0.15,
        "trend_breakout:volatility_breakout": 0.38,
        "trend_breakout:support_bounce": 0.22,
        "trend_breakout:resistance_rejection": 0.18,
        "trend_breakout:trend_pullback": 0.45,
        "trend_breakout:channel_breakout": 0.48,
        "trend_breakout:double_bottom": 0.25,
        "trend_breakout:double_top": 0.20,
    })
    
    result = engine.analyze_signal("ETH", "trend_breakout")
    
    # Assertions
    assert result.correlation_state == CorrelationState.PARTIAL, \
        f"Expected PARTIAL, got {result.correlation_state}"
    
    assert 0.30 <= result.max_correlation < 0.60, \
        f"Expected max_correlation in 0.30-0.60, got {result.max_correlation}"
    
    assert result.confidence_modifier == 0.90, \
        f"Expected conf_mod = 0.90, got {result.confidence_modifier}"
    
    print("TEST 2 PASSED: Partially related signals detected")
    print(f"  max_correlation={result.max_correlation:.3f}")
    print(f"  max_correlated_signal={result.max_correlated_signal}")
    print(f"  state={result.correlation_state.value}")
    
    return True


def test_3_highly_correlated_signals():
    """Test 3: Almost identical signals → HIGHLY_CORRELATED"""
    engine = MockAlphaCorrelationEngine()
    
    # High correlations
    engine.set_mock_correlations({
        "trend_breakout:momentum_continuation": 0.68,
        "trend_breakout:mean_reversion": 0.25,
        "trend_breakout:volatility_breakout": 0.55,
        "trend_breakout:support_bounce": 0.30,
        "trend_breakout:resistance_rejection": 0.28,
        "trend_breakout:trend_pullback": 0.72,  # High!
        "trend_breakout:channel_breakout": 0.78,  # Very high!
        "trend_breakout:double_bottom": 0.35,
        "trend_breakout:double_top": 0.32,
    })
    
    result = engine.analyze_signal("SOL", "trend_breakout")
    
    # Assertions
    assert result.correlation_state == CorrelationState.HIGHLY_CORRELATED, \
        f"Expected HIGHLY_CORRELATED, got {result.correlation_state}"
    
    assert result.max_correlation >= 0.60, \
        f"Expected max_correlation >= 0.60, got {result.max_correlation}"
    
    assert result.confidence_modifier <= 0.75, \
        f"Expected conf_mod <= 0.75, got {result.confidence_modifier}"
    
    print("TEST 3 PASSED: Highly correlated signals detected")
    print(f"  max_correlation={result.max_correlation:.3f}")
    print(f"  max_correlated_signal={result.max_correlated_signal}")
    print(f"  conf_mod={result.confidence_modifier:.3f}")
    
    return True


def test_4_uniqueness_calculation():
    """Test 4: Uniqueness calculation correct"""
    engine = MockAlphaCorrelationEngine()
    
    # Set specific correlation
    engine.set_mock_correlations({
        "trend_breakout:momentum_continuation": 0.45,
        "trend_breakout:mean_reversion": 0.20,
        "trend_breakout:volatility_breakout": 0.35,
        "trend_breakout:support_bounce": 0.25,
        "trend_breakout:resistance_rejection": 0.22,
        "trend_breakout:trend_pullback": 0.40,
        "trend_breakout:channel_breakout": 0.38,
        "trend_breakout:double_bottom": 0.28,
        "trend_breakout:double_top": 0.30,
    })
    
    result = engine.analyze_signal("BTC", "trend_breakout")
    
    # Uniqueness = 1 - max_correlation
    expected_uniqueness = 1.0 - result.max_correlation
    
    assert abs(result.uniqueness_score - expected_uniqueness) < 0.001, \
        f"Expected uniqueness {expected_uniqueness:.4f}, got {result.uniqueness_score:.4f}"
    
    print("TEST 4 PASSED: Uniqueness calculation correct")
    print(f"  max_correlation={result.max_correlation:.3f}")
    print(f"  uniqueness_score={result.uniqueness_score:.3f} = 1 - {result.max_correlation:.3f}")
    
    return True


def test_5_modifiers_correct():
    """Test 5: Modifiers applied correctly per state"""
    engine = MockAlphaCorrelationEngine()
    
    # Test UNIQUE state
    engine.set_mock_correlations({
        f"trend_breakout:{s}": 0.15 for s in [
            "momentum_continuation", "mean_reversion", "volatility_breakout",
            "support_bounce", "resistance_rejection", "trend_pullback",
            "channel_breakout", "double_bottom", "double_top"
        ]
    })
    result = engine.analyze_signal("BTC", "trend_breakout")
    assert result.confidence_modifier == 1.0, f"UNIQUE: Expected 1.0, got {result.confidence_modifier}"
    
    # Test PARTIAL state
    engine.set_mock_correlations({
        f"trend_breakout:{s}": 0.45 for s in [
            "momentum_continuation", "mean_reversion", "volatility_breakout",
            "support_bounce", "resistance_rejection", "trend_pullback",
            "channel_breakout", "double_bottom", "double_top"
        ]
    })
    result = engine.analyze_signal("BTC", "trend_breakout")
    assert result.confidence_modifier == 0.90, f"PARTIAL: Expected 0.90, got {result.confidence_modifier}"
    
    # Test HIGHLY_CORRELATED state
    engine.set_mock_correlations({
        f"trend_breakout:{s}": 0.65 for s in [
            "momentum_continuation", "mean_reversion", "volatility_breakout",
            "support_bounce", "resistance_rejection", "trend_pullback",
            "channel_breakout", "double_bottom", "double_top"
        ]
    })
    result = engine.analyze_signal("BTC", "trend_breakout")
    assert result.confidence_modifier <= 0.75, f"HIGH: Expected <= 0.75, got {result.confidence_modifier}"
    
    print("TEST 5 PASSED: Modifiers correct for all states")
    
    return True


def test_6_multiple_signals():
    """Test 6: Engine handles multiple signals correctly"""
    engine = get_alpha_correlation_engine()
    
    snapshot = engine.analyze_symbol("BTC")
    
    # Check structure
    assert snapshot.symbol == "BTC"
    assert len(snapshot.signal_correlations) > 0
    assert snapshot.highly_correlated_count >= 0
    assert snapshot.partial_count >= 0
    assert snapshot.unique_count >= 0
    assert 0.0 <= snapshot.avg_uniqueness <= 1.0
    
    total = snapshot.highly_correlated_count + snapshot.partial_count + snapshot.unique_count
    assert total == len(snapshot.signal_correlations), \
        "State counts don't match signal count"
    
    print("TEST 6 PASSED: Multiple signals handled correctly")
    print(f"  signals analyzed: {len(snapshot.signal_correlations)}")
    print(f"  highly_correlated: {snapshot.highly_correlated_count}")
    print(f"  partial: {snapshot.partial_count}")
    print(f"  unique: {snapshot.unique_count}")
    print(f"  avg_uniqueness: {snapshot.avg_uniqueness:.3f}")
    
    return True


def test_7_correlation_never_blocks():
    """
    Test 7: CRITICAL - Correlation NEVER blocks a signal
    
    Even maximum correlation produces modifiers > 0.
    """
    engine = MockAlphaCorrelationEngine()
    
    # Maximum possible correlation
    engine.set_mock_correlations({
        f"trend_breakout:{s}": 0.99 for s in [
            "momentum_continuation", "mean_reversion", "volatility_breakout",
            "support_bounce", "resistance_rejection", "trend_pullback",
            "channel_breakout", "double_bottom", "double_top"
        ]
    })
    
    result = engine.analyze_signal("BTC", "trend_breakout")
    
    # CRITICAL: Even at max correlation, modifiers are positive
    assert result.confidence_modifier > 0, \
        f"Correlation should never zero confidence. Got: {result.confidence_modifier}"
    
    assert result.size_modifier > 0, \
        f"Correlation should never zero size. Got: {result.size_modifier}"
    
    # Minimum thresholds
    assert result.confidence_modifier >= 0.5, \
        f"Minimum confidence modifier is 0.5. Got: {result.confidence_modifier}"
    
    assert result.size_modifier >= 0.5, \
        f"Minimum size modifier is 0.5. Got: {result.size_modifier}"
    
    print("TEST 7 PASSED: Correlation NEVER blocks signal")
    print(f"  max_correlation: {result.max_correlation:.3f}")
    print(f"  uniqueness: {result.uniqueness_score:.3f}")
    print(f"  conf_mod={result.confidence_modifier:.3f} >= 0.5 (never blocks)")
    print(f"  size_mod={result.size_modifier:.3f} >= 0.5 (never blocks)")
    
    return True


def test_8_real_data_integration():
    """Test 8: Real engine with correlation analysis"""
    engine = get_alpha_correlation_engine()
    
    result = engine.analyze_signal("BTC", "trend_breakout")
    
    # Check all fields present
    assert result.signal_type == "trend_breakout"
    assert result.correlation_state in CorrelationState
    assert 0.0 <= result.max_correlation <= 1.0
    assert 0.0 <= result.uniqueness_score <= 1.0
    assert len(result.correlation_with_signals) > 0
    assert 0.5 <= result.confidence_modifier <= 1.0
    assert 0.5 <= result.size_modifier <= 1.0
    
    print("TEST 8 PASSED: Real data integration works")
    print(f"  signal={result.signal_type}")
    print(f"  max_correlation={result.max_correlation:.3f}")
    print(f"  max_correlated_with={result.max_correlated_signal}")
    print(f"  state={result.correlation_state.value}")
    print(f"  signal_group={result.signal_group}")
    
    return True


def run_all_tests():
    """Run all correlation engine tests."""
    print("\n" + "=" * 60)
    print("PHASE 15.3 — Alpha Correlation Engine Tests")
    print("=" * 60 + "\n")
    
    tests = [
        ("Test 1: Independent signals → UNIQUE", test_1_independent_signals),
        ("Test 2: Partially related → PARTIAL", test_2_partially_related_signals),
        ("Test 3: Highly correlated → HIGH", test_3_highly_correlated_signals),
        ("Test 4: Uniqueness calculation", test_4_uniqueness_calculation),
        ("Test 5: Modifiers correct", test_5_modifiers_correct),
        ("Test 6: Multiple signals", test_6_multiple_signals),
        ("Test 7: Correlation NEVER blocks", test_7_correlation_never_blocks),
        ("Test 8: Real data integration", test_8_real_data_integration),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        print(f"\n--- {name} ---")
        try:
            if test_fn():
                passed += 1
        except AssertionError as e:
            print(f"FAILED: {name}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {name}")
            print(f"  Exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    print("=" * 60)
    
    return passed == len(tests)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
