#!/usr/bin/env python3
"""
TA Engine Best-Fit Boundary Selection Testing
=============================================

Tests for:
- /api/ta/setup?symbol=BTC&tf=1D endpoint
- /api/health endpoint
- Pattern detection with Best-Fit implementation
- line_scores presence (Best-Fit quality metrics)
- Upper/Lower boundary lines correctness
"""

import requests
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

class TAEngineAPITester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            print(f"✅ {test_name} - PASSED")
        else:
            print(f"❌ {test_name} - FAILED: {details}")
        
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> tuple:
        """Make API request and return (success, response_data, status_code)"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=30)
            else:
                return False, {}, 0
                
            return True, response.json() if response.text else {}, response.status_code
            
        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}, 0
        except Exception as e:
            return False, {"error": str(e)}, 0

    # ═══════════════════════════════════════════════════════════════
    # Core TA Engine Tests
    # ═══════════════════════════════════════════════════════════════

    def test_health_endpoint(self):
        """Test health check endpoint"""
        success, data, status = self.make_request("GET", "/api/health")
        
        if not success or status != 200:
            self.log_result("Health Endpoint", False, f"Request failed: status={status}")
            return False
            
        if not data.get("ok"):
            self.log_result("Health Endpoint", False, "Health status not OK")
            return False
            
        if data.get("mode") != "TA_ENGINE_RUNTIME":
            self.log_result("Health Endpoint", False, f"Unexpected mode: {data.get('mode')}")
            return False
            
        print(f"   ✨ Server mode: {data.get('mode')}")
        print(f"   ✨ Version: {data.get('version')}")
        
        self.log_result("Health Endpoint", True)
        return True

    def test_ta_setup_basic_request(self):
        """Test basic TA setup endpoint"""
        success, data, status = self.make_request("GET", "/api/ta/setup?symbol=BTC&tf=1D")
        
        if not success or status != 200:
            self.log_result("TA Setup Basic Request", False, f"Request failed: status={status}, error={data.get('error', 'unknown')}")
            return False
            
        # Check basic response structure
        required_fields = ["symbol", "timeframe", "candles", "pattern", "levels", "structure", "setup"]
        
        missing_fields = []
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
                
        if missing_fields:
            self.log_result("TA Setup Basic Request", False, f"Missing fields: {missing_fields}")
            return False
        
        print(f"   📈 Symbol: {data.get('symbol')}")
        print(f"   📈 Timeframe: {data.get('timeframe')}")
        print(f"   📈 Candles count: {len(data.get('candles', []))}")
        
        self.log_result("TA Setup Basic Request", True)
        return data

    def test_pattern_detection_with_line_scores(self, setup_data: Dict):
        """Test pattern detection with Best-Fit line_scores"""
        if not setup_data:
            self.log_result("Pattern Detection with Line Scores", False, "No setup data provided")
            return False
            
        pattern = setup_data.get("pattern")
        
        if pattern is None:
            # No pattern detected is valid behavior
            print(f"   ⚠️  No pattern detected (market conditions not met)")
            self.log_result("Pattern Detection with Line Scores", True, "No pattern conditions met")
            return True
            
        # Validate pattern structure
        required_pattern_fields = ["type", "confidence", "touches", "points"]
        
        missing_fields = []
        for field in required_pattern_fields:
            if field not in pattern:
                missing_fields.append(field)
                
        if missing_fields:
            self.log_result("Pattern Detection with Line Scores", False, f"Missing pattern fields: {missing_fields}")
            return False
        
        # Check for line_scores (Best-Fit quality metric)
        if "line_scores" not in pattern:
            self.log_result("Pattern Detection with Line Scores", False, "line_scores field missing - Best-Fit quality not reported")
            return False
            
        line_scores = pattern.get("line_scores", {})
        if not isinstance(line_scores, dict):
            self.log_result("Pattern Detection with Line Scores", False, f"line_scores should be dict, got {type(line_scores)}")
            return False
            
        # Validate line_scores structure
        if "upper" not in line_scores or "lower" not in line_scores:
            self.log_result("Pattern Detection with Line Scores", False, "line_scores missing upper/lower scores")
            return False
            
        upper_score = line_scores.get("upper")
        lower_score = line_scores.get("lower")
        
        if not isinstance(upper_score, (int, float)) or not isinstance(lower_score, (int, float)):
            self.log_result("Pattern Detection with Line Scores", False, "line_scores values should be numeric")
            return False
        
        print(f"   🎯 Pattern type: {pattern.get('type')}")
        print(f"   🎯 Confidence: {pattern.get('confidence'):.2f}")
        print(f"   🎯 Touches: {pattern.get('touches')}")
        print(f"   🎯 Upper line score: {upper_score}")
        print(f"   🎯 Lower line score: {lower_score}")
        print(f"   🎯 Total line quality: {upper_score + lower_score}")
        
        self.log_result("Pattern Detection with Line Scores", True)
        return True

    def test_boundary_lines_structure(self, setup_data: Dict):
        """Test Upper and Lower boundary lines have correct points"""
        if not setup_data:
            self.log_result("Boundary Lines Structure", False, "No setup data provided")
            return False
            
        pattern = setup_data.get("pattern")
        
        if pattern is None:
            print(f"   ⚠️  No pattern to test boundary lines")
            self.log_result("Boundary Lines Structure", True, "No pattern present")
            return True
            
        points = pattern.get("points", {})
        if not isinstance(points, dict):
            self.log_result("Boundary Lines Structure", False, f"points should be dict, got {type(points)}")
            return False
        
        # Check for upper and lower boundary lines
        if "upper" not in points or "lower" not in points:
            self.log_result("Boundary Lines Structure", False, "Missing upper/lower boundary lines")
            return False
            
        upper_points = points.get("upper", [])
        lower_points = points.get("lower", [])
        
        if not isinstance(upper_points, list) or not isinstance(lower_points, list):
            self.log_result("Boundary Lines Structure", False, "Boundary points should be lists")
            return False
        
        # Each line should have exactly 2 points
        if len(upper_points) != 2:
            self.log_result("Boundary Lines Structure", False, f"Upper line should have 2 points, got {len(upper_points)}")
            return False
            
        if len(lower_points) != 2:
            self.log_result("Boundary Lines Structure", False, f"Lower line should have 2 points, got {len(lower_points)}")
            return False
        
        # Validate point structure
        for i, point in enumerate(upper_points):
            if not isinstance(point, dict) or "time" not in point or "value" not in point:
                self.log_result("Boundary Lines Structure", False, f"Upper point {i} missing time/value fields")
                return False
                
        for i, point in enumerate(lower_points):
            if not isinstance(point, dict) or "time" not in point or "value" not in point:
                self.log_result("Boundary Lines Structure", False, f"Lower point {i} missing time/value fields")
                return False
        
        print(f"   📐 Upper line: ({upper_points[0]['time']}, {upper_points[0]['value']:.2f}) -> ({upper_points[1]['time']}, {upper_points[1]['value']:.2f})")
        print(f"   📐 Lower line: ({lower_points[0]['time']}, {lower_points[0]['value']:.2f}) -> ({lower_points[1]['time']}, {lower_points[1]['value']:.2f})")
        
        # Validate that upper line is actually above lower line
        upper_avg = (upper_points[0]['value'] + upper_points[1]['value']) / 2
        lower_avg = (lower_points[0]['value'] + lower_points[1]['value']) / 2
        
        if upper_avg <= lower_avg:
            self.log_result("Boundary Lines Structure", False, f"Upper line ({upper_avg:.2f}) not above lower line ({lower_avg:.2f})")
            return False
        
        print(f"   📐 Upper/Lower positioning: ✅ Upper ({upper_avg:.2f}) > Lower ({lower_avg:.2f})")
        
        self.log_result("Boundary Lines Structure", True)
        return True

    def test_ta_debug_endpoint(self):
        """Test TA debug endpoint for additional insights"""
        success, data, status = self.make_request("GET", "/api/ta/debug?symbol=BTC&tf=1D")
        
        if not success or status != 200:
            self.log_result("TA Debug Endpoint", False, f"Request failed: status={status}")
            return False
            
        # Check debug response structure
        expected_fields = ["symbol", "timeframe", "candles_count", "pattern", "levels_count", "structure_trend"]
        
        for field in expected_fields:
            if field not in data:
                self.log_result("TA Debug Endpoint", False, f"Missing debug field: {field}")
                return False
                
        print(f"   🔍 Debug - Candles: {data.get('candles_count')}")
        print(f"   🔍 Debug - Pattern: {data.get('pattern')}")
        print(f"   🔍 Debug - Levels: {data.get('levels_count')}")
        print(f"   🔍 Debug - Structure: {data.get('structure_trend')}")
        
        self.log_result("TA Debug Endpoint", True)
        return True

    def test_different_symbols_and_timeframes(self):
        """Test TA setup with different symbols and timeframes"""
        test_cases = [
            {"symbol": "ETH", "tf": "1D"},
            {"symbol": "BTC", "tf": "4H"},
            {"symbol": "SOL", "tf": "1D"}
        ]
        
        results = []
        for case in test_cases:
            symbol = case["symbol"]
            tf = case["tf"]
            
            success, data, status = self.make_request("GET", f"/api/ta/setup?symbol={symbol}&tf={tf}")
            
            if success and status == 200:
                pattern = data.get("pattern")
                results.append({
                    "symbol": symbol,
                    "tf": tf,
                    "has_pattern": pattern is not None,
                    "pattern_type": pattern.get("type") if pattern else None,
                    "line_scores": pattern.get("line_scores") if pattern else None
                })
                print(f"   🔄 {symbol}/{tf}: {'✅ Pattern' if pattern else '⚪ No pattern'}")
                if pattern:
                    print(f"      Type: {pattern.get('type')}, Confidence: {pattern.get('confidence', 0):.2f}")
            else:
                results.append({
                    "symbol": symbol,
                    "tf": tf,
                    "has_pattern": False,
                    "error": f"Request failed: {status}"
                })
                print(f"   🔄 {symbol}/{tf}: ❌ Request failed")
        
        # At least one test should succeed
        successful_requests = sum(1 for r in results if "error" not in r)
        if successful_requests == 0:
            self.log_result("Different Symbols & Timeframes", False, "All requests failed")
            return False
            
        self.log_result("Different Symbols & Timeframes", True, f"{successful_requests}/{len(test_cases)} requests successful")
        return True

    # ═══════════════════════════════════════════════════════════════
    # Test Runner
    # ═══════════════════════════════════════════════════════════════

    def run_all_tests(self):
        """Run all TA engine tests"""
        print("🚀 Starting TA Engine Best-Fit API Tests...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Core functionality tests
        print("\n🔧 CORE TA ENGINE TESTS")
        print("-" * 50)
        
        # Test health first
        if not self.test_health_endpoint():
            print("❌ Health check failed - stopping tests")
            return False
        
        # Test basic setup endpoint
        setup_data = self.test_ta_setup_basic_request()
        
        if not setup_data:
            print("❌ Basic setup failed - stopping tests") 
            return False
        
        # Best-Fit specific tests
        print("\n🎯 BEST-FIT BOUNDARY SELECTION TESTS")
        print("-" * 50)
        
        self.test_pattern_detection_with_line_scores(setup_data)
        self.test_boundary_lines_structure(setup_data)
        
        # Additional validation tests
        print("\n🔍 ADDITIONAL VALIDATION TESTS")
        print("-" * 50)
        
        self.test_ta_debug_endpoint()
        self.test_different_symbols_and_timeframes()
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 TA ENGINE TEST SUMMARY")
        print("=" * 80)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {success_rate:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TA ENGINE TESTS PASSED!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} TESTS FAILED")
            
            # Print failed tests
            failed_tests = [r for r in self.test_results if not r["passed"]]
            if failed_tests:
                print("\n❌ FAILED TESTS:")
                for test in failed_tests:
                    print(f"   - {test['test']}: {test['details']}")
            
            return False


def main():
    """Main test runner"""
    print("TA Engine Best-Fit Boundary Selection Tester")
    print("=" * 80)
    
    # Initialize tester
    tester = TAEngineAPITester()
    
    try:
        # Run tests
        success = tester.run_all_tests()
        
        # Exit with appropriate code
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return 1
        
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())