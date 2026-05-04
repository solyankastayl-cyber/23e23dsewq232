"""
Memory Auto-Write Tests

TASK 93 — Auto-write Memory Records after Outcome Tracking

Tests for automatic memory record creation from outcome tracking.
Minimum 12 tests as per requirements.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from .memory_auto_writer import MemoryAutoWriter, get_memory_auto_writer
from .memory_types import RegimeMemoryRecord
from ..hypothesis_competition.outcome_tracking_types import HypothesisOutcome


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def writer():
    """Create fresh writer instance."""
    w = MemoryAutoWriter()
    w.clear_cache()
    return w


@pytest.fixture
def sample_outcome():
    """Create sample hypothesis outcome."""
    return HypothesisOutcome(
        symbol="BTC",
        hypothesis_type="BULLISH_CONTINUATION",
        directional_bias="LONG",
        price_at_creation=100000.0,
        evaluation_price=101500.0,
        horizon_minutes=60,
        expected_direction="UP",
        actual_direction="UP",
        pnl_percent=1.5,
        success=True,
        confidence=0.75,
        reliability=0.80,
        capital_weight=0.25,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )


@pytest.fixture
def failed_outcome():
    """Create sample failed outcome."""
    return HypothesisOutcome(
        symbol="ETH",
        hypothesis_type="BEARISH_CONTINUATION",
        directional_bias="SHORT",
        price_at_creation=3500.0,
        evaluation_price=3550.0,
        horizon_minutes=15,
        expected_direction="DOWN",
        actual_direction="UP",
        pnl_percent=-1.43,
        success=False,
        confidence=0.65,
        reliability=0.70,
        capital_weight=0.20,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=30),
    )


# ══════════════════════════════════════════════════════════════
# 1. Deduplication Tests
# ══════════════════════════════════════════════════════════════

def test_generate_outcome_id_unique(writer, sample_outcome):
    """Test outcome ID generation is deterministic."""
    id1 = writer._generate_outcome_id(sample_outcome)
    id2 = writer._generate_outcome_id(sample_outcome)
    
    assert id1 == id2
    assert len(id1) == 16


def test_generate_outcome_id_different_outcomes(writer, sample_outcome, failed_outcome):
    """Test different outcomes get different IDs."""
    id1 = writer._generate_outcome_id(sample_outcome)
    id2 = writer._generate_outcome_id(failed_outcome)
    
    assert id1 != id2


def test_is_duplicate_false_initially(writer, sample_outcome):
    """Test new outcome is not duplicate."""
    outcome_id = writer._generate_outcome_id(sample_outcome)
    
    assert not writer._is_duplicate(outcome_id)


def test_is_duplicate_after_write(writer, sample_outcome):
    """Test duplicate detection after write."""
    # Write once
    writer.write_from_outcome(sample_outcome)
    
    # Check duplicate
    outcome_id = writer._generate_outcome_id(sample_outcome)
    assert writer._is_duplicate(outcome_id)


# ══════════════════════════════════════════════════════════════
# 2. State Extraction Tests
# ══════════════════════════════════════════════════════════════

def test_map_hypothesis_type_bullish(writer):
    """Test hypothesis type mapping for bullish."""
    assert writer._map_hypothesis_type("BULLISH_CONTINUATION") == "BULLISH_CONTINUATION"
    assert writer._map_hypothesis_type("TREND_CONTINUATION") == "BULLISH_CONTINUATION"


def test_map_hypothesis_type_bearish(writer):
    """Test hypothesis type mapping for bearish."""
    assert writer._map_hypothesis_type("BEARISH_CONTINUATION") == "BEARISH_CONTINUATION"
    assert writer._map_hypothesis_type("TREND_REVERSAL") == "BEARISH_CONTINUATION"


def test_map_hypothesis_type_unknown(writer):
    """Test unknown hypothesis type defaults to NO_EDGE."""
    assert writer._map_hypothesis_type("UNKNOWN_TYPE") == "NO_EDGE"


def test_derive_trend_slope_long(writer, sample_outcome):
    """Test trend slope derivation for LONG."""
    sample_outcome.directional_bias = "LONG"
    sample_outcome.confidence = 0.8
    
    slope = writer._derive_trend_slope(sample_outcome)
    
    assert slope > 0
    assert slope <= 1.0


def test_derive_trend_slope_short(writer, failed_outcome):
    """Test trend slope derivation for SHORT."""
    failed_outcome.directional_bias = "SHORT"
    failed_outcome.confidence = 0.7
    
    slope = writer._derive_trend_slope(failed_outcome)
    
    assert slope < 0
    assert slope >= -1.0


# ══════════════════════════════════════════════════════════════
# 3. Write Operation Tests
# ══════════════════════════════════════════════════════════════

def test_write_from_outcome_returns_id(writer, sample_outcome):
    """Test write returns record ID."""
    record_id = writer.write_from_outcome(sample_outcome)
    
    assert record_id is not None
    assert len(record_id) == 16


def test_write_from_outcome_duplicate_returns_none(writer, sample_outcome):
    """Test duplicate write returns None."""
    # First write
    writer.write_from_outcome(sample_outcome)
    
    # Duplicate write
    result = writer.write_from_outcome(sample_outcome)
    
    assert result is None


def test_write_batch_counts(writer, sample_outcome, failed_outcome):
    """Test batch write returns correct count."""
    count = writer.write_batch([sample_outcome, failed_outcome])
    
    assert count == 2


def test_write_batch_no_duplicates(writer, sample_outcome):
    """Test batch write handles duplicates."""
    # Write same outcome twice in batch
    count = writer.write_batch([sample_outcome, sample_outcome])
    
    # First should succeed, second should be duplicate
    assert count == 1


# ══════════════════════════════════════════════════════════════
# 4. Structure Vector Tests
# ══════════════════════════════════════════════════════════════

def test_build_structure_vector_size(writer, sample_outcome):
    """Test structure vector has correct size."""
    vector = writer._build_structure_vector("BTC", sample_outcome)
    
    assert len(vector) == 7


def test_build_structure_vector_bounds(writer, sample_outcome):
    """Test structure vector values are bounded."""
    vector = writer._build_structure_vector("ETH", sample_outcome)
    
    for i, val in enumerate(vector):
        assert -1.0 <= val <= 1.0, f"Vector element {i} out of bounds: {val}"


# ══════════════════════════════════════════════════════════════
# 5. Stats Tests
# ══════════════════════════════════════════════════════════════

def test_get_stats_initial(writer):
    """Test stats are empty initially."""
    stats = writer.get_stats()
    
    assert stats["total_written"] == 0


def test_get_stats_after_writes(writer, sample_outcome, failed_outcome):
    """Test stats update after writes."""
    writer.write_from_outcome(sample_outcome)
    writer.write_from_outcome(failed_outcome)
    
    stats = writer.get_stats()
    
    assert stats["total_written"] == 2


def test_clear_cache(writer, sample_outcome):
    """Test cache clearing."""
    writer.write_from_outcome(sample_outcome)
    assert writer.get_stats()["total_written"] == 1
    
    writer.clear_cache()
    assert writer.get_stats()["total_written"] == 0


# ══════════════════════════════════════════════════════════════
# 6. Singleton Test
# ══════════════════════════════════════════════════════════════

def test_singleton_returns_same_instance():
    """Test singleton returns same instance."""
    writer1 = get_memory_auto_writer()
    writer2 = get_memory_auto_writer()
    
    assert writer1 is writer2


# ══════════════════════════════════════════════════════════════
# 7. Edge Cases
# ══════════════════════════════════════════════════════════════

def test_write_outcome_with_zero_confidence(writer):
    """Test writing outcome with zero confidence."""
    outcome = HypothesisOutcome(
        symbol="SOL",
        hypothesis_type="NO_EDGE",
        directional_bias="NEUTRAL",
        price_at_creation=150.0,
        evaluation_price=150.5,
        horizon_minutes=5,
        expected_direction="FLAT",
        actual_direction="FLAT",
        pnl_percent=0.33,
        success=True,
        confidence=0.0,
        reliability=0.0,
        created_at=datetime.now(timezone.utc),
    )
    
    result = writer.write_from_outcome(outcome)
    assert result is not None


def test_write_outcome_with_negative_pnl(writer):
    """Test writing outcome with negative PnL."""
    outcome = HypothesisOutcome(
        symbol="BTC",
        hypothesis_type="BEARISH_CONTINUATION",
        directional_bias="SHORT",
        price_at_creation=100000.0,
        evaluation_price=103000.0,
        horizon_minutes=240,
        expected_direction="DOWN",
        actual_direction="UP",
        pnl_percent=-3.0,
        success=False,
        confidence=0.85,
        reliability=0.75,
        created_at=datetime.now(timezone.utc),
    )
    
    result = writer.write_from_outcome(outcome)
    assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
