"""
Hypothesis Engine API Tests - PHASE 29.1

Tests all 4 hypothesis endpoints:
- GET /api/v1/hypothesis/current/{symbol}
- GET /api/v1/hypothesis/history/{symbol}
- GET /api/v1/hypothesis/summary/{symbol}
- POST /api/v1/hypothesis/recompute/{symbol}
"""

import os
import pytest
import requests

# Get BASE_URL from environment
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Valid enum values based on hypothesis_types.py
VALID_HYPOTHESIS_TYPES = [
    "BULLISH_CONTINUATION",
    "BEARISH_CONTINUATION",
    "BREAKOUT_FORMING",
    "BREAKOUT_FAILURE_RISK",
    "RANGE_MEAN_REVERSION",
    "SHORT_SQUEEZE_SETUP",
    "LONG_SQUEEZE_SETUP",
    "VOLATILE_UNWIND",
    "NO_EDGE",
]

VALID_DIRECTIONAL_BIAS = ["LONG", "SHORT", "NEUTRAL"]
VALID_EXECUTION_STATES = ["FAVORABLE", "CAUTIOUS", "UNFAVORABLE"]


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestHypothesisCurrentEndpoint:
    """Tests for GET /api/v1/hypothesis/current/{symbol}"""

    def test_current_returns_200(self, api_client):
        """Test 1: current endpoint returns 200"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/current/BTC")
        assert response.status_code == 200

    def test_current_response_has_required_fields(self, api_client):
        """Test 2: response contains all required fields"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/current/ETH")
        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "symbol",
            "hypothesis_type",
            "directional_bias",
            "confidence",
            "reliability",
            "alpha_support",
            "regime_support",
            "microstructure_support",
            "macro_fractal_support",
            "execution_state",
            "reason",
            "created_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_current_hypothesis_type_valid(self, api_client):
        """Test 3: hypothesis_type is a valid enum value"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/current/SOL")
        data = response.json()
        assert data["hypothesis_type"] in VALID_HYPOTHESIS_TYPES

    def test_current_directional_bias_valid(self, api_client):
        """Test 4: directional_bias is LONG/SHORT/NEUTRAL"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/current/BTC")
        data = response.json()
        assert data["directional_bias"] in VALID_DIRECTIONAL_BIAS

    def test_current_execution_state_valid(self, api_client):
        """Test 5: execution_state is FAVORABLE/CAUTIOUS/UNFAVORABLE"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/current/BTC")
        data = response.json()
        assert data["execution_state"] in VALID_EXECUTION_STATES

    def test_current_confidence_in_range(self, api_client):
        """Test 6: confidence is in [0, 1] range"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/current/BTC")
        data = response.json()
        assert 0.0 <= data["confidence"] <= 1.0

    def test_current_reliability_in_range(self, api_client):
        """Test 7: reliability is in [0, 1] range"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/current/BTC")
        data = response.json()
        assert 0.0 <= data["reliability"] <= 1.0

    def test_current_support_values_in_range(self, api_client):
        """Test 8: all support values are in [0, 1] range"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/current/BTC")
        data = response.json()
        assert 0.0 <= data["alpha_support"] <= 1.0
        assert 0.0 <= data["regime_support"] <= 1.0
        assert 0.0 <= data["microstructure_support"] <= 1.0
        assert 0.0 <= data["macro_fractal_support"] <= 1.0

    def test_current_symbol_uppercase(self, api_client):
        """Test 9: symbol is returned uppercase"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/current/btc")
        data = response.json()
        assert data["symbol"] == "BTC"


class TestHypothesisHistoryEndpoint:
    """Tests for GET /api/v1/hypothesis/history/{symbol}"""

    def test_history_returns_200(self, api_client):
        """Test 10: history endpoint returns 200"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/history/BTC")
        assert response.status_code == 200

    def test_history_has_required_fields(self, api_client):
        """Test 11: response has symbol, total, records"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/history/BTC")
        data = response.json()
        assert "symbol" in data
        assert "total" in data
        assert "records" in data
        assert isinstance(data["records"], list)

    def test_history_record_fields(self, api_client):
        """Test 12: each history record has correct fields"""
        # First generate some history
        api_client.post(f"{BASE_URL}/api/v1/hypothesis/recompute/AVAX")
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/history/AVAX")
        data = response.json()
        
        if data["records"]:
            record = data["records"][0]
            assert "hypothesis_type" in record
            assert "directional_bias" in record
            assert "confidence" in record
            assert "reliability" in record
            assert "execution_state" in record
            assert "created_at" in record

    def test_history_limit_parameter(self, api_client):
        """Test 13: limit parameter works"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/history/BTC?limit=2")
        data = response.json()
        # Total can be more, but records should respect limit
        assert len(data["records"]) <= 2


class TestHypothesisSummaryEndpoint:
    """Tests for GET /api/v1/hypothesis/summary/{symbol}"""

    def test_summary_returns_200(self, api_client):
        """Test 14: summary endpoint returns 200"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/summary/BTC")
        assert response.status_code == 200

    def test_summary_has_required_structure(self, api_client):
        """Test 15: summary has correct nested structure"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/summary/BTC")
        data = response.json()

        assert "symbol" in data
        assert "total_records" in data
        assert "types" in data
        assert "bias" in data
        assert "execution_states" in data
        assert "averages" in data
        assert "current" in data

    def test_summary_types_counts(self, api_client):
        """Test 16: types object has correct keys"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/summary/BTC")
        data = response.json()

        expected_type_keys = [
            "bullish_continuation",
            "bearish_continuation",
            "breakout_forming",
            "range_mean_reversion",
            "no_edge",
            "other",
        ]
        for key in expected_type_keys:
            assert key in data["types"]

    def test_summary_bias_counts(self, api_client):
        """Test 17: bias object has long/short/neutral"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/summary/BTC")
        data = response.json()
        assert "long" in data["bias"]
        assert "short" in data["bias"]
        assert "neutral" in data["bias"]

    def test_summary_execution_states(self, api_client):
        """Test 18: execution_states has favorable/cautious/unfavorable"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/summary/BTC")
        data = response.json()
        assert "favorable" in data["execution_states"]
        assert "cautious" in data["execution_states"]
        assert "unfavorable" in data["execution_states"]

    def test_summary_averages_in_range(self, api_client):
        """Test 19: average confidence/reliability in [0, 1]"""
        response = api_client.get(f"{BASE_URL}/api/v1/hypothesis/summary/BTC")
        data = response.json()
        assert 0.0 <= data["averages"]["confidence"] <= 1.0
        assert 0.0 <= data["averages"]["reliability"] <= 1.0


class TestHypothesisRecomputeEndpoint:
    """Tests for POST /api/v1/hypothesis/recompute/{symbol}"""

    def test_recompute_returns_200(self, api_client):
        """Test 20: recompute endpoint returns 200"""
        response = api_client.post(f"{BASE_URL}/api/v1/hypothesis/recompute/BTC")
        assert response.status_code == 200

    def test_recompute_returns_status_ok(self, api_client):
        """Test 21: recompute returns status=ok"""
        response = api_client.post(f"{BASE_URL}/api/v1/hypothesis/recompute/BTC")
        data = response.json()
        assert data["status"] == "ok"

    def test_recompute_has_computed_at(self, api_client):
        """Test 22: recompute response has computed_at timestamp"""
        response = api_client.post(f"{BASE_URL}/api/v1/hypothesis/recompute/BTC")
        data = response.json()
        assert "computed_at" in data

    def test_recompute_has_full_hypothesis(self, api_client):
        """Test 23: recompute returns full hypothesis data"""
        response = api_client.post(f"{BASE_URL}/api/v1/hypothesis/recompute/BTC")
        data = response.json()
        
        required_fields = [
            "status",
            "symbol",
            "hypothesis_type",
            "directional_bias",
            "confidence",
            "reliability",
            "alpha_support",
            "regime_support",
            "microstructure_support",
            "macro_fractal_support",
            "execution_state",
            "reason",
            "computed_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_recompute_different_symbol(self, api_client):
        """Test 24: recompute works for different symbols"""
        for symbol in ["ETH", "SOL", "DOGE"]:
            response = api_client.post(f"{BASE_URL}/api/v1/hypothesis/recompute/{symbol}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["symbol"] == symbol


class TestHypothesisDataIntegrity:
    """Tests for data consistency and integrity"""

    def test_current_and_recompute_consistency(self, api_client):
        """Test 25: current and recompute return consistent data"""
        # Recompute first
        recompute_resp = api_client.post(f"{BASE_URL}/api/v1/hypothesis/recompute/XRP")
        recompute_data = recompute_resp.json()
        
        # Get current
        current_resp = api_client.get(f"{BASE_URL}/api/v1/hypothesis/current/XRP")
        current_data = current_resp.json()
        
        # They should have same hypothesis type
        assert recompute_data["hypothesis_type"] == current_data["hypothesis_type"]
        assert recompute_data["directional_bias"] == current_data["directional_bias"]

    def test_history_includes_recent_recompute(self, api_client):
        """Test 26: history includes recently computed hypothesis"""
        # Create new entry with recompute
        api_client.post(f"{BASE_URL}/api/v1/hypothesis/recompute/LINK")
        
        # Check history
        history_resp = api_client.get(f"{BASE_URL}/api/v1/hypothesis/history/LINK")
        history_data = history_resp.json()
        
        assert history_data["total"] >= 1
        assert len(history_data["records"]) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
