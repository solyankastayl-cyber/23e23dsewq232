"""
PHASE 4.8 + 4.8.1 — Microstructure Entry Layer Tests

Tests for:
- Microstructure Entry Layer (Phase 4.8)
- Integration Layer with Microstructure support (Phase 4.8.1)
- Backward compatibility with Phase 4.1-4.7 endpoints
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestMicrostructureHealth:
    """Phase 4.8 - Microstructure Health Check"""

    def test_microstructure_health(self):
        """GET /api/entry-timing/microstructure/health - should return ok:true, 5 engines"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/microstructure/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Health check should return ok:true"
        assert data.get("module") == "microstructure_entry", "Module should be microstructure_entry"
        assert data.get("version") == "4.8", "Version should be 4.8"
        
        engines = data.get("engines", [])
        assert len(engines) == 5, f"Expected 5 engines, got {len(engines)}"
        expected_engines = ["liquidity", "orderbook", "imbalance", "absorption", "sweep"]
        for eng in expected_engines:
            assert eng in engines, f"Engine {eng} should be in engines list"
        
        print(f"✓ Microstructure health check passed - 5 engines: {engines}")


class TestMicrostructureMockScenarios:
    """Phase 4.8 - Mock Scenario Evaluations"""

    def test_mock_supportive(self):
        """POST /api/entry-timing/microstructure/evaluate/mock/supportive - ENTER_NOW, permission:true, score >= 0.75"""
        response = requests.post(f"{BASE_URL}/api/entry-timing/microstructure/evaluate/mock/supportive")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        assert data.get("scenario") == "supportive", "Scenario should be supportive"
        assert data.get("decision") == "ENTER_NOW", f"Expected ENTER_NOW, got {data.get('decision')}"
        assert data.get("entry_permission") is True, "entry_permission should be True"
        
        score = data.get("microstructure_score", 0)
        assert score >= 0.75, f"Score should be >= 0.75, got {score}"
        
        print(f"✓ Supportive scenario: decision={data.get('decision')}, score={score}, permission={data.get('entry_permission')}")

    def test_mock_hostile_spread(self):
        """POST /api/entry-timing/microstructure/evaluate/mock/hostile_spread - SKIP_HOSTILE_SPREAD, permission:false"""
        response = requests.post(f"{BASE_URL}/api/entry-timing/microstructure/evaluate/mock/hostile_spread")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        assert data.get("decision") == "SKIP_HOSTILE_SPREAD", f"Expected SKIP_HOSTILE_SPREAD, got {data.get('decision')}"
        assert data.get("entry_permission") is False, "entry_permission should be False"
        
        print(f"✓ Hostile spread scenario: decision={data.get('decision')}, permission={data.get('entry_permission')}")

    def test_mock_sweep_risk(self):
        """POST /api/entry-timing/microstructure/evaluate/mock/sweep_risk - WAIT_SWEEP, permission:false, sweep_risk >= 0.7"""
        response = requests.post(f"{BASE_URL}/api/entry-timing/microstructure/evaluate/mock/sweep_risk")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        assert data.get("decision") == "WAIT_SWEEP", f"Expected WAIT_SWEEP, got {data.get('decision')}"
        assert data.get("entry_permission") is False, "entry_permission should be False"
        
        sweep_risk = data.get("sweep_risk", 0)
        assert sweep_risk >= 0.7, f"sweep_risk should be >= 0.7, got {sweep_risk}"
        
        print(f"✓ Sweep risk scenario: decision={data.get('decision')}, sweep_risk={sweep_risk}")

    def test_mock_liquidity_cluster(self):
        """POST /api/entry-timing/microstructure/evaluate/mock/liquidity_cluster - WAIT_LIQUIDITY_CLEAR, permission:false, liquidity_risk >= 0.7"""
        response = requests.post(f"{BASE_URL}/api/entry-timing/microstructure/evaluate/mock/liquidity_cluster")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        assert data.get("decision") == "WAIT_LIQUIDITY_CLEAR", f"Expected WAIT_LIQUIDITY_CLEAR, got {data.get('decision')}"
        assert data.get("entry_permission") is False, "entry_permission should be False"
        
        liquidity_risk = data.get("liquidity_risk", 0)
        assert liquidity_risk >= 0.7, f"liquidity_risk should be >= 0.7, got {liquidity_risk}"
        
        print(f"✓ Liquidity cluster scenario: decision={data.get('decision')}, liquidity_risk={liquidity_risk}")


class TestMicrostructureFullEvaluation:
    """Phase 4.8 - Full Custom Input Evaluation"""

    def test_full_evaluation(self):
        """POST /api/entry-timing/microstructure/evaluate - full custom input evaluation"""
        payload = {
            "symbol": "ETHUSDT",
            "side": "LONG",
            "price": 3500.0,
            "orderbook": {
                "bid_depth": 1000000,
                "ask_depth": 900000,
                "best_bid": 3499.5,
                "best_ask": 3500.0,
                "spread_bps": 2.5
            },
            "liquidity": {
                "above_liquidity": 0.6,
                "below_liquidity": 0.4,
                "local_cluster_nearby": False,
                "cluster_distance_bps": 20.0
            },
            "flow": {
                "buy_pressure": 0.65,
                "sell_pressure": 0.35,
                "recent_sweep_up": False,
                "recent_sweep_down": True
            },
            "execution_context": {
                "entry_type": "pullback",
                "expected_slippage_bps": 3.0,
                "volatility_state": "normal"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/entry-timing/microstructure/evaluate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        assert "decision" in data, "Response should contain decision"
        assert "entry_permission" in data, "Response should contain entry_permission"
        assert "microstructure_score" in data, "Response should contain microstructure_score"
        assert "components" in data, "Response should contain components"
        
        components = data.get("components", {})
        assert "liquidity" in components, "Components should contain liquidity"
        assert "orderbook" in components, "Components should contain orderbook"
        assert "imbalance" in components, "Components should contain imbalance"
        assert "absorption" in components, "Components should contain absorption"
        assert "sweep" in components, "Components should contain sweep"
        
        print(f"✓ Full evaluation: decision={data.get('decision')}, score={data.get('microstructure_score')}, permission={data.get('entry_permission')}")


class TestMicrostructureScenarios:
    """Phase 4.8 - Scenarios and Simulation"""

    def test_list_scenarios(self):
        """GET /api/entry-timing/microstructure/scenarios - should list 4 scenarios"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/microstructure/scenarios")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        
        scenarios = data.get("scenarios", [])
        assert len(scenarios) == 4, f"Expected 4 scenarios, got {len(scenarios)}"
        
        scenario_names = [s.get("name") for s in scenarios]
        expected_names = ["supportive", "hostile_spread", "sweep_risk", "liquidity_cluster"]
        for name in expected_names:
            assert name in scenario_names, f"Scenario {name} should be in list"
        
        print(f"✓ Scenarios list: {scenario_names}")

    def test_simulate_all(self):
        """POST /api/entry-timing/microstructure/simulate/all - should return results for all 4 scenarios"""
        response = requests.post(f"{BASE_URL}/api/entry-timing/microstructure/simulate/all")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        
        results = data.get("results", {})
        assert len(results) == 4, f"Expected 4 results, got {len(results)}"
        
        expected_scenarios = ["supportive", "hostile_spread", "sweep_risk", "liquidity_cluster"]
        for scenario in expected_scenarios:
            assert scenario in results, f"Results should contain {scenario}"
            assert "decision" in results[scenario], f"{scenario} should have decision"
        
        print(f"✓ Simulate all: {list(results.keys())}")


class TestMicrostructureStatsHistory:
    """Phase 4.8 - Stats and History"""

    def test_get_stats(self):
        """GET /api/entry-timing/microstructure/stats - should return statistics"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/microstructure/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        assert "total" in data, "Stats should contain total"
        assert "by_decision" in data, "Stats should contain by_decision"
        
        print(f"✓ Stats: total={data.get('total')}, by_decision={data.get('by_decision')}")

    def test_get_history(self):
        """GET /api/entry-timing/microstructure/history - should return history entries"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/microstructure/history")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        assert "history" in data, "Response should contain history"
        assert "count" in data, "Response should contain count"
        
        # After running mock scenarios, history should have entries
        history = data.get("history", [])
        count = data.get("count", 0)
        assert count >= 0, "Count should be non-negative"
        
        print(f"✓ History: count={count}, entries={len(history)}")


class TestIntegrationWithMicrostructure:
    """Phase 4.8.1 - Integration Layer with Microstructure Support"""

    def test_integration_health(self):
        """GET /api/entry-timing/integration/health - should show version 4.8.1 and microstructure feature"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/integration/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        assert data.get("version") == "4.8.1", f"Expected version 4.8.1, got {data.get('version')}"
        
        features = data.get("features", [])
        assert "microstructure" in features, "Features should include microstructure"
        assert "mtf" in features, "Features should include mtf"
        assert "timing" in features, "Features should include timing"
        
        print(f"✓ Integration health: version={data.get('version')}, features={features}")

    def test_integration_decisions(self):
        """GET /api/entry-timing/integration/decisions - should include GO_FULL and WAIT_MICROSTRUCTURE"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/integration/decisions")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        
        decisions = data.get("decisions", [])
        assert "GO_FULL" in decisions, "Decisions should include GO_FULL"
        assert "WAIT_MICROSTRUCTURE" in decisions, "Decisions should include WAIT_MICROSTRUCTURE"
        assert "GO" in decisions, "Decisions should include GO"
        assert "GO_REDUCED" in decisions, "Decisions should include GO_REDUCED"
        assert "WAIT" in decisions, "Decisions should include WAIT"
        assert "SKIP" in decisions, "Decisions should include SKIP"
        
        print(f"✓ Integration decisions: {decisions}")

    def test_integration_go_full(self):
        """POST /api/entry-timing/integration/evaluate - GO timing + supportive micro = GO_FULL"""
        payload = {
            "prediction": {
                "direction": "LONG",
                "confidence": 0.85,
                "tradeable": True
            },
            "setup": {
                "entry": 62410,
                "stop_loss": 62200,
                "target": 62800,
                "rr": 1.86
            },
            "entry_mode": {
                "entry_mode": "ENTER_IMMEDIATE",
                "reason": "strong_signal"
            },
            "execution_strategy": {
                "execution_strategy": "SINGLE_ENTRY",
                "valid": True,
                "reason": "standard_entry",
                "legs": []
            },
            "entry_quality": {
                "entry_quality_score": 0.85,
                "entry_quality_grade": "A",
                "reasons": ["high_confidence", "good_rr"]
            },
            "mtf": {
                "decision": "ENTER_AGGRESSIVE",
                "confidence": 0.8
            },
            "microstructure": {
                "entry_permission": True,
                "microstructure_score": 0.85,
                "liquidity_risk": 0.2,
                "sweep_risk": 0.15,
                "absorption_detected": True,
                "imbalance": "buy",
                "decision": "ENTER_NOW",
                "reasons": ["buy_imbalance_supportive", "absorption_detected", "low_sweep_risk"]
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/entry-timing/integration/evaluate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        assert data.get("final_entry_decision") == "GO_FULL", f"Expected GO_FULL, got {data.get('final_entry_decision')}"
        assert data.get("micro_applied") is True, "micro_applied should be True"
        
        print(f"✓ GO timing + supportive micro = {data.get('final_entry_decision')}, reason={data.get('reason')}")

    def test_integration_wait_microstructure(self):
        """POST /api/entry-timing/integration/evaluate - GO timing + sweep risk micro = WAIT_MICROSTRUCTURE"""
        payload = {
            "prediction": {
                "direction": "LONG",
                "confidence": 0.85,
                "tradeable": True
            },
            "setup": {
                "entry": 62410,
                "stop_loss": 62200,
                "target": 62800,
                "rr": 1.86
            },
            "entry_mode": {
                "entry_mode": "ENTER_IMMEDIATE",
                "reason": "strong_signal"
            },
            "execution_strategy": {
                "execution_strategy": "SINGLE_ENTRY",
                "valid": True,
                "reason": "standard_entry",
                "legs": []
            },
            "entry_quality": {
                "entry_quality_score": 0.85,
                "entry_quality_grade": "A",
                "reasons": ["high_confidence", "good_rr"]
            },
            "mtf": {
                "decision": "ENTER_AGGRESSIVE",
                "confidence": 0.8
            },
            "microstructure": {
                "entry_permission": False,
                "microstructure_score": 0.35,
                "liquidity_risk": 0.3,
                "sweep_risk": 0.85,
                "absorption_detected": False,
                "imbalance": "neutral",
                "decision": "WAIT_SWEEP",
                "reasons": ["high_sweep_risk", "no_absorption"]
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/entry-timing/integration/evaluate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        assert data.get("final_entry_decision") == "WAIT_MICROSTRUCTURE", f"Expected WAIT_MICROSTRUCTURE, got {data.get('final_entry_decision')}"
        assert data.get("micro_applied") is True, "micro_applied should be True"
        
        print(f"✓ GO timing + sweep risk micro = {data.get('final_entry_decision')}, reason={data.get('reason')}")

    def test_integration_backward_compatible_no_micro(self):
        """POST /api/entry-timing/integration/evaluate - without mtf/microstructure fields should still work"""
        payload = {
            "prediction": {
                "direction": "LONG",
                "confidence": 0.75,
                "tradeable": True
            },
            "setup": {
                "entry": 62410,
                "stop_loss": 62200,
                "target": 62800,
                "rr": 1.86
            },
            "entry_mode": {
                "entry_mode": "ENTER_IMMEDIATE",
                "reason": "standard_entry"
            },
            "execution_strategy": {
                "execution_strategy": "SINGLE_ENTRY",
                "valid": True,
                "reason": "standard_entry",
                "legs": []
            },
            "entry_quality": {
                "entry_quality_score": 0.65,
                "entry_quality_grade": "B",
                "reasons": ["medium_confidence"]
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/entry-timing/integration/evaluate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        assert data.get("final_entry_decision") in ["GO", "GO_REDUCED", "WAIT", "SKIP"], f"Unexpected decision: {data.get('final_entry_decision')}"
        assert data.get("micro_applied") is False, "micro_applied should be False when no micro data"
        
        print(f"✓ Backward compatible (no micro): decision={data.get('final_entry_decision')}, micro_applied={data.get('micro_applied')}")

    def test_integration_skip_preserved_with_supportive_micro(self):
        """POST /api/entry-timing/integration/evaluate - SKIP timing preserved even with supportive micro"""
        payload = {
            "prediction": {
                "direction": "LONG",
                "confidence": 0.3,
                "tradeable": False  # Not tradeable = SKIP
            },
            "setup": {
                "entry": 62410,
                "stop_loss": 62200,
                "target": 62800,
                "rr": 1.86
            },
            "entry_mode": {
                "entry_mode": "SKIP_LATE_ENTRY",
                "reason": "late_entry"
            },
            "execution_strategy": {
                "execution_strategy": "SINGLE_ENTRY",
                "valid": True,
                "reason": "standard_entry",
                "legs": []
            },
            "entry_quality": {
                "entry_quality_score": 0.25,
                "entry_quality_grade": "D",
                "reasons": ["low_confidence"]
            },
            "microstructure": {
                "entry_permission": True,
                "microstructure_score": 0.9,
                "liquidity_risk": 0.1,
                "sweep_risk": 0.1,
                "absorption_detected": True,
                "imbalance": "buy",
                "decision": "ENTER_NOW",
                "reasons": ["all_supportive"]
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/entry-timing/integration/evaluate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        assert data.get("final_entry_decision") == "SKIP", f"Expected SKIP, got {data.get('final_entry_decision')}"
        
        print(f"✓ SKIP preserved with supportive micro: decision={data.get('final_entry_decision')}")


class TestBackwardCompatibilityMTF:
    """Phase 4.7 - MTF Endpoints Still Work"""

    def test_mtf_health(self):
        """GET /api/entry-timing/mtf/health - should still work"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/mtf/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        assert data.get("version") == "4.7", f"Expected version 4.7, got {data.get('version')}"
        
        print(f"✓ MTF health: version={data.get('version')}")

    def test_mtf_mock_aligned(self):
        """POST /api/entry-timing/mtf/decide/mock/aligned - should still work"""
        response = requests.post(f"{BASE_URL}/api/entry-timing/mtf/decide/mock/aligned")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        assert data.get("entry_mode") == "ENTER_AGGRESSIVE", f"Expected ENTER_AGGRESSIVE, got {data.get('entry_mode')}"
        
        print(f"✓ MTF mock aligned: entry_mode={data.get('entry_mode')}")


class TestBackwardCompatibilityPhase41_46:
    """Phase 4.1-4.6 - Existing Endpoints Still Work"""

    def test_wrong_early_summary(self):
        """GET /api/entry-timing/wrong-early/summary - should still work"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/wrong-early/summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        
        print(f"✓ Wrong-early summary endpoint works")

    def test_mode_types(self):
        """GET /api/entry-timing/mode/types - should still work"""
        response = requests.get(f"{BASE_URL}/api/entry-timing/mode/types")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") is True, "Should return ok:true"
        assert "modes" in data, "Response should contain modes"
        
        print(f"✓ Mode types endpoint works: {len(data.get('modes', []))} modes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
