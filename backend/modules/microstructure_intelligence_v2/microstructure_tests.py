"""
Microstructure Intelligence v2 — Tests

PHASE 28.1 — Microstructure Snapshot Engine Tests

Minimum 16 tests:
1.  spread_bps calculation
2.  depth_score calculation
3.  imbalance_score calculation
4.  liquidity_state DEEP
5.  liquidity_state NORMAL
6.  liquidity_state THIN
7.  pressure_state BUY_PRESSURE
8.  pressure_state SELL_PRESSURE
9.  pressure_state BALANCED
10. supportive microstructure classification
11. neutral microstructure classification
12. fragile microstructure classification
13. stressed microstructure classification
14. confidence calculation
15. current endpoint
16. summary/history endpoints
"""

import pytest
import asyncio
from datetime import datetime

from .microstructure_snapshot_engine import (
    MicrostructureSnapshotEngine,
    get_microstructure_snapshot_engine,
)
from .microstructure_registry import MicrostructureRegistry
from .microstructure_types import (
    OrderbookData,
    ExchangeData,
    MicrostructureSnapshot,
    MicrostructureHistoryRecord,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Get fresh engine instance."""
    return MicrostructureSnapshotEngine()


@pytest.fixture
def registry():
    """Get fresh registry instance with cache."""
    return MicrostructureRegistry(db=None)


# ══════════════════════════════════════════════════════════════
# Test 1: Spread BPS Calculation
# ══════════════════════════════════════════════════════════════

def test_spread_bps_calculation(engine):
    """Test 1: spread_bps calculation."""
    # Setup: bid=42000, ask=42010 -> mid=42005 -> spread=10 -> bps = (10/42005)*10000 = 2.38
    spread_bps = engine.calculate_spread_bps(
        best_bid=42000.0,
        best_ask=42010.0,
    )
    
    assert spread_bps > 0
    assert 2.0 < spread_bps < 3.0  # ~2.38 bps
    
    # Edge case: zero values
    assert engine.calculate_spread_bps(0, 0) == 0.0
    assert engine.calculate_spread_bps(-100, 100) == 0.0


# ══════════════════════════════════════════════════════════════
# Test 2: Depth Score Calculation
# ══════════════════════════════════════════════════════════════

def test_depth_score_calculation(engine):
    """Test 2: depth_score calculation."""
    # 800000 / 1000000 = 0.8
    depth = engine.calculate_depth_score(
        total_depth=800000.0,
        depth_reference=1000000.0,
    )
    assert depth == 0.8
    
    # Cap at 1.0
    depth = engine.calculate_depth_score(
        total_depth=1500000.0,
        depth_reference=1000000.0,
    )
    assert depth == 1.0
    
    # Edge case: zero reference
    assert engine.calculate_depth_score(100000, 0) == 0.5


# ══════════════════════════════════════════════════════════════
# Test 3: Imbalance Score Calculation
# ══════════════════════════════════════════════════════════════

def test_imbalance_score_calculation(engine):
    """Test 3: imbalance_score calculation."""
    # 60% bid, 40% ask -> (60-40)/(60+40) = 0.2
    imbalance = engine.calculate_imbalance_score(
        bid_volume=60000.0,
        ask_volume=40000.0,
    )
    assert imbalance == 0.2
    
    # Negative imbalance (more asks)
    imbalance = engine.calculate_imbalance_score(
        bid_volume=30000.0,
        ask_volume=70000.0,
    )
    assert imbalance == -0.4
    
    # Edge case: zero volumes
    assert engine.calculate_imbalance_score(0, 0) == 0.0


# ══════════════════════════════════════════════════════════════
# Test 4: Liquidity State DEEP
# ══════════════════════════════════════════════════════════════

def test_liquidity_state_deep(engine):
    """Test 4: liquidity_state DEEP."""
    state = engine.classify_liquidity_state(
        depth_score=0.80,  # >= 0.70
        spread_bps=3.0,    # <= 5.0
    )
    assert state == "DEEP"


# ══════════════════════════════════════════════════════════════
# Test 5: Liquidity State NORMAL
# ══════════════════════════════════════════════════════════════

def test_liquidity_state_normal(engine):
    """Test 5: liquidity_state NORMAL."""
    state = engine.classify_liquidity_state(
        depth_score=0.55,  # 0.40-0.70
        spread_bps=8.0,    # < 15
    )
    assert state == "NORMAL"


# ══════════════════════════════════════════════════════════════
# Test 6: Liquidity State THIN
# ══════════════════════════════════════════════════════════════

def test_liquidity_state_thin(engine):
    """Test 6: liquidity_state THIN."""
    # High spread triggers THIN
    state = engine.classify_liquidity_state(
        depth_score=0.80,
        spread_bps=20.0,  # > 15
    )
    assert state == "THIN"
    
    # Low depth triggers THIN
    state = engine.classify_liquidity_state(
        depth_score=0.30,  # < 0.40
        spread_bps=8.0,
    )
    assert state == "THIN"


# ══════════════════════════════════════════════════════════════
# Test 7: Pressure State BUY_PRESSURE
# ══════════════════════════════════════════════════════════════

def test_pressure_state_buy_pressure(engine):
    """Test 7: pressure_state BUY_PRESSURE."""
    state = engine.classify_pressure_state(
        imbalance_score=0.25,  # > 0.15
    )
    assert state == "BUY_PRESSURE"


# ══════════════════════════════════════════════════════════════
# Test 8: Pressure State SELL_PRESSURE
# ══════════════════════════════════════════════════════════════

def test_pressure_state_sell_pressure(engine):
    """Test 8: pressure_state SELL_PRESSURE."""
    state = engine.classify_pressure_state(
        imbalance_score=-0.30,  # < -0.15
    )
    assert state == "SELL_PRESSURE"


# ══════════════════════════════════════════════════════════════
# Test 9: Pressure State BALANCED
# ══════════════════════════════════════════════════════════════

def test_pressure_state_balanced(engine):
    """Test 9: pressure_state BALANCED."""
    state = engine.classify_pressure_state(
        imbalance_score=0.05,  # between -0.15 and 0.15
    )
    assert state == "BALANCED"


# ══════════════════════════════════════════════════════════════
# Test 10: Microstructure State SUPPORTIVE
# ══════════════════════════════════════════════════════════════

def test_microstructure_state_supportive(engine):
    """Test 10: supportive microstructure classification."""
    state = engine.classify_microstructure_state(
        liquidity_state="DEEP",
        pressure_state="BUY_PRESSURE",
        liquidation_pressure=0.2,
        funding_pressure=0.1,
        oi_pressure=0.15,
    )
    assert state == "SUPPORTIVE"


# ══════════════════════════════════════════════════════════════
# Test 11: Microstructure State NEUTRAL
# ══════════════════════════════════════════════════════════════

def test_microstructure_state_neutral(engine):
    """Test 11: neutral microstructure classification."""
    state = engine.classify_microstructure_state(
        liquidity_state="NORMAL",
        pressure_state="BALANCED",
        liquidation_pressure=0.1,
        funding_pressure=0.1,
        oi_pressure=0.1,
    )
    assert state == "NEUTRAL"


# ══════════════════════════════════════════════════════════════
# Test 12: Microstructure State FRAGILE
# ══════════════════════════════════════════════════════════════

def test_microstructure_state_fragile(engine):
    """Test 12: fragile microstructure classification."""
    state = engine.classify_microstructure_state(
        liquidity_state="THIN",
        pressure_state="BALANCED",
        liquidation_pressure=0.2,  # Low stress
        funding_pressure=0.1,
        oi_pressure=0.1,
    )
    assert state == "FRAGILE"


# ══════════════════════════════════════════════════════════════
# Test 13: Microstructure State STRESSED
# ══════════════════════════════════════════════════════════════

def test_microstructure_state_stressed(engine):
    """Test 13: stressed microstructure classification."""
    state = engine.classify_microstructure_state(
        liquidity_state="THIN",
        pressure_state="SELL_PRESSURE",
        liquidation_pressure=0.7,  # High stress
        funding_pressure=0.6,
        oi_pressure=0.5,
    )
    assert state == "STRESSED"


# ══════════════════════════════════════════════════════════════
# Test 14: Confidence Calculation
# ══════════════════════════════════════════════════════════════

def test_confidence_calculation(engine):
    """Test 14: confidence calculation."""
    confidence = engine.calculate_confidence(
        spread_bps=2.0,  # Low spread = good
        depth_score=0.8,  # High depth = good
        imbalance_score=0.3,
        liquidation_pressure=0.2,
        oi_pressure=0.15,
    )
    
    # Confidence should be reasonable (0.4-0.9 range typically)
    assert 0.0 <= confidence <= 1.0
    assert confidence > 0.4  # With good inputs, should be decent
    
    # Verify bounds
    assert engine.calculate_confidence(0, 0, 0, 0, 0) == 0.25  # Only spread component


# ══════════════════════════════════════════════════════════════
# Test 15: Full Snapshot Build
# ══════════════════════════════════════════════════════════════

def test_full_snapshot_build(engine):
    """Test 15: current endpoint / full snapshot build."""
    orderbook = OrderbookData(
        best_bid=42000.0,
        best_ask=42010.0,
        bid_volume=120000.0,
        ask_volume=80000.0,
        total_depth=800000.0,
        depth_reference=1000000.0,
    )
    
    exchange = ExchangeData(
        liquidation_long=1000000.0,
        liquidation_short=500000.0,
        funding_rate=0.0002,
        oi_current=1000000000.0,
        oi_previous=980000000.0,
    )
    
    snapshot = engine.build_snapshot("BTC", orderbook, exchange)
    
    # Verify snapshot structure
    assert snapshot.symbol == "BTC"
    assert snapshot.spread_bps > 0
    assert 0 <= snapshot.depth_score <= 1
    assert -1 <= snapshot.imbalance_score <= 1
    assert -1 <= snapshot.liquidation_pressure <= 1
    assert -1 <= snapshot.funding_pressure <= 1
    assert -1 <= snapshot.oi_pressure <= 1
    assert snapshot.liquidity_state in ["DEEP", "NORMAL", "THIN"]
    assert snapshot.pressure_state in ["BUY_PRESSURE", "SELL_PRESSURE", "BALANCED"]
    assert snapshot.microstructure_state in ["SUPPORTIVE", "NEUTRAL", "FRAGILE", "STRESSED"]
    assert 0 <= snapshot.confidence <= 1
    assert len(snapshot.reason) > 0


# ══════════════════════════════════════════════════════════════
# Test 16: Registry Store and History
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_store_and_history(engine, registry):
    """Test 16: summary/history endpoints - registry operations."""
    # Build snapshot
    snapshot = engine.build_snapshot_simulated("ETH")
    
    # Store
    record = await registry.store_snapshot(snapshot)
    assert record.symbol == "ETH"
    
    # Get history
    history = await registry.get_history("ETH", limit=10)
    assert len(history) >= 1
    
    # Get latest
    latest = await registry.get_latest("ETH")
    assert latest is not None
    assert latest.symbol == "ETH"
    
    # Get summary
    summary = await registry.get_summary("ETH")
    assert summary.symbol == "ETH"
    assert summary.total_records >= 1


# ══════════════════════════════════════════════════════════════
# Additional Edge Case Tests
# ══════════════════════════════════════════════════════════════

def test_liquidation_pressure_calculation(engine):
    """Test liquidation pressure with various scenarios."""
    # More shorts liquidated = bullish
    pressure = engine.calculate_liquidation_pressure(
        liquidation_long=100000,
        liquidation_short=300000,
    )
    assert pressure > 0  # Bullish
    
    # More longs liquidated = bearish
    pressure = engine.calculate_liquidation_pressure(
        liquidation_long=400000,
        liquidation_short=100000,
    )
    assert pressure < 0  # Bearish


def test_funding_pressure_calculation(engine):
    """Test funding pressure normalization."""
    # Positive funding = overcrowded longs
    pressure = engine.calculate_funding_pressure(0.005)
    assert pressure > 0
    assert pressure <= 1.0
    
    # Negative funding = overcrowded shorts
    pressure = engine.calculate_funding_pressure(-0.003)
    assert pressure < 0
    assert pressure >= -1.0


def test_oi_pressure_calculation(engine):
    """Test OI pressure with various changes."""
    # OI increasing
    pressure = engine.calculate_oi_pressure(
        oi_current=1050000000,
        oi_previous=1000000000,
    )
    assert pressure > 0  # 5% increase
    
    # OI decreasing
    pressure = engine.calculate_oi_pressure(
        oi_current=950000000,
        oi_previous=1000000000,
    )
    assert pressure < 0  # 5% decrease


def test_reason_generation(engine):
    """Test reason string generation."""
    reason = engine.generate_reason(
        liquidity_state="DEEP",
        pressure_state="BUY_PRESSURE",
        microstructure_state="SUPPORTIVE",
        liquidation_pressure=0.2,
    )
    
    assert "deep orderbook" in reason
    assert "buy imbalance" in reason
    assert "manageable" in reason


def test_simulated_snapshot(engine):
    """Test simulated snapshot generation."""
    snapshot = engine.build_snapshot_simulated("SOL")
    
    assert snapshot.symbol == "SOL"
    assert snapshot.spread_bps >= 0
    assert isinstance(snapshot.microstructure_state, str)


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

def run_all_tests():
    """Run all tests and print results."""
    engine = MicrostructureSnapshotEngine()
    registry = MicrostructureRegistry(db=None)
    
    results = []
    
    # Test 1
    try:
        test_spread_bps_calculation(engine)
        results.append(("1. spread_bps calculation", "PASS"))
    except AssertionError as e:
        results.append(("1. spread_bps calculation", f"FAIL: {e}"))
    
    # Test 2
    try:
        test_depth_score_calculation(engine)
        results.append(("2. depth_score calculation", "PASS"))
    except AssertionError as e:
        results.append(("2. depth_score calculation", f"FAIL: {e}"))
    
    # Test 3
    try:
        test_imbalance_score_calculation(engine)
        results.append(("3. imbalance_score calculation", "PASS"))
    except AssertionError as e:
        results.append(("3. imbalance_score calculation", f"FAIL: {e}"))
    
    # Test 4
    try:
        test_liquidity_state_deep(engine)
        results.append(("4. liquidity_state DEEP", "PASS"))
    except AssertionError as e:
        results.append(("4. liquidity_state DEEP", f"FAIL: {e}"))
    
    # Test 5
    try:
        test_liquidity_state_normal(engine)
        results.append(("5. liquidity_state NORMAL", "PASS"))
    except AssertionError as e:
        results.append(("5. liquidity_state NORMAL", f"FAIL: {e}"))
    
    # Test 6
    try:
        test_liquidity_state_thin(engine)
        results.append(("6. liquidity_state THIN", "PASS"))
    except AssertionError as e:
        results.append(("6. liquidity_state THIN", f"FAIL: {e}"))
    
    # Test 7
    try:
        test_pressure_state_buy_pressure(engine)
        results.append(("7. pressure_state BUY_PRESSURE", "PASS"))
    except AssertionError as e:
        results.append(("7. pressure_state BUY_PRESSURE", f"FAIL: {e}"))
    
    # Test 8
    try:
        test_pressure_state_sell_pressure(engine)
        results.append(("8. pressure_state SELL_PRESSURE", "PASS"))
    except AssertionError as e:
        results.append(("8. pressure_state SELL_PRESSURE", f"FAIL: {e}"))
    
    # Test 9
    try:
        test_pressure_state_balanced(engine)
        results.append(("9. pressure_state BALANCED", "PASS"))
    except AssertionError as e:
        results.append(("9. pressure_state BALANCED", f"FAIL: {e}"))
    
    # Test 10
    try:
        test_microstructure_state_supportive(engine)
        results.append(("10. supportive classification", "PASS"))
    except AssertionError as e:
        results.append(("10. supportive classification", f"FAIL: {e}"))
    
    # Test 11
    try:
        test_microstructure_state_neutral(engine)
        results.append(("11. neutral classification", "PASS"))
    except AssertionError as e:
        results.append(("11. neutral classification", f"FAIL: {e}"))
    
    # Test 12
    try:
        test_microstructure_state_fragile(engine)
        results.append(("12. fragile classification", "PASS"))
    except AssertionError as e:
        results.append(("12. fragile classification", f"FAIL: {e}"))
    
    # Test 13
    try:
        test_microstructure_state_stressed(engine)
        results.append(("13. stressed classification", "PASS"))
    except AssertionError as e:
        results.append(("13. stressed classification", f"FAIL: {e}"))
    
    # Test 14
    try:
        test_confidence_calculation(engine)
        results.append(("14. confidence calculation", "PASS"))
    except AssertionError as e:
        results.append(("14. confidence calculation", f"FAIL: {e}"))
    
    # Test 15
    try:
        test_full_snapshot_build(engine)
        results.append(("15. current endpoint", "PASS"))
    except AssertionError as e:
        results.append(("15. current endpoint", f"FAIL: {e}"))
    
    # Test 16
    try:
        asyncio.get_event_loop().run_until_complete(
            test_registry_store_and_history(engine, registry)
        )
        results.append(("16. summary/history endpoints", "PASS"))
    except Exception as e:
        results.append(("16. summary/history endpoints", f"FAIL: {e}"))
    
    # Print results
    print("\n" + "=" * 60)
    print("PHASE 28.1 — Microstructure Snapshot Engine Tests")
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
