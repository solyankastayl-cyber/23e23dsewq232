"""
PHASE 15.1 — Alpha Decay Engine Tests
======================================
Test signal decay detection and modifier computation.

Test Cases:
1. Signal with clear decay → DECAYING state
2. Stable signal → STABLE state
3. Improving signal → IMPROVING state
4. Symbol-level aggregation
5. Modifier computation
6. Integration with Trading Product
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_ecology.alpha_ecology_types import (
    DecayState,
    SignalPerformanceWindow,
    SignalDecayResult,
)
from modules.alpha_ecology.alpha_decay_engine import (
    AlphaDecayEngine,
    get_alpha_decay_engine,
    DECAY_THRESHOLDS,
    DECAY_MODIFIERS,
)


class MockAlphaDecayEngine(AlphaDecayEngine):
    """Engine with mock performance windows for testing."""
    
    def __init__(self):
        self._mock_recent = None
        self._mock_historical = None
        self._mock_consistency = 0.7
    
    def set_mock_windows(
        self,
        recent: SignalPerformanceWindow,
        historical: SignalPerformanceWindow,
    ):
        """Set mock performance windows."""
        self._mock_recent = recent
        self._mock_historical = historical
    
    def _get_performance_window(
        self,
        symbol: str,
        signal_type: str,
        window_days: int,
        window_name: str,
    ) -> SignalPerformanceWindow:
        """Return mock windows."""
        if window_name == "recent":
            return self._mock_recent
        return self._mock_historical
    
    def _compute_consistency(
        self,
        symbol: str,
        signal_type: str,
    ) -> float:
        """Return mock consistency."""
        return self._mock_consistency


def test_1_decaying_signal():
    """Test 1: Signal with clear decay → DECAYING state"""
    engine = MockAlphaDecayEngine()
    now = datetime.now(timezone.utc)
    
    # Historical: 65% win rate, PF 2.3
    historical = SignalPerformanceWindow(
        window_name="historical",
        start_date=now,
        end_date=now,
        total_signals=100,
        winning_signals=65,
        losing_signals=35,
        win_rate=0.65,
        avg_return=0.025,
        profit_factor=2.3,
        sharpe_ratio=1.2,
    )
    
    # Recent: 48% win rate, PF 1.4 (severe decay)
    recent = SignalPerformanceWindow(
        window_name="recent",
        start_date=now,
        end_date=now,
        total_signals=30,
        winning_signals=14,
        losing_signals=16,
        win_rate=0.48,
        avg_return=0.005,
        profit_factor=1.4,
        sharpe_ratio=0.5,
    )
    
    engine.set_mock_windows(recent, historical)
    result = engine.analyze_signal("BTC", "trend_breakout")
    
    # Assertions
    assert result.decay_state == DecayState.DECAYING, \
        f"Expected DECAYING, got {result.decay_state}"
    
    assert result.decay_ratio < 0.85, \
        f"Expected decay_ratio < 0.85, got {result.decay_ratio}"
    
    assert result.confidence_modifier < 1.0, \
        f"Expected confidence_modifier < 1.0, got {result.confidence_modifier}"
    
    assert result.size_modifier < 1.0, \
        f"Expected size_modifier < 1.0, got {result.size_modifier}"
    
    print("TEST 1 PASSED: Decaying signal detected")
    print(f"  decay_ratio={result.decay_ratio:.3f}")
    print(f"  decay_state={result.decay_state.value}")
    print(f"  conf_mod={result.confidence_modifier:.2f}, size_mod={result.size_modifier:.2f}")
    
    return True


def test_2_stable_signal():
    """Test 2: Stable signal → STABLE state"""
    engine = MockAlphaDecayEngine()
    now = datetime.now(timezone.utc)
    
    # Historical: 58% win rate, PF 1.9
    historical = SignalPerformanceWindow(
        window_name="historical",
        start_date=now,
        end_date=now,
        total_signals=100,
        winning_signals=58,
        losing_signals=42,
        win_rate=0.58,
        avg_return=0.018,
        profit_factor=1.9,
        sharpe_ratio=0.9,
    )
    
    # Recent: 56% win rate, PF 1.85 (stable, slight variance)
    recent = SignalPerformanceWindow(
        window_name="recent",
        start_date=now,
        end_date=now,
        total_signals=30,
        winning_signals=17,
        losing_signals=13,
        win_rate=0.56,
        avg_return=0.016,
        profit_factor=1.85,
        sharpe_ratio=0.85,
    )
    
    engine.set_mock_windows(recent, historical)
    result = engine.analyze_signal("ETH", "momentum_continuation")
    
    # Assertions
    assert result.decay_state == DecayState.STABLE, \
        f"Expected STABLE, got {result.decay_state}"
    
    assert 0.85 <= result.decay_ratio <= 1.1, \
        f"Expected decay_ratio in stable range, got {result.decay_ratio}"
    
    assert result.confidence_modifier == 1.0, \
        f"Expected confidence_modifier = 1.0, got {result.confidence_modifier}"
    
    print("TEST 2 PASSED: Stable signal detected")
    print(f"  decay_ratio={result.decay_ratio:.3f}")
    print(f"  decay_state={result.decay_state.value}")
    
    return True


def test_3_improving_signal():
    """Test 3: Improving signal → IMPROVING state"""
    engine = MockAlphaDecayEngine()
    now = datetime.now(timezone.utc)
    
    # Historical: 52% win rate, PF 1.5
    historical = SignalPerformanceWindow(
        window_name="historical",
        start_date=now,
        end_date=now,
        total_signals=100,
        winning_signals=52,
        losing_signals=48,
        win_rate=0.52,
        avg_return=0.01,
        profit_factor=1.5,
        sharpe_ratio=0.6,
    )
    
    # Recent: 62% win rate, PF 2.1 (improving)
    recent = SignalPerformanceWindow(
        window_name="recent",
        start_date=now,
        end_date=now,
        total_signals=30,
        winning_signals=19,
        losing_signals=11,
        win_rate=0.62,
        avg_return=0.022,
        profit_factor=2.1,
        sharpe_ratio=1.1,
    )
    
    engine.set_mock_windows(recent, historical)
    result = engine.analyze_signal("SOL", "volatility_breakout")
    
    # Assertions
    assert result.decay_state == DecayState.IMPROVING, \
        f"Expected IMPROVING, got {result.decay_state}"
    
    assert result.decay_ratio > 1.1, \
        f"Expected decay_ratio > 1.1, got {result.decay_ratio}"
    
    assert result.confidence_modifier >= 1.0, \
        f"Expected confidence_modifier >= 1.0, got {result.confidence_modifier}"
    
    print("TEST 3 PASSED: Improving signal detected")
    print(f"  decay_ratio={result.decay_ratio:.3f}")
    print(f"  decay_state={result.decay_state.value}")
    print(f"  conf_mod={result.confidence_modifier:.2f}")
    
    return True


def test_4_symbol_aggregation():
    """Test 4: Symbol-level aggregation across signals"""
    # Use real engine
    engine = get_alpha_decay_engine()
    
    snapshot = engine.analyze_symbol("BTC")
    
    # Assertions
    assert snapshot.symbol == "BTC"
    assert len(snapshot.signal_decays) > 0
    assert snapshot.decaying_signals_count >= 0
    assert snapshot.stable_signals_count >= 0
    assert snapshot.improving_signals_count >= 0
    assert snapshot.overall_decay_state in DecayState
    assert 0.5 <= snapshot.overall_confidence_modifier <= 1.2
    assert 0.5 <= snapshot.overall_size_modifier <= 1.1
    
    print("TEST 4 PASSED: Symbol aggregation works")
    print(f"  symbol={snapshot.symbol}")
    print(f"  signals: decaying={snapshot.decaying_signals_count}, stable={snapshot.stable_signals_count}, improving={snapshot.improving_signals_count}")
    print(f"  overall_state={snapshot.overall_decay_state.value}")
    print(f"  avg_decay_ratio={snapshot.avg_decay_ratio:.3f}")
    
    return True


def test_5_modifier_computation():
    """Test 5: Modifier computation follows rules"""
    engine = MockAlphaDecayEngine()
    now = datetime.now(timezone.utc)
    
    # Test severe decay (ratio < 0.7)
    historical = SignalPerformanceWindow(
        window_name="historical",
        start_date=now,
        end_date=now,
        total_signals=100,
        winning_signals=70,
        losing_signals=30,
        win_rate=0.70,
        avg_return=0.03,
        profit_factor=2.5,
        sharpe_ratio=1.5,
    )
    
    recent = SignalPerformanceWindow(
        window_name="recent",
        start_date=now,
        end_date=now,
        total_signals=30,
        winning_signals=12,
        losing_signals=18,
        win_rate=0.40,
        avg_return=-0.005,
        profit_factor=1.1,
        sharpe_ratio=0.2,
    )
    
    engine.set_mock_windows(recent, historical)
    result = engine.analyze_signal("BTC", "trend_breakout")
    
    # Severe decay should have stronger modifiers
    assert result.decay_state == DecayState.DECAYING
    assert result.confidence_modifier <= 0.80 * 0.95  # Severe penalty
    assert result.size_modifier <= 0.70 * 0.9
    
    print("TEST 5 PASSED: Modifier computation correct")
    print(f"  decay_ratio={result.decay_ratio:.3f} (severe)")
    print(f"  conf_mod={result.confidence_modifier:.3f}")
    print(f"  size_mod={result.size_modifier:.3f}")
    
    return True


def test_6_integration_modifier():
    """Test 6: Get modifier for Trading Product integration"""
    engine = get_alpha_decay_engine()
    
    modifier = engine.get_modifier_for_symbol("BTC")
    
    # Check required fields
    assert "decay_confidence_modifier" in modifier
    assert "decay_size_modifier" in modifier
    assert "decay_state" in modifier
    assert "decaying_signals" in modifier
    assert "total_signals" in modifier
    
    # Check value ranges
    assert 0.5 <= modifier["decay_confidence_modifier"] <= 1.2
    assert 0.5 <= modifier["decay_size_modifier"] <= 1.1
    assert modifier["decay_state"] in [s.value for s in DecayState]
    
    print("TEST 6 PASSED: Integration modifier works")
    print(f"  decay_confidence_modifier={modifier['decay_confidence_modifier']:.3f}")
    print(f"  decay_size_modifier={modifier['decay_size_modifier']:.3f}")
    print(f"  decay_state={modifier['decay_state']}")
    print(f"  decaying_signals={modifier['decaying_signals']}/{modifier['total_signals']}")
    
    return True


def test_7_decay_does_not_block_signal():
    """
    Test 7: CRITICAL - Decay NEVER blocks a signal
    
    Decay only reduces confidence/size, never sets action=BLOCK
    """
    engine = MockAlphaDecayEngine()
    now = datetime.now(timezone.utc)
    
    # Even with 100% decay (recent = 0%), modifiers should exist, not block
    historical = SignalPerformanceWindow(
        window_name="historical",
        start_date=now,
        end_date=now,
        total_signals=100,
        winning_signals=60,
        losing_signals=40,
        win_rate=0.60,
        avg_return=0.02,
        profit_factor=2.0,
        sharpe_ratio=1.0,
    )
    
    recent = SignalPerformanceWindow(
        window_name="recent",
        start_date=now,
        end_date=now,
        total_signals=30,
        winning_signals=9,
        losing_signals=21,
        win_rate=0.30,  # Terrible recent performance
        avg_return=-0.01,
        profit_factor=0.8,
        sharpe_ratio=-0.5,
    )
    
    engine.set_mock_windows(recent, historical)
    result = engine.analyze_signal("BTC", "trend_breakout")
    
    # CRITICAL: Even severe decay produces modifiers, not blocks
    assert result.confidence_modifier > 0, "Decay should never zero confidence"
    assert result.size_modifier > 0, "Decay should never zero size"
    assert result.confidence_modifier >= 0.5, "Minimum confidence modifier"
    assert result.size_modifier >= 0.4, "Minimum size modifier"
    
    print("TEST 7 PASSED: Decay does NOT block signal")
    print(f"  decay_ratio={result.decay_ratio:.3f} (severe)")
    print(f"  conf_mod={result.confidence_modifier:.3f} > 0 (never blocks)")
    print(f"  size_mod={result.size_modifier:.3f} > 0 (never blocks)")
    
    return True


def run_all_tests():
    """Run all decay engine tests."""
    print("\n" + "=" * 60)
    print("PHASE 15.1 — Alpha Decay Engine Tests")
    print("=" * 60 + "\n")
    
    tests = [
        ("Test 1: Decaying signal → DECAYING", test_1_decaying_signal),
        ("Test 2: Stable signal → STABLE", test_2_stable_signal),
        ("Test 3: Improving signal → IMPROVING", test_3_improving_signal),
        ("Test 4: Symbol aggregation", test_4_symbol_aggregation),
        ("Test 5: Modifier computation", test_5_modifier_computation),
        ("Test 6: Integration modifier", test_6_integration_modifier),
        ("Test 7: Decay does NOT block signal", test_7_decay_does_not_block_signal),
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
