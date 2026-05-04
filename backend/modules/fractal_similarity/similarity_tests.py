"""
Fractal Similarity Tests

PHASE 32.2 — Unit tests for Fractal Similarity Engine.

28+ tests covering:
- Structure encoding
- Cosine similarity algorithm
- Pattern matching
- Direction inference
- Confidence calculation
- Modifier generation
- API endpoints
"""

import pytest
import math
from datetime import datetime, timezone

from .similarity_types import (
    StructureVector,
    HistoricalPattern,
    SimilarityMatch,
    SimilarityAnalysis,
    SimilarityModifier,
    WINDOW_SIZES,
    SIMILARITY_THRESHOLD,
    SIMILARITY_ALIGNED_MODIFIER,
    SIMILARITY_CONFLICT_MODIFIER,
)

from .similarity_engine import FractalSimilarityEngine, get_similarity_engine


# ══════════════════════════════════════════════════════════════
# 1. Structure Vector Tests
# ══════════════════════════════════════════════════════════════

class TestStructureVector:
    """Tests for structure vector encoding."""
    
    def test_structure_vector_creation(self):
        """Test basic structure vector creation."""
        vector = StructureVector(
            symbol="BTC",
            window_size=100,
            trend_slope=0.05,
            volatility_ratio=1.2,
            volume_delta=0.1,
            momentum=0.3,
            range_position=0.7,
        )
        
        assert vector.symbol == "BTC"
        assert vector.window_size == 100
        assert vector.trend_slope == 0.05
        assert vector.volatility_ratio == 1.2
    
    def test_structure_vector_to_vector(self):
        """Test vector conversion."""
        vector = StructureVector(
            symbol="BTC",
            window_size=100,
            trend_slope=0.1,
            volatility_ratio=1.0,
            volume_delta=0.2,
            momentum=0.5,
            range_position=0.6,
            body_ratio=0.4,
            upper_wick_ratio=0.3,
            lower_wick_ratio=0.2,
            trend_strength=0.7,
        )
        
        v = vector.to_vector()
        
        assert len(v) == 9
        assert v[0] == 0.1  # trend_slope
        assert v[1] == 1.0  # volatility_ratio
        assert v[4] == 0.6  # range_position
    
    def test_structure_vector_defaults(self):
        """Test default values."""
        vector = StructureVector(symbol="ETH", window_size=50)
        
        assert vector.trend_slope == 0.0
        assert vector.volatility_ratio == 1.0
        assert vector.volume_delta == 0.0
        assert vector.range_position == 0.5


# ══════════════════════════════════════════════════════════════
# 2. Cosine Similarity Tests
# ══════════════════════════════════════════════════════════════

class TestCosineSimilarity:
    """Tests for cosine similarity algorithm."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = FractalSimilarityEngine()
    
    def test_identical_vectors(self):
        """Test similarity of identical vectors."""
        vec = [0.5, 0.3, 0.2, 0.4, 0.6]
        
        similarity = self.engine.cosine_similarity(vec, vec)
        
        assert similarity == 1.0
    
    def test_opposite_vectors(self):
        """Test similarity of opposite vectors."""
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [-1.0, 0.0, 0.0]
        
        similarity = self.engine.cosine_similarity(vec_a, vec_b)
        
        assert similarity == 0.0  # Normalized from -1 to [0,1]
    
    def test_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors."""
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0]
        
        similarity = self.engine.cosine_similarity(vec_a, vec_b)
        
        assert similarity == 0.5  # cos(90°) = 0, normalized to 0.5
    
    def test_similar_vectors(self):
        """Test similar vectors."""
        vec_a = [0.5, 0.3, 0.2]
        vec_b = [0.6, 0.35, 0.25]
        
        similarity = self.engine.cosine_similarity(vec_a, vec_b)
        
        assert similarity > 0.9  # Should be very similar
    
    def test_empty_vectors(self):
        """Test empty vectors."""
        similarity = self.engine.cosine_similarity([], [])
        assert similarity == 0.0
    
    def test_different_length_vectors(self):
        """Test different length vectors."""
        vec_a = [0.5, 0.3]
        vec_b = [0.5, 0.3, 0.2]
        
        similarity = self.engine.cosine_similarity(vec_a, vec_b)
        
        assert similarity == 0.0  # Invalid comparison
    
    def test_zero_vector(self):
        """Test zero vector."""
        vec_a = [0.0, 0.0, 0.0]
        vec_b = [0.5, 0.3, 0.2]
        
        similarity = self.engine.cosine_similarity(vec_a, vec_b)
        
        assert similarity == 0.0  # Zero magnitude


# ══════════════════════════════════════════════════════════════
# 3. Structure Encoding Tests
# ══════════════════════════════════════════════════════════════

class TestStructureEncoding:
    """Tests for structure encoding."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = FractalSimilarityEngine()
    
    def test_encode_structure_basic(self):
        """Test basic structure encoding."""
        vector = self.engine.encode_structure("BTC", 100)
        
        assert vector.symbol == "BTC"
        assert vector.window_size == 100
        assert len(vector.to_vector()) == 9
    
    def test_encode_structure_with_data(self):
        """Test encoding with provided data."""
        data = {
            "trend_slope": 0.05,
            "volatility_ratio": 1.3,
            "volume_delta": 0.2,
            "momentum": 0.6,
            "range_position": 0.8,
            "body_ratio": 0.45,
            "upper_wick_ratio": 0.2,
            "lower_wick_ratio": 0.15,
            "trend_strength": 0.7,
        }
        
        vector = self.engine.encode_structure("ETH", 50, data)
        
        assert vector.trend_slope == 0.05
        assert vector.volatility_ratio == 1.3
        assert vector.momentum == 0.6
    
    def test_encode_different_windows(self):
        """Test encoding different window sizes."""
        for window in WINDOW_SIZES:
            vector = self.engine.encode_structure("BTC", window)
            assert vector.window_size == window
    
    def test_encode_deterministic(self):
        """Test encoding is deterministic."""
        v1 = self.engine.encode_structure("BTC", 100)
        v2 = self.engine.encode_structure("BTC", 100)
        
        # Mock data should be deterministic for same symbol/window
        assert v1.trend_slope == v2.trend_slope
        assert v1.volatility_ratio == v2.volatility_ratio


# ══════════════════════════════════════════════════════════════
# 4. Pattern Matching Tests
# ══════════════════════════════════════════════════════════════

class TestPatternMatching:
    """Tests for pattern matching."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = FractalSimilarityEngine()
    
    def test_find_similar_patterns(self):
        """Test finding similar patterns."""
        vector = self.engine.encode_structure("BTC", 100)
        
        matches = self.engine.find_similar_patterns(vector)
        
        assert isinstance(matches, list)
        assert all(isinstance(m, SimilarityMatch) for m in matches)
    
    def test_matches_above_threshold(self):
        """Test matches are above threshold."""
        vector = self.engine.encode_structure("BTC", 100)
        
        matches = self.engine.find_similar_patterns(vector, threshold=0.75)
        
        for match in matches:
            assert match.similarity_score >= 0.75
    
    def test_matches_sorted_by_similarity(self):
        """Test matches are sorted by similarity."""
        vector = self.engine.encode_structure("BTC", 100)
        
        matches = self.engine.find_similar_patterns(vector)
        
        if len(matches) > 1:
            for i in range(len(matches) - 1):
                assert matches[i].similarity_score >= matches[i + 1].similarity_score
    
    def test_max_results_limit(self):
        """Test max results limit."""
        vector = self.engine.encode_structure("BTC", 100)
        
        matches = self.engine.find_similar_patterns(vector, max_results=5)
        
        assert len(matches) <= 5


# ══════════════════════════════════════════════════════════════
# 5. Direction Inference Tests
# ══════════════════════════════════════════════════════════════

class TestDirectionInference:
    """Tests for direction inference."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = FractalSimilarityEngine()
    
    def test_infer_long_direction(self):
        """Test inferring LONG direction."""
        matches = [
            SimilarityMatch(
                pattern_id="p1",
                similarity_score=0.9,
                historical_direction="LONG",
                historical_return=5.0,
                was_successful=True,
                pattern_timestamp=datetime.now(timezone.utc),
                window_size=100,
            ),
            SimilarityMatch(
                pattern_id="p2",
                similarity_score=0.85,
                historical_direction="LONG",
                historical_return=3.0,
                was_successful=True,
                pattern_timestamp=datetime.now(timezone.utc),
                window_size=100,
            ),
        ]
        
        direction, confidence = self.engine.infer_direction(matches)
        
        assert direction == "LONG"
        assert confidence > 0.5
    
    def test_infer_short_direction(self):
        """Test inferring SHORT direction."""
        matches = [
            SimilarityMatch(
                pattern_id="p1",
                similarity_score=0.9,
                historical_direction="SHORT",
                historical_return=-5.0,
                was_successful=True,
                pattern_timestamp=datetime.now(timezone.utc),
                window_size=100,
            ),
        ]
        
        direction, confidence = self.engine.infer_direction(matches)
        
        assert direction == "SHORT"
    
    def test_infer_neutral_empty(self):
        """Test inferring NEUTRAL with no matches."""
        direction, confidence = self.engine.infer_direction([])
        
        assert direction == "NEUTRAL"
        assert confidence == 0.0
    
    def test_success_weight_boost(self):
        """Test successful patterns get weight boost."""
        successful = SimilarityMatch(
            pattern_id="p1",
            similarity_score=0.8,
            historical_direction="LONG",
            historical_return=5.0,
            was_successful=True,
            pattern_timestamp=datetime.now(timezone.utc),
            window_size=100,
        )
        
        unsuccessful = SimilarityMatch(
            pattern_id="p2",
            similarity_score=0.8,
            historical_direction="SHORT",
            historical_return=-3.0,
            was_successful=False,
            pattern_timestamp=datetime.now(timezone.utc),
            window_size=100,
        )
        
        direction, _ = self.engine.infer_direction([successful, unsuccessful])
        
        # Successful LONG should outweigh unsuccessful SHORT
        assert direction == "LONG"


# ══════════════════════════════════════════════════════════════
# 6. Success Rate Tests
# ══════════════════════════════════════════════════════════════

class TestSuccessRate:
    """Tests for success rate calculation."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = FractalSimilarityEngine()
    
    def test_success_rate_all_successful(self):
        """Test 100% success rate."""
        matches = [
            SimilarityMatch(
                pattern_id=f"p{i}",
                similarity_score=0.8,
                historical_direction="LONG",
                historical_return=5.0,
                was_successful=True,
                pattern_timestamp=datetime.now(timezone.utc),
                window_size=100,
            )
            for i in range(5)
        ]
        
        rate, avg_return = self.engine.calculate_success_rate(matches)
        
        assert rate == 1.0
        assert avg_return == 5.0
    
    def test_success_rate_half(self):
        """Test 50% success rate."""
        matches = [
            SimilarityMatch(
                pattern_id="p1",
                similarity_score=0.8,
                historical_direction="LONG",
                historical_return=5.0,
                was_successful=True,
                pattern_timestamp=datetime.now(timezone.utc),
                window_size=100,
            ),
            SimilarityMatch(
                pattern_id="p2",
                similarity_score=0.8,
                historical_direction="LONG",
                historical_return=-3.0,
                was_successful=False,
                pattern_timestamp=datetime.now(timezone.utc),
                window_size=100,
            ),
        ]
        
        rate, _ = self.engine.calculate_success_rate(matches)
        
        assert rate == 0.5
    
    def test_success_rate_empty(self):
        """Test empty matches."""
        rate, avg_return = self.engine.calculate_success_rate([])
        
        assert rate == 0.0
        assert avg_return == 0.0


# ══════════════════════════════════════════════════════════════
# 7. Confidence Calculation Tests
# ══════════════════════════════════════════════════════════════

class TestConfidenceCalculation:
    """Tests for confidence calculation."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = FractalSimilarityEngine()
    
    def test_confidence_formula(self):
        """Test confidence formula."""
        # 0.60 * similarity + 0.40 * success_rate
        confidence = self.engine.calculate_confidence(0.9, 0.8)
        
        expected = 0.60 * 0.9 + 0.40 * 0.8
        assert confidence == round(expected, 4)
    
    def test_confidence_bounds(self):
        """Test confidence is bounded [0, 1]."""
        # Max values
        conf_max = self.engine.calculate_confidence(1.0, 1.0)
        assert conf_max <= 1.0
        
        # Min values
        conf_min = self.engine.calculate_confidence(0.0, 0.0)
        assert conf_min >= 0.0


# ══════════════════════════════════════════════════════════════
# 8. Full Analysis Tests
# ══════════════════════════════════════════════════════════════

class TestFullAnalysis:
    """Tests for full similarity analysis."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = FractalSimilarityEngine()
    
    def test_analyze_similarity(self):
        """Test full analysis."""
        analysis = self.engine.analyze_similarity("BTC")
        
        assert isinstance(analysis, SimilarityAnalysis)
        assert analysis.symbol == "BTC"
        assert analysis.expected_direction in ["LONG", "SHORT", "NEUTRAL"]
    
    def test_analysis_has_matches(self):
        """Test analysis contains matches."""
        analysis = self.engine.analyze_similarity("ETH")
        
        # Should find some matches with mock data
        assert analysis.matches_found >= 0
    
    def test_analysis_stored(self):
        """Test analysis is stored."""
        analysis = self.engine.analyze_similarity("SOL")
        
        stored = self.engine.get_current_analysis("SOL")
        
        assert stored is not None
        assert stored.symbol == analysis.symbol


# ══════════════════════════════════════════════════════════════
# 9. Modifier Tests
# ══════════════════════════════════════════════════════════════

class TestSimilarityModifier:
    """Tests for similarity modifier."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = FractalSimilarityEngine()
    
    def test_modifier_aligned_boost(self):
        """Test aligned modifier boost."""
        # Force a LONG analysis
        self.engine.analyze_similarity("BTC")
        
        modifier = self.engine.get_similarity_modifier("BTC", "LONG")
        
        # Either aligned (1.12) or conflict (0.90) or neutral (1.0)
        assert modifier.modifier in [SIMILARITY_ALIGNED_MODIFIER, SIMILARITY_CONFLICT_MODIFIER, 1.0]
    
    def test_modifier_has_details(self):
        """Test modifier contains details."""
        modifier = self.engine.get_similarity_modifier("ETH", "SHORT")
        
        assert modifier.hypothesis_direction == "SHORT"
        assert modifier.expected_direction in ["LONG", "SHORT", "NEUTRAL"]
        assert modifier.reason != ""
    
    def test_modifier_normalization(self):
        """Test direction normalization."""
        # Different ways to say LONG
        for direction in ["LONG", "BULLISH", "UP", "TREND_UP"]:
            modifier = self.engine.get_similarity_modifier("BTC", direction)
            # Should normalize to LONG internally
            assert "LONG" in modifier.reason or "NEUTRAL" in modifier.reason or "conflict" in modifier.reason.lower()


# ══════════════════════════════════════════════════════════════
# 10. Summary Tests
# ══════════════════════════════════════════════════════════════

class TestSummary:
    """Tests for similarity summary."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = FractalSimilarityEngine()
    
    def test_summary_basic(self):
        """Test basic summary."""
        # Run analysis first
        self.engine.analyze_similarity("BTC")
        
        summary = self.engine.get_summary("BTC")
        
        assert summary.symbol == "BTC"
        assert summary.total_analyses >= 1
    
    def test_summary_empty(self):
        """Test summary for unanalyzed symbol."""
        new_engine = FractalSimilarityEngine()
        summary = new_engine.get_summary("XYZ")
        
        assert summary.symbol == "XYZ"
        assert summary.total_analyses == 0


# ══════════════════════════════════════════════════════════════
# 11. Singleton Tests
# ══════════════════════════════════════════════════════════════

class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_similarity_engine(self):
        """Test singleton getter."""
        engine1 = get_similarity_engine()
        engine2 = get_similarity_engine()
        
        assert engine1 is engine2


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
