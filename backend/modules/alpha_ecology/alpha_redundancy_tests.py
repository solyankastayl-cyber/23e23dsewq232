"""
PHASE 15.4 — Alpha Redundancy Engine Tests
==========================================
Test signal consensus density detection.

Test Cases:
1. Evenly distributed signals → DIVERSIFIED (LOW redundancy)
2. Moderate consensus → NORMAL (MEDIUM)
3. Strong consensus → REDUNDANT (HIGH)
4. Diversity calculation correct
5. Modifiers applied correctly
6. Mixed long/short/neutral scenarios
7. Redundancy NEVER blocks signal
8. Real data integration
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_ecology.alpha_ecology_types import RedundancyState
from modules.alpha_ecology.alpha_redundancy_engine import (
    AlphaRedundancyEngine,
    AlphaRedundancyResult,
    SignalVote,
    SignalDirection,
    get_alpha_redundancy_engine,
    REDUNDANCY_THRESHOLDS,
    REDUNDANCY_MODIFIERS,
)


class MockAlphaRedundancyEngine(AlphaRedundancyEngine):
    """Engine with mock signal votes for testing."""
    
    def __init__(self):
        self._mock_votes: list = []
    
    def set_mock_votes(self, votes: list):
        """
        Set mock signal votes.
        
        Format: [("signal_name", "LONG/SHORT/NEUTRAL"), ...]
        """
        self._mock_votes = [
            SignalVote(
                signal_type=name,
                direction=SignalDirection(direction),
                confidence=0.6,
                source="mock",
            )
            for name, direction in votes
        ]
    
    def _collect_signal_votes(self, symbol: str):
        """Return mock votes."""
        return self._mock_votes


def test_1_diversified_signals():
    """Test 1: Evenly distributed signals → DIVERSIFIED (LOW redundancy)"""
    engine = MockAlphaRedundancyEngine()
    
    # 3 long, 3 short, 4 neutral = diverse
    engine.set_mock_votes([
        ("signal_1", "LONG"),
        ("signal_2", "LONG"),
        ("signal_3", "LONG"),
        ("signal_4", "SHORT"),
        ("signal_5", "SHORT"),
        ("signal_6", "SHORT"),
        ("signal_7", "NEUTRAL"),
        ("signal_8", "NEUTRAL"),
        ("signal_9", "NEUTRAL"),
        ("signal_10", "NEUTRAL"),
    ])
    
    result = engine.analyze("BTC")
    
    # Redundancy = max(3, 3) / 10 = 0.3
    assert result.redundancy_state == RedundancyState.DIVERSIFIED, \
        f"Expected DIVERSIFIED, got {result.redundancy_state}"
    
    assert result.redundancy_score < 0.40, \
        f"Expected redundancy < 0.40, got {result.redundancy_score}"
    
    assert result.diversity_score > 0.60, \
        f"Expected diversity > 0.60, got {result.diversity_score}"
    
    assert result.confidence_modifier == 1.0, \
        f"Expected conf_mod = 1.0, got {result.confidence_modifier}"
    
    print("TEST 1 PASSED: Diversified signals detected")
    print(f"  redundancy_score={result.redundancy_score:.3f}")
    print(f"  diversity_score={result.diversity_score:.3f}")
    print(f"  state={result.redundancy_state.value}")
    
    return True


def test_2_moderate_consensus():
    """Test 2: Moderate consensus → NORMAL (MEDIUM)"""
    engine = MockAlphaRedundancyEngine()
    
    # 5 long, 2 short, 3 neutral = moderate consensus
    engine.set_mock_votes([
        ("signal_1", "LONG"),
        ("signal_2", "LONG"),
        ("signal_3", "LONG"),
        ("signal_4", "LONG"),
        ("signal_5", "LONG"),
        ("signal_6", "SHORT"),
        ("signal_7", "SHORT"),
        ("signal_8", "NEUTRAL"),
        ("signal_9", "NEUTRAL"),
        ("signal_10", "NEUTRAL"),
    ])
    
    result = engine.analyze("ETH")
    
    # Redundancy = max(5, 2) / 10 = 0.5
    assert result.redundancy_state == RedundancyState.NORMAL, \
        f"Expected NORMAL, got {result.redundancy_state}"
    
    assert 0.40 <= result.redundancy_score < 0.65, \
        f"Expected redundancy in 0.40-0.65, got {result.redundancy_score}"
    
    assert result.dominant_direction == SignalDirection.LONG, \
        f"Expected dominant LONG, got {result.dominant_direction}"
    
    assert result.confidence_modifier == 0.92, \
        f"Expected conf_mod = 0.92, got {result.confidence_modifier}"
    
    print("TEST 2 PASSED: Moderate consensus detected")
    print(f"  redundancy_score={result.redundancy_score:.3f}")
    print(f"  dominant_direction={result.dominant_direction.value}")
    print(f"  state={result.redundancy_state.value}")
    
    return True


def test_3_strong_consensus():
    """Test 3: Strong consensus → REDUNDANT (HIGH)"""
    engine = MockAlphaRedundancyEngine()
    
    # 8 long, 1 short, 1 neutral = strong consensus
    engine.set_mock_votes([
        ("signal_1", "LONG"),
        ("signal_2", "LONG"),
        ("signal_3", "LONG"),
        ("signal_4", "LONG"),
        ("signal_5", "LONG"),
        ("signal_6", "LONG"),
        ("signal_7", "LONG"),
        ("signal_8", "LONG"),
        ("signal_9", "SHORT"),
        ("signal_10", "NEUTRAL"),
    ])
    
    result = engine.analyze("SOL")
    
    # Redundancy = max(8, 1) / 10 = 0.8
    assert result.redundancy_state == RedundancyState.REDUNDANT, \
        f"Expected REDUNDANT, got {result.redundancy_state}"
    
    assert result.redundancy_score >= 0.65, \
        f"Expected redundancy >= 0.65, got {result.redundancy_score}"
    
    assert result.confidence_modifier <= 0.80, \
        f"Expected conf_mod <= 0.80, got {result.confidence_modifier}"
    
    print("TEST 3 PASSED: Strong consensus (REDUNDANT) detected")
    print(f"  redundancy_score={result.redundancy_score:.3f}")
    print(f"  signals_long={result.signals_long}")
    print(f"  conf_mod={result.confidence_modifier:.3f}")
    
    return True


def test_4_diversity_calculation():
    """Test 4: Diversity calculation correct"""
    engine = MockAlphaRedundancyEngine()
    
    # 6 long, 4 short, 0 neutral
    engine.set_mock_votes([
        ("signal_1", "LONG"),
        ("signal_2", "LONG"),
        ("signal_3", "LONG"),
        ("signal_4", "LONG"),
        ("signal_5", "LONG"),
        ("signal_6", "LONG"),
        ("signal_7", "SHORT"),
        ("signal_8", "SHORT"),
        ("signal_9", "SHORT"),
        ("signal_10", "SHORT"),
    ])
    
    result = engine.analyze("BTC")
    
    # Redundancy = 6/10 = 0.6
    # Diversity = 1 - 0.6 = 0.4
    expected_diversity = 1.0 - result.redundancy_score
    
    assert abs(result.diversity_score - expected_diversity) < 0.001, \
        f"Expected diversity {expected_diversity:.4f}, got {result.diversity_score:.4f}"
    
    print("TEST 4 PASSED: Diversity calculation correct")
    print(f"  redundancy_score={result.redundancy_score:.3f}")
    print(f"  diversity_score={result.diversity_score:.3f} = 1 - {result.redundancy_score:.3f}")
    
    return True


def test_5_modifiers_correct():
    """Test 5: Modifiers applied correctly per state"""
    engine = MockAlphaRedundancyEngine()
    
    # Test DIVERSIFIED
    engine.set_mock_votes([
        ("s1", "LONG"), ("s2", "LONG"), ("s3", "LONG"),
        ("s4", "SHORT"), ("s5", "SHORT"), ("s6", "SHORT"),
        ("s7", "NEUTRAL"), ("s8", "NEUTRAL"), ("s9", "NEUTRAL"), ("s10", "NEUTRAL"),
    ])
    result = engine.analyze("BTC")
    assert result.confidence_modifier == 1.0, f"DIVERSIFIED: Expected 1.0, got {result.confidence_modifier}"
    
    # Test NORMAL
    engine.set_mock_votes([
        ("s1", "LONG"), ("s2", "LONG"), ("s3", "LONG"),
        ("s4", "LONG"), ("s5", "LONG"),
        ("s6", "SHORT"), ("s7", "SHORT"),
        ("s8", "NEUTRAL"), ("s9", "NEUTRAL"), ("s10", "NEUTRAL"),
    ])
    result = engine.analyze("BTC")
    assert result.confidence_modifier == 0.92, f"NORMAL: Expected 0.92, got {result.confidence_modifier}"
    
    # Test REDUNDANT
    engine.set_mock_votes([
        ("s1", "LONG"), ("s2", "LONG"), ("s3", "LONG"),
        ("s4", "LONG"), ("s5", "LONG"), ("s6", "LONG"),
        ("s7", "LONG"),
        ("s8", "SHORT"), ("s9", "SHORT"), ("s10", "NEUTRAL"),
    ])
    result = engine.analyze("BTC")
    assert result.confidence_modifier <= 0.80, f"REDUNDANT: Expected <= 0.80, got {result.confidence_modifier}"
    
    print("TEST 5 PASSED: Modifiers correct for all states")
    
    return True


def test_6_mixed_scenarios():
    """Test 6: Mixed long/short/neutral scenarios"""
    engine = MockAlphaRedundancyEngine()
    
    # All SHORT consensus
    engine.set_mock_votes([
        ("s1", "SHORT"), ("s2", "SHORT"), ("s3", "SHORT"),
        ("s4", "SHORT"), ("s5", "SHORT"), ("s6", "SHORT"),
        ("s7", "SHORT"), ("s8", "SHORT"),
        ("s9", "LONG"), ("s10", "NEUTRAL"),
    ])
    result = engine.analyze("BTC")
    
    assert result.dominant_direction == SignalDirection.SHORT, \
        f"Expected dominant SHORT, got {result.dominant_direction}"
    assert result.signals_short == 8
    assert result.redundancy_state == RedundancyState.REDUNDANT
    
    # All NEUTRAL
    engine.set_mock_votes([
        ("s1", "NEUTRAL"), ("s2", "NEUTRAL"), ("s3", "NEUTRAL"),
        ("s4", "NEUTRAL"), ("s5", "NEUTRAL"), ("s6", "NEUTRAL"),
        ("s7", "NEUTRAL"), ("s8", "NEUTRAL"),
        ("s9", "LONG"), ("s10", "SHORT"),
    ])
    result = engine.analyze("BTC")
    
    # max(1, 1) / 10 = 0.1 but neutral dominant
    assert result.signals_neutral == 8
    
    print("TEST 6 PASSED: Mixed scenarios handled correctly")
    print(f"  SHORT consensus: dominant={result.dominant_direction.value}")
    
    return True


def test_7_redundancy_never_blocks():
    """
    Test 7: CRITICAL - Redundancy NEVER blocks a signal
    
    Even 100% consensus produces modifiers > 0.
    """
    engine = MockAlphaRedundancyEngine()
    
    # 100% consensus - all LONG
    engine.set_mock_votes([
        ("s1", "LONG"), ("s2", "LONG"), ("s3", "LONG"),
        ("s4", "LONG"), ("s5", "LONG"), ("s6", "LONG"),
        ("s7", "LONG"), ("s8", "LONG"), ("s9", "LONG"), ("s10", "LONG"),
    ])
    
    result = engine.analyze("BTC")
    
    # CRITICAL: Even at max redundancy, modifiers are positive
    assert result.confidence_modifier > 0, \
        f"Redundancy should never zero confidence. Got: {result.confidence_modifier}"
    
    assert result.size_modifier > 0, \
        f"Redundancy should never zero size. Got: {result.size_modifier}"
    
    # Minimum thresholds
    assert result.confidence_modifier >= 0.5, \
        f"Minimum confidence modifier is 0.5. Got: {result.confidence_modifier}"
    
    assert result.size_modifier >= 0.5, \
        f"Minimum size modifier is 0.5. Got: {result.size_modifier}"
    
    print("TEST 7 PASSED: Redundancy NEVER blocks signal")
    print(f"  100% consensus (all LONG)")
    print(f"  redundancy_score={result.redundancy_score:.3f}")
    print(f"  conf_mod={result.confidence_modifier:.3f} >= 0.5 (never blocks)")
    print(f"  size_mod={result.size_modifier:.3f} >= 0.5 (never blocks)")
    
    return True


def test_8_real_data_integration():
    """Test 8: Real engine with actual signal collection"""
    engine = get_alpha_redundancy_engine()
    
    result = engine.analyze("BTC")
    
    # Check all fields present
    assert result.symbol == "BTC"
    assert result.total_signals > 0
    assert result.signals_long >= 0
    assert result.signals_short >= 0
    assert result.signals_neutral >= 0
    assert result.signals_long + result.signals_short + result.signals_neutral == result.total_signals
    assert 0.0 <= result.redundancy_score <= 1.0
    assert 0.0 <= result.diversity_score <= 1.0
    assert result.redundancy_state in RedundancyState
    assert 0.5 <= result.confidence_modifier <= 1.0
    
    print("TEST 8 PASSED: Real data integration works")
    print(f"  total_signals={result.total_signals}")
    print(f"  long={result.signals_long}, short={result.signals_short}, neutral={result.signals_neutral}")
    print(f"  redundancy_score={result.redundancy_score:.3f}")
    print(f"  state={result.redundancy_state.value}")
    print(f"  dominant={result.dominant_direction.value}")
    
    return True


def run_all_tests():
    """Run all redundancy engine tests."""
    print("\n" + "=" * 60)
    print("PHASE 15.4 — Alpha Redundancy Engine Tests")
    print("=" * 60 + "\n")
    
    tests = [
        ("Test 1: Diversified signals", test_1_diversified_signals),
        ("Test 2: Moderate consensus → NORMAL", test_2_moderate_consensus),
        ("Test 3: Strong consensus → REDUNDANT", test_3_strong_consensus),
        ("Test 4: Diversity calculation", test_4_diversity_calculation),
        ("Test 5: Modifiers correct", test_5_modifiers_correct),
        ("Test 6: Mixed scenarios", test_6_mixed_scenarios),
        ("Test 7: Redundancy NEVER blocks", test_7_redundancy_never_blocks),
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
