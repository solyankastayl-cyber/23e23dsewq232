"""
PHASE 16.3 — Conflict Patterns Tests
=====================================
Tests for conflict pattern detection.

Tests:
1. TA vs Exchange conflict detected
2. Trend vs mean reversion conflict detected
3. Flow vs structure conflict detected
4. Derivatives vs trend conflict detected
5. Multiple conflicts increase severity
6. No conflict patterns
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_interactions.conflict_patterns import (
    ConflictPattern,
    ConflictSeverity,
    TAExchangeConflictInput,
    TrendMeanReversionInput,
    FlowStructureInput,
    DerivativesTrendInput,
)

from modules.alpha_interactions.conflict_patterns_engine import (
    ConflictPatternsEngine,
    get_conflict_patterns_engine,
)


def test_ta_exchange_conflict():
    """
    TEST 1: TA vs Exchange direction conflict detected
    """
    print("\n" + "=" * 60)
    print("TEST 1: TA vs Exchange Direction Conflict")
    print("=" * 60)
    
    engine = ConflictPatternsEngine()
    
    ta_exchange = TAExchangeConflictInput(
        ta_direction="LONG",
        ta_conviction=0.7,
        exchange_bias="BEARISH",
        exchange_confidence=0.65,
    )
    
    trend_reversion = TrendMeanReversionInput(
        trend_state="RANGE",
        trend_strength=0.4,
        mean_reversion_signal=False,
        mean_reversion_strength=0.0,
        rsi_extreme=False,
    )
    
    flow_structure = FlowStructureInput(
        flow_direction="NEUTRAL",
        flow_intensity=0.3,
        structure_break_direction="NONE",
        structure_quality=0.3,
    )
    
    derivatives_trend = DerivativesTrendInput(
        trend_direction="NEUTRAL",
        trend_strength=0.3,
        funding_state="NEUTRAL",
        crowding_risk=0.2,
        leverage_index=0.3,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        ta_exchange=ta_exchange,
        trend_reversion=trend_reversion,
        flow_structure=flow_structure,
        derivatives_trend=derivatives_trend,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Conflict Strength: {result.conflict_strength:.4f}")
    print(f"  Modifier: {result.conflict_modifier:.4f}")
    print(f"  Severity: {result.conflict_severity.value}")
    
    assert "ta_exchange_direction_conflict" in result.patterns_detected, \
        f"Expected ta_exchange_direction_conflict, got {result.patterns_detected}"
    assert result.conflict_modifier < 1.0, \
        f"Expected modifier < 1.0, got {result.conflict_modifier}"
    
    print("  ✅ PASSED")
    return True


def test_trend_mean_reversion_conflict():
    """
    TEST 2: Trend vs mean reversion conflict detected
    """
    print("\n" + "=" * 60)
    print("TEST 2: Trend vs Mean Reversion Conflict")
    print("=" * 60)
    
    engine = ConflictPatternsEngine()
    
    ta_exchange = TAExchangeConflictInput(
        ta_direction="NEUTRAL",
        ta_conviction=0.4,
        exchange_bias="NEUTRAL",
        exchange_confidence=0.4,
    )
    
    trend_reversion = TrendMeanReversionInput(
        trend_state="TREND_UP",
        trend_strength=0.7,
        mean_reversion_signal=True,
        mean_reversion_strength=0.6,
        rsi_extreme=True,
    )
    
    flow_structure = FlowStructureInput(
        flow_direction="NEUTRAL",
        flow_intensity=0.3,
        structure_break_direction="NONE",
        structure_quality=0.3,
    )
    
    derivatives_trend = DerivativesTrendInput(
        trend_direction="NEUTRAL",
        trend_strength=0.3,
        funding_state="NEUTRAL",
        crowding_risk=0.2,
        leverage_index=0.3,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        ta_exchange=ta_exchange,
        trend_reversion=trend_reversion,
        flow_structure=flow_structure,
        derivatives_trend=derivatives_trend,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Conflict Strength: {result.conflict_strength:.4f}")
    print(f"  Modifier: {result.conflict_modifier:.4f}")
    print(f"  Severity: {result.conflict_severity.value}")
    
    assert "trend_vs_mean_reversion" in result.patterns_detected, \
        f"Expected trend_vs_mean_reversion, got {result.patterns_detected}"
    
    print("  ✅ PASSED")
    return True


def test_flow_structure_conflict():
    """
    TEST 3: Flow vs structure conflict detected (liquidity trap)
    """
    print("\n" + "=" * 60)
    print("TEST 3: Flow vs Structure Conflict")
    print("=" * 60)
    
    engine = ConflictPatternsEngine()
    
    ta_exchange = TAExchangeConflictInput(
        ta_direction="NEUTRAL",
        ta_conviction=0.4,
        exchange_bias="NEUTRAL",
        exchange_confidence=0.4,
    )
    
    trend_reversion = TrendMeanReversionInput(
        trend_state="RANGE",
        trend_strength=0.3,
        mean_reversion_signal=False,
        mean_reversion_strength=0.0,
        rsi_extreme=False,
    )
    
    # Flow BUY but structure BEARISH = conflict
    flow_structure = FlowStructureInput(
        flow_direction="BUY",
        flow_intensity=0.7,
        structure_break_direction="BEARISH",
        structure_quality=0.65,
    )
    
    derivatives_trend = DerivativesTrendInput(
        trend_direction="NEUTRAL",
        trend_strength=0.3,
        funding_state="NEUTRAL",
        crowding_risk=0.2,
        leverage_index=0.3,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        ta_exchange=ta_exchange,
        trend_reversion=trend_reversion,
        flow_structure=flow_structure,
        derivatives_trend=derivatives_trend,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Conflict Strength: {result.conflict_strength:.4f}")
    print(f"  Modifier: {result.conflict_modifier:.4f}")
    print(f"  Severity: {result.conflict_severity.value}")
    
    assert "flow_vs_structure_conflict" in result.patterns_detected, \
        f"Expected flow_vs_structure_conflict, got {result.patterns_detected}"
    
    print("  ✅ PASSED")
    return True


def test_derivatives_trend_conflict():
    """
    TEST 4: Derivatives vs trend conflict detected (crowding)
    """
    print("\n" + "=" * 60)
    print("TEST 4: Derivatives vs Trend Conflict")
    print("=" * 60)
    
    engine = ConflictPatternsEngine()
    
    ta_exchange = TAExchangeConflictInput(
        ta_direction="NEUTRAL",
        ta_conviction=0.4,
        exchange_bias="NEUTRAL",
        exchange_confidence=0.4,
    )
    
    trend_reversion = TrendMeanReversionInput(
        trend_state="RANGE",
        trend_strength=0.3,
        mean_reversion_signal=False,
        mean_reversion_strength=0.0,
        rsi_extreme=False,
    )
    
    flow_structure = FlowStructureInput(
        flow_direction="NEUTRAL",
        flow_intensity=0.3,
        structure_break_direction="NONE",
        structure_quality=0.3,
    )
    
    # Trend LONG but market is LONG_CROWDED = dangerous
    derivatives_trend = DerivativesTrendInput(
        trend_direction="LONG",
        trend_strength=0.65,
        funding_state="EXTREME_LONG",
        crowding_risk=0.75,
        leverage_index=0.7,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        ta_exchange=ta_exchange,
        trend_reversion=trend_reversion,
        flow_structure=flow_structure,
        derivatives_trend=derivatives_trend,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Conflict Strength: {result.conflict_strength:.4f}")
    print(f"  Modifier: {result.conflict_modifier:.4f}")
    print(f"  Severity: {result.conflict_severity.value}")
    
    assert "derivatives_vs_trend_conflict" in result.patterns_detected, \
        f"Expected derivatives_vs_trend_conflict, got {result.patterns_detected}"
    # Derivatives conflict should be HIGH danger
    conflict_result = [p for p in result.pattern_results if p.pattern_name == "derivatives_vs_trend_conflict"][0]
    assert conflict_result.danger_level == "HIGH", \
        f"Expected HIGH danger for derivatives conflict, got {conflict_result.danger_level}"
    
    print("  ✅ PASSED")
    return True


def test_multiple_conflicts_increase_severity():
    """
    TEST 5: Multiple conflicts increase severity
    """
    print("\n" + "=" * 60)
    print("TEST 5: Multiple Conflicts Increase Severity")
    print("=" * 60)
    
    engine = ConflictPatternsEngine()
    
    # Multiple conflicts active
    ta_exchange = TAExchangeConflictInput(
        ta_direction="LONG",
        ta_conviction=0.7,
        exchange_bias="BEARISH",
        exchange_confidence=0.7,
    )
    
    trend_reversion = TrendMeanReversionInput(
        trend_state="TREND_UP",
        trend_strength=0.7,
        mean_reversion_signal=True,
        mean_reversion_strength=0.6,
        rsi_extreme=True,
    )
    
    flow_structure = FlowStructureInput(
        flow_direction="BUY",
        flow_intensity=0.65,
        structure_break_direction="BEARISH",
        structure_quality=0.6,
    )
    
    derivatives_trend = DerivativesTrendInput(
        trend_direction="LONG",
        trend_strength=0.65,
        funding_state="LONG_CROWDED",
        crowding_risk=0.65,
        leverage_index=0.6,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        ta_exchange=ta_exchange,
        trend_reversion=trend_reversion,
        flow_structure=flow_structure,
        derivatives_trend=derivatives_trend,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Conflict Strength: {result.conflict_strength:.4f}")
    print(f"  Modifier: {result.conflict_modifier:.4f}")
    print(f"  Severity: {result.conflict_severity.value}")
    print(f"  Dominant Conflict: {result.dominant_conflict}")
    
    assert result.pattern_count >= 3, \
        f"Expected at least 3 conflicts, got {result.pattern_count}"
    assert result.conflict_modifier <= 0.85, \
        f"Expected modifier <= 0.85 for multiple conflicts, got {result.conflict_modifier}"
    assert result.conflict_severity in [ConflictSeverity.HIGH_CONFLICT, ConflictSeverity.MEDIUM_CONFLICT], \
        f"Expected HIGH or MEDIUM severity, got {result.conflict_severity}"
    
    print("  ✅ PASSED")
    return True


def test_no_conflict_patterns():
    """
    TEST 6: No conflict patterns
    """
    print("\n" + "=" * 60)
    print("TEST 6: No Conflict Patterns")
    print("=" * 60)
    
    engine = ConflictPatternsEngine()
    
    # All aligned, no conflicts
    ta_exchange = TAExchangeConflictInput(
        ta_direction="LONG",
        ta_conviction=0.7,
        exchange_bias="BULLISH",  # Same direction
        exchange_confidence=0.7,
    )
    
    trend_reversion = TrendMeanReversionInput(
        trend_state="TREND_UP",
        trend_strength=0.7,
        mean_reversion_signal=False,  # No reversion signal
        mean_reversion_strength=0.0,
        rsi_extreme=False,
    )
    
    flow_structure = FlowStructureInput(
        flow_direction="BUY",
        flow_intensity=0.7,
        structure_break_direction="BULLISH",  # Aligned
        structure_quality=0.7,
    )
    
    derivatives_trend = DerivativesTrendInput(
        trend_direction="LONG",
        trend_strength=0.7,
        funding_state="NEUTRAL",  # No crowding
        crowding_risk=0.2,
        leverage_index=0.3,
    )
    
    result = engine.analyze_from_inputs(
        symbol="BTC",
        ta_exchange=ta_exchange,
        trend_reversion=trend_reversion,
        flow_structure=flow_structure,
        derivatives_trend=derivatives_trend,
    )
    
    print(f"  Patterns Detected: {result.patterns_detected}")
    print(f"  Pattern Count: {result.pattern_count}")
    print(f"  Conflict Strength: {result.conflict_strength:.4f}")
    print(f"  Modifier: {result.conflict_modifier:.4f}")
    print(f"  Severity: {result.conflict_severity.value}")
    
    assert result.pattern_count == 0, \
        f"Expected 0 conflicts, got {result.pattern_count}"
    assert result.conflict_modifier == 1.0, \
        f"Expected modifier = 1.0 for no conflicts, got {result.conflict_modifier}"
    assert result.conflict_severity == ConflictSeverity.LOW_CONFLICT, \
        f"Expected LOW_CONFLICT severity, got {result.conflict_severity}"
    
    print("  ✅ PASSED")
    return True


def run_all_tests():
    """Run all conflict patterns tests."""
    print("\n" + "=" * 60)
    print("PHASE 16.3 — CONFLICT PATTERNS TESTS")
    print("=" * 60)
    
    tests = [
        ("1. TA vs Exchange Conflict", test_ta_exchange_conflict),
        ("2. Trend vs Mean Reversion", test_trend_mean_reversion_conflict),
        ("3. Flow vs Structure Conflict", test_flow_structure_conflict),
        ("4. Derivatives vs Trend Conflict", test_derivatives_trend_conflict),
        ("5. Multiple Conflicts Increase", test_multiple_conflicts_increase_severity),
        ("6. No Conflict Patterns", test_no_conflict_patterns),
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
