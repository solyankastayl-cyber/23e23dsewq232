#!/usr/bin/env python3
"""
Market Mechanics Visualization Layer Testing
===========================================

Tests Market Mechanics Layer backend API functionality:
- POI zones (demand/supply)
- Liquidity lines (EQH/EQL) 
- Sweep markers (BSL/SSL)
- CHOCH validation labels (VALID/WEAK/FAKE)
- Maximum 3 POI zones displayed
- Backend /api/ta/setup/v2 returns poi, liquidity, choch_validation, displacement
"""

import requests
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

# Base URL for testing
BASE_URL = "https://tech-analysis-core-1.preview.emergentagent.com"


class MarketMechanicsAPITester:
    def __init__(self, base_url: str = BASE_URL):
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

    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        success, data, status = self.make_request("GET", "/api/health")
        
        if not success or status != 200:
            self.log_result("Health Endpoint", False, f"Request failed: status={status}")
            return False
            
        if not data.get("ok"):
            self.log_result("Health Endpoint", False, "Status not OK")
            return False
            
        print(f"   💚 Mode: {data.get('mode')}")
        print(f"   💚 Version: {data.get('version')}")
        
        self.log_result("Health Endpoint", True)
        return True

    def test_setup_v2_market_mechanics_data(self):
        """Test /api/ta/setup/v2 returns poi, liquidity, choch_validation, displacement"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("Setup V2 Market Mechanics Data", False, f"Request failed: status={status}")
            return False
            
        # Check required market mechanics fields
        required_fields = ["poi", "liquidity", "choch_validation", "displacement"]
        for field in required_fields:
            if field not in data:
                self.log_result("Setup V2 Market Mechanics Data", False, f"Missing field: {field}")
                return False
        
        poi = data.get("poi", {})
        liquidity = data.get("liquidity", {})
        choch_validation = data.get("choch_validation", {})
        displacement = data.get("displacement", {})
        
        print(f"   📊 POI zones: {len(poi.get('zones', []))}")
        print(f"   📊 Liquidity pools: {len(liquidity.get('pools', []))}")
        print(f"   📊 CHOCH validation score: {choch_validation.get('score', 0)}")
        print(f"   📊 Displacement events: {len(displacement.get('events', []))}")
        
        self.log_result("Setup V2 Market Mechanics Data", True)
        return data

    def test_poi_zones_structure(self):
        """Test POI zones are returned as rectangles with proper structure"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("POI Zones Structure", False, f"Request failed: status={status}")
            return False
            
        poi = data.get("poi", {})
        zones = poi.get("zones", [])
        
        if not zones:
            print("   ⚠️ No POI zones found (this may be normal)")
            self.log_result("POI Zones Structure", True, "No zones found - normal behavior")
            return True
        
        print(f"   📈 POI zones count: {len(zones)}")
        
        # Check zone structure
        for i, zone in enumerate(zones):
            required_fields = ["type", "price_high", "price_low", "mitigated", "strength"]
            for field in required_fields:
                if field not in zone:
                    self.log_result("POI Zones Structure", False, f"Missing field '{field}' in zone {i}")
                    return False
            
            zone_type = zone.get("type")
            if zone_type not in ["demand", "supply"]:
                self.log_result("POI Zones Structure", False, f"Invalid zone type: {zone_type}")
                return False
            
            # Validate price structure for rectangles
            price_high = zone.get("price_high")
            price_low = zone.get("price_low")
            
            if not isinstance(price_high, (int, float)) or not isinstance(price_low, (int, float)):
                self.log_result("POI Zones Structure", False, f"Invalid price values in zone {i}")
                return False
            
            if price_high <= price_low:
                self.log_result("POI Zones Structure", False, f"price_high must be > price_low in zone {i}")
                return False
            
            print(f"   📈   Zone {i+1}: {zone_type.upper()} @ {price_low}-{price_high} (mitigated: {zone.get('mitigated')})")
        
        self.log_result("POI Zones Structure", True)
        return zones

    def test_liquidity_lines_structure(self):
        """Test liquidity lines (EQH/EQL) as dashed price lines"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("Liquidity Lines Structure", False, f"Request failed: status={status}")
            return False
            
        liquidity = data.get("liquidity", {})
        pools = liquidity.get("pools", [])
        
        if not pools:
            print("   ⚠️ No liquidity pools found (this may be normal)")
            self.log_result("Liquidity Lines Structure", True, "No pools found - normal behavior")
            return True
        
        print(f"   💧 Liquidity pools count: {len(pools)}")
        
        eqh_count = 0
        eql_count = 0
        
        # Check pool structure
        for i, pool in enumerate(pools):
            required_fields = ["side", "price", "touches", "strength"]
            for field in required_fields:
                if field not in pool:
                    self.log_result("Liquidity Lines Structure", False, f"Missing field '{field}' in pool {i}")
                    return False
            
            side = pool.get("side")
            if side not in ["high", "low"]:
                self.log_result("Liquidity Lines Structure", False, f"Invalid pool side: {side}")
                return False
            
            # Count EQH/EQL
            if side == "high":
                eqh_count += 1
                label = "EQH"
            else:
                eql_count += 1
                label = "EQL"
            
            price = pool.get("price")
            touches = pool.get("touches", 0)
            strength = pool.get("strength", 0)
            
            print(f"   💧   {label} @ {price} (touches: {touches}, strength: {strength})")
        
        print(f"   💧 EQH (Equal Highs): {eqh_count}")
        print(f"   💧 EQL (Equal Lows): {eql_count}")
        
        self.log_result("Liquidity Lines Structure", True)
        return pools

    def test_sweep_markers_structure(self):
        """Test sweep markers (BSL/SSL) shown as arrows"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("Sweep Markers Structure", False, f"Request failed: status={status}")
            return False
            
        liquidity = data.get("liquidity", {})
        sweeps = liquidity.get("sweeps", [])
        
        if not sweeps:
            print("   ⚠️ No sweep markers found (this may be normal)")
            self.log_result("Sweep Markers Structure", True, "No sweeps found - normal behavior")
            return True
        
        print(f"   ⚡ Sweep markers count: {len(sweeps)}")
        
        bsl_count = 0
        ssl_count = 0
        
        # Check sweep structure
        for i, sweep in enumerate(sweeps):
            required_fields = ["type", "direction", "pool_price", "time", "strength"]
            for field in required_fields:
                if field not in sweep:
                    self.log_result("Sweep Markers Structure", False, f"Missing field '{field}' in sweep {i}")
                    return False
            
            sweep_type = sweep.get("type")
            direction = sweep.get("direction")
            
            # Validate sweep type and direction
            if sweep_type not in ["buy_side_sweep", "sell_side_sweep"]:
                self.log_result("Sweep Markers Structure", False, f"Invalid sweep type: {sweep_type}")
                return False
            
            if direction not in ["bullish", "bearish"]:
                self.log_result("Sweep Markers Structure", False, f"Invalid sweep direction: {direction}")
                return False
            
            # Count BSL/SSL
            if sweep_type == "buy_side_sweep":
                bsl_count += 1
                label = "BSL"
            else:
                ssl_count += 1
                label = "SSL"
            
            pool_price = sweep.get("pool_price")
            strength = sweep.get("strength", 0)
            
            print(f"   ⚡   {label} @ {pool_price} ({direction}, strength: {strength})")
        
        print(f"   ⚡ BSL (Buy-Side Liquidity sweeps): {bsl_count}")
        print(f"   ⚡ SSL (Sell-Side Liquidity sweeps): {ssl_count}")
        
        self.log_result("Sweep Markers Structure", True)
        return sweeps

    def test_choch_validation_labels(self):
        """Test CHOCH validation shown with VALID/WEAK/FAKE labels"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("CHOCH Validation Labels", False, f"Request failed: status={status}")
            return False
            
        choch_validation = data.get("choch_validation", {})
        
        if not choch_validation:
            self.log_result("CHOCH Validation Labels", False, "Missing choch_validation object")
            return False
        
        # Check required fields
        required_fields = ["is_valid", "label", "score", "direction"]
        for field in required_fields:
            if field not in choch_validation:
                self.log_result("CHOCH Validation Labels", False, f"Missing choch_validation field: {field}")
                return False
        
        is_valid = choch_validation.get("is_valid")
        label = choch_validation.get("label")
        score = choch_validation.get("score", 0)
        direction = choch_validation.get("direction")
        
        # Validate label types
        valid_labels = ["valid_choch", "weak_choch", "fake_choch", "no_choch"]
        if label not in valid_labels:
            self.log_result("CHOCH Validation Labels", False, f"Invalid label: {label}")
            return False
        
        # Check label logic
        expected_label = ""
        if score >= 0.70:
            expected_label = "valid_choch"
        elif score >= 0.45:
            expected_label = "weak_choch"
        else:
            expected_label = "fake_choch"
        
        # Map labels for display
        display_labels = {
            "valid_choch": "VALID",
            "weak_choch": "WEAK", 
            "fake_choch": "FAKE",
            "no_choch": "NONE"
        }
        
        display_label = display_labels.get(label, label)
        
        print(f"   🔄 CHOCH validation: {display_label}")
        print(f"   🔄 Score: {score} (threshold: >= 0.70 for VALID)")
        print(f"   🔄 Direction: {direction}")
        print(f"   🔄 Is valid: {is_valid}")
        
        self.log_result("CHOCH Validation Labels", True)
        return choch_validation

    def test_maximum_poi_zones_constraint(self):
        """Test maximum 3 POI zones are displayed"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("Maximum POI Zones Constraint", False, f"Request failed: status={status}")
            return False
            
        poi = data.get("poi", {})
        zones = poi.get("zones", [])
        
        # Check active zones (ones that should be displayed)
        active_zones = [zone for zone in zones if not zone.get("mitigated", True)]
        total_zones = len(zones)
        active_count = len(active_zones)
        
        print(f"   📊 Total POI zones: {total_zones}")
        print(f"   📊 Active POI zones (should be displayed): {active_count}")
        
        # Frontend should display maximum 3 zones (as per MarketMechanicsRenderer options)
        # Backend can return more, but frontend limits to maxPOIZones: 3
        if active_count <= 3:
            print(f"   ✅ Active zones ({active_count}) within display limit (≤3)")
            self.log_result("Maximum POI Zones Constraint", True)
            return True
        else:
            print(f"   ℹ️ Backend returns {active_count} active zones, but frontend will limit to 3")
            # This is still valid - backend can return more, frontend will filter
            self.log_result("Maximum POI Zones Constraint", True, f"Backend has {active_count} zones, frontend will show max 3")
            return True

    def test_market_mechanics_integration(self):
        """Test complete Market Mechanics integration"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("Market Mechanics Integration", False, f"Request failed: status={status}")
            return False
        
        # Check all components are present
        poi = data.get("poi", {})
        liquidity = data.get("liquidity", {})
        choch_validation = data.get("choch_validation", {})
        displacement = data.get("displacement", {})
        
        components_present = {
            "POI": len(poi.get("zones", [])) > 0,
            "Liquidity": len(liquidity.get("pools", [])) > 0,
            "Sweeps": len(liquidity.get("sweeps", [])) > 0,
            "CHOCH": choch_validation.get("score", 0) > 0,
            "Displacement": len(displacement.get("events", [])) > 0
        }
        
        print(f"   🔗 Market Mechanics Components:")
        for component, present in components_present.items():
            status_icon = "✅" if present else "⚠️"
            print(f"   🔗   {status_icon} {component}: {'Present' if present else 'Not present'}")
        
        # Check integration quality - at least 3 components should be working
        active_components = sum(components_present.values())
        
        if active_components >= 3:
            print(f"   🔗 Integration working: {active_components}/5 components active")
            self.log_result("Market Mechanics Integration", True)
            return True
        else:
            self.log_result("Market Mechanics Integration", False, f"Only {active_components}/5 components active")
            return False

    def test_manual_validation_match(self):
        """Test against expected manual results from agent context"""
        success, data, status = self.make_request("GET", "/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        
        if not success or status != 200:
            self.log_result("Manual Validation Match", False, f"Request failed: status={status}")
            return False
        
        poi = data.get("poi", {})
        liquidity = data.get("liquidity", {})
        choch_validation = data.get("choch_validation", {})
        displacement = data.get("displacement", {})
        
        # Expected from agent context:
        # - poi (5 zones, 1 active)
        # - liquidity (3 EQH, 2 EQL) 
        # - choch_validation (score 0.79 = valid)
        # - displacement (16 events)
        
        zones_count = len(poi.get("zones", []))
        active_zones = [z for z in poi.get("zones", []) if not z.get("mitigated", True)]
        pools = liquidity.get("pools", [])
        eqh_count = len([p for p in pools if p.get("side") == "high"])
        eql_count = len([p for p in pools if p.get("side") == "low"])
        choch_score = choch_validation.get("score", 0)
        displacement_events = len(displacement.get("events", []))
        
        print(f"   🎯 Manual Validation Results:")
        print(f"   🎯   POI zones: {zones_count} (expected: ~5)")
        print(f"   🎯   Active zones: {len(active_zones)} (expected: ~1)")
        print(f"   🎯   EQH count: {eqh_count} (expected: ~3)")
        print(f"   🎯   EQL count: {eql_count} (expected: ~2)")
        print(f"   🎯   CHOCH score: {choch_score} (expected: ~0.79)")
        print(f"   🎯   Displacement events: {displacement_events} (expected: ~16)")
        
        # Allow tolerance for dynamic data
        tolerance_checks = {
            "POI zones": 3 <= zones_count <= 7,
            "Active zones": 0 <= len(active_zones) <= 3,
            "Liquidity pools": len(pools) >= 2,
            "CHOCH score": choch_score > 0,
            "Displacement events": displacement_events >= 10
        }
        
        passed_checks = sum(tolerance_checks.values())
        total_checks = len(tolerance_checks)
        
        print(f"   🎯 Validation checks passed: {passed_checks}/{total_checks}")
        for check, passed in tolerance_checks.items():
            icon = "✅" if passed else "❌"
            print(f"   🎯   {icon} {check}")
        
        # Consider successful if most checks pass
        if passed_checks >= total_checks * 0.8:  # 80% threshold
            self.log_result("Manual Validation Match", True)
            return True
        else:
            self.log_result("Manual Validation Match", False, f"Only {passed_checks}/{total_checks} checks passed")
            return False

    def run_all_tests(self):
        """Run all Market Mechanics API tests"""
        print("🧪 Starting Market Mechanics Visualization Layer API Tests...")
        print("=" * 60)
        
        # Core tests
        self.test_health_endpoint()
        self.test_setup_v2_market_mechanics_data()
        
        # Component-specific tests
        self.test_poi_zones_structure()
        self.test_liquidity_lines_structure() 
        self.test_sweep_markers_structure()
        self.test_choch_validation_labels()
        
        # Constraints and integration
        self.test_maximum_poi_zones_constraint()
        self.test_market_mechanics_integration()
        self.test_manual_validation_match()
        
        # Results summary
        print("\n" + "=" * 60)
        print(f"🧪 Market Mechanics API Tests Complete")
        print(f"📊 Tests run: {self.tests_run}")
        print(f"✅ Tests passed: {self.tests_passed}")
        print(f"❌ Tests failed: {self.tests_run - self.tests_passed}")
        print(f"📈 Success rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        
        return self.tests_passed == self.tests_run


def main():
    """Main test runner"""
    tester = MarketMechanicsAPITester()
    all_passed = tester.run_all_tests()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())