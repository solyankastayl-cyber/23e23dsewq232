"""
TT5 - Operator Control Layer API Tests
=======================================
Tests for TT5 Control Layer endpoints:
- System state (ACTIVE/PAUSED/SOFT_KILL/HARD_KILL/EMERGENCY)
- Kill switches (soft/hard)
- Alpha mode control (AUTO/MANUAL/OFF)
- Pending actions queue (approve/reject)
- Overrides management
"""

import pytest
import requests
import os
import time
from datetime import datetime

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestTT5ControlState:
    """TT5 Control State Tests"""
    
    def test_get_control_state(self):
        """GET /api/control/state - Get current control state with all fields"""
        response = requests.get(f"{BASE_URL}/api/control/state")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["ok"] == True
        assert "data" in data
        assert "timestamp" in data
        
        # Verify all control state fields
        state = data["data"]
        required_fields = [
            "trading_enabled",
            "new_entries_enabled", 
            "position_management_enabled",
            "alpha_mode",
            "system_state",
            "emergency",
            "soft_kill",
            "hard_kill",
            "last_state_change"
        ]
        
        for field in required_fields:
            assert field in state, f"Missing field: {field}"
        
        # Validate field types
        assert isinstance(state["trading_enabled"], bool)
        assert isinstance(state["new_entries_enabled"], bool)
        assert isinstance(state["position_management_enabled"], bool)
        assert state["alpha_mode"] in ["AUTO", "MANUAL", "OFF"]
        assert state["system_state"] in ["ACTIVE", "PAUSED", "SOFT_KILL", "HARD_KILL", "EMERGENCY"]
        assert isinstance(state["emergency"], bool)
        assert isinstance(state["soft_kill"], bool)
        assert isinstance(state["hard_kill"], bool)
        
        print(f"Control state: system_state={state['system_state']}, alpha_mode={state['alpha_mode']}")
    
    def test_get_control_summary(self):
        """GET /api/control/summary - Get control summary for UI"""
        response = requests.get(f"{BASE_URL}/api/control/summary")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert "data" in data
        
        summary = data["data"]
        required_fields = [
            "system_state",
            "alpha_mode",
            "trading_enabled",
            "new_entries_enabled",
            "position_management_enabled",
            "soft_kill",
            "hard_kill",
            "emergency",
            "pending_actions_count",
            "active_overrides_count",
            "status"
        ]
        
        for field in required_fields:
            assert field in summary, f"Missing field: {field}"
        
        print(f"Control summary: pending_actions={summary['pending_actions_count']}, overrides={summary['active_overrides_count']}")


class TestTT5SystemControls:
    """TT5 System Control Actions Tests"""
    
    @pytest.fixture(autouse=True)
    def reset_state(self):
        """Reset control state before each test"""
        # Reset to defaults
        requests.post(f"{BASE_URL}/api/control/reset")
        yield
        # Cleanup - reset again after test
        requests.post(f"{BASE_URL}/api/control/reset")
    
    def test_pause_system(self):
        """POST /api/control/pause - Changes system_state to PAUSED and disables new entries"""
        response = requests.post(f"{BASE_URL}/api/control/pause")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert "data" in data
        assert data["message"] == "System paused"
        
        # Verify state changes
        state = data["data"]
        assert state["system_state"] == "PAUSED"
        assert state["new_entries_enabled"] == False
        
        # Verify via GET
        verify_response = requests.get(f"{BASE_URL}/api/control/state")
        verify_state = verify_response.json()["data"]
        assert verify_state["system_state"] == "PAUSED"
        assert verify_state["new_entries_enabled"] == False
        
        print("Pause: system_state=PAUSED, new_entries_enabled=False")
    
    def test_resume_system(self):
        """POST /api/control/resume - Restores system to ACTIVE with all enables true"""
        # First pause
        requests.post(f"{BASE_URL}/api/control/pause")
        
        # Then resume
        response = requests.post(f"{BASE_URL}/api/control/resume")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["message"] == "System resumed"
        
        # Verify state changes
        state = data["data"]
        assert state["system_state"] == "ACTIVE"
        assert state["trading_enabled"] == True
        assert state["new_entries_enabled"] == True
        assert state["position_management_enabled"] == True
        assert state["soft_kill"] == False
        assert state["hard_kill"] == False
        assert state["emergency"] == False
        
        print("Resume: system_state=ACTIVE, all enables=True")
    
    def test_soft_kill(self):
        """POST /api/control/kill/soft - Sets soft_kill=true and system_state=SOFT_KILL"""
        response = requests.post(f"{BASE_URL}/api/control/kill/soft")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["message"] == "Soft kill activated"
        
        # Verify state changes
        state = data["data"]
        assert state["system_state"] == "SOFT_KILL"
        assert state["soft_kill"] == True
        assert state["new_entries_enabled"] == False
        
        # Verify via GET
        verify_response = requests.get(f"{BASE_URL}/api/control/state")
        verify_state = verify_response.json()["data"]
        assert verify_state["system_state"] == "SOFT_KILL"
        assert verify_state["soft_kill"] == True
        
        print("Soft kill: system_state=SOFT_KILL, soft_kill=True")
    
    def test_hard_kill(self):
        """POST /api/control/kill/hard - Sets hard_kill=true and trading_enabled=false"""
        response = requests.post(f"{BASE_URL}/api/control/kill/hard")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["message"] == "Hard kill activated - ALL TRADING STOPPED"
        
        # Verify state changes
        state = data["data"]
        assert state["system_state"] == "HARD_KILL"
        assert state["hard_kill"] == True
        assert state["trading_enabled"] == False
        assert state["new_entries_enabled"] == False
        
        # Verify via GET
        verify_response = requests.get(f"{BASE_URL}/api/control/state")
        verify_state = verify_response.json()["data"]
        assert verify_state["system_state"] == "HARD_KILL"
        assert verify_state["hard_kill"] == True
        assert verify_state["trading_enabled"] == False
        
        print("Hard kill: system_state=HARD_KILL, hard_kill=True, trading_enabled=False")
    
    def test_emergency_stop(self):
        """POST /api/control/emergency - Emergency stop halts everything"""
        response = requests.post(f"{BASE_URL}/api/control/emergency")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["message"] == "EMERGENCY STOP ACTIVATED"
        
        # Verify state changes
        state = data["data"]
        assert state["system_state"] == "EMERGENCY"
        assert state["emergency"] == True
        assert state["hard_kill"] == True
        assert state["trading_enabled"] == False
        assert state["new_entries_enabled"] == False
        assert state["position_management_enabled"] == False
        
        print("Emergency: system_state=EMERGENCY, all trading stopped")


class TestTT5AlphaMode:
    """TT5 Alpha Mode Control Tests"""
    
    @pytest.fixture(autouse=True)
    def reset_state(self):
        """Reset control state before each test"""
        requests.post(f"{BASE_URL}/api/control/reset")
        yield
        requests.post(f"{BASE_URL}/api/control/reset")
    
    def test_set_alpha_mode_auto(self):
        """POST /api/control/alpha/mode with {mode: AUTO} changes alpha_mode"""
        response = requests.post(
            f"{BASE_URL}/api/control/alpha/mode",
            json={"mode": "AUTO"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["message"] == "Alpha mode set to AUTO"
        assert data["data"]["alpha_mode"] == "AUTO"
        
        # Verify via GET
        verify_response = requests.get(f"{BASE_URL}/api/control/state")
        assert verify_response.json()["data"]["alpha_mode"] == "AUTO"
        
        print("Alpha mode set to AUTO")
    
    def test_set_alpha_mode_manual(self):
        """POST /api/control/alpha/mode with {mode: MANUAL} changes alpha_mode"""
        response = requests.post(
            f"{BASE_URL}/api/control/alpha/mode",
            json={"mode": "MANUAL"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["message"] == "Alpha mode set to MANUAL"
        assert data["data"]["alpha_mode"] == "MANUAL"
        
        print("Alpha mode set to MANUAL")
    
    def test_set_alpha_mode_off(self):
        """POST /api/control/alpha/mode with {mode: OFF} changes alpha_mode"""
        response = requests.post(
            f"{BASE_URL}/api/control/alpha/mode",
            json={"mode": "OFF"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["message"] == "Alpha mode set to OFF"
        assert data["data"]["alpha_mode"] == "OFF"
        
        print("Alpha mode set to OFF")
    
    def test_set_alpha_mode_invalid(self):
        """POST /api/control/alpha/mode with invalid mode returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/control/alpha/mode",
            json={"mode": "INVALID"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
        
        print("Invalid alpha mode correctly rejected")


class TestTT5PendingActions:
    """TT5 Pending Actions Queue Tests"""
    
    @pytest.fixture(autouse=True)
    def setup_pending_actions(self):
        """Setup pending actions for testing"""
        # Reset state
        requests.post(f"{BASE_URL}/api/control/reset")
        
        # Set alpha mode to MANUAL to queue actions
        requests.post(
            f"{BASE_URL}/api/control/alpha/mode",
            json={"mode": "MANUAL"},
            headers={"Content-Type": "application/json"}
        )
        
        # Ingest test actions
        test_actions = [
            {
                "scope": "symbol",
                "scope_key": "TESTUSDT",
                "action": "DISABLE_SYMBOL",
                "magnitude": 1.0,
                "reason": "test_action",
                "source": "test",
                "confidence": 0.8,
                "auto_apply": False
            },
            {
                "scope": "symbol",
                "scope_key": "TESTETH",
                "action": "REDUCE_RISK",
                "magnitude": 0.5,
                "reason": "test_reduce",
                "source": "test",
                "confidence": 0.6,
                "auto_apply": False
            }
        ]
        
        requests.post(
            f"{BASE_URL}/api/control/alpha/ingest",
            json={"actions": test_actions},
            headers={"Content-Type": "application/json"}
        )
        
        yield
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/control/reset")
    
    def test_ingest_alpha_actions_manual_mode(self):
        """POST /api/control/alpha/ingest queues actions when mode=MANUAL"""
        # Set to MANUAL mode
        requests.post(
            f"{BASE_URL}/api/control/alpha/mode",
            json={"mode": "MANUAL"},
            headers={"Content-Type": "application/json"}
        )
        
        # Ingest new action
        test_action = {
            "scope": "symbol",
            "scope_key": "NEWTEST",
            "action": "DISABLE_SYMBOL",
            "magnitude": 1.0,
            "reason": "new_test",
            "source": "test",
            "confidence": 0.9,
            "auto_apply": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/control/alpha/ingest",
            json={"actions": [test_action]},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["data"]["status"] == "processed"
        assert data["data"]["mode"] == "MANUAL"
        assert data["data"]["queued"] >= 1
        
        print(f"Ingested action: queued={data['data']['queued']}")
    
    def test_ingest_alpha_actions_off_mode(self):
        """POST /api/control/alpha/ingest ignores actions when mode=OFF"""
        # Set to OFF mode
        requests.post(
            f"{BASE_URL}/api/control/alpha/mode",
            json={"mode": "OFF"},
            headers={"Content-Type": "application/json"}
        )
        
        # Try to ingest action
        test_action = {
            "scope": "symbol",
            "scope_key": "OFFTEST",
            "action": "DISABLE_SYMBOL",
            "magnitude": 1.0,
            "reason": "off_test",
            "source": "test",
            "confidence": 0.9,
            "auto_apply": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/control/alpha/ingest",
            json={"actions": [test_action]},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["data"]["status"] == "ignored"
        assert data["data"]["reason"] == "alpha_mode_off"
        assert data["data"]["queued"] == 0
        
        print("Actions ignored when alpha_mode=OFF")
    
    def test_get_pending_actions(self):
        """GET /api/control/alpha/pending returns pending actions list"""
        response = requests.get(f"{BASE_URL}/api/control/alpha/pending")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert "data" in data
        assert "count" in data
        assert isinstance(data["data"], list)
        
        # Should have pending actions from setup
        assert data["count"] >= 2
        
        # Verify action structure
        if data["data"]:
            action = data["data"][0]
            required_fields = [
                "pending_id",
                "scope",
                "scope_key",
                "action",
                "magnitude",
                "reason",
                "source",
                "confidence",
                "status",
                "created_at"
            ]
            for field in required_fields:
                assert field in action, f"Missing field: {field}"
            
            assert action["status"] == "PENDING"
        
        print(f"Pending actions: count={data['count']}")
    
    def test_approve_pending_action(self):
        """POST /api/control/alpha/approve/{id} approves a pending action"""
        # Get pending actions
        pending_response = requests.get(f"{BASE_URL}/api/control/alpha/pending")
        pending_data = pending_response.json()
        
        assert pending_data["count"] > 0, "No pending actions to approve"
        
        pending_id = pending_data["data"][0]["pending_id"]
        
        # Approve the action
        response = requests.post(f"{BASE_URL}/api/control/alpha/approve/{pending_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["data"]["status"] == "approved"
        
        # Verify action is no longer pending
        verify_response = requests.get(f"{BASE_URL}/api/control/alpha/pending")
        verify_data = verify_response.json()
        
        pending_ids = [a["pending_id"] for a in verify_data["data"]]
        assert pending_id not in pending_ids
        
        print(f"Approved action: {pending_id}")
    
    def test_reject_pending_action(self):
        """POST /api/control/alpha/reject/{id} rejects a pending action"""
        # Get pending actions
        pending_response = requests.get(f"{BASE_URL}/api/control/alpha/pending")
        pending_data = pending_response.json()
        
        assert pending_data["count"] > 0, "No pending actions to reject"
        
        pending_id = pending_data["data"][0]["pending_id"]
        
        # Reject the action
        response = requests.post(f"{BASE_URL}/api/control/alpha/reject/{pending_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["data"]["status"] == "rejected"
        
        # Verify action is no longer pending
        verify_response = requests.get(f"{BASE_URL}/api/control/alpha/pending")
        verify_data = verify_response.json()
        
        pending_ids = [a["pending_id"] for a in verify_data["data"]]
        assert pending_id not in pending_ids
        
        print(f"Rejected action: {pending_id}")
    
    def test_approve_nonexistent_action(self):
        """POST /api/control/alpha/approve/{id} returns 404 for non-existent action"""
        response = requests.post(f"{BASE_URL}/api/control/alpha/approve/nonexistent-id")
        assert response.status_code == 404
        
        print("Non-existent action correctly returns 404")
    
    def test_reject_nonexistent_action(self):
        """POST /api/control/alpha/reject/{id} returns 404 for non-existent action"""
        response = requests.post(f"{BASE_URL}/api/control/alpha/reject/nonexistent-id")
        assert response.status_code == 404
        
        print("Non-existent action correctly returns 404")
    
    def test_approve_all_actions(self):
        """POST /api/control/alpha/approve-all approves all pending actions"""
        response = requests.post(f"{BASE_URL}/api/control/alpha/approve-all")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["data"]["status"] == "approved_all"
        assert "count" in data["data"]
        
        # Verify no pending actions remain
        verify_response = requests.get(f"{BASE_URL}/api/control/alpha/pending")
        verify_data = verify_response.json()
        assert verify_data["count"] == 0
        
        print(f"Approved all: count={data['data']['count']}")
    
    def test_reject_all_actions(self):
        """POST /api/control/alpha/reject-all rejects all pending actions"""
        # First add some actions
        test_actions = [
            {"scope": "symbol", "scope_key": "REJECT1", "action": "DISABLE_SYMBOL", "magnitude": 1.0, "reason": "test"},
            {"scope": "symbol", "scope_key": "REJECT2", "action": "REDUCE_RISK", "magnitude": 0.5, "reason": "test"}
        ]
        requests.post(
            f"{BASE_URL}/api/control/alpha/ingest",
            json={"actions": test_actions},
            headers={"Content-Type": "application/json"}
        )
        
        response = requests.post(f"{BASE_URL}/api/control/alpha/reject-all")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["data"]["status"] == "rejected_all"
        
        # Verify no pending actions remain
        verify_response = requests.get(f"{BASE_URL}/api/control/alpha/pending")
        verify_data = verify_response.json()
        assert verify_data["count"] == 0
        
        print(f"Rejected all: count={data['data']['count']}")


class TestTT5Overrides:
    """TT5 Overrides Management Tests"""
    
    @pytest.fixture(autouse=True)
    def reset_state(self):
        """Reset control state before each test"""
        requests.post(f"{BASE_URL}/api/control/reset")
        yield
        requests.post(f"{BASE_URL}/api/control/reset")
    
    def test_add_override(self):
        """POST /api/control/override - Add operator override rule"""
        override_data = {
            "override_type": "DISABLE_SYMBOL",
            "scope_key": "TESTUSDT",
            "reason": "Testing override"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/control/override",
            json=override_data,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert "data" in data
        
        override = data["data"]
        assert "rule_id" in override
        assert override["override_type"] == "DISABLE_SYMBOL"
        assert override["scope_key"] == "TESTUSDT"
        assert override["active"] == True
        
        print(f"Added override: {override['rule_id']}")
    
    def test_list_overrides(self):
        """GET /api/control/overrides - List active overrides"""
        # Add an override first
        requests.post(
            f"{BASE_URL}/api/control/override",
            json={"override_type": "DISABLE_SYMBOL", "scope_key": "LISTTEST", "reason": "test"},
            headers={"Content-Type": "application/json"}
        )
        
        response = requests.get(f"{BASE_URL}/api/control/overrides")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert "data" in data
        assert isinstance(data["data"], list)
        
        # Should have at least one override
        assert len(data["data"]) >= 1
        
        print(f"Active overrides: {len(data['data'])}")
    
    def test_remove_override(self):
        """DELETE /api/control/override/{rule_id} - Remove override rule"""
        # Add an override first
        add_response = requests.post(
            f"{BASE_URL}/api/control/override",
            json={"override_type": "DISABLE_SYMBOL", "scope_key": "REMOVETEST", "reason": "test"},
            headers={"Content-Type": "application/json"}
        )
        rule_id = add_response.json()["data"]["rule_id"]
        
        # Remove the override
        response = requests.delete(f"{BASE_URL}/api/control/override/{rule_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["data"]["success"] == True
        
        print(f"Removed override: {rule_id}")


class TestTT5PermissionChecks:
    """TT5 Permission Check Tests"""
    
    @pytest.fixture(autouse=True)
    def reset_state(self):
        """Reset control state before each test"""
        requests.post(f"{BASE_URL}/api/control/reset")
        yield
        requests.post(f"{BASE_URL}/api/control/reset")
    
    def test_can_trade_check(self):
        """GET /api/control/can-trade - Check if trading is allowed"""
        response = requests.get(f"{BASE_URL}/api/control/can-trade")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert "data" in data
        
        permissions = data["data"]
        assert "can_trade" in permissions
        assert "can_open_entry" in permissions
        assert "can_manage_positions" in permissions
        
        # In ACTIVE state, all should be True
        assert permissions["can_trade"] == True
        assert permissions["can_open_entry"] == True
        assert permissions["can_manage_positions"] == True
        
        print(f"Permissions: can_trade={permissions['can_trade']}, can_open_entry={permissions['can_open_entry']}")
    
    def test_can_trade_when_paused(self):
        """Verify can_open_entry is False when paused"""
        # Pause system
        requests.post(f"{BASE_URL}/api/control/pause")
        
        response = requests.get(f"{BASE_URL}/api/control/can-trade")
        data = response.json()
        
        permissions = data["data"]
        assert permissions["can_open_entry"] == False
        
        print("Paused: can_open_entry=False")
    
    def test_can_trade_when_hard_kill(self):
        """Verify can_trade is False when hard kill active"""
        # Activate hard kill
        requests.post(f"{BASE_URL}/api/control/kill/hard")
        
        response = requests.get(f"{BASE_URL}/api/control/can-trade")
        data = response.json()
        
        permissions = data["data"]
        assert permissions["can_trade"] == False
        assert permissions["can_open_entry"] == False
        
        print("Hard kill: can_trade=False, can_open_entry=False")


class TestTT5History:
    """TT5 Action History Tests"""
    
    @pytest.fixture(autouse=True)
    def setup_history(self):
        """Setup some history by approving/rejecting actions"""
        requests.post(f"{BASE_URL}/api/control/reset")
        
        # Set to MANUAL mode
        requests.post(
            f"{BASE_URL}/api/control/alpha/mode",
            json={"mode": "MANUAL"},
            headers={"Content-Type": "application/json"}
        )
        
        # Ingest and approve/reject some actions
        test_actions = [
            {"scope": "symbol", "scope_key": "HIST1", "action": "DISABLE_SYMBOL", "magnitude": 1.0, "reason": "history_test"},
            {"scope": "symbol", "scope_key": "HIST2", "action": "REDUCE_RISK", "magnitude": 0.5, "reason": "history_test"}
        ]
        
        requests.post(
            f"{BASE_URL}/api/control/alpha/ingest",
            json={"actions": test_actions},
            headers={"Content-Type": "application/json"}
        )
        
        # Approve all to create history
        requests.post(f"{BASE_URL}/api/control/alpha/approve-all")
        
        yield
        
        requests.post(f"{BASE_URL}/api/control/reset")
    
    def test_get_action_history(self):
        """GET /api/control/history - Get resolved actions history"""
        response = requests.get(f"{BASE_URL}/api/control/history")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert "data" in data
        assert isinstance(data["data"], list)
        
        # Should have history from setup
        if data["data"]:
            history_item = data["data"][0]
            assert "pending_id" in history_item
            assert "status" in history_item
            assert history_item["status"] in ["APPROVED", "REJECTED", "APPLIED"]
            assert "resolved_at" in history_item
        
        print(f"Action history: count={len(data['data'])}")
    
    def test_get_action_history_with_limit(self):
        """GET /api/control/history?limit=5 - Get limited history"""
        response = requests.get(f"{BASE_URL}/api/control/history?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert len(data["data"]) <= 5
        
        print(f"Limited history: count={len(data['data'])}")


class TestTT5TerminalIntegration:
    """TT5 Terminal State Integration Tests"""
    
    def test_control_for_terminal_state(self):
        """GET /api/control/for-terminal-state - Get control data for terminal"""
        response = requests.get(f"{BASE_URL}/api/control/for-terminal-state")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert "data" in data
        
        print("Terminal state integration endpoint working")


class TestTT5Reset:
    """TT5 Reset Tests"""
    
    def test_reset_control(self):
        """POST /api/control/reset - Reset control to defaults"""
        # First make some changes
        requests.post(f"{BASE_URL}/api/control/pause")
        requests.post(
            f"{BASE_URL}/api/control/alpha/mode",
            json={"mode": "OFF"},
            headers={"Content-Type": "application/json"}
        )
        
        # Reset
        response = requests.post(f"{BASE_URL}/api/control/reset")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert data["message"] == "Control layer reset"
        
        # Verify defaults restored
        state = data["data"]
        assert state["system_state"] == "ACTIVE"
        assert state["alpha_mode"] == "MANUAL"
        assert state["trading_enabled"] == True
        assert state["new_entries_enabled"] == True
        assert state["soft_kill"] == False
        assert state["hard_kill"] == False
        
        print("Reset: all defaults restored")


# Run configuration for pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
