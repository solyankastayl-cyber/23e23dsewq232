"""
Reflexivity Engine Tests

PHASE 35 — Market Reflexivity Engine

Unit tests for reflexivity calculation.
"""

import pytest
from datetime import datetime, timezone

from .reflexivity_types import (
    ReflexivityState,
    ReflexivitySource,
    ReflexivityModifier,
    REFLEXIVITY_WEIGHT,
    WEIGHT_SENTIMENT,
    WEIGHT_POSITIONING,
    WEIGHT_TREND_ACCELERATION,
    WEIGHT_VOLATILITY_EXPANSION,
)
from .reflexivity_engine import ReflexivityEngine


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Create fresh engine instance."""
    return ReflexivityEngine()


@pytest.fixture
def bullish_source():
    """Create bullish market source data."""
    return ReflexivitySource(
        funding_rate=0.002,
        funding_sentiment=0.67,
        oi_change_24h=0.08,
        oi_expansion=True,
        long_liquidations=1000000,
        short_liquidations=3000000,
        liquidation_imbalance=0.5,
        volume_spike_ratio=1.5,
        price_momentum=0.6,
        trend_acceleration=0.4,
    )


@pytest.fixture
def bearish_source():
    """Create bearish market source data."""
    return ReflexivitySource(
        funding_rate=-0.002,
        funding_sentiment=-0.67,
        oi_change_24h=0.05,
        oi_expansion=True,
        long_liquidations=3000000,
        short_liquidations=1000000,
        liquidation_imbalance=-0.5,
        volume_spike_ratio=1.3,
        price_momentum=-0.5,
        trend_acceleration=-0.3,
    )


@pytest.fixture
def exhausted_source():
    """Create exhausted/crowded market source data."""
    return ReflexivitySource(
        funding_rate=0.003,
        funding_sentiment=0.9,  # Extreme crowding
        oi_change_24h=0.02,
        oi_expansion=False,
        long_liquidations=500000,
        short_liquidations=500000,
        liquidation_imbalance=0.0,
        volume_spike_ratio=0.8,
        price_momentum=0.1,
        trend_acceleration=-0.2,  # Decelerating
    )


# ══════════════════════════════════════════════════════════════
# Test Component Scores
# ══════════════════════════════════════════════════════════════

def test_sentiment_score_bullish(engine, bullish_source):
    """Test sentiment score for bullish market."""
    score = engine.calculate_sentiment_score(bullish_source)
    
    assert 0 <= score <= 1
    assert score > 0.5  # Should be high for bullish
    
    # Check formula: combines funding_sentiment and liquidation_imbalance
    expected_raw = abs(0.6 * bullish_source.funding_sentiment + 0.4 * bullish_source.liquidation_imbalance)
    assert abs(score - expected_raw) < 0.01


def test_sentiment_score_bearish(engine, bearish_source):
    """Test sentiment score for bearish market."""
    score = engine.calculate_sentiment_score(bearish_source)
    
    assert 0 <= score <= 1
    assert score > 0.5  # Should be high (absolute value)


def test_positioning_score(engine, bullish_source):
    """Test positioning score calculation."""
    score = engine.calculate_positioning_score(bullish_source)
    
    assert 0 <= score <= 1
    assert score > 0.3  # Should be elevated with OI expansion


def test_trend_acceleration_score(engine, bullish_source):
    """Test trend acceleration score."""
    score = engine.calculate_trend_acceleration_score(bullish_source)
    
    assert 0 <= score <= 1
    # Momentum and acceleration aligned, should get boost
    assert score > 0.3


def test_volatility_expansion_score(engine, bullish_source):
    """Test volatility expansion score."""
    score = engine.calculate_volatility_expansion_score(bullish_source)
    
    assert 0 <= score <= 1
    assert score > 0.2  # Should be elevated with volume spike


# ══════════════════════════════════════════════════════════════
# Test Reflexivity Score
# ══════════════════════════════════════════════════════════════

def test_reflexivity_score_formula(engine):
    """Test reflexivity score formula correctness."""
    sentiment = 0.8
    positioning = 0.6
    trend_accel = 0.5
    vol_expansion = 0.4
    
    score = engine.calculate_reflexivity_score(
        sentiment, positioning, trend_accel, vol_expansion
    )
    
    expected = (
        WEIGHT_SENTIMENT * sentiment
        + WEIGHT_POSITIONING * positioning
        + WEIGHT_TREND_ACCELERATION * trend_accel
        + WEIGHT_VOLATILITY_EXPANSION * vol_expansion
    )
    
    assert abs(score - expected) < 0.001
    assert 0 <= score <= 1


def test_reflexivity_score_weights_sum():
    """Verify weights sum to 1.0."""
    total = (
        WEIGHT_SENTIMENT
        + WEIGHT_POSITIONING
        + WEIGHT_TREND_ACCELERATION
        + WEIGHT_VOLATILITY_EXPANSION
    )
    assert abs(total - 1.0) < 0.001


# ══════════════════════════════════════════════════════════════
# Test Feedback Direction
# ══════════════════════════════════════════════════════════════

def test_feedback_direction_positive(engine, bullish_source):
    """Test positive feedback detection."""
    direction = engine.determine_feedback_direction(bullish_source)
    
    assert direction == "POSITIVE"


def test_feedback_direction_negative(engine, bearish_source):
    """Test negative feedback detection."""
    direction = engine.determine_feedback_direction(bearish_source)
    
    assert direction == "NEGATIVE"


def test_feedback_direction_exhausted(engine, exhausted_source):
    """Test exhaustion detection (negative feedback due to crowding)."""
    direction = engine.determine_feedback_direction(exhausted_source)
    
    # Extreme crowding should trigger negative feedback (mean reversion expected)
    assert direction == "NEGATIVE"


# ══════════════════════════════════════════════════════════════
# Test Sentiment State
# ══════════════════════════════════════════════════════════════

def test_sentiment_state_greed(engine, bullish_source):
    """Test greed detection."""
    state = engine.determine_sentiment_state(bullish_source)
    
    assert state in ["GREED", "EXTREME_GREED"]


def test_sentiment_state_fear(engine, bearish_source):
    """Test fear detection."""
    state = engine.determine_sentiment_state(bearish_source)
    
    assert state in ["FEAR", "EXTREME_FEAR"]


# ══════════════════════════════════════════════════════════════
# Test Strength Classification
# ══════════════════════════════════════════════════════════════

def test_strength_weak(engine):
    """Test weak strength classification."""
    assert engine.determine_strength(0.2) == "WEAK"
    assert engine.determine_strength(0.34) == "WEAK"


def test_strength_moderate(engine):
    """Test moderate strength classification."""
    assert engine.determine_strength(0.35) == "MODERATE"
    assert engine.determine_strength(0.5) == "MODERATE"
    assert engine.determine_strength(0.65) == "MODERATE"


def test_strength_strong(engine):
    """Test strong strength classification."""
    assert engine.determine_strength(0.66) == "STRONG"
    assert engine.determine_strength(0.9) == "STRONG"


# ══════════════════════════════════════════════════════════════
# Test Full Analysis
# ══════════════════════════════════════════════════════════════

def test_analyze_returns_valid_state(engine):
    """Test full analysis returns valid state."""
    state = engine.analyze("BTC")
    
    assert isinstance(state, ReflexivityState)
    assert state.symbol == "BTC"
    assert 0 <= state.reflexivity_score <= 1
    assert state.feedback_direction in ["POSITIVE", "NEGATIVE", "NEUTRAL"]
    assert state.strength in ["WEAK", "MODERATE", "STRONG"]
    assert state.sentiment_state in ["EXTREME_GREED", "GREED", "NEUTRAL", "FEAR", "EXTREME_FEAR"]
    assert -1 <= state.crowd_positioning <= 1
    assert 0 <= state.confidence <= 1


def test_analyze_caches_state(engine):
    """Test that analysis caches state."""
    state1 = engine.analyze("ETH")
    cached = engine.get_current_state("ETH")
    
    assert cached is not None
    assert cached.symbol == state1.symbol


# ══════════════════════════════════════════════════════════════
# Test Modifier
# ══════════════════════════════════════════════════════════════

def test_modifier_returns_valid(engine):
    """Test modifier returns valid structure."""
    modifier = engine.get_modifier("BTC", "LONG")
    
    assert isinstance(modifier, ReflexivityModifier)
    assert modifier.symbol == "BTC"
    assert 0 <= modifier.reflexivity_score <= 1
    assert modifier.reflexivity_weight == REFLEXIVITY_WEIGHT
    assert modifier.modifier > 0  # Should never be zero or negative


def test_modifier_weight_is_correct(engine):
    """Test modifier uses correct weight."""
    modifier = engine.get_modifier("SOL", "SHORT")
    
    assert modifier.reflexivity_weight == 0.06


def test_modifier_weighted_contribution(engine):
    """Test weighted contribution calculation."""
    modifier = engine.get_modifier("BTC", "LONG")
    
    expected = modifier.reflexivity_score * REFLEXIVITY_WEIGHT
    assert abs(modifier.weighted_contribution - expected) < 0.001


# ══════════════════════════════════════════════════════════════
# Test Edge Cases
# ══════════════════════════════════════════════════════════════

def test_zero_source_values(engine):
    """Test handling of zero source values."""
    zero_source = ReflexivitySource()
    
    sentiment = engine.calculate_sentiment_score(zero_source)
    positioning = engine.calculate_positioning_score(zero_source)
    
    assert sentiment == 0.0
    assert positioning == 0.0


def test_liquidation_imbalance_zero_total(engine):
    """Test liquidation imbalance with zero total."""
    imbalance = engine._calculate_liquidation_imbalance(0, 0)
    
    assert imbalance == 0.0


def test_multiple_symbols(engine):
    """Test analyzing multiple symbols."""
    symbols = ["BTC", "ETH", "SOL"]
    states = [engine.analyze(s) for s in symbols]
    
    assert len(states) == 3
    assert all(s.symbol == symbols[i] for i, s in enumerate(states))


# ══════════════════════════════════════════════════════════════
# Test Summary
# ══════════════════════════════════════════════════════════════

def test_summary_generation(engine):
    """Test summary generation."""
    # Analyze multiple times to build history
    for _ in range(5):
        engine.analyze("BTC")
    
    summary = engine.generate_summary("BTC")
    
    assert summary.symbol == "BTC"
    assert summary.total_records >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
