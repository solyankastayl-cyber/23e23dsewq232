"""
PHASE 15.5 — Alpha Survival Engine Tests
========================================
Test signal survival across market regimes.

Test Cases:
1. Robust signal across regimes
2. Regime-dependent signal
3. Fragile signal
4. Survival score calculation correct
5. Regime dependency calculation correct
6. Modifiers applied correctly
7. Survival NEVER blocks signal
8. Real data integration
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_ecology.alpha_ecology_types import SurvivalState
from modules.alpha_ecology.alpha_survival_engine import (
    AlphaSurvivalEngine,
    AlphaSurvivalResult,
    MarketRegime,
    get_alpha_survival_engine,
    SURVIVAL_THRESHOLDS,
    SURVIVAL_MODIFIERS,
    ALL_REGIMES,
)


class MockAlphaSurvivalEngine(AlphaSurvivalEngine):
    """Engine with mock regime performance for testing."""
    
    def __init__(self):
        self._mock_performance: dict = {}
        self._mock_regime: MarketRegime = MarketRegime.RANGE
    
    def set_mock_performance(self, performance: dict):
        """
        Set mock regime performance.
        
        Format: {"TREND_UP": 0.5, "TREND_DOWN": 0.3, ...}
        """
        self._mock_performance = performance
    
    def set_mock_regime(self, regime: MarketRegime):
        """Set mock current regime."""
        self._mock_regime = regime
    
    def _get_regime_performance(self, symbol: str, signal_type: str) -> dict:
        """Return mock performance."""
        return self._mock_performance
    
    def _detect_current_regime(self, symbol: str) -> MarketRegime:
        """Return mock regime."""
        return self._mock_regime


def test_1_robust_signal():
    """Test 1: Robust signal across regimes"""
    engine = MockAlphaSurvivalEngine()
    
    # Signal works in all 5 regimes
    engine.set_mock_performance({
        "TREND_UP": 0.65,
        "TREND_DOWN": 0.55,
        "RANGE": 0.40,
        "HIGH_VOL": 0.50,
        "LOW_VOL": 0.35,
    })
    engine.set_mock_regime(MarketRegime.TREND_UP)
    
    result = engine.analyze_signal("BTC", "trend_breakout")
    
    # 5/5 positive regimes = 1.0 survival
    assert result.survival_state == SurvivalState.ROBUST, \
        f"Expected ROBUST, got {result.survival_state}"
    
    assert result.survival_score > 0.70, \
        f"Expected survival > 0.70, got {result.survival_score}"
    
    assert result.positive_regimes == 5
    assert result.negative_regimes == 0
    
    assert result.confidence_modifier >= 1.0, \
        f"Expected conf_mod >= 1.0 for ROBUST, got {result.confidence_modifier}"
    
    print("TEST 1 PASSED: Robust signal detected")
    print(f"  survival_score={result.survival_score:.3f}")
    print(f"  positive_regimes={result.positive_regimes}")
    print(f"  state={result.survival_state.value}")
    print(f"  conf_mod={result.confidence_modifier:.3f}")
    
    return True


def test_2_regime_dependent_signal():
    """Test 2: Regime-dependent signal"""
    engine = MockAlphaSurvivalEngine()
    
    # Signal works in 3/5 regimes
    engine.set_mock_performance({
        "TREND_UP": 0.55,
        "TREND_DOWN": 0.45,
        "RANGE": -0.20,    # Negative
        "HIGH_VOL": 0.30,
        "LOW_VOL": -0.15,  # Negative
    })
    engine.set_mock_regime(MarketRegime.TREND_UP)
    
    result = engine.analyze_signal("ETH", "trend_breakout")
    
    # 3/5 = 0.6 survival
    assert result.survival_state == SurvivalState.STABLE, \
        f"Expected STABLE (regime-dependent), got {result.survival_state}"
    
    assert 0.40 <= result.survival_score <= 0.70, \
        f"Expected survival in 0.40-0.70, got {result.survival_score}"
    
    assert result.positive_regimes == 3
    assert result.negative_regimes == 2
    
    print("TEST 2 PASSED: Regime-dependent signal detected")
    print(f"  survival_score={result.survival_score:.3f}")
    print(f"  positive={result.positive_regimes}, negative={result.negative_regimes}")
    print(f"  state={result.survival_state.value}")
    
    return True


def test_3_fragile_signal():
    """Test 3: Fragile signal (only works in specific conditions)"""
    engine = MockAlphaSurvivalEngine()
    
    # Signal only works in 1/5 regimes
    engine.set_mock_performance({
        "TREND_UP": 0.60,    # Only positive
        "TREND_DOWN": -0.30,
        "RANGE": -0.25,
        "HIGH_VOL": -0.10,
        "LOW_VOL": -0.20,
    })
    engine.set_mock_regime(MarketRegime.RANGE)
    
    result = engine.analyze_signal("SOL", "trend_breakout")
    
    # 1/5 = 0.2 survival
    assert result.survival_state == SurvivalState.FRAGILE, \
        f"Expected FRAGILE, got {result.survival_state}"
    
    assert result.survival_score < 0.40, \
        f"Expected survival < 0.40, got {result.survival_score}"
    
    assert result.positive_regimes == 1
    assert result.negative_regimes == 4
    
    assert result.confidence_modifier <= 0.80, \
        f"Expected conf_mod <= 0.80 for FRAGILE, got {result.confidence_modifier}"
    
    print("TEST 3 PASSED: Fragile signal detected")
    print(f"  survival_score={result.survival_score:.3f}")
    print(f"  positive={result.positive_regimes}, negative={result.negative_regimes}")
    print(f"  conf_mod={result.confidence_modifier:.3f}")
    
    return True


def test_4_survival_score_calculation():
    """Test 4: Survival score calculation correct"""
    engine = MockAlphaSurvivalEngine()
    
    # 4/5 positive regimes
    engine.set_mock_performance({
        "TREND_UP": 0.50,
        "TREND_DOWN": 0.40,
        "RANGE": 0.30,
        "HIGH_VOL": 0.20,
        "LOW_VOL": -0.10,  # 1 negative
    })
    engine.set_mock_regime(MarketRegime.TREND_UP)
    
    result = engine.analyze_signal("BTC", "trend_breakout")
    
    # Expected: 4/5 = 0.8
    assert abs(result.survival_score - 0.80) < 0.01, \
        f"Expected survival_score 0.80, got {result.survival_score}"
    
    print("TEST 4 PASSED: Survival score calculation correct")
    print(f"  positive_regimes={result.positive_regimes}/5")
    print(f"  survival_score={result.survival_score:.3f}")
    
    return True


def test_5_regime_dependency_calculation():
    """Test 5: Regime dependency calculation correct"""
    engine = MockAlphaSurvivalEngine()
    
    # High variance in performance
    engine.set_mock_performance({
        "TREND_UP": 0.80,
        "TREND_DOWN": -0.40,
        "RANGE": 0.30,
        "HIGH_VOL": 0.70,
        "LOW_VOL": -0.20,
    })
    engine.set_mock_regime(MarketRegime.TREND_UP)
    
    result = engine.analyze_signal("BTC", "volatility_breakout")
    
    # Regime dependency should be high due to variance
    assert result.regime_dependency > 0.3, \
        f"Expected high regime_dependency, got {result.regime_dependency}"
    
    # Low variance case
    engine.set_mock_performance({
        "TREND_UP": 0.50,
        "TREND_DOWN": 0.45,
        "RANGE": 0.48,
        "HIGH_VOL": 0.52,
        "LOW_VOL": 0.47,
    })
    
    result2 = engine.analyze_signal("BTC", "consistent_signal")
    
    assert result2.regime_dependency < result.regime_dependency, \
        "Low variance should have lower regime_dependency"
    
    print("TEST 5 PASSED: Regime dependency calculation correct")
    print(f"  High variance: regime_dependency={result.regime_dependency:.3f}")
    print(f"  Low variance: regime_dependency={result2.regime_dependency:.3f}")
    
    return True


def test_6_modifiers_correct():
    """Test 6: Modifiers applied correctly per state"""
    engine = MockAlphaSurvivalEngine()
    engine.set_mock_regime(MarketRegime.TREND_UP)
    
    # Test ROBUST
    engine.set_mock_performance({r.value: 0.5 for r in ALL_REGIMES})
    result = engine.analyze_signal("BTC", "test")
    assert result.confidence_modifier >= 1.0, f"ROBUST: Expected >= 1.0, got {result.confidence_modifier}"
    
    # Test STABLE (regime-dependent)
    engine.set_mock_performance({
        "TREND_UP": 0.5, "TREND_DOWN": 0.4, "RANGE": -0.2,
        "HIGH_VOL": 0.3, "LOW_VOL": -0.1
    })
    result = engine.analyze_signal("BTC", "test")
    assert 0.9 <= result.confidence_modifier <= 1.1, f"STABLE: Expected ~1.0, got {result.confidence_modifier}"
    
    # Test FRAGILE
    engine.set_mock_performance({
        "TREND_UP": 0.5, "TREND_DOWN": -0.3, "RANGE": -0.2,
        "HIGH_VOL": -0.1, "LOW_VOL": -0.15
    })
    result = engine.analyze_signal("BTC", "test")
    assert result.confidence_modifier <= 0.85, f"FRAGILE: Expected <= 0.85, got {result.confidence_modifier}"
    
    print("TEST 6 PASSED: Modifiers correct for all states")
    
    return True


def test_7_survival_never_blocks():
    """
    Test 7: CRITICAL - Survival NEVER blocks a signal
    
    Even completely fragile signal produces modifiers > 0.
    """
    engine = MockAlphaSurvivalEngine()
    engine.set_mock_regime(MarketRegime.RANGE)
    
    # Signal fails in ALL regimes
    engine.set_mock_performance({
        "TREND_UP": -0.30,
        "TREND_DOWN": -0.25,
        "RANGE": -0.40,
        "HIGH_VOL": -0.35,
        "LOW_VOL": -0.20,
    })
    
    result = engine.analyze_signal("BTC", "doomed_signal")
    
    # CRITICAL: Even at 0% survival, modifiers are positive
    assert result.confidence_modifier > 0, \
        f"Survival should never zero confidence. Got: {result.confidence_modifier}"
    
    assert result.size_modifier > 0, \
        f"Survival should never zero size. Got: {result.size_modifier}"
    
    # Minimum thresholds
    assert result.confidence_modifier >= 0.5, \
        f"Minimum confidence modifier is 0.5. Got: {result.confidence_modifier}"
    
    assert result.size_modifier >= 0.5, \
        f"Minimum size modifier is 0.5. Got: {result.size_modifier}"
    
    print("TEST 7 PASSED: Survival NEVER blocks signal")
    print(f"  0% survival (all regimes negative)")
    print(f"  survival_score={result.survival_score:.3f}")
    print(f"  conf_mod={result.confidence_modifier:.3f} >= 0.5 (never blocks)")
    print(f"  size_mod={result.size_modifier:.3f} >= 0.5 (never blocks)")
    
    return True


def test_8_real_data_integration():
    """Test 8: Real engine with actual data"""
    engine = get_alpha_survival_engine()
    
    result = engine.analyze_signal("BTC", "trend_breakout")
    
    # Check all fields present
    assert result.signal_type == "trend_breakout"
    assert result.survival_state in SurvivalState
    assert 0.0 <= result.survival_score <= 1.0
    assert result.regime_dependency >= 0
    assert result.positive_regimes >= 0
    assert result.negative_regimes >= 0
    assert result.positive_regimes + result.negative_regimes == len(ALL_REGIMES)
    assert result.current_regime in MarketRegime
    assert 0.5 <= result.confidence_modifier <= 1.1
    assert len(result.regime_performance) == 5
    
    print("TEST 8 PASSED: Real data integration works")
    print(f"  signal={result.signal_type}")
    print(f"  survival_score={result.survival_score:.3f}")
    print(f"  state={result.survival_state.value}")
    print(f"  current_regime={result.current_regime.value}")
    print(f"  best_regime={result.best_regime}")
    print(f"  worst_regime={result.worst_regime}")
    
    return True


def run_all_tests():
    """Run all survival engine tests."""
    print("\n" + "=" * 60)
    print("PHASE 15.5 — Alpha Survival Engine Tests")
    print("=" * 60 + "\n")
    
    tests = [
        ("Test 1: Robust signal", test_1_robust_signal),
        ("Test 2: Regime-dependent signal", test_2_regime_dependent_signal),
        ("Test 3: Fragile signal", test_3_fragile_signal),
        ("Test 4: Survival score calculation", test_4_survival_score_calculation),
        ("Test 5: Regime dependency calculation", test_5_regime_dependency_calculation),
        ("Test 6: Modifiers correct", test_6_modifiers_correct),
        ("Test 7: Survival NEVER blocks", test_7_survival_never_blocks),
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
