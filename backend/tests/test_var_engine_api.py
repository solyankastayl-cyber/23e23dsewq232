"""
PHASE 22.1 VaR Engine API Tests
================================
Comprehensive API tests for VaR Engine endpoints.

Tests:
- GET /api/v1/institutional-risk/var (full VaR state with params)
- GET /api/v1/institutional-risk/var/summary
- GET /api/v1/institutional-risk/var/state
- GET /api/v1/institutional-risk/var/tail
- POST /api/v1/institutional-risk/var/recompute
- GET /api/v1/institutional-risk/var/history
- VaR formula verification
- Risk state thresholds verification
- Modifiers verification
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')


class TestVaREngineHealth:
    """Health check for VaR Engine"""
    
    def test_api_health(self):
        """Verify API is running"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True


class TestVaRStateEndpoint:
    """Tests for GET /api/v1/institutional-risk/var"""
    
    def test_default_params(self):
        """VaR state with default parameters returns valid response"""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "22.1"
        
        var_data = data["data"]
        # Verify required fields
        assert "portfolio_var_95" in var_data
        assert "portfolio_var_99" in var_data
        assert "expected_shortfall_95" in var_data
        assert "expected_shortfall_99" in var_data
        assert "var_ratio" in var_data
        assert "risk_state" in var_data
        assert "recommended_action" in var_data
        assert "confidence_modifier" in var_data
        assert "capital_modifier" in var_data
        assert "inputs" in var_data
    
    def test_critical_risk_state(self):
        """Extreme params → CRITICAL risk state"""
        params = {
            "gross_exposure": 0.9,
            "volatility_state": "EXTREME",
            "regime": "CRISIS",
            "deployable_capital": 0.40,
            "position_concentration": 0.5
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var", params=params)
        assert response.status_code == 200
        
        data = response.json()["data"]
        assert data["risk_state"] == "CRITICAL"
        assert data["recommended_action"] == "EMERGENCY_CUT"
        assert data["confidence_modifier"] == 0.75
        assert data["capital_modifier"] == 0.5
    
    def test_elevated_risk_state(self):
        """Moderate exposure + NORMAL vol → ELEVATED risk state"""
        params = {
            "gross_exposure": 0.7,
            "volatility_state": "NORMAL",
            "regime": "MIXED",
            "deployable_capital": 0.57
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var", params=params)
        assert response.status_code == 200
        
        data = response.json()["data"]
        assert data["risk_state"] == "ELEVATED"
        assert data["recommended_action"] == "REDUCE_RISK"
        assert data["confidence_modifier"] == 0.95
        assert data["capital_modifier"] == 0.90
    
    def test_normal_risk_state(self):
        """Low exposure + LOW vol → NORMAL risk state"""
        params = {
            "gross_exposure": 0.2,
            "volatility_state": "LOW",
            "regime": "TREND",
            "deployable_capital": 0.57
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var", params=params)
        assert response.status_code == 200
        
        data = response.json()["data"]
        assert data["risk_state"] == "NORMAL"
        assert data["recommended_action"] == "HOLD"
        assert data["confidence_modifier"] == 1.0
        assert data["capital_modifier"] == 1.0
    
    def test_high_risk_state(self):
        """HIGH vol + HIGH exposure → HIGH or CRITICAL risk state"""
        params = {
            "gross_exposure": 0.8,
            "volatility_state": "HIGH",
            "regime": "MIXED",
            "deployable_capital": 0.57,
            "position_concentration": 0.4
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var", params=params)
        assert response.status_code == 200
        
        data = response.json()["data"]
        assert data["risk_state"] in ["HIGH", "CRITICAL"]


class TestVaRSummaryEndpoint:
    """Tests for GET /api/v1/institutional-risk/var/summary"""
    
    def test_summary_response_structure(self):
        """Summary returns compact data with required fields"""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "22.1"
        
        summary = data["data"]
        # Verify compact summary fields
        assert "portfolio_var_95" in summary
        assert "var_ratio" in summary
        assert "risk_state" in summary
        assert "recommended_action" in summary
        assert "confidence_modifier" in summary
        assert "capital_modifier" in summary


class TestRiskStateEndpoint:
    """Tests for GET /api/v1/institutional-risk/var/state"""
    
    def test_state_response_structure(self):
        """State info returns is_action_required and is_emergency booleans"""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var/state")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        
        state_info = data["data"]
        assert "risk_state" in state_info
        assert "recommended_action" in state_info
        assert "var_ratio" in state_info
        assert "is_action_required" in state_info
        assert "is_emergency" in state_info
        assert isinstance(state_info["is_action_required"], bool)
        assert isinstance(state_info["is_emergency"], bool)
    
    def test_state_with_params(self):
        """State changes with input parameters"""
        params = {
            "gross_exposure": 0.9,
            "volatility_state": "EXTREME",
            "regime": "CRISIS"
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var/state", params=params)
        assert response.status_code == 200
        
        data = response.json()["data"]
        # Extreme conditions should require action
        assert data["is_action_required"] is True
        assert data["is_emergency"] is True


class TestTailRiskEndpoint:
    """Tests for GET /api/v1/institutional-risk/var/tail"""
    
    def test_tail_response_structure(self):
        """Tail info returns expected shortfall and tail metrics"""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var/tail")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        
        tail_info = data["data"]
        assert "expected_shortfall_95" in tail_info
        assert "expected_shortfall_99" in tail_info
        assert "portfolio_var_95" in tail_info
        assert "portfolio_var_99" in tail_info
        assert "tail_risk_ratio" in tail_info
        assert "tail_severity" in tail_info
        assert "is_elevated" in tail_info
    
    def test_tail_severity_values(self):
        """Tail severity should be one of valid values"""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var/tail")
        assert response.status_code == 200
        
        tail_severity = response.json()["data"]["tail_severity"]
        assert tail_severity in ["NORMAL", "ELEVATED", "HIGH", "CRITICAL"]


class TestRecomputeEndpoint:
    """Tests for POST /api/v1/institutional-risk/var/recompute"""
    
    def test_recompute_success(self):
        """Recompute returns success and records to history"""
        response = requests.post(f"{BASE_URL}/api/v1/institutional-risk/var/recompute")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "VaR state recomputed and recorded"
        assert "data" in data
        
        var_data = data["data"]
        assert "portfolio_var_95" in var_data
        assert "risk_state" in var_data


class TestHistoryEndpoint:
    """Tests for GET /api/v1/institutional-risk/var/history"""
    
    def test_history_response_structure(self):
        """History returns list of entries with count"""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var/history")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert "history" in data
        assert "count" in data
        assert isinstance(data["history"], list)
        assert data["count"] == len(data["history"])
    
    def test_history_entry_structure(self):
        """Each history entry has required fields"""
        # First recompute to ensure we have history
        requests.post(f"{BASE_URL}/api/v1/institutional-risk/var/recompute")
        
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var/history")
        assert response.status_code == 200
        
        history = response.json()["history"]
        assert len(history) > 0
        
        entry = history[-1]  # Get latest entry
        assert "risk_state" in entry
        assert "portfolio_var_95" in entry
        assert "var_ratio" in entry
        assert "recommended_action" in entry
        assert "timestamp" in entry
    
    def test_history_limit(self):
        """History respects limit parameter"""
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var/history", params={"limit": 1})
        assert response.status_code == 200
        
        history = response.json()["history"]
        assert len(history) <= 1


class TestVaRFormulaVerification:
    """Tests to verify VaR calculation formula"""
    
    def test_var_95_formula(self):
        """Verify: portfolio_var_95 = gross × vol_mult × regime_mult × conc_mult × 0.08"""
        # Using known multipliers: NORMAL vol=1.0, RANGE regime=1.0
        params = {
            "gross_exposure": 0.5,
            "volatility_state": "NORMAL",
            "regime": "RANGE",
            "position_concentration": 0.3
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var", params=params)
        assert response.status_code == 200
        
        var_95 = response.json()["data"]["portfolio_var_95"]
        
        # Expected: 0.5 × 1.0 × 1.0 × (1.0 + 0.3*0.3) × 0.08 = 0.5 × 1.09 × 0.08 = 0.0436
        expected = 0.5 * 1.0 * 1.0 * 1.09 * 0.08
        assert abs(var_95 - expected) < 0.001, f"Expected {expected}, got {var_95}"
    
    def test_var_99_formula(self):
        """Verify: portfolio_var_99 = portfolio_var_95 × 1.35"""
        params = {
            "gross_exposure": 0.5,
            "volatility_state": "NORMAL",
            "regime": "RANGE",
            "position_concentration": 0.3
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var", params=params)
        assert response.status_code == 200
        
        data = response.json()["data"]
        var_95 = data["portfolio_var_95"]
        var_99 = data["portfolio_var_99"]
        
        # VaR 99 should be VaR 95 × 1.35
        expected_99 = var_95 * 1.35
        assert abs(var_99 - expected_99) < 0.001, f"Expected {expected_99}, got {var_99}"
    
    def test_volatility_multipliers(self):
        """Verify volatility multipliers: LOW=0.7, NORMAL=1.0, HIGH=1.4, EXPANDING=1.7, EXTREME=2.0"""
        vol_states = [
            ("LOW", 0.7),
            ("NORMAL", 1.0),
            ("HIGH", 1.4),
            ("EXPANDING", 1.7),
            ("EXTREME", 2.0),
        ]
        
        base_params = {
            "gross_exposure": 0.5,
            "regime": "RANGE",
            "position_concentration": 0.3,
            "deployable_capital": 0.57
        }
        
        results = {}
        for vol_state, expected_mult in vol_states:
            params = {**base_params, "volatility_state": vol_state}
            response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var", params=params)
            assert response.status_code == 200
            results[vol_state] = response.json()["data"]["portfolio_var_95"]
        
        # Verify ratios between volatility states
        # LOW/NORMAL should be ~0.7
        ratio_low_normal = results["LOW"] / results["NORMAL"]
        assert abs(ratio_low_normal - 0.7) < 0.01
        
        # HIGH/NORMAL should be ~1.4
        ratio_high_normal = results["HIGH"] / results["NORMAL"]
        assert abs(ratio_high_normal - 1.4) < 0.01
    
    def test_regime_multipliers(self):
        """Verify regime multipliers: TREND=0.9, RANGE=1.0, MIXED=1.1, SQUEEZE=1.3, CRISIS=1.6"""
        regimes = [
            ("TREND", 0.9),
            ("RANGE", 1.0),
            ("MIXED", 1.1),
            ("SQUEEZE", 1.3),
            ("CRISIS", 1.6),
        ]
        
        base_params = {
            "gross_exposure": 0.5,
            "volatility_state": "NORMAL",
            "position_concentration": 0.3,
            "deployable_capital": 0.57
        }
        
        results = {}
        for regime, expected_mult in regimes:
            params = {**base_params, "regime": regime}
            response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var", params=params)
            assert response.status_code == 200
            results[regime] = response.json()["data"]["portfolio_var_95"]
        
        # Verify ratio TREND/RANGE should be ~0.9
        ratio_trend_range = results["TREND"] / results["RANGE"]
        assert abs(ratio_trend_range - 0.9) < 0.01
        
        # CRISIS/RANGE should be ~1.6
        ratio_crisis_range = results["CRISIS"] / results["RANGE"]
        assert abs(ratio_crisis_range - 1.6) < 0.01


class TestRiskStateThresholds:
    """Tests to verify risk state classification thresholds"""
    
    def test_normal_threshold(self):
        """NORMAL: var_ratio < 0.10"""
        # With very low exposure, var_ratio should be < 0.10
        params = {
            "gross_exposure": 0.15,
            "volatility_state": "LOW",
            "regime": "TREND",
            "deployable_capital": 0.57
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var", params=params)
        assert response.status_code == 200
        
        data = response.json()["data"]
        assert data["var_ratio"] < 0.10
        assert data["risk_state"] == "NORMAL"
    
    def test_elevated_threshold(self):
        """ELEVATED: 0.10 <= var_ratio < 0.18"""
        params = {
            "gross_exposure": 0.7,
            "volatility_state": "NORMAL",
            "regime": "MIXED",
            "deployable_capital": 0.57
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var", params=params)
        assert response.status_code == 200
        
        data = response.json()["data"]
        assert 0.10 <= data["var_ratio"] < 0.18, f"var_ratio {data['var_ratio']} not in ELEVATED range"
        assert data["risk_state"] == "ELEVATED"
    
    def test_critical_threshold(self):
        """CRITICAL: var_ratio > 0.28"""
        params = {
            "gross_exposure": 0.9,
            "volatility_state": "EXTREME",
            "regime": "CRISIS",
            "deployable_capital": 0.40,
            "position_concentration": 0.5
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var", params=params)
        assert response.status_code == 200
        
        data = response.json()["data"]
        assert data["var_ratio"] > 0.28, f"var_ratio {data['var_ratio']} should be > 0.28"
        assert data["risk_state"] == "CRITICAL"


class TestModifiersVerification:
    """Tests to verify risk state modifiers"""
    
    def test_normal_modifiers(self):
        """NORMAL: confidence=1.0, capital=1.0"""
        params = {
            "gross_exposure": 0.2,
            "volatility_state": "LOW",
            "regime": "TREND",
            "deployable_capital": 0.57
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var", params=params)
        assert response.status_code == 200
        
        data = response.json()["data"]
        assert data["risk_state"] == "NORMAL"
        assert data["confidence_modifier"] == 1.0
        assert data["capital_modifier"] == 1.0
    
    def test_elevated_modifiers(self):
        """ELEVATED: confidence=0.95, capital=0.90"""
        params = {
            "gross_exposure": 0.7,
            "volatility_state": "NORMAL",
            "regime": "MIXED",
            "deployable_capital": 0.57
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var", params=params)
        assert response.status_code == 200
        
        data = response.json()["data"]
        assert data["risk_state"] == "ELEVATED"
        assert data["confidence_modifier"] == 0.95
        assert data["capital_modifier"] == 0.90
    
    def test_critical_modifiers(self):
        """CRITICAL: confidence=0.75, capital=0.50"""
        params = {
            "gross_exposure": 0.9,
            "volatility_state": "EXTREME",
            "regime": "CRISIS",
            "deployable_capital": 0.40,
            "position_concentration": 0.5
        }
        response = requests.get(f"{BASE_URL}/api/v1/institutional-risk/var", params=params)
        assert response.status_code == 200
        
        data = response.json()["data"]
        assert data["risk_state"] == "CRITICAL"
        assert data["confidence_modifier"] == 0.75
        assert data["capital_modifier"] == 0.50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
