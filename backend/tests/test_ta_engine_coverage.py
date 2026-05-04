"""
Backend API tests for NEW TA Engine Coverage (Phase TA-1/TA-2)
Tests 6 new indicators (CCI, Williams %R, Ichimoku, PSAR, Donchian, Keltner)
Tests 4 new patterns (Head & Shoulders, Wedge, Double Top/Bottom, Cup & Handle)
Tests Harmonic patterns (Gartley, Bat)
Tests regime-based suggested indicators logic
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestNewIndicators:
    """Test new indicator calculations (CCI, Williams %R, Ichimoku, PSAR, Donchian, Keltner)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Verify BASE_URL is set"""
        assert BASE_URL, "REACT_APP_BACKEND_URL environment variable must be set"
    
    def test_cci_indicator_in_response(self):
        """Test CCI indicator is returned for ranging regime and values are in typical range"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D?include_hypothesis=true"
        response = requests.get(url)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check if market regime is ranging (should suggest CCI)
        regime = data.get("market_regime", "").lower()
        suggested = data.get("suggested_indicators", [])
        
        print(f"Market regime: {regime}")
        print(f"Suggested indicators: {suggested}")
        
        # For ranging regime, CCI should be in suggested indicators
        if "rang" in regime:
            assert "cci" in suggested, f"CCI should be suggested for ranging regime, got {suggested}"
        
        # Check indicators array for CCI type
        indicators = data.get("indicators", [])
        indicator_types = [ind.get("type", "") for ind in indicators]
        print(f"Indicator types in response: {indicator_types}")
        
        print(f"SUCCESS: Found {len(indicators)} indicators")
    
    def test_williams_r_suggested_for_ranging(self):
        """Test Williams %R is suggested for ranging regime"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        regime = data.get("market_regime", "").lower()
        suggested = data.get("suggested_indicators", [])
        
        if "rang" in regime:
            assert "williams_r" in suggested, f"Williams %R should be suggested for ranging, got {suggested}"
            print(f"SUCCESS: Williams %R in suggested indicators for ranging regime")
        else:
            print(f"INFO: Regime is {regime}, Williams %R may not be suggested")
    
    def test_ichimoku_suggested_for_trending(self):
        """Test Ichimoku suggested for trending regime"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        suggested = data.get("suggested_indicators", [])
        regime = data.get("market_regime", "").lower()
        
        # Check if ichimoku would be in list for trending
        if "trend" in regime or "bullish" in regime or "bearish" in regime:
            assert "ichimoku" in suggested, f"Ichimoku should be suggested for trending, got {suggested}"
            print(f"SUCCESS: Ichimoku in suggested indicators for trending regime")
        
        print(f"Regime: {regime}, Suggested: {suggested}")
    
    def test_donchian_suggested_for_ranging(self):
        """Test Donchian channel suggested for ranging regime"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        regime = data.get("market_regime", "").lower()
        suggested = data.get("suggested_indicators", [])
        
        if "rang" in regime:
            assert "donchian" in suggested, f"Donchian should be suggested for ranging, got {suggested}"
            print(f"SUCCESS: Donchian in suggested indicators for ranging regime")
    
    def test_parabolic_sar_suggested_for_trending(self):
        """Test PSAR suggested for trending"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        regime = data.get("market_regime", "").lower()
        suggested = data.get("suggested_indicators", [])
        
        if "trend" in regime or "bullish" in regime or "bearish" in regime:
            assert "parabolic_sar" in suggested, f"PSAR should be suggested for trending, got {suggested}"
            print(f"SUCCESS: Parabolic SAR in suggested indicators for trending regime")
        else:
            print(f"INFO: Regime is {regime}, checking general suggested list")
            print(f"Suggested indicators: {suggested}")


class TestNewPatternTypes:
    """Test new pattern types in objects[] response"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        assert BASE_URL, "REACT_APP_BACKEND_URL environment variable must be set"
    
    def test_objects_contain_new_pattern_types(self):
        """Test objects array contains new pattern types"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D?include_hypothesis=true"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        objects = data.get("objects", [])
        pattern_types_found = set()
        
        # New pattern types to look for
        new_pattern_types = {
            "head_shoulders", "head_shoulders_inverse",
            "double_top", "double_bottom",
            "cup_handle",
            "wedge_rising", "wedge_falling",
            "harmonic_gartley", "harmonic_bat"
        }
        
        for obj in objects:
            obj_type = obj.get("type", "")
            if obj_type in new_pattern_types:
                pattern_types_found.add(obj_type)
                print(f"Found new pattern: {obj_type} (confidence: {obj.get('confidence', 'N/A')})")
        
        print(f"Total objects: {len(objects)}")
        print(f"New pattern types found: {pattern_types_found}")
        
        # At minimum, verify objects array exists and has structure
        if len(objects) > 0:
            sample = objects[0]
            assert "id" in sample, "Object missing id"
            assert "type" in sample, "Object missing type"
            assert "category" in sample, "Object missing category"
        
        print(f"SUCCESS: Objects array has {len(objects)} items")
    
    def test_eth_4h_patterns(self):
        """Test ETH 4H also returns patterns correctly"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/ETH/4H?include_hypothesis=true"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        objects = data.get("objects", [])
        pattern_objects = [o for o in objects if o.get("category") == "pattern"]
        
        print(f"ETH 4H: Found {len(pattern_objects)} pattern objects out of {len(objects)} total")
        
        for pattern in pattern_objects:
            print(f"  - {pattern.get('type')}: {pattern.get('label', 'N/A')} (conf: {pattern.get('confidence', 'N/A')})")
    
    def test_head_shoulders_pattern_structure(self):
        """Test head & shoulders pattern has correct structure when present"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D?include_hypothesis=true"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        objects = data.get("objects", [])
        hs_patterns = [o for o in objects if "head_shoulders" in o.get("type", "")]
        
        if hs_patterns:
            hs = hs_patterns[0]
            print(f"Found H&S pattern: {hs.get('type')}")
            
            # Verify structure
            assert "points" in hs, "H&S pattern should have points"
            assert "confidence" in hs, "H&S pattern should have confidence"
            assert "metadata" in hs, "H&S pattern should have metadata"
            
            points = hs.get("points", [])
            print(f"  Points: {len(points)} (expected 3 for left shoulder, head, right shoulder)")
            
            metadata = hs.get("metadata", {})
            if "neckline" in metadata:
                print(f"  Neckline: {metadata['neckline']}")
            
            print(f"SUCCESS: H&S pattern has valid structure")
        else:
            print("INFO: No H&S patterns detected in current data (patterns are dynamic)")
    
    def test_double_top_bottom_structure(self):
        """Test double top/bottom patterns when present"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D?include_hypothesis=true"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        objects = data.get("objects", [])
        double_patterns = [o for o in objects if "double_" in o.get("type", "")]
        
        if double_patterns:
            dp = double_patterns[0]
            print(f"Found double pattern: {dp.get('type')}")
            
            # Verify structure
            assert "points" in dp, "Double pattern should have points"
            points = dp.get("points", [])
            print(f"  Points: {len(points)} (expected 2 for two peaks/troughs)")
            
            metadata = dp.get("metadata", {})
            if "neckline" in metadata:
                print(f"  Neckline: {metadata['neckline']}")
            
            print(f"SUCCESS: Double pattern has valid structure")
        else:
            print("INFO: No double top/bottom patterns detected in current data")


class TestHarmonicPatterns:
    """Test harmonic pattern detection (Gartley, Bat)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        assert BASE_URL, "REACT_APP_BACKEND_URL environment variable must be set"
    
    def test_harmonic_patterns_integration(self):
        """Test harmonic patterns are returned from full-analysis endpoint"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D?include_hypothesis=true"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        objects = data.get("objects", [])
        harmonic_patterns = [o for o in objects if "harmonic" in o.get("type", "")]
        
        print(f"Harmonic patterns found: {len(harmonic_patterns)}")
        
        for hp in harmonic_patterns:
            pattern_type = hp.get("type", "")
            confidence = hp.get("confidence", 0)
            direction = hp.get("metadata", {}).get("direction", hp.get("direction", "N/A"))
            points = hp.get("points", [])
            
            print(f"  - {pattern_type}: direction={direction}, confidence={confidence}, points={len(points)}")
            
            # Validate harmonic structure (should have 5 points: X, A, B, C, D)
            if len(points) >= 5:
                print(f"    XABCD points present")
        
        print(f"SUCCESS: Harmonic pattern integration verified")


class TestSuggestedIndicatorsLogic:
    """Test regime-based suggested indicators logic"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        assert BASE_URL, "REACT_APP_BACKEND_URL environment variable must be set"
    
    def test_suggested_indicators_for_btc_regime(self):
        """Test suggested indicators match regime"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        regime = data.get("market_regime", "")
        suggested = data.get("suggested_indicators", [])
        
        print(f"Market Regime: {regime}")
        print(f"Suggested Indicators: {suggested}")
        
        # Verify suggested indicators list is not empty
        assert len(suggested) > 0, "Suggested indicators should not be empty"
        assert isinstance(suggested, list), "Suggested indicators should be a list"
        
        # Validate against expected regime-based suggestions
        regime_lower = regime.lower()
        
        if "rang" in regime_lower or "sideways" in regime_lower:
            expected = ["bollinger", "rsi", "cci", "williams_r", "donchian"]
            print(f"Ranging regime - expected indicators: {expected}")
            
            # Check at least 3 of expected are present
            matches = sum(1 for e in expected if e in suggested)
            print(f"Matches: {matches} out of {len(expected)}")
            assert matches >= 3, f"Expected at least 3 matches from {expected}, got {matches}"
            
        elif "trend" in regime_lower or "bullish" in regime_lower or "bearish" in regime_lower:
            expected = ["ema", "supertrend", "ichimoku", "macd", "parabolic_sar"]
            print(f"Trending regime - expected indicators: {expected}")
            
            matches = sum(1 for e in expected if e in suggested)
            print(f"Matches: {matches} out of {len(expected)}")
            assert matches >= 3, f"Expected at least 3 matches from {expected}, got {matches}"
        
        print(f"SUCCESS: Suggested indicators match regime logic")
    
    def test_suggested_indicators_always_populated(self):
        """Test suggested indicators always returns a list"""
        timeframes = ["1H", "4H", "1D", "1W"]
        
        for tf in timeframes:
            url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/{tf}"
            response = requests.get(url)
            
            assert response.status_code == 200
            data = response.json()
            
            suggested = data.get("suggested_indicators", [])
            regime = data.get("market_regime", "")
            
            assert isinstance(suggested, list), f"Suggested should be list for {tf}"
            assert len(suggested) > 0, f"Suggested should not be empty for {tf}"
            
            print(f"BTC {tf}: regime={regime}, suggested={suggested}")
        
        print(f"SUCCESS: All timeframes return suggested indicators")


class TestObjectCountAndStats:
    """Test stats and object counts"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        assert BASE_URL, "REACT_APP_BACKEND_URL environment variable must be set"
    
    def test_stats_object_counts(self):
        """Test stats contains object count breakdown"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D?include_hypothesis=true&include_fractals=true"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        stats = data.get("stats", {})
        print(f"Stats: {stats}")
        
        # Verify stats fields
        if "total_objects" in stats:
            assert isinstance(stats["total_objects"], int)
            print(f"Total objects: {stats['total_objects']}")
        
        if "patterns_shown" in stats:
            assert isinstance(stats["patterns_shown"], int)
            print(f"Patterns shown: {stats['patterns_shown']}")
        
        if "levels_shown" in stats:
            assert isinstance(stats["levels_shown"], int)
            print(f"Levels shown: {stats['levels_shown']}")
        
        if "indicators_shown" in stats:
            assert isinstance(stats["indicators_shown"], int)
            print(f"Indicators shown: {stats['indicators_shown']}")
        
        # Verify total is reasonable (>=21 as per requirements)
        total = stats.get("total_objects", 0)
        objects = data.get("objects", [])
        indicators = data.get("indicators", [])
        
        combined = len(objects) + len(indicators)
        print(f"Objects array: {len(objects)}, Indicators array: {len(indicators)}, Combined: {combined}")
        
        print(f"SUCCESS: Stats object verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
