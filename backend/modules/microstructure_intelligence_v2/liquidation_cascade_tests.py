"""
Liquidation Cascade Probability — Tests

PHASE 28.4 — Liquidation Cascade Detection Tests

Minimum 18 tests:
1.  up cascade direction detection
2.  down cascade direction detection
3.  none direction detection
4.  cascade_probability calculation
5.  alignment multiplier 3/3
6.  alignment multiplier 2/3
7.  alignment multiplier conflict
8.  severity LOW
9.  severity MEDIUM
10. severity HIGH
11. severity EXTREME
12. state STABLE
13. state BUILDING
14. state ACTIVE
15. state CRITICAL
16. cascade endpoint
17. summary/history endpoints
18. integration with snapshot + vacuum + pressure
"""

import pytest
import asyncio
from datetime import datetime

from .liquidation_cascade_engine import (
    LiquidationCascadeEngine,
    get_liquidation_cascade_engine,
)
from .liquidation_cascade_registry import LiquidationCascadeRegistry
from .liquidation_cascade_types import (
    CascadeInputContext,
    LiquidationCascadeState,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Get fresh engine instance."""
    return LiquidationCascadeEngine()


@pytest.fixture
def registry():
    """Get fresh registry instance with cache."""
    return LiquidationCascadeRegistry(db=None)


# ══════════════════════════════════════════════════════════════
# Test 1: UP Cascade Direction Detection
# ══════════════════════════════════════════════════════════════

def test_up_cascade_direction(engine):
    """Test 1: up cascade direction detection."""
    direction = engine.detect_cascade_direction(
        liquidation_pressure=0.5,  # Bullish (shorts squeezed)
        vacuum_direction="UP",
        sweep_risk="UP",
        pressure_bias="BID_DOMINANT",
    )
    assert direction == "UP"


# ══════════════════════════════════════════════════════════════
# Test 2: DOWN Cascade Direction Detection
# ══════════════════════════════════════════════════════════════

def test_down_cascade_direction(engine):
    """Test 2: down cascade direction detection."""
    direction = engine.detect_cascade_direction(
        liquidation_pressure=-0.5,  # Bearish (longs flushed)
        vacuum_direction="DOWN",
        sweep_risk="DOWN",
        pressure_bias="ASK_DOMINANT",
    )
    assert direction == "DOWN"


# ══════════════════════════════════════════════════════════════
# Test 3: NONE Direction Detection
# ══════════════════════════════════════════════════════════════

def test_none_direction(engine):
    """Test 3: none direction detection."""
    direction = engine.detect_cascade_direction(
        liquidation_pressure=0.05,  # Neutral
        vacuum_direction="NONE",
        sweep_risk="NONE",
        pressure_bias="BALANCED",
    )
    assert direction == "NONE"
    
    # Mixed signals
    direction = engine.detect_cascade_direction(
        liquidation_pressure=0.3,  # Bullish
        vacuum_direction="DOWN",  # Bearish
        sweep_risk="UP",  # Bullish
        pressure_bias="ASK_DOMINANT",  # Bearish
    )
    assert direction == "NONE"  # 2 up, 2 down = conflict


# ══════════════════════════════════════════════════════════════
# Test 4: Cascade Probability Calculation
# ══════════════════════════════════════════════════════════════

def test_cascade_probability_calculation(engine):
    """Test 4: cascade_probability calculation."""
    # Base formula: 0.40*|liq| + 0.30*vacuum + 0.20*sweep + 0.10*(1-depth)
    prob = engine.calculate_cascade_probability(
        liquidation_pressure=0.6,
        vacuum_probability=0.5,
        sweep_probability=0.4,
        depth_score=0.7,
        alignment_multiplier=1.0,
    )
    
    # 0.40*0.6 + 0.30*0.5 + 0.20*0.4 + 0.10*(1-0.7) = 0.24 + 0.15 + 0.08 + 0.03 = 0.50
    assert 0.45 <= prob <= 0.55
    assert 0.0 <= prob <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 5: Alignment Multiplier 3/3
# ══════════════════════════════════════════════════════════════

def test_alignment_multiplier_full(engine):
    """Test 5: alignment multiplier 3/3."""
    alignment_score, multiplier = engine.calculate_alignment_score(
        liquidation_pressure=0.5,  # UP
        vacuum_direction="UP",
        sweep_risk="UP",
        pressure_bias="BID_DOMINANT",  # UP
    )
    
    assert alignment_score == 1.0
    assert multiplier == 1.15  # Full alignment


# ══════════════════════════════════════════════════════════════
# Test 6: Alignment Multiplier 2/3
# ══════════════════════════════════════════════════════════════

def test_alignment_multiplier_partial(engine):
    """Test 6: alignment multiplier 2/3."""
    alignment_score, multiplier = engine.calculate_alignment_score(
        liquidation_pressure=0.5,  # UP
        vacuum_direction="UP",
        sweep_risk="NONE",  # Neutral
        pressure_bias="BALANCED",  # Neutral
    )
    
    assert alignment_score == 0.66
    assert multiplier == 1.0  # Partial alignment


# ══════════════════════════════════════════════════════════════
# Test 7: Alignment Multiplier Conflict
# ══════════════════════════════════════════════════════════════

def test_alignment_multiplier_conflict(engine):
    """Test 7: alignment multiplier conflict."""
    alignment_score, multiplier = engine.calculate_alignment_score(
        liquidation_pressure=0.5,  # UP
        vacuum_direction="DOWN",  # DOWN
        sweep_risk="NONE",  # Neutral
        pressure_bias="BALANCED",  # Neutral
    )
    
    assert alignment_score <= 0.5
    assert multiplier == 0.75  # Conflict


# ══════════════════════════════════════════════════════════════
# Test 8: Severity LOW
# ══════════════════════════════════════════════════════════════

def test_severity_low(engine):
    """Test 8: severity LOW."""
    severity = engine.classify_severity(0.15)  # < 0.25
    assert severity == "LOW"


# ══════════════════════════════════════════════════════════════
# Test 9: Severity MEDIUM
# ══════════════════════════════════════════════════════════════

def test_severity_medium(engine):
    """Test 9: severity MEDIUM."""
    severity = engine.classify_severity(0.35)  # 0.25 <= p < 0.45
    assert severity == "MEDIUM"


# ══════════════════════════════════════════════════════════════
# Test 10: Severity HIGH
# ══════════════════════════════════════════════════════════════

def test_severity_high(engine):
    """Test 10: severity HIGH."""
    severity = engine.classify_severity(0.55)  # 0.45 <= p < 0.70
    assert severity == "HIGH"


# ══════════════════════════════════════════════════════════════
# Test 11: Severity EXTREME
# ══════════════════════════════════════════════════════════════

def test_severity_extreme(engine):
    """Test 11: severity EXTREME."""
    severity = engine.classify_severity(0.75)  # p >= 0.70
    assert severity == "EXTREME"


# ══════════════════════════════════════════════════════════════
# Test 12: State STABLE
# ══════════════════════════════════════════════════════════════

def test_state_stable(engine):
    """Test 12: state STABLE."""
    state = engine.classify_cascade_state(
        cascade_direction="NONE",
        cascade_severity="LOW",
        depth_score=0.7,
        alignment_score=0.3,
    )
    assert state == "STABLE"


# ══════════════════════════════════════════════════════════════
# Test 13: State BUILDING
# ══════════════════════════════════════════════════════════════

def test_state_building(engine):
    """Test 13: state BUILDING."""
    state = engine.classify_cascade_state(
        cascade_direction="UP",
        cascade_severity="MEDIUM",
        depth_score=0.6,
        alignment_score=0.66,
    )
    assert state == "BUILDING"


# ══════════════════════════════════════════════════════════════
# Test 14: State ACTIVE
# ══════════════════════════════════════════════════════════════

def test_state_active(engine):
    """Test 14: state ACTIVE."""
    state = engine.classify_cascade_state(
        cascade_direction="DOWN",
        cascade_severity="HIGH",
        depth_score=0.5,
        alignment_score=0.66,
    )
    assert state == "ACTIVE"


# ══════════════════════════════════════════════════════════════
# Test 15: State CRITICAL
# ══════════════════════════════════════════════════════════════

def test_state_critical(engine):
    """Test 15: state CRITICAL."""
    state = engine.classify_cascade_state(
        cascade_direction="DOWN",
        cascade_severity="EXTREME",
        depth_score=0.3,  # Thin liquidity
        alignment_score=0.8,  # Strong alignment
    )
    assert state == "CRITICAL"


# ══════════════════════════════════════════════════════════════
# Test 16: Full Cascade State Build (cascade endpoint)
# ══════════════════════════════════════════════════════════════

def test_full_cascade_state_build(engine):
    """Test 16: cascade endpoint / full cascade state build."""
    context = CascadeInputContext(
        liquidation_pressure=0.5,
        funding_pressure=0.2,
        oi_pressure=0.3,
        depth_score=0.4,
        vacuum_direction="UP",
        vacuum_probability=0.6,
        liquidity_state="THIN_ZONE",
        pressure_bias="BID_DOMINANT",
        sweep_risk="UP",
        sweep_probability=0.5,
        pressure_state="SUPPORTIVE",
    )
    
    state = engine.build_cascade_state("BTC", context)
    
    assert state.symbol == "BTC"
    assert state.cascade_direction in ["UP", "DOWN", "NONE"]
    assert 0 <= state.cascade_probability <= 1
    assert state.cascade_severity in ["LOW", "MEDIUM", "HIGH", "EXTREME"]
    assert state.cascade_state in ["STABLE", "BUILDING", "ACTIVE", "CRITICAL"]
    assert 0 <= state.confidence <= 1
    assert len(state.reason) > 0


# ══════════════════════════════════════════════════════════════
# Test 17: Registry History/Summary
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_history_summary(engine, registry):
    """Test 17: summary/history endpoints."""
    context = CascadeInputContext(
        liquidation_pressure=0.4,
        vacuum_probability=0.5,
        sweep_probability=0.3,
        depth_score=0.6,
    )
    
    # Store multiple states
    for _ in range(3):
        state = engine.build_cascade_state("ETH", context)
        await registry.store_cascade_state(state)
    
    # Get history
    history = await registry.get_history("ETH", limit=10)
    assert len(history) >= 3
    
    # Get summary
    summary = await registry.get_summary("ETH")
    assert summary.symbol == "ETH"
    assert summary.total_records >= 3


# ══════════════════════════════════════════════════════════════
# Test 18: Integration with Snapshot + Vacuum + Pressure
# ══════════════════════════════════════════════════════════════

def test_integration_with_layers(engine):
    """Test 18: integration with snapshot + vacuum + pressure."""
    # Build cascade state using simulated data from all layers
    state = engine.build_cascade_state_simulated("SOL")
    
    # Should have integrated all inputs
    assert state.symbol == "SOL"
    assert state.liquidation_pressure is not None
    assert state.vacuum_probability is not None
    assert state.sweep_probability is not None
    assert state.cascade_direction in ["UP", "DOWN", "NONE"]


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

def test_confidence_calculation(engine):
    """Test confidence calculation."""
    conf = engine.calculate_confidence(
        liquidation_pressure=0.5,
        vacuum_probability=0.6,
        sweep_probability=0.4,
        alignment_score=0.8,
    )
    
    # 0.35*0.5 + 0.25*0.6 + 0.20*0.4 + 0.20*0.8 = 0.175 + 0.15 + 0.08 + 0.16 = 0.565
    assert 0.5 <= conf <= 0.65
    assert 0.0 <= conf <= 1.0


def test_reason_generation(engine):
    """Test reason string generation."""
    reason = engine.generate_reason(
        cascade_direction="UP",
        liquidation_pressure=0.5,
        vacuum_direction="UP",
        pressure_bias="BID_DOMINANT",
        alignment_score=0.8,
    )
    
    assert "upward" in reason.lower() or "up" in reason.lower()
    assert "cascade" in reason.lower()


def test_simulated_cascade_state(engine):
    """Test simulated cascade state generation."""
    state = engine.build_cascade_state_simulated("BTC")
    
    assert state.symbol == "BTC"
    assert state.cascade_direction in ["UP", "DOWN", "NONE"]
    assert isinstance(state.cascade_state, str)


def test_neutral_state_classification(engine):
    """Test neutral state classification."""
    state = engine.classify_cascade_state(
        cascade_direction="NONE",
        cascade_severity="LOW",
        depth_score=0.8,
        alignment_score=0.2,
    )
    assert state == "STABLE"


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

def run_all_tests():
    """Run all tests and print results."""
    engine = LiquidationCascadeEngine()
    registry = LiquidationCascadeRegistry(db=None)
    
    results = []
    
    # Test 1
    try:
        test_up_cascade_direction(engine)
        results.append(("1. up cascade direction", "PASS"))
    except AssertionError as e:
        results.append(("1. up cascade direction", f"FAIL: {e}"))
    
    # Test 2
    try:
        test_down_cascade_direction(engine)
        results.append(("2. down cascade direction", "PASS"))
    except AssertionError as e:
        results.append(("2. down cascade direction", f"FAIL: {e}"))
    
    # Test 3
    try:
        test_none_direction(engine)
        results.append(("3. none direction", "PASS"))
    except AssertionError as e:
        results.append(("3. none direction", f"FAIL: {e}"))
    
    # Test 4
    try:
        test_cascade_probability_calculation(engine)
        results.append(("4. cascade_probability calc", "PASS"))
    except AssertionError as e:
        results.append(("4. cascade_probability calc", f"FAIL: {e}"))
    
    # Test 5
    try:
        test_alignment_multiplier_full(engine)
        results.append(("5. alignment 3/3", "PASS"))
    except AssertionError as e:
        results.append(("5. alignment 3/3", f"FAIL: {e}"))
    
    # Test 6
    try:
        test_alignment_multiplier_partial(engine)
        results.append(("6. alignment 2/3", "PASS"))
    except AssertionError as e:
        results.append(("6. alignment 2/3", f"FAIL: {e}"))
    
    # Test 7
    try:
        test_alignment_multiplier_conflict(engine)
        results.append(("7. alignment conflict", "PASS"))
    except AssertionError as e:
        results.append(("7. alignment conflict", f"FAIL: {e}"))
    
    # Test 8
    try:
        test_severity_low(engine)
        results.append(("8. severity LOW", "PASS"))
    except AssertionError as e:
        results.append(("8. severity LOW", f"FAIL: {e}"))
    
    # Test 9
    try:
        test_severity_medium(engine)
        results.append(("9. severity MEDIUM", "PASS"))
    except AssertionError as e:
        results.append(("9. severity MEDIUM", f"FAIL: {e}"))
    
    # Test 10
    try:
        test_severity_high(engine)
        results.append(("10. severity HIGH", "PASS"))
    except AssertionError as e:
        results.append(("10. severity HIGH", f"FAIL: {e}"))
    
    # Test 11
    try:
        test_severity_extreme(engine)
        results.append(("11. severity EXTREME", "PASS"))
    except AssertionError as e:
        results.append(("11. severity EXTREME", f"FAIL: {e}"))
    
    # Test 12
    try:
        test_state_stable(engine)
        results.append(("12. state STABLE", "PASS"))
    except AssertionError as e:
        results.append(("12. state STABLE", f"FAIL: {e}"))
    
    # Test 13
    try:
        test_state_building(engine)
        results.append(("13. state BUILDING", "PASS"))
    except AssertionError as e:
        results.append(("13. state BUILDING", f"FAIL: {e}"))
    
    # Test 14
    try:
        test_state_active(engine)
        results.append(("14. state ACTIVE", "PASS"))
    except AssertionError as e:
        results.append(("14. state ACTIVE", f"FAIL: {e}"))
    
    # Test 15
    try:
        test_state_critical(engine)
        results.append(("15. state CRITICAL", "PASS"))
    except AssertionError as e:
        results.append(("15. state CRITICAL", f"FAIL: {e}"))
    
    # Test 16
    try:
        test_full_cascade_state_build(engine)
        results.append(("16. cascade endpoint", "PASS"))
    except AssertionError as e:
        results.append(("16. cascade endpoint", f"FAIL: {e}"))
    
    # Test 17
    try:
        asyncio.get_event_loop().run_until_complete(
            test_registry_history_summary(engine, registry)
        )
        results.append(("17. history/summary endpoints", "PASS"))
    except Exception as e:
        results.append(("17. history/summary endpoints", f"FAIL: {e}"))
    
    # Test 18
    try:
        test_integration_with_layers(engine)
        results.append(("18. integration with layers", "PASS"))
    except AssertionError as e:
        results.append(("18. integration with layers", f"FAIL: {e}"))
    
    # Print results
    print("\n" + "=" * 60)
    print("PHASE 28.4 — Liquidation Cascade Probability Tests")
    print("=" * 60)
    
    passed = sum(1 for _, status in results if status == "PASS")
    failed = len(results) - passed
    
    for name, status in results:
        icon = "✅" if status == "PASS" else "❌"
        print(f"{icon} {name}: {status}")
    
    print("-" * 60)
    print(f"Total: {passed}/{len(results)} passed")
    
    if failed > 0:
        print(f"⚠️  {failed} tests failed")
    else:
        print("✅ All tests passed!")
    
    return passed == len(results)


if __name__ == "__main__":
    run_all_tests()
