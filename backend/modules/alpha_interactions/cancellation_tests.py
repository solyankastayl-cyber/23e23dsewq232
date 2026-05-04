"""
PHASE 16.5 — Cancellation Engine Tests
=======================================
Tests for cancellation pattern detection.

Cancellation voids trades even with reinforcement/synergy.

Tests:
1. Extreme crowding reversal detected
2. Liquidity trap detected
3. Volatility fake expansion detected
4. Trend exhaustion detected
5. Multiple cancellation patterns reduce reinforcement
6. No cancellation patterns
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_interactions.cancellation_patterns import (
    CancellationPattern,
    CrowdingReversalInput,
    LiquidityTrapInput,
    FakeExpansionInput,
    TrendExhaustionInput,
)

from modules.alpha_interactions.cancellation_engine import (
    CancellationEngine,
    get_cancellation_engine,
)


def test_extreme_crowding_reversal():
    """
    TEST 1: Extreme crowding reversal detected
    """
    print("\n" + "=" * 60)
    print("TEST 1: Extreme Crowding Reversal")
    print("=" * 60)
    
    engine = CancellationEngine()
    
    crowding = CrowdingReversalInput(
        crowding_score=0.85,
        funding_extreme=True,
        funding_direction="LONG_CROWDED",
        leverage_index=0.7,
        open_interest_change=0.3,
    )
    
    liquidity = LiquidityTrapInput(
        flow_direction="NEUTRAL",
        flow_intensity=0.3,
        structure_break_direction="NONE",
        price_rejection=False,
        wick_ratio=0.2,
    )
    
    fake_expansion = FakeExpansionInput(
        volatility_expanding=False,
        volatility_change_rate=0.2,
        volume_spike=True,
        volume_ratio=1.2,
        price_follow_through=True,
    )
    
    exhaustion = TrendExhaustionInput(
        trend_direction="NEUTRAL",
        trend_strength=0.4,
        momentum_divergence=False,
        divergence_strength=0.0,
        rsi_extreme=False,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        crowding=crowding,
        liquidity=liquidity,
        fake_expansion=fake_expansion,
        exhaustion=exhaustion,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Cancellation Strength: {result.cancellation_strength:.4f}")
    print(f"  Modifier: {result.cancellation_modifier:.4f}")
    print(f"  Trade Cancelled: {result.trade_cancelled}")
    
    assert "extreme_crowding_reversal" in result.patterns_detected, \
        f"Expected extreme_crowding_reversal, got {result.patterns_detected}"
    assert result.cancellation_modifier < 1.0, \
        f"Expected modifier < 1.0, got {result.cancellation_modifier}"
    
    print("  ✅ PASSED")
    return True


def test_liquidity_trap():
    """
    TEST 2: Liquidity trap detected
    """
    print("\n" + "=" * 60)
    print("TEST 2: Liquidity Trap")
    print("=" * 60)
    
    engine = CancellationEngine()
    
    crowding = CrowdingReversalInput(
        crowding_score=0.5,
        funding_extreme=False,
        funding_direction="NEUTRAL",
        leverage_index=0.4,
        open_interest_change=0.0,
    )
    
    # Flow BUY but structure BEARISH with rejection
    liquidity = LiquidityTrapInput(
        flow_direction="BUY",
        flow_intensity=0.7,
        structure_break_direction="BEARISH",
        price_rejection=True,
        wick_ratio=0.6,
    )
    
    fake_expansion = FakeExpansionInput(
        volatility_expanding=False,
        volatility_change_rate=0.2,
        volume_spike=True,
        volume_ratio=1.0,
        price_follow_through=True,
    )
    
    exhaustion = TrendExhaustionInput(
        trend_direction="NEUTRAL",
        trend_strength=0.4,
        momentum_divergence=False,
        divergence_strength=0.0,
        rsi_extreme=False,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        crowding=crowding,
        liquidity=liquidity,
        fake_expansion=fake_expansion,
        exhaustion=exhaustion,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Cancellation Strength: {result.cancellation_strength:.4f}")
    print(f"  Modifier: {result.cancellation_modifier:.4f}")
    
    assert "liquidity_trap" in result.patterns_detected, \
        f"Expected liquidity_trap, got {result.patterns_detected}"
    
    print("  ✅ PASSED")
    return True


def test_volatility_fake_expansion():
    """
    TEST 3: Volatility fake expansion detected
    """
    print("\n" + "=" * 60)
    print("TEST 3: Volatility Fake Expansion")
    print("=" * 60)
    
    engine = CancellationEngine()
    
    crowding = CrowdingReversalInput(
        crowding_score=0.5,
        funding_extreme=False,
        funding_direction="NEUTRAL",
        leverage_index=0.4,
        open_interest_change=0.0,
    )
    
    liquidity = LiquidityTrapInput(
        flow_direction="NEUTRAL",
        flow_intensity=0.3,
        structure_break_direction="NONE",
        price_rejection=False,
        wick_ratio=0.2,
    )
    
    # Volatility expanding but NO volume confirmation
    fake_expansion = FakeExpansionInput(
        volatility_expanding=True,
        volatility_change_rate=0.6,
        volume_spike=False,
        volume_ratio=0.6,  # Below average
        price_follow_through=False,
    )
    
    exhaustion = TrendExhaustionInput(
        trend_direction="NEUTRAL",
        trend_strength=0.4,
        momentum_divergence=False,
        divergence_strength=0.0,
        rsi_extreme=False,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        crowding=crowding,
        liquidity=liquidity,
        fake_expansion=fake_expansion,
        exhaustion=exhaustion,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Cancellation Strength: {result.cancellation_strength:.4f}")
    print(f"  Modifier: {result.cancellation_modifier:.4f}")
    
    assert "volatility_fake_expansion" in result.patterns_detected, \
        f"Expected volatility_fake_expansion, got {result.patterns_detected}"
    
    print("  ✅ PASSED")
    return True


def test_trend_exhaustion():
    """
    TEST 4: Trend exhaustion detected
    """
    print("\n" + "=" * 60)
    print("TEST 4: Trend Exhaustion")
    print("=" * 60)
    
    engine = CancellationEngine()
    
    crowding = CrowdingReversalInput(
        crowding_score=0.5,
        funding_extreme=False,
        funding_direction="NEUTRAL",
        leverage_index=0.4,
        open_interest_change=0.0,
    )
    
    liquidity = LiquidityTrapInput(
        flow_direction="NEUTRAL",
        flow_intensity=0.3,
        structure_break_direction="NONE",
        price_rejection=False,
        wick_ratio=0.2,
    )
    
    fake_expansion = FakeExpansionInput(
        volatility_expanding=False,
        volatility_change_rate=0.2,
        volume_spike=True,
        volume_ratio=1.0,
        price_follow_through=True,
    )
    
    # Strong trend with divergence
    exhaustion = TrendExhaustionInput(
        trend_direction="LONG",
        trend_strength=0.85,
        momentum_divergence=True,
        divergence_strength=0.7,
        rsi_extreme=True,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        crowding=crowding,
        liquidity=liquidity,
        fake_expansion=fake_expansion,
        exhaustion=exhaustion,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Cancellation Strength: {result.cancellation_strength:.4f}")
    print(f"  Modifier: {result.cancellation_modifier:.4f}")
    
    assert "trend_exhaustion" in result.patterns_detected, \
        f"Expected trend_exhaustion, got {result.patterns_detected}"
    
    print("  ✅ PASSED")
    return True


def test_multiple_cancellation_patterns():
    """
    TEST 5: Multiple cancellation patterns reduce reinforcement
    """
    print("\n" + "=" * 60)
    print("TEST 5: Multiple Cancellation Patterns")
    print("=" * 60)
    
    engine = CancellationEngine()
    
    # Multiple cancellation signals active
    crowding = CrowdingReversalInput(
        crowding_score=0.85,
        funding_extreme=True,
        funding_direction="LONG_CROWDED",
        leverage_index=0.7,
        open_interest_change=0.2,
    )
    
    liquidity = LiquidityTrapInput(
        flow_direction="BUY",
        flow_intensity=0.65,
        structure_break_direction="BEARISH",
        price_rejection=True,
        wick_ratio=0.55,
    )
    
    fake_expansion = FakeExpansionInput(
        volatility_expanding=True,
        volatility_change_rate=0.5,
        volume_spike=False,
        volume_ratio=0.7,
        price_follow_through=False,
    )
    
    exhaustion = TrendExhaustionInput(
        trend_direction="LONG",
        trend_strength=0.82,
        momentum_divergence=True,
        divergence_strength=0.6,
        rsi_extreme=True,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        crowding=crowding,
        liquidity=liquidity,
        fake_expansion=fake_expansion,
        exhaustion=exhaustion,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Cancellation Strength: {result.cancellation_strength:.4f}")
    print(f"  Modifier: {result.cancellation_modifier:.4f}")
    print(f"  Trade Cancelled: {result.trade_cancelled}")
    print(f"  Dominant: {result.dominant_cancellation}")
    
    assert result.pattern_count >= 3, \
        f"Expected at least 3 cancellation patterns, got {result.pattern_count}"
    assert result.cancellation_modifier <= 0.75, \
        f"Expected modifier <= 0.75 for multiple cancellations, got {result.cancellation_modifier}"
    
    print("  ✅ PASSED")
    return True


def test_no_cancellation_patterns():
    """
    TEST 6: No cancellation patterns
    """
    print("\n" + "=" * 60)
    print("TEST 6: No Cancellation Patterns")
    print("=" * 60)
    
    engine = CancellationEngine()
    
    # All clean, no cancellation
    crowding = CrowdingReversalInput(
        crowding_score=0.4,
        funding_extreme=False,
        funding_direction="NEUTRAL",
        leverage_index=0.3,
        open_interest_change=0.0,
    )
    
    liquidity = LiquidityTrapInput(
        flow_direction="BUY",
        flow_intensity=0.6,
        structure_break_direction="BULLISH",  # Aligned
        price_rejection=False,
        wick_ratio=0.2,
    )
    
    fake_expansion = FakeExpansionInput(
        volatility_expanding=True,
        volatility_change_rate=0.5,
        volume_spike=True,  # Confirmed
        volume_ratio=1.5,
        price_follow_through=True,
    )
    
    exhaustion = TrendExhaustionInput(
        trend_direction="LONG",
        trend_strength=0.6,  # Not extreme
        momentum_divergence=False,
        divergence_strength=0.0,
        rsi_extreme=False,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        crowding=crowding,
        liquidity=liquidity,
        fake_expansion=fake_expansion,
        exhaustion=exhaustion,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Cancellation Strength: {result.cancellation_strength:.4f}")
    print(f"  Modifier: {result.cancellation_modifier:.4f}")
    print(f"  Trade Cancelled: {result.trade_cancelled}")
    
    assert result.pattern_count == 0, \
        f"Expected 0 cancellation patterns, got {result.pattern_count}"
    assert result.cancellation_modifier == 1.0, \
        f"Expected modifier = 1.0 for no cancellation, got {result.cancellation_modifier}"
    assert result.trade_cancelled == False, \
        f"Expected trade_cancelled = False, got {result.trade_cancelled}"
    
    print("  ✅ PASSED")
    return True


def run_all_tests():
    """Run all cancellation engine tests."""
    print("\n" + "=" * 60)
    print("PHASE 16.5 — CANCELLATION ENGINE TESTS")
    print("=" * 60)
    
    tests = [
        ("1. Extreme Crowding Reversal", test_extreme_crowding_reversal),
        ("2. Liquidity Trap", test_liquidity_trap),
        ("3. Volatility Fake Expansion", test_volatility_fake_expansion),
        ("4. Trend Exhaustion", test_trend_exhaustion),
        ("5. Multiple Cancellation Patterns", test_multiple_cancellation_patterns),
        ("6. No Cancellation Patterns", test_no_cancellation_patterns),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} PASSED")
    print("=" * 60)
    
    return passed == len(tests)


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
