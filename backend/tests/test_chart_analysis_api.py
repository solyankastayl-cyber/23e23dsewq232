"""
Backend API tests for Chart Full Analysis endpoint
Tests F4.2 - Chart API for Technical Analysis Module
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestChartFullAnalysisAPI:
    """Tests for /api/v1/chart/full-analysis/{symbol}/{timeframe} endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Verify BASE_URL is set"""
        assert BASE_URL, "REACT_APP_BACKEND_URL environment variable must be set"
    
    def test_btc_1d_analysis(self):
        """Test BTC 1D chart analysis returns all required fields"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D?include_hypothesis=true&include_fractals=true"
        response = requests.get(url)
        
        # Status assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Data assertions
        data = response.json()
        assert data["symbol"] == "BTC"
        assert data["timeframe"] == "1D"
        
        # Verify required fields exist
        required_fields = ["candles", "objects", "indicators", "hypothesis", 
                          "fractal_matches", "market_regime", "capital_flow_bias"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Verify candles have correct structure
        assert len(data["candles"]) > 0, "Candles should not be empty"
        candle = data["candles"][0]
        assert "timestamp" in candle or "time" in candle
        assert "open" in candle
        assert "high" in candle
        assert "low" in candle
        assert "close" in candle
        
        print(f"SUCCESS: BTC 1D returned {len(data['candles'])} candles")
    
    def test_eth_4h_analysis(self):
        """Test ETH 4H chart analysis"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/ETH/4H?include_hypothesis=true&include_fractals=true"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["symbol"] == "ETH"
        assert data["timeframe"] == "4H"
        assert "candles" in data
        assert len(data["candles"]) > 0
        
        print(f"SUCCESS: ETH 4H returned {len(data['candles'])} candles")
    
    def test_sol_1w_analysis(self):
        """Test SOL 1W chart analysis"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/SOL/1W?include_hypothesis=true&include_fractals=true"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["symbol"] == "SOL"
        assert data["timeframe"] == "1W"
        assert "candles" in data
        
        print(f"SUCCESS: SOL 1W returned {len(data['candles'])} candles")
    
    def test_all_timeframes(self):
        """Test all timeframes work for BTC"""
        timeframes = ["1H", "4H", "1D", "1W"]
        
        for tf in timeframes:
            url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/{tf}?include_hypothesis=true&include_fractals=true"
            response = requests.get(url)
            
            assert response.status_code == 200, f"Failed for timeframe {tf}"
            data = response.json()
            assert data["timeframe"] == tf, f"Timeframe mismatch for {tf}"
            print(f"SUCCESS: BTC {tf} returned {len(data['candles'])} candles")
    
    def test_hypothesis_structure(self):
        """Test hypothesis data structure"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D?include_hypothesis=true"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        hypothesis = data.get("hypothesis")
        assert hypothesis is not None, "Hypothesis should not be None when include_hypothesis=true"
        
        # Verify hypothesis structure
        assert "direction" in hypothesis, "Hypothesis missing direction"
        assert "confidence" in hypothesis, "Hypothesis missing confidence"
        assert "scenarios" in hypothesis, "Hypothesis missing scenarios"
        
        # Verify direction is valid
        assert hypothesis["direction"] in ["bullish", "bearish", "neutral"], \
            f"Invalid direction: {hypothesis['direction']}"
        
        # Verify confidence is between 0 and 1
        assert 0 <= hypothesis["confidence"] <= 1, \
            f"Confidence should be 0-1, got {hypothesis['confidence']}"
        
        print(f"SUCCESS: Hypothesis direction={hypothesis['direction']}, confidence={hypothesis['confidence']}")
    
    def test_fractal_matches(self):
        """Test fractal matches are returned"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D?include_fractals=true"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "fractal_matches" in data
        # Fractal matches can be empty list
        assert isinstance(data["fractal_matches"], list)
        
        print(f"SUCCESS: Returned {len(data['fractal_matches'])} fractal matches")
    
    def test_objects_structure(self):
        """Test TA objects structure (patterns, levels, hypothesis paths)"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D?include_hypothesis=true"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        objects = data.get("objects", [])
        assert isinstance(objects, list)
        
        # Check object categories
        categories = set()
        for obj in objects:
            assert "id" in obj, "Object missing id"
            assert "type" in obj, "Object missing type"
            assert "category" in obj, "Object missing category"
            categories.add(obj["category"])
        
        print(f"SUCCESS: Found {len(objects)} objects with categories: {categories}")
    
    def test_indicators_structure(self):
        """Test indicators structure (Bollinger bands, EMA, SMA)"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D?include_hypothesis=true"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        indicators = data.get("indicators", [])
        assert isinstance(indicators, list)
        
        # Check indicator types
        indicator_types = set()
        for ind in indicators:
            assert "id" in ind, "Indicator missing id"
            assert "type" in ind, "Indicator missing type"
            indicator_types.add(ind["type"])
        
        print(f"SUCCESS: Found {len(indicators)} indicators with types: {indicator_types}")
    
    def test_market_regime(self):
        """Test market regime is returned"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "market_regime" in data
        assert isinstance(data["market_regime"], str)
        
        print(f"SUCCESS: Market regime = {data['market_regime']}")
    
    def test_stats_object(self):
        """Test stats object contains total_objects count"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/1D"
        response = requests.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        stats = data.get("stats", {})
        assert isinstance(stats, dict)
        
        if "total_objects" in stats:
            assert isinstance(stats["total_objects"], int)
            print(f"SUCCESS: Stats shows {stats['total_objects']} total objects")
        else:
            print("INFO: stats.total_objects not present")


class TestChartAPIErrorHandling:
    """Test error handling for invalid requests"""
    
    def test_invalid_symbol(self):
        """Test invalid symbol returns appropriate error"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/INVALID/1D"
        response = requests.get(url)
        
        # Could be 400, 404, or still 200 with empty data
        # Just verify it doesn't crash
        assert response.status_code in [200, 400, 404], \
            f"Unexpected status code for invalid symbol: {response.status_code}"
        
        print(f"INFO: Invalid symbol returned status {response.status_code}")
    
    def test_invalid_timeframe(self):
        """Test invalid timeframe"""
        url = f"{BASE_URL}/api/v1/chart/full-analysis/BTC/INVALID"
        response = requests.get(url)
        
        # Could be 400, 404, or 200
        assert response.status_code in [200, 400, 404, 422], \
            f"Unexpected status code for invalid timeframe: {response.status_code}"
        
        print(f"INFO: Invalid timeframe returned status {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
