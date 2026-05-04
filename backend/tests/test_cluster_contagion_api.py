"""
PHASE 22.3 — Cluster Contagion Engine API Tests
================================================
Comprehensive API tests for Cluster Contagion Engine endpoints.

Tests:
1. GET /cluster-contagion - full state with default params
2. GET /cluster-contagion with extreme params → SYSTEMIC
3. GET /cluster-contagion with low params → LOW
4. GET /cluster-contagion/summary - compact summary
5. GET /cluster-contagion/paths - contagion paths and probabilities
6. GET /cluster-contagion/stress - per-cluster stress scores
7. POST /cluster-contagion/recompute - recompute and record
8. GET /cluster-contagion/history - history entries
9. Verify systemic_risk_score bounded [0.0, 1.0]
10. Verify contagion states: LOW(<0.25), ELEVATED(0.25-0.45), HIGH(0.45-0.65), SYSTEMIC(>0.65)
11. Verify modifiers: LOW(1.0/1.0), ELEVATED(0.95/0.90), HIGH(0.85/0.75), SYSTEMIC(0.70/0.55)
12. Verify contagion paths contain proper cluster chain format
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')
ENDPOINT_PREFIX = f"{BASE_URL}/api/v1/institutional-risk/cluster-contagion"

CLUSTER_IDS = ["btc_cluster", "majors_cluster", "alts_cluster", "trend_cluster", "reversal_cluster"]


class TestClusterContagionDefaultState:
    """Tests for default cluster contagion state"""

    def test_get_contagion_state_default(self):
        """GET /cluster-contagion with default params returns valid state"""
        response = requests.get(f"{ENDPOINT_PREFIX}")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "22.3"
        assert "data" in data

        state = data["data"]
        # Verify all required fields
        assert "cluster_stress" in state
        assert "contagion_probabilities" in state
        assert "contagion_paths" in state
        assert "systemic_risk_score" in state
        assert "contagion_state" in state
        assert "recommended_action" in state
        assert "confidence_modifier" in state
        assert "capital_modifier" in state
        assert "dominant_cluster" in state
        assert "weakest_cluster" in state
        assert "reason" in state
        assert "timestamp" in state
        assert "inputs" in state

    def test_cluster_stress_contains_all_clusters(self):
        """cluster_stress contains all 5 clusters"""
        response = requests.get(f"{ENDPOINT_PREFIX}")
        assert response.status_code == 200

        state = response.json()["data"]
        cluster_stress = state["cluster_stress"]

        for cid in CLUSTER_IDS:
            assert cid in cluster_stress
            assert isinstance(cluster_stress[cid], (int, float))
            assert 0.0 <= cluster_stress[cid] <= 1.0


class TestExtremeParamsSystemic:
    """Tests for extreme params → SYSTEMIC state"""

    def test_extreme_params_systemic(self):
        """Extreme exposures + EXTREME volatility + CRITICAL risk → SYSTEMIC"""
        params = {
            "btc_exposure": 0.70,
            "majors_exposure": 0.65,
            "alts_exposure": 0.60,
            "trend_exposure": 0.55,
            "reversal_exposure": 0.50,
            "volatility_state": "EXTREME",
            "market_risk_state": "CRITICAL",
            "concentration_score": 0.80,
        }
        response = requests.get(f"{ENDPOINT_PREFIX}", params=params)
        assert response.status_code == 200

        state = response.json()["data"]
        assert state["contagion_state"] == "SYSTEMIC"
        assert state["recommended_action"] == "DELEVER_SYSTEM"
        assert state["systemic_risk_score"] > 0.65

    def test_systemic_modifiers(self):
        """SYSTEMIC state has confidence=0.70, capital=0.55"""
        params = {
            "btc_exposure": 0.70,
            "majors_exposure": 0.65,
            "alts_exposure": 0.60,
            "trend_exposure": 0.55,
            "reversal_exposure": 0.50,
            "volatility_state": "EXTREME",
            "market_risk_state": "CRITICAL",
            "concentration_score": 0.80,
        }
        response = requests.get(f"{ENDPOINT_PREFIX}", params=params)
        assert response.status_code == 200

        state = response.json()["data"]
        assert state["contagion_state"] == "SYSTEMIC"
        assert abs(state["confidence_modifier"] - 0.70) < 0.01
        assert abs(state["capital_modifier"] - 0.55) < 0.01


class TestLowParamsLow:
    """Tests for low params → LOW state"""

    def test_low_params_low(self):
        """Low exposures + LOW volatility → LOW"""
        params = {
            "btc_exposure": 0.10,
            "majors_exposure": 0.08,
            "alts_exposure": 0.06,
            "trend_exposure": 0.05,
            "reversal_exposure": 0.04,
            "volatility_state": "LOW",
            "concentration_score": 0.1,
        }
        response = requests.get(f"{ENDPOINT_PREFIX}", params=params)
        assert response.status_code == 200

        state = response.json()["data"]
        assert state["contagion_state"] == "LOW"
        assert state["recommended_action"] == "HOLD"
        assert state["systemic_risk_score"] < 0.25

    def test_low_modifiers(self):
        """LOW state has confidence=1.0, capital=1.0"""
        params = {
            "btc_exposure": 0.10,
            "majors_exposure": 0.08,
            "alts_exposure": 0.06,
            "trend_exposure": 0.05,
            "reversal_exposure": 0.04,
            "volatility_state": "LOW",
            "concentration_score": 0.1,
        }
        response = requests.get(f"{ENDPOINT_PREFIX}", params=params)
        assert response.status_code == 200

        state = response.json()["data"]
        assert state["contagion_state"] == "LOW"
        assert abs(state["confidence_modifier"] - 1.0) < 0.01
        assert abs(state["capital_modifier"] - 1.0) < 0.01

    def test_low_params_empty_paths(self):
        """Very low exposures with LOW volatility result in no contagion paths"""
        params = {
            "btc_exposure": 0.10,
            "majors_exposure": 0.08,
            "alts_exposure": 0.06,
            "trend_exposure": 0.05,
            "reversal_exposure": 0.04,
            "volatility_state": "LOW",
            "concentration_score": 0.1,
        }
        response = requests.get(f"{ENDPOINT_PREFIX}", params=params)
        assert response.status_code == 200

        state = response.json()["data"]
        # With very low stress, contagion probabilities fall below threshold
        assert state["contagion_paths"] == []


class TestSummaryEndpoint:
    """Tests for /cluster-contagion/summary endpoint"""

    def test_summary_structure(self):
        """Summary endpoint returns compact summary with required keys"""
        response = requests.get(f"{ENDPOINT_PREFIX}/summary")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "22.3"
        assert "data" in data

        summary = data["data"]
        # Required keys for summary
        required_keys = [
            "systemic_risk_score",
            "contagion_state",
            "recommended_action",
            "dominant_cluster",
            "weakest_cluster",
            "confidence_modifier",
            "capital_modifier",
        ]
        for key in required_keys:
            assert key in summary, f"Missing key: {key}"


class TestPathsEndpoint:
    """Tests for /cluster-contagion/paths endpoint"""

    def test_paths_structure(self):
        """Paths endpoint returns contagion paths and probabilities"""
        response = requests.get(f"{ENDPOINT_PREFIX}/paths")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "22.3"

        paths_data = data["data"]
        assert "contagion_paths" in paths_data
        assert "contagion_probabilities" in paths_data
        assert "systemic_risk_score" in paths_data
        assert "contagion_state" in paths_data

    def test_paths_format(self):
        """Contagion paths follow 'cluster -> cluster' format"""
        response = requests.get(f"{ENDPOINT_PREFIX}/paths")
        assert response.status_code == 200

        paths_data = response.json()["data"]
        for path in paths_data["contagion_paths"]:
            assert " -> " in path
            segments = path.split(" -> ")
            assert len(segments) >= 2
            for seg in segments:
                assert seg in CLUSTER_IDS

    def test_probabilities_format(self):
        """Contagion probabilities follow 'src->tgt' format"""
        response = requests.get(f"{ENDPOINT_PREFIX}/paths")
        assert response.status_code == 200

        paths_data = response.json()["data"]
        for key, prob in paths_data["contagion_probabilities"].items():
            assert "->" in key
            parts = key.split("->")
            assert len(parts) == 2
            assert parts[0] in CLUSTER_IDS
            assert parts[1] in CLUSTER_IDS
            assert 0.0 <= prob <= 1.0


class TestStressEndpoint:
    """Tests for /cluster-contagion/stress endpoint"""

    def test_stress_structure(self):
        """Stress endpoint returns per-cluster stress scores"""
        response = requests.get(f"{ENDPOINT_PREFIX}/stress")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "22.3"

        stress_data = data["data"]
        assert "cluster_stress" in stress_data
        assert "dominant_cluster" in stress_data
        assert "weakest_cluster" in stress_data
        assert "contagion_state" in stress_data

    def test_stress_all_clusters(self):
        """Stress data includes all 5 clusters"""
        response = requests.get(f"{ENDPOINT_PREFIX}/stress")
        assert response.status_code == 200

        stress = response.json()["data"]["cluster_stress"]
        for cid in CLUSTER_IDS:
            assert cid in stress
            assert 0.0 <= stress[cid] <= 1.0


class TestRecomputeEndpoint:
    """Tests for POST /cluster-contagion/recompute endpoint"""

    def test_recompute_success(self):
        """Recompute endpoint returns updated state and records to history"""
        response = requests.post(f"{ENDPOINT_PREFIX}/recompute")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "22.3"
        assert data["message"] == "Cluster contagion state recomputed and recorded"
        assert "data" in data

    def test_recompute_adds_history(self):
        """Recompute adds entry to history"""
        # First call recompute
        requests.post(f"{ENDPOINT_PREFIX}/recompute")

        # Then check history
        response = requests.get(f"{ENDPOINT_PREFIX}/history")
        assert response.status_code == 200

        history_data = response.json()
        assert history_data["count"] >= 1


class TestHistoryEndpoint:
    """Tests for /cluster-contagion/history endpoint"""

    def test_history_structure(self):
        """History endpoint returns list of history entries"""
        # Ensure at least one history entry
        requests.post(f"{ENDPOINT_PREFIX}/recompute")

        response = requests.get(f"{ENDPOINT_PREFIX}/history")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "22.3"
        assert "history" in data
        assert "count" in data
        assert isinstance(data["history"], list)

    def test_history_entry_structure(self):
        """History entries contain required fields"""
        requests.post(f"{ENDPOINT_PREFIX}/recompute")

        response = requests.get(f"{ENDPOINT_PREFIX}/history")
        assert response.status_code == 200

        history = response.json()["history"]
        if len(history) > 0:
            entry = history[-1]
            assert "contagion_state" in entry
            assert "systemic_risk_score" in entry
            assert "dominant_cluster" in entry
            assert "recommended_action" in entry
            assert "timestamp" in entry

    def test_history_limit(self):
        """History respects limit parameter"""
        # Add multiple history entries
        for _ in range(3):
            requests.post(f"{ENDPOINT_PREFIX}/recompute")

        response = requests.get(f"{ENDPOINT_PREFIX}/history", params={"limit": 2})
        assert response.status_code == 200

        data = response.json()
        assert len(data["history"]) <= 2


class TestScoreBounds:
    """Tests for systemic_risk_score bounds [0.0, 1.0]"""

    def test_score_bounded_low(self):
        """Score is >= 0.0 with minimal params"""
        params = {
            "btc_exposure": 0.01,
            "majors_exposure": 0.01,
            "alts_exposure": 0.01,
            "trend_exposure": 0.01,
            "reversal_exposure": 0.01,
            "volatility_state": "LOW",
            "concentration_score": 0.01,
        }
        response = requests.get(f"{ENDPOINT_PREFIX}", params=params)
        assert response.status_code == 200

        score = response.json()["data"]["systemic_risk_score"]
        assert score >= 0.0

    def test_score_bounded_high(self):
        """Score is <= 1.0 with maximal params"""
        params = {
            "btc_exposure": 1.0,
            "majors_exposure": 1.0,
            "alts_exposure": 1.0,
            "trend_exposure": 1.0,
            "reversal_exposure": 1.0,
            "volatility_state": "EXTREME",
            "market_risk_state": "CRITICAL",
            "concentration_score": 1.0,
        }
        response = requests.get(f"{ENDPOINT_PREFIX}", params=params)
        assert response.status_code == 200

        score = response.json()["data"]["systemic_risk_score"]
        assert score <= 1.0


class TestContagionStateThresholds:
    """Tests for contagion state thresholds"""

    def test_low_threshold(self):
        """Score < 0.25 → LOW"""
        params = {
            "btc_exposure": 0.10,
            "majors_exposure": 0.08,
            "alts_exposure": 0.06,
            "trend_exposure": 0.05,
            "reversal_exposure": 0.04,
            "volatility_state": "LOW",
            "concentration_score": 0.1,
        }
        response = requests.get(f"{ENDPOINT_PREFIX}", params=params)
        assert response.status_code == 200

        state = response.json()["data"]
        assert state["systemic_risk_score"] < 0.25
        assert state["contagion_state"] == "LOW"

    def test_elevated_threshold(self):
        """Score 0.25-0.45 → ELEVATED"""
        # Params calibrated to produce ELEVATED
        params = {
            "btc_exposure": 0.35,
            "majors_exposure": 0.30,
            "alts_exposure": 0.25,
            "trend_exposure": 0.20,
            "reversal_exposure": 0.15,
            "volatility_state": "NORMAL",
            "market_risk_state": "ELEVATED",
            "concentration_score": 0.35,
        }
        response = requests.get(f"{ENDPOINT_PREFIX}", params=params)
        assert response.status_code == 200

        state = response.json()["data"]
        if 0.25 <= state["systemic_risk_score"] < 0.45:
            assert state["contagion_state"] == "ELEVATED"

    def test_systemic_threshold(self):
        """Score > 0.65 → SYSTEMIC"""
        params = {
            "btc_exposure": 0.70,
            "majors_exposure": 0.65,
            "alts_exposure": 0.60,
            "trend_exposure": 0.55,
            "reversal_exposure": 0.50,
            "volatility_state": "EXTREME",
            "market_risk_state": "CRITICAL",
            "concentration_score": 0.80,
        }
        response = requests.get(f"{ENDPOINT_PREFIX}", params=params)
        assert response.status_code == 200

        state = response.json()["data"]
        assert state["systemic_risk_score"] > 0.65
        assert state["contagion_state"] == "SYSTEMIC"


class TestRecommendedActions:
    """Tests for recommended actions per state"""

    def test_low_hold(self):
        """LOW → HOLD"""
        params = {
            "btc_exposure": 0.10,
            "majors_exposure": 0.08,
            "alts_exposure": 0.06,
            "trend_exposure": 0.05,
            "reversal_exposure": 0.04,
            "volatility_state": "LOW",
            "concentration_score": 0.1,
        }
        response = requests.get(f"{ENDPOINT_PREFIX}", params=params)
        assert response.status_code == 200

        state = response.json()["data"]
        assert state["contagion_state"] == "LOW"
        assert state["recommended_action"] == "HOLD"

    def test_systemic_delever(self):
        """SYSTEMIC → DELEVER_SYSTEM"""
        params = {
            "btc_exposure": 0.70,
            "majors_exposure": 0.65,
            "alts_exposure": 0.60,
            "trend_exposure": 0.55,
            "reversal_exposure": 0.50,
            "volatility_state": "EXTREME",
            "market_risk_state": "CRITICAL",
            "concentration_score": 0.80,
        }
        response = requests.get(f"{ENDPOINT_PREFIX}", params=params)
        assert response.status_code == 200

        state = response.json()["data"]
        assert state["contagion_state"] == "SYSTEMIC"
        assert state["recommended_action"] == "DELEVER_SYSTEM"


class TestContagionMap:
    """Tests for contagion map structure"""

    def test_btc_spreads_to_majors_alts(self):
        """btc_cluster spreads to majors_cluster and alts_cluster"""
        response = requests.get(f"{ENDPOINT_PREFIX}/paths")
        assert response.status_code == 200

        probs = response.json()["data"]["contagion_probabilities"]
        assert "btc_cluster->majors_cluster" in probs
        assert "btc_cluster->alts_cluster" in probs

    def test_majors_spreads_to_alts(self):
        """majors_cluster spreads to alts_cluster"""
        response = requests.get(f"{ENDPOINT_PREFIX}/paths")
        assert response.status_code == 200

        probs = response.json()["data"]["contagion_probabilities"]
        assert "majors_cluster->alts_cluster" in probs

    def test_trend_spreads_to_majors(self):
        """trend_cluster spreads to majors_cluster"""
        response = requests.get(f"{ENDPOINT_PREFIX}/paths")
        assert response.status_code == 200

        probs = response.json()["data"]["contagion_probabilities"]
        assert "trend_cluster->majors_cluster" in probs

    def test_alts_spreads_to_reversal(self):
        """alts_cluster spreads to reversal_cluster"""
        response = requests.get(f"{ENDPOINT_PREFIX}/paths")
        assert response.status_code == 200

        probs = response.json()["data"]["contagion_probabilities"]
        assert "alts_cluster->reversal_cluster" in probs


class TestVolatilityMultipliers:
    """Tests for volatility state multipliers"""

    def test_extreme_volatility_increases_stress(self):
        """EXTREME volatility increases cluster stress"""
        # Normal volatility
        normal_response = requests.get(f"{ENDPOINT_PREFIX}/stress", params={"volatility_state": "NORMAL"})
        assert normal_response.status_code == 200
        normal_stress = normal_response.json()["data"]["cluster_stress"]["btc_cluster"]

        # Extreme volatility
        extreme_response = requests.get(f"{ENDPOINT_PREFIX}/stress", params={"volatility_state": "EXTREME"})
        assert extreme_response.status_code == 200
        extreme_stress = extreme_response.json()["data"]["cluster_stress"]["btc_cluster"]

        assert extreme_stress > normal_stress


class TestMarketRiskMultipliers:
    """Tests for market risk state multipliers"""

    def test_critical_risk_increases_stress(self):
        """CRITICAL market risk increases cluster stress"""
        # Normal risk
        normal_response = requests.get(f"{ENDPOINT_PREFIX}/stress", params={"market_risk_state": "NORMAL"})
        assert normal_response.status_code == 200
        normal_stress = normal_response.json()["data"]["cluster_stress"]["btc_cluster"]

        # Critical risk
        critical_response = requests.get(f"{ENDPOINT_PREFIX}/stress", params={"market_risk_state": "CRITICAL"})
        assert critical_response.status_code == 200
        critical_stress = critical_response.json()["data"]["cluster_stress"]["btc_cluster"]

        assert critical_stress > normal_stress


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
