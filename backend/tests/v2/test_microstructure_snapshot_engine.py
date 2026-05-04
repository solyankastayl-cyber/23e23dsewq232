"""
Tests for Microstructure Snapshot Engine (PHASE 28.1)

Minimum 16 tests:
 1  spread_bps calculation
 2  depth_score calculation
 3  imbalance_score calculation
 4  liquidity_state DEEP
 5  liquidity_state NORMAL
 6  liquidity_state THIN
 7  pressure_state BUY_PRESSURE
 8  pressure_state SELL_PRESSURE
 9  pressure_state BALANCED
10  supportive microstructure classification
11  neutral microstructure classification
12  fragile microstructure classification
13  stressed microstructure classification
14  confidence calculation
15  current endpoint
16  summary/history endpoints
"""

import sys
import os
import pytest
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from modules.microstructure_intelligence_v2.microstructure_snapshot_engine import (
    MicrostructureSnapshotEngine,
    get_microstructure_snapshot_engine,
)
from modules.microstructure_intelligence_v2.microstructure_registry import (
    MicrostructureRegistry,
)
from modules.microstructure_intelligence_v2.microstructure_types import (
    MicrostructureSnapshot,
    OrderbookData,
    ExchangeData,
    DEPTH_DEEP_THRESHOLD,
    DEPTH_NORMAL_THRESHOLD,
    SPREAD_LOW_THRESHOLD,
    SPREAD_HIGH_THRESHOLD,
    IMBALANCE_THRESHOLD,
)


@pytest.fixture
def engine():
    return MicrostructureSnapshotEngine()


@pytest.fixture
def registry():
    return MicrostructureRegistry()


# ══════════════════════════════════════════════════════════════
# 1. spread_bps calculation
# ══════════════════════════════════════════════════════════════

def test_spread_bps_calculation(engine):
    """spread_bps = ((ask - bid) / mid) * 10000"""
    bid = 42000.0
    ask = 42004.2
    mid = (bid + ask) / 2
    expected = ((ask - bid) / mid) * 10000

    result = engine.calculate_spread_bps(bid, ask)
    assert abs(result - round(expected, 2)) < 0.01


def test_spread_bps_zero_bid(engine):
    """Edge case: bid=0 returns 0."""
    assert engine.calculate_spread_bps(0.0, 100.0) == 0.0


# ══════════════════════════════════════════════════════════════
# 2. depth_score calculation
# ══════════════════════════════════════════════════════════════

def test_depth_score_calculation(engine):
    """depth_score = min(total_depth / reference, 1.0)"""
    assert engine.calculate_depth_score(700000, 1000000) == 0.7
    assert engine.calculate_depth_score(1500000, 1000000) == 1.0
    assert engine.calculate_depth_score(0, 1000000) == 0.0


def test_depth_score_zero_reference(engine):
    """Edge case: reference=0 returns 0.5"""
    assert engine.calculate_depth_score(500000, 0) == 0.5


# ══════════════════════════════════════════════════════════════
# 3. imbalance_score calculation
# ══════════════════════════════════════════════════════════════

def test_imbalance_score_calculation(engine):
    """imbalance = (bid - ask) / (bid + ask)"""
    # Bid > Ask => positive
    score = engine.calculate_imbalance_score(150000, 100000)
    assert score == 0.2

    # Ask > Bid => negative
    score = engine.calculate_imbalance_score(100000, 150000)
    assert score == -0.2

    # Equal => 0
    score = engine.calculate_imbalance_score(100000, 100000)
    assert score == 0.0


def test_imbalance_score_zero_volume(engine):
    """Edge case: total volume=0 returns 0."""
    assert engine.calculate_imbalance_score(0, 0) == 0.0


# ══════════════════════════════════════════════════════════════
# 4. liquidity_state DEEP
# ══════════════════════════════════════════════════════════════

def test_liquidity_state_deep(engine):
    """DEEP: depth >= 0.70 and spread <= 5.0 bps"""
    state = engine.classify_liquidity_state(depth_score=0.80, spread_bps=3.0)
    assert state == "DEEP"


# ══════════════════════════════════════════════════════════════
# 5. liquidity_state NORMAL
# ══════════════════════════════════════════════════════════════

def test_liquidity_state_normal(engine):
    """NORMAL: depth 0.40-0.70"""
    state = engine.classify_liquidity_state(depth_score=0.55, spread_bps=8.0)
    assert state == "NORMAL"


# ══════════════════════════════════════════════════════════════
# 6. liquidity_state THIN
# ══════════════════════════════════════════════════════════════

def test_liquidity_state_thin_low_depth(engine):
    """THIN: depth < 0.40"""
    state = engine.classify_liquidity_state(depth_score=0.30, spread_bps=8.0)
    assert state == "THIN"


def test_liquidity_state_thin_high_spread(engine):
    """THIN: spread > 15 bps regardless of depth"""
    state = engine.classify_liquidity_state(depth_score=0.80, spread_bps=20.0)
    assert state == "THIN"


# ══════════════════════════════════════════════════════════════
# 7. pressure_state BUY_PRESSURE
# ══════════════════════════════════════════════════════════════

def test_pressure_state_buy(engine):
    """BUY_PRESSURE: imbalance > 0.15"""
    state = engine.classify_pressure_state(0.25)
    assert state == "BUY_PRESSURE"


# ══════════════════════════════════════════════════════════════
# 8. pressure_state SELL_PRESSURE
# ══════════════════════════════════════════════════════════════

def test_pressure_state_sell(engine):
    """SELL_PRESSURE: imbalance < -0.15"""
    state = engine.classify_pressure_state(-0.25)
    assert state == "SELL_PRESSURE"


# ══════════════════════════════════════════════════════════════
# 9. pressure_state BALANCED
# ══════════════════════════════════════════════════════════════

def test_pressure_state_balanced(engine):
    """BALANCED: -0.15 <= imbalance <= 0.15"""
    state = engine.classify_pressure_state(0.05)
    assert state == "BALANCED"


# ══════════════════════════════════════════════════════════════
# 10. SUPPORTIVE microstructure classification
# ══════════════════════════════════════════════════════════════

def test_microstructure_supportive(engine):
    """SUPPORTIVE: DEEP liquidity, low stress"""
    state = engine.classify_microstructure_state(
        liquidity_state="DEEP",
        pressure_state="BUY_PRESSURE",
        liquidation_pressure=0.2,
        funding_pressure=0.1,
        oi_pressure=0.15,
    )
    assert state == "SUPPORTIVE"


# ══════════════════════════════════════════════════════════════
# 11. NEUTRAL microstructure classification
# ══════════════════════════════════════════════════════════════

def test_microstructure_neutral(engine):
    """NEUTRAL: NORMAL liquidity, BALANCED pressure"""
    state = engine.classify_microstructure_state(
        liquidity_state="NORMAL",
        pressure_state="BALANCED",
        liquidation_pressure=0.1,
        funding_pressure=0.05,
        oi_pressure=0.1,
    )
    assert state == "NEUTRAL"


# ══════════════════════════════════════════════════════════════
# 12. FRAGILE microstructure classification
# ══════════════════════════════════════════════════════════════

def test_microstructure_fragile(engine):
    """FRAGILE: THIN liquidity, moderate stress"""
    state = engine.classify_microstructure_state(
        liquidity_state="THIN",
        pressure_state="BALANCED",
        liquidation_pressure=0.2,
        funding_pressure=0.1,
        oi_pressure=0.15,
    )
    assert state == "FRAGILE"


# ══════════════════════════════════════════════════════════════
# 13. STRESSED microstructure classification
# ══════════════════════════════════════════════════════════════

def test_microstructure_stressed(engine):
    """STRESSED: THIN liquidity + high stress"""
    state = engine.classify_microstructure_state(
        liquidity_state="THIN",
        pressure_state="SELL_PRESSURE",
        liquidation_pressure=0.8,
        funding_pressure=0.7,
        oi_pressure=0.6,
    )
    assert state == "STRESSED"


# ══════════════════════════════════════════════════════════════
# 14. confidence calculation
# ══════════════════════════════════════════════════════════════

def test_confidence_calculation(engine):
    """Confidence formula verification."""
    spread_bps = 2.0
    depth_score = 0.75
    imbalance_score = 0.20
    liquidation_pressure = 0.30
    oi_pressure = 0.25

    normalized_spread = min(spread_bps / 20.0, 1.0)
    expected = (
        0.25 * (1.0 - normalized_spread)
        + 0.25 * depth_score
        + 0.20 * abs(imbalance_score)
        + 0.15 * abs(liquidation_pressure)
        + 0.15 * abs(oi_pressure)
    )
    expected = round(min(max(expected, 0.0), 1.0), 4)

    result = engine.calculate_confidence(
        spread_bps, depth_score, imbalance_score, liquidation_pressure, oi_pressure
    )
    assert abs(result - expected) < 0.001


def test_confidence_bounds(engine):
    """Confidence is bounded 0..1"""
    c = engine.calculate_confidence(0.0, 1.0, 1.0, 1.0, 1.0)
    assert 0.0 <= c <= 1.0

    c = engine.calculate_confidence(100.0, 0.0, 0.0, 0.0, 0.0)
    assert 0.0 <= c <= 1.0


# ══════════════════════════════════════════════════════════════
# 15. Full snapshot build
# ══════════════════════════════════════════════════════════════

def test_build_snapshot_full(engine):
    """Full build_snapshot produces valid MicrostructureSnapshot."""
    orderbook = OrderbookData(
        best_bid=42000.0,
        best_ask=42002.0,
        bid_volume=150000,
        ask_volume=100000,
        total_depth=800000,
        depth_reference=1000000,
    )
    exchange = ExchangeData(
        liquidation_long=1000000,
        liquidation_short=2000000,
        funding_rate=0.002,
        oi_current=1100000000,
        oi_previous=1000000000,
    )
    snapshot = engine.build_snapshot("BTC", orderbook, exchange)

    assert isinstance(snapshot, MicrostructureSnapshot)
    assert snapshot.symbol == "BTC"
    assert snapshot.spread_bps > 0
    assert 0.0 <= snapshot.depth_score <= 1.0
    assert -1.0 <= snapshot.imbalance_score <= 1.0
    assert snapshot.liquidity_state in ("DEEP", "NORMAL", "THIN")
    assert snapshot.pressure_state in ("BUY_PRESSURE", "SELL_PRESSURE", "BALANCED")
    assert snapshot.microstructure_state in ("SUPPORTIVE", "NEUTRAL", "FRAGILE", "STRESSED")
    assert 0.0 <= snapshot.confidence <= 1.0
    assert len(snapshot.reason) > 0


def test_build_snapshot_simulated(engine):
    """Simulated snapshot works."""
    snapshot = engine.build_snapshot_simulated("ETH")
    assert isinstance(snapshot, MicrostructureSnapshot)
    assert snapshot.symbol == "ETH"


# ══════════════════════════════════════════════════════════════
# 16. Pressure metric calculations
# ══════════════════════════════════════════════════════════════

def test_liquidation_pressure(engine):
    """Liquidation: shorts squeezed => positive."""
    p = engine.calculate_liquidation_pressure(1000000, 3000000)
    assert p > 0  # more shorts liquidated = bullish

    p = engine.calculate_liquidation_pressure(3000000, 1000000)
    assert p < 0  # more longs liquidated = bearish


def test_funding_pressure(engine):
    """Funding rate normalization."""
    p = engine.calculate_funding_pressure(0.005)
    assert p == 0.5  # 0.005 * 100

    p = engine.calculate_funding_pressure(-0.005)
    assert p == -0.5


def test_oi_pressure(engine):
    """OI pressure normalization."""
    # 10% increase => 1.0
    p = engine.calculate_oi_pressure(1100000, 1000000)
    assert p == 1.0

    # 5% decrease => -0.5
    p = engine.calculate_oi_pressure(950000, 1000000)
    assert p == -0.5


# ══════════════════════════════════════════════════════════════
# 17. Registry tests
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_store_and_get(engine, registry):
    """Store snapshot and retrieve history."""
    snapshot = engine.build_snapshot_simulated("BTC")
    await registry.store_snapshot(snapshot)

    history = await registry.get_history("BTC", limit=10)
    assert len(history) >= 1
    assert history[0].symbol == "BTC"


@pytest.mark.asyncio
async def test_registry_summary(engine, registry):
    """Summary statistics from stored snapshots."""
    await registry.clear_history("SOL")

    for _ in range(5):
        snapshot = engine.build_snapshot_simulated("SOL")
        await registry.store_snapshot(snapshot)

    summary = await registry.get_summary("SOL")
    assert summary.symbol == "SOL"
    assert summary.total_records == 5
    assert summary.average_spread_bps >= 0
    assert summary.average_depth_score >= 0


@pytest.mark.asyncio
async def test_registry_empty_summary(registry):
    """Summary for unknown symbol returns zeros."""
    await registry.clear_history("UNKNOWN")
    summary = await registry.get_summary("UNKNOWN")
    assert summary.total_records == 0
    assert summary.current_state == "NEUTRAL"


# ══════════════════════════════════════════════════════════════
# 18. Singleton
# ══════════════════════════════════════════════════════════════

def test_singleton():
    """get_microstructure_snapshot_engine returns same instance."""
    e1 = get_microstructure_snapshot_engine()
    e2 = get_microstructure_snapshot_engine()
    assert e1 is e2
