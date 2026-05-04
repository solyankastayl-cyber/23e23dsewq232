"""
TR6 Trading Dashboard API Tests
================================

Comprehensive tests for Trading Dashboard module.
Tests all 17 API endpoints for the TR6 dashboard that aggregates data 
from modules TR1-TR5 and STR4.

Endpoints tested:
- Health & State: /api/dashboard/health, /state, /summary
- Widgets: /portfolio, /strategy, /risk, /trades, /accounts, /alerts, /system, /widgets
- Snapshots: POST /snapshot, GET /snapshots
- Events: GET /events, /events/types
- Stream: GET /stream/status
- Modules: GET /modules
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestTR6DashboardHealth:
    """TR6 Health and basic state tests"""
    
    def test_health_endpoint(self):
        """GET /api/dashboard/health - TR6 module health check"""
        response = requests.get(f"{BASE_URL}/api/dashboard/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Status assertions
        assert data["module"] == "Trading Dashboard Service"
        assert data["phase"] == "TR6"
        assert data["status"] == "healthy"
        
        # System health should be present
        assert "systemHealth" in data
        assert data["systemHealth"] in ["HEALTHY", "WARNING", "DEGRADED", "CRITICAL"]
        
        # Components should all be present
        assert "components" in data
        assert "aggregator" in data["components"]
        assert "widgets" in data["components"]
        assert "stream" in data["components"]
        assert "repository" in data["components"]
        
        # Modules status
        assert "modules" in data
        for module_name in ["portfolio", "strategy", "risk", "trades", "accounts"]:
            assert module_name in data["modules"]
        
        print(f"✓ TR6 Health check passed. Status: {data['status']}, SystemHealth: {data['systemHealth']}")
    
    def test_dashboard_state(self):
        """GET /api/dashboard/state - Unified dashboard state"""
        response = requests.get(f"{BASE_URL}/api/dashboard/state")
        
        assert response.status_code == 200
        data = response.json()
        
        # Required top-level fields
        assert "dashboardId" in data
        assert data["dashboardId"].startswith("dash_")
        
        # Module summaries should be present
        assert "portfolio" in data
        assert "strategy" in data
        assert "risk" in data
        assert "trades" in data
        assert "accounts" in data
        
        # System health
        assert "systemHealth" in data
        assert data["systemHealth"] in ["HEALTHY", "WARNING", "DEGRADED", "CRITICAL"]
        assert "healthReasons" in data
        assert isinstance(data["healthReasons"], list)
        
        # Timestamp
        assert "generatedAt" in data
        
        # Portfolio data structure
        portfolio = data["portfolio"]
        assert "equity" in portfolio
        assert "availableBalance" in portfolio
        assert "dailyPnl" in portfolio
        assert "openPositions" in portfolio
        
        print(f"✓ Dashboard state retrieved. ID: {data['dashboardId']}, Health: {data['systemHealth']}")
    
    def test_quick_summary(self):
        """GET /api/dashboard/summary - Lightweight polling summary"""
        response = requests.get(f"{BASE_URL}/api/dashboard/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # All summary fields should be present
        required_fields = ["equity", "dailyPnl", "positions", "profile", "mode", "riskLevel", "alerts", "health"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Validate types
        assert isinstance(data["equity"], (int, float))
        assert isinstance(data["dailyPnl"], (int, float))
        assert isinstance(data["positions"], int)
        assert isinstance(data["alerts"], int)
        assert data["health"] in ["HEALTHY", "WARNING", "DEGRADED", "CRITICAL"]
        
        print(f"✓ Quick summary: equity={data['equity']}, positions={data['positions']}, health={data['health']}")


class TestTR6DashboardWidgets:
    """Individual widget endpoint tests"""
    
    def test_portfolio_widget(self):
        """GET /api/dashboard/portfolio - Portfolio widget"""
        response = requests.get(f"{BASE_URL}/api/dashboard/portfolio")
        
        assert response.status_code == 200
        data = response.json()
        
        # Widget structure
        assert "widgetId" in data
        assert data["widgetId"].startswith("wgt_")
        assert data["widgetType"] == "PORTFOLIO"
        assert "payload" in data
        assert "updatedAt" in data
        
        # Payload structure
        payload = data["payload"]
        assert "equity" in payload
        assert "available" in payload
        assert "dailyPnl" in payload
        assert "positions" in payload or "positionsCount" in payload
        assert "exposure" in payload
        
        print(f"✓ Portfolio widget: equity={payload['equity']}, exposure={payload['exposure']}")
    
    def test_strategy_widget(self):
        """GET /api/dashboard/strategy - Strategy widget"""
        response = requests.get(f"{BASE_URL}/api/dashboard/strategy")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["widgetType"] == "STRATEGY"
        payload = data["payload"]
        
        assert "activeProfile" in payload
        assert payload["activeProfile"] in ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]
        assert "mode" in payload
        assert "tradingEnabled" in payload
        assert "paused" in payload
        assert "killSwitch" in payload
        assert "active" in payload["killSwitch"]
        
        print(f"✓ Strategy widget: profile={payload['activeProfile']}, mode={payload['mode']}")
    
    def test_risk_widget(self):
        """GET /api/dashboard/risk - Risk widget"""
        response = requests.get(f"{BASE_URL}/api/dashboard/risk")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["widgetType"] == "RISK"
        payload = data["payload"]
        
        assert "riskLevel" in payload
        assert payload["riskLevel"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
        assert "drawdown" in payload
        assert "dailyLoss" in payload
        assert "exposure" in payload
        assert "leverage" in payload
        assert "tailRisk" in payload
        assert "alerts" in payload
        assert "alertsCount" in payload
        
        print(f"✓ Risk widget: level={payload['riskLevel']}, leverage={payload['leverage']}")
    
    def test_trades_widget(self):
        """GET /api/dashboard/trades - Trades widget"""
        response = requests.get(f"{BASE_URL}/api/dashboard/trades")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["widgetType"] == "TRADES"
        payload = data["payload"]
        
        assert "recentOrders" in payload
        assert "recentFills" in payload
        assert "recentTrades" in payload
        assert "ordersCount" in payload
        assert "fillsCount" in payload
        assert "tradesCount" in payload
        
        print(f"✓ Trades widget: orders={payload['ordersCount']}, fills={payload['fillsCount']}")
    
    def test_accounts_widget(self):
        """GET /api/dashboard/accounts - Accounts widget"""
        response = requests.get(f"{BASE_URL}/api/dashboard/accounts")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["widgetType"] == "ACCOUNTS"
        payload = data["payload"]
        
        assert "exchanges" in payload
        assert isinstance(payload["exchanges"], list)
        assert "balances" in payload
        assert "total" in payload["balances"]
        assert "health" in payload
        assert "connected" in payload["health"]
        assert "healthy" in payload["health"]
        
        print(f"✓ Accounts widget: connected={payload['health']['connected']}, total=${payload['balances']['total']}")
    
    def test_alerts_widget(self):
        """GET /api/dashboard/alerts - Alerts widget"""
        response = requests.get(f"{BASE_URL}/api/dashboard/alerts")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["widgetType"] == "ALERTS"
        payload = data["payload"]
        
        assert "alerts" in payload
        assert isinstance(payload["alerts"], list)
        assert "totalCount" in payload
        assert "bySource" in payload
        
        # Verify alert structure if there are alerts
        if payload["alerts"]:
            alert = payload["alerts"][0]
            assert "id" in alert
            assert "source" in alert
            assert "type" in alert
            assert "severity" in alert
        
        print(f"✓ Alerts widget: totalCount={payload['totalCount']}, sources={payload['bySource']}")
    
    def test_system_widget(self):
        """GET /api/dashboard/system - System health widget"""
        response = requests.get(f"{BASE_URL}/api/dashboard/system")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["widgetType"] == "SYSTEM"
        payload = data["payload"]
        
        assert "health" in payload
        assert payload["health"] in ["HEALTHY", "WARNING", "DEGRADED", "CRITICAL"]
        assert "reasons" in payload
        assert isinstance(payload["reasons"], list)
        assert "modules" in payload
        assert "uptime" in payload
        assert "generatedAt" in payload
        
        # All modules should have status
        for module_name in ["portfolio", "strategy", "risk", "trades", "accounts"]:
            assert module_name in payload["modules"]
        
        print(f"✓ System widget: health={payload['health']}, reasons={payload['reasons']}")
    
    def test_all_widgets(self):
        """GET /api/dashboard/widgets - All widgets in single request"""
        response = requests.get(f"{BASE_URL}/api/dashboard/widgets")
        
        assert response.status_code == 200
        data = response.json()
        
        # All 7 widgets should be present
        expected_widgets = ["portfolio", "strategy", "risk", "trades", "accounts", "alerts", "system"]
        for widget_name in expected_widgets:
            assert widget_name in data, f"Missing widget: {widget_name}"
            assert "widgetId" in data[widget_name]
            assert "widgetType" in data[widget_name]
            assert "payload" in data[widget_name]
            assert "updatedAt" in data[widget_name]
        
        print(f"✓ All widgets retrieved: {list(data.keys())}")


class TestTR6DashboardSnapshots:
    """Snapshot management tests"""
    
    def test_save_snapshot(self):
        """POST /api/dashboard/snapshot - Save current state as snapshot"""
        response = requests.post(f"{BASE_URL}/api/dashboard/snapshot")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "snapshot" in data
        
        snapshot = data["snapshot"]
        assert "snapshotId" in snapshot
        assert snapshot["snapshotId"].startswith("snap_")
        assert "state" in snapshot
        assert "createdAt" in snapshot
        
        # Verify state contains all dashboard sections
        state = snapshot["state"]
        assert "dashboardId" in state
        assert "portfolio" in state
        assert "strategy" in state
        assert "risk" in state
        assert "systemHealth" in state
        
        print(f"✓ Snapshot saved: {snapshot['snapshotId']}")
        return snapshot["snapshotId"]
    
    def test_get_snapshots(self):
        """GET /api/dashboard/snapshots - Retrieve stored snapshots"""
        # First save a snapshot to ensure we have at least one
        requests.post(f"{BASE_URL}/api/dashboard/snapshot")
        
        response = requests.get(f"{BASE_URL}/api/dashboard/snapshots")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "snapshots" in data
        assert "count" in data
        assert isinstance(data["snapshots"], list)
        assert data["count"] >= 1
        
        # Verify snapshot structure
        if data["snapshots"]:
            snapshot = data["snapshots"][0]
            assert "snapshotId" in snapshot
            assert "state" in snapshot
            assert "createdAt" in snapshot
        
        print(f"✓ Snapshots retrieved: count={data['count']}")
    
    def test_get_snapshots_with_limit(self):
        """GET /api/dashboard/snapshots?limit=5 - Retrieve with limit"""
        response = requests.get(f"{BASE_URL}/api/dashboard/snapshots", params={"limit": 5})
        
        assert response.status_code == 200
        data = response.json()
        
        assert "snapshots" in data
        assert len(data["snapshots"]) <= 5
        
        print(f"✓ Snapshots with limit=5: count={data['count']}")


class TestTR6DashboardEvents:
    """Event streaming and history tests"""
    
    def test_get_events(self):
        """GET /api/dashboard/events - Get recent dashboard events"""
        response = requests.get(f"{BASE_URL}/api/dashboard/events")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "events" in data
        assert "count" in data
        assert isinstance(data["events"], list)
        
        # If there are events, verify structure
        if data["events"]:
            event = data["events"][0]
            assert "eventId" in event
            assert "eventType" in event
            assert "payload" in event
            assert "timestamp" in event
        
        print(f"✓ Events retrieved: count={data['count']}")
    
    def test_get_events_with_limit(self):
        """GET /api/dashboard/events?limit=10 - Events with limit"""
        response = requests.get(f"{BASE_URL}/api/dashboard/events", params={"limit": 10})
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["events"]) <= 10
        print(f"✓ Events with limit=10: retrieved {data['count']}")
    
    def test_get_event_types(self):
        """GET /api/dashboard/events/types - Available event types"""
        response = requests.get(f"{BASE_URL}/api/dashboard/events/types")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "types" in data
        assert isinstance(data["types"], list)
        
        # Verify expected event types are present
        expected_types = [
            "PORTFOLIO_UPDATED", "RISK_ALERT", "STRATEGY_SWITCHED",
            "TRADE_FILLED", "KILL_SWITCH_TRIGGERED", "SYSTEM_HEALTH_CHANGED"
        ]
        for event_type in expected_types:
            assert event_type in data["types"], f"Missing event type: {event_type}"
        
        print(f"✓ Event types: {len(data['types'])} types available")


class TestTR6DashboardStream:
    """WebSocket stream status tests"""
    
    def test_stream_status(self):
        """GET /api/dashboard/stream/status - WebSocket stream status"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stream/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "healthy"
        assert "connectedClients" in data
        assert isinstance(data["connectedClients"], int)
        assert "clients" in data
        assert isinstance(data["clients"], list)
        
        print(f"✓ Stream status: {data['status']}, connectedClients={data['connectedClients']}")


class TestTR6DashboardModules:
    """Module information tests"""
    
    def test_modules_status(self):
        """GET /api/dashboard/modules - Integrated modules info"""
        response = requests.get(f"{BASE_URL}/api/dashboard/modules")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "modules" in data
        
        # Verify all trading terminal modules are listed
        expected_modules = {
            "TR1": {"name": "Account Manager", "prefix": "/api/accounts"},
            "TR2": {"name": "Portfolio Monitor", "prefix": "/api/portfolio"},
            "TR3": {"name": "Trade Monitor", "prefix": "/api/trades"},
            "TR4": {"name": "Risk Dashboard", "prefix": "/api/risk"},
            "TR5": {"name": "Strategy Control", "prefix": "/api/control"},
            "TR6": {"name": "Trading Dashboard", "prefix": "/api/dashboard"},
            "STR4": {"name": "Strategy Diagnostics", "prefix": "/api/strategy/diagnostics"}
        }
        
        for module_id, expected_info in expected_modules.items():
            assert module_id in data["modules"], f"Missing module: {module_id}"
            assert data["modules"][module_id]["name"] == expected_info["name"]
            assert data["modules"][module_id]["prefix"] == expected_info["prefix"]
        
        print(f"✓ Modules info: {len(data['modules'])} modules configured")


class TestTR6DashboardDataIntegrity:
    """Data integrity and consistency tests"""
    
    def test_dashboard_state_consistency(self):
        """Verify state data matches widget data"""
        # Get unified state
        state_response = requests.get(f"{BASE_URL}/api/dashboard/state")
        assert state_response.status_code == 200
        state_data = state_response.json()
        
        # Get portfolio widget
        portfolio_response = requests.get(f"{BASE_URL}/api/dashboard/portfolio")
        assert portfolio_response.status_code == 200
        portfolio_data = portfolio_response.json()
        
        # Compare equity values - should be consistent
        state_equity = state_data["portfolio"]["equity"]
        widget_equity = portfolio_data["payload"]["equity"]
        
        # Allow small difference due to timing
        assert abs(state_equity - widget_equity) < 0.01, f"Equity mismatch: state={state_equity}, widget={widget_equity}"
        
        print(f"✓ Data consistency verified: equity={state_equity}")
    
    def test_summary_matches_state(self):
        """Verify summary data matches full state"""
        state_response = requests.get(f"{BASE_URL}/api/dashboard/state")
        summary_response = requests.get(f"{BASE_URL}/api/dashboard/summary")
        
        assert state_response.status_code == 200
        assert summary_response.status_code == 200
        
        state_data = state_response.json()
        summary_data = summary_response.json()
        
        # Check key fields match
        assert state_data["portfolio"]["equity"] == summary_data["equity"]
        assert state_data["systemHealth"] == summary_data["health"]
        assert state_data["strategy"]["activeProfile"] == summary_data["profile"]
        
        print(f"✓ Summary matches state: health={summary_data['health']}")
    
    def test_system_health_calculation(self):
        """Verify system health is calculated correctly"""
        response = requests.get(f"{BASE_URL}/api/dashboard/state")
        
        assert response.status_code == 200
        data = response.json()
        
        system_health = data["systemHealth"]
        health_reasons = data["healthReasons"]
        
        # If HEALTHY, should have no reasons
        if system_health == "HEALTHY":
            assert len(health_reasons) == 0, "HEALTHY status should have no reasons"
        else:
            # If not HEALTHY, should have at least one reason
            assert len(health_reasons) > 0, f"{system_health} status should have reasons"
        
        print(f"✓ System health: {system_health}, reasons: {health_reasons}")


class TestTR6DashboardWidgetStructure:
    """Widget response structure validation"""
    
    def test_widget_standard_format(self):
        """Verify all widgets follow standard format"""
        widgets_response = requests.get(f"{BASE_URL}/api/dashboard/widgets")
        assert widgets_response.status_code == 200
        widgets = widgets_response.json()
        
        for widget_name, widget_data in widgets.items():
            # Every widget must have these fields
            assert "widgetId" in widget_data, f"{widget_name} missing widgetId"
            assert "widgetType" in widget_data, f"{widget_name} missing widgetType"
            assert "payload" in widget_data, f"{widget_name} missing payload"
            assert "updatedAt" in widget_data, f"{widget_name} missing updatedAt"
            
            # widgetId format
            assert widget_data["widgetId"].startswith("wgt_"), f"{widget_name} widgetId format invalid"
            
            # widgetType should match expected
            expected_type = widget_name.upper()
            assert widget_data["widgetType"] == expected_type, f"{widget_name} type mismatch"
            
            # updatedAt should be valid ISO format
            try:
                datetime.fromisoformat(widget_data["updatedAt"].replace("Z", "+00:00"))
            except:
                assert False, f"{widget_name} updatedAt is not valid ISO format"
        
        print(f"✓ All {len(widgets)} widgets follow standard format")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
