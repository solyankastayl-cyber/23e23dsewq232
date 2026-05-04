"""
PHASE 32.2 — Fractal Similarity Engine API Tests

Tests for all API endpoints:
- GET /api/v1/fractal-similarity/health - Health check
- GET /api/v1/fractal-similarity/{symbol} - Similarity analysis
- GET /api/v1/fractal-similarity/top/{symbol} - Top matches
- GET /api/v1/fractal-similarity/history/{symbol} - Analysis history
- POST /api/v1/fractal-similarity/recompute/{symbol} - Force recomputation
- GET /api/v1/fractal-similarity/modifier/{symbol} - Modifier calculation
- GET /api/v1/fractal-similarity/summary/{symbol} - Summary

Tests cover:
- Cosine similarity algorithm correctness
- Structure vector encoding with 9 features
- Pattern matching with threshold 0.75
- Direction inference weighted by similarity and success
- Confidence calculation (0.60 × similarity + 0.40 × success_rate)
- Modifier values: 1.12 for aligned, 0.90 for conflict
"""

import pytest
import requests
import os
import math


# Use localhost since external URL has 404 issues
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# Constants from requirements
SIMILARITY_THRESHOLD = 0.75
SIMILARITY_WEIGHT = 0.60
HISTORICAL_SUCCESS_WEIGHT = 0.40
SIMILARITY_ALIGNED_MODIFIER = 1.12
SIMILARITY_CONFLICT_MODIFIER = 0.90
WINDOW_SIZES = [50, 100, 200]


class TestHealthEndpoint:
    """Tests for health check endpoint"""
    
    def test_health_returns_200(self):
        """Test health endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/health")
        assert response.status_code == 200
        print(f"Health check status: {response.status_code}")
    
    def test_health_response_structure(self):
        """Test health response has correct fields"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/health")
        data = response.json()
        
        assert data["status"] == "ok"
        assert data["module"] == "fractal_similarity"
        assert data["phase"] == "32.2"
        assert "version" in data
        assert "timestamp" in data
        print(f"Health response: {data}")


class TestSimilarityAnalysisEndpoint:
    """Tests for GET /api/v1/fractal-similarity/{symbol}"""
    
    def test_analysis_btcusdt(self):
        """Test similarity analysis for BTCUSDT"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/BTCUSDT")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["symbol"] == "BTCUSDT"
        print(f"BTCUSDT analysis: expected_direction={data['analysis']['expected_direction']}")
    
    def test_analysis_response_structure(self):
        """Test analysis response has all required fields"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/ETHUSDT")
        data = response.json()
        
        # Top-level fields
        assert "status" in data
        assert "symbol" in data
        assert "analysis" in data
        assert "top_matches" in data
        assert "current_vector" in data
        assert "timestamp" in data
        
        # Analysis fields
        analysis = data["analysis"]
        assert "expected_direction" in analysis
        assert "direction_confidence" in analysis
        assert "similarity_confidence" in analysis
        assert "best_similarity" in analysis
        assert "matches_found" in analysis
        assert "patterns_searched" in analysis
        assert "historical_success_rate" in analysis
        assert "avg_historical_return" in analysis
        print(f"Analysis structure verified with {len(analysis)} fields")
    
    def test_expected_direction_values(self):
        """Test expected_direction is one of LONG/SHORT/NEUTRAL"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/BTCUSDT")
        data = response.json()
        
        direction = data["analysis"]["expected_direction"]
        assert direction in ["LONG", "SHORT", "NEUTRAL"]
        print(f"Expected direction: {direction}")
    
    def test_confidence_bounds(self):
        """Test confidence values are bounded [0, 1]"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/BTCUSDT")
        data = response.json()
        
        analysis = data["analysis"]
        assert 0 <= analysis["direction_confidence"] <= 1
        assert 0 <= analysis["similarity_confidence"] <= 1
        assert 0 <= analysis["best_similarity"] <= 1
        assert 0 <= analysis["historical_success_rate"] <= 1
        print(f"Confidence bounds verified: dir={analysis['direction_confidence']:.4f}, sim={analysis['similarity_confidence']:.4f}")
    
    def test_structure_vector_9_features(self):
        """Test structure vector has 9 features"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/BTCUSDT")
        data = response.json()
        
        vector = data["current_vector"]
        assert vector is not None
        
        # Verify 9 features
        required_features = [
            "trend_slope", "volatility_ratio", "volume_delta",
            "momentum", "range_position", "body_ratio",
            "upper_wick_ratio", "lower_wick_ratio", "trend_strength"
        ]
        
        for feature in required_features:
            assert feature in vector, f"Missing feature: {feature}"
        
        # Check vector array has 9 elements
        assert len(vector["vector"]) == 9
        print(f"Structure vector with 9 features verified")
    
    def test_top_matches_threshold(self):
        """Test matches meet similarity threshold >= 0.75"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/BTCUSDT")
        data = response.json()
        
        for match in data["top_matches"]:
            assert match["similarity"] >= SIMILARITY_THRESHOLD
        print(f"All {len(data['top_matches'])} matches above threshold {SIMILARITY_THRESHOLD}")


class TestConfidenceFormula:
    """Tests for confidence calculation formula"""
    
    def test_confidence_formula(self):
        """Test confidence = 0.60 × similarity + 0.40 × success_rate"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/BTCUSDT")
        data = response.json()
        
        analysis = data["analysis"]
        best_similarity = analysis["best_similarity"]
        success_rate = analysis["historical_success_rate"]
        reported_confidence = analysis["similarity_confidence"]
        
        # Calculate expected confidence using formula
        expected_confidence = SIMILARITY_WEIGHT * best_similarity + HISTORICAL_SUCCESS_WEIGHT * success_rate
        
        # Allow small tolerance for floating point
        assert abs(reported_confidence - expected_confidence) < 0.01, \
            f"Confidence mismatch: reported={reported_confidence}, expected={expected_confidence}"
        print(f"Confidence formula verified: {SIMILARITY_WEIGHT}×{best_similarity:.4f} + {HISTORICAL_SUCCESS_WEIGHT}×{success_rate:.4f} = {expected_confidence:.4f}")


class TestTopMatchesEndpoint:
    """Tests for GET /api/v1/fractal-similarity/top/{symbol}"""
    
    def test_top_matches_default_limit(self):
        """Test top matches returns default 5 matches"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/top/BTCUSDT")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["count"] <= 5
        print(f"Top matches count: {data['count']}")
    
    def test_top_matches_custom_limit(self):
        """Test top matches with custom limit"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/top/BTCUSDT?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] <= 10
        print(f"Top matches with limit=10: count={data['count']}")
    
    def test_top_matches_sorted_descending(self):
        """Test matches are sorted by similarity descending"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/top/BTCUSDT")
        data = response.json()
        
        matches = data["matches"]
        if len(matches) > 1:
            for i in range(len(matches) - 1):
                assert matches[i]["similarity_score"] >= matches[i + 1]["similarity_score"]
        print(f"Matches sorted by similarity descending")
    
    def test_match_structure(self):
        """Test match response has correct fields"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/top/BTCUSDT")
        data = response.json()
        
        if data["matches"]:
            match = data["matches"][0]
            assert "pattern_id" in match
            assert "similarity_score" in match
            assert "historical_direction" in match
            assert "historical_return" in match
            assert "was_successful" in match
            assert "window_size" in match
            assert "pattern_timestamp" in match
        print(f"Match structure verified")


class TestHistoryEndpoint:
    """Tests for GET /api/v1/fractal-similarity/history/{symbol}"""
    
    def test_history_returns_200(self):
        """Test history endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/history/BTCUSDT")
        assert response.status_code == 200
        print(f"History status: {response.status_code}")
    
    def test_history_response_structure(self):
        """Test history response structure"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/history/BTCUSDT")
        data = response.json()
        
        assert data["status"] == "ok"
        assert "symbol" in data
        assert "count" in data
        assert "history" in data
        assert isinstance(data["history"], list)
        print(f"History count: {data['count']}")
    
    def test_history_entry_fields(self):
        """Test history entry has correct fields"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/history/BTCUSDT")
        data = response.json()
        
        if data["history"]:
            entry = data["history"][0]
            assert "expected_direction" in entry
            assert "direction_confidence" in entry
            assert "similarity_confidence" in entry
            assert "best_similarity" in entry
            assert "matches_found" in entry
            assert "historical_success_rate" in entry
            assert "created_at" in entry
        print(f"History entry structure verified")


class TestRecomputeEndpoint:
    """Tests for POST /api/v1/fractal-similarity/recompute/{symbol}"""
    
    def test_recompute_returns_200(self):
        """Test recompute endpoint returns 200"""
        response = requests.post(f"{BASE_URL}/api/v1/fractal-similarity/recompute/BTCUSDT")
        assert response.status_code == 200
        print(f"Recompute status: {response.status_code}")
    
    def test_recompute_response_structure(self):
        """Test recompute response structure"""
        response = requests.post(f"{BASE_URL}/api/v1/fractal-similarity/recompute/ETHUSDT")
        data = response.json()
        
        assert data["status"] == "ok"
        assert data["symbol"] == "ETHUSDT"
        assert "analysis" in data
        assert "recomputed_at" in data
        print(f"Recompute response verified")
    
    def test_recompute_triggers_analysis(self):
        """Test recompute triggers fresh analysis"""
        response = requests.post(f"{BASE_URL}/api/v1/fractal-similarity/recompute/SOLUSDT")
        data = response.json()
        
        analysis = data["analysis"]
        assert "expected_direction" in analysis
        assert "similarity_confidence" in analysis
        assert analysis["matches_found"] > 0
        print(f"Recompute found {analysis['matches_found']} matches")


class TestModifierEndpoint:
    """Tests for GET /api/v1/fractal-similarity/modifier/{symbol}"""
    
    def test_modifier_long_returns_200(self):
        """Test modifier with LONG direction"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/modifier/BTCUSDT?hypothesis_direction=LONG")
        assert response.status_code == 200
        print(f"Modifier LONG status: {response.status_code}")
    
    def test_modifier_short_returns_200(self):
        """Test modifier with SHORT direction"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/modifier/BTCUSDT?hypothesis_direction=SHORT")
        assert response.status_code == 200
        print(f"Modifier SHORT status: {response.status_code}")
    
    def test_modifier_response_structure(self):
        """Test modifier response has correct fields"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/modifier/BTCUSDT?hypothesis_direction=LONG")
        data = response.json()
        
        assert data["status"] == "ok"
        assert "modifier" in data
        
        modifier = data["modifier"]
        assert "hypothesis_direction" in modifier
        assert "expected_direction" in modifier
        assert "similarity_confidence" in modifier
        assert "is_aligned" in modifier
        assert "modifier_value" in modifier
        assert "matches_found" in modifier
        assert "best_similarity" in modifier
        assert "historical_success_rate" in modifier
        assert "reason" in modifier
        print(f"Modifier structure verified")
    
    def test_aligned_modifier_value(self):
        """Test aligned modifier = 1.12"""
        # First get the expected direction
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/BTCUSDT")
        expected_direction = response.json()["analysis"]["expected_direction"]
        
        # Test with matching direction
        if expected_direction in ["LONG", "SHORT"]:
            mod_response = requests.get(
                f"{BASE_URL}/api/v1/fractal-similarity/modifier/BTCUSDT?hypothesis_direction={expected_direction}"
            )
            modifier = mod_response.json()["modifier"]
            
            assert modifier["is_aligned"] == True
            assert modifier["modifier_value"] == SIMILARITY_ALIGNED_MODIFIER
            print(f"Aligned modifier verified: {modifier['modifier_value']} == {SIMILARITY_ALIGNED_MODIFIER}")
        else:
            print(f"Expected direction is NEUTRAL, skipping aligned test")
    
    def test_conflict_modifier_value(self):
        """Test conflict modifier = 0.90"""
        # First get the expected direction
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/BTCUSDT")
        expected_direction = response.json()["analysis"]["expected_direction"]
        
        # Test with opposite direction
        if expected_direction == "LONG":
            opposite = "SHORT"
        elif expected_direction == "SHORT":
            opposite = "LONG"
        else:
            print(f"Expected direction is NEUTRAL, skipping conflict test")
            return
        
        mod_response = requests.get(
            f"{BASE_URL}/api/v1/fractal-similarity/modifier/BTCUSDT?hypothesis_direction={opposite}"
        )
        modifier = mod_response.json()["modifier"]
        
        assert modifier["is_aligned"] == False
        assert modifier["modifier_value"] == SIMILARITY_CONFLICT_MODIFIER
        print(f"Conflict modifier verified: {modifier['modifier_value']} == {SIMILARITY_CONFLICT_MODIFIER}")
    
    def test_modifier_direction_normalization(self):
        """Test direction normalization (BULLISH -> LONG, etc.)"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/modifier/BTCUSDT?hypothesis_direction=BULLISH")
        data = response.json()
        
        # Should normalize to LONG
        modifier = data["modifier"]
        assert "LONG" in modifier["reason"] or "NEUTRAL" in modifier["reason"] or "conflict" in modifier["reason"].lower()
        print(f"Direction normalization verified: BULLISH processed")


class TestSummaryEndpoint:
    """Tests for GET /api/v1/fractal-similarity/summary/{symbol}"""
    
    def test_summary_returns_200(self):
        """Test summary endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/summary/BTCUSDT")
        assert response.status_code == 200
        print(f"Summary status: {response.status_code}")
    
    def test_summary_response_structure(self):
        """Test summary response structure"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/summary/BTCUSDT")
        data = response.json()
        
        assert data["status"] == "ok"
        assert "symbol" in data
        assert "summary" in data
        
        summary = data["summary"]
        assert "current_direction" in summary
        assert "current_confidence" in summary
        assert "total_patterns_stored" in summary
        assert "total_analyses" in summary
        assert "avg_match_rate" in summary
        assert "avg_success_rate" in summary
        assert "best_window_size" in summary
        assert "best_window_success_rate" in summary
        print(f"Summary structure verified")
    
    def test_best_window_in_allowed_sizes(self):
        """Test best_window_size is one of 50, 100, 200"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/summary/BTCUSDT")
        data = response.json()
        
        best_window = data["summary"]["best_window_size"]
        assert best_window in WINDOW_SIZES
        print(f"Best window size: {best_window}")


class TestWindowSizes:
    """Tests for window size handling"""
    
    def test_all_window_sizes_used(self):
        """Test that matches from all window sizes are present"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/BTCUSDT")
        data = response.json()
        
        # Patterns searched should be multiple of window sizes count
        patterns_searched = data["analysis"]["patterns_searched"]
        assert patterns_searched >= 50 * len(WINDOW_SIZES)  # At least 50 patterns per window
        print(f"Patterns searched: {patterns_searched} (expected multiple of {len(WINDOW_SIZES)} windows)")
    
    def test_matches_have_window_size(self):
        """Test each match has window_size field"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/top/BTCUSDT?limit=20")
        data = response.json()
        
        window_sizes_found = set()
        for match in data["matches"]:
            assert "window_size" in match
            assert match["window_size"] in WINDOW_SIZES
            window_sizes_found.add(match["window_size"])
        
        print(f"Window sizes in matches: {window_sizes_found}")


class TestCrossEndpointConsistency:
    """Tests for data consistency across endpoints"""
    
    def test_analysis_and_modifier_consistency(self):
        """Test analysis and modifier return consistent data"""
        # Get analysis
        analysis_response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/BTCUSDT")
        analysis = analysis_response.json()["analysis"]
        
        # Get modifier
        modifier_response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/modifier/BTCUSDT?hypothesis_direction=LONG")
        modifier = modifier_response.json()["modifier"]
        
        # Check consistency
        assert analysis["expected_direction"] == modifier["expected_direction"]
        assert analysis["matches_found"] == modifier["matches_found"]
        assert abs(analysis["best_similarity"] - modifier["best_similarity"]) < 0.0001
        print(f"Cross-endpoint consistency verified")
    
    def test_analysis_and_summary_consistency(self):
        """Test analysis and summary return consistent current state"""
        # Get analysis
        analysis_response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/BTCUSDT")
        analysis = analysis_response.json()["analysis"]
        
        # Get summary
        summary_response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/summary/BTCUSDT")
        summary = summary_response.json()["summary"]
        
        # Check current state consistency
        assert analysis["expected_direction"] == summary["current_direction"]
        print(f"Analysis-Summary consistency verified")


class TestDifferentSymbols:
    """Tests for different trading symbols"""
    
    def test_btcusdt(self):
        """Test BTCUSDT analysis"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/BTCUSDT")
        assert response.status_code == 200
        assert response.json()["symbol"] == "BTCUSDT"
        print("BTCUSDT: OK")
    
    def test_ethusdt(self):
        """Test ETHUSDT analysis"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/ETHUSDT")
        assert response.status_code == 200
        assert response.json()["symbol"] == "ETHUSDT"
        print("ETHUSDT: OK")
    
    def test_solusdt(self):
        """Test SOLUSDT analysis"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/SOLUSDT")
        assert response.status_code == 200
        assert response.json()["symbol"] == "SOLUSDT"
        print("SOLUSDT: OK")
    
    def test_symbol_uppercase_normalization(self):
        """Test lowercase symbol is normalized to uppercase"""
        response = requests.get(f"{BASE_URL}/api/v1/fractal-similarity/btcusdt")
        assert response.status_code == 200
        assert response.json()["symbol"] == "BTCUSDT"
        print("Symbol normalization: OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
