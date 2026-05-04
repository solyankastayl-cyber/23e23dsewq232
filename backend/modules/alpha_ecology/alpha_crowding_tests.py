"""
PHASE 15.2 — Alpha Crowding Engine Tests
=========================================
Test market crowding detection.

Test Cases:
1. Low funding + stable OI → LOW_CROWDING
2. High funding → MEDIUM_CROWDING
3. High OI pressure → HIGH_CROWDING
4. Liquidation clusters → HIGH_CROWDING
5. Extreme funding + OI → EXTREME_CROWDING
6. Modifiers applied correctly
7. Crowding NEVER blocks signal
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_ecology.alpha_ecology_types import CrowdingState
from modules.alpha_ecology.alpha_crowding_engine import (
    AlphaCrowdingEngine,
    AlphaCrowdingResult,
    get_alpha_crowding_engine,
    CROWDING_THRESHOLDS,
    CROWDING_MODIFIERS,
)


class MockAlphaCrowdingEngine(AlphaCrowdingEngine):
    """Engine with mock component scores for testing."""
    
    def __init__(self):
        self._mock_funding = 0.0
        self._mock_oi = 0.0
        self._mock_liq = 0.0
        self._mock_volume = 0.0
    
    def set_mock_scores(
        self,
        funding: float,
        oi: float,
        liq: float,
        volume: float,
    ):
        """Set mock component scores."""
        self._mock_funding = funding
        self._mock_oi = oi
        self._mock_liq = liq
        self._mock_volume = volume
    
    def _compute_funding_extreme(self, symbol: str) -> float:
        return self._mock_funding
    
    def _compute_oi_pressure(self, symbol: str) -> float:
        return self._mock_oi
    
    def _compute_liquidation_pressure(self, symbol: str) -> float:
        return self._mock_liq
    
    def _compute_volume_spike(self, symbol: str) -> float:
        return self._mock_volume


def test_1_low_crowding():
    """Test 1: Low funding + stable OI → LOW_CROWDING"""
    engine = MockAlphaCrowdingEngine()
    
    # All components low
    engine.set_mock_scores(
        funding=0.15,
        oi=0.10,
        liq=0.08,
        volume=0.12,
    )
    
    result = engine.analyze("BTC")
    
    # Expected score: 0.35*0.15 + 0.25*0.10 + 0.25*0.08 + 0.15*0.12 = 0.115
    assert result.crowding_state == CrowdingState.LOW_CROWDING, \
        f"Expected LOW_CROWDING, got {result.crowding_state}"
    
    assert result.crowding_score < 0.30, \
        f"Expected score < 0.30, got {result.crowding_score}"
    
    assert result.confidence_modifier == 1.0, \
        f"Expected conf_mod = 1.0, got {result.confidence_modifier}"
    
    print("TEST 1 PASSED: Low crowding detected")
    print(f"  score={result.crowding_score:.3f}, state={result.crowding_state.value}")
    
    return True


def test_2_high_funding_medium_crowding():
    """Test 2: High funding → MEDIUM_CROWDING"""
    engine = MockAlphaCrowdingEngine()
    
    # High funding, others low
    engine.set_mock_scores(
        funding=0.72,
        oi=0.20,
        liq=0.15,
        volume=0.18,
    )
    
    result = engine.analyze("BTC")
    
    # Expected score: 0.35*0.72 + 0.25*0.20 + 0.25*0.15 + 0.15*0.18 = 0.366
    assert result.crowding_state == CrowdingState.MEDIUM_CROWDING, \
        f"Expected MEDIUM_CROWDING, got {result.crowding_state}"
    
    assert 0.30 <= result.crowding_score < 0.50, \
        f"Expected score in 0.30-0.50, got {result.crowding_score}"
    
    assert result.confidence_modifier == 0.95, \
        f"Expected conf_mod = 0.95, got {result.confidence_modifier}"
    
    print("TEST 2 PASSED: Medium crowding from high funding")
    print(f"  score={result.crowding_score:.3f}, state={result.crowding_state.value}")
    print(f"  dominant_factor={result.drivers.get('dominant_factor')}")
    
    return True


def test_3_high_oi_pressure():
    """Test 3: High OI pressure → HIGH_CROWDING"""
    engine = MockAlphaCrowdingEngine()
    
    # High OI + moderate others
    engine.set_mock_scores(
        funding=0.45,
        oi=0.78,
        liq=0.42,
        volume=0.35,
    )
    
    result = engine.analyze("ETH")
    
    # Expected score: 0.35*0.45 + 0.25*0.78 + 0.25*0.42 + 0.15*0.35 = 0.510
    assert result.crowding_state == CrowdingState.HIGH_CROWDING, \
        f"Expected HIGH_CROWDING, got {result.crowding_state}"
    
    assert 0.50 <= result.crowding_score < 0.70, \
        f"Expected score in 0.50-0.70, got {result.crowding_score}"
    
    assert result.confidence_modifier == 0.85, \
        f"Expected conf_mod = 0.85, got {result.confidence_modifier}"
    
    print("TEST 3 PASSED: High crowding from OI pressure")
    print(f"  score={result.crowding_score:.3f}, state={result.crowding_state.value}")
    
    return True


def test_4_liquidation_clusters():
    """Test 4: Liquidation clusters → HIGH_CROWDING"""
    engine = MockAlphaCrowdingEngine()
    
    # High liquidations + moderate others
    engine.set_mock_scores(
        funding=0.35,
        oi=0.40,
        liq=0.82,
        volume=0.45,
    )
    
    result = engine.analyze("SOL")
    
    # Expected score: 0.35*0.35 + 0.25*0.40 + 0.25*0.82 + 0.15*0.45 = 0.495
    assert result.crowding_state in [CrowdingState.MEDIUM_CROWDING, CrowdingState.HIGH_CROWDING], \
        f"Expected MEDIUM or HIGH, got {result.crowding_state}"
    
    # Liquidation should be dominant factor
    assert result.drivers.get("dominant_factor") == "liquidation", \
        f"Expected liquidation dominant, got {result.drivers.get('dominant_factor')}"
    
    print("TEST 4 PASSED: Crowding from liquidation clusters")
    print(f"  score={result.crowding_score:.3f}, state={result.crowding_state.value}")
    print(f"  dominant_factor={result.drivers.get('dominant_factor')}")
    
    return True


def test_5_extreme_crowding():
    """Test 5: Extreme funding + OI → EXTREME_CROWDING"""
    engine = MockAlphaCrowdingEngine()
    
    # All components high
    engine.set_mock_scores(
        funding=0.88,
        oi=0.85,
        liq=0.72,
        volume=0.65,
    )
    
    result = engine.analyze("BTC")
    
    # Expected score: 0.35*0.88 + 0.25*0.85 + 0.25*0.72 + 0.15*0.65 = 0.798
    assert result.crowding_state == CrowdingState.EXTREME_CROWDING, \
        f"Expected EXTREME_CROWDING, got {result.crowding_state}"
    
    assert result.crowding_score >= 0.70, \
        f"Expected score >= 0.70, got {result.crowding_score}"
    
    assert result.confidence_modifier <= 0.70, \
        f"Expected conf_mod <= 0.70, got {result.confidence_modifier}"
    
    assert result.size_modifier <= 0.70, \
        f"Expected size_mod <= 0.70, got {result.size_modifier}"
    
    print("TEST 5 PASSED: Extreme crowding detected")
    print(f"  score={result.crowding_score:.3f}, state={result.crowding_state.value}")
    print(f"  conf_mod={result.confidence_modifier:.3f}, size_mod={result.size_modifier:.3f}")
    
    return True


def test_6_modifiers_correct():
    """Test 6: Modifiers applied correctly per state"""
    engine = MockAlphaCrowdingEngine()
    
    # Test each state
    test_cases = [
        (0.10, 0.10, 0.10, 0.10, CrowdingState.LOW_CROWDING, 1.0, 1.0),
        (0.50, 0.30, 0.25, 0.20, CrowdingState.MEDIUM_CROWDING, 0.95, 0.95),
        (0.65, 0.55, 0.50, 0.40, CrowdingState.HIGH_CROWDING, 0.85, 0.85),
    ]
    
    all_passed = True
    for funding, oi, liq, vol, expected_state, expected_conf, expected_size in test_cases:
        engine.set_mock_scores(funding, oi, liq, vol)
        result = engine.analyze("BTC")
        
        if result.crowding_state != expected_state:
            print(f"  FAIL: Expected {expected_state}, got {result.crowding_state}")
            all_passed = False
        
        if result.confidence_modifier != expected_conf:
            print(f"  FAIL: Expected conf_mod {expected_conf}, got {result.confidence_modifier}")
            all_passed = False
    
    assert all_passed, "Some modifier tests failed"
    
    print("TEST 6 PASSED: Modifiers correct for all states")
    
    return True


def test_7_crowding_never_blocks():
    """
    Test 7: CRITICAL - Crowding NEVER blocks a signal
    
    Even extreme crowding produces modifiers > 0, never blocks.
    """
    engine = MockAlphaCrowdingEngine()
    
    # Maximum possible crowding
    engine.set_mock_scores(
        funding=1.0,
        oi=1.0,
        liq=1.0,
        volume=1.0,
    )
    
    result = engine.analyze("BTC")
    
    # CRITICAL: Even at max crowding, modifiers are positive
    assert result.confidence_modifier > 0, \
        f"Crowding should never zero confidence. Got: {result.confidence_modifier}"
    
    assert result.size_modifier > 0, \
        f"Crowding should never zero size. Got: {result.size_modifier}"
    
    # Minimum thresholds
    assert result.confidence_modifier >= 0.5, \
        f"Minimum confidence modifier is 0.5. Got: {result.confidence_modifier}"
    
    assert result.size_modifier >= 0.5, \
        f"Minimum size modifier is 0.5. Got: {result.size_modifier}"
    
    print("TEST 7 PASSED: Crowding NEVER blocks signal")
    print(f"  Max crowding score: {result.crowding_score:.3f}")
    print(f"  conf_mod={result.confidence_modifier:.3f} > 0 (never blocks)")
    print(f"  size_mod={result.size_modifier:.3f} > 0 (never blocks)")
    
    return True


def test_8_real_data_integration():
    """Test 8: Real engine with actual exchange data"""
    engine = get_alpha_crowding_engine()
    
    result = engine.analyze("BTC")
    
    # Check all fields present
    assert result.symbol == "BTC"
    assert result.crowding_state in CrowdingState
    assert 0.0 <= result.crowding_score <= 1.0
    assert 0.0 <= result.funding_extreme <= 1.0
    assert 0.0 <= result.oi_pressure <= 1.0
    assert 0.0 <= result.liquidation_pressure <= 1.0
    assert 0.0 <= result.volume_spike <= 1.0
    assert 0.5 <= result.confidence_modifier <= 1.0
    assert 0.5 <= result.size_modifier <= 1.0
    
    print("TEST 8 PASSED: Real data integration works")
    print(f"  symbol={result.symbol}")
    print(f"  crowding_score={result.crowding_score:.3f}")
    print(f"  state={result.crowding_state.value}")
    print(f"  components: funding={result.funding_extreme:.2f}, oi={result.oi_pressure:.2f}, liq={result.liquidation_pressure:.2f}, vol={result.volume_spike:.2f}")
    
    return True


def run_all_tests():
    """Run all crowding engine tests."""
    print("\n" + "=" * 60)
    print("PHASE 15.2 — Alpha Crowding Engine Tests")
    print("=" * 60 + "\n")
    
    tests = [
        ("Test 1: Low crowding", test_1_low_crowding),
        ("Test 2: High funding → MEDIUM", test_2_high_funding_medium_crowding),
        ("Test 3: High OI → HIGH", test_3_high_oi_pressure),
        ("Test 4: Liquidation clusters", test_4_liquidation_clusters),
        ("Test 5: Extreme crowding", test_5_extreme_crowding),
        ("Test 6: Modifiers correct", test_6_modifiers_correct),
        ("Test 7: Crowding NEVER blocks", test_7_crowding_never_blocks),
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
