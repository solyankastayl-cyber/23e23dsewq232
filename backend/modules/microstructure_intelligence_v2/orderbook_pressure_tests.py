"""
Orderbook Pressure Map — Tests

PHASE 28.3 — Orderbook Pressure Detection Tests

Minimum 18 tests:
1.  bid_pressure calculation
2.  ask_pressure calculation
3.  net_pressure calculation
4.  bid dominant classification
5.  ask dominant classification
6.  balanced classification
7.  bid absorption detection
8.  ask absorption detection
9.  no absorption detection
10. sweep risk UP
11. sweep risk DOWN
12. sweep risk NONE
13. sweep probability calculation
14. supportive state classification
15. fragile state classification
16. stressed state classification
17. pressure endpoint
18. history/summary endpoints
"""

import pytest
import asyncio
from datetime import datetime

from .orderbook_pressure_engine import (
    OrderbookPressureEngine,
    get_orderbook_pressure_engine,
)
from .orderbook_pressure_registry import OrderbookPressureRegistry
from .orderbook_pressure_types import (
    OrderbookPressureLevel,
    OrderbookPressureInput,
    MicrostructurePressureContext,
    OrderbookPressureMap,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Get fresh engine instance."""
    return OrderbookPressureEngine()


@pytest.fixture
def registry():
    """Get fresh registry instance with cache."""
    return OrderbookPressureRegistry(db=None)


# ══════════════════════════════════════════════════════════════
# Test 1: Bid Pressure Calculation
# ══════════════════════════════════════════════════════════════

def test_bid_pressure_calculation(engine):
    """Test 1: bid_pressure calculation."""
    levels = [
        OrderbookPressureLevel(price=41990, size=100000, distance_bps=2.0),
        OrderbookPressureLevel(price=41980, size=100000, distance_bps=5.0),
        OrderbookPressureLevel(price=41970, size=100000, distance_bps=7.0),
    ]
    
    pressure = engine.calculate_bid_pressure(levels)
    
    # Weighted sum: closer levels = higher weight
    assert 0.0 <= pressure <= 1.0
    assert pressure > 0.0  # Should have some pressure


# ══════════════════════════════════════════════════════════════
# Test 2: Ask Pressure Calculation
# ══════════════════════════════════════════════════════════════

def test_ask_pressure_calculation(engine):
    """Test 2: ask_pressure calculation."""
    levels = [
        OrderbookPressureLevel(price=42010, size=150000, distance_bps=1.5),
        OrderbookPressureLevel(price=42020, size=100000, distance_bps=4.0),
        OrderbookPressureLevel(price=42030, size=80000, distance_bps=6.0),
    ]
    
    pressure = engine.calculate_ask_pressure(levels)
    
    assert 0.0 <= pressure <= 1.0
    assert pressure > 0.0


# ══════════════════════════════════════════════════════════════
# Test 3: Net Pressure Calculation
# ══════════════════════════════════════════════════════════════

def test_net_pressure_calculation(engine):
    """Test 3: net_pressure calculation."""
    # Bid dominant: 0.7 > 0.5
    net = engine.calculate_net_pressure(0.7, 0.5)
    assert net > 0  # Positive = bid dominant
    
    # Ask dominant: 0.3 < 0.6
    net = engine.calculate_net_pressure(0.3, 0.6)
    assert net < 0  # Negative = ask dominant
    
    # Balanced: equal
    net = engine.calculate_net_pressure(0.5, 0.5)
    assert net == 0.0
    
    # Range check
    net = engine.calculate_net_pressure(1.0, 0.0)
    assert net == 1.0
    
    net = engine.calculate_net_pressure(0.0, 1.0)
    assert net == -1.0


# ══════════════════════════════════════════════════════════════
# Test 4: Bid Dominant Classification
# ══════════════════════════════════════════════════════════════

def test_bid_dominant_classification(engine):
    """Test 4: bid dominant classification."""
    bias = engine.classify_pressure_bias(0.25)  # > 0.15
    assert bias == "BID_DOMINANT"


# ══════════════════════════════════════════════════════════════
# Test 5: Ask Dominant Classification
# ══════════════════════════════════════════════════════════════

def test_ask_dominant_classification(engine):
    """Test 5: ask dominant classification."""
    bias = engine.classify_pressure_bias(-0.30)  # < -0.15
    assert bias == "ASK_DOMINANT"


# ══════════════════════════════════════════════════════════════
# Test 6: Balanced Classification
# ══════════════════════════════════════════════════════════════

def test_balanced_classification(engine):
    """Test 6: balanced classification."""
    bias = engine.classify_pressure_bias(0.05)  # Between -0.15 and 0.15
    assert bias == "BALANCED"
    
    bias = engine.classify_pressure_bias(-0.10)
    assert bias == "BALANCED"


# ══════════════════════════════════════════════════════════════
# Test 7: Bid Absorption Detection
# ══════════════════════════════════════════════════════════════

def test_bid_absorption_detection(engine):
    """Test 7: bid absorption detection."""
    # Bid levels with wall (large order) near mid
    bid_levels = [
        OrderbookPressureLevel(price=41995, size=50000, distance_bps=1.0),
        OrderbookPressureLevel(price=41990, size=200000, distance_bps=2.5),  # Wall: 4x typical
        OrderbookPressureLevel(price=41980, size=50000, distance_bps=5.0),
    ]
    ask_levels = [
        OrderbookPressureLevel(price=42005, size=50000, distance_bps=1.0),
        OrderbookPressureLevel(price=42010, size=50000, distance_bps=2.5),
    ]
    
    absorption = engine.detect_absorption_zone(bid_levels, ask_levels, "BID_DOMINANT")
    assert absorption == "BID_ABSORPTION"


# ══════════════════════════════════════════════════════════════
# Test 8: Ask Absorption Detection
# ══════════════════════════════════════════════════════════════

def test_ask_absorption_detection(engine):
    """Test 8: ask absorption detection."""
    bid_levels = [
        OrderbookPressureLevel(price=41995, size=50000, distance_bps=1.0),
        OrderbookPressureLevel(price=41990, size=50000, distance_bps=2.5),
    ]
    # Ask levels with wall near mid
    ask_levels = [
        OrderbookPressureLevel(price=42005, size=50000, distance_bps=1.0),
        OrderbookPressureLevel(price=42010, size=200000, distance_bps=2.5),  # Wall
        OrderbookPressureLevel(price=42020, size=50000, distance_bps=5.0),
    ]
    
    absorption = engine.detect_absorption_zone(bid_levels, ask_levels, "BALANCED")
    assert absorption == "ASK_ABSORPTION"


# ══════════════════════════════════════════════════════════════
# Test 9: No Absorption Detection
# ══════════════════════════════════════════════════════════════

def test_no_absorption_detection(engine):
    """Test 9: no absorption detection."""
    # No walls in either side
    bid_levels = [
        OrderbookPressureLevel(price=41995, size=50000, distance_bps=1.0),
        OrderbookPressureLevel(price=41990, size=55000, distance_bps=2.5),
        OrderbookPressureLevel(price=41980, size=45000, distance_bps=5.0),
    ]
    ask_levels = [
        OrderbookPressureLevel(price=42005, size=50000, distance_bps=1.0),
        OrderbookPressureLevel(price=42010, size=48000, distance_bps=2.5),
    ]
    
    absorption = engine.detect_absorption_zone(bid_levels, ask_levels, "BALANCED")
    assert absorption == "NONE"


# ══════════════════════════════════════════════════════════════
# Test 10: Sweep Risk UP
# ══════════════════════════════════════════════════════════════

def test_sweep_risk_up(engine):
    """Test 10: sweep risk UP."""
    # Bid dominant, thin asks
    bid_levels = [
        OrderbookPressureLevel(price=41990, size=200000, distance_bps=2.0),
        OrderbookPressureLevel(price=41980, size=200000, distance_bps=5.0),
    ]
    ask_levels = [
        OrderbookPressureLevel(price=42010, size=50000, distance_bps=2.0),  # Thin
    ]
    
    sweep = engine.assess_sweep_risk("BID_DOMINANT", bid_levels, ask_levels, "UP")
    assert sweep == "UP"


# ══════════════════════════════════════════════════════════════
# Test 11: Sweep Risk DOWN
# ══════════════════════════════════════════════════════════════

def test_sweep_risk_down(engine):
    """Test 11: sweep risk DOWN."""
    # Ask dominant, thin bids
    bid_levels = [
        OrderbookPressureLevel(price=41990, size=50000, distance_bps=2.0),  # Thin
    ]
    ask_levels = [
        OrderbookPressureLevel(price=42010, size=200000, distance_bps=2.0),
        OrderbookPressureLevel(price=42020, size=200000, distance_bps=5.0),
    ]
    
    sweep = engine.assess_sweep_risk("ASK_DOMINANT", bid_levels, ask_levels, "DOWN")
    assert sweep == "DOWN"


# ══════════════════════════════════════════════════════════════
# Test 12: Sweep Risk NONE
# ══════════════════════════════════════════════════════════════

def test_sweep_risk_none(engine):
    """Test 12: sweep risk NONE."""
    # Balanced with decent depth on both sides
    bid_levels = [
        OrderbookPressureLevel(price=41990, size=100000, distance_bps=2.0),
        OrderbookPressureLevel(price=41980, size=100000, distance_bps=5.0),
    ]
    ask_levels = [
        OrderbookPressureLevel(price=42010, size=100000, distance_bps=2.0),
        OrderbookPressureLevel(price=42020, size=100000, distance_bps=5.0),
    ]
    
    sweep = engine.assess_sweep_risk("BALANCED", bid_levels, ask_levels, "NONE")
    assert sweep == "NONE"


# ══════════════════════════════════════════════════════════════
# Test 13: Sweep Probability Calculation
# ══════════════════════════════════════════════════════════════

def test_sweep_probability_calculation(engine):
    """Test 13: sweep probability calculation."""
    # Formula: 0.40*|net| + 0.30*vacuum + 0.30*(1-depth)
    prob = engine.calculate_sweep_probability(
        net_pressure=0.3,
        vacuum_probability=0.5,
        depth_score=0.6,
    )
    
    # 0.40*0.3 + 0.30*0.5 + 0.30*(1-0.6) = 0.12 + 0.15 + 0.12 = 0.39
    assert 0.35 <= prob <= 0.45
    assert 0.0 <= prob <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 14: Supportive State Classification
# ══════════════════════════════════════════════════════════════

def test_supportive_state_classification(engine):
    """Test 14: supportive state classification."""
    state = engine.classify_pressure_state(
        pressure_bias="BID_DOMINANT",
        absorption_zone="BID_ABSORPTION",
        sweep_risk="UP",
        sweep_probability=0.3,  # Low
        depth_score=0.7,  # Good depth
    )
    assert state == "SUPPORTIVE"


# ══════════════════════════════════════════════════════════════
# Test 15: Fragile State Classification
# ══════════════════════════════════════════════════════════════

def test_fragile_state_classification(engine):
    """Test 15: fragile state classification."""
    state = engine.classify_pressure_state(
        pressure_bias="BID_DOMINANT",
        absorption_zone="NONE",
        sweep_risk="UP",
        sweep_probability=0.45,  # Moderate
        depth_score=0.35,  # Thin liquidity
    )
    assert state == "FRAGILE"


# ══════════════════════════════════════════════════════════════
# Test 16: Stressed State Classification
# ══════════════════════════════════════════════════════════════

def test_stressed_state_classification(engine):
    """Test 16: stressed state classification."""
    state = engine.classify_pressure_state(
        pressure_bias="ASK_DOMINANT",
        absorption_zone="NONE",
        sweep_risk="DOWN",
        sweep_probability=0.70,  # High
        depth_score=0.30,  # Thin liquidity
    )
    assert state == "STRESSED"


# ══════════════════════════════════════════════════════════════
# Test 17: Full Pressure Map Build (pressure endpoint)
# ══════════════════════════════════════════════════════════════

def test_full_pressure_map_build(engine):
    """Test 17: pressure endpoint / full pressure map build."""
    bids = [
        OrderbookPressureLevel(price=41990, size=150000, distance_bps=2.0),
        OrderbookPressureLevel(price=41980, size=100000, distance_bps=5.0),
        OrderbookPressureLevel(price=41970, size=80000, distance_bps=7.0),
    ]
    asks = [
        OrderbookPressureLevel(price=42010, size=100000, distance_bps=2.0),
        OrderbookPressureLevel(price=42020, size=120000, distance_bps=5.0),
    ]
    
    orderbook = OrderbookPressureInput(
        bids=bids,
        asks=asks,
        mid_price=42000,
    )
    
    context = MicrostructurePressureContext(
        depth_score=0.6,
        imbalance_score=0.15,
        spread_bps=3.0,
        vacuum_probability=0.4,
        vacuum_direction="UP",
        liquidity_state="NORMAL",
    )
    
    pressure_map = engine.build_pressure_map("BTC", orderbook, context)
    
    assert pressure_map.symbol == "BTC"
    assert 0 <= pressure_map.bid_pressure <= 1
    assert 0 <= pressure_map.ask_pressure <= 1
    assert -1 <= pressure_map.net_pressure <= 1
    assert pressure_map.pressure_bias in ["BID_DOMINANT", "ASK_DOMINANT", "BALANCED"]
    assert pressure_map.absorption_zone in ["BID_ABSORPTION", "ASK_ABSORPTION", "NONE"]
    assert pressure_map.sweep_risk in ["UP", "DOWN", "NONE"]
    assert 0 <= pressure_map.sweep_probability <= 1
    assert pressure_map.pressure_state in ["SUPPORTIVE", "NEUTRAL", "FRAGILE", "STRESSED"]
    assert 0 <= pressure_map.confidence <= 1
    assert len(pressure_map.reason) > 0


# ══════════════════════════════════════════════════════════════
# Test 18: Registry History/Summary
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_history_summary(engine, registry):
    """Test 18: history/summary endpoints."""
    # Store multiple pressure maps
    for _ in range(3):
        pressure_map = engine.build_pressure_map_simulated("ETH")
        await registry.store_pressure_map(pressure_map)
    
    # Get history
    history = await registry.get_history("ETH", limit=10)
    assert len(history) >= 3
    
    # Get summary
    summary = await registry.get_summary("ETH")
    assert summary.symbol == "ETH"
    assert summary.total_records >= 3


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

def test_confidence_calculation(engine):
    """Test confidence calculation."""
    conf = engine.calculate_confidence(
        net_pressure=0.3,
        depth_score=0.7,
        sweep_probability=0.5,
        absorption_zone="BID_ABSORPTION",
    )
    
    # 0.35*0.3 + 0.25*0.7 + 0.20*0.5 + 0.20*1.0 = 0.105 + 0.175 + 0.1 + 0.2 = 0.58
    assert 0.5 <= conf <= 0.7
    assert 0.0 <= conf <= 1.0


def test_reason_generation(engine):
    """Test reason string generation."""
    reason = engine.generate_reason(
        pressure_bias="BID_DOMINANT",
        absorption_zone="BID_ABSORPTION",
        sweep_risk="UP",
        pressure_state="SUPPORTIVE",
    )
    
    assert "bid side dominates" in reason
    assert "absorption" in reason
    assert "upside sweep" in reason


def test_simulated_pressure_map(engine):
    """Test simulated pressure map generation."""
    pressure_map = engine.build_pressure_map_simulated("SOL")
    
    assert pressure_map.symbol == "SOL"
    assert pressure_map.pressure_bias in ["BID_DOMINANT", "ASK_DOMINANT", "BALANCED"]
    assert isinstance(pressure_map.pressure_state, str)


def test_neutral_state_classification(engine):
    """Test neutral state classification."""
    state = engine.classify_pressure_state(
        pressure_bias="BALANCED",
        absorption_zone="NONE",
        sweep_risk="NONE",
        sweep_probability=0.2,  # Low
        depth_score=0.7,
    )
    assert state == "NEUTRAL"


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

def run_all_tests():
    """Run all tests and print results."""
    engine = OrderbookPressureEngine()
    registry = OrderbookPressureRegistry(db=None)
    
    results = []
    
    # Test 1
    try:
        test_bid_pressure_calculation(engine)
        results.append(("1. bid_pressure calculation", "PASS"))
    except AssertionError as e:
        results.append(("1. bid_pressure calculation", f"FAIL: {e}"))
    
    # Test 2
    try:
        test_ask_pressure_calculation(engine)
        results.append(("2. ask_pressure calculation", "PASS"))
    except AssertionError as e:
        results.append(("2. ask_pressure calculation", f"FAIL: {e}"))
    
    # Test 3
    try:
        test_net_pressure_calculation(engine)
        results.append(("3. net_pressure calculation", "PASS"))
    except AssertionError as e:
        results.append(("3. net_pressure calculation", f"FAIL: {e}"))
    
    # Test 4
    try:
        test_bid_dominant_classification(engine)
        results.append(("4. bid dominant classification", "PASS"))
    except AssertionError as e:
        results.append(("4. bid dominant classification", f"FAIL: {e}"))
    
    # Test 5
    try:
        test_ask_dominant_classification(engine)
        results.append(("5. ask dominant classification", "PASS"))
    except AssertionError as e:
        results.append(("5. ask dominant classification", f"FAIL: {e}"))
    
    # Test 6
    try:
        test_balanced_classification(engine)
        results.append(("6. balanced classification", "PASS"))
    except AssertionError as e:
        results.append(("6. balanced classification", f"FAIL: {e}"))
    
    # Test 7
    try:
        test_bid_absorption_detection(engine)
        results.append(("7. bid absorption detection", "PASS"))
    except AssertionError as e:
        results.append(("7. bid absorption detection", f"FAIL: {e}"))
    
    # Test 8
    try:
        test_ask_absorption_detection(engine)
        results.append(("8. ask absorption detection", "PASS"))
    except AssertionError as e:
        results.append(("8. ask absorption detection", f"FAIL: {e}"))
    
    # Test 9
    try:
        test_no_absorption_detection(engine)
        results.append(("9. no absorption detection", "PASS"))
    except AssertionError as e:
        results.append(("9. no absorption detection", f"FAIL: {e}"))
    
    # Test 10
    try:
        test_sweep_risk_up(engine)
        results.append(("10. sweep risk UP", "PASS"))
    except AssertionError as e:
        results.append(("10. sweep risk UP", f"FAIL: {e}"))
    
    # Test 11
    try:
        test_sweep_risk_down(engine)
        results.append(("11. sweep risk DOWN", "PASS"))
    except AssertionError as e:
        results.append(("11. sweep risk DOWN", f"FAIL: {e}"))
    
    # Test 12
    try:
        test_sweep_risk_none(engine)
        results.append(("12. sweep risk NONE", "PASS"))
    except AssertionError as e:
        results.append(("12. sweep risk NONE", f"FAIL: {e}"))
    
    # Test 13
    try:
        test_sweep_probability_calculation(engine)
        results.append(("13. sweep probability calc", "PASS"))
    except AssertionError as e:
        results.append(("13. sweep probability calc", f"FAIL: {e}"))
    
    # Test 14
    try:
        test_supportive_state_classification(engine)
        results.append(("14. supportive state", "PASS"))
    except AssertionError as e:
        results.append(("14. supportive state", f"FAIL: {e}"))
    
    # Test 15
    try:
        test_fragile_state_classification(engine)
        results.append(("15. fragile state", "PASS"))
    except AssertionError as e:
        results.append(("15. fragile state", f"FAIL: {e}"))
    
    # Test 16
    try:
        test_stressed_state_classification(engine)
        results.append(("16. stressed state", "PASS"))
    except AssertionError as e:
        results.append(("16. stressed state", f"FAIL: {e}"))
    
    # Test 17
    try:
        test_full_pressure_map_build(engine)
        results.append(("17. pressure endpoint", "PASS"))
    except AssertionError as e:
        results.append(("17. pressure endpoint", f"FAIL: {e}"))
    
    # Test 18
    try:
        asyncio.get_event_loop().run_until_complete(
            test_registry_history_summary(engine, registry)
        )
        results.append(("18. history/summary endpoints", "PASS"))
    except Exception as e:
        results.append(("18. history/summary endpoints", f"FAIL: {e}"))
    
    # Print results
    print("\n" + "=" * 60)
    print("PHASE 28.3 — Orderbook Pressure Map Tests")
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
