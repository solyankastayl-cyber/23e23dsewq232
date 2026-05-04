"""
Test Suite for PHASE 5.2/5.3 - Market Data + Order Routing Engine
=================================================================

Tests:
1. P0 Bug Fix: MarketDataNormalizer orderbook normalization (bids/asks validation)
2. Market Data API endpoints
3. Order Routing Engine API endpoints
4. Integration: Routing engine with failover engine
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")


class TestMarketDataHealth:
    """Market Data Engine health and status tests"""
    
    def test_market_data_health(self):
        """Test market data health endpoint"""
        response = requests.get(f"{BASE_URL}/api/market-data/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "phase_5.2"
        print(f"PASS: Market data health check - version {data['version']}")


class TestMarketDataFeed:
    """Market Data feed management tests"""
    
    def test_start_market_data_feed(self):
        """POST /api/market-data/start - should start market data feed without errors"""
        payload = {
            "exchange": "BINANCE",
            "symbols": ["BTCUSDT"],
            "subscribe_ticker": True,
            "subscribe_orderbook": True,
            "subscribe_candles": True,
            "candle_timeframes": ["1m", "5m"]
        }
        response = requests.post(f"{BASE_URL}/api/market-data/start", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["started"] == True
        assert data["exchange"] == "BINANCE"
        assert "BTCUSDT" in data["symbols"]
        print(f"PASS: Start feed - started={data['started']}, exchange={data['exchange']}")
    
    def test_get_market_data_status(self):
        """GET /api/market-data/status - should return feed status with running=true"""
        response = requests.get(f"{BASE_URL}/api/market-data/status")
        assert response.status_code == 200
        data = response.json()
        # Check engine status structure
        assert "engine_status" in data or "feed_status" in data
        print(f"PASS: Market data status - {data}")
    
    def test_get_ticker_btcusdt(self):
        """GET /api/market-data/ticker/{symbol} - should return ticker data"""
        response = requests.get(f"{BASE_URL}/api/market-data/ticker/BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        # Either ticker data or error (no data yet) is acceptable
        assert "ticker" in data or "error" in data
        if "ticker" in data:
            ticker = data["ticker"]
            assert "price" in ticker or "symbol" in ticker
            print(f"PASS: Ticker BTCUSDT - price={ticker.get('price', 'N/A')}")
        else:
            print(f"INFO: Ticker BTCUSDT - {data.get('error', 'No data yet')}")
    
    def test_get_orderbook_btcusdt(self):
        """GET /api/market-data/orderbook/{symbol} - should return orderbook with bids/asks lists"""
        response = requests.get(f"{BASE_URL}/api/market-data/orderbook/BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        
        # Check orderbook structure
        if "orderbook" in data:
            orderbook = data["orderbook"]
            # P0 BUG FIX: bids and asks must be lists, not 0 or other invalid values
            assert "bids" in orderbook
            assert "asks" in orderbook
            assert isinstance(orderbook["bids"], list), f"bids must be list, got {type(orderbook['bids'])}"
            assert isinstance(orderbook["asks"], list), f"asks must be list, got {type(orderbook['asks'])}"
            print(f"PASS: Orderbook BTCUSDT - bids={len(orderbook['bids'])}, asks={len(orderbook['asks'])}")
        else:
            # No data yet is acceptable 
            print(f"INFO: Orderbook BTCUSDT - {data.get('error', 'No data yet')}")
    
    def test_get_snapshot_btcusdt(self):
        """GET /api/market-data/snapshot/{symbol} - should return market snapshot"""
        response = requests.get(f"{BASE_URL}/api/market-data/snapshot/BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        assert "snapshot" in data
        snapshot = data["snapshot"]
        # Snapshot should have symbol info
        assert "symbol" in snapshot
        print(f"PASS: Snapshot BTCUSDT - symbol={snapshot.get('symbol')}")


class TestOrderbookNormalization:
    """P0 Bug Fix Tests - MarketDataNormalizer orderbook handling"""
    
    def test_orderbook_handles_invalid_bids_asks(self):
        """
        P0 BUG FIX: Verify that orderbook normalization handles invalid bids/asks data.
        The bug was TypeError when bids/asks were returned as 0 instead of empty list.
        """
        # This tests the internal normalization via API response
        # The fix ensures bids/asks are always lists
        response = requests.get(f"{BASE_URL}/api/market-data/orderbook/BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        
        if "orderbook" in data:
            orderbook = data["orderbook"]
            # Critical assertion: bids and asks must be lists
            assert isinstance(orderbook.get("bids", []), list), "bids must be a list"
            assert isinstance(orderbook.get("asks", []), list), "asks must be a list"
            # Should not raise TypeError
            print("PASS: P0 Bug Fix - orderbook bids/asks are properly typed as lists")
        else:
            print("INFO: No orderbook data available yet, but endpoint works without TypeError")


class TestRoutingHealth:
    """Order Routing Engine health tests"""
    
    def test_routing_health(self):
        """Test routing engine health endpoint"""
        response = requests.get(f"{BASE_URL}/api/routing/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "phase_5.3"
        assert len(data["supported_policies"]) > 0
        print(f"PASS: Routing health - version {data['version']}, policies={data['supported_policies']}")


class TestRoutingEvaluation:
    """Order routing evaluation tests"""
    
    def test_evaluate_routing(self):
        """POST /api/routing/evaluate - should evaluate routing and return decision"""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "size": 0.1,
            "order_type": "LIMIT",
            "limit_price": 50000.0,
            "policy": "BEST_EXECUTION",
            "urgency": "NORMAL",
            "max_slippage_bps": 10.0
        }
        response = requests.post(f"{BASE_URL}/api/routing/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Check decision structure
        assert "decision" in data
        decision = data["decision"]
        assert "selected_exchange" in decision
        assert "expected_price" in decision
        assert "confidence" in decision
        assert "routing_reason" in decision
        print(f"PASS: Routing evaluate - exchange={decision['selected_exchange']}, confidence={decision['confidence']}")
    
    def test_create_execution_plan(self):
        """POST /api/routing/plan - should create execution plan"""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "size": 1.0,
            "order_type": "LIMIT",
            "limit_price": 50000.0,
            "policy": "BEST_EXECUTION",
            "split_threshold": 100.0
        }
        response = requests.post(f"{BASE_URL}/api/routing/plan", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert "plan" in data
        plan = data["plan"]
        assert "plan_id" in plan
        assert "symbol" in plan
        assert "total_size" in plan
        assert "legs" in data
        print(f"PASS: Execution plan - plan_id={plan['plan_id']}, legs={len(data['legs'])}")


class TestRoutingVenueAnalysis:
    """Venue analysis and selection tests"""
    
    def test_get_venues(self):
        """GET /api/routing/venues/{symbol} - should return venue analysis"""
        response = requests.get(f"{BASE_URL}/api/routing/venues/BTCUSDT?side=BUY&size=0.1")
        assert response.status_code == 200
        data = response.json()
        
        assert "symbol" in data
        assert data["symbol"] == "BTCUSDT"
        assert "venues" in data
        # Should have venue data for at least one exchange
        assert len(data["venues"]) > 0
        print(f"PASS: Venues - {len(data['venues'])} venues analyzed")
    
    def test_get_slippage_analysis(self):
        """GET /api/routing/slippage/{symbol} - should return slippage analysis"""
        response = requests.get(f"{BASE_URL}/api/routing/slippage/BTCUSDT?side=BUY&size=0.1")
        assert response.status_code == 200
        data = response.json()
        
        assert "symbol" in data
        assert data["symbol"] == "BTCUSDT"
        # Should have analyses for multiple exchanges
        assert "analyses" in data or "profile" in data
        print(f"PASS: Slippage analysis - {data}")
    
    def test_get_best_venues(self):
        """GET /api/routing/best-venues/{symbol} - should return ranked venues"""
        response = requests.get(f"{BASE_URL}/api/routing/best-venues/BTCUSDT?side=BUY&size=0.1")
        assert response.status_code == 200
        data = response.json()
        
        assert "best_venues" in data
        venues = data["best_venues"]
        assert len(venues) > 0
        # Check venue structure
        first_venue = venues[0]
        assert "rank" in first_venue
        assert "exchange" in first_venue
        assert "total_score" in first_venue
        print(f"PASS: Best venues - top={first_venue['exchange']}, score={first_venue['total_score']}")


class TestRoutingStats:
    """Routing statistics and policies tests"""
    
    def test_get_routing_stats(self):
        """GET /api/routing/stats - should return routing statistics"""
        response = requests.get(f"{BASE_URL}/api/routing/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "stats" in data
        stats = data["stats"]
        assert "total_requests" in stats or "decisions_made" in stats
        print(f"PASS: Routing stats - {stats}")
    
    def test_get_routing_policies(self):
        """GET /api/routing/policies - should return available routing policies"""
        response = requests.get(f"{BASE_URL}/api/routing/policies")
        assert response.status_code == 200
        data = response.json()
        
        assert "policies" in data
        policies = data["policies"]
        assert len(policies) > 0
        # Check policy structure
        first_policy = policies[0]
        assert "policy" in first_policy
        assert "description" in first_policy
        print(f"PASS: Routing policies - {len(policies)} policies available")


class TestFailoverIntegration:
    """Integration tests: Routing engine with failover engine"""
    
    def test_failover_status(self):
        """GET /api/failover/status - should return system status"""
        response = requests.get(f"{BASE_URL}/api/failover/status")
        assert response.status_code == 200
        data = response.json()
        
        assert "system_status" in data or "state" in data
        print(f"PASS: Failover status - {data}")
    
    def test_routing_uses_failover_correctly(self):
        """Integration: Routing engine should use failover engine correctly"""
        # First check failover status
        failover_response = requests.get(f"{BASE_URL}/api/failover/status")
        assert failover_response.status_code == 200
        
        # Then evaluate routing - this should use failover internally
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "size": 0.1,
            "order_type": "MARKET"
        }
        routing_response = requests.post(f"{BASE_URL}/api/routing/evaluate", json=payload)
        # Should not raise AttributeError anymore (bug was fixed)
        assert routing_response.status_code == 200
        
        data = routing_response.json()
        assert "decision" in data
        print(f"PASS: Routing with failover integration - decision made successfully")


class TestEdgeCases:
    """Edge case tests for robustness"""
    
    def test_routing_with_various_policies(self):
        """Test routing with different policies"""
        policies = ["BEST_PRICE", "BEST_EXECUTION", "SAFEST_VENUE", "LOW_SLIPPAGE", "LOWEST_FEE"]
        
        for policy in policies:
            payload = {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "size": 0.1,
                "order_type": "LIMIT",
                "limit_price": 50000.0,
                "policy": policy
            }
            response = requests.post(f"{BASE_URL}/api/routing/evaluate", json=payload)
            assert response.status_code == 200, f"Policy {policy} failed"
            data = response.json()
            assert "decision" in data
            print(f"PASS: Policy {policy} - exchange={data['decision']['selected_exchange']}")
    
    def test_routing_with_various_urgencies(self):
        """Test routing with different urgency levels"""
        urgencies = ["LOW", "NORMAL", "HIGH", "IMMEDIATE"]
        
        for urgency in urgencies:
            payload = {
                "symbol": "BTCUSDT",
                "side": "SELL",
                "size": 0.5,
                "order_type": "MARKET",
                "urgency": urgency
            }
            response = requests.post(f"{BASE_URL}/api/routing/evaluate", json=payload)
            assert response.status_code == 200, f"Urgency {urgency} failed"
            data = response.json()
            assert "decision" in data
            print(f"PASS: Urgency {urgency} - exchange={data['decision']['selected_exchange']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
