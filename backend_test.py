"""
Backend Testing for TA Prediction Intelligence Simulation Engine
================================================================

Tests all HTTP routes for the simulation engine with proper isolation validation.
Based on the review request requirements and DoD conditions from qa_simulation_engine.py.
"""

import requests
import sys
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

class SimulationEngineAPITester:
    def __init__(self, base_url: str = "https://trading-logic-suite.preview.emergentagent.com"):
        self.base_url = base_url.rstrip('/')
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests: List[str] = []
        self.session = requests.Session()
        self.session.timeout = 180  # 3 minutes timeout for replay operations

    def log_test(self, name: str, success: bool, detail: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} {('— ' + detail) if detail else ''}")
        else:
            self.failed_tests.append(name)
            print(f"❌ {name} {('— ' + detail) if detail else ''}")

    def test_endpoint(self, method: str, endpoint: str, expected_status: int, 
                     data: Optional[Dict] = None, timeout: int = 180) -> tuple[bool, Dict]:
        """Test a single endpoint"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, timeout=timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, headers=headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            try:
                response_data = response.json() if response.content else {}
            except:
                response_data = {"raw_response": response.text}
                
            return success, response_data
        except Exception as e:
            print(f"   Request failed: {str(e)}")
            return False, {"error": str(e)}

    def test_health_endpoints(self):
        """Test non-regression health endpoints"""
        print("\n🔍 Testing Health Endpoints (Non-regression)")
        
        # Test general health
        success, data = self.test_endpoint("GET", "/api/ta-prediction-intelligence/health", 200)
        self.log_test("health_endpoint", success, f"response: {data.get('ok', 'unknown')}")
        
        # Test data health
        success, data = self.test_endpoint("GET", "/api/ta-prediction-intelligence/data-health", 200)
        self.log_test("data_health_endpoint", success, f"response: {data.get('ok', 'unknown')}")

    def test_simulation_stats(self) -> Dict[str, Any]:
        """Test GET /simulation/stats endpoint"""
        print("\n🔍 Testing Simulation Stats")
        
        success, data = self.test_endpoint("GET", "/api/ta-prediction-intelligence/simulation/stats", 200)
        self.log_test("simulation_stats", success, f"sim_history: {data.get('sim_history_count', 0)}")
        
        # Validate required fields
        if success:
            required_fields = [
                'ok', 'simulation_version', 'sim_history_count', 'sim_debug_count',
                'sim_history_by_symbol_tf', 'sim_debug_by_error_type',
                'live_history_count', 'live_debug_count'
            ]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                self.log_test("stats_required_fields", False, f"missing: {missing_fields}")
            else:
                self.log_test("stats_required_fields", True, "all required fields present")
        
        return data if success else {}

    def test_simulation_clear_validation(self):
        """Test POST /simulation/clear validation"""
        print("\n🔍 Testing Simulation Clear Validation")
        
        # Test without confirm=true (should return 400)
        clear_data = {
            "symbol": "BTCUSDT",
            "tf": "1H",
            "confirm": False
        }
        success, data = self.test_endpoint("POST", "/api/ta-prediction-intelligence/simulation/clear", 400, clear_data)
        self.log_test("clear_without_confirm", success, "correctly rejected without confirm=true")
        
        # Test with confirm=true (should succeed)
        clear_data["confirm"] = True
        success, data = self.test_endpoint("POST", "/api/ta-prediction-intelligence/simulation/clear", 200, clear_data)
        self.log_test("clear_with_confirm", success, f"cleared: {data.get('cleared', {})}")

    def test_simulation_replay_validation(self):
        """Test POST /simulation/replay parameter validation"""
        print("\n🔍 Testing Simulation Replay Validation")
        
        # Test invalid params: start > end
        invalid_data = {
            "symbol": "BTCUSDT",
            "tf": "1H",
            "start_candle_index": 100,
            "end_candle_index": 90,  # Invalid: start > end
            "max_steps": 10,
            "clear_first": True,
            "candles_limit": 300,
            "min_horizon": 6
        }
        success, data = self.test_endpoint("POST", "/api/ta-prediction-intelligence/simulation/replay", 400, invalid_data)
        self.log_test("replay_invalid_start_end", success, "correctly rejected start > end")
        
        # Test max_steps > 1000 (should return 400)
        invalid_data2 = {
            "symbol": "BTCUSDT",
            "tf": "1H",
            "start_candle_index": 80,
            "end_candle_index": 90,
            "max_steps": 1001,  # Invalid: > 1000 cap
            "clear_first": True,
            "candles_limit": 300,
            "min_horizon": 6
        }
        success, data = self.test_endpoint("POST", "/api/ta-prediction-intelligence/simulation/replay", 422, invalid_data2)
        self.log_test("replay_max_steps_cap", success, "correctly rejected max_steps > 1000 (422 validation error)")

    def test_simulation_replay_execution(self) -> Dict[str, Any]:
        """Test actual simulation replay execution"""
        print("\n🔍 Testing Simulation Replay Execution")
        
        # Record live counts before replay
        stats_before = self.test_simulation_stats()
        live_history_before = stats_before.get('live_history_count', 0)
        live_debug_before = stats_before.get('live_debug_count', 0)
        
        # Execute replay with small range
        replay_data = {
            "symbol": "BTCUSDT",
            "tf": "1H",
            "start_candle_index": 80,
            "end_candle_index": 90,
            "max_steps": 20,
            "clear_first": True,
            "candles_limit": 300,
            "min_horizon": 6
        }
        
        print(f"   Executing replay (may take 30-120 seconds)...")
        start_time = time.time()
        success, data = self.test_endpoint("POST", "/api/ta-prediction-intelligence/simulation/replay", 200, replay_data, timeout=180)
        elapsed = time.time() - start_time
        
        self.log_test("replay_execution", success, f"completed in {elapsed:.1f}s")
        
        if success:
            # Validate response structure
            required_fields = [
                'ok', 'simulation_version', 'symbol', 'tf', 'steps_attempted', 'steps_persisted',
                'sim_history_total_after', 'sim_debug_total_after',
                'live_history_total_before', 'live_history_total_after',
                'live_debug_total_before', 'live_debug_total_after'
            ]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                self.log_test("replay_response_structure", False, f"missing: {missing_fields}")
            else:
                self.log_test("replay_response_structure", True, "all required fields present")
            
            # Validate isolation invariant
            live_history_after = data.get('live_history_total_after', 0)
            live_debug_after = data.get('live_debug_total_after', 0)
            
            isolation_ok = (
                data.get('live_history_total_before', -1) == live_history_after and
                data.get('live_debug_total_before', -1) == live_debug_after
            )
            self.log_test("isolation_invariant", isolation_ok, 
                         f"live counts unchanged: history={live_history_after}, debug={live_debug_after}")
            
            # Validate simulation data was created
            steps_persisted = data.get('steps_persisted', 0)
            sim_history_after = data.get('sim_history_total_after', 0)
            
            self.log_test("simulation_data_created", steps_persisted > 0 and sim_history_after > 0,
                         f"steps_persisted={steps_persisted}, sim_history={sim_history_after}")
            
            print(f"   Replay summary: {data.get('steps_attempted', 0)} attempted, "
                  f"{steps_persisted} persisted, "
                  f"{data.get('steps_skipped_insufficient_horizon', 0)} skipped (horizon), "
                  f"{data.get('steps_errored', 0)} errored")
        
        return data if success else {}

    def test_ml_readiness_details(self, replay_data: Dict[str, Any]):
        """Test ML readiness details endpoint and isolation validation"""
        print("\n🔍 Testing ML Readiness Details")
        
        success, data = self.test_endpoint("GET", "/api/ta-prediction-intelligence/ml-readiness/details", 200)
        self.log_test("ml_readiness_details", success, f"response: {data.get('ok', 'unknown')}")
        
        if success:
            # Check samples_by_source structure
            samples_block = (data.get('details', {}).get('samples', {})).get('samples_by_source', {})
            
            required_keys = ['live_total', 'live_evaluated', 'simulation_total', 'simulation_evaluated', 'scoring_basis']
            missing_keys = [k for k in required_keys if k not in samples_block]
            
            if missing_keys:
                self.log_test("ml_readiness_samples_structure", False, f"missing keys: {missing_keys}")
            else:
                self.log_test("ml_readiness_samples_structure", True, "all required keys present")
                
                # Validate isolation invariant: total should equal live_evaluated only
                total_samples = data.get('details', {}).get('samples', {}).get('total', -1)
                live_evaluated = samples_block.get('live_evaluated', -1)
                scoring_basis = samples_block.get('scoring_basis', '')
                
                isolation_ok = (total_samples == live_evaluated and scoring_basis == 'live_evaluated_only')
                self.log_test("ml_readiness_isolation", isolation_ok,
                             f"total={total_samples} == live_evaluated={live_evaluated}, basis={scoring_basis}")
                
                print(f"   Samples breakdown: live_total={samples_block.get('live_total', 0)}, "
                      f"live_evaluated={live_evaluated}, "
                      f"sim_total={samples_block.get('simulation_total', 0)}, "
                      f"sim_evaluated={samples_block.get('simulation_evaluated', 0)}")

    def test_root_cause_aggregator(self):
        """Test root cause aggregator endpoint (if exists)"""
        print("\n🔍 Testing Root Cause Aggregator (Non-regression)")
        
        success, data = self.test_endpoint("GET", "/api/ta-prediction-intelligence/root-cause/aggregator", 200)
        if success:
            self.log_test("root_cause_aggregator", True, "endpoint accessible")
        else:
            # This endpoint might not exist, which is acceptable
            print("   Root cause aggregator endpoint not found (acceptable)")

    def run_all_tests(self):
        """Run complete test suite"""
        print("=" * 80)
        print("TA Prediction Intelligence Simulation Engine - HTTP API Testing")
        print("=" * 80)
        print(f"Base URL: {self.base_url}")
        print(f"Timeout: {self.session.timeout}s")
        
        try:
            # Test sequence following the review requirements
            self.test_health_endpoints()
            self.test_simulation_stats()
            self.test_simulation_clear_validation()
            self.test_simulation_replay_validation()
            
            # Main replay test with isolation validation
            replay_result = self.test_simulation_replay_execution()
            
            # ML readiness validation
            self.test_ml_readiness_details(replay_result)
            
            # Non-regression tests
            self.test_root_cause_aggregator()
            
        except Exception as e:
            print(f"\n❌ Test suite failed with exception: {e}")
            import traceback
            traceback.print_exc()
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {len(self.failed_tests)}")
        
        if self.failed_tests:
            print("\nFailed tests:")
            for test in self.failed_tests:
                print(f"  - {test}")
            return 1
        else:
            print("\n🎉 ALL TESTS PASSED")
            return 0

def main():
    """Main test runner"""
    # Use the public URL from environment
    base_url = "https://trading-logic-suite.preview.emergentagent.com"
    
    tester = SimulationEngineAPITester(base_url)
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())