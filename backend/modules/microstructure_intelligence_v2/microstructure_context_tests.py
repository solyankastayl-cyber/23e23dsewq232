"""
Microstructure Context Integration — Tests

PHASE 28.5 — Unified Microstructure Context Tests

Minimum 18 tests:
1.  context builds from 4 components
2.  liquidity_state copied correctly
3.  pressure_bias copied correctly
4.  vacuum_direction copied correctly
5.  cascade_direction copied correctly
6.  supportive state classification
7.  neutral state classification
8.  fragile state classification
9.  stressed state classification
10. confidence modifier upper cap
11. confidence modifier lower cap
12. capital modifier upper cap
13. capital modifier lower cap
14. dominant driver detection
15. summary endpoint
16. drivers endpoint
17. recompute endpoint
18. integration with snapshot/vacuum/pressure/cascade
"""

import pytest

from .microstructure_context_engine import (
    MicrostructureContextEngine,
    get_microstructure_context_engine,
)
from .microstructure_context_types import (
    MicrostructureInputLayers,
    MicrostructureContext,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Get fresh engine instance."""
    return MicrostructureContextEngine()


# ══════════════════════════════════════════════════════════════
# Test 1: Context Builds from 4 Components
# ══════════════════════════════════════════════════════════════

def test_context_builds_from_components(engine):
    """Test 1: context builds from 4 components."""
    layers = MicrostructureInputLayers(
        snapshot_liquidity_state="NORMAL",
        vacuum_direction="UP",
        vacuum_probability=0.4,
        pressure_bias="BID_DOMINANT",
        sweep_probability=0.3,
        cascade_direction="UP",
        cascade_probability=0.35,
        cascade_state="BUILDING",
    )
    
    context = engine.build_context("BTC", layers)
    
    assert context.symbol == "BTC"
    assert context.liquidity_state is not None
    assert context.pressure_bias is not None
    assert context.vacuum_direction is not None
    assert context.cascade_direction is not None


# ══════════════════════════════════════════════════════════════
# Test 2: Liquidity State Copied Correctly
# ══════════════════════════════════════════════════════════════

def test_liquidity_state_copied(engine):
    """Test 2: liquidity_state copied correctly."""
    layers = MicrostructureInputLayers(snapshot_liquidity_state="DEEP")
    context = engine.build_context("BTC", layers)
    assert context.liquidity_state == "DEEP"
    
    layers = MicrostructureInputLayers(snapshot_liquidity_state="THIN")
    context = engine.build_context("BTC", layers)
    assert context.liquidity_state == "THIN"


# ══════════════════════════════════════════════════════════════
# Test 3: Pressure Bias Copied Correctly
# ══════════════════════════════════════════════════════════════

def test_pressure_bias_copied(engine):
    """Test 3: pressure_bias copied correctly."""
    layers = MicrostructureInputLayers(pressure_bias="ASK_DOMINANT")
    context = engine.build_context("BTC", layers)
    assert context.pressure_bias == "ASK_DOMINANT"


# ══════════════════════════════════════════════════════════════
# Test 4: Vacuum Direction Copied Correctly
# ══════════════════════════════════════════════════════════════

def test_vacuum_direction_copied(engine):
    """Test 4: vacuum_direction copied correctly."""
    layers = MicrostructureInputLayers(vacuum_direction="DOWN")
    context = engine.build_context("BTC", layers)
    assert context.vacuum_direction == "DOWN"


# ══════════════════════════════════════════════════════════════
# Test 5: Cascade Direction Copied Correctly
# ══════════════════════════════════════════════════════════════

def test_cascade_direction_copied(engine):
    """Test 5: cascade_direction copied correctly."""
    layers = MicrostructureInputLayers(cascade_direction="UP")
    context = engine.build_context("BTC", layers)
    assert context.cascade_direction == "UP"


# ══════════════════════════════════════════════════════════════
# Test 6: Supportive State Classification
# ══════════════════════════════════════════════════════════════

def test_supportive_state_classification(engine):
    """Test 6: supportive state classification."""
    state = engine.classify_microstructure_state(
        liquidity_state="DEEP",
        pressure_bias="BID_DOMINANT",
        vacuum_probability=0.2,
        cascade_probability=0.15,
        cascade_state="STABLE",
    )
    assert state == "SUPPORTIVE"


# ══════════════════════════════════════════════════════════════
# Test 7: Neutral State Classification
# ══════════════════════════════════════════════════════════════

def test_neutral_state_classification(engine):
    """Test 7: neutral state classification."""
    state = engine.classify_microstructure_state(
        liquidity_state="NORMAL",
        pressure_bias="BALANCED",
        vacuum_probability=0.2,
        cascade_probability=0.15,
        cascade_state="STABLE",
    )
    assert state == "NEUTRAL"


# ══════════════════════════════════════════════════════════════
# Test 8: Fragile State Classification
# ══════════════════════════════════════════════════════════════

def test_fragile_state_classification(engine):
    """Test 8: fragile state classification."""
    state = engine.classify_microstructure_state(
        liquidity_state="THIN",
        pressure_bias="BALANCED",
        vacuum_probability=0.35,
        cascade_probability=0.30,
        cascade_state="BUILDING",
    )
    assert state == "FRAGILE"


# ══════════════════════════════════════════════════════════════
# Test 9: Stressed State Classification
# ══════════════════════════════════════════════════════════════

def test_stressed_state_classification(engine):
    """Test 9: stressed state classification."""
    # High cascade probability
    state = engine.classify_microstructure_state(
        liquidity_state="THIN",
        pressure_bias="ASK_DOMINANT",
        vacuum_probability=0.6,
        cascade_probability=0.55,  # >= 0.45
        cascade_state="ACTIVE",
    )
    assert state == "STRESSED"
    
    # Critical cascade state
    state = engine.classify_microstructure_state(
        liquidity_state="NORMAL",
        pressure_bias="BALANCED",
        vacuum_probability=0.3,
        cascade_probability=0.35,
        cascade_state="CRITICAL",
    )
    assert state == "STRESSED"


# ══════════════════════════════════════════════════════════════
# Test 10: Confidence Modifier Upper Cap
# ══════════════════════════════════════════════════════════════

def test_confidence_modifier_upper_cap(engine):
    """Test 10: confidence modifier upper cap."""
    # Best case: DEEP liquidity, directional pressure, no vacuum/cascade
    modifier = engine.calculate_confidence_modifier(
        liquidity_state="DEEP",
        pressure_bias="BID_DOMINANT",
        vacuum_probability=0.0,
        cascade_probability=0.0,
    )
    assert modifier <= 1.12
    assert modifier >= 1.10  # Should be near cap


# ══════════════════════════════════════════════════════════════
# Test 11: Confidence Modifier Lower Cap
# ══════════════════════════════════════════════════════════════

def test_confidence_modifier_lower_cap(engine):
    """Test 11: confidence modifier lower cap."""
    # Worst case: THIN liquidity, high vacuum/cascade
    modifier = engine.calculate_confidence_modifier(
        liquidity_state="THIN",
        pressure_bias="BALANCED",
        vacuum_probability=1.0,
        cascade_probability=1.0,
    )
    assert modifier >= 0.82
    assert modifier <= 0.85  # Should be near floor


# ══════════════════════════════════════════════════════════════
# Test 12: Capital Modifier Upper Cap
# ══════════════════════════════════════════════════════════════

def test_capital_modifier_upper_cap(engine):
    """Test 12: capital modifier upper cap."""
    # Best case: DEEP liquidity, no vacuum/cascade
    modifier = engine.calculate_capital_modifier(
        liquidity_state="DEEP",
        vacuum_probability=0.0,
        cascade_probability=0.0,
    )
    assert modifier <= 1.10
    assert modifier >= 1.08  # Should be near cap


# ══════════════════════════════════════════════════════════════
# Test 13: Capital Modifier Lower Cap
# ══════════════════════════════════════════════════════════════

def test_capital_modifier_lower_cap(engine):
    """Test 13: capital modifier lower cap."""
    # Worst case: THIN liquidity, high vacuum/cascade
    modifier = engine.calculate_capital_modifier(
        liquidity_state="THIN",
        vacuum_probability=1.0,
        cascade_probability=1.0,
    )
    assert modifier >= 0.70
    assert modifier <= 0.75  # Should be near floor


# ══════════════════════════════════════════════════════════════
# Test 14: Dominant Driver Detection
# ══════════════════════════════════════════════════════════════

def test_dominant_driver_detection(engine):
    """Test 14: dominant driver detection."""
    # CASCADE dominant
    impacts = engine.calculate_driver_impacts(
        liquidity_state="NORMAL",
        pressure_bias="BALANCED",
        vacuum_probability=0.3,
        cascade_probability=0.7,
    )
    driver = engine.determine_dominant_driver(impacts)
    assert driver == "CASCADE"
    
    # VACUUM dominant
    impacts = engine.calculate_driver_impacts(
        liquidity_state="NORMAL",
        pressure_bias="BALANCED",
        vacuum_probability=0.8,
        cascade_probability=0.2,
    )
    driver = engine.determine_dominant_driver(impacts)
    assert driver == "VACUUM"


# ══════════════════════════════════════════════════════════════
# Test 15: Summary Endpoint
# ══════════════════════════════════════════════════════════════

def test_summary_endpoint(engine):
    """Test 15: summary endpoint."""
    # Build multiple contexts
    for _ in range(3):
        layers = MicrostructureInputLayers(
            snapshot_liquidity_state="NORMAL",
            vacuum_probability=0.3,
            cascade_probability=0.2,
        )
        engine.build_context("ETH", layers)
    
    summary = engine.get_summary("ETH")
    
    assert summary.symbol == "ETH"
    assert summary.supportive_count + summary.neutral_count + \
           summary.fragile_count + summary.stressed_count >= 3


# ══════════════════════════════════════════════════════════════
# Test 16: Drivers Endpoint
# ══════════════════════════════════════════════════════════════

def test_drivers_endpoint(engine):
    """Test 16: drivers endpoint."""
    layers = MicrostructureInputLayers(
        snapshot_liquidity_state="THIN",
        vacuum_probability=0.6,
        cascade_probability=0.4,
    )
    engine.build_context("SOL", layers)
    
    drivers = engine.get_drivers("SOL")
    
    assert drivers is not None
    assert drivers.symbol == "SOL"
    assert drivers.liquidity_impact >= 0
    assert drivers.vacuum_impact == 0.6
    assert drivers.cascade_impact == 0.4


# ══════════════════════════════════════════════════════════════
# Test 17: Recompute Endpoint
# ══════════════════════════════════════════════════════════════

def test_recompute_endpoint(engine):
    """Test 17: recompute endpoint."""
    # First compute
    layers1 = MicrostructureInputLayers(vacuum_probability=0.3)
    context1 = engine.build_context("BTC", layers1)
    
    # Recompute with different values
    layers2 = MicrostructureInputLayers(vacuum_probability=0.7)
    context2 = engine.build_context("BTC", layers2)
    
    assert context1.vacuum_probability == 0.3
    assert context2.vacuum_probability == 0.7


# ══════════════════════════════════════════════════════════════
# Test 18: Integration with All Layers
# ══════════════════════════════════════════════════════════════

def test_integration_with_all_layers(engine):
    """Test 18: integration with snapshot/vacuum/pressure/cascade."""
    # Build context from simulated layer data
    context = engine.build_context_simulated("BTC")
    
    assert context.symbol == "BTC"
    assert context.liquidity_state in ["DEEP", "NORMAL", "THIN"]
    assert context.pressure_bias in ["BID_DOMINANT", "ASK_DOMINANT", "BALANCED"]
    assert context.vacuum_direction in ["UP", "DOWN", "NONE"]
    assert context.cascade_direction in ["UP", "DOWN", "NONE"]
    assert 0.82 <= context.confidence_modifier <= 1.12
    assert 0.70 <= context.capital_modifier <= 1.10


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

def test_depth_component(engine):
    """Test depth component calculation."""
    assert engine.get_depth_component("DEEP") == 1.0
    assert engine.get_depth_component("NORMAL") == 0.0
    assert engine.get_depth_component("THIN") == -1.0


def test_pressure_component(engine):
    """Test pressure component calculation."""
    assert engine.get_pressure_component("BID_DOMINANT") == 0.5
    assert engine.get_pressure_component("ASK_DOMINANT") == 0.5
    assert engine.get_pressure_component("BALANCED") == 0.0


def test_direction_consistency(engine):
    """Test direction consistency check."""
    # All aligned UP
    is_consistent, score = engine.check_direction_consistency("UP", "UP", "BID_DOMINANT")
    assert is_consistent is True
    assert score == 1.0
    
    # Mixed directions
    is_consistent, score = engine.check_direction_consistency("UP", "DOWN", "BALANCED")
    assert is_consistent is False
    assert score == 0.5


def test_reason_generation(engine):
    """Test reason string generation."""
    reason = engine.generate_reason(
        microstructure_state="STRESSED",
        liquidity_state="THIN",
        pressure_bias="ASK_DOMINANT",
        vacuum_direction="DOWN",
        cascade_direction="DOWN",
        vacuum_probability=0.6,
        cascade_probability=0.55,
    )
    
    assert "cascade" in reason.lower() or "stress" in reason.lower()


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

def run_all_tests():
    """Run all tests and print results."""
    engine = MicrostructureContextEngine()
    
    results = []
    
    # Test 1
    try:
        test_context_builds_from_components(engine)
        results.append(("1. context from 4 components", "PASS"))
    except AssertionError as e:
        results.append(("1. context from 4 components", f"FAIL: {e}"))
    
    # Test 2
    try:
        test_liquidity_state_copied(engine)
        results.append(("2. liquidity_state copied", "PASS"))
    except AssertionError as e:
        results.append(("2. liquidity_state copied", f"FAIL: {e}"))
    
    # Test 3
    try:
        test_pressure_bias_copied(engine)
        results.append(("3. pressure_bias copied", "PASS"))
    except AssertionError as e:
        results.append(("3. pressure_bias copied", f"FAIL: {e}"))
    
    # Test 4
    try:
        test_vacuum_direction_copied(engine)
        results.append(("4. vacuum_direction copied", "PASS"))
    except AssertionError as e:
        results.append(("4. vacuum_direction copied", f"FAIL: {e}"))
    
    # Test 5
    try:
        test_cascade_direction_copied(engine)
        results.append(("5. cascade_direction copied", "PASS"))
    except AssertionError as e:
        results.append(("5. cascade_direction copied", f"FAIL: {e}"))
    
    # Test 6
    try:
        test_supportive_state_classification(engine)
        results.append(("6. supportive state", "PASS"))
    except AssertionError as e:
        results.append(("6. supportive state", f"FAIL: {e}"))
    
    # Test 7
    try:
        test_neutral_state_classification(engine)
        results.append(("7. neutral state", "PASS"))
    except AssertionError as e:
        results.append(("7. neutral state", f"FAIL: {e}"))
    
    # Test 8
    try:
        test_fragile_state_classification(engine)
        results.append(("8. fragile state", "PASS"))
    except AssertionError as e:
        results.append(("8. fragile state", f"FAIL: {e}"))
    
    # Test 9
    try:
        test_stressed_state_classification(engine)
        results.append(("9. stressed state", "PASS"))
    except AssertionError as e:
        results.append(("9. stressed state", f"FAIL: {e}"))
    
    # Test 10
    try:
        test_confidence_modifier_upper_cap(engine)
        results.append(("10. conf_mod upper cap", "PASS"))
    except AssertionError as e:
        results.append(("10. conf_mod upper cap", f"FAIL: {e}"))
    
    # Test 11
    try:
        test_confidence_modifier_lower_cap(engine)
        results.append(("11. conf_mod lower cap", "PASS"))
    except AssertionError as e:
        results.append(("11. conf_mod lower cap", f"FAIL: {e}"))
    
    # Test 12
    try:
        test_capital_modifier_upper_cap(engine)
        results.append(("12. cap_mod upper cap", "PASS"))
    except AssertionError as e:
        results.append(("12. cap_mod upper cap", f"FAIL: {e}"))
    
    # Test 13
    try:
        test_capital_modifier_lower_cap(engine)
        results.append(("13. cap_mod lower cap", "PASS"))
    except AssertionError as e:
        results.append(("13. cap_mod lower cap", f"FAIL: {e}"))
    
    # Test 14
    try:
        test_dominant_driver_detection(engine)
        results.append(("14. dominant driver", "PASS"))
    except AssertionError as e:
        results.append(("14. dominant driver", f"FAIL: {e}"))
    
    # Test 15
    try:
        test_summary_endpoint(engine)
        results.append(("15. summary endpoint", "PASS"))
    except AssertionError as e:
        results.append(("15. summary endpoint", f"FAIL: {e}"))
    
    # Test 16
    try:
        test_drivers_endpoint(engine)
        results.append(("16. drivers endpoint", "PASS"))
    except AssertionError as e:
        results.append(("16. drivers endpoint", f"FAIL: {e}"))
    
    # Test 17
    try:
        test_recompute_endpoint(engine)
        results.append(("17. recompute endpoint", "PASS"))
    except AssertionError as e:
        results.append(("17. recompute endpoint", f"FAIL: {e}"))
    
    # Test 18
    try:
        test_integration_with_all_layers(engine)
        results.append(("18. integration with layers", "PASS"))
    except AssertionError as e:
        results.append(("18. integration with layers", f"FAIL: {e}"))
    
    # Print results
    print("\n" + "=" * 60)
    print("PHASE 28.5 — Microstructure Context Integration Tests")
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
