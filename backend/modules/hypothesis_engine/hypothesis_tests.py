"""
Hypothesis Engine — Tests

PHASE 29.1 — Hypothesis Contract + Core Engine Tests

Minimum 18 tests:
1.  hypothesis generation
2.  bullish continuation detection
3.  bearish continuation detection
4.  breakout forming detection
5.  range mean reversion detection
6.  no edge fallback
7.  raw score calculation
8.  confidence calculation
9.  reliability calculation
10. execution state mapping
11. candidate selection
12. hypothesis endpoint (current)
13. history endpoint
14. summary endpoint
15. recompute endpoint
16. integration alpha
17. integration regime
18. integration microstructure
"""

import math
import pytest

from .hypothesis_engine import (
    HypothesisEngine,
    get_hypothesis_engine,
)
from .hypothesis_types import (
    HypothesisCandidate,
    HypothesisInputLayers,
    MarketHypothesis,
    WEIGHT_ALPHA,
    WEIGHT_REGIME,
    WEIGHT_MICROSTRUCTURE,
    WEIGHT_MACRO,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Get fresh engine instance."""
    return HypothesisEngine()


# ══════════════════════════════════════════════════════════════
# Test 1: Hypothesis Generation
# ══════════════════════════════════════════════════════════════

def test_hypothesis_generation(engine):
    """Test 1: hypothesis generation produces a valid MarketHypothesis."""
    layers = HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.7,
        regime_type="TRENDING",
        regime_confidence=0.65,
        microstructure_state="NEUTRAL",
        microstructure_confidence=0.6,
        macro_confidence=0.55,
    )

    hypothesis = engine.generate_hypothesis("BTC", layers)

    assert isinstance(hypothesis, MarketHypothesis)
    assert hypothesis.symbol == "BTC"
    assert hypothesis.hypothesis_type in (
        "BULLISH_CONTINUATION", "BEARISH_CONTINUATION",
        "BREAKOUT_FORMING", "RANGE_MEAN_REVERSION", "NO_EDGE",
        "BREAKOUT_FAILURE_RISK", "SHORT_SQUEEZE_SETUP",
        "LONG_SQUEEZE_SETUP", "VOLATILE_UNWIND",
    )
    assert hypothesis.directional_bias in ("LONG", "SHORT", "NEUTRAL")
    assert 0.0 <= hypothesis.confidence <= 1.0
    assert 0.0 <= hypothesis.reliability <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 2: Bullish Continuation Detection
# ══════════════════════════════════════════════════════════════

def test_bullish_continuation_detection(engine):
    """Test 2: bullish continuation correctly detected."""
    layers = HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.8,
        regime_type="TRENDING",
        regime_confidence=0.75,
        microstructure_state="SUPPORTIVE",
        microstructure_confidence=0.7,
        macro_confidence=0.6,
    )

    hypothesis = engine.generate_hypothesis("BTC", layers)

    assert hypothesis.hypothesis_type == "BULLISH_CONTINUATION"
    assert hypothesis.directional_bias == "LONG"


# ══════════════════════════════════════════════════════════════
# Test 3: Bearish Continuation Detection
# ══════════════════════════════════════════════════════════════

def test_bearish_continuation_detection(engine):
    """Test 3: bearish continuation correctly detected."""
    layers = HypothesisInputLayers(
        alpha_direction="BEARISH",
        alpha_strength=0.75,
        regime_type="TRENDING",
        regime_confidence=0.7,
        microstructure_state="FRAGILE",
        microstructure_confidence=0.55,
        macro_confidence=0.5,
    )

    hypothesis = engine.generate_hypothesis("BTC", layers)

    assert hypothesis.hypothesis_type == "BEARISH_CONTINUATION"
    assert hypothesis.directional_bias == "SHORT"


# ══════════════════════════════════════════════════════════════
# Test 4: Breakout Forming Detection
# ══════════════════════════════════════════════════════════════

def test_breakout_forming_detection(engine):
    """Test 4: breakout forming correctly detected."""
    layers = HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.6,
        alpha_breakout_strength=0.75,
        regime_type="TRENDING",
        regime_confidence=0.65,
        regime_in_transition=False,
        microstructure_state="NEUTRAL",
        microstructure_confidence=0.6,
        vacuum_direction="UP",
        pressure_directional=True,
        pressure_direction="UP",
        macro_confidence=0.55,
    )

    hypothesis = engine.generate_hypothesis("BTC", layers)

    # Should be either BULLISH_CONTINUATION or BREAKOUT_FORMING
    # depending on which scores higher
    assert hypothesis.hypothesis_type in ("BULLISH_CONTINUATION", "BREAKOUT_FORMING")


# ══════════════════════════════════════════════════════════════
# Test 5: Range Mean Reversion Detection
# ══════════════════════════════════════════════════════════════

def test_range_mean_reversion_detection(engine):
    """Test 5: range mean reversion correctly detected."""
    layers = HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.4,
        alpha_mean_reversion_strength=0.65,
        regime_type="RANGING",
        regime_confidence=0.7,
        microstructure_state="NEUTRAL",
        microstructure_confidence=0.6,
        macro_confidence=0.5,
    )

    hypothesis = engine.generate_hypothesis("BTC", layers)

    assert hypothesis.hypothesis_type == "RANGE_MEAN_REVERSION"
    assert hypothesis.directional_bias == "LONG"


# ══════════════════════════════════════════════════════════════
# Test 6: No Edge Fallback
# ══════════════════════════════════════════════════════════════

def test_no_edge_fallback(engine):
    """Test 6: no edge fallback when no conditions met."""
    layers = HypothesisInputLayers(
        alpha_direction="NEUTRAL",
        alpha_strength=0.2,
        alpha_breakout_strength=0.1,
        alpha_mean_reversion_strength=0.1,
        regime_type="UNCERTAIN",
        regime_confidence=0.3,
        microstructure_state="STRESSED",
        microstructure_confidence=0.25,
        macro_confidence=0.3,
    )

    hypothesis = engine.generate_hypothesis("BTC", layers)

    assert hypothesis.hypothesis_type == "NO_EDGE"
    assert hypothesis.directional_bias == "NEUTRAL"


# ══════════════════════════════════════════════════════════════
# Test 7: Raw Score Calculation
# ══════════════════════════════════════════════════════════════

def test_raw_score_calculation(engine):
    """Test 7: raw score calculation follows weighted formula."""
    candidate = HypothesisCandidate(
        hypothesis_type="BULLISH_CONTINUATION",
        alpha_support=0.8,
        regime_support=0.7,
        microstructure_support=0.6,
        macro_support=0.5,
        directional_bias="LONG",
    )

    score = engine.calculate_raw_score(candidate)

    expected = (
        WEIGHT_ALPHA * 0.8
        + WEIGHT_REGIME * 0.7
        + WEIGHT_MICROSTRUCTURE * 0.6
        + WEIGHT_MACRO * 0.5
    )

    assert abs(score - round(expected, 4)) < 0.001


# ══════════════════════════════════════════════════════════════
# Test 8: Confidence Calculation
# ══════════════════════════════════════════════════════════════

def test_confidence_calculation(engine):
    """Test 8: confidence = raw_score clipped [0, 1]."""
    # Normal case
    assert engine.calculate_confidence(0.67) == 0.67

    # Clip upper
    assert engine.calculate_confidence(1.5) == 1.0

    # Clip lower
    assert engine.calculate_confidence(-0.2) == 0.0


# ══════════════════════════════════════════════════════════════
# Test 9: Reliability Calculation
# ══════════════════════════════════════════════════════════════

def test_reliability_calculation(engine):
    """Test 9: reliability = 1 - std(alpha, regime, micro)."""
    # Perfectly aligned supports → reliability near 1.0
    candidate_aligned = HypothesisCandidate(
        hypothesis_type="BULLISH_CONTINUATION",
        alpha_support=0.7,
        regime_support=0.7,
        microstructure_support=0.7,
        macro_support=0.5,
        directional_bias="LONG",
    )
    reliability = engine.calculate_reliability(candidate_aligned)
    assert reliability == 1.0  # std = 0, so 1 - 0 = 1.0

    # Divergent supports → lower reliability
    candidate_divergent = HypothesisCandidate(
        hypothesis_type="BULLISH_CONTINUATION",
        alpha_support=0.9,
        regime_support=0.3,
        microstructure_support=0.6,
        macro_support=0.5,
        directional_bias="LONG",
    )
    reliability = engine.calculate_reliability(candidate_divergent)
    assert reliability < 1.0
    assert reliability >= 0.0

    # Verify formula
    values = [0.9, 0.3, 0.6]
    mean = sum(values) / 3
    variance = sum((v - mean) ** 2 for v in values) / 3
    expected_std = math.sqrt(variance)
    expected_reliability = round(1.0 - expected_std, 4)
    assert abs(reliability - expected_reliability) < 0.001


# ══════════════════════════════════════════════════════════════
# Test 10: Execution State Mapping
# ══════════════════════════════════════════════════════════════

def test_execution_state_mapping(engine):
    """Test 10: execution state mapping from microstructure state."""
    assert engine.map_execution_state("SUPPORTIVE") == "FAVORABLE"
    assert engine.map_execution_state("NEUTRAL") == "CAUTIOUS"
    assert engine.map_execution_state("FRAGILE") == "UNFAVORABLE"
    assert engine.map_execution_state("STRESSED") == "UNFAVORABLE"


# ══════════════════════════════════════════════════════════════
# Test 11: Candidate Selection
# ══════════════════════════════════════════════════════════════

def test_candidate_selection(engine):
    """Test 11: best candidate selected by highest raw score."""
    candidates = [
        HypothesisCandidate(
            hypothesis_type="BULLISH_CONTINUATION",
            alpha_support=0.8,
            regime_support=0.7,
            microstructure_support=0.6,
            macro_support=0.5,
            directional_bias="LONG",
        ),
        HypothesisCandidate(
            hypothesis_type="NO_EDGE",
            alpha_support=0.1,
            regime_support=0.1,
            microstructure_support=0.1,
            macro_support=0.1,
            directional_bias="NEUTRAL",
        ),
    ]

    best = engine.select_best_candidate(candidates)
    assert best.hypothesis_type == "BULLISH_CONTINUATION"


# ══════════════════════════════════════════════════════════════
# Test 12: Hypothesis Endpoint (Current)
# ══════════════════════════════════════════════════════════════

def test_hypothesis_endpoint_current(engine):
    """Test 12: hypothesis endpoint returns valid data."""
    layers = HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.72,
        regime_type="TRENDING",
        regime_confidence=0.64,
        microstructure_state="NEUTRAL",
        microstructure_confidence=0.59,
        macro_confidence=0.53,
    )

    hypothesis = engine.generate_hypothesis("BTC", layers)

    # Verify all fields present
    assert hypothesis.symbol == "BTC"
    assert hypothesis.confidence > 0
    assert hypothesis.reliability > 0
    assert hypothesis.alpha_support > 0
    assert hypothesis.regime_support > 0
    assert hypothesis.microstructure_support > 0
    assert hypothesis.macro_fractal_support > 0
    assert hypothesis.execution_state in ("FAVORABLE", "CAUTIOUS", "UNFAVORABLE")
    assert len(hypothesis.reason) > 0
    assert hypothesis.created_at is not None


# ══════════════════════════════════════════════════════════════
# Test 13: History Endpoint
# ══════════════════════════════════════════════════════════════

def test_history_endpoint(engine):
    """Test 13: history tracking works."""
    # Generate multiple hypotheses
    for i in range(3):
        layers = HypothesisInputLayers(
            alpha_direction="BULLISH",
            alpha_strength=0.5 + i * 0.1,
            regime_type="TRENDING",
            regime_confidence=0.6,
            microstructure_state="NEUTRAL",
            microstructure_confidence=0.5,
            macro_confidence=0.5,
        )
        engine.generate_hypothesis("ETH", layers)

    history = engine._history.get("ETH", [])
    assert len(history) == 3


# ══════════════════════════════════════════════════════════════
# Test 14: Summary Endpoint
# ══════════════════════════════════════════════════════════════

def test_summary_endpoint(engine):
    """Test 14: summary computation."""
    # Generate diverse hypotheses
    layers_bull = HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.8,
        regime_type="TRENDING",
        regime_confidence=0.7,
        microstructure_state="SUPPORTIVE",
        microstructure_confidence=0.7,
        macro_confidence=0.6,
    )
    engine.generate_hypothesis("SOL", layers_bull)

    layers_bear = HypothesisInputLayers(
        alpha_direction="BEARISH",
        alpha_strength=0.75,
        regime_type="TRENDING",
        regime_confidence=0.65,
        microstructure_state="FRAGILE",
        microstructure_confidence=0.5,
        macro_confidence=0.5,
    )
    engine.generate_hypothesis("SOL", layers_bear)

    summary = engine.get_summary("SOL")

    assert summary.symbol == "SOL"
    assert summary.total_records == 2
    assert summary.bullish_continuation_count + summary.bearish_continuation_count >= 2
    assert summary.long_count >= 1
    assert summary.short_count >= 1


# ══════════════════════════════════════════════════════════════
# Test 15: Recompute Endpoint
# ══════════════════════════════════════════════════════════════

def test_recompute_endpoint(engine):
    """Test 15: recompute generates new hypothesis."""
    layers1 = HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.7,
        regime_type="TRENDING",
        regime_confidence=0.6,
        microstructure_state="NEUTRAL",
        microstructure_confidence=0.5,
        macro_confidence=0.5,
    )
    h1 = engine.generate_hypothesis("BTC", layers1)

    layers2 = HypothesisInputLayers(
        alpha_direction="NEUTRAL",
        alpha_strength=0.2,
        regime_type="UNCERTAIN",
        regime_confidence=0.3,
        microstructure_state="STRESSED",
        microstructure_confidence=0.2,
        macro_confidence=0.3,
    )
    h2 = engine.generate_hypothesis("BTC", layers2)

    assert h1.hypothesis_type != h2.hypothesis_type or h1.confidence != h2.confidence
    assert engine.get_hypothesis("BTC") == h2  # Latest cached


# ══════════════════════════════════════════════════════════════
# Test 16: Integration Alpha
# ══════════════════════════════════════════════════════════════

def test_integration_alpha(engine):
    """Test 16: alpha layer integration affects hypothesis."""
    # Strong bullish alpha → should produce bullish hypothesis
    layers_strong = HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.9,
        regime_type="TRENDING",
        regime_confidence=0.7,
        microstructure_state="SUPPORTIVE",
        microstructure_confidence=0.7,
        macro_confidence=0.6,
    )
    h_strong = engine.generate_hypothesis("BTC", layers_strong)

    # Weak alpha → should produce NO_EDGE
    layers_weak = HypothesisInputLayers(
        alpha_direction="NEUTRAL",
        alpha_strength=0.15,
        regime_type="UNCERTAIN",
        regime_confidence=0.3,
        microstructure_state="NEUTRAL",
        microstructure_confidence=0.4,
        macro_confidence=0.3,
    )
    h_weak = engine.generate_hypothesis("ETH", layers_weak)

    assert h_strong.alpha_support > h_weak.alpha_support
    assert h_strong.confidence > h_weak.confidence


# ══════════════════════════════════════════════════════════════
# Test 17: Integration Regime
# ══════════════════════════════════════════════════════════════

def test_integration_regime(engine):
    """Test 17: regime layer integration affects hypothesis selection."""
    # TRENDING regime → continuation hypothesis possible
    layers_trending = HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.7,
        regime_type="TRENDING",
        regime_confidence=0.8,
        microstructure_state="NEUTRAL",
        microstructure_confidence=0.6,
        macro_confidence=0.5,
    )
    h_trending = engine.generate_hypothesis("BTC", layers_trending)

    # RANGING regime with mean reversion → mean reversion hypothesis
    layers_ranging = HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.5,
        alpha_mean_reversion_strength=0.7,
        regime_type="RANGING",
        regime_confidence=0.75,
        microstructure_state="NEUTRAL",
        microstructure_confidence=0.6,
        macro_confidence=0.5,
    )
    h_ranging = engine.generate_hypothesis("ETH", layers_ranging)

    assert h_trending.hypothesis_type == "BULLISH_CONTINUATION"
    assert h_ranging.hypothesis_type == "RANGE_MEAN_REVERSION"


# ══════════════════════════════════════════════════════════════
# Test 18: Integration Microstructure
# ══════════════════════════════════════════════════════════════

def test_integration_microstructure(engine):
    """Test 18: microstructure integration affects execution state."""
    # SUPPORTIVE → FAVORABLE
    layers_support = HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.7,
        regime_type="TRENDING",
        regime_confidence=0.65,
        microstructure_state="SUPPORTIVE",
        microstructure_confidence=0.7,
        macro_confidence=0.55,
    )
    h_support = engine.generate_hypothesis("BTC", layers_support)
    assert h_support.execution_state == "FAVORABLE"

    # STRESSED → UNFAVORABLE and blocks bullish continuation
    layers_stressed = HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.7,
        regime_type="TRENDING",
        regime_confidence=0.65,
        microstructure_state="STRESSED",
        microstructure_confidence=0.3,
        macro_confidence=0.55,
    )
    h_stressed = engine.generate_hypothesis("ETH", layers_stressed)
    assert h_stressed.execution_state == "UNFAVORABLE"
    # STRESSED blocks BULLISH_CONTINUATION, so must be something else
    assert h_stressed.hypothesis_type != "BULLISH_CONTINUATION"


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

def run_all_tests():
    """Run all tests and print results."""
    engine = HypothesisEngine()

    tests = [
        ("1. hypothesis generation", test_hypothesis_generation),
        ("2. bullish continuation detection", test_bullish_continuation_detection),
        ("3. bearish continuation detection", test_bearish_continuation_detection),
        ("4. breakout forming detection", test_breakout_forming_detection),
        ("5. range mean reversion detection", test_range_mean_reversion_detection),
        ("6. no edge fallback", test_no_edge_fallback),
        ("7. raw score calculation", test_raw_score_calculation),
        ("8. confidence calculation", test_confidence_calculation),
        ("9. reliability calculation", test_reliability_calculation),
        ("10. execution state mapping", test_execution_state_mapping),
        ("11. candidate selection", test_candidate_selection),
        ("12. hypothesis endpoint (current)", test_hypothesis_endpoint_current),
        ("13. history endpoint", test_history_endpoint),
        ("14. summary endpoint", test_summary_endpoint),
        ("15. recompute endpoint", test_recompute_endpoint),
        ("16. integration alpha", test_integration_alpha),
        ("17. integration regime", test_integration_regime),
        ("18. integration microstructure", test_integration_microstructure),
    ]

    results = []

    for name, test_func in tests:
        # Each test gets a fresh engine
        test_engine = HypothesisEngine()
        try:
            test_func(test_engine)
            results.append((name, "PASS"))
        except AssertionError as e:
            results.append((name, f"FAIL: {e}"))
        except Exception as e:
            results.append((name, f"ERROR: {e}"))

    # Print results
    print("\n" + "=" * 60)
    print("PHASE 29.1 — Hypothesis Contract + Core Engine Tests")
    print("=" * 60)

    passed = sum(1 for _, status in results if status == "PASS")
    failed = len(results) - passed

    for name, status in results:
        icon = "+" if status == "PASS" else "-"
        print(f"[{icon}] {name}: {status}")

    print("-" * 60)
    print(f"Total: {passed}/{len(results)} passed")

    if failed > 0:
        print(f"  {failed} tests failed")
    else:
        print("All tests passed!")

    return passed == len(results)


if __name__ == "__main__":
    run_all_tests()
