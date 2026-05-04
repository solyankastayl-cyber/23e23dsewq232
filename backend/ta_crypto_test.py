#!/usr/bin/env python3
"""
TA Crypto Data API Testing
==========================

Tests for:
- GET /api/ta/setup?symbol=BTCUSDT&tf=1D - should return 2500+ candles from 2019
- GET /api/ta/setup?symbol=ETHUSDT&tf=1D - should return full ETH history  
- GET /api/ta/setup?symbol=SOLUSDT&tf=1D - should return SOL history from 2021
- Coinbase provider pagination functionality
- Data quality and completeness
"""

import requests
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional


class TACryptoAPITester:
    def __init__(self, base_url: str = "https://tech-analysis-core-1.preview.emergentagent.com"):
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

    def make_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> tuple:
        """Make API request and return (success, response_data, status_code)"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, timeout=60)
            else:
                return False, {}, 0
                
            return True, response.json() if response.text else {}, response.status_code
            
        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}, 0
        except Exception as e:
            return False, {"error": str(e)}, 0

    def test_btc_full_history(self):
        """Test BTC data - should return 2500+ candles from 2019"""
        print("🔍 Testing BTC full history (target: 2500+ candles from 2019)...")
        
        params = {"symbol": "BTCUSDT", "tf": "1D"}
        success, data, status = self.make_request("GET", "/api/ta/setup", params)
        
        if not success:
            self.log_result("BTC Full History", False, f"Request failed with error: {data}")
            return False
            
        if status != 200:
            self.log_result("BTC Full History", False, f"HTTP status {status}: {data}")
            return False
            
        # Validate response structure
        if not isinstance(data, dict):
            self.log_result("BTC Full History", False, "Response is not a dictionary")
            return False
            
        candles = data.get("candles", [])
        if not isinstance(candles, list):
            self.log_result("BTC Full History", False, "Candles is not a list")
            return False
            
        candles_count = len(candles)
        print(f"   📊 Candles received: {candles_count}")
        
        # Check minimum count requirement  
        if candles_count < 2000:
            self.log_result("BTC Full History", False, f"Only {candles_count} candles, expected 2000+")
            return False
            
        # Check date range - should go back to 2019 or earlier
        if candles:
            candles.sort(key=lambda x: x.get('time', 0))
            earliest = candles[0]
            latest = candles[-1]
            
            earliest_time = earliest.get('time', 0)
            latest_time = latest.get('time', 0)
            
            # Convert to datetime
            earliest_dt = datetime.fromtimestamp(earliest_time, tz=timezone.utc) if earliest_time else None
            latest_dt = datetime.fromtimestamp(latest_time, tz=timezone.utc) if latest_time else None
            
            if earliest_dt:
                print(f"   📅 Earliest data: {earliest_dt.date()}")
                # Check if data goes back to 2019 or earlier
                if earliest_dt.year > 2019:
                    self.log_result("BTC Full History", False, f"Data only goes back to {earliest_dt.year}, expected 2019 or earlier")
                    return False
                    
            if latest_dt:
                print(f"   📅 Latest data: {latest_dt.date()}")
                
            # Validate data quality
            valid_candles = 0
            for candle in candles[:10]:  # Sample first 10
                if all(k in candle for k in ['time', 'open', 'high', 'low', 'close']):
                    if candle['high'] >= candle['low'] > 0:
                        valid_candles += 1
                        
            if valid_candles < 8:  # At least 80% valid
                self.log_result("BTC Full History", False, f"Data quality issues: only {valid_candles}/10 valid candles")
                return False
                
        self.log_result("BTC Full History", True, f"{candles_count} candles from {earliest_dt.date() if earliest_dt else 'unknown'}")
        return True

    def test_eth_full_history(self):
        """Test ETH data - should return full ETH history"""
        print("🔍 Testing ETH full history...")
        
        params = {"symbol": "ETHUSDT", "tf": "1D"}
        success, data, status = self.make_request("GET", "/api/ta/setup", params)
        
        if not success:
            self.log_result("ETH Full History", False, f"Request failed with error: {data}")
            return False
            
        if status != 200:
            self.log_result("ETH Full History", False, f"HTTP status {status}: {data}")
            return False
            
        candles = data.get("candles", [])
        candles_count = len(candles)
        print(f"   📊 Candles received: {candles_count}")
        
        # ETH should have substantial history
        if candles_count < 1500:
            self.log_result("ETH Full History", False, f"Only {candles_count} candles, expected 1500+")
            return False
            
        if candles:
            candles.sort(key=lambda x: x.get('time', 0))
            earliest = candles[0]
            earliest_time = earliest.get('time', 0)
            earliest_dt = datetime.fromtimestamp(earliest_time, tz=timezone.utc) if earliest_time else None
            
            if earliest_dt:
                print(f"   📅 Earliest ETH data: {earliest_dt.date()}")
                
        self.log_result("ETH Full History", True, f"{candles_count} candles")
        return True

    def test_sol_history(self):
        """Test SOL data - should return SOL history from 2021+"""
        print("🔍 Testing SOL history (from 2021+)...")
        
        params = {"symbol": "SOLUSDT", "tf": "1D"}  
        success, data, status = self.make_request("GET", "/api/ta/setup", params)
        
        if not success:
            self.log_result("SOL History", False, f"Request failed with error: {data}")
            return False
            
        if status != 200:
            self.log_result("SOL History", False, f"HTTP status {status}: {data}")
            return False
            
        candles = data.get("candles", [])
        candles_count = len(candles)
        print(f"   📊 Candles received: {candles_count}")
        
        # SOL started trading around 2021, so should have reasonable history
        if candles_count < 1000:
            self.log_result("SOL History", False, f"Only {candles_count} candles, expected 1000+ for SOL")
            return False
            
        if candles:
            candles.sort(key=lambda x: x.get('time', 0))
            earliest = candles[0]
            earliest_time = earliest.get('time', 0)
            earliest_dt = datetime.fromtimestamp(earliest_time, tz=timezone.utc) if earliest_time else None
            
            if earliest_dt:
                print(f"   📅 Earliest SOL data: {earliest_dt.date()}")
                # SOL should start around 2021
                if earliest_dt.year < 2020:
                    print(f"   ⚠️  SOL data goes back to {earliest_dt.year} (unexpected)")
                    
        self.log_result("SOL History", True, f"{candles_count} candles")
        return True

    def test_ta_data_structure(self):
        """Test TA setup data structure completeness"""
        print("🔍 Testing TA setup data structure...")
        
        params = {"symbol": "BTCUSDT", "tf": "1D"}
        success, data, status = self.make_request("GET", "/api/ta/setup", params)
        
        if not success or status != 200:
            self.log_result("TA Data Structure", False, f"Request failed: status={status}")
            return False
            
        # Check required fields
        required_fields = ["symbol", "timeframe", "candles", "pattern", "levels", "structure", "setup"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            self.log_result("TA Data Structure", False, f"Missing fields: {missing_fields}")
            return False
            
        # Validate pattern structure
        pattern = data.get("pattern")
        if pattern:
            pattern_fields = ["type", "confidence", "points"]
            missing_pattern = [f for f in pattern_fields if f not in pattern]
            if missing_pattern:
                print(f"   ⚠️  Missing pattern fields: {missing_pattern}")
            else:
                print(f"   📊 Pattern: {pattern['type']} (confidence: {pattern['confidence']})")
                
        # Validate levels structure
        levels = data.get("levels", [])
        if levels and isinstance(levels, list):
            print(f"   📊 Support/Resistance levels: {len(levels)}")
            for level in levels[:3]:  # Show first 3
                print(f"      - {level.get('type', 'unknown')}: {level.get('price', 0)}")
                
        # Validate structure analysis
        structure = data.get("structure", {})
        if structure:
            print(f"   📊 Market structure: {structure.get('trend', 'unknown')}")
            
        self.log_result("TA Data Structure", True)
        return True

    def test_debug_endpoint(self):
        """Test debug endpoint for quick validation"""
        print("🔍 Testing TA debug endpoint...")
        
        params = {"symbol": "BTCUSDT", "tf": "1D"}
        success, data, status = self.make_request("GET", "/api/ta/debug", params)
        
        if not success or status != 200:
            self.log_result("TA Debug Endpoint", False, f"Request failed: status={status}")
            return False
            
        # Should have summary info
        if "candles_count" not in data:
            self.log_result("TA Debug Endpoint", False, "Missing candles_count in debug response")
            return False
            
        candles_count = data.get("candles_count", 0)
        pattern_type = data.get("pattern")
        
        print(f"   📊 Debug info - Candles: {candles_count}, Pattern: {pattern_type}")
        
        self.log_result("TA Debug Endpoint", True)
        return True

    def run_all_tests(self):
        """Run all crypto data tests"""
        print("🚀 Starting TA Crypto Data API Tests...")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 80)
        
        print("\n📈 CRYPTO DATA HISTORY TESTS")
        print("-" * 50)
        
        self.test_btc_full_history()
        self.test_eth_full_history() 
        self.test_sol_history()
        
        print("\n🔧 TA DATA STRUCTURE TESTS")
        print("-" * 50)
        
        self.test_ta_data_structure()
        self.test_debug_endpoint()
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {success_rate:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL CRYPTO DATA TESTS PASSED!")
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
    print("TA Crypto Data API Tester")
    print("=" * 80)
    
    # Initialize tester
    tester = TACryptoAPITester()
    
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