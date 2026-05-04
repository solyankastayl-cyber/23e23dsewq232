"""
PHASE 16.2 — Reinforcement Patterns Tests
==========================================
Tests for reinforcement pattern detection.

Tests:
1. Trend + Momentum alignment detected
2. Breakout + Volatility expansion detected
3. Flow + Squeeze detected
4. Trend + Structure break detected
5. Multiple patterns increase reinforcement
6. No patterns → neutral
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_interactions.reinforcement_patterns import (
    ReinforcementPattern,
    TrendMomentumInput,
    BreakoutVolatilityInput,
    FlowSqueezeInput,
    TrendStructureInput,
)

from modules.alpha_interactions.reinforcement_patterns_engine import (
    ReinforcementPatternsEngine,
    get_reinforcement_patterns_engine,
)


def test_trend_momentum_alignment():
    """
    TEST 1: Trend + Momentum alignment detected
    """
    print("\n" + "=" * 60)
    print("TEST 1: Trend + Momentum Alignment")
    print("=" * 60)
    
    engine = ReinforcementPatternsEngine()
    
    trend_momentum = TrendMomentumInput(
        trend_direction="LONG",
        trend_strength=0.75,
        momentum_direction="LONG",
        momentum_strength=0.65,
    )
    
    breakout_volatility = BreakoutVolatilityInput(
        breakout_detected=False,
        breakout_direction="NEUTRAL",
        breakout_strength=0.0,
        volatility_state="NORMAL",
        volatility_expansion_rate=0.2,
    )
    
    flow_squeeze = FlowSqueezeInput(
        flow_direction="NEUTRAL",
        flow_intensity=0.3,
        squeeze_probability=0.2,
        squeeze_type="NONE",
    )
    
    trend_structure = TrendStructureInput(
        trend_direction="LONG",
        trend_strength=0.7,
        structure_break_detected=False,
        structure_break_direction="NONE",
        structure_quality=0.4,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        trend_momentum=trend_momentum,
        breakout_volatility=breakout_volatility,
        flow_squeeze=flow_squeeze,
        trend_structure=trend_structure,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Reinforcement Strength: {result.reinforcement_strength:.4f}")
    print(f"  Modifier: {result.reinforcement_modifier:.4f}")
    
    assert "trend_momentum_alignment" in result.patterns_detected, \
        f"Expected trend_momentum_alignment, got {result.patterns_detected}"
    assert result.pattern_count >= 1, \
        f"Expected at least 1 pattern, got {result.pattern_count}"
    assert result.reinforcement_modifier >= 1.03, \
        f"Expected modifier >= 1.03, got {result.reinforcement_modifier}"
    
    print("  ✅ PASSED")
    return True


def test_breakout_volatility_expansion():
    """
    TEST 2: Breakout + Volatility expansion detected
    """
    print("\n" + "=" * 60)
    print("TEST 2: Breakout + Volatility Expansion")
    print("=" * 60)
    
    engine = ReinforcementPatternsEngine()
    
    trend_momentum = TrendMomentumInput(
        trend_direction="NEUTRAL",
        trend_strength=0.4,
        momentum_direction="NEUTRAL",
        momentum_strength=0.4,
    )
    
    breakout_volatility = BreakoutVolatilityInput(
        breakout_detected=True,
        breakout_direction="LONG",
        breakout_strength=0.7,
        volatility_state="EXPANDING",
        volatility_expansion_rate=0.6,
    )
    
    flow_squeeze = FlowSqueezeInput(
        flow_direction="NEUTRAL",
        flow_intensity=0.3,
        squeeze_probability=0.2,
        squeeze_type="NONE",
    )
    
    trend_structure = TrendStructureInput(
        trend_direction="NEUTRAL",
        trend_strength=0.4,
        structure_break_detected=False,
        structure_break_direction="NONE",
        structure_quality=0.3,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        trend_momentum=trend_momentum,
        breakout_volatility=breakout_volatility,
        flow_squeeze=flow_squeeze,
        trend_structure=trend_structure,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Reinforcement Strength: {result.reinforcement_strength:.4f}")
    print(f"  Modifier: {result.reinforcement_modifier:.4f}")
    
    assert "breakout_volatility_expansion" in result.patterns_detected, \
        f"Expected breakout_volatility_expansion, got {result.patterns_detected}"
    
    print("  ✅ PASSED")
    return True


def test_flow_squeeze_alignment():
    """
    TEST 3: Flow + Squeeze alignment detected
    """
    print("\n" + "=" * 60)
    print("TEST 3: Flow + Squeeze Alignment")
    print("=" * 60)
    
    engine = ReinforcementPatternsEngine()
    
    trend_momentum = TrendMomentumInput(
        trend_direction="NEUTRAL",
        trend_strength=0.4,
        momentum_direction="NEUTRAL",
        momentum_strength=0.4,
    )
    
    breakout_volatility = BreakoutVolatilityInput(
        breakout_detected=False,
        breakout_direction="NEUTRAL",
        breakout_strength=0.0,
        volatility_state="NORMAL",
        volatility_expansion_rate=0.3,
    )
    
    flow_squeeze = FlowSqueezeInput(
        flow_direction="BUY",
        flow_intensity=0.7,
        squeeze_probability=0.65,
        squeeze_type="SHORT_SQUEEZE",
    )
    
    trend_structure = TrendStructureInput(
        trend_direction="NEUTRAL",
        trend_strength=0.4,
        structure_break_detected=False,
        structure_break_direction="NONE",
        structure_quality=0.3,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        trend_momentum=trend_momentum,
        breakout_volatility=breakout_volatility,
        flow_squeeze=flow_squeeze,
        trend_structure=trend_structure,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Reinforcement Strength: {result.reinforcement_strength:.4f}")
    print(f"  Modifier: {result.reinforcement_modifier:.4f}")
    
    assert "flow_squeeze_alignment" in result.patterns_detected, \
        f"Expected flow_squeeze_alignment, got {result.patterns_detected}"
    
    print("  ✅ PASSED")
    return True


def test_trend_structure_break():
    """
    TEST 4: Trend + Structure break detected
    """
    print("\n" + "=" * 60)
    print("TEST 4: Trend + Structure Break")
    print("=" * 60)
    
    engine = ReinforcementPatternsEngine()
    
    trend_momentum = TrendMomentumInput(
        trend_direction="LONG",
        trend_strength=0.4,  # Below threshold
        momentum_direction="NEUTRAL",
        momentum_strength=0.3,
    )
    
    breakout_volatility = BreakoutVolatilityInput(
        breakout_detected=False,
        breakout_direction="NEUTRAL",
        breakout_strength=0.0,
        volatility_state="NORMAL",
        volatility_expansion_rate=0.3,
    )
    
    flow_squeeze = FlowSqueezeInput(
        flow_direction="NEUTRAL",
        flow_intensity=0.3,
        squeeze_probability=0.2,
        squeeze_type="NONE",
    )
    
    trend_structure = TrendStructureInput(
        trend_direction="LONG",
        trend_strength=0.65,
        structure_break_detected=True,
        structure_break_direction="BULLISH",
        structure_quality=0.7,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        trend_momentum=trend_momentum,
        breakout_volatility=breakout_volatility,
        flow_squeeze=flow_squeeze,
        trend_structure=trend_structure,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Reinforcement Strength: {result.reinforcement_strength:.4f}")
    print(f"  Modifier: {result.reinforcement_modifier:.4f}")
    
    assert "trend_structure_break" in result.patterns_detected, \
        f"Expected trend_structure_break, got {result.patterns_detected}"
    
    print("  ✅ PASSED")
    return True


def test_multiple_patterns_increase_reinforcement():
    """
    TEST 5: Multiple patterns increase reinforcement
    """
    print("\n" + "=" * 60)
    print("TEST 5: Multiple Patterns Increase Reinforcement")
    print("=" * 60)
    
    engine = ReinforcementPatternsEngine()
    
    # Setup with multiple patterns active
    trend_momentum = TrendMomentumInput(
        trend_direction="LONG",
        trend_strength=0.75,
        momentum_direction="LONG",
        momentum_strength=0.7,
    )
    
    breakout_volatility = BreakoutVolatilityInput(
        breakout_detected=True,
        breakout_direction="LONG",
        breakout_strength=0.65,
        volatility_state="EXPANDING",
        volatility_expansion_rate=0.55,
    )
    
    flow_squeeze = FlowSqueezeInput(
        flow_direction="BUY",
        flow_intensity=0.65,
        squeeze_probability=0.6,
        squeeze_type="SHORT_SQUEEZE",
    )
    
    trend_structure = TrendStructureInput(
        trend_direction="LONG",
        trend_strength=0.7,
        structure_break_detected=True,
        structure_break_direction="BULLISH",
        structure_quality=0.65,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        trend_momentum=trend_momentum,
        breakout_volatility=breakout_volatility,
        flow_squeeze=flow_squeeze,
        trend_structure=trend_structure,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Reinforcement Strength: {result.reinforcement_strength:.4f}")
    print(f"  Modifier: {result.reinforcement_modifier:.4f}")
    print(f"  Dominant Pattern: {result.dominant_pattern}")
    
    # Multiple patterns should give higher modifier
    assert result.pattern_count >= 3, \
        f"Expected at least 3 patterns, got {result.pattern_count}"
    assert result.reinforcement_modifier >= 1.10, \
        f"Expected modifier >= 1.10 for multiple patterns, got {result.reinforcement_modifier}"
    assert result.reinforcement_strength >= 0.5, \
        f"Expected strength >= 0.5 for multiple patterns, got {result.reinforcement_strength}"
    
    print("  ✅ PASSED")
    return True


def test_no_patterns_neutral():
    """
    TEST 6: No patterns → neutral
    """
    print("\n" + "=" * 60)
    print("TEST 6: No Patterns → Neutral")
    print("=" * 60)
    
    engine = ReinforcementPatternsEngine()
    
    # Weak signals, no patterns should trigger
    trend_momentum = TrendMomentumInput(
        trend_direction="NEUTRAL",
        trend_strength=0.3,
        momentum_direction="SHORT",  # Opposite
        momentum_strength=0.3,
    )
    
    breakout_volatility = BreakoutVolatilityInput(
        breakout_detected=False,
        breakout_direction="NEUTRAL",
        breakout_strength=0.0,
        volatility_state="LOW",
        volatility_expansion_rate=0.1,
    )
    
    flow_squeeze = FlowSqueezeInput(
        flow_direction="NEUTRAL",
        flow_intensity=0.2,
        squeeze_probability=0.1,
        squeeze_type="NONE",
    )
    
    trend_structure = TrendStructureInput(
        trend_direction="NEUTRAL",
        trend_strength=0.3,
        structure_break_detected=False,
        structure_break_direction="NONE",
        structure_quality=0.2,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        trend_momentum=trend_momentum,
        breakout_volatility=breakout_volatility,
        flow_squeeze=flow_squeeze,
        trend_structure=trend_structure,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Reinforcement Strength: {result.reinforcement_strength:.4f}")
    print(f"  Modifier: {result.reinforcement_modifier:.4f}")
    
    # No patterns = neutral modifier
    assert result.pattern_count == 0, \
        f"Expected 0 patterns, got {result.pattern_count}"
    assert result.reinforcement_modifier == 1.0, \
        f"Expected modifier = 1.0 for no patterns, got {result.reinforcement_modifier}"
    assert result.reinforcement_strength == 0.0, \
        f"Expected strength = 0 for no patterns, got {result.reinforcement_strength}"
    
    print("  ✅ PASSED")
    return True


def run_all_tests():
    """Run all reinforcement patterns tests."""
    print("\n" + "=" * 60)
    print("PHASE 16.2 — REINFORCEMENT PATTERNS TESTS")
    print("=" * 60)
    
    tests = [
        ("1. Trend + Momentum Alignment", test_trend_momentum_alignment),
        ("2. Breakout + Volatility Expansion", test_breakout_volatility_expansion),
        ("3. Flow + Squeeze Alignment", test_flow_squeeze_alignment),
        ("4. Trend + Structure Break", test_trend_structure_break),
        ("5. Multiple Patterns Increase", test_multiple_patterns_increase_reinforcement),
        ("6. No Patterns → Neutral", test_no_patterns_neutral),
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
