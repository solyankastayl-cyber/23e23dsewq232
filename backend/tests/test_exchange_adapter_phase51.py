"""
Exchange Adapter Layer PHASE 5.1 - Comprehensive API Tests
==========================================================

Tests for the Exchange Adapter Layer module including:
- Connection management
- Account operations (balances, positions)
- Order operations (create, cancel, status)
- Market data (ticker, orderbook)
- WebSocket streams
- Exchange routing
"""

import pytest
import requests
import os
import time
from datetime import datetime

# Get base URL from environment
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://tech-analysis-core-1.preview.emergentagent.com"


class TestExchangeHealth:
    """Health check endpoint tests"""
    
    def test_health_endpoint_returns_200(self):
        """GET /api/exchange/health - basic health check"""
        response = requests.get(f"{BASE_URL}/api/exchange/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "phase_5.1"
        assert "BINANCE" in data["supported_exchanges"]
        assert "BYBIT" in data["supported_exchanges"]
        assert "OKX" in data["supported_exchanges"]
        print("✓ Health endpoint returns healthy status with 3 supported exchanges")


class TestConnectionManagement:
    """Connection management tests"""
    
    def test_connect_binance(self):
        """POST /api/exchange/connect - connect to Binance"""
        response = requests.post(
            f"{BASE_URL}/api/exchange/connect",
            json={"exchange": "BINANCE", "testnet": True}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["exchange"] == "BINANCE"
        assert data["connected"] == True
        assert data["testnet"] == True
        print("✓ Connected to Binance testnet")
    
    def test_connect_okx(self):
        """POST /api/exchange/connect - connect to OKX"""
        response = requests.post(
            f"{BASE_URL}/api/exchange/connect",
            json={"exchange": "OKX", "testnet": True}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["exchange"] == "OKX"
        assert data["connected"] == True
        print("✓ Connected to OKX")
    
    def test_get_status(self):
        """GET /api/exchange/status - get router status"""
        response = requests.get(f"{BASE_URL}/api/exchange/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "router_status" in data
        assert "registered_exchanges" in data["router_status"]
        assert "connections" in data["router_status"]
        print(f"✓ Router status: {len(data['router_status']['registered_exchanges'])} exchanges registered")
    
    def test_get_exchange_status(self):
        """GET /api/exchange/status?exchange=BINANCE - get specific exchange status"""
        response = requests.get(f"{BASE_URL}/api/exchange/status?exchange=BINANCE")
        assert response.status_code == 200
        
        data = response.json()
        assert data["exchange"] == "BINANCE"
        print("✓ Got Binance specific status")


class TestAccountOperations:
    """Account operations tests"""
    
    def test_get_balances(self):
        """GET /api/exchange/balances - get account balances"""
        # Ensure connected
        requests.post(
            f"{BASE_URL}/api/exchange/connect",
            json={"exchange": "BINANCE", "testnet": True}
        )
        
        response = requests.get(f"{BASE_URL}/api/exchange/balances")
        assert response.status_code == 200
        
        data = response.json()
        assert "balances" in data
        
        # Should have mock balances
        if "BINANCE" in data["balances"]:
            balances = data["balances"]["BINANCE"]
            assert len(balances) > 0
            for bal in balances:
                assert "asset" in bal
                assert "free" in bal
                assert "total" in bal
        
        print(f"✓ Got balances from {len(data['balances'])} exchanges")
    
    def test_get_positions(self):
        """GET /api/exchange/positions - get open positions"""
        response = requests.get(f"{BASE_URL}/api/exchange/positions")
        assert response.status_code == 200
        
        data = response.json()
        assert "positions" in data
        
        # Check position structure if exists
        if "BINANCE" in data["positions"] and data["positions"]["BINANCE"]:
            pos = data["positions"]["BINANCE"][0]
            assert "symbol" in pos
            assert "side" in pos
            assert "size" in pos
            assert "entry_price" in pos
        
        print(f"✓ Got positions from {len(data['positions'])} exchanges")
    
    def test_get_open_orders(self):
        """GET /api/exchange/open-orders - get open orders"""
        response = requests.get(f"{BASE_URL}/api/exchange/open-orders")
        assert response.status_code == 200
        
        data = response.json()
        assert "open_orders" in data
        print("✓ Got open orders")


class TestOrderOperations:
    """Order operations tests"""
    
    def test_create_market_order(self):
        """POST /api/exchange/create-order - create market order"""
        # Ensure connected
        requests.post(
            f"{BASE_URL}/api/exchange/connect",
            json={"exchange": "BINANCE", "testnet": True}
        )
        
        response = requests.post(
            f"{BASE_URL}/api/exchange/create-order",
            json={
                "exchange": "BINANCE",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "size": 0.01
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "order" in data
        order = data["order"]
        assert order["exchange"] == "BINANCE"
        assert order["symbol"] == "BTCUSDT"
        assert order["side"] == "BUY"
        assert order["order_type"] == "MARKET"
        assert "exchange_order_id" in order
        assert "status" in order
        
        print(f"✓ Created market order: {order['exchange_order_id']}")
        return order["exchange_order_id"]
    
    def test_create_limit_order(self):
        """POST /api/exchange/create-order - create limit order"""
        response = requests.post(
            f"{BASE_URL}/api/exchange/create-order",
            json={
                "exchange": "BINANCE",
                "symbol": "ETHUSDT",
                "side": "SELL",
                "order_type": "LIMIT",
                "size": 0.1,
                "price": 3000.0,
                "time_in_force": "GTC"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "order" in data
        print(f"✓ Created limit order")


class TestMarketData:
    """Market data tests"""
    
    def test_get_ticker(self):
        """GET /api/exchange/ticker/{symbol} - get ticker"""
        # Ensure connected
        requests.post(
            f"{BASE_URL}/api/exchange/connect",
            json={"exchange": "BINANCE", "testnet": True}
        )
        
        response = requests.get(f"{BASE_URL}/api/exchange/ticker/BTCUSDT?exchange=BINANCE")
        assert response.status_code == 200
        
        data = response.json()
        assert "ticker" in data
        ticker = data["ticker"]
        assert ticker["exchange"] == "BINANCE"
        assert ticker["symbol"] == "BTCUSDT"
        assert "last_price" in ticker
        assert ticker["last_price"] > 0
        
        print(f"✓ Got ticker: BTCUSDT @ ${ticker['last_price']}")
    
    def test_get_orderbook(self):
        """GET /api/exchange/orderbook/{symbol} - get orderbook"""
        response = requests.get(f"{BASE_URL}/api/exchange/orderbook/BTCUSDT?exchange=BINANCE&depth=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "orderbook" in data
        ob = data["orderbook"]
        assert ob["exchange"] == "BINANCE"
        assert ob["symbol"] == "BTCUSDT"
        assert "bids" in ob
        assert "asks" in ob
        assert len(ob["bids"]) > 0 or len(ob["asks"]) > 0
        
        print(f"✓ Got orderbook: {len(ob['bids'])} bids, {len(ob['asks'])} asks")
    
    def test_get_best_price(self):
        """GET /api/exchange/best-price/{symbol} - get best price across exchanges"""
        response = requests.get(f"{BASE_URL}/api/exchange/best-price/BTCUSDT?side=BUY")
        assert response.status_code == 200
        
        data = response.json()
        assert "best_price" in data
        print("✓ Got best price")


class TestWebSocketStreams:
    """WebSocket stream tests"""
    
    def test_start_ticker_stream(self):
        """POST /api/exchange/stream/start - start ticker stream"""
        # Ensure connected
        requests.post(
            f"{BASE_URL}/api/exchange/connect",
            json={"exchange": "BINANCE", "testnet": True}
        )
        
        response = requests.post(
            f"{BASE_URL}/api/exchange/stream/start",
            json={
                "exchange": "BINANCE",
                "stream_type": "TICKER",
                "symbols": ["BTCUSDT", "ETHUSDT"]
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["started"] == True
        assert data["exchange"] == "BINANCE"
        assert data["stream_type"] == "TICKER"
        assert "BTCUSDT" in data["symbols"]
        
        print("✓ Started ticker stream")
    
    def test_start_orderbook_stream(self):
        """POST /api/exchange/stream/start - start orderbook stream"""
        response = requests.post(
            f"{BASE_URL}/api/exchange/stream/start",
            json={
                "exchange": "BINANCE",
                "stream_type": "ORDERBOOK",
                "symbols": ["BTCUSDT"]
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["started"] == True
        print("✓ Started orderbook stream")
    
    def test_get_stream_status(self):
        """GET /api/exchange/stream/status - get stream status"""
        response = requests.get(f"{BASE_URL}/api/exchange/stream/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "streams" in data
        assert "active_streams" in data
        
        print(f"✓ Got stream status: {len(data['active_streams'])} active streams")
    
    def test_stop_stream(self):
        """POST /api/exchange/stream/stop - stop stream"""
        response = requests.post(
            f"{BASE_URL}/api/exchange/stream/stop",
            json={
                "exchange": "BINANCE",
                "stream_type": "ORDERBOOK",
                "symbols": ["BTCUSDT"]
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["stopped"] == True
        print("✓ Stopped orderbook stream")


class TestHistory:
    """History and statistics tests"""
    
    def test_get_order_history(self):
        """GET /api/exchange/history/orders - get order history"""
        response = requests.get(f"{BASE_URL}/api/exchange/history/orders?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "orders" in data
        assert "count" in data
        
        print(f"✓ Got order history: {data['count']} orders")
    
    def test_get_position_history(self):
        """GET /api/exchange/history/positions - get position history"""
        response = requests.get(f"{BASE_URL}/api/exchange/history/positions?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "positions" in data
        print("✓ Got position history")
    
    def test_get_balance_history(self):
        """GET /api/exchange/history/balances - get balance history"""
        response = requests.get(f"{BASE_URL}/api/exchange/history/balances?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "balances" in data
        print("✓ Got balance history")
    
    def test_get_order_stats(self):
        """GET /api/exchange/stats/orders - get order statistics"""
        response = requests.get(f"{BASE_URL}/api/exchange/stats/orders?days=7")
        assert response.status_code == 200
        
        data = response.json()
        assert "stats" in data
        print("✓ Got order statistics")


class TestErrorHandling:
    """Error handling tests"""
    
    def test_unknown_exchange(self):
        """Test error on unknown exchange"""
        response = requests.post(
            f"{BASE_URL}/api/exchange/connect",
            json={"exchange": "UNKNOWN_EXCHANGE"}
        )
        assert response.status_code == 400
        print("✓ Properly rejects unknown exchange")
    
    def test_invalid_order_side(self):
        """Test error on invalid order side"""
        # Connect first
        requests.post(
            f"{BASE_URL}/api/exchange/connect",
            json={"exchange": "BINANCE", "testnet": True}
        )
        
        response = requests.post(
            f"{BASE_URL}/api/exchange/create-order",
            json={
                "exchange": "BINANCE",
                "symbol": "BTCUSDT",
                "side": "INVALID",
                "order_type": "MARKET",
                "size": 0.01
            }
        )
        assert response.status_code == 400
        print("✓ Properly rejects invalid order side")


class TestIntegration:
    """Integration workflow tests"""
    
    def test_full_trading_workflow(self):
        """Test complete trading workflow"""
        # 1. Connect
        connect_response = requests.post(
            f"{BASE_URL}/api/exchange/connect",
            json={"exchange": "BINANCE", "testnet": True}
        )
        assert connect_response.status_code == 200
        assert connect_response.json()["connected"] == True
        
        # 2. Check balance
        balance_response = requests.get(f"{BASE_URL}/api/exchange/balances?exchange=BINANCE")
        assert balance_response.status_code == 200
        
        # 3. Get market price
        ticker_response = requests.get(f"{BASE_URL}/api/exchange/ticker/BTCUSDT?exchange=BINANCE")
        assert ticker_response.status_code == 200
        
        # 4. Place order
        order_response = requests.post(
            f"{BASE_URL}/api/exchange/create-order",
            json={
                "exchange": "BINANCE",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "size": 0.01
            }
        )
        assert order_response.status_code == 200
        
        # 5. Check positions
        position_response = requests.get(f"{BASE_URL}/api/exchange/positions?exchange=BINANCE")
        assert position_response.status_code == 200
        
        print("✓ Full trading workflow completed successfully")


# Cleanup
@pytest.fixture(scope="module", autouse=True)
def cleanup_after_tests():
    """Cleanup after all tests"""
    yield
    # Disconnect all exchanges
    for exchange in ["BINANCE", "BYBIT", "OKX"]:
        try:
            requests.post(f"{BASE_URL}/api/exchange/disconnect?exchange={exchange}")
        except:
            pass
    print("✓ Cleanup: Disconnected all exchanges")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
