"""
Hypothesis Conflict Resolver — Tests

PHASE 29.3 — 15+ tests for Hypothesis Conflict Resolver

Tests:
1. low conflict detection
2. moderate conflict detection
3. high conflict detection
4. confidence reduction moderate
5. confidence reduction high
6. reliability reduction moderate
7. reliability reduction high
8. execution_state downgrade moderate
9. execution_state forced unfavorable
10. reason modification
11. integration with scoring engine
12. conflict edge case
13. endpoint returns conflict_state
14. recompute endpoint works
15. history stores conflict_state
16. should_block_trade
17. get_conflict_severity
"""

import pytest
from datetime import datetime

from modules.hypothesis_engine.hypothesis_conflict_resolver import (
    HypothesisConflictResolver,
    get_hypothesis_conflict_resolver,
    ConflictState,
    ConflictResolutionResult,
    CONFLICT_LOW_THRESHOLD,
    CONFLICT_HIGH_THRESHOLD,
    MODERATE_CONFIDENCE_MODIFIER,
    MODERATE_RELIABILITY_MODIFIER,
    HIGH_CONFIDENCE_MODIFIER,
    HIGH_RELIABILITY_MODIFIER,
)
from modules.hypothesis_engine.hypothesis_engine import (
    HypothesisEngine,
    get_hypothesis_engine,
)
from modules.hypothesis_engine.hypothesis_types import (
    HypothesisInputLayers,
)


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def conflict_resolver():
    """Create a fresh conflict resolver for each test."""
    return HypothesisConflictResolver()


@pytest.fixture
def hypothesis_engine():
    """Create a fresh hypothesis engine for each test."""
    return HypothesisEngine()


@pytest.fixture
def low_conflict_layers():
    """Layers with low conflict (aligned signals)."""
    return HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.7,
        regime_type="TRENDING",
        regime_confidence=0.72,
        microstructure_state="SUPPORTIVE",
        microstructure_confidence=0.68,
        macro_confidence=0.65,
    )


@pytest.fixture
def moderate_conflict_layers():
    """Layers with moderate conflict."""
    return HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.75,
        regime_type="RANGING",  # Mismatch with bullish alpha
        regime_confidence=0.5,
        microstructure_state="NEUTRAL",
        microstructure_confidence=0.6,
        macro_confidence=0.5,
    )


@pytest.fixture
def high_conflict_layers():
    """Layers with high conflict (chaotic signals)."""
    return HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.85,  # Very bullish alpha
        regime_type="VOLATILE",
        regime_confidence=0.3,  # Low regime confidence
        microstructure_state="STRESSED",  # Stressed microstructure
        microstructure_confidence=0.2,  # Very low
        macro_confidence=0.4,
    )


# ══════════════════════════════════════════════════════════════
# Test 1: Low Conflict Detection
# ══════════════════════════════════════════════════════════════

def test_low_conflict_detection(conflict_resolver):
    """Test detection of LOW conflict state."""
    conflict_state = conflict_resolver.detect_conflict_state(0.05)
    assert conflict_state == ConflictState.LOW
    
    conflict_state = conflict_resolver.detect_conflict_state(0.09)
    assert conflict_state == ConflictState.LOW


# ══════════════════════════════════════════════════════════════
# Test 2: Moderate Conflict Detection
# ══════════════════════════════════════════════════════════════

def test_moderate_conflict_detection(conflict_resolver):
    """Test detection of MODERATE conflict state."""
    conflict_state = conflict_resolver.detect_conflict_state(0.10)
    assert conflict_state == ConflictState.MODERATE
    
    conflict_state = conflict_resolver.detect_conflict_state(0.20)
    assert conflict_state == ConflictState.MODERATE
    
    conflict_state = conflict_resolver.detect_conflict_state(0.24)
    assert conflict_state == ConflictState.MODERATE


# ══════════════════════════════════════════════════════════════
# Test 3: High Conflict Detection
# ══════════════════════════════════════════════════════════════

def test_high_conflict_detection(conflict_resolver):
    """Test detection of HIGH conflict state."""
    conflict_state = conflict_resolver.detect_conflict_state(0.25)
    assert conflict_state == ConflictState.HIGH
    
    conflict_state = conflict_resolver.detect_conflict_state(0.40)
    assert conflict_state == ConflictState.HIGH
    
    conflict_state = conflict_resolver.detect_conflict_state(0.80)
    assert conflict_state == ConflictState.HIGH


# ══════════════════════════════════════════════════════════════
# Test 4: Confidence Reduction Moderate
# ══════════════════════════════════════════════════════════════

def test_confidence_reduction_moderate(conflict_resolver):
    """Test confidence reduction for MODERATE conflict."""
    original_confidence = 0.70
    
    adjusted = conflict_resolver.adjust_confidence(
        original_confidence, ConflictState.MODERATE
    )
    
    expected = round(original_confidence * MODERATE_CONFIDENCE_MODIFIER, 4)
    assert adjusted == expected
    assert adjusted < original_confidence


# ══════════════════════════════════════════════════════════════
# Test 5: Confidence Reduction High
# ══════════════════════════════════════════════════════════════

def test_confidence_reduction_high(conflict_resolver):
    """Test confidence reduction for HIGH conflict."""
    original_confidence = 0.70
    
    adjusted = conflict_resolver.adjust_confidence(
        original_confidence, ConflictState.HIGH
    )
    
    expected = round(original_confidence * HIGH_CONFIDENCE_MODIFIER, 4)
    assert adjusted == expected
    assert adjusted < original_confidence * MODERATE_CONFIDENCE_MODIFIER


# ══════════════════════════════════════════════════════════════
# Test 6: Reliability Reduction Moderate
# ══════════════════════════════════════════════════════════════

def test_reliability_reduction_moderate(conflict_resolver):
    """Test reliability reduction for MODERATE conflict."""
    original_reliability = 0.60
    
    adjusted = conflict_resolver.adjust_reliability(
        original_reliability, ConflictState.MODERATE
    )
    
    expected = round(original_reliability * MODERATE_RELIABILITY_MODIFIER, 4)
    assert adjusted == expected
    assert adjusted < original_reliability


# ══════════════════════════════════════════════════════════════
# Test 7: Reliability Reduction High
# ══════════════════════════════════════════════════════════════

def test_reliability_reduction_high(conflict_resolver):
    """Test reliability reduction for HIGH conflict."""
    original_reliability = 0.60
    
    adjusted = conflict_resolver.adjust_reliability(
        original_reliability, ConflictState.HIGH
    )
    
    expected = round(original_reliability * HIGH_RELIABILITY_MODIFIER, 4)
    assert adjusted == expected
    assert adjusted < original_reliability * MODERATE_RELIABILITY_MODIFIER


# ══════════════════════════════════════════════════════════════
# Test 8: Execution State Downgrade Moderate
# ══════════════════════════════════════════════════════════════

def test_execution_state_downgrade_moderate(conflict_resolver):
    """Test execution state downgrade for MODERATE conflict."""
    # FAVORABLE → CAUTIOUS
    adjusted = conflict_resolver.adjust_execution_state(
        "FAVORABLE", ConflictState.MODERATE
    )
    assert adjusted == "CAUTIOUS"
    
    # CAUTIOUS → CAUTIOUS (no change)
    adjusted = conflict_resolver.adjust_execution_state(
        "CAUTIOUS", ConflictState.MODERATE
    )
    assert adjusted == "CAUTIOUS"
    
    # UNFAVORABLE → UNFAVORABLE (no change)
    adjusted = conflict_resolver.adjust_execution_state(
        "UNFAVORABLE", ConflictState.MODERATE
    )
    assert adjusted == "UNFAVORABLE"


# ══════════════════════════════════════════════════════════════
# Test 9: Execution State Forced Unfavorable
# ══════════════════════════════════════════════════════════════

def test_execution_state_forced_unfavorable(conflict_resolver):
    """Test execution state forced to UNFAVORABLE for HIGH conflict."""
    # FAVORABLE → UNFAVORABLE
    adjusted = conflict_resolver.adjust_execution_state(
        "FAVORABLE", ConflictState.HIGH
    )
    assert adjusted == "UNFAVORABLE"
    
    # CAUTIOUS → UNFAVORABLE
    adjusted = conflict_resolver.adjust_execution_state(
        "CAUTIOUS", ConflictState.HIGH
    )
    assert adjusted == "UNFAVORABLE"
    
    # UNFAVORABLE → UNFAVORABLE
    adjusted = conflict_resolver.adjust_execution_state(
        "UNFAVORABLE", ConflictState.HIGH
    )
    assert adjusted == "UNFAVORABLE"


# ══════════════════════════════════════════════════════════════
# Test 10: Reason Modification
# ══════════════════════════════════════════════════════════════

def test_reason_modification(conflict_resolver):
    """Test reason generation for conflicts."""
    # LOW conflict - no reason
    reason = conflict_resolver.generate_conflict_reason(
        ConflictState.LOW, 0.7, 0.7, 0.7, "BULLISH_CONTINUATION"
    )
    assert reason == ""
    
    # MODERATE conflict - should have reason
    reason = conflict_resolver.generate_conflict_reason(
        ConflictState.MODERATE, 0.8, 0.4, 0.6, "BULLISH_CONTINUATION"
    )
    assert len(reason) > 0
    
    # HIGH conflict - should have detailed reason
    reason = conflict_resolver.generate_conflict_reason(
        ConflictState.HIGH, 0.9, 0.3, 0.2, "BULLISH_CONTINUATION"
    )
    assert len(reason) > 0
    assert "reduces reliability" in reason.lower() or "conflict" in reason.lower()


# ══════════════════════════════════════════════════════════════
# Test 11: Integration with Hypothesis Engine
# ══════════════════════════════════════════════════════════════

def test_integration_with_hypothesis_engine(hypothesis_engine, low_conflict_layers):
    """Test that hypothesis engine uses conflict resolver."""
    hypothesis = hypothesis_engine.generate_hypothesis(
        symbol="BTC",
        layers=low_conflict_layers,
    )
    
    # Should have conflict_state field
    assert hasattr(hypothesis, "conflict_state")
    assert hypothesis.conflict_state in ["LOW_CONFLICT", "MODERATE_CONFLICT", "HIGH_CONFLICT"]


# ══════════════════════════════════════════════════════════════
# Test 12: Conflict Edge Case
# ══════════════════════════════════════════════════════════════

def test_conflict_edge_case(conflict_resolver):
    """Test edge cases at thresholds."""
    # Exactly at LOW threshold boundary
    state = conflict_resolver.detect_conflict_state(CONFLICT_LOW_THRESHOLD)
    assert state == ConflictState.MODERATE
    
    # Just below LOW threshold
    state = conflict_resolver.detect_conflict_state(CONFLICT_LOW_THRESHOLD - 0.001)
    assert state == ConflictState.LOW
    
    # Exactly at HIGH threshold
    state = conflict_resolver.detect_conflict_state(CONFLICT_HIGH_THRESHOLD)
    assert state == ConflictState.HIGH
    
    # Just below HIGH threshold
    state = conflict_resolver.detect_conflict_state(CONFLICT_HIGH_THRESHOLD - 0.001)
    assert state == ConflictState.MODERATE


# ══════════════════════════════════════════════════════════════
# Test 13: Endpoint Returns Conflict State
# ══════════════════════════════════════════════════════════════

def test_endpoint_returns_conflict_state(hypothesis_engine):
    """Test that generated hypothesis has conflict_state (simulates API)."""
    hypothesis = hypothesis_engine.generate_hypothesis_simulated("BTC")
    
    assert hypothesis.conflict_state is not None
    assert hypothesis.conflict_state in ["LOW_CONFLICT", "MODERATE_CONFLICT", "HIGH_CONFLICT"]


# ══════════════════════════════════════════════════════════════
# Test 14: Recompute Endpoint Works
# ══════════════════════════════════════════════════════════════

def test_recompute_works(hypothesis_engine):
    """Test that recompute (multiple calls) works correctly."""
    h1 = hypothesis_engine.generate_hypothesis_simulated("ETH")
    h2 = hypothesis_engine.generate_hypothesis_simulated("ETH")
    
    # Both should have conflict_state
    assert h1.conflict_state is not None
    assert h2.conflict_state is not None


# ══════════════════════════════════════════════════════════════
# Test 15: History Stores Conflict State
# ══════════════════════════════════════════════════════════════

def test_history_stores_conflict_state(hypothesis_engine, low_conflict_layers):
    """Test that history stores conflict_state."""
    # Generate several hypotheses
    for _ in range(3):
        hypothesis_engine.generate_hypothesis("SOL", low_conflict_layers)
    
    history = hypothesis_engine._history.get("SOL", [])
    
    # All entries should have conflict_state
    for h in history:
        assert hasattr(h, "conflict_state")
        assert h.conflict_state in ["LOW_CONFLICT", "MODERATE_CONFLICT", "HIGH_CONFLICT"]


# ══════════════════════════════════════════════════════════════
# Test 16: Should Block Trade
# ══════════════════════════════════════════════════════════════

def test_should_block_trade(conflict_resolver):
    """Test should_block_trade helper."""
    assert conflict_resolver.should_block_trade(ConflictState.HIGH) is True
    assert conflict_resolver.should_block_trade(ConflictState.MODERATE) is False
    assert conflict_resolver.should_block_trade(ConflictState.LOW) is False


# ══════════════════════════════════════════════════════════════
# Test 17: Get Conflict Severity
# ══════════════════════════════════════════════════════════════

def test_get_conflict_severity(conflict_resolver):
    """Test conflict severity calculation."""
    # Below LOW threshold → 0
    severity = conflict_resolver.get_conflict_severity(0.05)
    assert severity == 0.0
    
    # At/above HIGH threshold → 1
    severity = conflict_resolver.get_conflict_severity(0.30)
    assert severity == 1.0
    
    # In between → linear interpolation
    severity = conflict_resolver.get_conflict_severity(0.175)  # Midpoint
    assert 0.4 < severity < 0.6  # Should be around 0.5


# ══════════════════════════════════════════════════════════════
# Test 18: Full Resolution Flow
# ══════════════════════════════════════════════════════════════

def test_full_resolution_flow(conflict_resolver):
    """Test complete resolution flow."""
    result = conflict_resolver.resolve(
        conflict_score=0.30,  # HIGH conflict
        confidence=0.70,
        reliability=0.60,
        execution_state="FAVORABLE",
        alpha_support=0.8,
        regime_support=0.3,
        microstructure_support=0.4,
        hypothesis_type="BULLISH_CONTINUATION",
    )
    
    assert result.conflict_state == ConflictState.HIGH
    assert result.adjusted_confidence == round(0.70 * HIGH_CONFIDENCE_MODIFIER, 4)
    assert result.adjusted_reliability == round(0.60 * HIGH_RELIABILITY_MODIFIER, 4)
    assert result.adjusted_execution_state == "UNFAVORABLE"
    assert len(result.reason_suffix) > 0


# ══════════════════════════════════════════════════════════════
# Test 19: No Change on Low Conflict
# ══════════════════════════════════════════════════════════════

def test_no_change_on_low_conflict(conflict_resolver):
    """Test that LOW conflict doesn't change values."""
    result = conflict_resolver.resolve(
        conflict_score=0.05,  # LOW conflict
        confidence=0.70,
        reliability=0.60,
        execution_state="FAVORABLE",
        alpha_support=0.7,
        regime_support=0.7,
        microstructure_support=0.7,
        hypothesis_type="BULLISH_CONTINUATION",
    )
    
    assert result.conflict_state == ConflictState.LOW
    assert result.adjusted_confidence == 0.70
    assert result.adjusted_reliability == 0.60
    assert result.adjusted_execution_state == "FAVORABLE"
    assert result.reason_suffix == ""


# ══════════════════════════════════════════════════════════════
# Test 20: Singleton Pattern
# ══════════════════════════════════════════════════════════════

def test_singleton_pattern():
    """Test that get_hypothesis_conflict_resolver returns singleton."""
    resolver1 = get_hypothesis_conflict_resolver()
    resolver2 = get_hypothesis_conflict_resolver()
    
    assert resolver1 is resolver2


# ══════════════════════════════════════════════════════════════
# Run tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
