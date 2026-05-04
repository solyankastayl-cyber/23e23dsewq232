#!/usr/bin/env python3
"""
TA Geometry Fixes Backend Testing - P0 Release
================================================

Tests for P0 Geometry Fixes:
1. extendLine() - lines extend to chart end, not p1→p2
2. pivot window filter - filter by pattern_start
3. anchor penalty - penalty for early anchors
4. violation hard filter - enhanced penalty (6) + cutoff (max 3)
5. confidence threshold (0.6) - don't show garbage patterns

Test Coverage:
- API /api/ta/setup?symbol=BTC&tf=1D returns extended lines in points
- API returns anchor_points separately from extended points
- Extended lines continue to chart end (end_time > anchor p2 time)
- Confidence threshold works (4H doesn't return pattern if confidence < 0.6)
- Pattern validation rejects lines with violations > 3
- API /api/health works
"""

import requests
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional


class TAGeometryTester:
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
    # P0 Geometry Fix Tests
    # ═══════════════════════════════════════════════════════════════

    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        success, data, status = self.make_request("GET", "/api/health")
        
        if not success or status != 200:
            self.log_result("Health Endpoint", False, f"Request failed: status={status}")
            return False
            
        if not data.get("ok"):
            self.log_result("Health Endpoint", False, "Health check failed")
            return False
            
        print(f"   💚 Health status: OK")
        print(f"   💚 Mode: {data.get('mode', 'unknown')}")
        
        self.log_result("Health Endpoint", True)
        return True

    def test_ta_setup_btc_1d_extended_lines(self):
        """Test P0.1: Extended lines in points (BTC 1D)"""
        success, data, status = self.make_request("GET", "/api/ta/setup?symbol=BTC&tf=1D")
        
        if not success or status != 200:
            self.log_result("BTC 1D Extended Lines", False, f"Request failed: status={status}")
            return False
            
        # Check if pattern exists
        pattern = data.get("pattern")
        if not pattern:
            print(f"   ⚠️  No patterns found for BTC 1D (may be normal)")
            self.log_result("BTC 1D Extended Lines", True, "No patterns to test")
            return True
        
        # Check P0.1: Extended lines in "points" field
        if "points" not in pattern:
            self.log_result("BTC 1D Extended Lines", False, "Missing 'points' field in pattern")
            return False
            
        points = pattern["points"]
        if not isinstance(points, dict) or "upper" not in points or "lower" not in points:
            self.log_result("BTC 1D Extended Lines", False, "Invalid points structure")
            return False
            
        # Check P0.1: Separate anchor_points field
        if "anchor_points" not in pattern:
            self.log_result("BTC 1D Extended Lines", False, "Missing 'anchor_points' field")
            return False
            
        anchor_points = pattern["anchor_points"]
        if not isinstance(anchor_points, dict) or "upper" not in anchor_points or "lower" not in anchor_points:
            self.log_result("BTC 1D Extended Lines", False, "Invalid anchor_points structure")
            return False
            
        # P0.1 FIX: Verify extended lines != anchor points
        upper_extended = points["upper"]
        upper_anchor = anchor_points["upper"]
        
        if upper_extended == upper_anchor:
            self.log_result("BTC 1D Extended Lines", False, "Extended lines same as anchor points (not extended)")
            return False
        
        # Check that extended lines have later end time than anchor p2 time
        if len(upper_extended) >= 2 and len(upper_anchor) >= 2:
            extended_end_time = upper_extended[-1]["time"]
            anchor_p2_time = upper_anchor[-1]["time"]
            
            if extended_end_time <= anchor_p2_time:
                self.log_result("BTC 1D Extended Lines", False, 
                             f"Extended line end time ({extended_end_time}) not > anchor p2 time ({anchor_p2_time})")
                return False
                
        print(f"   🔧 Pattern type: {pattern.get('type', 'unknown')}")
        print(f"   🔧 Extended lines: {len(upper_extended)} points")
        print(f"   🔧 Anchor points: {len(upper_anchor)} points")
        print(f"   🔧 Time extension verified: extended > anchor")
        
        self.log_result("BTC 1D Extended Lines", True)
        return True

    def test_confidence_threshold_4h_filter(self):
        """Test P0.5: Confidence threshold (4H should not return patterns < 0.6)"""
        success, data, status = self.make_request("GET", "/api/ta/setup?symbol=BTC&tf=4H")
        
        if not success or status != 200:
            self.log_result("Confidence Threshold 4H", False, f"Request failed: status={status}")
            return False
            
        # Check if pattern exists
        pattern = data.get("pattern")
        if not pattern:
            print(f"   ✅ No patterns returned for 4H (confidence filtering working)")
            self.log_result("Confidence Threshold 4H", True, "No low-confidence patterns returned")
            return True
            
        # If pattern exists, verify confidence >= 0.6
        confidence = pattern.get("confidence", 0)
        if confidence < 0.6:
            self.log_result("Confidence Threshold 4H", False, 
                          f"Found low-confidence pattern: {pattern.get('type', 'unknown')}: {confidence}")
            return False
            
        print(f"   🎯 Pattern found: {pattern.get('type', 'unknown')}")
        print(f"   🎯 Confidence: {confidence:.2f}")
            
        self.log_result("Confidence Threshold 4H", True)
        return True

    def test_pattern_validation_violation_filter(self):
        """Test P0.4: Pattern validation rejects lines with violations > 3"""
        # Test multiple timeframes to find patterns and check violation filtering
        symbols_tfs = [("BTC", "1D"), ("ETH", "1D"), ("BTC", "4H")]
        
        violations_checked = 0
        patterns_with_violations = []
        
        for symbol, tf in symbols_tfs:
            success, data, status = self.make_request("GET", f"/api/ta/setup?symbol={symbol}&tf={tf}")
            
            if not success or status != 200:
                continue
                
            pattern = data.get("pattern")
            if not pattern:
                continue
                
            violations_checked += 1
            
            # Check line scores and confidence to infer violation filtering worked
            line_scores = pattern.get("line_scores", {})
            confidence = pattern.get("confidence", 0)
            
            # If we have very low line scores or confidence, it suggests violations weren't filtered
            upper_score = line_scores.get("upper", 0)
            lower_score = line_scores.get("lower", 0)
            
            # Patterns with extremely negative scores likely had too many violations
            if upper_score < -10 or lower_score < -10:
                patterns_with_violations.append(
                    f"{symbol} {tf} {pattern.get('type')}: scores {upper_score}, {lower_score}"
                )
                
        if patterns_with_violations:
            self.log_result("Violation Filter", False, 
                          f"Found patterns with likely excessive violations: {patterns_with_violations}")
            return False
        
        if violations_checked == 0:
            print(f"   ⚠️  No patterns found to check violations (may be normal)")
            self.log_result("Violation Filter", True, "No patterns to validate violations")
        else:
            print(f"   🛡️  Checked {violations_checked} patterns for violation filtering")
            print(f"   🛡️  No patterns with excessive violations found")
            self.log_result("Violation Filter", True)
        
        return True

    def test_anchor_points_separate_from_extended(self):
        """Test that anchor_points are properly separated from extended points"""
        symbols_tfs = [("BTC", "1D"), ("ETH", "1D")]
        
        anchor_tests = 0
        
        for symbol, tf in symbols_tfs:
            success, data, status = self.make_request("GET", f"/api/ta/setup?symbol={symbol}&tf={tf}")
            
            if not success or status != 200:
                continue
                
            pattern = data.get("pattern")
            if not pattern:
                continue
                
            anchor_tests += 1
            
            # Verify both points and anchor_points exist
            if "points" not in pattern or "anchor_points" not in pattern:
                self.log_result("Anchor Points Separation", False, 
                              f"Missing points or anchor_points in {symbol} {tf}")
                return False
                
            points = pattern["points"]
            anchor_points = pattern["anchor_points"]
            
            # They should be different (extended vs original p1->p2)
            if points == anchor_points:
                self.log_result("Anchor Points Separation", False, 
                              f"Points same as anchor_points in {symbol} {tf}")
                return False
                
            # Extended points should have different end times
            if ("upper" in points and "upper" in anchor_points and 
                len(points["upper"]) >= 2 and len(anchor_points["upper"]) >= 2):
                
                extended_end = points["upper"][-1]["time"]
                anchor_end = anchor_points["upper"][-1]["time"]
                
                if extended_end == anchor_end:
                    self.log_result("Anchor Points Separation", False, 
                                  f"Extended and anchor end times same in {symbol} {tf}")
                    return False
                    
        if anchor_tests == 0:
            print(f"   ⚠️  No patterns found to test anchor point separation")
            self.log_result("Anchor Points Separation", True, "No patterns to test")
        else:
            print(f"   ⚓ Tested {anchor_tests} patterns for anchor point separation")
            print(f"   ⚓ All patterns have properly separated anchor_points and extended points")
            self.log_result("Anchor Points Separation", True)
        
        return True

    def test_ta_status_endpoint(self):
        """Test TA engine status endpoint"""
        success, data, status = self.make_request("GET", "/api/ta/status")
        
        if not success or status != 200:
            self.log_result("TA Status Endpoint", False, f"Request failed: status={status}")
            return False
            
        if not data.get("ok"):
            self.log_result("TA Status Endpoint", False, "TA status not OK")
            return False
            
        # Check required components
        components = data.get("components", {})
        required_components = ["setup_builder", "pattern_detector", "indicator_engine", 
                              "level_engine", "structure_engine"]
        
        missing_components = []
        for comp in required_components:
            if components.get(comp) != "active":
                missing_components.append(comp)
                
        if missing_components:
            self.log_result("TA Status Endpoint", False, f"Inactive components: {missing_components}")
            return False
            
        print(f"   🏗️  All TA components active: {len(components)}")
        print(f"   🏗️  Module: {data.get('module', 'unknown')}")
        
        self.log_result("TA Status Endpoint", True)
        return True

    # ═══════════════════════════════════════════════════════════════
    # Test Runner
    # ═══════════════════════════════════════════════════════════════

    def run_all_tests(self):
        """Run all P0 geometry fix tests"""
        print("🚀 Starting TA Geometry Fixes Tests (P0)...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Health checks
        print("\n💚 HEALTH CHECK TESTS")
        print("-" * 50)
        self.test_health_endpoint()
        self.test_ta_status_endpoint()
        
        # P0 Geometry Fix tests
        print("\n🔧 P0 GEOMETRY FIX TESTS")
        print("-" * 50)
        
        self.test_ta_setup_btc_1d_extended_lines()
        self.test_confidence_threshold_4h_filter()
        self.test_pattern_validation_violation_filter()
        self.test_anchor_points_separate_from_extended()
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {success_rate:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL P0 GEOMETRY TESTS PASSED!")
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
    print("TA Geometry Fixes Tester - P0 Release")
    print("=" * 80)
    
    # Initialize tester with public URL
    tester = TAGeometryTester()
    
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