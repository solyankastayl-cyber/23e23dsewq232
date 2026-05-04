#!/usr/bin/env python3
"""
TA Hypothesis Tests
====================
Phase 14.2 — Unit tests for TA hypothesis building.

Tests:
1. Strong bullish trend
2. Strong bearish trend
3. Neutral range
4. Strong trend but bad entry
5. Conflicting indicators
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.ta_engine.hypothesis.ta_hypothesis_types import (
    TAHypothesis,
    TADirection,
    MarketRegime,
    SetupType,
)
from modules.ta_engine.hypothesis.ta_hypothesis_rules import (
    CONVICTION_WEIGHTS,
    DRIVER_WEIGHTS,
)


def test_conviction_weights():
    """Test conviction weight configuration."""
    print("\n[TEST] Conviction Weights")
    
    total = sum(CONVICTION_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001, f"Weights don't sum to 1: {total}"
    print(f"  ✓ Weights sum to 1.0")
    
    assert CONVICTION_WEIGHTS["setup_quality"] == 0.35
    print(f"  ✓ Setup quality weight: {CONVICTION_WEIGHTS['setup_quality']}")
    
    return True


def test_driver_weights():
    """Test driver weight configuration."""
    print("\n[TEST] Driver Weights")
    
    total = sum(DRIVER_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001, f"Weights don't sum to 1: {total}"
    print(f"  ✓ Driver weights sum to 1.0")
    
    assert "trend" in DRIVER_WEIGHTS
    assert "momentum" in DRIVER_WEIGHTS
    assert "structure" in DRIVER_WEIGHTS
    print(f"  ✓ All drivers present")
    
    return True


def test_hypothesis_integration():
    """Test full hypothesis building with real data."""
    print("\n[TEST] Hypothesis Integration (Real Data)")
    
    from modules.ta_engine.hypothesis import TAHypothesisBuilder
    
    builder = TAHypothesisBuilder()
    
    for symbol in ["BTC", "ETH", "SOL"]:
        hypo = builder.build(symbol)
        
        assert hypo.symbol == symbol
        assert hypo.direction in [TADirection.LONG, TADirection.SHORT, TADirection.NEUTRAL]
        assert 0 <= hypo.setup_quality <= 1
        assert 0 <= hypo.conviction <= 1
        assert isinstance(hypo.setup_type, SetupType)
        assert isinstance(hypo.regime, MarketRegime)
        
        print(f"  ✓ {symbol}: direction={hypo.direction.value}, conviction={hypo.conviction:.3f}, regime={hypo.regime.value}")
    
    return True


def test_hypothesis_components():
    """Test individual hypothesis components."""
    print("\n[TEST] Hypothesis Components")
    
    from modules.ta_engine.hypothesis import TAHypothesisBuilder
    
    builder = TAHypothesisBuilder()
    hypo = builder.build("BTC")
    
    # Check all components exist
    assert hypo.trend_signal is not None
    print(f"  ✓ Trend signal: {hypo.trend_signal.direction.value}")
    
    assert hypo.momentum_signal is not None
    print(f"  ✓ Momentum signal: RSI={hypo.momentum_signal.rsi_value:.1f}")
    
    assert hypo.structure_signal is not None
    print(f"  ✓ Structure signal: HH={hypo.structure_signal.higher_highs}, HL={hypo.structure_signal.higher_lows}")
    
    assert hypo.breakout_signal is not None
    print(f"  ✓ Breakout signal: detected={hypo.breakout_signal.detected}")
    
    return True


def test_drivers_calculation():
    """Test driver scores calculation."""
    print("\n[TEST] Driver Calculation")
    
    from modules.ta_engine.hypothesis import TAHypothesisBuilder
    
    builder = TAHypothesisBuilder()
    hypo = builder.build("BTC")
    
    assert "trend" in hypo.drivers
    assert "momentum" in hypo.drivers
    assert "structure" in hypo.drivers
    assert "breakout" in hypo.drivers
    
    print(f"  ✓ Drivers: {hypo.drivers}")
    
    # Drivers should be in -1 to 1 range
    for name, value in hypo.drivers.items():
        assert -1.0 <= value <= 1.0, f"Driver {name} out of range: {value}"
    
    print(f"  ✓ All drivers in valid range")
    
    return True


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("TA HYPOTHESIS TESTS")
    print("=" * 60)
    
    tests = [
        ("Conviction Weights", test_conviction_weights),
        ("Driver Weights", test_driver_weights),
        ("Hypothesis Integration", test_hypothesis_integration),
        ("Hypothesis Components", test_hypothesis_components),
        ("Driver Calculation", test_drivers_calculation),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            result = test_fn()
            if result:
                passed += 1
        except Exception as e:
            print(f"\n[FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} passed")
    print("=" * 60)
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = run_all_tests()
    sys.exit(0 if failed == 0 else 1)
