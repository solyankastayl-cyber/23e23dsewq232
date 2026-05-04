"""
PHASE 15.6 — Alpha Ecology Aggregator Tests
============================================
Test unified ecology aggregation.

Test Cases:
1. Healthy alpha (all components good)
2. Stable alpha (mixed components)
3. Stressed alpha (several weak components)
4. Critical alpha (many weak components)
5. Modifiers applied correctly
6. Driver aggregation correct
7. Ecology NEVER blocks signal
8. Real data integration
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_ecology.alpha_ecology_types import (
    DecayState,
    CrowdingState,
    CorrelationState,
    RedundancyState,
    SurvivalState,
)
from modules.alpha_ecology.alpha_ecology_engine import (
    AlphaEcologyEngine,
    AlphaEcologyResult,
    EcologyState,
    get_alpha_ecology_engine,
    ECOLOGY_THRESHOLDS,
    ECOLOGY_MODIFIERS,
    ECOLOGY_WEIGHTS,
)


class MockAlphaEcologyEngine(AlphaEcologyEngine):
    """Engine with mock component modifiers for testing."""
    
    def __init__(self):
        self._mock_decay = {"decay_confidence_modifier": 1.0, "decay_state": "STABLE"}
        self._mock_crowding = {"crowding_confidence_modifier": 1.0, "crowding_state": "LOW_CROWDING"}
        self._mock_correlation = {"correlation_confidence_modifier": 1.0, "correlation_state": "UNIQUE"}
        self._mock_redundancy = {"redundancy_confidence_modifier": 1.0, "redundancy_state": "DIVERSIFIED"}
        self._mock_survival = {"survival_confidence_modifier": 1.0, "survival_state": "ROBUST"}
    
    def set_mock_components(
        self,
        decay_mod: float = 1.0,
        decay_state: str = "STABLE",
        crowding_mod: float = 1.0,
        crowding_state: str = "LOW_CROWDING",
        correlation_mod: float = 1.0,
        correlation_state: str = "UNIQUE",
        redundancy_mod: float = 1.0,
        redundancy_state: str = "DIVERSIFIED",
        survival_mod: float = 1.0,
        survival_state: str = "ROBUST",
    ):
        """Set mock component modifiers."""
        self._mock_decay = {"decay_confidence_modifier": decay_mod, "decay_state": decay_state}
        self._mock_crowding = {"crowding_confidence_modifier": crowding_mod, "crowding_state": crowding_state}
        self._mock_correlation = {"correlation_confidence_modifier": correlation_mod, "correlation_state": correlation_state}
        self._mock_redundancy = {"redundancy_confidence_modifier": redundancy_mod, "redundancy_state": redundancy_state}
        self._mock_survival = {"survival_confidence_modifier": survival_mod, "survival_state": survival_state}
    
    @property
    def decay_engine(self):
        return MockEngine(self._mock_decay)
    
    @property
    def crowding_engine(self):
        return MockEngine(self._mock_crowding)
    
    @property
    def correlation_engine(self):
        return MockEngine(self._mock_correlation)
    
    @property
    def redundancy_engine(self):
        return MockEngine(self._mock_redundancy)
    
    @property
    def survival_engine(self):
        return MockEngine(self._mock_survival)


class MockEngine:
    """Simple mock engine that returns preset modifier."""
    
    def __init__(self, modifier: dict):
        self._modifier = modifier
    
    def get_modifier_for_symbol(self, symbol: str) -> dict:
        return self._modifier


def test_1_healthy_alpha():
    """Test 1: Healthy alpha (all components good)"""
    engine = MockAlphaEcologyEngine()
    
    # All components healthy
    engine.set_mock_components(
        decay_mod=1.10, decay_state="IMPROVING",
        crowding_mod=1.0, crowding_state="LOW_CROWDING",
        correlation_mod=1.0, correlation_state="UNIQUE",
        redundancy_mod=1.0, redundancy_state="DIVERSIFIED",
        survival_mod=1.05, survival_state="ROBUST",
    )
    
    result = engine.analyze("BTC")
    
    # Expected score: 0.2*(1.1+1.0+1.0+1.0+1.05) = 1.03
    assert result.ecology_state == EcologyState.STABLE or result.ecology_state == EcologyState.HEALTHY, \
        f"Expected STABLE/HEALTHY, got {result.ecology_state}"
    
    assert result.ecology_score >= 0.95, \
        f"Expected high ecology_score, got {result.ecology_score}"
    
    assert result.confidence_modifier >= 1.0, \
        f"Expected conf_mod >= 1.0 for healthy, got {result.confidence_modifier}"
    
    print("TEST 1 PASSED: Healthy alpha detected")
    print(f"  ecology_score={result.ecology_score:.3f}")
    print(f"  ecology_state={result.ecology_state.value}")
    print(f"  conf_mod={result.confidence_modifier:.3f}")
    
    return True


def test_2_stable_alpha():
    """Test 2: Stable alpha (mixed components)"""
    engine = MockAlphaEcologyEngine()
    
    # Mixed - some good, some neutral
    engine.set_mock_components(
        decay_mod=1.0, decay_state="STABLE",
        crowding_mod=0.95, crowding_state="MEDIUM_CROWDING",
        correlation_mod=0.90, correlation_state="PARTIAL",
        redundancy_mod=0.92, redundancy_state="NORMAL",
        survival_mod=1.0, survival_state="STABLE",
    )
    
    result = engine.analyze("ETH")
    
    # Expected score: 0.2*(1.0+0.95+0.90+0.92+1.0) = 0.954
    assert result.ecology_state == EcologyState.STABLE, \
        f"Expected STABLE, got {result.ecology_state}"
    
    assert 0.90 <= result.ecology_score <= 1.05, \
        f"Expected ecology_score in stable range, got {result.ecology_score}"
    
    assert result.confidence_modifier == 1.0, \
        f"Expected conf_mod = 1.0 for stable, got {result.confidence_modifier}"
    
    print("TEST 2 PASSED: Stable alpha detected")
    print(f"  ecology_score={result.ecology_score:.3f}")
    print(f"  ecology_state={result.ecology_state.value}")
    
    return True


def test_3_stressed_alpha():
    """Test 3: Stressed alpha (several weak components)"""
    engine = MockAlphaEcologyEngine()
    
    # Several components stressed
    engine.set_mock_components(
        decay_mod=0.80, decay_state="DECAYING",
        crowding_mod=0.85, crowding_state="HIGH_CROWDING",
        correlation_mod=0.75, correlation_state="HIGHLY_CORRELATED",
        redundancy_mod=0.80, redundancy_state="REDUNDANT",
        survival_mod=0.95, survival_state="STABLE",
    )
    
    result = engine.analyze("SOL")
    
    # Expected score: 0.2*(0.80+0.85+0.75+0.80+0.95) = 0.83
    assert result.ecology_state == EcologyState.STRESSED, \
        f"Expected STRESSED, got {result.ecology_state}"
    
    assert 0.75 <= result.ecology_score < 0.90, \
        f"Expected ecology_score in stressed range, got {result.ecology_score}"
    
    assert result.confidence_modifier == 0.85, \
        f"Expected conf_mod = 0.85 for stressed, got {result.confidence_modifier}"
    
    print("TEST 3 PASSED: Stressed alpha detected")
    print(f"  ecology_score={result.ecology_score:.3f}")
    print(f"  ecology_state={result.ecology_state.value}")
    print(f"  weakest_component={result.weakest_component}")
    
    return True


def test_4_critical_alpha():
    """Test 4: Critical alpha (many weak components)"""
    engine = MockAlphaEcologyEngine()
    
    # All components weak
    engine.set_mock_components(
        decay_mod=0.70, decay_state="DECAYING",
        crowding_mod=0.70, crowding_state="EXTREME_CROWDING",
        correlation_mod=0.65, correlation_state="HIGHLY_CORRELATED",
        redundancy_mod=0.70, redundancy_state="REDUNDANT",
        survival_mod=0.72, survival_state="FRAGILE",
    )
    
    result = engine.analyze("DOGE")
    
    # Expected score: 0.2*(0.70+0.70+0.65+0.70+0.72) = 0.694
    assert result.ecology_state == EcologyState.CRITICAL, \
        f"Expected CRITICAL, got {result.ecology_state}"
    
    assert result.ecology_score < 0.75, \
        f"Expected ecology_score < 0.75 for critical, got {result.ecology_score}"
    
    assert result.confidence_modifier <= 0.65, \
        f"Expected conf_mod <= 0.65 for critical, got {result.confidence_modifier}"
    
    print("TEST 4 PASSED: Critical alpha detected")
    print(f"  ecology_score={result.ecology_score:.3f}")
    print(f"  ecology_state={result.ecology_state.value}")
    print(f"  conf_mod={result.confidence_modifier:.3f}")
    
    return True


def test_5_modifiers_correct():
    """Test 5: Modifiers applied correctly per state"""
    engine = MockAlphaEcologyEngine()
    
    # Test HEALTHY
    engine.set_mock_components(
        decay_mod=1.1, crowding_mod=1.05, correlation_mod=1.05,
        redundancy_mod=1.05, survival_mod=1.1
    )
    result = engine.analyze("BTC")
    assert result.confidence_modifier >= 1.05, f"HEALTHY: Expected >= 1.05, got {result.confidence_modifier}"
    
    # Test STABLE
    engine.set_mock_components(
        decay_mod=1.0, crowding_mod=0.95, correlation_mod=0.95,
        redundancy_mod=0.95, survival_mod=1.0
    )
    result = engine.analyze("BTC")
    assert result.confidence_modifier == 1.0, f"STABLE: Expected 1.0, got {result.confidence_modifier}"
    
    # Test STRESSED
    engine.set_mock_components(
        decay_mod=0.85, crowding_mod=0.80, correlation_mod=0.85,
        redundancy_mod=0.85, survival_mod=0.85
    )
    result = engine.analyze("BTC")
    assert result.confidence_modifier == 0.85, f"STRESSED: Expected 0.85, got {result.confidence_modifier}"
    
    # Test CRITICAL
    engine.set_mock_components(
        decay_mod=0.70, crowding_mod=0.65, correlation_mod=0.70,
        redundancy_mod=0.70, survival_mod=0.70
    )
    result = engine.analyze("BTC")
    assert result.confidence_modifier <= 0.65, f"CRITICAL: Expected <= 0.65, got {result.confidence_modifier}"
    
    print("TEST 5 PASSED: Modifiers correct for all states")
    
    return True


def test_6_driver_aggregation():
    """Test 6: Driver aggregation correct"""
    engine = MockAlphaEcologyEngine()
    
    engine.set_mock_components(
        decay_mod=0.80, decay_state="DECAYING",
        crowding_mod=0.70, crowding_state="EXTREME_CROWDING",
        correlation_mod=0.90, correlation_state="PARTIAL",
        redundancy_mod=0.85, redundancy_state="NORMAL",
        survival_mod=1.05, survival_state="ROBUST",
    )
    
    result = engine.analyze("BTC")
    
    # Check drivers are correctly aggregated
    assert result.drivers["decay"] == "DECAYING"
    assert result.drivers["crowding"] == "EXTREME_CROWDING"
    assert result.drivers["correlation"] == "PARTIAL"
    assert result.drivers["redundancy"] == "NORMAL"
    assert result.drivers["survival"] == "ROBUST"
    
    # Check component scores
    assert result.component_scores["decay"] == 0.80
    assert result.component_scores["crowding"] == 0.70
    assert result.component_scores["survival"] == 1.05
    
    # Check weakest/strongest
    assert result.weakest_component == "crowding"
    assert result.strongest_component == "survival"
    
    print("TEST 6 PASSED: Driver aggregation correct")
    print(f"  weakest={result.weakest_component} ({result.component_scores['crowding']:.2f})")
    print(f"  strongest={result.strongest_component} ({result.component_scores['survival']:.2f})")
    
    return True


def test_7_ecology_never_blocks():
    """
    Test 7: CRITICAL - Ecology NEVER blocks a signal
    
    Even worst-case ecology produces modifiers > 0.
    """
    engine = MockAlphaEcologyEngine()
    
    # Absolute worst case - all components at minimum
    engine.set_mock_components(
        decay_mod=0.50, decay_state="DECAYING",
        crowding_mod=0.50, crowding_state="EXTREME_CROWDING",
        correlation_mod=0.50, correlation_state="HIGHLY_CORRELATED",
        redundancy_mod=0.50, redundancy_state="REDUNDANT",
        survival_mod=0.50, survival_state="FRAGILE",
    )
    
    result = engine.analyze("BTC")
    
    # CRITICAL: Even at minimum, modifiers are positive
    assert result.confidence_modifier > 0, \
        f"Ecology should never zero confidence. Got: {result.confidence_modifier}"
    
    assert result.size_modifier > 0, \
        f"Ecology should never zero size. Got: {result.size_modifier}"
    
    # Minimum thresholds
    assert result.confidence_modifier >= 0.5, \
        f"Minimum confidence modifier is 0.5. Got: {result.confidence_modifier}"
    
    assert result.size_modifier >= 0.5, \
        f"Minimum size modifier is 0.5. Got: {result.size_modifier}"
    
    print("TEST 7 PASSED: Ecology NEVER blocks signal")
    print(f"  Worst case: all components at 0.50")
    print(f"  ecology_score={result.ecology_score:.3f}")
    print(f"  ecology_state={result.ecology_state.value}")
    print(f"  conf_mod={result.confidence_modifier:.3f} >= 0.5 (never blocks)")
    print(f"  size_mod={result.size_modifier:.3f} >= 0.5 (never blocks)")
    
    return True


def test_8_real_data_integration():
    """Test 8: Real engine with actual data from all sub-engines"""
    engine = get_alpha_ecology_engine()
    
    result = engine.analyze("BTC")
    
    # Check all fields present
    assert result.symbol == "BTC"
    assert result.ecology_state in EcologyState
    assert result.decay_state in DecayState
    assert result.crowding_state in CrowdingState
    assert result.correlation_state in CorrelationState
    assert result.redundancy_state in RedundancyState
    assert result.survival_state in SurvivalState
    assert 0.0 <= result.ecology_score <= 1.5
    assert 0.5 <= result.confidence_modifier <= 1.1
    assert len(result.drivers) == 5
    assert len(result.component_scores) == 5
    
    # Test Trading Product integration format
    tp_data = engine.get_trading_product_ecology("BTC")
    assert "ecology_score" in tp_data
    assert "ecology_state" in tp_data
    assert "components" in tp_data
    assert len(tp_data["components"]) == 5
    
    print("TEST 8 PASSED: Real data integration works")
    print(f"  symbol={result.symbol}")
    print(f"  ecology_score={result.ecology_score:.3f}")
    print(f"  ecology_state={result.ecology_state.value}")
    print(f"  conf_mod={result.confidence_modifier:.3f}")
    print(f"  weakest={result.weakest_component}")
    print(f"  strongest={result.strongest_component}")
    print(f"  drivers: {result.drivers}")
    
    return True


def run_all_tests():
    """Run all ecology aggregator tests."""
    print("\n" + "=" * 60)
    print("PHASE 15.6 — Alpha Ecology Aggregator Tests")
    print("=" * 60 + "\n")
    
    tests = [
        ("Test 1: Healthy alpha", test_1_healthy_alpha),
        ("Test 2: Stable alpha", test_2_stable_alpha),
        ("Test 3: Stressed alpha", test_3_stressed_alpha),
        ("Test 4: Critical alpha", test_4_critical_alpha),
        ("Test 5: Modifiers correct", test_5_modifiers_correct),
        ("Test 6: Driver aggregation", test_6_driver_aggregation),
        ("Test 7: Ecology NEVER blocks", test_7_ecology_never_blocks),
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
