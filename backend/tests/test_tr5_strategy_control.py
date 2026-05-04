"""
TR5 Strategy Control Module - Backend API Tests
================================================

Tests for all TR5 Strategy Control endpoints:
- Health & State management
- Profile switching (CONSERVATIVE, BALANCED, AGGRESSIVE)
- Config switching
- Trading pause/resume
- Kill switch (SOFT/HARD) with mode hierarchy
- Override mode
- Events & History

Mode Hierarchy: NORMAL → PAUSED → SOFT_KILL → HARD_KILL
"""

import pytest
import requests
import os
import time

# Get base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://tech-analysis-core-1.preview.emergentagent.com"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestTR5HealthAndState:
    """TR5 Health check and state management tests"""
    
    def test_health_endpoint(self, api_client):
        """Test GET /api/control/health - TR5 module health"""
        response = api_client.get(f"{BASE_URL}/api/control/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["module"] == "Strategy Control Service"
        assert data["phase"] == "TR5"
        assert data["status"] == "healthy"
        assert "current_mode" in data
        assert "trading_enabled" in data
        assert "active_profile" in data
        
        # Check services status
        services = data.get("services", {})
        assert "profile_switch" in services
        assert "config_switch" in services
        assert "trading_pause" in services
        assert "kill_switch" in services
        assert "override" in services
        
        print(f"✓ TR5 health: {data['status']}, mode: {data['current_mode']}, profile: {data['active_profile']}")
    
    def test_state_endpoint(self, api_client):
        """Test GET /api/control/state - Current control state"""
        response = api_client.get(f"{BASE_URL}/api/control/state")
        assert response.status_code == 200
        
        data = response.json()
        assert "state_id" in data
        assert "trading_enabled" in data
        assert "active_profile" in data
        assert "mode" in data
        assert "paused" in data
        assert "kill_switch" in data
        assert "override_mode" in data
        
        # Verify mode is valid
        assert data["mode"] in ["NORMAL", "PAUSED", "SOFT_KILL", "HARD_KILL"]
        
        print(f"✓ Control state: mode={data['mode']}, trading={data['trading_enabled']}")
    
    def test_dashboard_endpoint(self, api_client):
        """Test GET /api/control/dashboard - Dashboard data"""
        response = api_client.get(f"{BASE_URL}/api/control/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        assert "state" in data
        assert "profile" in data
        assert "config" in data
        assert "pause" in data
        assert "kill_switch" in data
        assert "override" in data
        assert "mode_hierarchy" in data
        assert "current_mode" in data
        assert "trading_enabled" in data
        
        # Verify mode hierarchy
        assert data["mode_hierarchy"] == ["NORMAL", "PAUSED", "SOFT_KILL", "HARD_KILL"]
        
        print(f"✓ Dashboard: mode={data['current_mode']}, enabled={data['trading_enabled']}")


class TestTR5ProfileControl:
    """Profile switching tests - CONSERVATIVE, BALANCED, AGGRESSIVE"""
    
    def test_get_profile_info(self, api_client):
        """Test GET /api/control/profile - Profile information"""
        response = api_client.get(f"{BASE_URL}/api/control/profile")
        assert response.status_code == 200
        
        data = response.json()
        assert "current" in data
        assert "available" in data
        assert "descriptions" in data
        
        # Verify available profiles
        assert set(data["available"]) == {"CONSERVATIVE", "BALANCED", "AGGRESSIVE"}
        
        print(f"✓ Current profile: {data['current']}, available: {data['available']}")
    
    def test_switch_profile_to_balanced(self, api_client):
        """Test POST /api/control/profile/switch - Switch to BALANCED"""
        response = api_client.post(
            f"{BASE_URL}/api/control/profile/switch",
            json={
                "profile": "BALANCED",
                "reason": "TEST: Switch to balanced profile",
                "actor": "test_agent"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        # If changed, to_profile will be present; if not changed, profile key will be present
        assert data.get("to_profile") == "BALANCED" or data.get("profile") == "BALANCED" or "BALANCED" in data.get("message", "")
        
        print(f"✓ Profile set to BALANCED")
    
    def test_switch_profile_to_conservative(self, api_client):
        """Test POST /api/control/profile/switch - Switch to CONSERVATIVE"""
        response = api_client.post(
            f"{BASE_URL}/api/control/profile/switch",
            json={
                "profile": "CONSERVATIVE",
                "reason": "TEST: Switch to conservative profile",
                "actor": "test_agent"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        
        print(f"✓ Switched to CONSERVATIVE profile")
    
    def test_switch_profile_to_aggressive(self, api_client):
        """Test POST /api/control/profile/switch - Switch to AGGRESSIVE"""
        response = api_client.post(
            f"{BASE_URL}/api/control/profile/switch",
            json={
                "profile": "AGGRESSIVE",
                "reason": "TEST: Switch to aggressive profile",
                "actor": "test_agent"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        
        print(f"✓ Switched to AGGRESSIVE profile")
    
    def test_switch_profile_invalid(self, api_client):
        """Test invalid profile switch - should return 400"""
        response = api_client.post(
            f"{BASE_URL}/api/control/profile/switch",
            json={
                "profile": "INVALID_PROFILE",
                "reason": "TEST: Invalid profile",
                "actor": "test_agent"
            }
        )
        assert response.status_code == 400
        print(f"✓ Invalid profile correctly rejected")
    
    def test_switch_to_same_profile(self, api_client):
        """Test switching to same profile - should return success but no change"""
        # First switch to BALANCED
        api_client.post(
            f"{BASE_URL}/api/control/profile/switch",
            json={"profile": "BALANCED", "reason": "Setup", "actor": "test"}
        )
        
        # Switch again to BALANCED
        response = api_client.post(
            f"{BASE_URL}/api/control/profile/switch",
            json={"profile": "BALANCED", "reason": "Same profile test", "actor": "test"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data.get("changed") == False  # No change should happen
        
        print(f"✓ Same profile switch handled correctly (no change)")


class TestTR5ConfigControl:
    """Config switching tests"""
    
    def test_get_config_info(self, api_client):
        """Test GET /api/control/config - Config information"""
        response = api_client.get(f"{BASE_URL}/api/control/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "current" in data
        assert "available" in data
        assert "configs" in data
        
        print(f"✓ Current config: {data['current']}, available: {data['available']}")
    
    def test_switch_config(self, api_client):
        """Test POST /api/control/config/switch - Switch config"""
        response = api_client.post(
            f"{BASE_URL}/api/control/config/switch",
            json={
                "config_id": "config_default",
                "reason": "TEST: Switch to default config",
                "actor": "test_agent"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        
        print(f"✓ Config switch successful")
    
    def test_switch_config_conservative(self, api_client):
        """Test switch to conservative config"""
        response = api_client.post(
            f"{BASE_URL}/api/control/config/switch",
            json={
                "config_id": "config_conservative",
                "reason": "TEST: Conservative config",
                "actor": "test_agent"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        
        print(f"✓ Switched to config_conservative")
    
    def test_switch_config_custom(self, api_client):
        """Test switch to custom config (allowed even if not predefined)"""
        response = api_client.post(
            f"{BASE_URL}/api/control/config/switch",
            json={
                "config_id": "custom_test_config",
                "reason": "TEST: Custom config",
                "actor": "test_agent"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        
        print(f"✓ Custom config switch allowed")


class TestTR5TradingPauseResume:
    """Trading pause/resume tests"""
    
    def test_pause_trading(self, api_client):
        """Test POST /api/control/trading/pause - Pause trading"""
        response = api_client.post(
            f"{BASE_URL}/api/control/trading/pause",
            json={
                "reason": "TEST: Pause trading",
                "actor": "test_agent"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["paused"] == True
        
        print(f"✓ Trading paused successfully")
    
    def test_verify_paused_state(self, api_client):
        """Verify trading is paused in state"""
        response = api_client.get(f"{BASE_URL}/api/control/state")
        assert response.status_code == 200
        
        data = response.json()
        assert data["paused"] == True
        assert data["mode"] == "PAUSED"
        
        print(f"✓ Paused state verified: mode={data['mode']}")
    
    def test_can_trade_when_paused(self, api_client):
        """Test can-trade returns false when paused"""
        response = api_client.get(f"{BASE_URL}/api/control/can-trade")
        assert response.status_code == 200
        
        data = response.json()
        assert data["can_trade"] == False
        assert "paused" in data.get("reason", "").lower() or not data["can_trade"]
        
        print(f"✓ Can trade check: {data['can_trade']}, reason: {data.get('reason', 'N/A')}")
    
    def test_resume_trading(self, api_client):
        """Test POST /api/control/trading/resume - Resume trading"""
        response = api_client.post(
            f"{BASE_URL}/api/control/trading/resume",
            json={
                "reason": "TEST: Resume trading",
                "actor": "test_agent"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["paused"] == False
        
        print(f"✓ Trading resumed successfully")
    
    def test_verify_resumed_state(self, api_client):
        """Verify trading is resumed in state"""
        response = api_client.get(f"{BASE_URL}/api/control/state")
        assert response.status_code == 200
        
        data = response.json()
        assert data["paused"] == False
        
        print(f"✓ Resumed state verified: mode={data['mode']}")


class TestTR5KillSwitch:
    """Kill switch tests - SOFT and HARD modes"""
    
    def test_get_kill_switch_state(self, api_client):
        """Test GET /api/control/kill-switch - Kill switch state"""
        response = api_client.get(f"{BASE_URL}/api/control/kill-switch")
        assert response.status_code == 200
        
        data = response.json()
        assert "active" in data
        assert "mode" in data
        
        print(f"✓ Kill switch state: active={data['active']}, mode={data['mode']}")
    
    def test_trigger_soft_kill(self, api_client):
        """Test POST /api/control/kill-switch/soft - Trigger SOFT kill"""
        response = api_client.post(
            f"{BASE_URL}/api/control/kill-switch/soft",
            json={
                "reason": "TEST: Soft kill switch activation",
                "actor": "test_agent"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["mode"] == "SOFT"
        assert "config" in data
        
        # Verify config settings for SOFT
        config = data["config"]
        assert config["cancel_open_orders"] == True
        assert config["block_new_entries"] == True
        assert config["allow_reductions"] == True
        assert config["force_close_positions"] == False
        
        print(f"✓ SOFT kill switch activated: {data['mode']}")
    
    def test_verify_soft_kill_state(self, api_client):
        """Verify SOFT kill switch is active"""
        response = api_client.get(f"{BASE_URL}/api/control/state")
        assert response.status_code == 200
        
        data = response.json()
        assert data["mode"] == "SOFT_KILL"
        assert data["kill_switch"]["active"] == True
        assert data["kill_switch"]["mode"] == "SOFT"
        
        print(f"✓ SOFT kill state verified: mode={data['mode']}")
    
    def test_can_trade_with_soft_kill(self, api_client):
        """Test can-trade returns false with SOFT kill"""
        response = api_client.get(f"{BASE_URL}/api/control/can-trade")
        assert response.status_code == 200
        
        data = response.json()
        assert data["can_trade"] == False
        
        print(f"✓ Can trade with soft kill: {data['can_trade']}")
    
    def test_reset_kill_switch(self, api_client):
        """Test POST /api/control/kill-switch/reset - Reset kill switch"""
        response = api_client.post(
            f"{BASE_URL}/api/control/kill-switch/reset",
            json={
                "reason": "TEST: Reset kill switch",
                "actor": "test_agent"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        
        print(f"✓ Kill switch reset successfully")
    
    def test_trigger_hard_kill(self, api_client):
        """Test POST /api/control/kill-switch/hard - Trigger HARD kill"""
        response = api_client.post(
            f"{BASE_URL}/api/control/kill-switch/hard",
            json={
                "reason": "TEST: Hard kill switch activation",
                "actor": "test_agent",
                "close_method": "market"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["mode"] == "HARD"
        
        # Verify config settings for HARD
        config = data["config"]
        assert config["cancel_open_orders"] == True
        assert config["block_new_entries"] == True
        assert config["force_close_positions"] == True
        
        print(f"✓ HARD kill switch activated: {data['mode']}")
    
    def test_verify_hard_kill_state(self, api_client):
        """Verify HARD kill switch is active"""
        response = api_client.get(f"{BASE_URL}/api/control/state")
        assert response.status_code == 200
        
        data = response.json()
        assert data["mode"] == "HARD_KILL"
        assert data["kill_switch"]["active"] == True
        assert data["kill_switch"]["mode"] == "HARD"
        
        print(f"✓ HARD kill state verified: mode={data['mode']}")
    
    def test_reset_hard_kill(self, api_client):
        """Reset HARD kill switch for cleanup"""
        response = api_client.post(
            f"{BASE_URL}/api/control/kill-switch/reset",
            json={
                "reason": "TEST: Cleanup - reset HARD kill",
                "actor": "test_agent"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        
        print(f"✓ HARD kill switch reset for cleanup")
    
    def test_get_kill_switch_events(self, api_client):
        """Test GET /api/control/events/kill-switch - Kill switch events"""
        response = api_client.get(f"{BASE_URL}/api/control/events/kill-switch")
        assert response.status_code == 200
        
        data = response.json()
        assert "events" in data
        assert "count" in data
        
        # Should have events from our tests
        if data["count"] > 0:
            event = data["events"][0]
            assert event["action"] in ["SOFT_KILL_SWITCH", "HARD_KILL_SWITCH", "KILL_SWITCH_RESET"]
        
        print(f"✓ Kill switch events count: {data['count']}")


class TestTR5OverrideMode:
    """Override mode tests - manual control override"""
    
    def test_get_override_state(self, api_client):
        """Test GET /api/control/override - Override state"""
        response = api_client.get(f"{BASE_URL}/api/control/override")
        assert response.status_code == 200
        
        data = response.json()
        assert "enabled" in data
        
        print(f"✓ Override state: enabled={data['enabled']}")
    
    def test_enable_override_mode(self, api_client):
        """Test POST /api/control/override - Enable override"""
        response = api_client.post(
            f"{BASE_URL}/api/control/override",
            json={
                "reason": "TEST: Enable override mode",
                "actor": "test_agent",
                "manual_order_routing": True,
                "disable_auto_switching": True,
                "disable_strategy_runtime": True
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["enabled"] == True
        
        # Verify settings
        settings = data.get("settings", {})
        assert settings.get("manual_order_routing") == True
        assert settings.get("disable_auto_switching") == True
        assert settings.get("disable_strategy_runtime") == True
        
        print(f"✓ Override mode enabled with settings")
    
    def test_verify_override_in_state(self, api_client):
        """Verify override mode in state"""
        response = api_client.get(f"{BASE_URL}/api/control/state")
        assert response.status_code == 200
        
        data = response.json()
        assert data["override_mode"] == True
        
        print(f"✓ Override mode verified in state")
    
    def test_can_enter_with_override(self, api_client):
        """Test can-enter with override mode (strategy runtime disabled)"""
        response = api_client.get(f"{BASE_URL}/api/control/can-enter")
        assert response.status_code == 200
        
        data = response.json()
        # With override and strategy runtime disabled, can_enter should be False
        assert data["can_enter"] == False
        
        print(f"✓ Can enter with override: {data['can_enter']}")
    
    def test_disable_override_mode(self, api_client):
        """Test POST /api/control/override/disable - Disable override"""
        response = api_client.post(
            f"{BASE_URL}/api/control/override/disable",
            json={
                "reason": "TEST: Disable override mode",
                "actor": "test_agent"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["enabled"] == False
        
        print(f"✓ Override mode disabled")


class TestTR5EventsAndHistory:
    """Events and state history tests"""
    
    def test_get_events(self, api_client):
        """Test GET /api/control/events - Control events"""
        response = api_client.get(f"{BASE_URL}/api/control/events")
        assert response.status_code == 200
        
        data = response.json()
        assert "events" in data
        assert "count" in data
        
        # Should have events from our tests
        if data["count"] > 0:
            event = data["events"][0]
            assert "event_id" in event
            assert "action" in event
            assert "actor" in event
            assert "timestamp" in event
        
        print(f"✓ Events retrieved: count={data['count']}")
    
    def test_get_events_with_limit(self, api_client):
        """Test events with limit parameter"""
        response = api_client.get(f"{BASE_URL}/api/control/events?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["events"]) <= 5
        
        print(f"✓ Events with limit: {len(data['events'])}")
    
    def test_get_events_with_action_filter(self, api_client):
        """Test events with action filter"""
        response = api_client.get(f"{BASE_URL}/api/control/events?action=PROFILE_SWITCH")
        assert response.status_code == 200
        
        data = response.json()
        # All events should be PROFILE_SWITCH
        for event in data["events"]:
            assert event["action"] == "PROFILE_SWITCH"
        
        print(f"✓ Events filtered by action: {data['count']}")
    
    def test_get_state_history(self, api_client):
        """Test GET /api/control/history - State history"""
        response = api_client.get(f"{BASE_URL}/api/control/history")
        assert response.status_code == 200
        
        data = response.json()
        assert "history" in data
        assert "count" in data
        
        print(f"✓ State history: count={data['count']}")
    
    def test_get_state_history_with_limit(self, api_client):
        """Test state history with limit"""
        response = api_client.get(f"{BASE_URL}/api/control/history?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["history"]) <= 10
        
        print(f"✓ State history with limit: {len(data['history'])}")


class TestTR5ValidationHelpers:
    """Validation helper endpoint tests"""
    
    def test_can_trade_endpoint(self, api_client):
        """Test GET /api/control/can-trade - Trade validation"""
        response = api_client.get(f"{BASE_URL}/api/control/can-trade")
        assert response.status_code == 200
        
        data = response.json()
        assert "can_trade" in data
        assert "reason" in data
        assert "trading_enabled" in data
        
        print(f"✓ Can trade: {data['can_trade']}")
    
    def test_can_enter_endpoint(self, api_client):
        """Test GET /api/control/can-enter - Entry validation"""
        response = api_client.get(f"{BASE_URL}/api/control/can-enter")
        assert response.status_code == 200
        
        data = response.json()
        assert "can_enter" in data
        assert "reason" in data
        
        print(f"✓ Can enter: {data['can_enter']}")


class TestTR5ModeHierarchy:
    """Test mode hierarchy: NORMAL → PAUSED → SOFT_KILL → HARD_KILL"""
    
    def test_mode_hierarchy_normal_to_paused(self, api_client):
        """Test NORMAL to PAUSED transition"""
        # Ensure we start from NORMAL
        api_client.post(f"{BASE_URL}/api/control/kill-switch/reset", json={"reason": "setup", "actor": "test"})
        api_client.post(f"{BASE_URL}/api/control/trading/resume", json={"reason": "setup", "actor": "test"})
        
        # Verify NORMAL state
        response = api_client.get(f"{BASE_URL}/api/control/state")
        data = response.json()
        assert data["mode"] == "NORMAL"
        
        # Transition to PAUSED
        api_client.post(f"{BASE_URL}/api/control/trading/pause", json={"reason": "test", "actor": "test"})
        
        response = api_client.get(f"{BASE_URL}/api/control/state")
        data = response.json()
        assert data["mode"] == "PAUSED"
        
        print(f"✓ Mode transition NORMAL → PAUSED verified")
    
    def test_mode_hierarchy_paused_to_soft_kill(self, api_client):
        """Test PAUSED to SOFT_KILL transition"""
        # Trigger soft kill (overrides PAUSED)
        api_client.post(f"{BASE_URL}/api/control/kill-switch/soft", json={"reason": "test", "actor": "test"})
        
        response = api_client.get(f"{BASE_URL}/api/control/state")
        data = response.json()
        assert data["mode"] == "SOFT_KILL"
        
        print(f"✓ Mode transition PAUSED → SOFT_KILL verified")
    
    def test_mode_hierarchy_soft_to_hard_kill(self, api_client):
        """Test SOFT_KILL to HARD_KILL transition"""
        # First reset kill switch
        api_client.post(f"{BASE_URL}/api/control/kill-switch/reset", json={"reason": "setup", "actor": "test"})
        
        # Trigger hard kill
        api_client.post(f"{BASE_URL}/api/control/kill-switch/hard", json={"reason": "test", "actor": "test"})
        
        response = api_client.get(f"{BASE_URL}/api/control/state")
        data = response.json()
        assert data["mode"] == "HARD_KILL"
        
        print(f"✓ Mode transition → HARD_KILL verified")
    
    def test_cleanup_to_normal(self, api_client):
        """Cleanup: return to NORMAL mode"""
        # Reset everything
        api_client.post(f"{BASE_URL}/api/control/kill-switch/reset", json={"reason": "cleanup", "actor": "test"})
        api_client.post(f"{BASE_URL}/api/control/trading/resume", json={"reason": "cleanup", "actor": "test"})
        api_client.post(f"{BASE_URL}/api/control/override/disable", json={"reason": "cleanup", "actor": "test"})
        
        response = api_client.get(f"{BASE_URL}/api/control/state")
        data = response.json()
        assert data["mode"] == "NORMAL"
        assert data["trading_enabled"] == True
        
        print(f"✓ Cleanup complete: mode={data['mode']}, trading_enabled={data['trading_enabled']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
