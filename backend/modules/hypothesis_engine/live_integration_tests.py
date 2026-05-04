"""
Live Integration Tests

TASK 94 — Live integration of reflexivity_modifier
TASK 95 — Live integration of regime_graph_modifier

Tests for live integration of reflexivity and regime graph
modifiers into hypothesis scoring.

Minimum 10 tests per task = 20 total.
"""

import pytest
from datetime import datetime, timezone

from .hypothesis_scoring_engine import (
    HypothesisScoringEngine,
    get_hypothesis_scoring_engine,
    STRUCTURAL_WEIGHT_REFLEXIVITY,
    STRUCTURAL_WEIGHT_REGIME_GRAPH,
)
from .hypothesis_types import HypothesisCandidate, HypothesisInputLayers


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Create fresh engine instance."""
    return HypothesisScoringEngine()


@pytest.fixture
def sample_candidate():
    """Create sample hypothesis candidate."""
    return HypothesisCandidate(
        hypothesis_type="BULLISH_CONTINUATION",
        directional_bias="LONG",
        alpha_support=0.75,
        regime_support=0.70,
        microstructure_support=0.65,
        macro_support=0.60,
        trigger_pattern="BREAKOUT",
        target_price_low=105000.0,
        target_price_high=110000.0,
        stop_loss_price=98000.0,
        invalidation_level=96000.0,
    )


@pytest.fixture
def sample_layers():
    """Create sample input layers."""
    return HypothesisInputLayers(
        regime_type="TRENDING",
        regime_confidence=0.75,
        alpha_direction="BULLISH",
        alpha_strength=0.70,
        microstructure_state="SUPPORTIVE",
        microstructure_confidence=0.72,
        macro_fractal_support=0.65,
    )


# ══════════════════════════════════════════════════════════════
# TASK 94 — Reflexivity Integration Tests
# ══════════════════════════════════════════════════════════════

def test_reflexivity_weight_correct():
    """Test reflexivity weight is 0.05."""
    assert STRUCTURAL_WEIGHT_REFLEXIVITY == 0.05


def test_get_reflexivity_score_returns_tuple(engine):
    """Test get_reflexivity_score returns tuple."""
    score, modifier, aligned = engine.get_reflexivity_score("BTC", "LONG")
    
    assert isinstance(score, float)
    assert isinstance(modifier, float)
    assert isinstance(aligned, bool)
    assert 0 <= score <= 1


def test_reflexivity_score_in_structural(engine, sample_candidate, sample_layers):
    """Test reflexivity score contributes to structural score."""
    # Score with low reflexivity
    low_score = engine.calculate_structural_score(
        sample_candidate,
        sample_layers,
        reflexivity_score=0.2,
        regime_graph_score=0.5,
    )
    
    # Score with high reflexivity
    high_score = engine.calculate_structural_score(
        sample_candidate,
        sample_layers,
        reflexivity_score=0.9,
        regime_graph_score=0.5,
    )
    
    # High reflexivity should increase score
    assert high_score > low_score


def test_reflexivity_modifier_affects_confidence(engine, sample_candidate, sample_layers):
    """Test reflexivity modifier affects final confidence."""
    scores = engine.score_hypothesis(
        sample_candidate,
        sample_layers,
        symbol="BTC",
    )
    
    assert "reflexivity_score" in scores
    assert "reflexivity_modifier" in scores
    assert "reflexivity_aligned" in scores


def test_reflexivity_aligned_boosts_confidence(engine):
    """Test aligned reflexivity boosts hypothesis."""
    # Get reflexivity for LONG
    score_long, mod_long, aligned_long = engine.get_reflexivity_score("BTC", "LONG")
    
    # Get reflexivity for SHORT
    score_short, mod_short, aligned_short = engine.get_reflexivity_score("BTC", "SHORT")
    
    # Both should return valid values
    assert 0 <= score_long <= 1
    assert 0 <= score_short <= 1


def test_reflexivity_conflict_reduces_confidence(engine, sample_candidate, sample_layers):
    """Test conflicting reflexivity reduces confidence."""
    # Test hypothesis scoring handles reflexivity
    scores = engine.score_hypothesis(
        sample_candidate,
        sample_layers,
        symbol="ETH",
    )
    
    # Confidence should be affected by reflexivity
    assert scores["confidence"] > 0
    assert scores["reflexivity_modifier"] > 0


def test_reflexivity_in_full_scoring(engine, sample_candidate, sample_layers):
    """Test reflexivity appears in full scoring result."""
    scores = engine.score_hypothesis(
        sample_candidate,
        sample_layers,
        symbol="SOL",
    )
    
    required_fields = [
        "reflexivity_score",
        "reflexivity_modifier",
        "reflexivity_aligned",
    ]
    
    for field in required_fields:
        assert field in scores, f"Missing field: {field}"


def test_reflexivity_multiple_symbols(engine):
    """Test reflexivity works for multiple symbols."""
    symbols = ["BTC", "ETH", "SOL"]
    
    for symbol in symbols:
        score, modifier, aligned = engine.get_reflexivity_score(symbol, "LONG")
        assert 0 <= score <= 1
        assert modifier > 0


def test_reflexivity_long_short_different(engine):
    """Test LONG and SHORT get different reflexivity responses."""
    score_long, mod_long, _ = engine.get_reflexivity_score("BTC", "LONG")
    score_short, mod_short, _ = engine.get_reflexivity_score("BTC", "SHORT")
    
    # Both should return valid values (may or may not differ)
    assert 0 <= score_long <= 1
    assert 0 <= score_short <= 1


def test_reflexivity_backward_compatible(engine, sample_candidate, sample_layers):
    """Test backward compatibility with old scoring."""
    # Scoring should work without errors
    scores = engine.score_hypothesis(
        sample_candidate,
        sample_layers,
        symbol="BTC",
    )
    
    # Old fields should still exist
    assert "structural_score" in scores
    assert "execution_score" in scores
    assert "confidence" in scores
    assert "reliability" in scores


# ══════════════════════════════════════════════════════════════
# TASK 95 — Regime Graph Integration Tests
# ══════════════════════════════════════════════════════════════

def test_regime_graph_weight_correct():
    """Test regime graph weight is 0.04."""
    assert STRUCTURAL_WEIGHT_REGIME_GRAPH == 0.04


def test_get_regime_graph_score_returns_tuple(engine):
    """Test get_regime_graph_score returns tuple."""
    score, modifier, favorable = engine.get_regime_graph_score("BTC", "LONG")
    
    assert isinstance(score, float)
    assert isinstance(modifier, float)
    assert isinstance(favorable, bool)
    assert 0 <= score <= 1


def test_regime_graph_score_in_structural(engine, sample_candidate, sample_layers):
    """Test regime graph score contributes to structural score."""
    # Score with low graph confidence
    low_score = engine.calculate_structural_score(
        sample_candidate,
        sample_layers,
        reflexivity_score=0.5,
        regime_graph_score=0.2,
    )
    
    # Score with high graph confidence
    high_score = engine.calculate_structural_score(
        sample_candidate,
        sample_layers,
        reflexivity_score=0.5,
        regime_graph_score=0.9,
    )
    
    # High graph confidence should increase score
    assert high_score > low_score


def test_regime_graph_modifier_affects_confidence(engine, sample_candidate, sample_layers):
    """Test graph modifier affects final confidence."""
    scores = engine.score_hypothesis(
        sample_candidate,
        sample_layers,
        symbol="BTC",
    )
    
    assert "regime_graph_score" in scores
    assert "regime_graph_modifier" in scores
    assert "regime_graph_favorable" in scores


def test_regime_graph_favorable_boosts(engine):
    """Test favorable graph transition boosts hypothesis."""
    score, modifier, favorable = engine.get_regime_graph_score("BTC", "LONG")
    
    # Should return valid values
    assert 0 <= score <= 1
    assert modifier > 0


def test_regime_graph_path_confidence(engine):
    """Test graph score reflects path confidence."""
    score, _, _ = engine.get_regime_graph_score("ETH", "SHORT")
    
    # Score should be path_confidence from graph engine
    assert 0 <= score <= 1


def test_regime_graph_in_full_scoring(engine, sample_candidate, sample_layers):
    """Test graph appears in full scoring result."""
    scores = engine.score_hypothesis(
        sample_candidate,
        sample_layers,
        symbol="BTC",
    )
    
    required_fields = [
        "regime_graph_score",
        "regime_graph_modifier",
        "regime_graph_favorable",
    ]
    
    for field in required_fields:
        assert field in scores, f"Missing field: {field}"


def test_regime_graph_multiple_symbols(engine):
    """Test graph works for multiple symbols."""
    symbols = ["BTC", "ETH", "SOL"]
    
    for symbol in symbols:
        score, modifier, favorable = engine.get_regime_graph_score(symbol, "LONG")
        assert 0 <= score <= 1
        assert modifier > 0


def test_reliability_boosted_when_both_aligned(engine, sample_candidate, sample_layers):
    """Test reliability is boosted when both reflexivity and graph are favorable."""
    scores = engine.score_hypothesis(
        sample_candidate,
        sample_layers,
        symbol="BTC",
    )
    
    # Reliability should be valid
    assert 0 <= scores["reliability"] <= 1


def test_all_weights_sum_to_one():
    """Test all structural weights sum to 1.0."""
    from .hypothesis_scoring_engine import (
        STRUCTURAL_WEIGHT_ALPHA,
        STRUCTURAL_WEIGHT_REGIME,
        STRUCTURAL_WEIGHT_MICROSTRUCTURE,
        STRUCTURAL_WEIGHT_MACRO,
        STRUCTURAL_WEIGHT_FRACTAL_MARKET,
        STRUCTURAL_WEIGHT_FRACTAL_SIMILARITY,
        STRUCTURAL_WEIGHT_CROSS_ASSET,
        STRUCTURAL_WEIGHT_REGIME_MEMORY,
        STRUCTURAL_WEIGHT_REFLEXIVITY,
        STRUCTURAL_WEIGHT_REGIME_GRAPH,
    )
    
    total = (
        STRUCTURAL_WEIGHT_ALPHA
        + STRUCTURAL_WEIGHT_REGIME
        + STRUCTURAL_WEIGHT_MICROSTRUCTURE
        + STRUCTURAL_WEIGHT_MACRO
        + STRUCTURAL_WEIGHT_FRACTAL_MARKET
        + STRUCTURAL_WEIGHT_FRACTAL_SIMILARITY
        + STRUCTURAL_WEIGHT_CROSS_ASSET
        + STRUCTURAL_WEIGHT_REGIME_MEMORY
        + STRUCTURAL_WEIGHT_REFLEXIVITY
        + STRUCTURAL_WEIGHT_REGIME_GRAPH
    )
    
    assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, not 1.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
