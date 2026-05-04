"""
Hypothesis Scoring Engine — Tests

PHASE 29.2 — 20+ tests for Hypothesis Scoring Engine

Tests:
1. structural score calculation
2. execution score calculation
3. conflict score calculation
4. confidence calculation
5. reliability calculation
6. execution state mapping
7. bullish continuation alignment
8. bearish continuation alignment
9. breakout alignment
10. range mean reversion alignment
11. microstructure supportive case
12. microstructure stressed case
13. regime transition impact
14. conflict high detection
15. conflict low detection
16. integration with hypothesis engine
17. API current endpoint
18. API summary endpoint
19. API recompute endpoint
20. history endpoint
21. edge case normalization
22. enhanced reason generation
"""

import pytest
import math
from datetime import datetime

from modules.hypothesis_engine.hypothesis_scoring_engine import (
    HypothesisScoringEngine,
    get_hypothesis_scoring_engine,
    STRUCTURAL_WEIGHT_ALPHA,
    STRUCTURAL_WEIGHT_REGIME,
    STRUCTURAL_WEIGHT_MACRO,
    STRUCTURAL_WEIGHT_ALIGNMENT,
    EXECUTION_WEIGHT_MICROSTRUCTURE,
    EXECUTION_WEIGHT_CONTEXT,
    EXECUTION_WEIGHT_REGIME_STABILITY,
    MICROSTRUCTURE_QUALITY_MAP,
    REGIME_STABILITY_MAP,
    CONFLICT_LOW_THRESHOLD,
    CONFLICT_HIGH_THRESHOLD,
)
from modules.hypothesis_engine.hypothesis_types import (
    HypothesisCandidate,
    HypothesisInputLayers,
)
from modules.hypothesis_engine.hypothesis_engine import (
    HypothesisEngine,
    get_hypothesis_engine,
)


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def scoring_engine():
    """Create a fresh scoring engine for each test."""
    return HypothesisScoringEngine()


@pytest.fixture
def hypothesis_engine():
    """Create a fresh hypothesis engine for each test."""
    return HypothesisEngine()


@pytest.fixture
def bullish_candidate():
    """Bullish continuation candidate."""
    return HypothesisCandidate(
        hypothesis_type="BULLISH_CONTINUATION",
        alpha_support=0.8,
        regime_support=0.7,
        microstructure_support=0.75,
        macro_support=0.6,
        directional_bias="LONG",
    )


@pytest.fixture
def bearish_candidate():
    """Bearish continuation candidate."""
    return HypothesisCandidate(
        hypothesis_type="BEARISH_CONTINUATION",
        alpha_support=0.75,
        regime_support=0.65,
        microstructure_support=0.7,
        macro_support=0.55,
        directional_bias="SHORT",
    )


@pytest.fixture
def breakout_candidate():
    """Breakout forming candidate."""
    return HypothesisCandidate(
        hypothesis_type="BREAKOUT_FORMING",
        alpha_support=0.7,
        regime_support=0.6,
        microstructure_support=0.65,
        macro_support=0.5,
        directional_bias="LONG",
    )


@pytest.fixture
def mean_reversion_candidate():
    """Range mean reversion candidate."""
    return HypothesisCandidate(
        hypothesis_type="RANGE_MEAN_REVERSION",
        alpha_support=0.65,
        regime_support=0.8,
        microstructure_support=0.7,
        macro_support=0.45,
        directional_bias="LONG",
    )


@pytest.fixture
def no_edge_candidate():
    """No edge candidate."""
    return HypothesisCandidate(
        hypothesis_type="NO_EDGE",
        alpha_support=0.2,
        regime_support=0.25,
        microstructure_support=0.3,
        macro_support=0.15,
        directional_bias="NEUTRAL",
    )


@pytest.fixture
def trending_layers():
    """Trending regime layers."""
    return HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.75,
        regime_type="TRENDING",
        regime_confidence=0.7,
        microstructure_state="SUPPORTIVE",
        microstructure_confidence=0.8,
        macro_confidence=0.6,
    )


@pytest.fixture
def ranging_layers():
    """Ranging regime layers."""
    return HypothesisInputLayers(
        alpha_direction="NEUTRAL",
        alpha_strength=0.5,
        regime_type="RANGING",
        regime_confidence=0.75,
        microstructure_state="NEUTRAL",
        microstructure_confidence=0.65,
        macro_confidence=0.5,
    )


@pytest.fixture
def stressed_layers():
    """Stressed microstructure layers."""
    return HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.6,
        regime_type="TRENDING",
        regime_confidence=0.5,
        microstructure_state="STRESSED",
        microstructure_confidence=0.3,
        macro_confidence=0.4,
    )


# ══════════════════════════════════════════════════════════════
# Test 1: Structural Score Calculation
# ══════════════════════════════════════════════════════════════

def test_structural_score_calculation(scoring_engine, bullish_candidate, trending_layers):
    """Test structural score formula."""
    score = scoring_engine.calculate_structural_score(bullish_candidate, trending_layers)
    
    # Manual calculation:
    # alignment = 1.0 (BULLISH_CONTINUATION + TRENDING + LONG)
    # score = 0.40*0.8 + 0.30*0.7 + 0.20*0.6 + 0.10*1.0 = 0.32 + 0.21 + 0.12 + 0.10 = 0.75
    expected = (
        STRUCTURAL_WEIGHT_ALPHA * 0.8
        + STRUCTURAL_WEIGHT_REGIME * 0.7
        + STRUCTURAL_WEIGHT_MACRO * 0.6
        + STRUCTURAL_WEIGHT_ALIGNMENT * 1.0
    )
    
    assert abs(score - round(expected, 4)) < 0.01
    assert 0.0 <= score <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 2: Execution Score Calculation
# ══════════════════════════════════════════════════════════════

def test_execution_score_calculation(scoring_engine):
    """Test execution score formula."""
    score = scoring_engine.calculate_execution_score(
        microstructure_state="SUPPORTIVE",
        confidence_modifier=1.0,
        transition_state="STABLE",
    )
    
    # Manual calculation:
    # micro_quality = 1.0
    # exec_modifier = (1.0 - 0.82) / (1.12 - 0.82) = 0.6
    # regime_stability = 1.0
    # score = 0.50*1.0 + 0.30*0.6 + 0.20*1.0 = 0.5 + 0.18 + 0.2 = 0.88
    expected = (
        EXECUTION_WEIGHT_MICROSTRUCTURE * 1.0
        + EXECUTION_WEIGHT_CONTEXT * 0.6
        + EXECUTION_WEIGHT_REGIME_STABILITY * 1.0
    )
    
    assert abs(score - round(expected, 4)) < 0.01
    assert 0.0 <= score <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 3: Conflict Score Calculation
# ══════════════════════════════════════════════════════════════

def test_conflict_score_calculation(scoring_engine):
    """Test conflict score as standard deviation."""
    # High agreement case
    low_conflict = scoring_engine.calculate_conflict_score(0.7, 0.72, 0.68)
    assert low_conflict < CONFLICT_LOW_THRESHOLD
    
    # High conflict case (more extreme values)
    high_conflict = scoring_engine.calculate_conflict_score(0.95, 0.25, 0.55)
    assert high_conflict > CONFLICT_HIGH_THRESHOLD


# ══════════════════════════════════════════════════════════════
# Test 4: Confidence Calculation
# ══════════════════════════════════════════════════════════════

def test_confidence_calculation(scoring_engine):
    """Test confidence formula."""
    confidence = scoring_engine.calculate_confidence(
        structural_score=0.75,
        execution_score=0.65,
    )
    
    # confidence = 0.60*0.75 + 0.40*0.65 = 0.45 + 0.26 = 0.71
    expected = 0.60 * 0.75 + 0.40 * 0.65
    
    assert abs(confidence - round(expected, 4)) < 0.01
    assert 0.0 <= confidence <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 5: Reliability Calculation
# ══════════════════════════════════════════════════════════════

def test_reliability_calculation(scoring_engine):
    """Test reliability formula."""
    reliability = scoring_engine.calculate_reliability(
        conflict_score=0.1,
        regime_support=0.7,
    )
    
    # reliability = (1 - 0.1) * 0.7 = 0.63
    expected = (1.0 - 0.1) * 0.7
    
    assert abs(reliability - round(expected, 4)) < 0.01
    assert 0.0 <= reliability <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 6: Execution State Mapping
# ══════════════════════════════════════════════════════════════

def test_execution_state_mapping(scoring_engine):
    """Test execution state mapping from execution_score."""
    assert scoring_engine.map_execution_state(0.85) == "FAVORABLE"
    assert scoring_engine.map_execution_state(0.70) == "FAVORABLE"
    assert scoring_engine.map_execution_state(0.55) == "CAUTIOUS"
    assert scoring_engine.map_execution_state(0.45) == "CAUTIOUS"
    assert scoring_engine.map_execution_state(0.30) == "UNFAVORABLE"
    assert scoring_engine.map_execution_state(0.0) == "UNFAVORABLE"


# ══════════════════════════════════════════════════════════════
# Test 7: Bullish Continuation Alignment
# ══════════════════════════════════════════════════════════════

def test_bullish_continuation_alignment(scoring_engine):
    """Test alignment for BULLISH_CONTINUATION."""
    # Perfect alignment
    assert scoring_engine.calculate_hypothesis_alignment(
        "BULLISH_CONTINUATION", "TRENDING", "LONG"
    ) == 1.0
    
    # Regime mismatch
    assert scoring_engine.calculate_hypothesis_alignment(
        "BULLISH_CONTINUATION", "RANGING", "LONG"
    ) == 0.6


# ══════════════════════════════════════════════════════════════
# Test 8: Bearish Continuation Alignment
# ══════════════════════════════════════════════════════════════

def test_bearish_continuation_alignment(scoring_engine):
    """Test alignment for BEARISH_CONTINUATION."""
    # Perfect alignment
    assert scoring_engine.calculate_hypothesis_alignment(
        "BEARISH_CONTINUATION", "TRENDING", "SHORT"
    ) == 1.0
    
    # Regime mismatch
    assert scoring_engine.calculate_hypothesis_alignment(
        "BEARISH_CONTINUATION", "VOLATILE", "SHORT"
    ) == 0.6


# ══════════════════════════════════════════════════════════════
# Test 9: Breakout Alignment
# ══════════════════════════════════════════════════════════════

def test_breakout_alignment(scoring_engine):
    """Test alignment for BREAKOUT_FORMING."""
    # Trending regime
    assert scoring_engine.calculate_hypothesis_alignment(
        "BREAKOUT_FORMING", "TRENDING", "LONG"
    ) == 0.9
    
    # Volatile regime
    assert scoring_engine.calculate_hypothesis_alignment(
        "BREAKOUT_FORMING", "VOLATILE", "LONG"
    ) == 0.9
    
    # Ranging regime (not ideal for breakout)
    assert scoring_engine.calculate_hypothesis_alignment(
        "BREAKOUT_FORMING", "RANGING", "LONG"
    ) == 0.6


# ══════════════════════════════════════════════════════════════
# Test 10: Range Mean Reversion Alignment
# ══════════════════════════════════════════════════════════════

def test_mean_reversion_alignment(scoring_engine):
    """Test alignment for RANGE_MEAN_REVERSION."""
    # Perfect alignment with ranging regime
    assert scoring_engine.calculate_hypothesis_alignment(
        "RANGE_MEAN_REVERSION", "RANGING", "LONG"
    ) == 1.0
    
    # Wrong regime
    assert scoring_engine.calculate_hypothesis_alignment(
        "RANGE_MEAN_REVERSION", "TRENDING", "LONG"
    ) == 0.5


# ══════════════════════════════════════════════════════════════
# Test 11: Microstructure Supportive Case
# ══════════════════════════════════════════════════════════════

def test_microstructure_supportive_case(scoring_engine):
    """Test execution quality for SUPPORTIVE microstructure."""
    quality = scoring_engine.calculate_microstructure_execution_quality("SUPPORTIVE")
    assert quality == 1.0
    
    exec_score = scoring_engine.calculate_execution_score(
        microstructure_state="SUPPORTIVE",
        confidence_modifier=1.0,
        transition_state="STABLE",
    )
    assert exec_score >= 0.70  # Should be FAVORABLE


# ══════════════════════════════════════════════════════════════
# Test 12: Microstructure Stressed Case
# ══════════════════════════════════════════════════════════════

def test_microstructure_stressed_case(scoring_engine):
    """Test execution quality for STRESSED microstructure."""
    quality = scoring_engine.calculate_microstructure_execution_quality("STRESSED")
    assert quality == 0.25
    
    exec_score = scoring_engine.calculate_execution_score(
        microstructure_state="STRESSED",
        confidence_modifier=0.85,
        transition_state="UNSTABLE",
    )
    assert exec_score < 0.45  # Should be UNFAVORABLE


# ══════════════════════════════════════════════════════════════
# Test 13: Regime Transition Impact
# ══════════════════════════════════════════════════════════════

def test_regime_transition_impact(scoring_engine):
    """Test regime transition impact on execution score."""
    # Stable transition - highest stability
    stable_score = scoring_engine.calculate_execution_score(
        microstructure_state="NEUTRAL",
        confidence_modifier=1.0,
        transition_state="STABLE",
    )
    
    # Active transition - lower stability
    transition_score = scoring_engine.calculate_execution_score(
        microstructure_state="NEUTRAL",
        confidence_modifier=1.0,
        transition_state="ACTIVE_TRANSITION",
    )
    
    # Unstable - lowest stability
    unstable_score = scoring_engine.calculate_execution_score(
        microstructure_state="NEUTRAL",
        confidence_modifier=1.0,
        transition_state="UNSTABLE",
    )
    
    assert stable_score > transition_score > unstable_score


# ══════════════════════════════════════════════════════════════
# Test 14: Conflict High Detection
# ══════════════════════════════════════════════════════════════

def test_conflict_high_detection(scoring_engine):
    """Test detection of HIGH conflict."""
    # High disagreement between layers
    conflict = scoring_engine.calculate_conflict_score(0.9, 0.2, 0.5)
    level = scoring_engine.interpret_conflict_level(conflict)
    
    assert conflict > CONFLICT_HIGH_THRESHOLD
    assert level == "HIGH"


# ══════════════════════════════════════════════════════════════
# Test 15: Conflict Low Detection
# ══════════════════════════════════════════════════════════════

def test_conflict_low_detection(scoring_engine):
    """Test detection of LOW conflict."""
    # High agreement between layers
    conflict = scoring_engine.calculate_conflict_score(0.7, 0.72, 0.68)
    level = scoring_engine.interpret_conflict_level(conflict)
    
    assert conflict < CONFLICT_LOW_THRESHOLD
    assert level == "LOW_CONFLICT"


# ══════════════════════════════════════════════════════════════
# Test 16: Integration with Hypothesis Engine
# ══════════════════════════════════════════════════════════════

def test_integration_with_hypothesis_engine(hypothesis_engine, trending_layers):
    """Test integration with hypothesis engine."""
    hypothesis = hypothesis_engine.generate_hypothesis(
        symbol="BTC",
        layers=trending_layers,
        execution_confidence_modifier=1.0,
        transition_state="STABLE",
    )
    
    # Should have all new scoring fields
    assert hasattr(hypothesis, "structural_score")
    assert hasattr(hypothesis, "execution_score")
    assert hasattr(hypothesis, "conflict_score")
    
    assert 0.0 <= hypothesis.structural_score <= 1.0
    assert 0.0 <= hypothesis.execution_score <= 1.0
    assert 0.0 <= hypothesis.conflict_score <= 1.0
    assert 0.0 <= hypothesis.confidence <= 1.0
    assert 0.0 <= hypothesis.reliability <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 17: API Current Endpoint (simulated)
# ══════════════════════════════════════════════════════════════

def test_api_current_endpoint_simulated(hypothesis_engine):
    """Test simulated hypothesis generation (mimics API /current)."""
    hypothesis = hypothesis_engine.generate_hypothesis_simulated("BTC")
    
    # Validate structure
    assert hypothesis.symbol == "BTC"
    assert hypothesis.hypothesis_type in [
        "BULLISH_CONTINUATION",
        "BEARISH_CONTINUATION",
        "BREAKOUT_FORMING",
        "RANGE_MEAN_REVERSION",
        "NO_EDGE",
    ]
    assert hypothesis.execution_state in ["FAVORABLE", "CAUTIOUS", "UNFAVORABLE"]
    
    # New PHASE 29.2 fields
    assert hypothesis.structural_score is not None
    assert hypothesis.execution_score is not None
    assert hypothesis.conflict_score is not None


# ══════════════════════════════════════════════════════════════
# Test 18: API Summary Endpoint (simulated)
# ══════════════════════════════════════════════════════════════

def test_api_summary_endpoint_simulated(hypothesis_engine):
    """Test summary generation (mimics API /summary)."""
    # Generate multiple hypotheses
    for _ in range(5):
        hypothesis_engine.generate_hypothesis_simulated("ETH")
    
    summary = hypothesis_engine.get_summary("ETH")
    
    assert summary.symbol == "ETH"
    assert summary.total_records == 5
    assert summary.average_confidence >= 0.0
    assert summary.average_reliability >= 0.0


# ══════════════════════════════════════════════════════════════
# Test 19: API Recompute Endpoint (simulated)
# ══════════════════════════════════════════════════════════════

def test_api_recompute_endpoint_simulated(hypothesis_engine):
    """Test hypothesis recompute (mimics API /recompute)."""
    # First generation
    h1 = hypothesis_engine.generate_hypothesis_simulated("SOL")
    
    # Recompute should work
    h2 = hypothesis_engine.generate_hypothesis_simulated("SOL")
    
    # Both should be valid
    assert h1.symbol == "SOL"
    assert h2.symbol == "SOL"
    
    # History should have 2 entries
    history = hypothesis_engine._history.get("SOL", [])
    assert len(history) == 2


# ══════════════════════════════════════════════════════════════
# Test 20: History Endpoint
# ══════════════════════════════════════════════════════════════

def test_history_tracking(hypothesis_engine, trending_layers):
    """Test hypothesis history tracking."""
    # Generate multiple hypotheses
    for _ in range(3):
        hypothesis_engine.generate_hypothesis("BTC", trending_layers)
    
    history = hypothesis_engine._history.get("BTC", [])
    
    assert len(history) == 3
    assert all(h.symbol == "BTC" for h in history)


# ══════════════════════════════════════════════════════════════
# Test 21: Edge Case Normalization
# ══════════════════════════════════════════════════════════════

def test_edge_case_normalization(scoring_engine):
    """Test edge case handling for score normalization."""
    # Very low confidence modifier
    exec_mod = scoring_engine.calculate_execution_context_modifier(0.5)
    assert exec_mod == 0.0  # Below min should clip to 0
    
    # Very high confidence modifier
    exec_mod = scoring_engine.calculate_execution_context_modifier(1.5)
    assert exec_mod == 1.0  # Above max should clip to 1
    
    # Exact min
    exec_mod = scoring_engine.calculate_execution_context_modifier(0.82)
    assert exec_mod == 0.0
    
    # Exact max
    exec_mod = scoring_engine.calculate_execution_context_modifier(1.12)
    assert exec_mod == 1.0


# ══════════════════════════════════════════════════════════════
# Test 22: Enhanced Reason Generation
# ══════════════════════════════════════════════════════════════

def test_enhanced_reason_generation(scoring_engine, bullish_candidate, trending_layers):
    """Test enhanced reason generation."""
    scores = scoring_engine.score_hypothesis(
        candidate=bullish_candidate,
        layers=trending_layers,
        execution_confidence_modifier=1.0,
        transition_state="STABLE",
    )
    
    reason = scoring_engine.generate_enhanced_reason(
        hypothesis_type="BULLISH_CONTINUATION",
        scores=scores,
        layers=trending_layers,
    )
    
    assert "bullish continuation" in reason.lower()
    assert len(reason) > 10


# ══════════════════════════════════════════════════════════════
# Test 23: Full Scoring Integration
# ══════════════════════════════════════════════════════════════

def test_full_scoring_integration(scoring_engine, bullish_candidate, trending_layers):
    """Test full scoring integration."""
    scores = scoring_engine.score_hypothesis(
        candidate=bullish_candidate,
        layers=trending_layers,
        execution_confidence_modifier=1.0,
        transition_state="STABLE",
    )
    
    # All keys should exist
    assert "structural_score" in scores
    assert "execution_score" in scores
    assert "conflict_score" in scores
    assert "confidence" in scores
    assert "reliability" in scores
    assert "execution_state" in scores
    assert "conflict_level" in scores
    assert "hypothesis_alignment" in scores
    
    # All should be valid
    assert 0.0 <= scores["structural_score"] <= 1.0
    assert 0.0 <= scores["execution_score"] <= 1.0
    assert 0.0 <= scores["conflict_score"] <= 1.0
    assert 0.0 <= scores["confidence"] <= 1.0
    assert 0.0 <= scores["reliability"] <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 24: Singleton Pattern
# ══════════════════════════════════════════════════════════════

def test_singleton_pattern():
    """Test that get_hypothesis_scoring_engine returns singleton."""
    engine1 = get_hypothesis_scoring_engine()
    engine2 = get_hypothesis_scoring_engine()
    
    assert engine1 is engine2


# ══════════════════════════════════════════════════════════════
# Test 25: NO_EDGE Hypothesis
# ══════════════════════════════════════════════════════════════

def test_no_edge_hypothesis(scoring_engine, no_edge_candidate, stressed_layers):
    """Test NO_EDGE hypothesis scoring."""
    scores = scoring_engine.score_hypothesis(
        candidate=no_edge_candidate,
        layers=stressed_layers,
        execution_confidence_modifier=0.85,
        transition_state="UNSTABLE",
    )
    
    # NO_EDGE should have low alignment
    assert scores["hypothesis_alignment"] == 0.3
    
    # Confidence and reliability should be low
    assert scores["confidence"] < 0.5
    assert scores["reliability"] < 0.5


# ══════════════════════════════════════════════════════════════
# Run tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
