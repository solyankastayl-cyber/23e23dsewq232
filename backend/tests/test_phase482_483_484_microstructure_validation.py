"""
Test Suite for Phase 4.8.2, 4.8.3, 4.8.4 — Microstructure Validation & Weighting

Phase 4.8.2: Microstructure A/B Validation
Phase 4.8.3: Microstructure Weighting (size, confidence, execution modifiers)
Phase 4.8.4: A/B/C Weighting Validation (Base vs Filter vs Weighting)

Tests cover:
- Health endpoints for all three phases
- Validation run endpoints with expected response structure
- Weighting evaluation with strong/weak/blocked micro contexts
- A/B/C comparison with verdict system
- History and latest result endpoints
- Backward compatibility with existing Phase 4.7/4.8 endpoints
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


class TestPhase482MicrostructureValidation:
    """Phase 4.8.2 — Microstructure A/B Validation Tests"""

    def test_validation_health(self):
        """Test validation health endpoint returns ok:true and version 4.8.2"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/microstructure/validate/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Health check should return ok:true"
        assert data.get("version") == "4.8.2", f"Expected version 4.8.2, got {data.get('version')}"
        assert data.get("module") == "micro_backtest_validation"
        print(f"✓ Validation health: version={data.get('version')}, runs={data.get('runs')}")

    def test_validation_run(self):
        """Test validation run with n_trades=200, seed=42"""
        response = requests.post(
            f"{BASE_URL}/api/entry-timing/microstructure/validate/run",
            json={"n_trades": 200, "seed": 42}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Run should return ok:true"
        assert data.get("n_trades") == 200
        assert data.get("seed") == 42
        
        # Check base_metrics structure
        base_metrics = data.get("base_metrics", {})
        assert "win_rate" in base_metrics, "base_metrics should have win_rate"
        assert "pnl" in base_metrics, "base_metrics should have pnl"
        assert "wrong_early_rate" in base_metrics, "base_metrics should have wrong_early_rate"
        assert "stop_out_rate" in base_metrics, "base_metrics should have stop_out_rate"
        
        # Check micro_metrics structure
        micro_metrics = data.get("micro_metrics", {})
        assert "win_rate" in micro_metrics, "micro_metrics should have win_rate"
        assert "pnl" in micro_metrics, "micro_metrics should have pnl"
        
        # Check comparison structure
        comparison = data.get("comparison", {})
        assert "win_rate_delta" in comparison, "comparison should have win_rate_delta"
        assert "pnl_delta" in comparison, "comparison should have pnl_delta"
        assert "wrong_early_delta" in comparison, "comparison should have wrong_early_delta"
        
        # Check impact structure
        impact = data.get("impact", {})
        assert "avoided_bad_trades" in impact, "impact should have avoided_bad_trades"
        assert "missed_good_trades" in impact, "impact should have missed_good_trades"
        assert "net_edge" in impact, "impact should have net_edge"
        
        # Check validation structure
        validation = data.get("validation", {})
        assert "passed" in validation, "validation should have passed"
        assert "checks" in validation, "validation should have checks"
        
        print(f"✓ Validation run: base_win_rate={base_metrics.get('win_rate')}, micro_win_rate={micro_metrics.get('win_rate')}")
        print(f"  Impact: avoided={impact.get('avoided_bad_trades')}, missed={impact.get('missed_good_trades')}, net_edge={impact.get('net_edge')}")

    def test_validation_checks(self):
        """Test validation checks: wrong_early_improved, stop_out_improved, net_edge_positive, missed_good_controlled"""
        response = requests.post(
            f"{BASE_URL}/api/entry-timing/microstructure/validate/run",
            json={"n_trades": 200, "seed": 42}
        )
        assert response.status_code == 200
        
        data = response.json()
        validation = data.get("validation", {})
        checks = validation.get("checks", {})
        
        # Verify all expected checks are present
        expected_checks = ["wrong_early_improved", "stop_out_improved", "net_edge_positive", "missed_good_controlled"]
        for check in expected_checks:
            assert check in checks, f"validation.checks should have {check}"
            print(f"  {check}: {checks.get(check)}")
        
        # With seed=42, micro should improve over base
        assert checks.get("wrong_early_improved") is True, "wrong_early should be improved"
        assert checks.get("stop_out_improved") is True, "stop_out should be improved"
        assert checks.get("net_edge_positive") is True, "net_edge should be positive"
        assert checks.get("missed_good_controlled") is True, "missed_good should be controlled"
        
        print(f"✓ Validation checks all passed: {validation.get('summary')}")

    def test_validation_latest(self):
        """Test latest validation result endpoint"""
        # First run a validation
        requests.post(
            f"{BASE_URL}/api/entry-timing/microstructure/validate/run",
            json={"n_trades": 100, "seed": 123}
        )
        
        response = requests.get(f"{BASE_URL}/api/entry-timing/microstructure/validate/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("ok") is True
        assert "base_metrics" in data or "message" in data
        print(f"✓ Latest validation result retrieved")

    def test_validation_history(self):
        """Test validation history endpoint"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/microstructure/validate/history")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("ok") is True
        assert "history" in data
        assert "count" in data
        assert isinstance(data.get("history"), list)
        print(f"✓ Validation history: count={data.get('count')}")


class TestPhase483MicrostructureWeighting:
    """Phase 4.8.3 — Microstructure Weighting Tests"""

    def test_weighting_health(self):
        """Test weighting health endpoint returns ok:true and version 4.8.3"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/microstructure/weight/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Health check should return ok:true"
        assert data.get("version") == "4.8.3", f"Expected version 4.8.3, got {data.get('version')}"
        assert data.get("module") == "micro_weighting"
        assert "size_modifier" in data.get("components", [])
        assert "confidence_modifier" in data.get("components", [])
        assert "execution_modifier" in data.get("components", [])
        print(f"✓ Weighting health: version={data.get('version')}, components={data.get('components')}")

    def test_weighting_strong_micro(self):
        """Test weighting with strong micro: size_multiplier=1.15, execution_modifier=AGGRESSIVE, weighted_decision=GO_FULL"""
        payload = {
            "prediction": {"confidence": 0.75},
            "microstructure": {
                "entry_permission": True,
                "microstructure_score": 0.85,
                "liquidity_risk": 0.2,
                "sweep_risk": 0.15,
                "absorption_detected": True,
                "imbalance": "bullish",
                "imbalance_supportive": True,
                "decision": "ENTER_NOW"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/entry-timing/microstructure/weight/evaluate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True
        assert data.get("size_multiplier") == 1.15, f"Expected size_multiplier=1.15, got {data.get('size_multiplier')}"
        assert data.get("execution_modifier") == "AGGRESSIVE", f"Expected AGGRESSIVE, got {data.get('execution_modifier')}"
        assert data.get("weighted_decision") == "GO_FULL", f"Expected GO_FULL, got {data.get('weighted_decision')}"
        
        print(f"✓ Strong micro: size={data.get('size_multiplier')}, exec={data.get('execution_modifier')}, decision={data.get('weighted_decision')}")

    def test_weighting_weak_micro(self):
        """Test weighting with weak micro: size_multiplier<=0.8, execution_modifier=PASSIVE_LIMIT, weighted_decision=GO_REDUCED"""
        payload = {
            "prediction": {"confidence": 0.55},
            "microstructure": {
                "entry_permission": True,
                "microstructure_score": 0.45,
                "liquidity_risk": 0.55,
                "sweep_risk": 0.5,
                "absorption_detected": False,
                "imbalance": "neutral",
                "imbalance_supportive": False,
                "decision": "ENTER_NOW"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/entry-timing/microstructure/weight/evaluate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True
        assert data.get("size_multiplier") <= 0.8, f"Expected size_multiplier<=0.8, got {data.get('size_multiplier')}"
        assert data.get("execution_modifier") == "PASSIVE_LIMIT", f"Expected PASSIVE_LIMIT, got {data.get('execution_modifier')}"
        assert data.get("weighted_decision") == "GO_REDUCED", f"Expected GO_REDUCED, got {data.get('weighted_decision')}"
        
        print(f"✓ Weak micro: size={data.get('size_multiplier')}, exec={data.get('execution_modifier')}, decision={data.get('weighted_decision')}")

    def test_weighting_blocked_micro(self):
        """Test weighting with blocked micro (entry_permission=false): size_multiplier=0.0, weighted_decision=SKIP or WAIT_MICROSTRUCTURE"""
        payload = {
            "prediction": {"confidence": 0.7},
            "microstructure": {
                "entry_permission": False,
                "microstructure_score": 0.3,
                "liquidity_risk": 0.8,
                "sweep_risk": 0.75,
                "absorption_detected": False,
                "imbalance": "bearish",
                "imbalance_supportive": False,
                "decision": "WAIT_SWEEP"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/entry-timing/microstructure/weight/evaluate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True
        assert data.get("size_multiplier") == 0.0, f"Expected size_multiplier=0.0, got {data.get('size_multiplier')}"
        assert data.get("weighted_decision") in ["SKIP", "WAIT_MICROSTRUCTURE"], f"Expected SKIP or WAIT_MICROSTRUCTURE, got {data.get('weighted_decision')}"
        
        print(f"✓ Blocked micro: size={data.get('size_multiplier')}, decision={data.get('weighted_decision')}")

    def test_weighting_stats(self):
        """Test weighting stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/microstructure/weight/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("ok") is True
        assert "total" in data
        print(f"✓ Weighting stats: total={data.get('total')}")


class TestPhase484ABCWeightingValidation:
    """Phase 4.8.4 — A/B/C Weighting Validation Tests"""

    def test_abc_validation_health(self):
        """Test A/B/C validation health endpoint returns ok:true and version 4.8.4"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/microstructure/weighting/validate/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Health check should return ok:true"
        assert data.get("version") == "4.8.4", f"Expected version 4.8.4, got {data.get('version')}"
        assert data.get("module") == "micro_weighting_ab_validation"
        print(f"✓ A/B/C validation health: version={data.get('version')}, runs={data.get('runs')}")

    def test_abc_validation_run(self):
        """Test A/B/C validation run with n_trades=200, seed=42"""
        response = requests.post(
            f"{BASE_URL}/api/entry-timing/microstructure/weighting/validate/run",
            json={"n_trades": 200, "seed": 42}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Run should return ok:true"
        assert data.get("n_trades") == 200
        assert data.get("seed") == 42
        
        # Check all three metrics sets
        assert "base_metrics" in data, "Should have base_metrics"
        assert "filter_metrics" in data, "Should have filter_metrics"
        assert "weighting_metrics" in data, "Should have weighting_metrics"
        
        base_metrics = data.get("base_metrics", {})
        filter_metrics = data.get("filter_metrics", {})
        weighting_metrics = data.get("weighting_metrics", {})
        
        # Verify metrics structure
        for name, metrics in [("base", base_metrics), ("filter", filter_metrics), ("weighting", weighting_metrics)]:
            assert "win_rate" in metrics, f"{name}_metrics should have win_rate"
            assert "pnl" in metrics, f"{name}_metrics should have pnl"
        
        print(f"✓ A/B/C run: base_wr={base_metrics.get('win_rate')}, filter_wr={filter_metrics.get('win_rate')}, weight_wr={weighting_metrics.get('win_rate')}")

    def test_abc_comparison_structure(self):
        """Test comparison has filter_vs_base, weighting_vs_filter, weighting_vs_base sections"""
        response = requests.post(
            f"{BASE_URL}/api/entry-timing/microstructure/weighting/validate/run",
            json={"n_trades": 200, "seed": 42}
        )
        assert response.status_code == 200
        
        data = response.json()
        comparison = data.get("comparison", {})
        
        assert "filter_vs_base" in comparison, "comparison should have filter_vs_base"
        assert "weighting_vs_filter" in comparison, "comparison should have weighting_vs_filter"
        assert "weighting_vs_base" in comparison, "comparison should have weighting_vs_base"
        
        # Check delta fields
        for section_name in ["filter_vs_base", "weighting_vs_filter", "weighting_vs_base"]:
            section = comparison.get(section_name, {})
            assert "win_rate_delta" in section, f"{section_name} should have win_rate_delta"
            assert "pnl_delta" in section, f"{section_name} should have pnl_delta"
        
        print(f"✓ Comparison structure verified with all three sections")

    def test_abc_impact_structure(self):
        """Test impact has filter and weighting sections with avoided/missed/net_edge and upgraded_size_wins/oversized_losses"""
        response = requests.post(
            f"{BASE_URL}/api/entry-timing/microstructure/weighting/validate/run",
            json={"n_trades": 200, "seed": 42}
        )
        assert response.status_code == 200
        
        data = response.json()
        impact = data.get("impact", {})
        
        # Check filter section
        filter_impact = impact.get("filter", {})
        assert "avoided_bad_trades" in filter_impact, "filter impact should have avoided_bad_trades"
        assert "missed_good_trades" in filter_impact, "filter impact should have missed_good_trades"
        assert "net_edge" in filter_impact, "filter impact should have net_edge"
        
        # Check weighting section
        weighting_impact = impact.get("weighting", {})
        assert "avoided_bad_trades" in weighting_impact, "weighting impact should have avoided_bad_trades"
        assert "missed_good_trades" in weighting_impact, "weighting impact should have missed_good_trades"
        assert "net_edge" in weighting_impact, "weighting impact should have net_edge"
        assert "upgraded_size_wins" in weighting_impact, "weighting impact should have upgraded_size_wins"
        assert "oversized_losses" in weighting_impact, "weighting impact should have oversized_losses"
        
        print(f"✓ Impact structure: filter_net_edge={filter_impact.get('net_edge')}, weighting_net_edge={weighting_impact.get('net_edge')}")
        print(f"  upgraded_wins={weighting_impact.get('upgraded_size_wins')}, oversized_losses={weighting_impact.get('oversized_losses')}")

    def test_abc_verdict(self):
        """Test verdict is CASE_1_IDEAL or CASE_2_GOOD with recommendation KEEP_WEIGHTING"""
        response = requests.post(
            f"{BASE_URL}/api/entry-timing/microstructure/weighting/validate/run",
            json={"n_trades": 200, "seed": 42}
        )
        assert response.status_code == 200
        
        data = response.json()
        verdict = data.get("verdict", {})
        
        assert "case" in verdict, "verdict should have case"
        assert "recommendation" in verdict, "verdict should have recommendation"
        assert "description" in verdict, "verdict should have description"
        
        # With seed=42, expect CASE_1_IDEAL or CASE_2_GOOD
        valid_cases = ["CASE_1_IDEAL", "CASE_2_GOOD"]
        assert verdict.get("case") in valid_cases, f"Expected {valid_cases}, got {verdict.get('case')}"
        assert verdict.get("recommendation") == "KEEP_WEIGHTING", f"Expected KEEP_WEIGHTING, got {verdict.get('recommendation')}"
        
        print(f"✓ Verdict: case={verdict.get('case')}, recommendation={verdict.get('recommendation')}")

    def test_abc_latest(self):
        """Test latest A/B/C validation result endpoint"""
        # First run a validation
        requests.post(
            f"{BASE_URL}/api/entry-timing/microstructure/weighting/validate/run",
            json={"n_trades": 100, "seed": 456}
        )
        
        response = requests.get(f"{BASE_URL}/api/entry-timing/microstructure/weighting/validate/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("ok") is True
        print(f"✓ Latest A/B/C validation result retrieved")

    def test_abc_history(self):
        """Test A/B/C validation history endpoint"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/microstructure/weighting/validate/history")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("ok") is True
        assert "history" in data
        assert "count" in data
        assert isinstance(data.get("history"), list)
        print(f"✓ A/B/C validation history: count={data.get('count')}")


class TestBackwardCompatibility:
    """Test backward compatibility with existing Phase 4.7 and 4.8 endpoints"""

    def test_phase48_microstructure_health(self):
        """Test existing Phase 4.8 microstructure health endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/microstructure/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True
        assert data.get("version") == "4.8"
        print(f"✓ Phase 4.8 microstructure health: version={data.get('version')}")

    def test_phase48_mock_supportive(self):
        """Test existing Phase 4.8 mock supportive endpoint still works"""
        response = requests.post(f"{BASE_URL}/api/entry-timing/microstructure/evaluate/mock/supportive")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True
        assert data.get("entry_permission") is True
        assert data.get("decision") == "ENTER_NOW"
        print(f"✓ Phase 4.8 mock supportive: decision={data.get('decision')}")

    def test_phase47_mtf_health(self):
        """Test existing Phase 4.7 MTF health endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/mtf/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True
        assert data.get("version") == "4.7"
        print(f"✓ Phase 4.7 MTF health: version={data.get('version')}")

    def test_phase45_integration_health(self):
        """Test existing Phase 4.5 Integration health endpoint still works (version 4.8.1)"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/integration/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True
        # Integration was updated to 4.8.1 with microstructure support
        assert data.get("version") == "4.8.1", f"Expected version 4.8.1, got {data.get('version')}"
        print(f"✓ Phase 4.5 Integration health: version={data.get('version')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
