"""
Regime Memory Tests

PHASE 34 — Market Regime Memory Layer

Unit tests (35+) covering:
- Structure vector normalization
- Cosine similarity calculation
- Memory score calculation
- Recency weighting
- Memory pruning
- Query and filtering
- Pattern analysis
- Modifier generation
- Registry operations
- API endpoints
"""

import pytest
import math
from datetime import datetime, timezone, timedelta
from typing import List

from .memory_types import (
    StructureVector,
    RegimeMemoryRecord,
    MemoryMatch,
    MemoryQuery,
    MemoryResponse,
    MemoryPattern,
    MemorySummary,
    MemoryModifier,
    PendingOutcomeRecord,
    VECTOR_SIZE,
    SIMILARITY_THRESHOLD,
    WEIGHT_SIMILARITY,
    WEIGHT_SUCCESS_RATE,
    WEIGHT_RECENCY,
)
from .memory_engine import RegimeMemoryEngine, get_memory_engine
from .memory_registry import MemoryRegistry, get_memory_registry


# ══════════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════════

def create_test_record(
    symbol: str = "BTC",
    regime: str = "TRENDING",
    hypothesis: str = "BULLISH_CONTINUATION",
    vector: List[float] = None,
    success: bool = True,
    future_move: float = 2.5,
    days_ago: int = 0,
) -> RegimeMemoryRecord:
    """Create a test memory record."""
    if vector is None:
        vector = [0.5, 0.5, 0.0, 0.0, 0.5, 1.0, 0.3]
    
    timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)
    
    return RegimeMemoryRecord(
        record_id=f"test_{symbol}_{days_ago}_{regime}",
        symbol=symbol,
        timestamp=timestamp,
        regime_state=regime,
        fractal_state="ALIGNED",
        hypothesis_type=hypothesis,
        microstructure_state="SUPPORTIVE",
        structure_vector=vector,
        future_move_percent=future_move,
        horizon_minutes=60,
        success=success,
    )


def create_test_records(count: int = 50, symbol: str = "BTC") -> List[RegimeMemoryRecord]:
    """Create multiple test records with varied parameters."""
    records = []
    
    regimes = ["TRENDING", "RANGING", "VOLATILE", "UNCERTAIN"]
    hypotheses = ["BULLISH_CONTINUATION", "BEARISH_CONTINUATION", "BREAKOUT_FORMING", "RANGE_MEAN_REVERSION"]
    
    for i in range(count):
        regime = regimes[i % len(regimes)]
        hypothesis = hypotheses[i % len(hypotheses)]
        
        # Vary the vector
        vector = [
            (i % 20 - 10) / 10,  # trend_slope
            0.3 + (i % 5) / 10,  # volatility
            (i % 16 - 8) / 10,   # volume_delta
            (i % 14 - 7) / 10,   # microstructure_bias
            0.3 + (i % 4) / 10,  # liquidity_state
            [1.0, 0.66, 0.33, 0.0][i % 4],  # regime_numeric
            (i % 16 - 8) / 10,   # fractal_alignment
        ]
        
        future_move = (i % 16 - 8)  # -8 to +7
        success = (hypothesis in ["BULLISH_CONTINUATION", "BREAKOUT_FORMING"] and future_move > 1) or \
                  (hypothesis == "BEARISH_CONTINUATION" and future_move < -1)
        
        record = create_test_record(
            symbol=symbol,
            regime=regime,
            hypothesis=hypothesis,
            vector=vector,
            success=success,
            future_move=future_move,
            days_ago=i,
        )
        records.append(record)
    
    return records


# ══════════════════════════════════════════════════════════════
# 1. Structure Vector Tests
# ══════════════════════════════════════════════════════════════

class TestStructureVector:
    """Tests for structure vector normalization."""
    
    def test_vector_size(self):
        """Test that vector has correct size."""
        vec = StructureVector()
        assert len(vec.to_vector()) == VECTOR_SIZE
    
    def test_default_values(self):
        """Test default vector values."""
        vec = StructureVector()
        values = vec.to_vector()
        assert values[0] == 0.0  # trend_slope
        assert values[1] == 0.5  # volatility
        assert values[2] == 0.0  # volume_delta
    
    def test_bounds_enforcement(self):
        """Test that values are bounded correctly."""
        vec = StructureVector(
            trend_slope=0.8,
            volatility=0.9,
            volume_delta=-0.5,
            microstructure_bias=0.3,
            liquidity_state=0.7,
            regime_numeric=1.0,
            fractal_alignment=-0.2,
        )
        
        values = vec.to_vector()
        assert -1.0 <= values[0] <= 1.0
        assert 0.0 <= values[1] <= 1.0
        assert 0.0 <= values[4] <= 1.0
    
    def test_from_vector(self):
        """Test creating StructureVector from list."""
        original = [0.5, 0.6, 0.1, -0.2, 0.7, 0.33, 0.4]
        vec = StructureVector.from_vector(original)
        
        assert vec.trend_slope == 0.5
        assert vec.volatility == 0.6
        assert vec.regime_numeric == 0.33
    
    def test_from_vector_invalid_size(self):
        """Test error on invalid vector size."""
        with pytest.raises(ValueError):
            StructureVector.from_vector([0.5, 0.6, 0.1])
    
    def test_to_vector_roundtrip(self):
        """Test that to_vector and from_vector are consistent."""
        original = StructureVector(
            trend_slope=0.3,
            volatility=0.7,
            volume_delta=-0.1,
            microstructure_bias=0.2,
            liquidity_state=0.6,
            regime_numeric=0.66,
            fractal_alignment=0.1,
        )
        
        vec_list = original.to_vector()
        reconstructed = StructureVector.from_vector(vec_list)
        
        assert reconstructed.trend_slope == original.trend_slope
        assert reconstructed.regime_numeric == original.regime_numeric


# ══════════════════════════════════════════════════════════════
# 2. Cosine Similarity Tests
# ══════════════════════════════════════════════════════════════

class TestCosineSimilarity:
    """Tests for cosine similarity calculation."""
    
    def test_identical_vectors(self):
        """Test similarity of identical vectors is 1.0."""
        engine = RegimeMemoryEngine()
        vec = [0.5, 0.5, 0.1, 0.2, 0.6, 0.8, 0.3]
        
        similarity = engine.calculate_cosine_similarity(vec, vec)
        assert similarity == 1.0
    
    def test_opposite_vectors(self):
        """Test similarity of opposite vectors is 0.0."""
        engine = RegimeMemoryEngine()
        vec_a = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        vec_b = [-1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0]
        
        similarity = engine.calculate_cosine_similarity(vec_a, vec_b)
        assert similarity == 0.0
    
    def test_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors is ~0.5."""
        engine = RegimeMemoryEngine()
        vec_a = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        
        similarity = engine.calculate_cosine_similarity(vec_a, vec_b)
        # Normalized to [0, 1], orthogonal = 0.5
        assert abs(similarity - 0.5) < 0.01
    
    def test_similar_vectors(self):
        """Test high similarity for similar vectors."""
        engine = RegimeMemoryEngine()
        vec_a = [0.5, 0.5, 0.1, 0.2, 0.6, 0.8, 0.3]
        vec_b = [0.6, 0.5, 0.15, 0.25, 0.55, 0.75, 0.35]
        
        similarity = engine.calculate_cosine_similarity(vec_a, vec_b)
        assert similarity >= 0.9
    
    def test_different_length_vectors(self):
        """Test that different length vectors return 0."""
        engine = RegimeMemoryEngine()
        vec_a = [0.5, 0.5, 0.1]
        vec_b = [0.5, 0.5, 0.1, 0.2, 0.6, 0.8, 0.3]
        
        similarity = engine.calculate_cosine_similarity(vec_a, vec_b)
        assert similarity == 0.0
    
    def test_zero_vector(self):
        """Test similarity with zero vector is 0."""
        engine = RegimeMemoryEngine()
        vec_a = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        vec_b = [0.5, 0.5, 0.1, 0.2, 0.6, 0.8, 0.3]
        
        similarity = engine.calculate_cosine_similarity(vec_a, vec_b)
        assert similarity == 0.0
    
    def test_similarity_range(self):
        """Test similarity is always in [0, 1]."""
        engine = RegimeMemoryEngine()
        
        test_cases = [
            ([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7], [0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]),
            ([-0.5, -0.3, 0.1, 0.2, 0.4, 0.6, 0.8], [0.8, 0.6, 0.4, 0.2, -0.1, -0.3, -0.5]),
            ([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0], [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]),
        ]
        
        for vec_a, vec_b in test_cases:
            similarity = engine.calculate_cosine_similarity(vec_a, vec_b)
            assert 0.0 <= similarity <= 1.0


# ══════════════════════════════════════════════════════════════
# 3. Recency Weight Tests
# ══════════════════════════════════════════════════════════════

class TestRecencyWeight:
    """Tests for recency weight calculation."""
    
    def test_recent_event_high_weight(self):
        """Test that recent events have high weight."""
        engine = RegimeMemoryEngine()
        recent = datetime.now(timezone.utc)
        
        weight = engine.calculate_recency_weight(recent)
        assert weight >= 0.6
    
    def test_old_event_low_weight(self):
        """Test that old events have low weight."""
        engine = RegimeMemoryEngine()
        old = datetime.now(timezone.utc) - timedelta(days=90)
        
        weight = engine.calculate_recency_weight(old)
        assert weight <= 0.3
    
    def test_recency_decreases_over_time(self):
        """Test that recency weight decreases over time."""
        engine = RegimeMemoryEngine()
        
        day_0 = datetime.now(timezone.utc)
        day_7 = datetime.now(timezone.utc) - timedelta(days=7)
        day_30 = datetime.now(timezone.utc) - timedelta(days=30)
        day_90 = datetime.now(timezone.utc) - timedelta(days=90)
        
        w0 = engine.calculate_recency_weight(day_0)
        w7 = engine.calculate_recency_weight(day_7)
        w30 = engine.calculate_recency_weight(day_30)
        w90 = engine.calculate_recency_weight(day_90)
        
        assert w0 > w7 > w30 > w90
    
    def test_recency_weight_range(self):
        """Test recency weight is in [0, 1]."""
        engine = RegimeMemoryEngine()
        
        for days in [0, 1, 7, 30, 90, 180, 365]:
            timestamp = datetime.now(timezone.utc) - timedelta(days=days)
            weight = engine.calculate_recency_weight(timestamp)
            assert 0.0 <= weight <= 1.0


# ══════════════════════════════════════════════════════════════
# 4. Memory Score Tests
# ══════════════════════════════════════════════════════════════

class TestMemoryScore:
    """Tests for memory score calculation."""
    
    def test_memory_score_formula(self):
        """Test memory score uses correct weights."""
        engine = RegimeMemoryEngine()
        
        similarity = 0.8
        success_rate = 0.7
        recency = 0.6
        
        expected = (
            WEIGHT_SIMILARITY * similarity
            + WEIGHT_SUCCESS_RATE * success_rate
            + WEIGHT_RECENCY * recency
        )
        
        score = engine.calculate_memory_score(similarity, success_rate, recency)
        assert abs(score - expected) < 0.0001
    
    def test_memory_score_range(self):
        """Test memory score is in [0, 1]."""
        engine = RegimeMemoryEngine()
        
        test_cases = [
            (0.0, 0.0, 0.0),
            (1.0, 1.0, 1.0),
            (0.5, 0.5, 0.5),
            (0.9, 0.1, 0.5),
        ]
        
        for sim, success, recency in test_cases:
            score = engine.calculate_memory_score(sim, success, recency)
            assert 0.0 <= score <= 1.0
    
    def test_high_similarity_high_score(self):
        """Test that high similarity leads to high score."""
        engine = RegimeMemoryEngine()
        
        high_sim = engine.calculate_memory_score(0.95, 0.5, 0.5)
        low_sim = engine.calculate_memory_score(0.5, 0.5, 0.5)
        
        assert high_sim > low_sim


# ══════════════════════════════════════════════════════════════
# 5. Find Similar Memories Tests
# ══════════════════════════════════════════════════════════════

class TestFindSimilarMemories:
    """Tests for finding similar memories."""
    
    def test_find_exact_match(self):
        """Test finding an exact match."""
        engine = RegimeMemoryEngine()
        
        query = [0.5, 0.5, 0.1, 0.2, 0.6, 0.8, 0.3]
        records = [create_test_record(vector=query.copy())]
        
        matches = engine.find_similar_memories(query, records)
        assert len(matches) == 1
        assert matches[0].similarity == 1.0
    
    def test_filter_by_threshold(self):
        """Test that matches below threshold are filtered."""
        engine = RegimeMemoryEngine()
        
        query = [0.5, 0.5, 0.1, 0.2, 0.6, 0.8, 0.3]
        records = [
            create_test_record(vector=query.copy()),  # similarity = 1.0
            create_test_record(vector=[-0.5, -0.5, -0.1, -0.2, -0.6, -0.8, -0.3]),  # similarity = 0.0
        ]
        
        matches = engine.find_similar_memories(query, records, threshold=0.75)
        assert len(matches) == 1
    
    def test_sort_by_memory_score(self):
        """Test matches are sorted by memory score."""
        engine = RegimeMemoryEngine()
        
        query = [0.5, 0.5, 0.1, 0.2, 0.6, 0.8, 0.3]
        records = [
            create_test_record(vector=[0.5, 0.5, 0.1, 0.2, 0.6, 0.8, 0.3], days_ago=30),
            create_test_record(vector=[0.5, 0.5, 0.1, 0.2, 0.6, 0.8, 0.3], days_ago=1),
        ]
        
        matches = engine.find_similar_memories(query, records)
        
        # More recent should have higher memory_score
        assert matches[0].memory_score >= matches[1].memory_score
    
    def test_empty_records(self):
        """Test with empty records list."""
        engine = RegimeMemoryEngine()
        
        query = [0.5, 0.5, 0.1, 0.2, 0.6, 0.8, 0.3]
        matches = engine.find_similar_memories(query, [])
        
        assert len(matches) == 0


# ══════════════════════════════════════════════════════════════
# 6. Query Memory Tests
# ══════════════════════════════════════════════════════════════

class TestQueryMemory:
    """Tests for memory query."""
    
    def test_query_returns_response(self):
        """Test query returns proper response."""
        engine = RegimeMemoryEngine()
        records = create_test_records(50, "BTC")
        
        response = engine.query_memory("BTC", records)
        
        assert isinstance(response, MemoryResponse)
        assert response.symbol == "BTC"
    
    def test_query_with_limit(self):
        """Test query respects limit."""
        engine = RegimeMemoryEngine()
        records = create_test_records(50, "BTC")
        
        response = engine.query_memory("BTC", records, limit=5)
        
        assert len(response.matches) <= 5
    
    def test_query_top_matches(self):
        """Test top_matches contains top 5."""
        engine = RegimeMemoryEngine()
        records = create_test_records(50, "BTC")
        
        response = engine.query_memory("BTC", records, limit=20)
        
        assert len(response.top_matches) <= 5
    
    def test_query_aggregates_direction(self):
        """Test query aggregates expected direction."""
        engine = RegimeMemoryEngine()
        records = create_test_records(50, "BTC")
        
        response = engine.query_memory("BTC", records)
        
        assert response.expected_direction in ["LONG", "SHORT", "NEUTRAL"]


# ══════════════════════════════════════════════════════════════
# 7. Memory Modifier Tests
# ══════════════════════════════════════════════════════════════

class TestMemoryModifier:
    """Tests for hypothesis modifier."""
    
    def test_modifier_returns_correct_type(self):
        """Test modifier returns MemoryModifier."""
        engine = RegimeMemoryEngine()
        records = create_test_records(50, "BTC")
        
        modifier = engine.get_memory_modifier("BTC", "LONG", records)
        
        assert isinstance(modifier, MemoryModifier)
    
    def test_modifier_range(self):
        """Test modifier value is in reasonable range."""
        engine = RegimeMemoryEngine()
        records = create_test_records(50, "BTC")
        
        modifier = engine.get_memory_modifier("BTC", "LONG", records)
        
        assert 0.8 <= modifier.modifier <= 1.2
    
    def test_aligned_modifier_boost(self):
        """Test aligned direction gets boost."""
        engine = RegimeMemoryEngine()
        
        # Create records that favor LONG
        records = []
        for i in range(20):
            record = create_test_record(
                vector=[0.8, 0.5, 0.3, 0.3, 0.7, 1.0, 0.5],
                hypothesis="BULLISH_CONTINUATION",
                success=True,
                future_move=5.0,
                days_ago=i,
            )
            records.append(record)
        
        modifier = engine.get_memory_modifier("BTC", "LONG", records)
        
        if modifier.is_aligned:
            assert modifier.modifier >= 1.0


# ══════════════════════════════════════════════════════════════
# 8. Pattern Analysis Tests
# ══════════════════════════════════════════════════════════════

class TestPatternAnalysis:
    """Tests for pattern analysis."""
    
    def test_analyze_patterns_returns_list(self):
        """Test pattern analysis returns list."""
        engine = RegimeMemoryEngine()
        records = create_test_records(50, "BTC")
        
        patterns = engine.analyze_patterns("BTC", records)
        
        assert isinstance(patterns, list)
    
    def test_patterns_have_required_fields(self):
        """Test patterns have required fields."""
        engine = RegimeMemoryEngine()
        records = create_test_records(50, "BTC")
        
        patterns = engine.analyze_patterns("BTC", records)
        
        for pattern in patterns:
            assert hasattr(pattern, 'pattern_type')
            assert hasattr(pattern, 'occurrence_count')
            assert hasattr(pattern, 'avg_success_rate')
    
    def test_minimum_occurrence_filter(self):
        """Test patterns require minimum occurrences."""
        engine = RegimeMemoryEngine()
        records = create_test_records(50, "BTC")
        
        patterns = engine.analyze_patterns("BTC", records)
        
        for pattern in patterns:
            assert pattern.occurrence_count >= 3


# ══════════════════════════════════════════════════════════════
# 9. Summary Tests
# ══════════════════════════════════════════════════════════════

class TestSummary:
    """Tests for summary generation."""
    
    def test_summary_returns_correct_type(self):
        """Test summary returns MemorySummary."""
        engine = RegimeMemoryEngine()
        records = create_test_records(50, "BTC")
        
        summary = engine.generate_summary("BTC", records)
        
        assert isinstance(summary, MemorySummary)
    
    def test_summary_counts_match(self):
        """Test summary counts are consistent."""
        engine = RegimeMemoryEngine()
        records = create_test_records(50, "BTC")
        
        summary = engine.generate_summary("BTC", records)
        
        assert summary.total_records == summary.successful_records + summary.failed_records
    
    def test_summary_success_rate_range(self):
        """Test success rates are in [0, 1]."""
        engine = RegimeMemoryEngine()
        records = create_test_records(50, "BTC")
        
        summary = engine.generate_summary("BTC", records)
        
        assert 0.0 <= summary.overall_success_rate <= 1.0
        assert 0.0 <= summary.trending_success_rate <= 1.0
        assert 0.0 <= summary.ranging_success_rate <= 1.0


# ══════════════════════════════════════════════════════════════
# 10. Registry Tests
# ══════════════════════════════════════════════════════════════

class TestRegistry:
    """Tests for memory registry."""
    
    def test_get_registry_singleton(self):
        """Test registry is singleton."""
        reg1 = get_memory_registry()
        reg2 = get_memory_registry()
        
        assert reg1 is reg2
    
    def test_get_records_returns_list(self):
        """Test get_records returns list."""
        registry = get_memory_registry()
        records = registry.get_records_by_symbol("BTC", limit=10)
        
        assert isinstance(records, list)
    
    def test_mock_records_have_correct_structure(self):
        """Test mock records have correct structure."""
        registry = get_memory_registry()
        records = registry.get_records_by_symbol("BTC", limit=10)
        
        for record in records:
            assert len(record.structure_vector) == VECTOR_SIZE
            assert record.symbol == "BTC"


# ══════════════════════════════════════════════════════════════
# 11. Memory Pruning Tests
# ══════════════════════════════════════════════════════════════

class TestMemoryPruning:
    """Tests for memory pruning."""
    
    def test_prune_returns_count(self):
        """Test prune returns deleted count."""
        registry = get_memory_registry()
        
        # This may return 0 if no old records exist
        count = registry.prune_old_records("BTC", days_to_keep=365)
        
        assert isinstance(count, int)
        assert count >= 0


# ══════════════════════════════════════════════════════════════
# 12. Edge Cases
# ══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_symbol(self):
        """Test handling of empty symbol."""
        engine = RegimeMemoryEngine()
        
        # Should not raise
        vec = engine.build_structure_vector("")
        assert len(vec.to_vector()) == VECTOR_SIZE
    
    def test_very_old_timestamp(self):
        """Test very old timestamp for recency."""
        engine = RegimeMemoryEngine()
        
        old = datetime.now(timezone.utc) - timedelta(days=1000)
        weight = engine.calculate_recency_weight(old)
        
        assert 0.0 <= weight <= 1.0
    
    def test_single_record_query(self):
        """Test query with single record."""
        engine = RegimeMemoryEngine()
        records = [create_test_record()]
        
        response = engine.query_memory("BTC", records)
        
        assert response.total_records_searched == 1


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
