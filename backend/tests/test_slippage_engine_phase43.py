"""
Slippage Engine Test Suite - PHASE 4.3
======================================

Tests for the Slippage Engine execution intelligence module including:
- Slippage calculation
- Latency tracking
- Fill quality analysis  
- Liquidity impact assessment

All endpoints use mocked data for testing.
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSlippageHealth:
    """Health check endpoint tests"""
    
    def test_health_endpoint_returns_200(self):
        """GET /api/slippage/health - returns 200 with correct structure"""
        response = requests.get(f"{BASE_URL}/api/slippage/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["version"] == "phase_4.3"
        assert "components" in data
        assert isinstance(data["components"], list)
        assert len(data["components"]) == 4
        assert "slippage_calculator" in data["components"]
        assert "latency_tracker" in data["components"]
        assert "fill_analyzer" in data["components"]
        assert "liquidity_engine" in data["components"]
        print("✓ Health endpoint working correctly")


class TestSlippageStats:
    """Stats endpoint tests"""
    
    def test_stats_endpoint_returns_200(self):
        """GET /api/slippage/stats - returns 200 with stats"""
        response = requests.get(f"{BASE_URL}/api/slippage/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "version" in data
        assert data["version"] == "phase_4.3"
        assert "filters" in data
        assert "stats" in data
        print("✓ Stats endpoint working correctly")
    
    def test_stats_with_symbol_filter(self):
        """GET /api/slippage/stats?symbol=BTCUSDT - returns filtered stats"""
        response = requests.get(f"{BASE_URL}/api/slippage/stats?symbol=BTCUSDT")
        assert response.status_code == 200
        
        data = response.json()
        assert data["filters"]["symbol"] == "BTCUSDT"
        print("✓ Stats with symbol filter working")
    
    def test_stats_with_exchange_filter(self):
        """GET /api/slippage/stats?exchange=BINANCE - returns filtered stats"""
        response = requests.get(f"{BASE_URL}/api/slippage/stats?exchange=BINANCE")
        assert response.status_code == 200
        
        data = response.json()
        assert data["filters"]["exchange"] == "BINANCE"
        print("✓ Stats with exchange filter working")


class TestSlippageAnalyze:
    """POST /api/slippage/analyze - Full execution analysis tests"""
    
    def test_analyze_with_mock_data_generation(self):
        """POST /api/slippage/analyze - generates mock data when expected_price=0"""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY"
        }
        response = requests.post(f"{BASE_URL}/api/slippage/analyze", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        # Verify response structure
        assert "order_id" in data
        assert "symbol" in data
        assert data["symbol"] == "BTCUSDT"
        assert "side" in data
        assert data["side"] == "BUY"
        assert "expected_price" in data
        assert data["expected_price"] > 0  # Mock should generate price
        assert "executed_price" in data
        assert "slippage_percent" in data
        assert "slippage_bps" in data
        assert "slippage_direction" in data
        assert data["slippage_direction"] in ["FAVORABLE", "UNFAVORABLE", "ZERO"]
        assert "execution_latency_ms" in data
        assert "latency_grade" in data
        assert data["latency_grade"] in ["FAST", "NORMAL", "SLOW", "TIMEOUT", "UNKNOWN"]
        assert "fill_quality" in data
        assert data["fill_quality"] in ["EXCELLENT", "GOOD", "FAIR", "POOR", "FAILED"]
        assert "fill_rate" in data
        assert 0 <= data["fill_rate"] <= 1
        assert "liquidity_impact" in data
        assert "execution_score" in data
        assert 0 <= data["execution_score"] <= 1
        assert "execution_grade" in data
        assert data["execution_grade"] in ["A+", "A", "B", "C", "D", "F"]
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)
        assert "warnings" in data
        assert isinstance(data["warnings"], list)
        assert "computed_at" in data
        print("✓ Analyze with mock data generation working correctly")
    
    def test_analyze_with_custom_prices(self):
        """POST /api/slippage/analyze - with custom expected/executed prices"""
        order_id = f"TEST_{uuid.uuid4().hex[:8]}"
        payload = {
            "order_id": order_id,
            "symbol": "ETHUSDT",
            "exchange": "BYBIT",
            "side": "SELL",
            "order_type": "MARKET",
            "expected_price": 2500.0,
            "executed_price": 2498.0,
            "total_quantity": 1.5,
            "filled_quantity": 1.5
        }
        response = requests.post(f"{BASE_URL}/api/slippage/analyze", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["order_id"] == order_id
        assert data["symbol"] == "ETHUSDT"
        assert data["exchange"] == "BYBIT"
        assert data["side"] == "SELL"
        assert data["expected_price"] == 2500.0
        assert data["executed_price"] == 2498.0
        # For SELL, lower executed price = unfavorable slippage
        assert data["slippage_direction"] == "UNFAVORABLE"
        print("✓ Analyze with custom prices working correctly")
    
    def test_analyze_with_fills(self):
        """POST /api/slippage/analyze - with multiple fills (VWAP calculation)"""
        order_id = f"TEST_{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow()
        payload = {
            "order_id": order_id,
            "symbol": "BTCUSDT",
            "exchange": "BINANCE",
            "side": "BUY",
            "expected_price": 45000.0,
            "total_quantity": 1.0,
            "filled_quantity": 1.0,
            "fills": [
                {"quantity": 0.4, "price": 44990.0},
                {"quantity": 0.35, "price": 45000.0},
                {"quantity": 0.25, "price": 45010.0}
            ],
            "order_sent_time": (now - timedelta(milliseconds=200)).isoformat(),
            "exchange_ack_time": (now - timedelta(milliseconds=150)).isoformat(),
            "first_fill_time": (now - timedelta(milliseconds=100)).isoformat(),
            "last_fill_time": now.isoformat()
        }
        response = requests.post(f"{BASE_URL}/api/slippage/analyze", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["order_id"] == order_id
        # VWAP should be calculated from fills
        # (0.4*44990 + 0.35*45000 + 0.25*45010) / 1.0 = 44998.5
        assert data["executed_price"] > 0
        assert data["fill_rate"] == 1.0
        # Multiple fills should have some fragmentation
        print("✓ Analyze with fills (VWAP) working correctly")
    
    def test_analyze_favorable_slippage_buy(self):
        """POST /api/slippage/analyze - favorable slippage for BUY"""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "expected_price": 45000.0,
            "executed_price": 44950.0,  # Bought cheaper = favorable
            "total_quantity": 1.0,
            "filled_quantity": 1.0
        }
        response = requests.post(f"{BASE_URL}/api/slippage/analyze", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["slippage_direction"] == "FAVORABLE"
        assert data["slippage_bps"] < 0  # Negative slippage = favorable for BUY
        print("✓ Favorable slippage for BUY working correctly")
    
    def test_analyze_favorable_slippage_sell(self):
        """POST /api/slippage/analyze - favorable slippage for SELL"""
        payload = {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "expected_price": 45000.0,
            "executed_price": 45050.0,  # Sold higher = favorable
            "total_quantity": 1.0,
            "filled_quantity": 1.0
        }
        response = requests.post(f"{BASE_URL}/api/slippage/analyze", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["slippage_direction"] == "FAVORABLE"
        assert data["slippage_bps"] > 0  # Positive slippage = favorable for SELL
        print("✓ Favorable slippage for SELL working correctly")


class TestSlippageEstimate:
    """POST /api/slippage/estimate - Pre-execution slippage estimation tests"""
    
    def test_estimate_default_params(self):
        """POST /api/slippage/estimate - with default parameters"""
        payload = {}
        response = requests.post(f"{BASE_URL}/api/slippage/estimate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "slippage_estimate" in data
        assert "impact_estimate" in data
        assert "timestamp" in data
        
        # Check slippage estimate structure
        slip_est = data["slippage_estimate"]
        assert "symbol" in slip_est
        assert "side" in slip_est
        assert "quantity" in slip_est
        assert "current_price" in slip_est
        assert "estimated_slippage_bps" in slip_est
        assert "estimated_slippage_percent" in slip_est
        assert "estimated_executed_price" in slip_est
        assert "factors" in slip_est
        
        # Check impact estimate structure
        impact = data["impact_estimate"]
        assert "order_size" in impact
        assert "order_value" in impact
        assert "estimated_impact_bps" in impact
        assert "predicted_level" in impact
        assert impact["predicted_level"] in ["NEGLIGIBLE", "LOW", "MODERATE", "HIGH", "SEVERE"]
        assert "recommendation" in impact
        print("✓ Estimate with default params working correctly")
    
    def test_estimate_high_volatility(self):
        """POST /api/slippage/estimate - with high volatility"""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 1.0,
            "current_price": 45000.0,
            "volatility": 0.10,  # High volatility
            "liquidity_factor": 0.5  # Low liquidity
        }
        response = requests.post(f"{BASE_URL}/api/slippage/estimate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        slip_est = data["slippage_estimate"]
        # High vol + low liquidity should increase slippage estimate
        assert slip_est["estimated_slippage_bps"] > 10
        assert slip_est["factors"]["volatility_adj"] > 0
        assert slip_est["factors"]["liquidity_adj"] > 0
        print("✓ Estimate with high volatility working correctly")
    
    def test_estimate_large_order(self):
        """POST /api/slippage/estimate - with large order size"""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 10.0,  # Large order
            "current_price": 45000.0,
            "volatility": 0.02,
            "liquidity_factor": 0.8
        }
        response = requests.post(f"{BASE_URL}/api/slippage/estimate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        slip_est = data["slippage_estimate"]
        # Large order should have size adjustment
        assert slip_est["factors"]["size_adj"] > 0
        print("✓ Estimate with large order working correctly")


class TestSlippageBatch:
    """POST /api/slippage/batch - Batch execution analysis tests"""
    
    def test_batch_analysis_empty(self):
        """POST /api/slippage/batch - with empty orders list"""
        payload = {"orders": []}
        response = requests.post(f"{BASE_URL}/api/slippage/batch", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert data["count"] == 0
        assert "results" in data
        assert len(data["results"]) == 0
        print("✓ Batch with empty orders working correctly")
    
    def test_batch_analysis_multiple_orders(self):
        """POST /api/slippage/batch - with multiple orders"""
        payload = {
            "orders": [
                {"symbol": "BTCUSDT", "side": "BUY"},
                {"symbol": "ETHUSDT", "side": "SELL"},
                {"symbol": "SOLUSDT", "side": "BUY"}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/slippage/batch", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 3
        assert len(data["results"]) == 3
        
        # Check each result has required fields
        for result in data["results"]:
            assert "order_id" in result
            assert "symbol" in result
            assert "slippage_bps" in result
            assert "execution_score" in result
            assert "execution_grade" in result
        
        symbols = [r["symbol"] for r in data["results"]]
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols
        assert "SOLUSDT" in symbols
        print("✓ Batch with multiple orders working correctly")
    
    def test_batch_analysis_limit_20(self):
        """POST /api/slippage/batch - respects limit of 20 orders"""
        payload = {
            "orders": [{"symbol": "BTCUSDT", "side": "BUY"} for _ in range(25)]
        }
        response = requests.post(f"{BASE_URL}/api/slippage/batch", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        # Should be capped at 20
        assert data["count"] <= 20
        print("✓ Batch respects limit of 20 orders")


class TestSlippageHistory:
    """GET /api/slippage/history - Execution history tests"""
    
    def test_history_default(self):
        """GET /api/slippage/history - returns history with default params"""
        response = requests.get(f"{BASE_URL}/api/slippage/history")
        assert response.status_code == 200
        
        data = response.json()
        assert "filters" in data
        assert "count" in data
        assert "history" in data
        assert isinstance(data["history"], list)
        print("✓ History with default params working correctly")
    
    def test_history_with_symbol_filter(self):
        """GET /api/slippage/history?symbol=BTCUSDT - filtered by symbol"""
        response = requests.get(f"{BASE_URL}/api/slippage/history?symbol=BTCUSDT")
        assert response.status_code == 200
        
        data = response.json()
        assert data["filters"]["symbol"] == "BTCUSDT"
        print("✓ History with symbol filter working correctly")
    
    def test_history_with_exchange_filter(self):
        """GET /api/slippage/history?exchange=BINANCE - filtered by exchange"""
        response = requests.get(f"{BASE_URL}/api/slippage/history?exchange=BINANCE")
        assert response.status_code == 200
        
        data = response.json()
        assert data["filters"]["exchange"] == "BINANCE"
        print("✓ History with exchange filter working correctly")
    
    def test_history_with_limit(self):
        """GET /api/slippage/history?limit=10 - respects limit"""
        response = requests.get(f"{BASE_URL}/api/slippage/history?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["history"]) <= 10
        print("✓ History with limit working correctly")
    
    def test_history_with_min_grade_filter(self):
        """GET /api/slippage/history?min_grade=B - filtered by minimum grade"""
        response = requests.get(f"{BASE_URL}/api/slippage/history?min_grade=B")
        assert response.status_code == 200
        
        data = response.json()
        assert data["filters"]["min_grade"] == "B"
        print("✓ History with min_grade filter working correctly")


class TestSlippageOrderLookup:
    """GET /api/slippage/order/{order_id} - Order lookup tests"""
    
    def test_order_lookup_not_found(self):
        """GET /api/slippage/order/{order_id} - returns 404 for non-existent order"""
        fake_order_id = f"NONEXISTENT_{uuid.uuid4().hex}"
        response = requests.get(f"{BASE_URL}/api/slippage/order/{fake_order_id}")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        print("✓ Order lookup 404 for non-existent order working correctly")
    
    def test_order_lookup_after_analyze(self):
        """GET /api/slippage/order/{order_id} - returns order after analyze"""
        # First create an order via analyze
        order_id = f"TEST_{uuid.uuid4().hex[:8]}"
        analyze_payload = {
            "order_id": order_id,
            "symbol": "BTCUSDT",
            "exchange": "BINANCE",
            "side": "BUY",
            "expected_price": 45000.0,
            "executed_price": 45050.0,
            "total_quantity": 1.0,
            "filled_quantity": 1.0
        }
        analyze_response = requests.post(f"{BASE_URL}/api/slippage/analyze", json=analyze_payload)
        assert analyze_response.status_code == 200
        
        # Now lookup the order
        response = requests.get(f"{BASE_URL}/api/slippage/order/{order_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["order_id"] == order_id
        assert data["symbol"] == "BTCUSDT"
        assert data["exchange"] == "BINANCE"
        print("✓ Order lookup after analyze working correctly")


class TestSlippageSymbolStats:
    """GET /api/slippage/symbol/{symbol} - Symbol statistics tests"""
    
    def test_symbol_stats_btcusdt(self):
        """GET /api/slippage/symbol/BTCUSDT - returns symbol stats"""
        response = requests.get(f"{BASE_URL}/api/slippage/symbol/BTCUSDT")
        assert response.status_code == 200
        
        data = response.json()
        assert "symbol" in data
        assert data["symbol"] == "BTCUSDT"
        assert "stats" in data
        assert "recent_count" in data
        assert "recent" in data
        assert isinstance(data["recent"], list)
        print("✓ Symbol stats working correctly")
    
    def test_symbol_stats_with_limit(self):
        """GET /api/slippage/symbol/ETHUSDT?limit=5 - respects limit"""
        response = requests.get(f"{BASE_URL}/api/slippage/symbol/ETHUSDT?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data["symbol"] == "ETHUSDT"
        assert len(data["recent"]) <= 5
        print("✓ Symbol stats with limit working correctly")


class TestSlippageExchangeStats:
    """GET /api/slippage/exchange/{exchange} - Exchange statistics tests"""
    
    def test_exchange_stats_binance(self):
        """GET /api/slippage/exchange/BINANCE - returns exchange stats"""
        response = requests.get(f"{BASE_URL}/api/slippage/exchange/BINANCE")
        assert response.status_code == 200
        
        data = response.json()
        assert "exchange" in data
        assert data["exchange"] == "BINANCE"
        assert "stats" in data
        assert "recent_count" in data
        assert "recent" in data
        print("✓ Exchange stats working correctly")
    
    def test_exchange_stats_with_limit(self):
        """GET /api/slippage/exchange/BYBIT?limit=5 - respects limit"""
        response = requests.get(f"{BASE_URL}/api/slippage/exchange/BYBIT?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data["exchange"] == "BYBIT"
        assert len(data["recent"]) <= 5
        print("✓ Exchange stats with limit working correctly")


class TestSlippageExchangeComparison:
    """GET /api/slippage/exchange-comparison - Exchange comparison tests"""
    
    def test_exchange_comparison(self):
        """GET /api/slippage/exchange-comparison - returns comparison data"""
        response = requests.get(f"{BASE_URL}/api/slippage/exchange-comparison")
        assert response.status_code == 200
        
        data = response.json()
        assert "comparison" in data
        assert isinstance(data["comparison"], list)
        assert "timestamp" in data
        print("✓ Exchange comparison working correctly")


class TestSlippageDataPersistence:
    """Integration tests verifying data persistence flow"""
    
    def test_analyze_then_retrieve_flow(self):
        """Test full flow: analyze -> lookup -> verify persistence"""
        # Step 1: Create a unique order via analyze
        unique_id = f"PERSIST_TEST_{uuid.uuid4().hex[:8]}"
        analyze_payload = {
            "order_id": unique_id,
            "symbol": "SOLUSDT",
            "exchange": "OKX",
            "side": "BUY",
            "expected_price": 100.0,
            "executed_price": 100.15,
            "total_quantity": 10.0,
            "filled_quantity": 10.0
        }
        
        analyze_response = requests.post(f"{BASE_URL}/api/slippage/analyze", json=analyze_payload)
        assert analyze_response.status_code == 200
        analyzed_data = analyze_response.json()
        
        # Step 2: Retrieve via order lookup
        lookup_response = requests.get(f"{BASE_URL}/api/slippage/order/{unique_id}")
        assert lookup_response.status_code == 200
        lookup_data = lookup_response.json()
        
        # Step 3: Verify data matches
        assert lookup_data["order_id"] == unique_id
        assert lookup_data["symbol"] == "SOLUSDT"
        assert lookup_data["exchange"] == "OKX"
        assert lookup_data["side"] == "BUY"
        print("✓ Analyze -> Retrieve persistence flow working correctly")
    
    def test_symbol_history_after_analyze(self):
        """Test that analyzed orders appear in symbol history"""
        # Create a unique order
        unique_id = f"HISTORY_TEST_{uuid.uuid4().hex[:8]}"
        analyze_payload = {
            "order_id": unique_id,
            "symbol": "AVAXUSDT",
            "exchange": "BINANCE",
            "side": "SELL",
            "expected_price": 35.0,
            "executed_price": 34.90,
            "total_quantity": 50.0,
            "filled_quantity": 50.0
        }
        
        analyze_response = requests.post(f"{BASE_URL}/api/slippage/analyze", json=analyze_payload)
        assert analyze_response.status_code == 200
        
        # Check symbol stats includes this order
        symbol_response = requests.get(f"{BASE_URL}/api/slippage/symbol/AVAXUSDT?limit=50")
        assert symbol_response.status_code == 200
        symbol_data = symbol_response.json()
        
        # Find the order in recent
        order_ids = [r.get("order_id") for r in symbol_data["recent"]]
        assert unique_id in order_ids, f"Order {unique_id} not found in symbol history"
        print("✓ Symbol history after analyze working correctly")


# Run tests when script is executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
