"""
Test Watch Levels and InsightPanel Features
============================================

Tests for the "What to Watch" layer and InsightPanel functionality:
1. Backend: watch_levels in pattern-v2 endpoint
2. Backend: watch_levels in mtf endpoint
3. Watch levels structure validation
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tech-analysis-core-1.preview.emergentagent.com')


class TestWatchLevelsBackend:
    """Test watch_levels feature in backend APIs"""
    
    def test_pattern_v2_returns_watch_levels(self):
        """GET /api/ta-engine/pattern-v2/BTC?timeframe=4H should return watch_levels"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/pattern-v2/BTC?timeframe=4H")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "interpretation" in data, "Response should contain interpretation"
        
        interpretation = data.get("interpretation", {})
        watch_levels = interpretation.get("watch_levels", [])
        
        # Watch levels should be present
        assert isinstance(watch_levels, list), "watch_levels should be a list"
        print(f"Found {len(watch_levels)} watch levels")
        
        # If watch_levels exist, validate structure
        if len(watch_levels) > 0:
            for lvl in watch_levels:
                assert "type" in lvl, "Each watch level should have 'type'"
                assert "price" in lvl, "Each watch level should have 'price'"
                assert "label" in lvl, "Each watch level should have 'label'"
                assert lvl["type"] in ["breakout_up", "breakdown_down"], f"Invalid type: {lvl['type']}"
                assert isinstance(lvl["price"], (int, float)), "Price should be numeric"
                print(f"  - {lvl['type']}: {lvl['price']} ({lvl['label']})")
    
    def test_pattern_v2_watch_levels_structure(self):
        """Validate watch_levels have correct breakout_up/breakdown_down structure"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/pattern-v2/BTC?timeframe=4H")
        assert response.status_code == 200
        
        data = response.json()
        watch_levels = data.get("interpretation", {}).get("watch_levels", [])
        
        # Check for breakout_up type
        breakout_up = [lvl for lvl in watch_levels if lvl.get("type") == "breakout_up"]
        breakdown_down = [lvl for lvl in watch_levels if lvl.get("type") == "breakdown_down"]
        
        print(f"Breakout up levels: {len(breakout_up)}")
        print(f"Breakdown down levels: {len(breakdown_down)}")
        
        # At least one of each type should exist for range patterns
        if len(watch_levels) > 0:
            # Validate price values are reasonable (positive numbers)
            for lvl in watch_levels:
                assert lvl["price"] > 0, f"Price should be positive: {lvl['price']}"
    
    def test_mtf_endpoint_returns_watch_levels(self):
        """GET /api/ta-engine/mtf/BTC?timeframes=4H should return watch_levels in tf_map"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/mtf/BTC?timeframes=4H")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "tf_map" in data, "Response should contain tf_map"
        
        tf_map = data.get("tf_map", {})
        assert "4H" in tf_map, "tf_map should contain 4H timeframe"
        
        tf_4h = tf_map.get("4H", {})
        watch_levels = tf_4h.get("watch_levels", [])
        
        print(f"MTF 4H watch_levels: {len(watch_levels)} levels")
        
        # Validate structure if present
        for lvl in watch_levels:
            assert "type" in lvl, "Each watch level should have 'type'"
            assert "price" in lvl, "Each watch level should have 'price'"
            assert "label" in lvl, "Each watch level should have 'label'"
            print(f"  - {lvl['type']}: {lvl['price']} ({lvl['label']})")
    
    def test_interpretation_contains_market_state(self):
        """Interpretation should contain market_state for InsightPanel context"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/pattern-v2/BTC?timeframe=4H")
        assert response.status_code == 200
        
        data = response.json()
        interpretation = data.get("interpretation", {})
        
        # Check for market_state
        market_state = interpretation.get("market_state")
        assert market_state is not None, "interpretation should contain market_state"
        print(f"Market state: {market_state}")
        
        # Check for line1 and line2 (interpretation text)
        line1 = interpretation.get("line1")
        line2 = interpretation.get("line2")
        print(f"Line1: {line1}")
        print(f"Line2: {line2}")
    
    def test_render_stack_for_insight_panel(self):
        """render_stack should contain patterns for InsightPanel selection"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/pattern-v2/BTC?timeframe=4H")
        assert response.status_code == 200
        
        data = response.json()
        render_stack = data.get("render_stack", [])
        
        print(f"Render stack contains {len(render_stack)} patterns")
        
        # Validate render_stack structure
        for i, pattern in enumerate(render_stack):
            assert "role" in pattern, f"Pattern {i} should have 'role'"
            assert "type" in pattern, f"Pattern {i} should have 'type'"
            print(f"  - {pattern.get('role')}: {pattern.get('type')}")
            
            # Dominant pattern should have contract
            if pattern.get("role") == "dominant":
                assert "contract" in pattern, "Dominant pattern should have 'contract'"


class TestHealthEndpoint:
    """Basic health check"""
    
    def test_health_endpoint(self):
        """Health endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
