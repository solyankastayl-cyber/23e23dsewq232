"""
PHASE 16.4 — Synergy Engine Tests
==================================
Tests for synergy pattern detection.

Synergy creates emergent edge from signal combinations.

Tests:
1. Trend + Compression + Breakout synergy
2. Flow + Liquidation Cascade synergy
3. Volatility Expansion + Trend synergy
4. Structure Break + Momentum synergy
5. Multiple synergy patterns increase modifier
6. No synergy patterns
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_interactions.synergy_patterns import (
    SynergyPattern,
    TrendCompressionInput,
    FlowLiquidationInput,
    VolatilityTrendInput,
    StructureMomentumInput,
)

from modules.alpha_interactions.synergy_engine import (
    SynergyEngine,
    get_synergy_engine,
)


def test_trend_compression_breakout():
    """
    TEST 1: Trend + Compression + Breakout synergy
    Classic volatility expansion setup.
    """
    print("\n" + "=" * 60)
    print("TEST 1: Trend + Compression + Breakout")
    print("=" * 60)
    
    engine = SynergyEngine()
    
    trend_compression = TrendCompressionInput(
        trend_direction="LONG",
        trend_strength=0.7,
        volatility_state="LOW_VOL",
        volatility_percentile=0.2,  # Compressed
        breakout_detected=True,
        breakout_strength=0.6,
    )
    
    flow_liquidation = FlowLiquidationInput(
        flow_direction="NEUTRAL",
        flow_intensity=0.3,
        liquidation_risk=0.2,
        liquidation_direction="NONE",
        leverage_index=0.3,
    )
    
    volatility_trend = VolatilityTrendInput(
        volatility_state="LOW_VOL",
        volatility_change_rate=0.1,
        trend_direction="LONG",
        trend_strength=0.7,
        regime="RANGE",
    )
    
    structure_momentum = StructureMomentumInput(
        structure_break_detected=False,
        structure_break_direction="NONE",
        structure_quality=0.4,
        momentum_direction="NEUTRAL",
        momentum_strength=0.4,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        trend_compression=trend_compression,
        flow_liquidation=flow_liquidation,
        volatility_trend=volatility_trend,
        structure_momentum=structure_momentum,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Synergy Strength: {result.synergy_strength:.4f}")
    print(f"  Synergy Modifier: {result.synergy_modifier:.4f}")
    print(f"  Synergy Potential: {result.synergy_potential}")
    
    assert "trend_compression_breakout" in result.patterns_detected, \
        f"Expected trend_compression_breakout, got {result.patterns_detected}"
    assert result.synergy_modifier >= 1.05, \
        f"Expected modifier >= 1.05, got {result.synergy_modifier}"
    
    print("  ✅ PASSED")
    return True


def test_flow_liquidation_cascade():
    """
    TEST 2: Flow + Liquidation Cascade synergy
    Cascade move setup.
    """
    print("\n" + "=" * 60)
    print("TEST 2: Flow + Liquidation Cascade")
    print("=" * 60)
    
    engine = SynergyEngine()
    
    trend_compression = TrendCompressionInput(
        trend_direction="NEUTRAL",
        trend_strength=0.4,
        volatility_state="NORMAL",
        volatility_percentile=0.5,
        breakout_detected=False,
        breakout_strength=0.0,
    )
    
    # Strong buy flow with short liquidation risk
    flow_liquidation = FlowLiquidationInput(
        flow_direction="BUY",
        flow_intensity=0.7,
        liquidation_risk=0.65,
        liquidation_direction="SHORT_LIQUIDATION",
        leverage_index=0.6,
    )
    
    volatility_trend = VolatilityTrendInput(
        volatility_state="NORMAL",
        volatility_change_rate=0.2,
        trend_direction="NEUTRAL",
        trend_strength=0.4,
        regime="RANGE",
    )
    
    structure_momentum = StructureMomentumInput(
        structure_break_detected=False,
        structure_break_direction="NONE",
        structure_quality=0.4,
        momentum_direction="NEUTRAL",
        momentum_strength=0.4,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        trend_compression=trend_compression,
        flow_liquidation=flow_liquidation,
        volatility_trend=volatility_trend,
        structure_momentum=structure_momentum,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Synergy Strength: {result.synergy_strength:.4f}")
    print(f"  Synergy Modifier: {result.synergy_modifier:.4f}")
    print(f"  Synergy Potential: {result.synergy_potential}")
    
    assert "flow_liquidation_cascade" in result.patterns_detected, \
        f"Expected flow_liquidation_cascade, got {result.patterns_detected}"
    
    print("  ✅ PASSED")
    return True


def test_volatility_expansion_trend():
    """
    TEST 3: Volatility Expansion + Trend synergy
    Trend acceleration setup.
    """
    print("\n" + "=" * 60)
    print("TEST 3: Volatility Expansion + Trend")
    print("=" * 60)
    
    engine = SynergyEngine()
    
    trend_compression = TrendCompressionInput(
        trend_direction="LONG",
        trend_strength=0.5,
        volatility_state="EXPANDING",
        volatility_percentile=0.6,
        breakout_detected=False,
        breakout_strength=0.0,
    )
    
    flow_liquidation = FlowLiquidationInput(
        flow_direction="NEUTRAL",
        flow_intensity=0.3,
        liquidation_risk=0.2,
        liquidation_direction="NONE",
        leverage_index=0.3,
    )
    
    # Volatility expanding with trend
    volatility_trend = VolatilityTrendInput(
        volatility_state="EXPANDING",
        volatility_change_rate=0.6,
        trend_direction="LONG",
        trend_strength=0.6,
        regime="TREND_UP",
    )
    
    structure_momentum = StructureMomentumInput(
        structure_break_detected=False,
        structure_break_direction="NONE",
        structure_quality=0.4,
        momentum_direction="NEUTRAL",
        momentum_strength=0.4,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        trend_compression=trend_compression,
        flow_liquidation=flow_liquidation,
        volatility_trend=volatility_trend,
        structure_momentum=structure_momentum,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Synergy Strength: {result.synergy_strength:.4f}")
    print(f"  Synergy Modifier: {result.synergy_modifier:.4f}")
    print(f"  Synergy Potential: {result.synergy_potential}")
    
    assert "volatility_expansion_trend" in result.patterns_detected, \
        f"Expected volatility_expansion_trend, got {result.patterns_detected}"
    
    print("  ✅ PASSED")
    return True


def test_structure_break_momentum():
    """
    TEST 4: Structure Break + Momentum synergy
    Strong continuation setup.
    """
    print("\n" + "=" * 60)
    print("TEST 4: Structure Break + Momentum")
    print("=" * 60)
    
    engine = SynergyEngine()
    
    trend_compression = TrendCompressionInput(
        trend_direction="NEUTRAL",
        trend_strength=0.4,
        volatility_state="NORMAL",
        volatility_percentile=0.5,
        breakout_detected=False,
        breakout_strength=0.0,
    )
    
    flow_liquidation = FlowLiquidationInput(
        flow_direction="NEUTRAL",
        flow_intensity=0.3,
        liquidation_risk=0.2,
        liquidation_direction="NONE",
        leverage_index=0.3,
    )
    
    volatility_trend = VolatilityTrendInput(
        volatility_state="NORMAL",
        volatility_change_rate=0.2,
        trend_direction="NEUTRAL",
        trend_strength=0.4,
        regime="RANGE",
    )
    
    # Bullish structure break + long momentum
    structure_momentum = StructureMomentumInput(
        structure_break_detected=True,
        structure_break_direction="BULLISH",
        structure_quality=0.7,
        momentum_direction="LONG",
        momentum_strength=0.65,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        trend_compression=trend_compression,
        flow_liquidation=flow_liquidation,
        volatility_trend=volatility_trend,
        structure_momentum=structure_momentum,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Synergy Strength: {result.synergy_strength:.4f}")
    print(f"  Synergy Modifier: {result.synergy_modifier:.4f}")
    print(f"  Synergy Potential: {result.synergy_potential}")
    
    assert "structure_break_momentum" in result.patterns_detected, \
        f"Expected structure_break_momentum, got {result.patterns_detected}"
    
    print("  ✅ PASSED")
    return True


def test_multiple_synergy_patterns():
    """
    TEST 5: Multiple synergy patterns increase modifier
    """
    print("\n" + "=" * 60)
    print("TEST 5: Multiple Synergy Patterns")
    print("=" * 60)
    
    engine = SynergyEngine()
    
    # All synergy conditions active
    trend_compression = TrendCompressionInput(
        trend_direction="LONG",
        trend_strength=0.7,
        volatility_state="LOW_VOL",
        volatility_percentile=0.2,
        breakout_detected=True,
        breakout_strength=0.6,
    )
    
    flow_liquidation = FlowLiquidationInput(
        flow_direction="BUY",
        flow_intensity=0.65,
        liquidation_risk=0.6,
        liquidation_direction="SHORT_LIQUIDATION",
        leverage_index=0.5,
    )
    
    volatility_trend = VolatilityTrendInput(
        volatility_state="EXPANDING",
        volatility_change_rate=0.5,
        trend_direction="LONG",
        trend_strength=0.65,
        regime="TREND_UP",
    )
    
    structure_momentum = StructureMomentumInput(
        structure_break_detected=True,
        structure_break_direction="BULLISH",
        structure_quality=0.65,
        momentum_direction="LONG",
        momentum_strength=0.6,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        trend_compression=trend_compression,
        flow_liquidation=flow_liquidation,
        volatility_trend=volatility_trend,
        structure_momentum=structure_momentum,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Synergy Strength: {result.synergy_strength:.4f}")
    print(f"  Synergy Modifier: {result.synergy_modifier:.4f}")
    print(f"  Synergy Potential: {result.synergy_potential}")
    print(f"  Dominant Synergy: {result.dominant_synergy}")
    
    assert result.pattern_count >= 3, \
        f"Expected at least 3 synergy patterns, got {result.pattern_count}"
    assert result.synergy_modifier >= 1.10, \
        f"Expected modifier >= 1.10 for multiple synergies, got {result.synergy_modifier}"
    assert result.synergy_potential in ["HIGH", "EXPLOSIVE"], \
        f"Expected HIGH or EXPLOSIVE potential, got {result.synergy_potential}"
    
    print("  ✅ PASSED")
    return True


def test_no_synergy_patterns():
    """
    TEST 6: No synergy patterns
    """
    print("\n" + "=" * 60)
    print("TEST 6: No Synergy Patterns")
    print("=" * 60)
    
    engine = SynergyEngine()
    
    # All weak, no synergy
    trend_compression = TrendCompressionInput(
        trend_direction="NEUTRAL",
        trend_strength=0.3,
        volatility_state="NORMAL",
        volatility_percentile=0.5,
        breakout_detected=False,
        breakout_strength=0.0,
    )
    
    flow_liquidation = FlowLiquidationInput(
        flow_direction="NEUTRAL",
        flow_intensity=0.2,
        liquidation_risk=0.2,
        liquidation_direction="NONE",
        leverage_index=0.2,
    )
    
    volatility_trend = VolatilityTrendInput(
        volatility_state="LOW_VOL",
        volatility_change_rate=0.1,
        trend_direction="NEUTRAL",
        trend_strength=0.3,
        regime="RANGE",
    )
    
    structure_momentum = StructureMomentumInput(
        structure_break_detected=False,
        structure_break_direction="NONE",
        structure_quality=0.3,
        momentum_direction="NEUTRAL",
        momentum_strength=0.3,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        trend_compression=trend_compression,
        flow_liquidation=flow_liquidation,
        volatility_trend=volatility_trend,
        structure_momentum=structure_momentum,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Synergy Strength: {result.synergy_strength:.4f}")
    print(f"  Synergy Modifier: {result.synergy_modifier:.4f}")
    print(f"  Synergy Potential: {result.synergy_potential}")
    
    assert result.pattern_count == 0, \
        f"Expected 0 synergy patterns, got {result.pattern_count}"
    assert result.synergy_modifier == 1.0, \
        f"Expected modifier = 1.0 for no synergy, got {result.synergy_modifier}"
    assert result.synergy_potential == "LOW", \
        f"Expected LOW potential, got {result.synergy_potential}"
    
    print("  ✅ PASSED")
    return True


def run_all_tests():
    """Run all synergy engine tests."""
    print("\n" + "=" * 60)
    print("PHASE 16.4 — SYNERGY ENGINE TESTS")
    print("=" * 60)
    
    tests = [
        ("1. Trend + Compression + Breakout", test_trend_compression_breakout),
        ("2. Flow + Liquidation Cascade", test_flow_liquidation_cascade),
        ("3. Volatility Expansion + Trend", test_volatility_expansion_trend),
        ("4. Structure Break + Momentum", test_structure_break_momentum),
        ("5. Multiple Synergy Patterns", test_multiple_synergy_patterns),
        ("6. No Synergy Patterns", test_no_synergy_patterns),
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
