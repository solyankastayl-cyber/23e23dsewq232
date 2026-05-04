"""
Test Suite for PHASE 3.1 Position Intelligence Module
======================================================
Tests: Quality Score, Health Score, Risk Adjustment, History endpoints
Regression test for iteration_6 404 bug fix - CONFIRMED FIXED
"""

import pytest
import requests
import os
import time

# API Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPositionIntelligenceHealth:
    """Test health check endpoint"""
    
    def test_health_check(self):
        """Verify module health check returns all engine statuses"""
        response = requests.get(f"{BASE_URL}/api/position-intelligence/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["module"] == "PHASE 3.1 Position Intelligence"
        assert "engines" in data
        
        engines = data["engines"]
        assert "quality" in engines
        assert "health" in engines
        assert "riskAdjustment" in engines
        
        # Verify each engine is active
        assert engines["quality"]["status"] == "active"
        assert engines["health"]["status"] == "active"
        assert engines["riskAdjustment"]["status"] == "active"
        
        print(f"✓ Health check passed: {data['module']} - {data['status']}")


class TestQualityScore:
    """Test Quality Score calculation endpoints"""
    
    def test_calculate_quality_score(self):
        """POST /quality - Calculate quality score with valid data"""
        payload = {
            "symbol": "BTC",
            "strategy": "TREND_CONFIRMATION",
            "direction": "LONG",
            "regime": "TRENDING",
            "entry_price": 40000.0,
            "stop_price": 39000.0,
            "target_price": 42000.0,
            "current_exposure_pct": 5.0,
            "current_drawdown_pct": 1.0
        }
        
        response = requests.post(f"{BASE_URL}/api/position-intelligence/quality", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify score structure
        assert "scores" in data
        total_score = data["scores"]["total"]
        assert 0 <= total_score <= 100, f"Score {total_score} out of range"
        
        # Verify grade is valid
        valid_grades = ["A+", "A", "B+", "B", "C", "D", "F"]
        assert data["grade"] in valid_grades, f"Invalid grade: {data['grade']}"
        
        # Verify required fields exist
        assert "positionId" in data
        assert "symbol" in data
        assert "scores" in data
        assert "signalQuality" in data["scores"]
        assert "marketContext" in data["scores"]
        assert "riskQuality" in data["scores"]
        
        print(f"✓ Quality Score: {total_score:.1f}/100, Grade: {data['grade']}")
        return data["positionId"]
    
    def test_quality_history_endpoint(self):
        """GET /quality/history - REGRESSION TEST for iteration_6 404 bug"""
        response = requests.get(f"{BASE_URL}/api/position-intelligence/quality/history")
        
        # This was returning 404 before the fix - verify it now returns 200
        assert response.status_code == 200, f"REGRESSION BUG: Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "history" in data, "Response missing 'history' field"
        assert "count" in data, "Response missing 'count' field"
        assert isinstance(data["history"], list), "History should be a list"
        
        print(f"✓ Quality History: {data['count']} records (404 bug FIXED)")
    
    def test_quality_by_position_id(self):
        """GET /quality/{position_id} - Retrieve quality by ID"""
        # First create a position
        payload = {
            "position_id": "test_quality_lookup_v2",
            "symbol": "ETH",
            "strategy": "MEAN_REVERSION",
            "direction": "LONG",
            "regime": "RANGE",
            "entry_price": 2500.0,
            "stop_price": 2400.0,
            "target_price": 2650.0
        }
        
        create_response = requests.post(f"{BASE_URL}/api/position-intelligence/quality", json=payload)
        assert create_response.status_code == 200
        
        # Now retrieve it
        response = requests.get(f"{BASE_URL}/api/position-intelligence/quality/test_quality_lookup_v2")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["positionId"] == "test_quality_lookup_v2"
        assert data["symbol"] == "ETH"
        
        print(f"✓ Quality by ID: {data['positionId']} - Score {data['scores']['total']:.1f}")
    
    def test_quality_not_found(self):
        """GET /quality/{position_id} - Should return 404 for non-existent ID"""
        response = requests.get(f"{BASE_URL}/api/position-intelligence/quality/nonexistent_position_xyz123")
        assert response.status_code == 404, f"Expected 404 for non-existent position, got {response.status_code}"
        print("✓ Quality not found returns 404 correctly")


class TestHealthScore:
    """Test Trade Health Score endpoints"""
    
    def test_calculate_health_score(self):
        """POST /health - Calculate health score"""
        payload = {
            "position_id": "test_health_pos_v2",
            "entry_price": 40000.0,
            "current_price": 40800.0,
            "stop_price": 39000.0,
            "target_price": 42000.0,
            "direction": "LONG",
            "bars_in_trade": 10,
            "max_bars": 100
        }
        
        response = requests.post(f"{BASE_URL}/api/position-intelligence/health", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify health score structure
        assert "health" in data
        current_health = data["health"]["current"]
        assert 0 <= current_health <= 100, f"Health {current_health} out of range"
        
        # Verify status is valid
        valid_statuses = ["EXCELLENT", "GOOD", "NEUTRAL", "WARNING", "CRITICAL", "TERMINAL"]
        assert data["health"]["status"] in valid_statuses, f"Invalid status: {data['health']['status']}"
        
        # Verify required fields
        assert "positionId" in data
        assert "components" in data
        assert "pnl" in data["components"]
        assert "priceAction" in data["components"]
        assert "structure" in data["components"]
        assert "momentum" in data["components"]
        assert "action" in data
        assert "recommended" in data["action"]
        
        print(f"✓ Health Score: {current_health:.1f}/100, Status: {data['health']['status']}")
        return data["positionId"]
    
    def test_health_history_endpoint(self):
        """GET /health/history - REGRESSION TEST for iteration_6 404 bug"""
        response = requests.get(f"{BASE_URL}/api/position-intelligence/health/history")
        
        # This was returning 404 before the fix - verify it now returns 200
        assert response.status_code == 200, f"REGRESSION BUG: Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "history" in data, "Response missing 'history' field"
        assert "count" in data, "Response missing 'count' field"
        assert isinstance(data["history"], list), "History should be a list"
        
        print(f"✓ Health History: {data['count']} records (404 bug FIXED)")
    
    def test_health_by_position_id(self):
        """GET /health/{position_id} - Retrieve health by ID"""
        # First create health record
        payload = {
            "position_id": "test_health_lookup_v2",
            "entry_price": 100.0,
            "current_price": 108.0,
            "stop_price": 95.0,
            "target_price": 115.0,
            "direction": "LONG",
            "bars_in_trade": 15,
            "max_bars": 100
        }
        
        create_response = requests.post(f"{BASE_URL}/api/position-intelligence/health", json=payload)
        assert create_response.status_code == 200
        
        # Now retrieve it
        response = requests.get(f"{BASE_URL}/api/position-intelligence/health/test_health_lookup_v2")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["positionId"] == "test_health_lookup_v2"
        
        print(f"✓ Health by ID: {data['positionId']} - Health {data['health']['current']:.1f}")
    
    def test_health_not_found(self):
        """GET /health/{position_id} - Should return 404 for non-existent ID"""
        response = requests.get(f"{BASE_URL}/api/position-intelligence/health/nonexistent_health_xyz123")
        assert response.status_code == 404, f"Expected 404 for non-existent position, got {response.status_code}"
        print("✓ Health not found returns 404 correctly")


class TestRiskAdjustment:
    """Test Risk Adjustment endpoints"""
    
    def test_calculate_risk_adjustment(self):
        """POST /risk - Calculate risk adjustment"""
        # First need to create quality score
        quality_payload = {
            "position_id": "test_risk_pos_v2",
            "symbol": "SOL",
            "strategy": "MOMENTUM_BREAKOUT",
            "direction": "LONG",
            "regime": "HIGH_VOLATILITY",
            "entry_price": 100.0,
            "stop_price": 95.0,
            "target_price": 115.0
        }
        
        quality_response = requests.post(f"{BASE_URL}/api/position-intelligence/quality", json=quality_payload)
        assert quality_response.status_code == 200
        
        # Now calculate risk adjustment
        risk_payload = {
            "position_id": "test_risk_pos_v2",
            "base_risk_pct": 1.0,
            "regime_stability": "NORMAL",
            "signal_confidence": 0.8
        }
        
        response = requests.post(f"{BASE_URL}/api/position-intelligence/risk", json=risk_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify required fields - check actual response structure
        assert "positionId" in data
        assert "multipliers" in data
        assert "risk" in data
        
        # Verify risk structure
        assert "base" in data["risk"]
        assert "adjusted" in data["risk"]
        assert "level" in data["risk"]
        
        # Verify multipliers structure
        multipliers = data["multipliers"]
        assert "quality" in multipliers
        assert "health" in multipliers
        assert "regime" in multipliers
        assert "confidence" in multipliers
        
        # Verify risk level is valid
        valid_levels = ["MAXIMUM", "ELEVATED", "NORMAL", "REDUCED", "MINIMAL"]
        assert data["risk"]["level"] in valid_levels, f"Invalid risk level: {data['risk']['level']}"
        
        print(f"✓ Risk Adjustment: Base {data['risk']['base']}% -> Adjusted {data['risk']['adjusted']}%, Level: {data['risk']['level']}")
    
    def test_risk_requires_quality(self):
        """POST /risk - Should require quality score first"""
        risk_payload = {
            "position_id": "no_quality_position_xyz",
            "base_risk_pct": 1.0,
            "regime_stability": "NORMAL",
            "signal_confidence": 0.8
        }
        
        response = requests.post(f"{BASE_URL}/api/position-intelligence/risk", json=risk_payload)
        assert response.status_code == 400, f"Expected 400 when quality missing, got {response.status_code}"
        print("✓ Risk correctly requires quality score first")
    
    def test_risk_multiplier_tables(self):
        """GET /risk/tables - Get multiplier tables"""
        response = requests.get(f"{BASE_URL}/api/position-intelligence/risk/tables")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify multiplier tables exist
        assert "quality" in data
        assert "health" in data
        assert "regime" in data
        assert "constraints" in data
        
        # Verify specific multipliers
        assert data["quality"]["A+"] == 1.5, f"A+ should be 1.5x, got {data['quality']['A+']}"
        assert data["quality"]["A"] == 1.25, f"A should be 1.25x, got {data['quality']['A']}"
        assert data["health"]["EXCELLENT"] == 1.1, f"EXCELLENT should be 1.1x, got {data['health']['EXCELLENT']}"
        
        print(f"✓ Risk Tables: A+={data['quality']['A+']}x, EXCELLENT={data['health']['EXCELLENT']}x")


class TestCombinedIntelligence:
    """Test combined intelligence endpoints"""
    
    def test_full_intelligence(self):
        """GET /full/{position_id} - Get full position intelligence"""
        # Create quality first
        quality_payload = {
            "position_id": "test_full_intel_v2",
            "symbol": "BTC",
            "strategy": "TREND_CONFIRMATION",
            "direction": "LONG",
            "regime": "TRENDING",
            "entry_price": 40000.0,
            "stop_price": 39000.0,
            "target_price": 42000.0
        }
        requests.post(f"{BASE_URL}/api/position-intelligence/quality", json=quality_payload)
        
        # Create health
        health_payload = {
            "position_id": "test_full_intel_v2",
            "entry_price": 40000.0,
            "current_price": 40800.0,
            "stop_price": 39000.0,
            "target_price": 42000.0,
            "direction": "LONG",
            "bars_in_trade": 10,
            "max_bars": 100
        }
        requests.post(f"{BASE_URL}/api/position-intelligence/health", json=health_payload)
        
        # Get full intelligence
        response = requests.get(f"{BASE_URL}/api/position-intelligence/full/test_full_intel_v2")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "positionId" in data
        assert "quality" in data
        assert "health" in data
        assert "overall" in data
        
        # Verify overall structure
        assert "score" in data["overall"]
        assert "status" in data["overall"]
        assert "primaryAction" in data["overall"]
        
        # Verify overall status
        valid_statuses = ["STRONG", "GOOD", "NEUTRAL", "WEAK", "EXIT"]
        assert data["overall"]["status"] in valid_statuses, f"Invalid status: {data['overall']['status']}"
        
        print(f"✓ Full Intelligence: Score {data['overall']['score']:.1f}, Status: {data['overall']['status']}, Action: {data['overall']['primaryAction']}")
    
    def test_full_intelligence_not_found(self):
        """GET /full/{position_id} - Should return 404 for non-existent position"""
        response = requests.get(f"{BASE_URL}/api/position-intelligence/full/nonexistent_full_xyz123")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Full intelligence not found returns 404 correctly")


class TestDemoAndStats:
    """Test demo and statistics endpoints"""
    
    def test_demo_endpoint(self):
        """POST /demo - Run demo with BTC, ETH, SOL"""
        response = requests.post(f"{BASE_URL}/api/position-intelligence/demo")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["demo"] == "complete"
        assert "positions" in data
        assert data["count"] == 3, f"Expected 3 demo positions, got {data['count']}"
        
        # Verify all three symbols
        symbols = [p["symbol"] for p in data["positions"]]
        assert "BTC" in symbols, "Missing BTC in demo"
        assert "ETH" in symbols, "Missing ETH in demo"
        assert "SOL" in symbols, "Missing SOL in demo"
        
        # Verify each position has required fields
        for pos in data["positions"]:
            assert "positionId" in pos
            assert "qualityScore" in pos
            assert "qualityGrade" in pos
            assert "healthScore" in pos
            assert "healthStatus" in pos
            assert "adjustedRisk" in pos
            
            # Verify score ranges
            assert 0 <= pos["qualityScore"] <= 100
            assert 0 <= pos["healthScore"] <= 100
            
        symbols_grades = ', '.join([f"{p['symbol']}:{p['qualityGrade']}" for p in data['positions']])
        print(f"✓ Demo: {data['count']} positions - {symbols_grades}")
    
    def test_stats_endpoint(self):
        """GET /stats - Get repository statistics"""
        response = requests.get(f"{BASE_URL}/api/position-intelligence/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Stats structure: positions.tracked, averages, history
        assert "positions" in data, f"Missing 'positions' in stats: {data}"
        assert "tracked" in data["positions"], f"Missing 'tracked' count in stats: {data}"
        
        print(f"✓ Stats endpoint: {data['positions']['tracked']} positions tracked")
    
    def test_all_positions_endpoint(self):
        """GET /all - Get all tracked positions"""
        response = requests.get(f"{BASE_URL}/api/position-intelligence/all")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "positions" in data
        assert "count" in data
        assert isinstance(data["positions"], list)
        
        print(f"✓ All positions: {data['count']} tracked")


class TestValidateScoreRangesAndGrades:
    """Validate score ranges and grade assignments"""
    
    def test_quality_grades_mapping(self):
        """Test different quality levels produce correct grades"""
        # A high quality setup should get A/A+ grade
        high_quality_payload = {
            "position_id": "test_grade_high",
            "symbol": "BTC",
            "strategy": "TREND_CONFIRMATION",
            "direction": "LONG",
            "regime": "TRENDING",
            "entry_price": 40000.0,
            "stop_price": 39000.0,
            "target_price": 44000.0,  # Good R:R
            "current_exposure_pct": 2.0,
            "current_drawdown_pct": 0.5
        }
        
        response = requests.post(f"{BASE_URL}/api/position-intelligence/quality", json=high_quality_payload)
        assert response.status_code == 200
        data = response.json()
        
        # High quality should be at least B+ grade
        assert data["grade"] in ["A+", "A", "B+"], f"Expected high grade, got {data['grade']}"
        print(f"✓ High quality setup: Score {data['scores']['total']:.1f}, Grade {data['grade']}")
    
    def test_health_status_thresholds(self):
        """Test health statuses based on position performance"""
        # Good position (price moving toward target)
        good_health_payload = {
            "position_id": "test_health_good",
            "entry_price": 100.0,
            "current_price": 112.0,  # Good profit
            "stop_price": 95.0,
            "target_price": 115.0,
            "direction": "LONG",
            "bars_in_trade": 5,
            "max_bars": 100
        }
        
        response = requests.post(f"{BASE_URL}/api/position-intelligence/health", json=good_health_payload)
        assert response.status_code == 200
        data = response.json()
        
        # Good position should have EXCELLENT or GOOD status
        assert data["health"]["status"] in ["EXCELLENT", "GOOD"], f"Expected good status, got {data['health']['status']}"
        assert data["health"]["current"] >= 60, f"Expected health >= 60, got {data['health']['current']}"
        
        print(f"✓ Good position health: {data['health']['current']:.1f}, Status: {data['health']['status']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
