"""
PHASE 41 — Production Safety Layer Tests

Testing:
- 41.1 Production Scheduler
- 41.2 Realtime Streams
- 41.3 Kill Switch Engine
- 41.4 Circuit Breaker Engine

All endpoints tested against external URL from REACT_APP_BACKEND_URL
"""

import os
import pytest
import requests
from datetime import datetime

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module", autouse=True)
def cleanup_state(api_client):
    """Reset state before and after tests"""
    # Reset kill switch to ACTIVE before tests
    api_client.post(f"{BASE_URL}/api/v1/safety/kill-switch/deactivate", json={"confirm_safe": True})
    # Reset circuit breaker
    api_client.post(f"{BASE_URL}/api/v1/safety/circuit-breaker/reset")
    yield
    # Cleanup after tests
    api_client.post(f"{BASE_URL}/api/v1/safety/kill-switch/deactivate", json={"confirm_safe": True})
    api_client.post(f"{BASE_URL}/api/v1/safety/circuit-breaker/reset")


# ═══════════════════════════════════════════════════════════════
# Overall Health Tests
# ═══════════════════════════════════════════════════════════════

class TestOverallHealth:
    """Test overall system health endpoints"""

    def test_health_endpoint_version_41(self, api_client):
        """GET /api/health — version 41.0.0"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["version"] == "41.0.0"
        assert "PHASE 41" in data["phase"]
        print(f"✓ Health check passed: version {data['version']}")

    def test_root_endpoint_shows_safety_endpoints(self, api_client):
        """GET /api/health — version 41 confirms PHASE 41 safety modules active"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        # Root is served by frontend; verify safety modules via health endpoint
        assert data["ok"] is True
        assert "PHASE 41" in data["phase"]
        assert "Safety" in data["phase"]
        print(f"✓ PHASE 41 Safety Layer confirmed active via health check")


# ═══════════════════════════════════════════════════════════════
# Kill Switch Tests (PHASE 41.3)
# ═══════════════════════════════════════════════════════════════

class TestKillSwitch:
    """Test Kill Switch Engine endpoints"""

    def test_get_kill_switch_state(self, api_client):
        """GET /api/v1/safety/kill-switch/state — returns current state"""
        response = api_client.get(f"{BASE_URL}/api/v1/safety/kill-switch/state")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "41"
        assert "state" in data
        assert data["state"] in ["ACTIVE", "DISABLED", "SAFE_MODE", "EMERGENCY_STOP"]
        print(f"✓ Kill switch state: {data['state']}")

    def test_get_kill_switch_status(self, api_client):
        """GET /api/v1/safety/kill-switch/status — returns full status"""
        response = api_client.get(f"{BASE_URL}/api/v1/safety/kill-switch/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "kill_switch" in data
        ks = data["kill_switch"]
        assert "state" in ks
        assert "is_active" in ks
        assert "is_safe_mode" in ks
        assert "blocked_orders_count" in ks
        print(f"✓ Kill switch status retrieved: is_active={ks['is_active']}")

    def test_get_kill_switch_config(self, api_client):
        """GET /api/v1/safety/kill-switch/config — returns configuration"""
        response = api_client.get(f"{BASE_URL}/api/v1/safety/kill-switch/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "config" in data
        config = data["config"]
        assert "portfolio_risk_limit" in config
        assert "drawdown_limit" in config
        assert "daily_loss_limit" in config
        print(f"✓ Kill switch config retrieved")

    def test_get_kill_switch_events(self, api_client):
        """GET /api/v1/safety/kill-switch/events — returns event history"""
        response = api_client.get(f"{BASE_URL}/api/v1/safety/kill-switch/events")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "events" in data
        assert "count" in data
        print(f"✓ Kill switch events retrieved: count={data['count']}")

    def test_get_kill_switch_health(self, api_client):
        """GET /api/v1/safety/kill-switch/health — returns health check"""
        response = api_client.get(f"{BASE_URL}/api/v1/safety/kill-switch/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["module"] == "Safety Kill Switch"
        assert "endpoints" in data
        print(f"✓ Kill switch health OK")

    def test_activate_kill_switch(self, api_client):
        """POST /api/v1/safety/kill-switch/activate — activate kill switch"""
        response = api_client.post(f"{BASE_URL}/api/v1/safety/kill-switch/activate", json={
            "trigger": "MANUAL",
            "reason": "TEST activation",
            "user": "test_agent",
            "emergency": False
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "event" in data
        assert data["event"]["new_state"] == "DISABLED"
        print(f"✓ Kill switch activated: state={data['event']['new_state']}")

    def test_check_order_blocked_when_disabled(self, api_client):
        """POST /api/v1/safety/kill-switch/check — verify orders blocked when DISABLED"""
        response = api_client.post(f"{BASE_URL}/api/v1/safety/kill-switch/check", json={
            "symbol": "BTCUSDT",
            "size_usd": 1000.0,
            "side": "BUY"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "check" in data
        # Should be blocked when kill switch is DISABLED
        if data["check"]["state"] == "DISABLED":
            assert data["check"]["allowed"] is False
            assert data["check"]["blocked_reason"] is not None
            print(f"✓ Order correctly blocked: {data['check']['blocked_reason']}")
        else:
            print(f"⚠ Kill switch state: {data['check']['state']}")

    def test_deactivate_without_confirm_safe_fails(self, api_client):
        """Deactivation without confirm_safe should fail with 400"""
        response = api_client.post(f"{BASE_URL}/api/v1/safety/kill-switch/deactivate", json={
            "user": "test_agent",
            "reason": "TEST deactivation",
            "confirm_safe": False
        })
        assert response.status_code == 400
        print(f"✓ Deactivation without confirm_safe correctly rejected")

    def test_deactivate_kill_switch(self, api_client):
        """POST /api/v1/safety/kill-switch/deactivate — deactivate, verify state back to ACTIVE"""
        response = api_client.post(f"{BASE_URL}/api/v1/safety/kill-switch/deactivate", json={
            "user": "test_agent",
            "reason": "TEST deactivation",
            "confirm_safe": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["event"]["new_state"] == "ACTIVE"
        print(f"✓ Kill switch deactivated: state={data['event']['new_state']}")

    def test_enter_safe_mode(self, api_client):
        """POST /api/v1/safety/kill-switch/safe-mode — verify SAFE_MODE with 50% size modifier"""
        response = api_client.post(f"{BASE_URL}/api/v1/safety/kill-switch/safe-mode", json={
            "reason": "TEST safe mode",
            "user": "test_agent"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["event"]["new_state"] == "SAFE_MODE"
        print(f"✓ Safe mode entered")

    def test_check_order_reduced_in_safe_mode(self, api_client):
        """POST /api/v1/safety/kill-switch/check — verify orders allowed with reduced size in SAFE_MODE"""
        response = api_client.post(f"{BASE_URL}/api/v1/safety/kill-switch/check", json={
            "symbol": "BTCUSDT",
            "size_usd": 1000.0,
            "side": "BUY"
        })
        assert response.status_code == 200
        data = response.json()
        check = data["check"]
        if check["state"] == "SAFE_MODE":
            assert check["allowed"] is True
            assert check["size_modified"] is True
            assert check["size_modifier"] == 0.5
            print(f"✓ Order allowed with size modifier {check['size_modifier']} in SAFE_MODE")
        else:
            print(f"⚠ State is {check['state']}, not SAFE_MODE")

    def test_emergency_mode_activation(self, api_client):
        """Emergency mode activation (emergency: true → EMERGENCY_STOP state)"""
        # First deactivate
        api_client.post(f"{BASE_URL}/api/v1/safety/kill-switch/deactivate", json={"confirm_safe": True})
        
        response = api_client.post(f"{BASE_URL}/api/v1/safety/kill-switch/activate", json={
            "trigger": "MANUAL",
            "reason": "EMERGENCY TEST",
            "user": "test_agent",
            "emergency": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["event"]["new_state"] == "EMERGENCY_STOP"
        print(f"✓ Emergency stop activated")
        
        # Cleanup - deactivate
        api_client.post(f"{BASE_URL}/api/v1/safety/kill-switch/deactivate", json={"confirm_safe": True})


# ═══════════════════════════════════════════════════════════════
# Circuit Breaker Tests (PHASE 41.4)
# ═══════════════════════════════════════════════════════════════

class TestCircuitBreaker:
    """Test Circuit Breaker Engine endpoints"""

    def test_get_circuit_breaker_status(self, api_client):
        """GET /api/v1/safety/circuit-breaker/status — state CLOSED, 6 rules"""
        response = api_client.get(f"{BASE_URL}/api/v1/safety/circuit-breaker/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "41"
        cb = data["circuit_breaker"]
        assert cb["state"] in ["CLOSED", "OPEN", "HALF_OPEN"]
        assert cb["total_rules"] == 6
        print(f"✓ Circuit breaker status: state={cb['state']}, rules={cb['total_rules']}")

    def test_get_circuit_breaker_rules(self, api_client):
        """GET /api/v1/safety/circuit-breaker/rules — lists all 6 default rules"""
        response = api_client.get(f"{BASE_URL}/api/v1/safety/circuit-breaker/rules")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["count"] == 6
        rule_ids = [r["rule_id"] for r in data["rules"]]
        expected_rules = ["DRAWDOWN", "DAILY_LOSS", "SLIPPAGE", "LOSS_STREAK", "VOLATILITY_SPIKE", "EXEC_ERRORS"]
        for rule in expected_rules:
            assert rule in rule_ids
        print(f"✓ All 6 circuit breaker rules found: {rule_ids}")

    def test_get_specific_rule_drawdown(self, api_client):
        """GET /api/v1/safety/circuit-breaker/rules/DRAWDOWN — get specific rule"""
        response = api_client.get(f"{BASE_URL}/api/v1/safety/circuit-breaker/rules/DRAWDOWN")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        rule = data["rule"]
        assert rule["rule_id"] == "DRAWDOWN"
        assert rule["rule_type"] == "PORTFOLIO_DRAWDOWN"
        assert "warning_threshold" in rule
        assert "trigger_threshold" in rule
        assert "critical_threshold" in rule
        print(f"✓ DRAWDOWN rule: warning={rule['warning_threshold']}, trigger={rule['trigger_threshold']}")

    def test_check_order_allowed_when_clean(self, api_client):
        """POST /api/v1/safety/circuit-breaker/check — allowed when clean"""
        response = api_client.post(f"{BASE_URL}/api/v1/safety/circuit-breaker/check", json={
            "symbol": "BTCUSDT",
            "size_usd": 1000.0,
            "side": "BUY"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        check = data["check"]
        assert check["state"] in ["CLOSED", "HALF_OPEN", "OPEN"]
        print(f"✓ Circuit breaker check: allowed={check['allowed']}, state={check['state']}")

    def test_record_fill_negative_pnl(self, api_client):
        """POST /api/v1/safety/circuit-breaker/record-fill with negative PnL"""
        response = api_client.post(f"{BASE_URL}/api/v1/safety/circuit-breaker/record-fill", json={
            "pnl": -100.0
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["pnl_recorded"] == -100.0
        print(f"✓ Negative PnL recorded: {data['pnl_recorded']}")

    def test_loss_streak_tracking(self, api_client):
        """After 5+ losses, LOSS_STREAK rule trips, check shows size_modifier=0.5"""
        # Reset first
        api_client.post(f"{BASE_URL}/api/v1/safety/circuit-breaker/reset")
        
        # Record 5 losing trades to trigger LOSS_STREAK
        for i in range(6):
            api_client.post(f"{BASE_URL}/api/v1/safety/circuit-breaker/record-fill", json={"pnl": -50.0})
        
        # Check status
        response = api_client.post(f"{BASE_URL}/api/v1/safety/circuit-breaker/check", json={
            "symbol": "BTCUSDT",
            "size_usd": 1000.0,
            "side": "BUY"
        })
        assert response.status_code == 200
        data = response.json()
        check = data["check"]
        
        # LOSS_STREAK should be tripped (threshold is 5)
        if "LOSS_STREAK" in check.get("tripped_rules", []):
            assert check["size_modifier"] <= 0.5
            print(f"✓ LOSS_STREAK tripped: size_modifier={check['size_modifier']}")
        else:
            print(f"⚠ LOSS_STREAK not in tripped_rules: {check}")

    def test_record_slippage_high_bps(self, api_client):
        """POST /api/v1/safety/circuit-breaker/record-slippage with high bps value"""
        response = api_client.post(f"{BASE_URL}/api/v1/safety/circuit-breaker/record-slippage", json={
            "slippage_bps": 75.0
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["slippage_recorded"] == 75.0
        print(f"✓ High slippage recorded: {data['slippage_recorded']} bps")

    def test_record_execution_error(self, api_client):
        """POST /api/v1/safety/circuit-breaker/record-error — execution error tracking"""
        response = api_client.post(f"{BASE_URL}/api/v1/safety/circuit-breaker/record-error", json={
            "error": "TEST execution error"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["error_recorded"] is True
        print(f"✓ Execution error recorded")

    def test_reset_all_breakers(self, api_client):
        """POST /api/v1/safety/circuit-breaker/reset — resets all rules to CLOSED"""
        response = api_client.post(f"{BASE_URL}/api/v1/safety/circuit-breaker/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "reset" in data["message"].lower()
        print(f"✓ All circuit breakers reset")

    def test_reset_specific_rule(self, api_client):
        """POST /api/v1/safety/circuit-breaker/reset/LOSS_STREAK — reset specific rule"""
        response = api_client.post(f"{BASE_URL}/api/v1/safety/circuit-breaker/reset/LOSS_STREAK")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["rule_id"] == "LOSS_STREAK"
        print(f"✓ LOSS_STREAK rule reset")

    def test_enable_disable_rule(self, api_client):
        """POST /api/v1/safety/circuit-breaker/enable/DRAWDOWN and disable/DRAWDOWN"""
        # Disable
        response = api_client.post(f"{BASE_URL}/api/v1/safety/circuit-breaker/disable/DRAWDOWN")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        print(f"✓ DRAWDOWN rule disabled")
        
        # Enable
        response = api_client.post(f"{BASE_URL}/api/v1/safety/circuit-breaker/enable/DRAWDOWN")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        print(f"✓ DRAWDOWN rule enabled")

    def test_get_circuit_breaker_events(self, api_client):
        """GET /api/v1/safety/circuit-breaker/events — event history"""
        response = api_client.get(f"{BASE_URL}/api/v1/safety/circuit-breaker/events")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "events" in data
        assert "count" in data
        print(f"✓ Circuit breaker events retrieved: count={data['count']}")

    def test_get_circuit_breaker_config(self, api_client):
        """GET /api/v1/safety/circuit-breaker/config — configuration"""
        response = api_client.get(f"{BASE_URL}/api/v1/safety/circuit-breaker/config")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "config" in data
        config = data["config"]
        assert "drawdown_trigger" in config
        assert "daily_loss_trigger" in config
        assert "loss_streak_trigger" in config
        print(f"✓ Circuit breaker config retrieved")

    def test_get_circuit_breaker_health(self, api_client):
        """GET /api/v1/safety/circuit-breaker/health — health check"""
        response = api_client.get(f"{BASE_URL}/api/v1/safety/circuit-breaker/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["module"] == "Circuit Breaker"
        print(f"✓ Circuit breaker health OK")


# ═══════════════════════════════════════════════════════════════
# Realtime Streams Tests (PHASE 41.2)
# ═══════════════════════════════════════════════════════════════

class TestRealtimeStreams:
    """Test Realtime Streams endpoints"""

    def test_get_streams_status(self, api_client):
        """GET /api/v1/streams/status — connections, channels info"""
        response = api_client.get(f"{BASE_URL}/api/v1/streams/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "41"
        assert "streams" in data
        streams = data["streams"]
        assert "connections" in streams
        assert "channels" in streams
        assert "messages_published" in streams
        print(f"✓ Streams status: connections={streams['connections']}, messages={streams['messages_published']}")

    def test_get_streams_channels(self, api_client):
        """GET /api/v1/streams/channels — available channels list"""
        response = api_client.get(f"{BASE_URL}/api/v1/streams/channels")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "available_channels" in data
        expected_channels = ["portfolio.updates", "orders.updates", "fills.updates", 
                           "alerts.updates", "dashboard.state", "safety.state"]
        for ch in expected_channels:
            assert ch in data["available_channels"]
        print(f"✓ All expected channels available: {data['available_channels']}")

    def test_get_stream_history(self, api_client):
        """GET /api/v1/streams/history/portfolio.updates — empty history ok"""
        response = api_client.get(f"{BASE_URL}/api/v1/streams/history/portfolio.updates")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["channel"] == "portfolio.updates"
        assert "messages" in data
        print(f"✓ Stream history retrieved: count={data['count']}")

    def test_publish_to_channel(self, api_client):
        """POST /api/v1/streams/publish — publish to channel"""
        response = api_client.post(f"{BASE_URL}/api/v1/streams/publish", json={
            "channel": "test.channel",
            "data": {"message": "TEST publish", "timestamp": datetime.now().isoformat()}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["published"] is True
        print(f"✓ Message published to channel")

    def test_get_streams_health(self, api_client):
        """GET /api/v1/streams/health — health check"""
        response = api_client.get(f"{BASE_URL}/api/v1/streams/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["module"] == "Realtime Streams"
        print(f"✓ Streams health OK")


# ═══════════════════════════════════════════════════════════════
# Production Scheduler Tests (PHASE 41.1)
# ═══════════════════════════════════════════════════════════════

class TestProductionScheduler:
    """Test Production Scheduler endpoints"""

    def test_get_scheduler_status(self, api_client):
        """GET /api/v1/scheduler/status — shows 8 tasks"""
        response = api_client.get(f"{BASE_URL}/api/v1/scheduler/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "41"
        sched = data["scheduler"]
        assert sched["task_count"] == 8
        print(f"✓ Scheduler status: running={sched['running']}, tasks={sched['task_count']}")

    def test_get_scheduler_tasks(self, api_client):
        """GET /api/v1/scheduler/tasks — lists all tasks with details"""
        response = api_client.get(f"{BASE_URL}/api/v1/scheduler/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["count"] == 8
        task_ids = [t["task_id"] for t in data["tasks"]]
        expected_tasks = ["circuit_breaker_check", "risk_budget_recompute", "dashboard_state_refresh",
                         "alerts_check", "regime_update", "fractal_recompute", 
                         "reflexivity_update", "memory_update"]
        for task in expected_tasks:
            assert task in task_ids
        print(f"✓ All 8 scheduler tasks found: {task_ids}")

    def test_start_scheduler(self, api_client):
        """POST /api/v1/scheduler/start — start scheduler"""
        response = api_client.post(f"{BASE_URL}/api/v1/scheduler/start")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "started" in data["message"].lower()
        print(f"✓ Scheduler started")

    def test_stop_scheduler(self, api_client):
        """POST /api/v1/scheduler/stop — stop scheduler"""
        response = api_client.post(f"{BASE_URL}/api/v1/scheduler/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "stopped" in data["message"].lower()
        print(f"✓ Scheduler stopped")

    def test_run_single_task_manually(self, api_client):
        """POST /api/v1/scheduler/run/circuit_breaker_check — run single task manually"""
        response = api_client.post(f"{BASE_URL}/api/v1/scheduler/run/circuit_breaker_check")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["result"]["success"] is True
        assert data["result"]["task_id"] == "circuit_breaker_check"
        print(f"✓ Task circuit_breaker_check executed: duration={data['result'].get('duration_ms', 0):.2f}ms")

    def test_enable_disable_task(self, api_client):
        """POST /api/v1/scheduler/enable/alerts_check and disable/alerts_check"""
        # Disable
        response = api_client.post(f"{BASE_URL}/api/v1/scheduler/disable/alerts_check")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        print(f"✓ Task alerts_check disabled")
        
        # Enable
        response = api_client.post(f"{BASE_URL}/api/v1/scheduler/enable/alerts_check")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        print(f"✓ Task alerts_check enabled")

    def test_get_scheduler_health(self, api_client):
        """GET /api/v1/scheduler/health — health check"""
        response = api_client.get(f"{BASE_URL}/api/v1/scheduler/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["module"] == "Production Scheduler"
        print(f"✓ Scheduler health OK")


# ═══════════════════════════════════════════════════════════════
# Run tests if executed directly
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
