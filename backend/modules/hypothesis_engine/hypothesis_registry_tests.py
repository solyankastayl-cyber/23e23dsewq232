"""
Hypothesis Registry — Tests

PHASE 29.4 — 18+ tests for Hypothesis Registry / History

Isolated tests using in-memory cache mode.
"""

import pytest
import asyncio
from datetime import datetime, timezone

from modules.hypothesis_engine.hypothesis_registry import (
    HypothesisRegistry,
    HypothesisHistoryRecordExtended,
    HypothesisStats,
)
from modules.hypothesis_engine.hypothesis_types import (
    MarketHypothesis,
    HypothesisInputLayers,
)
from modules.hypothesis_engine.hypothesis_engine import (
    HypothesisEngine,
)


# ══════════════════════════════════════════════════════════════
# Helper to create isolated registry
# ══════════════════════════════════════════════════════════════

def create_isolated_registry():
    """Create a registry with isolated in-memory cache."""
    r = HypothesisRegistry()
    r._use_cache = True
    r._cache = []
    r._db = None
    return r


def create_sample_hypothesis(
    symbol="BTC",
    hypothesis_type="BULLISH_CONTINUATION",
    bias="LONG",
    confidence=0.65,
    reliability=0.56,
    structural_score=0.72,
    execution_score=0.58,
    conflict_score=0.11,
    conflict_state="MODERATE_CONFLICT",
    execution_state="CAUTIOUS",
):
    return MarketHypothesis(
        symbol=symbol,
        hypothesis_type=hypothesis_type,
        directional_bias=bias,
        structural_score=structural_score,
        execution_score=execution_score,
        conflict_score=conflict_score,
        conflict_state=conflict_state,
        confidence=confidence,
        reliability=reliability,
        alpha_support=0.7,
        regime_support=0.6,
        microstructure_support=0.55,
        macro_fractal_support=0.5,
        execution_state=execution_state,
        reason="test hypothesis",
    )


# ══════════════════════════════════════════════════════════════
# Test 1: Store Hypothesis Works
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_store_hypothesis_works():
    """Test that store_hypothesis stores correctly."""
    registry = create_isolated_registry()
    hypothesis = create_sample_hypothesis()
    
    record = await registry.store_hypothesis(hypothesis)
    
    assert record.symbol == "BTC"
    assert record.hypothesis_type == "BULLISH_CONTINUATION"
    assert record.directional_bias == "LONG"
    assert record.confidence == 0.65
    assert len(registry._cache) == 1


# ══════════════════════════════════════════════════════════════
# Test 2: Price At Creation Saves
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_price_at_creation_saves():
    """Test that price_at_creation is stored."""
    registry = create_isolated_registry()
    hypothesis = create_sample_hypothesis()
    
    record = await registry.store_hypothesis(
        hypothesis,
        price_at_creation=68450.25,
    )
    
    assert record.price_at_creation == 68450.25


# ══════════════════════════════════════════════════════════════
# Test 3: History Retrieval
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_history_retrieval():
    """Test hypothesis history retrieval."""
    registry = create_isolated_registry()
    hypothesis = create_sample_hypothesis()
    
    for i in range(5):
        await registry.store_hypothesis(hypothesis)
    
    history = await registry.get_history("BTC", limit=10)
    
    assert len(history) == 5
    assert all(h.symbol == "BTC" for h in history)


# ══════════════════════════════════════════════════════════════
# Test 4: Symbol History Retrieval
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_symbol_history_retrieval():
    """Test get_symbol_history (alias)."""
    registry = create_isolated_registry()
    hypothesis = create_sample_hypothesis()
    
    await registry.store_hypothesis(hypothesis)
    
    history = await registry.get_symbol_history("BTC")
    
    assert len(history) == 1
    assert history[0].symbol == "BTC"


# ══════════════════════════════════════════════════════════════
# Test 5: Recent Hypotheses
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_recent_hypotheses():
    """Test get_recent_hypotheses across all symbols."""
    registry = create_isolated_registry()
    
    for symbol in ["BTC", "ETH", "SOL"]:
        h = create_sample_hypothesis(symbol=symbol)
        await registry.store_hypothesis(h)
    
    recent = await registry.get_recent_hypotheses(limit=10)
    
    assert len(recent) == 3
    symbols = {r.symbol for r in recent}
    assert symbols == {"BTC", "ETH", "SOL"}


# ══════════════════════════════════════════════════════════════
# Test 6: Stats Calculation
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_stats_calculation():
    """Test get_hypothesis_stats calculation."""
    registry = create_isolated_registry()
    
    types = ["BULLISH_CONTINUATION", "BEARISH_CONTINUATION", "BREAKOUT_FORMING"]
    biases = ["LONG", "SHORT", "NEUTRAL"]
    
    for i, (t, b) in enumerate(zip(types, biases)):
        h = create_sample_hypothesis(
            hypothesis_type=t,
            bias=b,
            confidence=0.6 + i * 0.05,
        )
        await registry.store_hypothesis(h)
    
    stats = await registry.get_hypothesis_stats("BTC")
    
    assert stats.total_hypotheses == 3


# ══════════════════════════════════════════════════════════════
# Test 7: Confidence Averaging
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_confidence_averaging():
    """Test average confidence calculation."""
    registry = create_isolated_registry()
    confidences = [0.5, 0.6, 0.7, 0.8]
    
    for conf in confidences:
        h = create_sample_hypothesis(symbol="ETH", confidence=conf)
        await registry.store_hypothesis(h)
    
    stats = await registry.get_hypothesis_stats("ETH")
    
    expected_avg = sum(confidences) / len(confidences)
    assert abs(stats.avg_confidence - expected_avg) < 0.01


# ══════════════════════════════════════════════════════════════
# Test 8: Reliability Averaging
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_reliability_averaging():
    """Test average reliability calculation."""
    registry = create_isolated_registry()
    reliabilities = [0.4, 0.5, 0.6, 0.7]
    
    for rel in reliabilities:
        h = create_sample_hypothesis(symbol="SOL", reliability=rel)
        await registry.store_hypothesis(h)
    
    stats = await registry.get_hypothesis_stats("SOL")
    
    expected_avg = sum(reliabilities) / len(reliabilities)
    assert abs(stats.avg_reliability - expected_avg) < 0.01


# ══════════════════════════════════════════════════════════════
# Test 9: Integration with Hypothesis Engine
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_integration_with_hypothesis_engine():
    """Test that registry integrates with hypothesis engine."""
    registry = create_isolated_registry()
    engine = HypothesisEngine()
    
    layers = HypothesisInputLayers(
        alpha_direction="BULLISH",
        alpha_strength=0.75,
        regime_type="TRENDING",
        regime_confidence=0.7,
        microstructure_state="SUPPORTIVE",
        microstructure_confidence=0.8,
        macro_confidence=0.6,
    )
    
    hypothesis = engine.generate_hypothesis("BTC", layers)
    record = await registry.store_hypothesis(hypothesis)
    
    assert record.symbol == hypothesis.symbol
    assert record.hypothesis_type == hypothesis.hypothesis_type
    assert record.structural_score == hypothesis.structural_score
    assert record.conflict_state == hypothesis.conflict_state


# ══════════════════════════════════════════════════════════════
# Test 10: API History Endpoint (simulated)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_api_history_endpoint():
    """Test history retrieval (simulates API /history)."""
    registry = create_isolated_registry()
    
    for _ in range(5):
        h = create_sample_hypothesis()
        await registry.store_hypothesis(h)
    
    history = await registry.get_history("BTC", limit=50)
    
    assert len(history) == 5
    assert all(r.structural_score is not None for r in history)


# ══════════════════════════════════════════════════════════════
# Test 11: API Stats Endpoint (simulated)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_api_stats_endpoint():
    """Test stats retrieval (simulates API /stats)."""
    registry = create_isolated_registry()
    
    for _ in range(10):
        h = create_sample_hypothesis()
        await registry.store_hypothesis(h)
    
    stats = await registry.get_hypothesis_stats("BTC")
    
    assert stats.total_hypotheses == 10
    assert stats.symbol == "BTC"
    assert stats.avg_confidence > 0


# ══════════════════════════════════════════════════════════════
# Test 12: API Recent Endpoint (simulated)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_api_recent_endpoint():
    """Test recent retrieval (simulates API /recent)."""
    registry = create_isolated_registry()
    
    for _ in range(5):
        h = create_sample_hypothesis()
        await registry.store_hypothesis(h)
    
    recent = await registry.get_recent_hypotheses(limit=100)
    
    assert len(recent) == 5


# ══════════════════════════════════════════════════════════════
# Test 13: Empty History Case
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_empty_history_case():
    """Test behavior with empty history."""
    registry = create_isolated_registry()
    
    history = await registry.get_history("UNKNOWN")
    assert history == []
    
    stats = await registry.get_hypothesis_stats("UNKNOWN")
    assert stats.total_hypotheses == 0


# ══════════════════════════════════════════════════════════════
# Test 14: Large History Case
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_large_history_case():
    """Test with large number of hypotheses."""
    registry = create_isolated_registry()
    
    for _ in range(200):
        h = create_sample_hypothesis()
        await registry.store_hypothesis(h)
    
    # Should respect limit
    history = await registry.get_history("BTC", limit=50)
    assert len(history) == 50
    
    # Total count should be full
    total = await registry.get_total_count("BTC")
    assert total == 200


# ══════════════════════════════════════════════════════════════
# Test 15: Timestamp Ordering
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_timestamp_ordering():
    """Test that history is ordered by timestamp (newest first)."""
    registry = create_isolated_registry()
    
    for _ in range(5):
        h = create_sample_hypothesis()
        await registry.store_hypothesis(h)
    
    history = await registry.get_history("BTC")
    
    # Should be ordered newest first
    for i in range(len(history) - 1):
        assert history[i].created_at >= history[i + 1].created_at


# ══════════════════════════════════════════════════════════════
# Test 16: Registry Edge Case
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_edge_case():
    """Test edge cases in registry."""
    registry = create_isolated_registry()
    
    # Empty latest
    latest = await registry.get_latest("EMPTY")
    assert latest is None
    
    # Zero limit
    history = await registry.get_history("BTC", limit=0)
    assert history == []


# ══════════════════════════════════════════════════════════════
# Test 17: Duplicate Storage
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_duplicate_storage():
    """Test that duplicate storage creates separate records."""
    registry = create_isolated_registry()
    hypothesis = create_sample_hypothesis()
    
    await registry.store_hypothesis(hypothesis)
    await registry.store_hypothesis(hypothesis)
    
    total = await registry.get_total_count("BTC")
    assert total == 2


# ══════════════════════════════════════════════════════════════
# Test 18: Integration Recompute
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_integration_recompute():
    """Test that recompute stores to registry."""
    registry = create_isolated_registry()
    engine = HypothesisEngine()
    
    h1 = engine.generate_hypothesis_simulated("BTC")
    await registry.store_hypothesis(h1)
    
    h2 = engine.generate_hypothesis_simulated("BTC")
    await registry.store_hypothesis(h2)
    
    history = await registry.get_history("BTC")
    assert len(history) == 2


# ══════════════════════════════════════════════════════════════
# Test 19: Conflict State in History
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_conflict_state_in_history():
    """Test that conflict_state is stored in history."""
    registry = create_isolated_registry()
    hypothesis = create_sample_hypothesis(conflict_state="HIGH_CONFLICT")
    
    record = await registry.store_hypothesis(hypothesis)
    
    assert record.conflict_state == "HIGH_CONFLICT"
    
    history = await registry.get_history("BTC")
    assert history[0].conflict_state == "HIGH_CONFLICT"


# ══════════════════════════════════════════════════════════════
# Test 20: Structural Score in History
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_structural_score_in_history():
    """Test that structural_score is stored in history."""
    registry = create_isolated_registry()
    hypothesis = create_sample_hypothesis(
        structural_score=0.82,
        execution_score=0.68,
        conflict_score=0.15,
    )
    
    record = await registry.store_hypothesis(hypothesis)
    
    assert record.structural_score == 0.82
    assert record.execution_score == 0.68
    assert record.conflict_score == 0.15
    
    history = await registry.get_history("BTC")
    assert history[0].structural_score == 0.82


# ══════════════════════════════════════════════════════════════
# Test 21: Get All Symbols
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_all_symbols():
    """Test get_all_symbols functionality."""
    registry = create_isolated_registry()
    
    for symbol in ["BTC", "ETH", "SOL", "AVAX"]:
        h = create_sample_hypothesis(symbol=symbol)
        await registry.store_hypothesis(h)
    
    symbols = await registry.get_all_symbols()
    
    assert len(symbols) == 4
    assert set(symbols) == {"BTC", "ETH", "SOL", "AVAX"}


# ══════════════════════════════════════════════════════════════
# Test 22: Clear History
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_clear_history():
    """Test clear_history functionality."""
    registry = create_isolated_registry()
    hypothesis = create_sample_hypothesis()
    
    for _ in range(5):
        await registry.store_hypothesis(hypothesis)
    
    await registry.clear_history("BTC")
    
    history = await registry.get_history("BTC")
    assert len(history) == 0


# ══════════════════════════════════════════════════════════════
# Run tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
