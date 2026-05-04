"""
PHASE 25.6 — A/B Test Tests

Test suite for system validation (A/B/C comparison).

Required tests (minimum 12):

1. direction consistency check
2. strategy consistency check
3. confidence drift calculation
4. capital drift calculation
5. validation PASSED case
6. validation WARNING case
7. validation FAILED direction
8. validation FAILED strategy
9. API schema validation
10. summary endpoint
11. health endpoint
12. integration with execution_context
"""

import pytest
from datetime import datetime

from modules.system_validation.ab_test_engine import (
    ABTestEngine,
    get_ab_test_engine,
)
from modules.system_validation.ab_test_types import (
    SystemComparison,
    SystemComparisonSummary,
    SystemValidationHealth,
    SystemOutput,
    CONFIDENCE_DRIFT_THRESHOLD,
    CAPITAL_DRIFT_THRESHOLD,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Create fresh engine instance."""
    return ABTestEngine()


@pytest.fixture
def consistent_systems():
    """Create consistent system outputs (should PASS)."""
    system_a = SystemOutput(
        system_type="A",
        direction="LONG",
        strategy="MOMENTUM",
        confidence=0.61,
        capital_modifier=1.0,
        context_state="NEUTRAL",
    )
    system_b = SystemOutput(
        system_type="B",
        direction="LONG",  # Same direction
        strategy="MOMENTUM",  # Same strategy
        confidence=0.66,
        capital_modifier=1.05,
        context_state="SUPPORTIVE",
    )
    system_c = SystemOutput(
        system_type="C",
        direction="LONG",  # Same direction
        strategy="MOMENTUM",  # Same strategy
        confidence=0.69,
        capital_modifier=1.08,
        context_state="SUPPORTIVE",
    )
    return system_a, system_b, system_c


@pytest.fixture
def direction_mismatch_systems():
    """Create systems with direction mismatch (should FAIL)."""
    system_a = SystemOutput(
        system_type="A",
        direction="LONG",
        strategy="MOMENTUM",
        confidence=0.61,
        capital_modifier=1.0,
        context_state="NEUTRAL",
    )
    system_b = SystemOutput(
        system_type="B",
        direction="LONG",
        strategy="MOMENTUM",
        confidence=0.66,
        capital_modifier=1.05,
        context_state="SUPPORTIVE",
    )
    system_c = SystemOutput(
        system_type="C",
        direction="SHORT",  # CHANGED! This is a failure
        strategy="MOMENTUM",
        confidence=0.69,
        capital_modifier=1.08,
        context_state="SUPPORTIVE",
    )
    return system_a, system_b, system_c


@pytest.fixture
def strategy_mismatch_systems():
    """Create systems with strategy mismatch (should FAIL)."""
    system_a = SystemOutput(
        system_type="A",
        direction="LONG",
        strategy="MOMENTUM",
        confidence=0.61,
        capital_modifier=1.0,
        context_state="NEUTRAL",
    )
    system_b = SystemOutput(
        system_type="B",
        direction="LONG",
        strategy="MOMENTUM",
        confidence=0.66,
        capital_modifier=1.05,
        context_state="SUPPORTIVE",
    )
    system_c = SystemOutput(
        system_type="C",
        direction="LONG",
        strategy="MEAN_REVERSION",  # CHANGED! This is a failure
        confidence=0.69,
        capital_modifier=1.08,
        context_state="SUPPORTIVE",
    )
    return system_a, system_b, system_c


@pytest.fixture
def high_drift_systems():
    """Create systems with high drift (should WARNING)."""
    system_a = SystemOutput(
        system_type="A",
        direction="LONG",
        strategy="MOMENTUM",
        confidence=0.50,  # Low confidence
        capital_modifier=1.0,
        context_state="NEUTRAL",
    )
    system_b = SystemOutput(
        system_type="B",
        direction="LONG",
        strategy="MOMENTUM",
        confidence=0.60,
        capital_modifier=1.10,
        context_state="SUPPORTIVE",
    )
    system_c = SystemOutput(
        system_type="C",
        direction="LONG",
        strategy="MOMENTUM",
        confidence=0.70,  # High drift: 0.70 - 0.50 = 0.20 > 0.15
        capital_modifier=1.30,  # High capital drift: 0.30 > 0.20
        context_state="SUPPORTIVE",
    )
    return system_a, system_b, system_c


# ══════════════════════════════════════════════════════════════
# Test 1: Direction Consistency Check
# ══════════════════════════════════════════════════════════════

def test_direction_consistency_check(engine, consistent_systems):
    """Test 1: Verify direction consistency check works."""
    system_a, system_b, system_c = consistent_systems
    
    comparison = engine.compare(system_a, system_b, system_c)
    
    assert comparison.direction_consistency is True
    assert comparison.system_a_direction == "LONG"
    assert comparison.system_b_direction == "LONG"
    assert comparison.system_c_direction == "LONG"


# ══════════════════════════════════════════════════════════════
# Test 2: Strategy Consistency Check
# ══════════════════════════════════════════════════════════════

def test_strategy_consistency_check(engine, consistent_systems):
    """Test 2: Verify strategy consistency check works."""
    system_a, system_b, system_c = consistent_systems
    
    comparison = engine.compare(system_a, system_b, system_c)
    
    assert comparison.strategy_consistency is True
    assert comparison.system_a_strategy == "MOMENTUM"
    assert comparison.system_b_strategy == "MOMENTUM"
    assert comparison.system_c_strategy == "MOMENTUM"


# ══════════════════════════════════════════════════════════════
# Test 3: Confidence Drift Calculation
# ══════════════════════════════════════════════════════════════

def test_confidence_drift_calculation(engine, consistent_systems):
    """Test 3: Verify confidence drift is calculated correctly."""
    system_a, system_b, system_c = consistent_systems
    
    comparison = engine.compare(system_a, system_b, system_c)
    
    expected_drift = abs(system_c.confidence - system_a.confidence)
    assert comparison.confidence_drift == pytest.approx(expected_drift, rel=0.01)
    
    # Drift should be |0.69 - 0.61| = 0.08
    assert comparison.confidence_drift == pytest.approx(0.08, rel=0.01)


# ══════════════════════════════════════════════════════════════
# Test 4: Capital Drift Calculation
# ══════════════════════════════════════════════════════════════

def test_capital_drift_calculation(engine, consistent_systems):
    """Test 4: Verify capital drift is calculated correctly."""
    system_a, system_b, system_c = consistent_systems
    
    comparison = engine.compare(system_a, system_b, system_c)
    
    expected_drift = abs(system_c.capital_modifier - system_a.capital_modifier)
    assert comparison.capital_drift == pytest.approx(expected_drift, rel=0.01)
    
    # Drift should be |1.08 - 1.0| = 0.08
    assert comparison.capital_drift == pytest.approx(0.08, rel=0.01)


# ══════════════════════════════════════════════════════════════
# Test 5: Validation PASSED Case
# ══════════════════════════════════════════════════════════════

def test_validation_passed(engine, consistent_systems):
    """Test 5: Verify PASSED validation state for consistent systems."""
    system_a, system_b, system_c = consistent_systems
    
    comparison = engine.compare(system_a, system_b, system_c)
    
    assert comparison.validation_state == "PASSED"
    assert comparison.direction_consistency is True
    assert comparison.strategy_consistency is True
    assert comparison.confidence_drift <= CONFIDENCE_DRIFT_THRESHOLD
    assert comparison.capital_drift <= CAPITAL_DRIFT_THRESHOLD


# ══════════════════════════════════════════════════════════════
# Test 6: Validation WARNING Case
# ══════════════════════════════════════════════════════════════

def test_validation_warning(engine, high_drift_systems):
    """Test 6: Verify WARNING validation state for high drift."""
    system_a, system_b, system_c = high_drift_systems
    
    comparison = engine.compare(system_a, system_b, system_c)
    
    assert comparison.validation_state == "WARNING"
    assert comparison.direction_consistency is True  # Still consistent
    assert comparison.strategy_consistency is True  # Still consistent
    # But drift exceeds threshold
    assert comparison.confidence_drift > CONFIDENCE_DRIFT_THRESHOLD or \
           comparison.capital_drift > CAPITAL_DRIFT_THRESHOLD


# ══════════════════════════════════════════════════════════════
# Test 7: Validation FAILED Direction
# ══════════════════════════════════════════════════════════════

def test_validation_failed_direction(engine, direction_mismatch_systems):
    """Test 7: Verify FAILED validation state for direction mismatch."""
    system_a, system_b, system_c = direction_mismatch_systems
    
    comparison = engine.compare(system_a, system_b, system_c)
    
    assert comparison.validation_state == "FAILED"
    assert comparison.direction_consistency is False
    assert "direction changed" in comparison.reason.lower()


# ══════════════════════════════════════════════════════════════
# Test 8: Validation FAILED Strategy
# ══════════════════════════════════════════════════════════════

def test_validation_failed_strategy(engine, strategy_mismatch_systems):
    """Test 8: Verify FAILED validation state for strategy mismatch."""
    system_a, system_b, system_c = strategy_mismatch_systems
    
    comparison = engine.compare(system_a, system_b, system_c)
    
    assert comparison.validation_state == "FAILED"
    assert comparison.strategy_consistency is False
    assert "strategy changed" in comparison.reason.lower()


# ══════════════════════════════════════════════════════════════
# Test 9: API Schema Validation
# ══════════════════════════════════════════════════════════════

def test_api_schema_validation(engine, consistent_systems):
    """Test 9: Verify SystemComparison has all required fields."""
    system_a, system_b, system_c = consistent_systems
    
    comparison = engine.compare(system_a, system_b, system_c)
    
    # Check all required fields exist
    assert hasattr(comparison, 'system_a_direction')
    assert hasattr(comparison, 'system_b_direction')
    assert hasattr(comparison, 'system_c_direction')
    assert hasattr(comparison, 'system_a_strategy')
    assert hasattr(comparison, 'system_b_strategy')
    assert hasattr(comparison, 'system_c_strategy')
    assert hasattr(comparison, 'system_a_confidence')
    assert hasattr(comparison, 'system_b_confidence')
    assert hasattr(comparison, 'system_c_confidence')
    assert hasattr(comparison, 'system_a_capital')
    assert hasattr(comparison, 'system_b_capital')
    assert hasattr(comparison, 'system_c_capital')
    assert hasattr(comparison, 'confidence_drift')
    assert hasattr(comparison, 'capital_drift')
    assert hasattr(comparison, 'direction_consistency')
    assert hasattr(comparison, 'strategy_consistency')
    assert hasattr(comparison, 'validation_state')
    assert hasattr(comparison, 'reason')


# ══════════════════════════════════════════════════════════════
# Test 10: Summary Endpoint
# ══════════════════════════════════════════════════════════════

def test_summary_endpoint(engine, consistent_systems):
    """Test 10: Verify summary endpoint returns correct format."""
    system_a, system_b, system_c = consistent_systems
    
    comparison = engine.compare(system_a, system_b, system_c)
    summary = engine.get_summary(comparison)
    
    assert isinstance(summary, SystemComparisonSummary)
    assert summary.validation_state == comparison.validation_state
    assert summary.confidence_drift == comparison.confidence_drift
    assert summary.capital_drift == comparison.capital_drift
    assert summary.direction_consistency == comparison.direction_consistency
    assert summary.strategy_consistency == comparison.strategy_consistency


# ══════════════════════════════════════════════════════════════
# Test 11: Health Endpoint
# ══════════════════════════════════════════════════════════════

def test_health_endpoint(engine, consistent_systems):
    """Test 11: Verify health endpoint returns correct format."""
    system_a, system_b, system_c = consistent_systems
    
    # First run comparison to update state
    comparison = engine.compare(system_a, system_b, system_c)
    
    health = engine.get_health()
    
    assert isinstance(health, SystemValidationHealth)
    assert health.status == "OK"
    assert health.system_a_available is True
    assert health.system_b_available is True
    assert health.system_c_available is True
    assert health.last_validation == comparison.validation_state


# ══════════════════════════════════════════════════════════════
# Test 12: Integration with Execution Context
# ══════════════════════════════════════════════════════════════

def test_integration_with_execution_context(engine):
    """Test 12: Verify integration maintains direction/strategy invariance."""
    # Simulate real system outputs
    system_a = SystemOutput(
        system_type="A",
        direction="SHORT",
        strategy="MEAN_REVERSION",
        confidence=0.55,
        capital_modifier=1.0,
        context_state="NEUTRAL",
    )
    
    # System B adds fractal (direction/strategy unchanged)
    system_b = SystemOutput(
        system_type="B",
        direction="SHORT",  # Must be same
        strategy="MEAN_REVERSION",  # Must be same
        confidence=0.58,
        capital_modifier=1.04,
        context_state="SUPPORTIVE",
    )
    
    # System C adds macro (direction/strategy unchanged)
    system_c = SystemOutput(
        system_type="C",
        direction="SHORT",  # Must be same
        strategy="MEAN_REVERSION",  # Must be same
        confidence=0.62,
        capital_modifier=1.09,
        context_state="SUPPORTIVE",
    )
    
    comparison = engine.compare(system_a, system_b, system_c)
    
    # Direction and strategy MUST NOT change
    assert comparison.direction_consistency is True
    assert comparison.strategy_consistency is True
    
    # Confidence and capital CAN increase
    assert system_c.confidence >= system_a.confidence
    assert system_c.capital_modifier >= system_a.capital_modifier
    
    # Validation should pass
    assert comparison.validation_state == "PASSED"


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

def test_singleton_engine():
    """Test singleton pattern for engine."""
    engine1 = get_ab_test_engine()
    engine2 = get_ab_test_engine()
    assert engine1 is engine2


def test_health_before_comparison():
    """Test health status before any comparison."""
    engine = ABTestEngine()
    health = engine.get_health()
    
    assert health.status == "ERROR"
    assert health.last_validation is None


def test_direction_b_differs_fails():
    """Test that direction mismatch in B also fails."""
    engine = ABTestEngine()
    
    system_a = SystemOutput(
        system_type="A",
        direction="LONG",
        strategy="MOMENTUM",
        confidence=0.61,
        capital_modifier=1.0,
        context_state="NEUTRAL",
    )
    system_b = SystemOutput(
        system_type="B",
        direction="SHORT",  # Different from A
        strategy="MOMENTUM",
        confidence=0.66,
        capital_modifier=1.05,
        context_state="SUPPORTIVE",
    )
    system_c = SystemOutput(
        system_type="C",
        direction="LONG",  # Same as A but different from B
        strategy="MOMENTUM",
        confidence=0.69,
        capital_modifier=1.08,
        context_state="SUPPORTIVE",
    )
    
    comparison = engine.compare(system_a, system_b, system_c)
    
    assert comparison.direction_consistency is False
    assert comparison.validation_state == "FAILED"


def test_confidence_drift_threshold_constant():
    """Test that threshold constants are correct."""
    assert CONFIDENCE_DRIFT_THRESHOLD == 0.15
    assert CAPITAL_DRIFT_THRESHOLD == 0.20
