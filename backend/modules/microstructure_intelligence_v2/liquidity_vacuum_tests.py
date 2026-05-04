"""
Liquidity Vacuum Detector — Tests

PHASE 28.2 — Liquidity Vacuum Detection Tests

Minimum 18 tests:
1.  orderbook gap detection
2.  gap normalization
3.  vacuum_size calculation
4.  vacuum_direction UP
5.  vacuum_direction DOWN
6.  vacuum_direction NONE
7.  nearest liquidity wall detection
8.  liquidity_state NORMAL
9.  liquidity_state THIN_ZONE
10. liquidity_state VACUUM
11. vacuum_probability calculation
12. confidence calculation
13. vacuum endpoint
14. history endpoint
15. summary endpoint
16. recompute endpoint
17. integration with MicrostructureSnapshot
18. extreme gap handling
"""

import pytest
import asyncio
from datetime import datetime

from .liquidity_vacuum_engine import (
    LiquidityVacuumEngine,
    get_liquidity_vacuum_engine,
)
from .liquidity_vacuum_registry import LiquidityVacuumRegistry
from .liquidity_vacuum_types import (
    OrderbookLevel,
    OrderbookLevels,
    OrderbookGap,
    MicrostructureContext,
    LiquidityVacuumState,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Get fresh engine instance."""
    return LiquidityVacuumEngine()


@pytest.fixture
def registry():
    """Get fresh registry instance with cache."""
    return LiquidityVacuumRegistry(db=None)


# ══════════════════════════════════════════════════════════════
# Test 1: Orderbook Gap Detection
# ══════════════════════════════════════════════════════════════

def test_orderbook_gap_detection(engine):
    """Test 1: orderbook gap detection."""
    # Create levels with one large gap
    levels = [
        OrderbookLevel(price=42000, size=100000),
        OrderbookLevel(price=41990, size=100000),  # 2.38 bps gap
        OrderbookLevel(price=41850, size=100000),  # 33.33 bps gap (large!)
        OrderbookLevel(price=41840, size=100000),  # 2.38 bps gap
    ]
    
    gaps = engine.detect_gaps(levels, mid_price=42000, side="BID")
    
    # Should detect the large gap (33+ bps > 3 bps threshold)
    assert len(gaps) >= 1
    large_gaps = [g for g in gaps if g.gap_bps >= 3.0]
    assert len(large_gaps) >= 1


# ══════════════════════════════════════════════════════════════
# Test 2: Gap Normalization
# ══════════════════════════════════════════════════════════════

def test_gap_normalization(engine):
    """Test 2: gap normalization."""
    # 5 bps gap normalized to 10 max = 0.5
    normalized = engine.normalize_gap(5.0, max_expected_gap=10.0)
    assert normalized == 0.5
    
    # 15 bps gap normalized to 10 max = 1.0 (capped)
    normalized = engine.normalize_gap(15.0, max_expected_gap=10.0)
    assert normalized == 1.0
    
    # Edge cases
    assert engine.normalize_gap(0.0, 10.0) == 0.0
    assert engine.normalize_gap(5.0, 0.0) == 0.0


# ══════════════════════════════════════════════════════════════
# Test 3: Vacuum Size Calculation
# ══════════════════════════════════════════════════════════════

def test_vacuum_size_calculation(engine):
    """Test 3: vacuum_size calculation."""
    bid_gaps = [
        OrderbookGap(price_start=42000, price_end=41950, gap_bps=4.5, side="BID", level_index=0),
        OrderbookGap(price_start=41950, price_end=41900, gap_bps=3.2, side="BID", level_index=1),
    ]
    ask_gaps = [
        OrderbookGap(price_start=42050, price_end=42100, gap_bps=7.8, side="ASK", level_index=0),
    ]
    
    vacuum_size = engine.calculate_vacuum_size(bid_gaps, ask_gaps)
    assert vacuum_size == 7.8  # Largest gap


# ══════════════════════════════════════════════════════════════
# Test 4: Vacuum Direction UP
# ══════════════════════════════════════════════════════════════

def test_vacuum_direction_up(engine):
    """Test 4: vacuum_direction UP."""
    bid_gaps = [
        OrderbookGap(price_start=42000, price_end=41950, gap_bps=3.5, side="BID", level_index=0),
    ]
    ask_gaps = [
        OrderbookGap(price_start=42050, price_end=42150, gap_bps=8.0, side="ASK", level_index=0),
    ]
    
    direction = engine.determine_vacuum_direction(bid_gaps, ask_gaps)
    assert direction == "UP"  # Larger gap on ask side


# ══════════════════════════════════════════════════════════════
# Test 5: Vacuum Direction DOWN
# ══════════════════════════════════════════════════════════════

def test_vacuum_direction_down(engine):
    """Test 5: vacuum_direction DOWN."""
    bid_gaps = [
        OrderbookGap(price_start=42000, price_end=41800, gap_bps=9.5, side="BID", level_index=0),
    ]
    ask_gaps = [
        OrderbookGap(price_start=42050, price_end=42100, gap_bps=3.2, side="ASK", level_index=0),
    ]
    
    direction = engine.determine_vacuum_direction(bid_gaps, ask_gaps)
    assert direction == "DOWN"  # Larger gap on bid side


# ══════════════════════════════════════════════════════════════
# Test 6: Vacuum Direction NONE
# ══════════════════════════════════════════════════════════════

def test_vacuum_direction_none(engine):
    """Test 6: vacuum_direction NONE."""
    # No gaps or gaps below threshold
    direction = engine.determine_vacuum_direction([], [])
    assert direction == "NONE"
    
    # Small gaps below threshold
    small_gaps = [
        OrderbookGap(price_start=42000, price_end=41995, gap_bps=1.5, side="BID", level_index=0),
    ]
    direction = engine.determine_vacuum_direction(small_gaps, [])
    assert direction == "NONE"


# ══════════════════════════════════════════════════════════════
# Test 7: Nearest Liquidity Wall Detection
# ══════════════════════════════════════════════════════════════

def test_nearest_liquidity_wall_detection(engine):
    """Test 7: nearest liquidity wall detection."""
    # Create levels with one large order (wall)
    levels = [
        OrderbookLevel(price=41990, size=50000),
        OrderbookLevel(price=41980, size=50000),
        OrderbookLevel(price=41970, size=200000),  # 4x median = wall
        OrderbookLevel(price=41960, size=50000),
    ]
    
    wall_price, wall_distance = engine.find_liquidity_wall(levels, mid_price=42000)
    
    assert wall_price == 41970  # Wall at 41970
    assert wall_distance > 0


# ══════════════════════════════════════════════════════════════
# Test 8: Liquidity State NORMAL
# ══════════════════════════════════════════════════════════════

def test_liquidity_state_normal(engine):
    """Test 8: liquidity_state NORMAL."""
    state = engine.classify_liquidity_state(max_gap_bps=1.5)
    assert state == "NORMAL"


# ══════════════════════════════════════════════════════════════
# Test 9: Liquidity State THIN_ZONE
# ══════════════════════════════════════════════════════════════

def test_liquidity_state_thin_zone(engine):
    """Test 9: liquidity_state THIN_ZONE."""
    state = engine.classify_liquidity_state(max_gap_bps=3.5)
    assert state == "THIN_ZONE"


# ══════════════════════════════════════════════════════════════
# Test 10: Liquidity State VACUUM
# ══════════════════════════════════════════════════════════════

def test_liquidity_state_vacuum(engine):
    """Test 10: liquidity_state VACUUM."""
    state = engine.classify_liquidity_state(max_gap_bps=8.0)
    assert state == "VACUUM"


# ══════════════════════════════════════════════════════════════
# Test 11: Vacuum Probability Calculation
# ══════════════════════════════════════════════════════════════

def test_vacuum_probability_calculation(engine):
    """Test 11: vacuum_probability calculation."""
    # Formula: 0.45*gap + 0.35*(1-depth) + 0.20*|imbalance|
    prob = engine.calculate_vacuum_probability(
        normalized_gap=0.7,
        depth_score=0.4,
        imbalance_score=0.3,
    )
    
    # 0.45*0.7 + 0.35*(1-0.4) + 0.20*0.3 = 0.315 + 0.21 + 0.06 = 0.585
    assert 0.5 <= prob <= 0.7
    assert 0.0 <= prob <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 12: Confidence Calculation
# ══════════════════════════════════════════════════════════════

def test_confidence_calculation(engine):
    """Test 12: confidence calculation."""
    # Formula: 0.4*gap + 0.3*(1-spread_norm) + 0.3*depth
    conf = engine.calculate_confidence(
        normalized_gap=0.6,
        spread_bps=4.0,  # 4/20 = 0.2 normalized
        depth_score=0.7,
    )
    
    # 0.4*0.6 + 0.3*(1-0.2) + 0.3*0.7 = 0.24 + 0.24 + 0.21 = 0.69
    assert 0.6 <= conf <= 0.8
    assert 0.0 <= conf <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 13: Full Vacuum State Build (vacuum endpoint)
# ══════════════════════════════════════════════════════════════

def test_full_vacuum_state_build(engine):
    """Test 13: vacuum endpoint / full vacuum state build."""
    # Create orderbook with gaps
    bids = [
        OrderbookLevel(price=41990, size=100000),
        OrderbookLevel(price=41980, size=100000),
        OrderbookLevel(price=41700, size=100000),  # Large gap
        OrderbookLevel(price=41690, size=100000),
    ]
    asks = [
        OrderbookLevel(price=42010, size=100000),
        OrderbookLevel(price=42020, size=100000),
        OrderbookLevel(price=42030, size=100000),
    ]
    
    orderbook = OrderbookLevels(
        bids=bids,
        asks=asks,
        mid_price=42000,
    )
    
    context = MicrostructureContext(
        depth_score=0.6,
        imbalance_score=0.2,
        spread_bps=3.0,
    )
    
    state = engine.build_vacuum_state("BTC", orderbook, context)
    
    assert state.symbol == "BTC"
    assert state.vacuum_direction in ["UP", "DOWN", "NONE"]
    assert 0 <= state.vacuum_probability <= 1
    assert state.vacuum_size_bps >= 0
    assert state.liquidity_state in ["NORMAL", "THIN_ZONE", "VACUUM"]
    assert 0 <= state.confidence <= 1
    assert len(state.reason) > 0


# ══════════════════════════════════════════════════════════════
# Test 14: Registry History
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_history(engine, registry):
    """Test 14: history endpoint - registry operations."""
    state = engine.build_vacuum_state_simulated("ETH")
    
    # Store
    record = await registry.store_vacuum_state(state)
    assert record.symbol == "ETH"
    
    # Get history
    history = await registry.get_history("ETH", limit=10)
    assert len(history) >= 1


# ══════════════════════════════════════════════════════════════
# Test 15: Registry Summary
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_summary(engine, registry):
    """Test 15: summary endpoint."""
    # Store multiple states
    for _ in range(3):
        state = engine.build_vacuum_state_simulated("SOL")
        await registry.store_vacuum_state(state)
    
    summary = await registry.get_summary("SOL")
    
    assert summary.symbol == "SOL"
    assert summary.total_records >= 3


# ══════════════════════════════════════════════════════════════
# Test 16: Recompute
# ══════════════════════════════════════════════════════════════

def test_recompute(engine):
    """Test 16: recompute endpoint."""
    # First compute
    state1 = engine.build_vacuum_state_simulated("BTC")
    
    # Recompute
    state2 = engine.build_vacuum_state_simulated("BTC")
    
    # Both should be valid states
    assert state1.symbol == "BTC"
    assert state2.symbol == "BTC"
    assert state1.liquidity_state in ["NORMAL", "THIN_ZONE", "VACUUM"]
    assert state2.liquidity_state in ["NORMAL", "THIN_ZONE", "VACUUM"]


# ══════════════════════════════════════════════════════════════
# Test 17: Integration with MicrostructureSnapshot
# ══════════════════════════════════════════════════════════════

def test_integration_with_microstructure_snapshot(engine):
    """Test 17: integration with MicrostructureSnapshot."""
    # Build vacuum state (simulated uses MicrostructureSnapshot context)
    state = engine.build_vacuum_state_simulated("BTC")
    
    # Should use context from microstructure snapshot
    assert state.vacuum_probability >= 0
    assert state.confidence >= 0


# ══════════════════════════════════════════════════════════════
# Test 18: Extreme Gap Handling
# ══════════════════════════════════════════════════════════════

def test_extreme_gap_handling(engine):
    """Test 18: extreme gap handling."""
    # Create orderbook with extreme gap
    bids = [
        OrderbookLevel(price=42000, size=100000),
        OrderbookLevel(price=40000, size=100000),  # 50 bps gap! (extreme)
    ]
    asks = [
        OrderbookLevel(price=42100, size=100000),
    ]
    
    orderbook = OrderbookLevels(
        bids=bids,
        asks=asks,
        mid_price=42050,
    )
    
    context = MicrostructureContext(
        depth_score=0.3,
        imbalance_score=-0.5,
        spread_bps=2.0,
    )
    
    state = engine.build_vacuum_state("BTC", orderbook, context)
    
    # Should handle extreme gaps gracefully
    assert state.liquidity_state == "VACUUM"
    assert state.vacuum_probability > 0.5  # High probability
    assert state.vacuum_direction in ["DOWN", "UP", "NONE"]


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

def test_orderbook_gap_score(engine):
    """Test orderbook gap score calculation."""
    gaps_bps = [1.0, 1.5, 2.0, 8.0, 1.2]  # One large gap
    
    score = engine.calculate_orderbook_gap_score(gaps_bps)
    
    # max(8.0) / median(1.5) = 5.33
    assert score > 3.0


def test_all_gaps_bps_calculation(engine):
    """Test calculation of all gaps in bps."""
    levels = [
        OrderbookLevel(price=42000, size=100000),
        OrderbookLevel(price=41990, size=100000),  # ~2.4 bps
        OrderbookLevel(price=41970, size=100000),  # ~4.8 bps
    ]
    
    gaps = engine.calculate_all_gaps_bps(levels, mid_price=42000)
    
    assert len(gaps) == 2
    assert all(g > 0 for g in gaps)


def test_reason_generation(engine):
    """Test reason string generation."""
    reason = engine.generate_reason(
        vacuum_direction="UP",
        liquidity_state="VACUUM",
        depth_score=0.3,
        imbalance_score=0.25,
    )
    
    assert "above price" in reason
    assert "large orderbook gap" in reason
    assert "weak depth" in reason


def test_simulated_vacuum_state(engine):
    """Test simulated vacuum state generation."""
    state = engine.build_vacuum_state_simulated("SOL")
    
    assert state.symbol == "SOL"
    assert state.vacuum_direction in ["UP", "DOWN", "NONE"]
    assert isinstance(state.liquidity_state, str)


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

def run_all_tests():
    """Run all tests and print results."""
    engine = LiquidityVacuumEngine()
    registry = LiquidityVacuumRegistry(db=None)
    
    results = []
    
    # Test 1
    try:
        test_orderbook_gap_detection(engine)
        results.append(("1. orderbook gap detection", "PASS"))
    except AssertionError as e:
        results.append(("1. orderbook gap detection", f"FAIL: {e}"))
    
    # Test 2
    try:
        test_gap_normalization(engine)
        results.append(("2. gap normalization", "PASS"))
    except AssertionError as e:
        results.append(("2. gap normalization", f"FAIL: {e}"))
    
    # Test 3
    try:
        test_vacuum_size_calculation(engine)
        results.append(("3. vacuum_size calculation", "PASS"))
    except AssertionError as e:
        results.append(("3. vacuum_size calculation", f"FAIL: {e}"))
    
    # Test 4
    try:
        test_vacuum_direction_up(engine)
        results.append(("4. vacuum_direction UP", "PASS"))
    except AssertionError as e:
        results.append(("4. vacuum_direction UP", f"FAIL: {e}"))
    
    # Test 5
    try:
        test_vacuum_direction_down(engine)
        results.append(("5. vacuum_direction DOWN", "PASS"))
    except AssertionError as e:
        results.append(("5. vacuum_direction DOWN", f"FAIL: {e}"))
    
    # Test 6
    try:
        test_vacuum_direction_none(engine)
        results.append(("6. vacuum_direction NONE", "PASS"))
    except AssertionError as e:
        results.append(("6. vacuum_direction NONE", f"FAIL: {e}"))
    
    # Test 7
    try:
        test_nearest_liquidity_wall_detection(engine)
        results.append(("7. nearest liquidity wall", "PASS"))
    except AssertionError as e:
        results.append(("7. nearest liquidity wall", f"FAIL: {e}"))
    
    # Test 8
    try:
        test_liquidity_state_normal(engine)
        results.append(("8. liquidity_state NORMAL", "PASS"))
    except AssertionError as e:
        results.append(("8. liquidity_state NORMAL", f"FAIL: {e}"))
    
    # Test 9
    try:
        test_liquidity_state_thin_zone(engine)
        results.append(("9. liquidity_state THIN_ZONE", "PASS"))
    except AssertionError as e:
        results.append(("9. liquidity_state THIN_ZONE", f"FAIL: {e}"))
    
    # Test 10
    try:
        test_liquidity_state_vacuum(engine)
        results.append(("10. liquidity_state VACUUM", "PASS"))
    except AssertionError as e:
        results.append(("10. liquidity_state VACUUM", f"FAIL: {e}"))
    
    # Test 11
    try:
        test_vacuum_probability_calculation(engine)
        results.append(("11. vacuum_probability calc", "PASS"))
    except AssertionError as e:
        results.append(("11. vacuum_probability calc", f"FAIL: {e}"))
    
    # Test 12
    try:
        test_confidence_calculation(engine)
        results.append(("12. confidence calculation", "PASS"))
    except AssertionError as e:
        results.append(("12. confidence calculation", f"FAIL: {e}"))
    
    # Test 13
    try:
        test_full_vacuum_state_build(engine)
        results.append(("13. vacuum endpoint", "PASS"))
    except AssertionError as e:
        results.append(("13. vacuum endpoint", f"FAIL: {e}"))
    
    # Test 14
    try:
        asyncio.get_event_loop().run_until_complete(
            test_registry_history(engine, registry)
        )
        results.append(("14. history endpoint", "PASS"))
    except Exception as e:
        results.append(("14. history endpoint", f"FAIL: {e}"))
    
    # Test 15
    try:
        asyncio.get_event_loop().run_until_complete(
            test_registry_summary(engine, registry)
        )
        results.append(("15. summary endpoint", "PASS"))
    except Exception as e:
        results.append(("15. summary endpoint", f"FAIL: {e}"))
    
    # Test 16
    try:
        test_recompute(engine)
        results.append(("16. recompute endpoint", "PASS"))
    except AssertionError as e:
        results.append(("16. recompute endpoint", f"FAIL: {e}"))
    
    # Test 17
    try:
        test_integration_with_microstructure_snapshot(engine)
        results.append(("17. MS snapshot integration", "PASS"))
    except AssertionError as e:
        results.append(("17. MS snapshot integration", f"FAIL: {e}"))
    
    # Test 18
    try:
        test_extreme_gap_handling(engine)
        results.append(("18. extreme gap handling", "PASS"))
    except AssertionError as e:
        results.append(("18. extreme gap handling", f"FAIL: {e}"))
    
    # Print results
    print("\n" + "=" * 60)
    print("PHASE 28.2 — Liquidity Vacuum Detector Tests")
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
