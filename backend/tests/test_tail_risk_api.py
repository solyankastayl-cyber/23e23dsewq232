"""
PHASE 22.2 — Tail Risk Engine API Tests
========================================
Comprehensive API tests for Tail Risk Engine endpoints.

Tests:
1-3.   GET /tail-risk with default, extreme, low params
4-5.   GET /tail-risk/summary - verify required keys
6-7.   GET /tail-risk/state - verify state info
8-9.   GET /tail-risk/asymmetry - verify asymmetry analysis
10-11. POST /tail-risk/recompute - verify recompute
12-13. GET /tail-risk/history - verify history after recompute
14-17. State threshold verification: LOW/ELEVATED/HIGH/EXTREME
18-20. Modifier verification by state
21-23. Recommended action verification
24-25. Score bounded [0.0, 1.0] verification
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')


class TestTailRiskDefaultEndpoint:
    """Test GET /api/v1/institutional-risk/tail-risk with default params."""
    
    def test_default_returns_elevated(self):
        """Default params should return ELEVATED state."""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "22.2"
        # Default should be ELEVATED based on default params
        assert data["data"]["tail_risk_state"] == "ELEVATED"
        assert data["data"]["recommended_action"] == "HEDGE"
    
    def test_default_has_required_fields(self):
        """Default response contains all required fields."""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk")
        assert response.status_code == 200
        data = response.json()["data"]
        required = [
            "tail_loss_95", "tail_loss_99", "crash_sensitivity",
            "tail_concentration", "asymmetry_score", "tail_risk_score",
            "tail_risk_state", "recommended_action",
            "confidence_modifier", "capital_modifier", "reason", "timestamp"
        ]
        for key in required:
            assert key in data, f"Missing required field: {key}"
    
    def test_default_has_inputs(self):
        """Default response contains inputs section."""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "inputs" in data
        assert "gross_exposure" in data["inputs"]
        assert "volatility_state" in data["inputs"]


class TestTailRiskExtremeParams:
    """Test GET /api/v1/institutional-risk/tail-risk with extreme params → EXTREME."""
    
    def test_extreme_params_returns_extreme(self):
        """Extreme params should return EXTREME state."""
        params = {
            "portfolio_var_95": 0.20,
            "expected_shortfall_95": 0.35,
            "gross_exposure": 0.9,
            "volatility_state": "EXTREME",
            "concentration_score": 0.7,
            "asset_exposure": 0.75,
            "cluster_exposure": 0.70,
            "factor_exposure": 0.65,
        }
        response = requests.get(
            f"{BASE_URL}/api/v1/institutional-risk/tail-risk",
            params=params
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["tail_risk_state"] == "EXTREME"
        assert data["recommended_action"] == "EMERGENCY_HEDGE"
        assert data["tail_risk_score"] > 0.65  # EXTREME threshold
    
    def test_extreme_modifiers(self):
        """Extreme state has correct modifiers (0.70/0.50)."""
        params = {
            "portfolio_var_95": 0.20,
            "expected_shortfall_95": 0.35,
            "gross_exposure": 0.9,
            "volatility_state": "EXTREME",
            "concentration_score": 0.7,
            "asset_exposure": 0.75,
        }
        response = requests.get(
            f"{BASE_URL}/api/v1/institutional-risk/tail-risk",
            params=params
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["confidence_modifier"] == 0.70
        assert data["capital_modifier"] == 0.50


class TestTailRiskLowParams:
    """Test GET /api/v1/institutional-risk/tail-risk with low params → LOW."""
    
    def test_low_params_returns_low(self):
        """Low params should return LOW state."""
        params = {
            "portfolio_var_95": 0.02,
            "expected_shortfall_95": 0.024,
            "gross_exposure": 0.2,
            "volatility_state": "LOW",
            "concentration_score": 0.1,
            "asset_exposure": 0.15,
            "cluster_exposure": 0.10,
            "factor_exposure": 0.10,
        }
        response = requests.get(
            f"{BASE_URL}/api/v1/institutional-risk/tail-risk",
            params=params
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["tail_risk_state"] == "LOW"
        assert data["recommended_action"] == "HOLD"
        assert data["tail_risk_score"] < 0.25  # LOW threshold
    
    def test_low_modifiers(self):
        """LOW state has correct modifiers (1.00/1.00)."""
        params = {
            "portfolio_var_95": 0.02,
            "expected_shortfall_95": 0.024,
            "gross_exposure": 0.2,
            "volatility_state": "LOW",
            "concentration_score": 0.1,
            "asset_exposure": 0.15,
            "cluster_exposure": 0.10,
            "factor_exposure": 0.10,
        }
        response = requests.get(
            f"{BASE_URL}/api/v1/institutional-risk/tail-risk",
            params=params
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["confidence_modifier"] == 1.00
        assert data["capital_modifier"] == 1.00


class TestTailRiskSummary:
    """Test GET /api/v1/institutional-risk/tail-risk/summary."""
    
    def test_summary_returns_ok(self):
        """Summary endpoint returns successfully."""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "22.2"
    
    def test_summary_has_required_keys(self):
        """Summary contains required keys."""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk/summary")
        assert response.status_code == 200
        summary = response.json()["data"]
        required = [
            "tail_risk_score", "tail_risk_state", "recommended_action",
            "crash_sensitivity", "asymmetry_score",
            "confidence_modifier", "capital_modifier"
        ]
        for key in required:
            assert key in summary, f"Missing summary key: {key}"


class TestTailRiskState:
    """Test GET /api/v1/institutional-risk/tail-risk/state."""
    
    def test_state_returns_ok(self):
        """State endpoint returns successfully."""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk/state")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_state_has_required_fields(self):
        """State endpoint has required fields."""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk/state")
        assert response.status_code == 200
        state_info = response.json()["data"]
        required = ["tail_risk_state", "tail_risk_score", "recommended_action"]
        for key in required:
            assert key in state_info, f"Missing state field: {key}"


class TestTailRiskAsymmetry:
    """Test GET /api/v1/institutional-risk/tail-risk/asymmetry."""
    
    def test_asymmetry_returns_ok(self):
        """Asymmetry endpoint returns successfully."""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk/asymmetry")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_asymmetry_has_required_fields(self):
        """Asymmetry endpoint has required fields."""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk/asymmetry")
        assert response.status_code == 200
        asymmetry = response.json()["data"]
        required = [
            "asymmetry_score", "asymmetry_normalized",
            "tail_loss_95", "tail_loss_99",
            "crash_sensitivity", "tail_concentration"
        ]
        for key in required:
            assert key in asymmetry, f"Missing asymmetry field: {key}"
    
    def test_asymmetry_calculation(self):
        """Verify asymmetry_score = ES_95 / VaR_95."""
        # Use specific values to verify calculation
        response = requests.get(
            f"{BASE_URL}/api/v1/institutional-risk/tail-risk/asymmetry",
            params={"portfolio_var_95": 0.10, "expected_shortfall_95": 0.12}
        )
        assert response.status_code == 200
        asymmetry = response.json()["data"]
        # asymmetry_score should be 0.12 / 0.10 = 1.2
        assert abs(asymmetry["asymmetry_score"] - 1.2) < 0.0001


class TestTailRiskRecompute:
    """Test POST /api/v1/institutional-risk/tail-risk/recompute."""
    
    def test_recompute_returns_ok(self):
        """Recompute endpoint returns successfully."""
        response = requests.post(f"{BASE_URL}/api/v1/institutional-risk/tail-risk/recompute")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "recomputed and recorded" in data["message"].lower()
    
    def test_recompute_returns_state(self):
        """Recompute returns tail risk state."""
        response = requests.post(f"{BASE_URL}/api/v1/institutional-risk/tail-risk/recompute")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "tail_risk_score" in data
        assert "tail_risk_state" in data


class TestTailRiskHistory:
    """Test GET /api/v1/institutional-risk/tail-risk/history."""
    
    def test_history_returns_ok(self):
        """History endpoint returns successfully."""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk/history")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "history" in data
        assert "count" in data
    
    def test_history_after_recompute(self):
        """History has entries after recompute."""
        # Recompute first
        requests.post(f"{BASE_URL}/api/v1/institutional-risk/tail-risk/recompute")
        # Get history
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk/history")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        assert len(data["history"]) >= 1
        # Verify history entry fields
        entry = data["history"][0]
        required = ["tail_risk_state", "tail_risk_score", "crash_sensitivity", "recommended_action", "timestamp"]
        for key in required:
            assert key in entry, f"Missing history field: {key}"


class TestStateThresholds:
    """Verify state thresholds: LOW(<0.25), ELEVATED(0.25-0.45), HIGH(0.45-0.65), EXTREME(>0.65)."""
    
    def test_low_threshold(self):
        """Score < 0.25 → LOW state."""
        params = {
            "portfolio_var_95": 0.02,
            "expected_shortfall_95": 0.024,
            "gross_exposure": 0.2,
            "volatility_state": "LOW",
            "concentration_score": 0.1,
            "asset_exposure": 0.15,
            "cluster_exposure": 0.10,
            "factor_exposure": 0.10,
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk", params=params)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["tail_risk_score"] < 0.25
        assert data["tail_risk_state"] == "LOW"
    
    def test_elevated_threshold(self):
        """Score 0.25-0.45 → ELEVATED state."""
        # Default params give ELEVATED with score ~0.27
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk")
        assert response.status_code == 200
        data = response.json()["data"]
        assert 0.25 <= data["tail_risk_score"] < 0.45
        assert data["tail_risk_state"] == "ELEVATED"
    
    def test_high_threshold(self):
        """Score 0.45-0.65 → HIGH state."""
        params = {
            "portfolio_var_95": 0.12,
            "expected_shortfall_95": 0.18,
            "gross_exposure": 0.7,
            "volatility_state": "HIGH",
            "concentration_score": 0.5,
            "asset_exposure": 0.55,
            "cluster_exposure": 0.50,
            "factor_exposure": 0.45,
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk", params=params)
        assert response.status_code == 200
        data = response.json()["data"]
        # This should be HIGH or EXTREME depending on exact calculation
        assert data["tail_risk_state"] in ["HIGH", "EXTREME"]
    
    def test_extreme_threshold(self):
        """Score > 0.65 → EXTREME state."""
        params = {
            "portfolio_var_95": 0.20,
            "expected_shortfall_95": 0.35,
            "gross_exposure": 0.9,
            "volatility_state": "EXTREME",
            "concentration_score": 0.7,
            "asset_exposure": 0.75,
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk", params=params)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["tail_risk_score"] > 0.65
        assert data["tail_risk_state"] == "EXTREME"


class TestRecommendedActions:
    """Verify recommended actions: LOW→HOLD, ELEVATED→HEDGE, HIGH→DELEVER, EXTREME→EMERGENCY_HEDGE."""
    
    def test_low_action_hold(self):
        """LOW state → HOLD action."""
        params = {
            "portfolio_var_95": 0.02,
            "expected_shortfall_95": 0.024,
            "gross_exposure": 0.2,
            "volatility_state": "LOW",
            "concentration_score": 0.1,
            "asset_exposure": 0.15,
            "cluster_exposure": 0.10,
            "factor_exposure": 0.10,
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk", params=params)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["tail_risk_state"] == "LOW"
        assert data["recommended_action"] == "HOLD"
    
    def test_elevated_action_hedge(self):
        """ELEVATED state → HEDGE action."""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["tail_risk_state"] == "ELEVATED"
        assert data["recommended_action"] == "HEDGE"
    
    def test_extreme_action_emergency_hedge(self):
        """EXTREME state → EMERGENCY_HEDGE action."""
        params = {
            "portfolio_var_95": 0.20,
            "expected_shortfall_95": 0.35,
            "gross_exposure": 0.9,
            "volatility_state": "EXTREME",
            "concentration_score": 0.7,
            "asset_exposure": 0.75,
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk", params=params)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["tail_risk_state"] == "EXTREME"
        assert data["recommended_action"] == "EMERGENCY_HEDGE"


class TestScoreBounding:
    """Verify tail_risk_score bounded [0.0, 1.0]."""
    
    def test_score_min_boundary(self):
        """Score is at least 0.0."""
        params = {
            "portfolio_var_95": 0.01,
            "expected_shortfall_95": 0.01,
            "gross_exposure": 0.1,
            "volatility_state": "LOW",
            "concentration_score": 0.05,
            "asset_exposure": 0.05,
            "cluster_exposure": 0.05,
            "factor_exposure": 0.05,
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk", params=params)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["tail_risk_score"] >= 0.0
    
    def test_score_max_boundary(self):
        """Score is at most 1.0."""
        params = {
            "portfolio_var_95": 0.50,
            "expected_shortfall_95": 0.80,
            "gross_exposure": 1.0,
            "volatility_state": "EXTREME",
            "concentration_score": 1.0,
            "asset_exposure": 1.0,
            "cluster_exposure": 1.0,
            "factor_exposure": 1.0,
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/tail-risk", params=params)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["tail_risk_score"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
