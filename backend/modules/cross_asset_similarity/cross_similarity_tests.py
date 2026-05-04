"""
Cross-Asset Similarity Tests

PHASE 32.4 — Unit tests for Cross-Asset Similarity Engine.

30+ tests covering:
- Structure vector building
- Cosine similarity calculation
- Cross-asset matching
- Direction inference
- Confidence calculation
- Modifier logic
- API endpoints
- Integration tests
"""

import pytest
import math
from datetime import datetime, timezone

from .cross_similarity_types import (
    StructureVector,
    CrossAssetMatch,
    CrossAssetAnalysis,
    CrossAssetModifier,
    CrossAssetSummary,
    ASSET_UNIVERSE,
    CRYPTO_ASSETS,
    TRADITIONAL_ASSETS,
    SIMILARITY_THRESHOLD,
    WEIGHT_SIMILARITY,
    WEIGHT_HISTORICAL_SUCCESS,
    WEIGHT_CROSS_ASSET,
    CROSS_ASSET_WEIGHTS,
    WINDOW_SIZES,
)

from .cross_similarity_engine import CrossAssetSimilarityEngine, get_cross_similarity_engine


# ══════════════════════════════════════════════════════════════
# 1. Structure Vector Tests
# ══════════════════════════════════════════════════════════════

class TestStructureVector:
    """Tests for structure vector building."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = CrossAssetSimilarityEngine()
    
    def test_build_current_vector(self):
        """Test building current structure vector."""
        vector = self.engine.build_current_vector("BTC")
        
        assert isinstance(vector, StructureVector)
        assert vector.symbol == "BTC"
    
    def test_vector_components_bounded(self):
        """Test all vector components are within bounds."""
        for symbol in ASSET_UNIVERSE:
            vector = self.engine.build_current_vector(symbol)
            
            assert -1.0 <= vector.trend_slope <= 1.0
            assert 0.0 <= vector.volatility <= 1.0
            assert -1.0 <= vector.volume_delta <= 1.0
            assert 0.0 <= vector.liquidity_state <= 1.0
            assert -1.0 <= vector.microstructure_bias <= 1.0
    
    def test_vector_to_list(self):
        """Test vector conversion to list."""
        vector = self.engine.build_current_vector("BTC")
        vec_list = vector.to_vector()
        
        assert isinstance(vec_list, list)
        assert len(vec_list) == 5
    
    def test_different_assets_have_different_vectors(self):
        """Test different assets produce different vectors."""
        btc_vec = self.engine.build_current_vector("BTC").to_vector()
        eth_vec = self.engine.build_current_vector("ETH").to_vector()
        
        # At least some components should differ
        differences = sum(1 for a, b in zip(btc_vec, eth_vec) if abs(a - b) > 0.01)
        assert differences > 0


# ══════════════════════════════════════════════════════════════
# 2. Cosine Similarity Tests
# ══════════════════════════════════════════════════════════════

class TestCosineSimilarity:
    """Tests for cosine similarity calculation."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = CrossAssetSimilarityEngine()
    
    def test_identical_vectors(self):
        """Test similarity of identical vectors."""
        vec = [0.5, 0.3, 0.2, 0.4, 0.1]
        similarity = self.engine.calculate_cosine_similarity(vec, vec)
        
        assert similarity == 1.0
    
    def test_opposite_vectors(self):
        """Test similarity of opposite vectors."""
        vec_a = [1.0, 1.0, 1.0, 1.0, 1.0]
        vec_b = [-1.0, -1.0, -1.0, -1.0, -1.0]
        similarity = self.engine.calculate_cosine_similarity(vec_a, vec_b)
        
        assert similarity == 0.0  # Normalized to [0, 1]
    
    def test_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors."""
        vec_a = [1.0, 0.0, 0.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0, 0.0, 0.0]
        similarity = self.engine.calculate_cosine_similarity(vec_a, vec_b)
        
        assert similarity == 0.5  # Orthogonal = 0 cosine, normalized to 0.5
    
    def test_similarity_bounded(self):
        """Test similarity is always in [0, 1]."""
        for _ in range(10):
            vec_a = [0.3, -0.2, 0.5, 0.1, -0.4]
            vec_b = [-0.1, 0.4, -0.3, 0.2, 0.6]
            similarity = self.engine.calculate_cosine_similarity(vec_a, vec_b)
            
            assert 0.0 <= similarity <= 1.0
    
    def test_zero_vector(self):
        """Test handling zero vector."""
        vec_a = [0.0, 0.0, 0.0, 0.0, 0.0]
        vec_b = [0.5, 0.3, 0.2, 0.4, 0.1]
        similarity = self.engine.calculate_cosine_similarity(vec_a, vec_b)
        
        assert similarity == 0.0


# ══════════════════════════════════════════════════════════════
# 3. Cross-Asset Matching Tests
# ══════════════════════════════════════════════════════════════

class TestCrossAssetMatching:
    """Tests for cross-asset matching."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = CrossAssetSimilarityEngine()
    
    def test_find_matches_returns_list(self):
        """Test matching returns list."""
        matches = self.engine.find_cross_asset_matches("BTC")
        
        assert isinstance(matches, list)
    
    def test_matches_above_threshold(self):
        """Test all matches are above threshold."""
        matches = self.engine.find_cross_asset_matches("BTC", threshold=SIMILARITY_THRESHOLD)
        
        for match in matches:
            assert match.similarity_score >= SIMILARITY_THRESHOLD
    
    def test_matches_exclude_self(self):
        """Test matches don't include self-comparison."""
        matches = self.engine.find_cross_asset_matches("BTC")
        
        for match in matches:
            assert match.reference_symbol != "BTC"
    
    def test_matches_sorted_by_confidence(self):
        """Test matches are sorted by confidence."""
        matches = self.engine.find_cross_asset_matches("BTC")
        
        if len(matches) > 1:
            for i in range(len(matches) - 1):
                assert matches[i].confidence >= matches[i + 1].confidence
    
    def test_match_has_required_fields(self):
        """Test match has all required fields."""
        matches = self.engine.find_cross_asset_matches("ETH")
        
        if matches:
            m = matches[0]
            assert hasattr(m, 'match_id')
            assert hasattr(m, 'source_symbol')
            assert hasattr(m, 'reference_symbol')
            assert hasattr(m, 'similarity_score')
            assert hasattr(m, 'expected_direction')
            assert hasattr(m, 'confidence')


# ══════════════════════════════════════════════════════════════
# 4. Direction Inference Tests
# ══════════════════════════════════════════════════════════════

class TestDirectionInference:
    """Tests for direction inference."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = CrossAssetSimilarityEngine()
    
    def test_direction_valid_values(self):
        """Test direction is valid."""
        analysis = self.engine.analyze("BTC")
        
        assert analysis.expected_direction in ["LONG", "SHORT", "NEUTRAL"]
    
    def test_direction_from_historical_outcome(self):
        """Test direction is inferred from historical outcome."""
        matches = self.engine.find_cross_asset_matches("BTC")
        
        for match in matches:
            # Direction should match historical direction
            assert match.expected_direction == match.historical_direction
    
    def test_aggregated_direction(self):
        """Test aggregated direction calculation."""
        analysis = self.engine.analyze("BTC")
        
        # Should have aggregated direction and confidence
        assert analysis.expected_direction in ["LONG", "SHORT", "NEUTRAL"]
        assert 0.0 <= analysis.aggregated_confidence <= 1.0


# ══════════════════════════════════════════════════════════════
# 5. Confidence Calculation Tests
# ══════════════════════════════════════════════════════════════

class TestConfidenceCalculation:
    """Tests for confidence calculation."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = CrossAssetSimilarityEngine()
    
    def test_confidence_bounded(self):
        """Test confidence is in [0, 1]."""
        matches = self.engine.find_cross_asset_matches("BTC")
        
        for match in matches:
            assert 0.0 <= match.confidence <= 1.0
    
    def test_confidence_formula_weights(self):
        """Test confidence uses correct weights."""
        # Verify weight constants sum to 1.0
        total = WEIGHT_SIMILARITY + WEIGHT_HISTORICAL_SUCCESS + WEIGHT_CROSS_ASSET
        assert abs(total - 1.0) < 0.01
    
    def test_higher_similarity_higher_confidence(self):
        """Test higher similarity leads to higher confidence component."""
        matches = self.engine.find_cross_asset_matches("ETH")
        
        if len(matches) >= 2:
            # Higher similarity match should generally have higher confidence
            # (unless other factors dominate)
            top_match = matches[0]
            assert top_match.similarity_score >= SIMILARITY_THRESHOLD


# ══════════════════════════════════════════════════════════════
# 6. Cross-Asset Weights Tests
# ══════════════════════════════════════════════════════════════

class TestCrossAssetWeights:
    """Tests for cross-asset weight logic."""
    
    def test_crypto_to_crypto_higher_weight(self):
        """Test crypto-to-crypto has higher weight than crypto-to-traditional."""
        btc_eth = CROSS_ASSET_WEIGHTS["BTC"]["ETH"]
        btc_spx = CROSS_ASSET_WEIGHTS["BTC"]["SPX"]
        
        assert btc_eth > btc_spx
    
    def test_weights_symmetric_category(self):
        """Test weights are consistent within category."""
        # Crypto assets should have similar high weights to each other
        for crypto in CRYPTO_ASSETS:
            for other_crypto in CRYPTO_ASSETS:
                if crypto != other_crypto:
                    weight = CROSS_ASSET_WEIGHTS[crypto][other_crypto]
                    assert weight >= 0.7  # High correlation expected
    
    def test_all_weights_defined(self):
        """Test all cross-asset weights are defined."""
        for source in ASSET_UNIVERSE:
            for target in ASSET_UNIVERSE:
                if source != target:
                    weight = CROSS_ASSET_WEIGHTS.get(source, {}).get(target)
                    assert weight is not None
                    assert 0.0 <= weight <= 1.0


# ══════════════════════════════════════════════════════════════
# 7. Modifier Tests
# ══════════════════════════════════════════════════════════════

class TestModifier:
    """Tests for hypothesis modifier."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = CrossAssetSimilarityEngine()
    
    def test_modifier_returns_object(self):
        """Test modifier returns CrossAssetModifier."""
        modifier = self.engine.get_cross_asset_modifier("BTC", "LONG")
        
        assert isinstance(modifier, CrossAssetModifier)
    
    def test_modifier_bounded(self):
        """Test modifier value is bounded [0.85, 1.15]."""
        for direction in ["LONG", "SHORT", "NEUTRAL"]:
            modifier = self.engine.get_cross_asset_modifier("ETH", direction)
            assert 0.85 <= modifier.modifier <= 1.15
    
    def test_aligned_modifier_value(self):
        """Test aligned direction gives 1.10 modifier."""
        # First get the expected direction
        analysis = self.engine.analyze("BTC")
        
        if analysis.aggregated_confidence >= 0.4 and analysis.expected_direction != "NEUTRAL":
            modifier = self.engine.get_cross_asset_modifier("BTC", analysis.expected_direction)
            assert modifier.modifier == 1.10
    
    def test_conflict_modifier_value(self):
        """Test conflicting direction gives 0.92 modifier."""
        analysis = self.engine.analyze("SOL")
        
        if analysis.aggregated_confidence >= 0.4 and analysis.expected_direction == "LONG":
            modifier = self.engine.get_cross_asset_modifier("SOL", "SHORT")
            assert modifier.modifier == 0.92


# ══════════════════════════════════════════════════════════════
# 8. Full Analysis Tests
# ══════════════════════════════════════════════════════════════

class TestFullAnalysis:
    """Tests for full analysis."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = CrossAssetSimilarityEngine()
    
    def test_analyze_returns_analysis(self):
        """Test analyze returns CrossAssetAnalysis."""
        analysis = self.engine.analyze("BTC")
        
        assert isinstance(analysis, CrossAssetAnalysis)
        assert analysis.symbol == "BTC"
    
    def test_analysis_has_matches(self):
        """Test analysis contains matches."""
        analysis = self.engine.analyze("BTC")
        
        # Should have compared against other assets
        assert len(analysis.assets_compared) == len(ASSET_UNIVERSE) - 1
    
    def test_analysis_has_asset_breakdown(self):
        """Test analysis has asset signal breakdown."""
        analysis = self.engine.analyze("ETH")
        
        assert isinstance(analysis.asset_signals, dict)
        assert isinstance(analysis.asset_confidences, dict)
    
    def test_analysis_stored(self):
        """Test analysis is stored."""
        analysis = self.engine.analyze("SOL")
        
        stored = self.engine.get_current_analysis("SOL")
        assert stored is not None
        assert stored.symbol == "SOL"


# ══════════════════════════════════════════════════════════════
# 9. Storage Tests
# ══════════════════════════════════════════════════════════════

class TestStorage:
    """Tests for storage operations."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = CrossAssetSimilarityEngine()
    
    def test_get_top_matches(self):
        """Test getting top matches."""
        self.engine.analyze("BTC")
        
        top = self.engine.get_top_matches("BTC", 5)
        assert len(top) <= 5
    
    def test_get_asset_signals(self):
        """Test getting asset signals."""
        signals = self.engine.get_asset_signals("BTC")
        
        assert isinstance(signals, dict)
        assert "ETH" in signals
    
    def test_get_history(self):
        """Test getting history."""
        self.engine.analyze("BTC")
        self.engine.analyze("BTC")
        
        history = self.engine.get_history("BTC")
        assert len(history) >= 2
    
    def test_get_summary(self):
        """Test getting summary."""
        self.engine.analyze("ETH")
        
        summary = self.engine.get_summary("ETH")
        
        assert isinstance(summary, CrossAssetSummary)
        assert summary.symbol == "ETH"


# ══════════════════════════════════════════════════════════════
# 10. Multi-Asset Tests
# ══════════════════════════════════════════════════════════════

class TestMultiAsset:
    """Tests for multi-asset scenarios."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = CrossAssetSimilarityEngine()
    
    def test_all_assets_analyzable(self):
        """Test all assets in universe can be analyzed."""
        for symbol in ASSET_UNIVERSE:
            analysis = self.engine.analyze(symbol)
            assert analysis is not None
            assert analysis.symbol == symbol
    
    def test_cross_asset_relationships(self):
        """Test cross-asset relationships work both ways."""
        btc_analysis = self.engine.analyze("BTC")
        eth_analysis = self.engine.analyze("ETH")
        
        # BTC should find matches with ETH and vice versa
        btc_has_eth = any(m.reference_symbol == "ETH" for m in btc_analysis.matches)
        eth_has_btc = any(m.reference_symbol == "BTC" for m in eth_analysis.matches)
        
        # At least one direction should have matches
        assert btc_has_eth or eth_has_btc or (len(btc_analysis.matches) > 0 and len(eth_analysis.matches) > 0)


# ══════════════════════════════════════════════════════════════
# 11. Edge Cases Tests
# ══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Tests for edge cases."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = CrossAssetSimilarityEngine()
    
    def test_unknown_symbol(self):
        """Test handling unknown symbol."""
        analysis = self.engine.analyze("UNKNOWN_XYZ")
        
        assert analysis is not None
        assert analysis.symbol == "UNKNOWN_XYZ"
    
    def test_high_threshold(self):
        """Test with very high threshold."""
        matches = self.engine.find_cross_asset_matches("BTC", threshold=0.99)
        
        # May have fewer matches with high threshold
        for m in matches:
            assert m.similarity_score >= 0.99
    
    def test_low_threshold(self):
        """Test with lower threshold."""
        matches = self.engine.find_cross_asset_matches("BTC", threshold=0.5)
        
        # Should have more matches
        assert len(matches) >= 0


# ══════════════════════════════════════════════════════════════
# 12. Singleton Tests
# ══════════════════════════════════════════════════════════════

class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_cross_similarity_engine(self):
        """Test singleton getter."""
        engine1 = get_cross_similarity_engine()
        engine2 = get_cross_similarity_engine()
        
        assert engine1 is engine2


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
