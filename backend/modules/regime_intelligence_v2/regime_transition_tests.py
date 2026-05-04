"""
Regime Transition Detector — Tests

Test suite for transition detection.

Required tests (18):
1. trend->range detection
2. trend->volatile detection
3. range->trend detection
4. range->illiquid detection
5. volatile->trend detection
6. volatile->illiquid detection
7. illiquid->range detection
8. illiquid->trend detection
9. transition_score calculation
10. transition_probability calculation
11. stable classification
12. early_shift classification
13. active_transition classification
14. unstable classification
15. trigger_factors extraction
16. registry write
17. current endpoint
18. summary endpoint
"""

import pytest
from datetime import datetime

from modules.regime_intelligence_v2.regime_transition_types import (
    RegimeTransitionState,
    RegimeMetricSnapshot,
    TransitionHistoryRecord,
    TransitionSummary,
    STABLE_THRESHOLD,
    EARLY_SHIFT_THRESHOLD,
    ACTIVE_TRANSITION_THRESHOLD,
    TRANSITION_MODIFIERS,
)
from modules.regime_intelligence_v2.regime_transition_engine import (
    RegimeTransitionEngine,
    get_regime_transition_engine,
)
from modules.regime_intelligence_v2.regime_transition_registry import (
    RegimeTransitionRegistry,
    get_regime_transition_registry,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def transition_engine():
    """Create fresh transition engine."""
    return RegimeTransitionEngine()


@pytest.fixture
def transition_registry():
    """Create fresh transition registry."""
    return RegimeTransitionRegistry()


# ══════════════════════════════════════════════════════════════
# Snapshot Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def trending_current():
    """Current TRENDING regime with falling trend."""
    return RegimeMetricSnapshot(
        regime_type="TRENDING",
        trend_strength=0.35,  # Falling
        volatility_level=0.25,
        liquidity_level=0.70,
        regime_confidence=0.60,
        dominant_driver="TREND",
    )


@pytest.fixture
def trending_previous():
    """Previous TRENDING regime with higher trend."""
    return RegimeMetricSnapshot(
        regime_type="TRENDING",
        trend_strength=0.50,  # Was higher
        volatility_level=0.20,
        liquidity_level=0.75,
        regime_confidence=0.70,
        dominant_driver="TREND",
    )


@pytest.fixture
def trending_volatile_current():
    """TRENDING regime with rising volatility."""
    return RegimeMetricSnapshot(
        regime_type="TRENDING",
        trend_strength=0.45,
        volatility_level=0.55,  # Rising
        liquidity_level=0.65,
        regime_confidence=0.55,
        dominant_driver="VOLATILITY",
    )


@pytest.fixture
def trending_volatile_previous():
    """Previous TRENDING regime with lower volatility."""
    return RegimeMetricSnapshot(
        regime_type="TRENDING",
        trend_strength=0.48,
        volatility_level=0.35,  # Was lower
        liquidity_level=0.70,
        regime_confidence=0.65,
        dominant_driver="TREND",
    )


@pytest.fixture
def ranging_current():
    """RANGING regime with rising trend."""
    return RegimeMetricSnapshot(
        regime_type="RANGING",
        trend_strength=0.30,  # Rising
        volatility_level=0.25,
        liquidity_level=0.70,
        regime_confidence=0.60,
        dominant_driver="TREND",
    )


@pytest.fixture
def ranging_previous():
    """Previous RANGING regime with lower trend."""
    return RegimeMetricSnapshot(
        regime_type="RANGING",
        trend_strength=0.15,  # Was lower
        volatility_level=0.22,
        liquidity_level=0.72,
        regime_confidence=0.65,
        dominant_driver="VOLATILITY",
    )


@pytest.fixture
def ranging_illiquid_current():
    """RANGING regime with falling liquidity."""
    return RegimeMetricSnapshot(
        regime_type="RANGING",
        trend_strength=0.15,
        volatility_level=0.25,
        liquidity_level=0.25,  # Falling
        regime_confidence=0.50,
        dominant_driver="LIQUIDITY",
    )


@pytest.fixture
def ranging_illiquid_previous():
    """Previous RANGING regime with normal liquidity."""
    return RegimeMetricSnapshot(
        regime_type="RANGING",
        trend_strength=0.18,
        volatility_level=0.22,
        liquidity_level=0.55,  # Was higher
        regime_confidence=0.60,
        dominant_driver="VOLATILITY",
    )


@pytest.fixture
def volatile_current():
    """VOLATILE regime with falling volatility and rising trend."""
    return RegimeMetricSnapshot(
        regime_type="VOLATILE",
        trend_strength=0.40,  # Rising
        volatility_level=0.45,  # Falling
        liquidity_level=0.60,
        regime_confidence=0.55,
        dominant_driver="TREND",
    )


@pytest.fixture
def volatile_previous():
    """Previous VOLATILE regime."""
    return RegimeMetricSnapshot(
        regime_type="VOLATILE",
        trend_strength=0.30,  # Was lower
        volatility_level=0.65,  # Was higher
        liquidity_level=0.55,
        regime_confidence=0.50,
        dominant_driver="VOLATILITY",
    )


@pytest.fixture
def volatile_illiquid_current():
    """VOLATILE regime with falling liquidity."""
    return RegimeMetricSnapshot(
        regime_type="VOLATILE",
        trend_strength=0.30,
        volatility_level=0.60,
        liquidity_level=0.20,  # Falling
        regime_confidence=0.45,
        dominant_driver="LIQUIDITY",
    )


@pytest.fixture
def volatile_illiquid_previous():
    """Previous VOLATILE regime with normal liquidity."""
    return RegimeMetricSnapshot(
        regime_type="VOLATILE",
        trend_strength=0.32,
        volatility_level=0.58,
        liquidity_level=0.50,  # Was higher
        regime_confidence=0.55,
        dominant_driver="VOLATILITY",
    )


@pytest.fixture
def illiquid_current():
    """ILLIQUID regime with recovering liquidity."""
    return RegimeMetricSnapshot(
        regime_type="ILLIQUID",
        trend_strength=0.15,
        volatility_level=0.35,
        liquidity_level=0.45,  # Recovering
        regime_confidence=0.50,
        dominant_driver="LIQUIDITY",
    )


@pytest.fixture
def illiquid_previous():
    """Previous ILLIQUID regime with low liquidity."""
    return RegimeMetricSnapshot(
        regime_type="ILLIQUID",
        trend_strength=0.12,
        volatility_level=0.38,
        liquidity_level=0.22,  # Was lower
        regime_confidence=0.45,
        dominant_driver="LIQUIDITY",
    )


@pytest.fixture
def illiquid_trend_current():
    """ILLIQUID regime with recovering liquidity and rising trend."""
    return RegimeMetricSnapshot(
        regime_type="ILLIQUID",
        trend_strength=0.30,  # Rising
        volatility_level=0.30,
        liquidity_level=0.45,  # Recovering
        regime_confidence=0.55,
        dominant_driver="TREND",
    )


@pytest.fixture
def illiquid_trend_previous():
    """Previous ILLIQUID regime."""
    return RegimeMetricSnapshot(
        regime_type="ILLIQUID",
        trend_strength=0.18,  # Was lower
        volatility_level=0.32,
        liquidity_level=0.25,  # Was lower
        regime_confidence=0.48,
        dominant_driver="LIQUIDITY",
    )


# ══════════════════════════════════════════════════════════════
# Test 1: TRENDING → RANGING Detection
# ══════════════════════════════════════════════════════════════

def test_trend_to_range_detection(transition_engine, trending_current, trending_previous):
    """Test 1: Detect TRENDING → RANGING transition."""
    next_regime = transition_engine.detect_next_regime_candidate(
        trending_current,
        trending_previous,
    )
    
    assert next_regime == "RANGING"


# ══════════════════════════════════════════════════════════════
# Test 2: TRENDING → VOLATILE Detection
# ══════════════════════════════════════════════════════════════

def test_trend_to_volatile_detection(transition_engine, trending_volatile_current, trending_volatile_previous):
    """Test 2: Detect TRENDING → VOLATILE transition."""
    next_regime = transition_engine.detect_next_regime_candidate(
        trending_volatile_current,
        trending_volatile_previous,
    )
    
    assert next_regime == "VOLATILE"


# ══════════════════════════════════════════════════════════════
# Test 3: RANGING → TRENDING Detection
# ══════════════════════════════════════════════════════════════

def test_range_to_trend_detection(transition_engine, ranging_current, ranging_previous):
    """Test 3: Detect RANGING → TRENDING transition."""
    next_regime = transition_engine.detect_next_regime_candidate(
        ranging_current,
        ranging_previous,
    )
    
    assert next_regime == "TRENDING"


# ══════════════════════════════════════════════════════════════
# Test 4: RANGING → ILLIQUID Detection
# ══════════════════════════════════════════════════════════════

def test_range_to_illiquid_detection(transition_engine, ranging_illiquid_current, ranging_illiquid_previous):
    """Test 4: Detect RANGING → ILLIQUID transition."""
    next_regime = transition_engine.detect_next_regime_candidate(
        ranging_illiquid_current,
        ranging_illiquid_previous,
    )
    
    assert next_regime == "ILLIQUID"


# ══════════════════════════════════════════════════════════════
# Test 5: VOLATILE → TRENDING Detection
# ══════════════════════════════════════════════════════════════

def test_volatile_to_trend_detection(transition_engine, volatile_current, volatile_previous):
    """Test 5: Detect VOLATILE → TRENDING transition."""
    next_regime = transition_engine.detect_next_regime_candidate(
        volatile_current,
        volatile_previous,
    )
    
    assert next_regime == "TRENDING"


# ══════════════════════════════════════════════════════════════
# Test 6: VOLATILE → ILLIQUID Detection
# ══════════════════════════════════════════════════════════════

def test_volatile_to_illiquid_detection(transition_engine, volatile_illiquid_current, volatile_illiquid_previous):
    """Test 6: Detect VOLATILE → ILLIQUID transition."""
    next_regime = transition_engine.detect_next_regime_candidate(
        volatile_illiquid_current,
        volatile_illiquid_previous,
    )
    
    assert next_regime == "ILLIQUID"


# ══════════════════════════════════════════════════════════════
# Test 7: ILLIQUID → RANGING Detection
# ══════════════════════════════════════════════════════════════

def test_illiquid_to_range_detection(transition_engine, illiquid_current, illiquid_previous):
    """Test 7: Detect ILLIQUID → RANGING transition."""
    next_regime = transition_engine.detect_next_regime_candidate(
        illiquid_current,
        illiquid_previous,
    )
    
    assert next_regime == "RANGING"


# ══════════════════════════════════════════════════════════════
# Test 8: ILLIQUID → TRENDING Detection
# ══════════════════════════════════════════════════════════════

def test_illiquid_to_trend_detection(transition_engine, illiquid_trend_current, illiquid_trend_previous):
    """Test 8: Detect ILLIQUID → TRENDING transition."""
    next_regime = transition_engine.detect_next_regime_candidate(
        illiquid_trend_current,
        illiquid_trend_previous,
    )
    
    assert next_regime == "TRENDING"


# ══════════════════════════════════════════════════════════════
# Test 9: Transition Score Calculation
# ══════════════════════════════════════════════════════════════

def test_transition_score_calculation(transition_engine, trending_current, trending_previous):
    """Test 9: Transition score is calculated correctly."""
    score = transition_engine.calculate_transition_score(
        trending_current,
        trending_previous,
    )
    
    # Score should be positive when metrics change
    assert 0.0 <= score <= 1.0
    assert score > 0  # Some change occurred


def test_transition_score_no_change(transition_engine):
    """Test score is zero when no change."""
    snapshot = RegimeMetricSnapshot(
        regime_type="TRENDING",
        trend_strength=0.50,
        volatility_level=0.30,
        liquidity_level=0.70,
        regime_confidence=0.65,
        dominant_driver="TREND",
    )
    
    score = transition_engine.calculate_transition_score(snapshot, snapshot)
    assert score == 0.0


# ══════════════════════════════════════════════════════════════
# Test 10: Transition Probability Calculation
# ══════════════════════════════════════════════════════════════

def test_transition_probability_calculation(transition_engine):
    """Test 10: Transition probability is calculated correctly."""
    # Formula: prob = 0.70 * score + 0.30 * (1 - confidence)
    
    # High score, low confidence = high probability
    prob_high = transition_engine.calculate_transition_probability(0.80, 0.30)
    assert prob_high > 0.6
    
    # Low score, high confidence = low probability
    prob_low = transition_engine.calculate_transition_probability(0.10, 0.90)
    assert prob_low < 0.15


def test_transition_probability_bounds(transition_engine):
    """Test probability is bounded 0-1."""
    prob = transition_engine.calculate_transition_probability(1.0, 0.0)
    assert 0.0 <= prob <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 11: STABLE Classification
# ══════════════════════════════════════════════════════════════

def test_stable_classification(transition_engine):
    """Test 11: STABLE classification when probability < 0.25."""
    state = transition_engine.classify_transition_state(0.20)
    assert state == "STABLE"


# ══════════════════════════════════════════════════════════════
# Test 12: EARLY_SHIFT Classification
# ══════════════════════════════════════════════════════════════

def test_early_shift_classification(transition_engine):
    """Test 12: EARLY_SHIFT classification when 0.25 ≤ prob < 0.45."""
    state = transition_engine.classify_transition_state(0.35)
    assert state == "EARLY_SHIFT"


# ══════════════════════════════════════════════════════════════
# Test 13: ACTIVE_TRANSITION Classification
# ══════════════════════════════════════════════════════════════

def test_active_transition_classification(transition_engine):
    """Test 13: ACTIVE_TRANSITION classification when 0.45 ≤ prob < 0.70."""
    state = transition_engine.classify_transition_state(0.55)
    assert state == "ACTIVE_TRANSITION"


# ══════════════════════════════════════════════════════════════
# Test 14: UNSTABLE Classification
# ══════════════════════════════════════════════════════════════

def test_unstable_classification(transition_engine):
    """Test 14: UNSTABLE classification when prob ≥ 0.70."""
    state = transition_engine.classify_transition_state(0.75)
    assert state == "UNSTABLE"


# ══════════════════════════════════════════════════════════════
# Test 15: Trigger Factors Extraction
# ══════════════════════════════════════════════════════════════

def test_trigger_factors_extraction(transition_engine, trending_current, trending_previous):
    """Test 15: Trigger factors are extracted correctly."""
    triggers = transition_engine.extract_trigger_factors(
        trending_current,
        trending_previous,
    )
    
    assert isinstance(triggers, list)
    # Should detect trend decay and confidence drop
    assert any("trend" in t for t in triggers) or any("confidence" in t for t in triggers)


def test_trigger_volatility_expansion(transition_engine, trending_volatile_current, trending_volatile_previous):
    """Test volatility expansion trigger."""
    triggers = transition_engine.extract_trigger_factors(
        trending_volatile_current,
        trending_volatile_previous,
    )
    
    assert "volatility_expansion" in triggers


# ══════════════════════════════════════════════════════════════
# Test 16: Registry Write
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_write(transition_registry, transition_engine, trending_current, trending_previous):
    """Test 16: Transition can be stored in registry."""
    transition = transition_engine.detect_transition(
        trending_current,
        trending_previous,
    )
    
    record = await transition_registry.store_transition(transition)
    
    assert record.current_regime == transition.current_regime
    assert record.transition_state == transition.transition_state


# ══════════════════════════════════════════════════════════════
# Test 17: Current Endpoint
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_current_endpoint(transition_engine):
    """Test 17: Current transition can be detected."""
    transition = await transition_engine.detect_transition_from_history()
    
    assert transition is not None
    assert transition.current_regime in ["TRENDING", "RANGING", "VOLATILE", "ILLIQUID"]
    assert transition.transition_state in ["STABLE", "EARLY_SHIFT", "ACTIVE_TRANSITION", "UNSTABLE"]


# ══════════════════════════════════════════════════════════════
# Test 18: Summary Endpoint
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_summary_endpoint(transition_registry, transition_engine, trending_current, trending_previous):
    """Test 18: Summary can be generated."""
    # Store some transitions
    for _ in range(3):
        transition = transition_engine.detect_transition(
            trending_current,
            trending_previous,
        )
        await transition_registry.store_transition(transition)
    
    summary = await transition_registry.get_summary("BTCUSDT", "1H")
    
    assert summary.total_records >= 3
    assert summary.current_state in ["STABLE", "EARLY_SHIFT", "ACTIVE_TRANSITION", "UNSTABLE"]


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

def test_thresholds():
    """Test all thresholds are correct."""
    assert STABLE_THRESHOLD == 0.25
    assert EARLY_SHIFT_THRESHOLD == 0.45
    assert ACTIVE_TRANSITION_THRESHOLD == 0.70


def test_modifiers():
    """Test modifiers are correct."""
    assert TRANSITION_MODIFIERS["STABLE"]["confidence_modifier"] == 1.00
    assert TRANSITION_MODIFIERS["EARLY_SHIFT"]["confidence_modifier"] == 0.97
    assert TRANSITION_MODIFIERS["ACTIVE_TRANSITION"]["confidence_modifier"] == 0.92
    assert TRANSITION_MODIFIERS["UNSTABLE"]["confidence_modifier"] == 0.85


def test_full_transition_detection(transition_engine, trending_current, trending_previous):
    """Test full transition detection flow."""
    transition = transition_engine.detect_transition(
        trending_current,
        trending_previous,
    )
    
    assert transition.current_regime == "TRENDING"
    assert transition.next_regime_candidate in ["TRENDING", "RANGING", "VOLATILE", "ILLIQUID", "NONE"]
    assert 0.0 <= transition.transition_probability <= 1.0
    assert transition.transition_state in ["STABLE", "EARLY_SHIFT", "ACTIVE_TRANSITION", "UNSTABLE"]
    assert len(transition.reason) > 0


def test_reason_generation(transition_engine, trending_current, trending_previous):
    """Test reason is generated."""
    transition = transition_engine.detect_transition(
        trending_current,
        trending_previous,
    )
    
    assert "trending" in transition.reason.lower()


def test_singleton_pattern():
    """Test singleton pattern for engine."""
    engine1 = get_regime_transition_engine()
    engine2 = get_regime_transition_engine()
    assert engine1 is engine2


def test_none_candidate_when_stable(transition_engine):
    """Test NONE candidate when no clear transition."""
    stable = RegimeMetricSnapshot(
        regime_type="TRENDING",
        trend_strength=0.50,
        volatility_level=0.30,
        liquidity_level=0.70,
        regime_confidence=0.65,
        dominant_driver="TREND",
    )
    
    # Minimal change
    stable_prev = RegimeMetricSnapshot(
        regime_type="TRENDING",
        trend_strength=0.48,
        volatility_level=0.29,
        liquidity_level=0.71,
        regime_confidence=0.66,
        dominant_driver="TREND",
    )
    
    next_regime = transition_engine.detect_next_regime_candidate(stable, stable_prev)
    assert next_regime == "NONE"
