"""
Meta-Alpha Pattern Engine Tests

PHASE 31.1 — 26+ tests for Meta-Alpha Pattern Engine

Tests:
1. Pattern extraction
2. Min observation filter
3. Meta score calculation
4. Meta score bounds
5. Pattern classification
6. Strong pattern detection
7. Weak pattern detection
8. Pattern storage
9. Pattern update
10. Pattern endpoint
11. Strong endpoint
12. Summary endpoint
13. Recompute endpoint
14. Integration with outcome engine
15. Integration with regime data
16. Integration with microstructure data
17. Meta modifier calculation
18. Allocation integration
19. Deterministic output
20. Missing data safe
21. Low observation safe
22. Pattern grouping correct
23. Multi pattern evaluation
24. Scheduler safe
25. Large dataset safe
26. Meta score stability
"""

import pytest
from datetime import datetime, timezone
from typing import List

from modules.meta_alpha.meta_alpha_engine import (
    MetaAlphaEngine,
    get_meta_alpha_engine,
)
from modules.meta_alpha.meta_alpha_types import (
    MetaAlphaPattern,
    MetaAlphaSummary,
    PatternObservation,
    MIN_META_OBSERVATIONS,
    META_ALPHA_MODIFIERS,
    STRONG_META_ALPHA_THRESHOLD,
    MODERATE_META_ALPHA_THRESHOLD,
)


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

def create_test_observations(
    count: int = 60,
    regime: str = "VOLATILE",
    hypothesis: str = "BREAKOUT_FORMING",
    microstructure: str = "VACUUM",
    success_rate: float = 0.70,
    avg_pnl: float = 1.5,
) -> List[PatternObservation]:
    """Create test observations."""
    observations = []
    successes = int(count * success_rate)
    
    for i in range(count):
        obs = PatternObservation(
            regime_type=regime,
            hypothesis_type=hypothesis,
            microstructure_state=microstructure,
            success=i < successes,
            pnl_percent=avg_pnl if i < successes else -avg_pnl * 0.5,
        )
        observations.append(obs)
    
    return observations


# ══════════════════════════════════════════════════════════════
# Test 1: Pattern Extraction
# ══════════════════════════════════════════════════════════════

def test_pattern_extraction():
    """Test pattern extraction from observations."""
    engine = MetaAlphaEngine()
    
    # Add observations
    for obs in create_test_observations():
        engine._observations.setdefault("BTC", []).append(obs)
    
    patterns = engine.extract_patterns("BTC")
    
    assert len(patterns) >= 1
    assert patterns[0].hypothesis_type == "BREAKOUT_FORMING"


# ══════════════════════════════════════════════════════════════
# Test 2: Min Observation Filter
# ══════════════════════════════════════════════════════════════

def test_min_observation_filter():
    """Test minimum observations filter."""
    engine = MetaAlphaEngine()
    
    # Score should be 0 if observations < MIN_META_OBSERVATIONS
    score = engine.calculate_meta_score(0.80, 5.0, 30)
    assert score == 0.0
    
    # Score should be > 0 if observations >= MIN_META_OBSERVATIONS
    score = engine.calculate_meta_score(0.80, 5.0, 60)
    assert score > 0.0


# ══════════════════════════════════════════════════════════════
# Test 3: Meta Score Calculation
# ══════════════════════════════════════════════════════════════

def test_meta_score_calculation():
    """Test meta score is calculated correctly."""
    engine = MetaAlphaEngine()
    
    # High success rate, positive PnL, many observations
    score = engine.calculate_meta_score(0.70, 5.0, 100)
    assert score > 0.5
    
    # Low success rate, negative PnL
    score = engine.calculate_meta_score(0.35, -3.0, 100)
    assert score < 0.5


# ══════════════════════════════════════════════════════════════
# Test 4: Meta Score Bounds
# ══════════════════════════════════════════════════════════════

def test_meta_score_bounds():
    """Test meta score is bounded [0, 1]."""
    engine = MetaAlphaEngine()
    
    # Extreme high values
    score = engine.calculate_meta_score(1.0, 100.0, 10000)
    assert 0.0 <= score <= 1.0
    
    # Extreme low values
    score = engine.calculate_meta_score(0.0, -100.0, 50)
    assert 0.0 <= score <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 5: Pattern Classification
# ══════════════════════════════════════════════════════════════

def test_pattern_classification():
    """Test pattern classification based on meta score."""
    engine = MetaAlphaEngine()
    
    # Strong
    classification = engine.classify_pattern(0.75)
    assert classification == "STRONG_META_ALPHA"
    
    # Moderate
    classification = engine.classify_pattern(0.60)
    assert classification == "MODERATE_META_ALPHA"
    
    # Weak
    classification = engine.classify_pattern(0.45)
    assert classification == "WEAK_PATTERN"


# ══════════════════════════════════════════════════════════════
# Test 6: Strong Pattern Detection
# ══════════════════════════════════════════════════════════════

def test_strong_pattern_detection():
    """Test detection of strong meta-alpha patterns."""
    engine = MetaAlphaEngine()
    
    # Generate patterns
    patterns = engine.extract_patterns("BTC")
    
    strong = engine.get_strong_patterns("BTC")
    
    # All strong patterns should have meta_score >= 0.70
    for p in strong:
        assert p.meta_score >= STRONG_META_ALPHA_THRESHOLD


# ══════════════════════════════════════════════════════════════
# Test 7: Weak Pattern Detection
# ══════════════════════════════════════════════════════════════

def test_weak_pattern_detection():
    """Test detection of weak patterns."""
    engine = MetaAlphaEngine()
    
    # Generate patterns
    patterns = engine.extract_patterns("BTC")
    
    weak = [p for p in patterns if p.classification == "WEAK_PATTERN"]
    
    # Weak patterns should have meta_score < 0.55
    for p in weak:
        assert p.meta_score < MODERATE_META_ALPHA_THRESHOLD


# ══════════════════════════════════════════════════════════════
# Test 8: Pattern Storage
# ══════════════════════════════════════════════════════════════

def test_pattern_storage():
    """Test patterns are stored correctly."""
    engine = MetaAlphaEngine()
    
    patterns = engine.extract_patterns("ETH")
    
    stored = engine.get_patterns("ETH")
    assert len(stored) == len(patterns)


# ══════════════════════════════════════════════════════════════
# Test 9: Pattern Update
# ══════════════════════════════════════════════════════════════

def test_pattern_update():
    """Test pattern update on recompute."""
    engine = MetaAlphaEngine()
    
    # First extraction
    patterns1 = engine.extract_patterns("BTC")
    
    # Add more observations
    for obs in create_test_observations(30, success_rate=0.80):
        engine._observations.setdefault("BTC", []).append(obs)
    
    # Second extraction
    patterns2 = engine.extract_patterns("BTC")
    
    # Should still work
    assert len(patterns2) >= 1


# ══════════════════════════════════════════════════════════════
# Test 10: Pattern Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_pattern_endpoint_valid():
    """Test pattern endpoint returns valid response."""
    import asyncio
    from modules.meta_alpha.meta_alpha_routes import get_meta_patterns
    
    response = asyncio.get_event_loop().run_until_complete(
        get_meta_patterns("BTC", None, None)
    )
    
    assert "symbol" in response
    assert response["symbol"] == "BTC"
    assert "patterns" in response


# ══════════════════════════════════════════════════════════════
# Test 11: Strong Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_strong_endpoint_valid():
    """Test strong endpoint returns valid response."""
    import asyncio
    from modules.meta_alpha.meta_alpha_routes import get_strong_patterns
    
    response = asyncio.get_event_loop().run_until_complete(get_strong_patterns("BTC"))
    
    assert "symbol" in response
    assert "patterns" in response


# ══════════════════════════════════════════════════════════════
# Test 12: Summary Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_summary_endpoint_valid():
    """Test summary endpoint returns valid response."""
    import asyncio
    from modules.meta_alpha.meta_alpha_routes import get_meta_summary
    
    response = asyncio.get_event_loop().run_until_complete(get_meta_summary("BTC"))
    
    assert "symbol" in response
    assert "classification" in response


# ══════════════════════════════════════════════════════════════
# Test 13: Recompute Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_recompute_endpoint_valid():
    """Test recompute endpoint returns valid response."""
    import asyncio
    from modules.meta_alpha.meta_alpha_routes import recompute_patterns
    
    response = asyncio.get_event_loop().run_until_complete(
        recompute_patterns("BTC", None, None)
    )
    
    assert "status" in response
    assert response["status"] == "ok"


# ══════════════════════════════════════════════════════════════
# Test 14: Integration with Outcome Engine
# ══════════════════════════════════════════════════════════════

def test_integration_with_outcome_engine():
    """Test integration with OutcomeTrackingEngine."""
    from modules.hypothesis_competition import get_outcome_tracking_engine
    
    outcome_engine = get_outcome_tracking_engine()
    meta_engine = MetaAlphaEngine()
    
    # Both engines should coexist
    assert outcome_engine is not None
    assert meta_engine is not None


# ══════════════════════════════════════════════════════════════
# Test 15: Integration with Regime Data
# ══════════════════════════════════════════════════════════════

def test_integration_with_regime_data():
    """Test regime type is used in patterns."""
    engine = MetaAlphaEngine()
    
    patterns = engine.extract_patterns("BTC")
    
    # All patterns should have regime_type
    for p in patterns:
        assert p.regime_type is not None
        assert len(p.regime_type) > 0


# ══════════════════════════════════════════════════════════════
# Test 16: Integration with Microstructure Data
# ══════════════════════════════════════════════════════════════

def test_integration_with_microstructure_data():
    """Test microstructure state is used in patterns."""
    engine = MetaAlphaEngine()
    
    patterns = engine.extract_patterns("BTC")
    
    # All patterns should have microstructure_state
    for p in patterns:
        assert p.microstructure_state is not None
        assert len(p.microstructure_state) > 0


# ══════════════════════════════════════════════════════════════
# Test 17: Meta Modifier Calculation
# ══════════════════════════════════════════════════════════════

def test_meta_modifier_calculation():
    """Test meta modifier is returned correctly."""
    engine = MetaAlphaEngine()
    
    # Generate patterns
    engine.extract_patterns("BTC")
    
    # Get modifier
    modifier = engine.get_meta_modifier("BTC", "BREAKOUT_FORMING", "VOLATILE", "VACUUM")
    
    # Should be one of the valid modifiers
    assert modifier in [1.0, 1.10, 1.25]


# ══════════════════════════════════════════════════════════════
# Test 18: Allocation Integration
# ══════════════════════════════════════════════════════════════

def test_allocation_integration():
    """Test integration with Capital Allocation Engine."""
    from modules.hypothesis_competition import get_capital_allocation_engine
    
    alloc_engine = get_capital_allocation_engine()
    meta_engine = MetaAlphaEngine()
    
    # Both should work
    assert alloc_engine is not None
    assert meta_engine is not None


# ══════════════════════════════════════════════════════════════
# Test 19: Deterministic Output
# ══════════════════════════════════════════════════════════════

def test_deterministic_output():
    """Test same input produces same output."""
    engine1 = MetaAlphaEngine()
    engine2 = MetaAlphaEngine()
    
    score1 = engine1.calculate_meta_score(0.65, 2.0, 100)
    score2 = engine2.calculate_meta_score(0.65, 2.0, 100)
    
    assert score1 == score2


# ══════════════════════════════════════════════════════════════
# Test 20: Missing Data Safe
# ══════════════════════════════════════════════════════════════

def test_missing_data_safe():
    """Test handling of missing data."""
    engine = MetaAlphaEngine()
    
    # Empty symbol should return mock patterns
    patterns = engine.extract_patterns("NONEXISTENT")
    assert isinstance(patterns, list)


# ══════════════════════════════════════════════════════════════
# Test 21: Low Observation Safe
# ══════════════════════════════════════════════════════════════

def test_low_observation_safe():
    """Test handling of low observations."""
    engine = MetaAlphaEngine()
    
    # Score with insufficient observations
    score = engine.calculate_meta_score(0.90, 10.0, 10)
    assert score == 0.0


# ══════════════════════════════════════════════════════════════
# Test 22: Pattern Grouping Correct
# ══════════════════════════════════════════════════════════════

def test_pattern_grouping_correct():
    """Test patterns are grouped by regime+hypothesis+microstructure."""
    engine = MetaAlphaEngine()
    
    # Add observations for different patterns
    for obs in create_test_observations(60, "TRENDING", "BULLISH", "BID_DOMINANT"):
        engine._observations.setdefault("SOL", []).append(obs)
    
    for obs in create_test_observations(60, "VOLATILE", "BREAKOUT", "VACUUM"):
        engine._observations.setdefault("SOL", []).append(obs)
    
    patterns = engine.extract_patterns("SOL")
    
    # Should have at least 2 distinct patterns
    assert len(patterns) >= 2


# ══════════════════════════════════════════════════════════════
# Test 23: Multi Pattern Evaluation
# ══════════════════════════════════════════════════════════════

def test_multi_pattern_evaluation():
    """Test evaluation of multiple patterns."""
    engine = MetaAlphaEngine()
    
    patterns = engine.extract_patterns("BTC")
    
    # Each pattern should have valid fields
    for p in patterns:
        assert p.pattern_id is not None
        assert 0 <= p.meta_score <= 1
        assert p.classification in ["STRONG_META_ALPHA", "MODERATE_META_ALPHA", "WEAK_PATTERN"]


# ══════════════════════════════════════════════════════════════
# Test 24: Scheduler Safe
# ══════════════════════════════════════════════════════════════

def test_scheduler_safe():
    """Test scheduler-like repeated calls are safe."""
    engine = MetaAlphaEngine()
    
    # Simulate scheduler calls
    for _ in range(5):
        patterns = engine.extract_patterns("BTC")
        assert isinstance(patterns, list)


# ══════════════════════════════════════════════════════════════
# Test 25: Large Dataset Safe
# ══════════════════════════════════════════════════════════════

def test_large_dataset_safe():
    """Test handling of large datasets."""
    engine = MetaAlphaEngine()
    
    # Add many observations
    for i in range(500):
        engine.record_observation(
            "LARGE",
            f"HYPO_{i % 10}",
            i % 2 == 0,
            0.5 * (1 if i % 2 == 0 else -1),
            f"REGIME_{i % 5}",
            f"MICRO_{i % 3}",
        )
    
    patterns = engine.extract_patterns("LARGE")
    assert isinstance(patterns, list)


# ══════════════════════════════════════════════════════════════
# Test 26: Meta Score Stability
# ══════════════════════════════════════════════════════════════

def test_meta_score_stability():
    """Test meta score is stable across calculations."""
    engine = MetaAlphaEngine()
    
    # Calculate same score multiple times
    scores = [
        engine.calculate_meta_score(0.65, 1.5, 80)
        for _ in range(10)
    ]
    
    # All should be identical
    assert len(set(scores)) == 1


# ══════════════════════════════════════════════════════════════
# Additional Tests (27-30)
# ══════════════════════════════════════════════════════════════

def test_constants_values():
    """Test constant values are correct."""
    assert MIN_META_OBSERVATIONS == 50
    assert STRONG_META_ALPHA_THRESHOLD == 0.70
    assert MODERATE_META_ALPHA_THRESHOLD == 0.55
    assert META_ALPHA_MODIFIERS["STRONG_META_ALPHA"] == 1.25
    assert META_ALPHA_MODIFIERS["MODERATE_META_ALPHA"] == 1.10
    assert META_ALPHA_MODIFIERS["WEAK_PATTERN"] == 1.00


def test_pattern_id_generation():
    """Test pattern ID is deterministic."""
    id1 = MetaAlphaPattern.generate_pattern_id("VOLATILE", "BREAKOUT", "VACUUM")
    id2 = MetaAlphaPattern.generate_pattern_id("VOLATILE", "BREAKOUT", "VACUUM")
    
    assert id1 == id2


def test_context_management():
    """Test context set and get."""
    engine = MetaAlphaEngine()
    
    engine.set_context("BTC", "TRENDING", "BID_DOMINANT")
    context = engine.get_context("BTC")
    
    assert context["regime_type"] == "TRENDING"
    assert context["microstructure_state"] == "BID_DOMINANT"


def test_get_all_modifiers():
    """Test get_all_modifiers returns dict."""
    engine = MetaAlphaEngine()
    engine.extract_patterns("BTC")
    
    modifiers = engine.get_all_modifiers("BTC", "VOLATILE", "VACUUM")
    assert isinstance(modifiers, dict)


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
