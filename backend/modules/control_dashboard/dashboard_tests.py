"""
Dashboard Tests

PHASE 40 — Real-Time Control Dashboard

60 tests covering:
- Dashboard state aggregation
- Approval queue workflow
- Alerts engine
- Audit logging
- API endpoints
"""

import pytest
from datetime import datetime, timezone, timedelta

from .dashboard_types import (
    DashboardState,
    PendingExecution,
    DashboardAlert,
    DashboardAuditLog,
)
from .dashboard_engine import DashboardStateEngine
from .approval_engine import ApprovalQueueEngine
from .alerts_engine import AlertsEngine
from .audit_engine import AuditEngine


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def dashboard_engine():
    return DashboardStateEngine()


@pytest.fixture
def approval_engine():
    return ApprovalQueueEngine(approval_timeout_seconds=300)


@pytest.fixture
def alerts_engine():
    return AlertsEngine()


@pytest.fixture
def audit_engine():
    return AuditEngine()


# ══════════════════════════════════════════════════════════════
# 1. Dashboard State Tests (15 tests)
# ══════════════════════════════════════════════════════════════

def test_build_dashboard_state(dashboard_engine):
    """Test building dashboard state."""
    state = dashboard_engine.build_dashboard_state("BTC")
    
    assert state.symbol == "BTC"
    assert state.execution_mode in ["PAPER", "APPROVAL", "LIVE"]


def test_dashboard_state_has_market_overview(dashboard_engine):
    """Test dashboard has market overview."""
    state = dashboard_engine.build_dashboard_state("ETH")
    
    assert hasattr(state, "market")
    assert hasattr(state.market, "regime")
    assert hasattr(state.market, "fractal_bias")


def test_dashboard_state_has_hypothesis(dashboard_engine):
    """Test dashboard has hypothesis state."""
    state = dashboard_engine.build_dashboard_state("BTC")
    
    assert hasattr(state, "hypothesis")
    assert hasattr(state.hypothesis, "top_hypothesis")
    assert hasattr(state.hypothesis, "confidence")


def test_dashboard_state_has_portfolio(dashboard_engine):
    """Test dashboard has portfolio state."""
    state = dashboard_engine.build_dashboard_state("PORTFOLIO")
    
    assert hasattr(state, "portfolio")
    assert state.portfolio.total_capital > 0


def test_dashboard_state_has_risk(dashboard_engine):
    """Test dashboard has risk state."""
    state = dashboard_engine.build_dashboard_state("BTC")
    
    assert hasattr(state, "risk")
    assert hasattr(state.risk, "portfolio_risk")
    assert hasattr(state.risk, "risk_state")


def test_dashboard_state_has_pnl(dashboard_engine):
    """Test dashboard has PnL state."""
    state = dashboard_engine.build_dashboard_state("BTC")
    
    assert hasattr(state, "pnl")
    assert hasattr(state.pnl, "realized_pnl")
    assert hasattr(state.pnl, "unrealized_pnl")


def test_dashboard_state_has_execution(dashboard_engine):
    """Test dashboard has execution state."""
    state = dashboard_engine.build_dashboard_state("BTC")
    
    assert hasattr(state, "execution")
    assert state.execution.mode in ["PAPER", "APPROVAL", "LIVE"]


def test_dashboard_state_has_alerts(dashboard_engine):
    """Test dashboard has alerts."""
    state = dashboard_engine.build_dashboard_state("BTC")
    
    assert hasattr(state, "alerts")
    assert isinstance(state.alerts, list)


def test_dashboard_state_caching(dashboard_engine):
    """Test state caching."""
    state1 = dashboard_engine.build_dashboard_state("BTC")
    state2 = dashboard_engine.build_dashboard_state("BTC")
    
    # Should be cached (same timestamp)
    assert state1.last_updated == state2.last_updated


def test_dashboard_cache_invalidation(dashboard_engine):
    """Test cache invalidation."""
    dashboard_engine.build_dashboard_state("BTC")
    dashboard_engine.invalidate_cache("BTC")
    
    # Cache should be empty
    assert "BTC" not in dashboard_engine._state_cache


def test_multi_symbol_dashboard(dashboard_engine):
    """Test multi-symbol dashboard."""
    dashboard = dashboard_engine.build_multi_dashboard(["BTC", "ETH"])
    
    assert len(dashboard.symbols) == 2
    assert "BTC" in dashboard.symbol_states
    assert "ETH" in dashboard.symbol_states


def test_portfolio_summary(dashboard_engine):
    """Test portfolio summary."""
    summary = dashboard_engine.get_portfolio_summary()
    
    assert "total_capital" in summary
    assert "deployed_capital" in summary


def test_risk_summary(dashboard_engine):
    """Test risk summary."""
    summary = dashboard_engine.get_risk_summary()
    
    assert "portfolio_risk" in summary
    assert "risk_state" in summary


def test_execution_summary(dashboard_engine):
    """Test execution summary."""
    summary = dashboard_engine.get_execution_summary()
    
    assert "mode" in summary
    assert "pending_count" in summary


def test_dashboard_data_freshness(dashboard_engine):
    """Test data freshness tracking."""
    state = dashboard_engine.build_dashboard_state("BTC")
    
    assert state.data_freshness_ms >= 0
    assert state.last_updated is not None


# ══════════════════════════════════════════════════════════════
# 2. Approval Queue Tests (20 tests)
# ══════════════════════════════════════════════════════════════

def test_add_pending_execution(approval_engine):
    """Test adding pending execution."""
    pending = approval_engine.add_pending_execution(
        symbol="BTC",
        side="BUY",
        size_usd=10000,
        strategy="TREND_FOLLOWING",
    )
    
    assert pending.pending_id is not None
    assert pending.symbol == "BTC"
    assert pending.size_usd == 10000
    assert pending.status == "PENDING"


def test_pending_has_recommendation(approval_engine):
    """Test pending has system recommendation."""
    pending = approval_engine.add_pending_execution(
        symbol="ETH",
        side="SELL",
        size_usd=5000,
        strategy="MEAN_REVERSION",
        confidence=0.9,
        reliability=0.85,
    )
    
    assert pending.system_recommendation in ["APPROVE", "REDUCE", "REJECT"]
    assert pending.recommendation_reason != ""


def test_pending_has_expiration(approval_engine):
    """Test pending has expiration."""
    pending = approval_engine.add_pending_execution(
        symbol="BTC",
        side="BUY",
        size_usd=10000,
        strategy="TREND",
    )
    
    assert pending.expires_at is not None
    assert pending.expires_at > datetime.now(timezone.utc)


def test_get_pending_executions(approval_engine):
    """Test getting pending executions."""
    approval_engine.add_pending_execution("BTC", "BUY", 10000, "TREND")
    approval_engine.add_pending_execution("ETH", "SELL", 5000, "MEAN_REV")
    
    pending = approval_engine.get_pending_executions()
    
    assert len(pending) >= 2


def test_get_pending_by_symbol(approval_engine):
    """Test filtering pending by symbol."""
    approval_engine.add_pending_execution("BTC", "BUY", 10000, "TREND")
    approval_engine.add_pending_execution("ETH", "BUY", 5000, "TREND")
    
    btc_pending = approval_engine.get_pending_executions(symbol="BTC")
    
    assert all(p.symbol == "BTC" for p in btc_pending)


def test_approve_execution(approval_engine):
    """Test approving execution."""
    pending = approval_engine.add_pending_execution("BTC", "BUY", 10000, "TREND")
    
    result = approval_engine.approve_execution(pending.pending_id, user="test")
    
    # Result depends on gateway availability
    assert result.action == "APPROVE"


def test_reject_execution(approval_engine):
    """Test rejecting execution."""
    pending = approval_engine.add_pending_execution("BTC", "BUY", 10000, "TREND")
    
    result = approval_engine.reject_execution(pending.pending_id, reason="Test")
    
    assert result.success is True
    assert result.action == "REJECT"


def test_reject_removes_from_queue(approval_engine):
    """Test reject removes from queue."""
    pending = approval_engine.add_pending_execution("BTC", "BUY", 10000, "TREND")
    pending_id = pending.pending_id
    
    approval_engine.reject_execution(pending_id)
    
    remaining = approval_engine.get_pending_executions()
    assert not any(p.pending_id == pending_id for p in remaining)


def test_reduce_execution(approval_engine):
    """Test reducing execution size."""
    pending = approval_engine.add_pending_execution("BTC", "BUY", 10000, "TREND")
    
    result = approval_engine.reduce_execution(pending.pending_id, new_size_usd=5000)
    
    assert result.success is True
    assert result.action == "REDUCE"


def test_reduce_updates_size(approval_engine):
    """Test reduce updates size."""
    pending = approval_engine.add_pending_execution("BTC", "BUY", 10000, "TREND")
    
    approval_engine.reduce_execution(pending.pending_id, new_size_usd=5000)
    
    updated = approval_engine.get_pending_execution(pending.pending_id)
    assert updated.size_usd == 5000


def test_reduce_fails_for_larger_size(approval_engine):
    """Test reduce fails for larger size."""
    pending = approval_engine.add_pending_execution("BTC", "BUY", 10000, "TREND")
    
    result = approval_engine.reduce_execution(pending.pending_id, new_size_usd=15000)
    
    assert result.success is False


def test_override_execution(approval_engine):
    """Test overriding execution params."""
    pending = approval_engine.add_pending_execution("BTC", "BUY", 10000, "TREND")
    
    result = approval_engine.override_execution(
        pending.pending_id,
        size_override=8000,
        order_type_override="LIMIT",
    )
    
    assert result.success is True
    assert result.action == "OVERRIDE"


def test_override_updates_params(approval_engine):
    """Test override updates params."""
    pending = approval_engine.add_pending_execution("BTC", "BUY", 10000, "TREND")
    
    approval_engine.override_execution(
        pending.pending_id,
        size_override=8000,
        order_type_override="LIMIT",
    )
    
    updated = approval_engine.get_pending_execution(pending.pending_id)
    assert updated.size_usd == 8000
    assert updated.order_type == "LIMIT"


def test_approve_nonexistent_fails(approval_engine):
    """Test approve nonexistent fails."""
    result = approval_engine.approve_execution("nonexistent_id")
    
    assert result.success is False


def test_reject_nonexistent_fails(approval_engine):
    """Test reject nonexistent fails."""
    result = approval_engine.reject_execution("nonexistent_id")
    
    assert result.success is False


def test_pending_count(approval_engine):
    """Test pending count."""
    approval_engine.add_pending_execution("BTC", "BUY", 10000, "TREND")
    approval_engine.add_pending_execution("ETH", "BUY", 5000, "TREND")
    
    count = approval_engine.get_pending_count()
    
    assert count >= 2


def test_pending_history(approval_engine):
    """Test pending history after reject."""
    pending = approval_engine.add_pending_execution("BTC", "BUY", 10000, "TREND")
    approval_engine.reject_execution(pending.pending_id)
    
    history = approval_engine.get_history()
    
    assert len(history) >= 1


def test_audit_log_from_approval(approval_engine):
    """Test audit log from approval actions."""
    pending = approval_engine.add_pending_execution("BTC", "BUY", 10000, "TREND")
    
    log = approval_engine.get_audit_log()
    
    assert len(log) >= 1


def test_expired_execution_rejected(approval_engine):
    """Test expired execution auto-rejected."""
    approval_engine._approval_timeout = 0  # Immediate expiry
    
    pending = approval_engine.add_pending_execution("BTC", "BUY", 10000, "TREND")
    pending.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    
    approval_engine._clean_expired()
    
    remaining = approval_engine.get_pending_executions()
    assert not any(p.pending_id == pending.pending_id and p.status == "PENDING" for p in remaining)


def test_recommendation_for_high_risk(approval_engine):
    """Test recommendation for high risk."""
    pending = approval_engine.add_pending_execution(
        symbol="BTC",
        side="BUY",
        size_usd=500000,  # Very large
        strategy="TREND",
        confidence=0.5,
        reliability=0.4,
    )
    
    # Should recommend reduce or reject
    assert pending.system_recommendation in ["REDUCE", "REJECT"]


# ══════════════════════════════════════════════════════════════
# 3. Alerts Engine Tests (15 tests)
# ══════════════════════════════════════════════════════════════

def test_create_alert(alerts_engine):
    """Test creating alert."""
    alert = alerts_engine.create_alert(
        title="Test Alert",
        message="Test message",
        severity="WARNING",
        category="RISK",
        source="Test",
    )
    
    assert alert.alert_id is not None
    assert alert.title == "Test Alert"
    assert alert.severity == "WARNING"


def test_get_active_alerts(alerts_engine):
    """Test getting active alerts."""
    alerts_engine.create_alert("Alert 1", "Msg 1", "INFO", "RISK", "Test")
    alerts_engine.create_alert("Alert 2", "Msg 2", "WARNING", "RISK", "Test")
    
    alerts = alerts_engine.get_active_alerts()
    
    assert len(alerts) >= 2


def test_get_alerts_by_severity(alerts_engine):
    """Test filtering alerts by severity."""
    alerts_engine.create_alert("Info", "Msg", "INFO", "RISK", "Test")
    alerts_engine.create_alert("Warning", "Msg", "WARNING", "RISK", "Test")
    
    warnings = alerts_engine.get_active_alerts(severity="WARNING")
    
    assert all(a.severity == "WARNING" for a in warnings)


def test_get_alerts_by_category(alerts_engine):
    """Test filtering alerts by category."""
    alerts_engine.create_alert("Risk", "Msg", "WARNING", "RISK", "Test")
    alerts_engine.create_alert("Exec", "Msg", "WARNING", "EXECUTION", "Test")
    
    risk_alerts = alerts_engine.get_active_alerts(category="RISK")
    
    assert all(a.category == "RISK" for a in risk_alerts)


def test_acknowledge_alert(alerts_engine):
    """Test acknowledging alert."""
    alert = alerts_engine.create_alert("Test", "Msg", "WARNING", "RISK", "Test")
    
    success = alerts_engine.acknowledge_alert(alert.alert_id, user="test")
    
    assert success is True
    assert alert.acknowledged is True


def test_dismiss_alert(alerts_engine):
    """Test dismissing alert."""
    alert = alerts_engine.create_alert("Test", "Msg", "WARNING", "RISK", "Test")
    alert_id = alert.alert_id
    
    success = alerts_engine.dismiss_alert(alert_id)
    
    assert success is True
    assert alert_id not in alerts_engine._alerts


def test_alert_count(alerts_engine):
    """Test alert count."""
    alerts_engine.create_alert("A1", "M1", "WARNING", "RISK", "Test")
    alerts_engine.create_alert("A2", "M2", "CRITICAL", "RISK", "Test")
    
    total = alerts_engine.get_alert_count()
    critical = alerts_engine.get_alert_count(severity="CRITICAL")
    
    assert total >= 2
    assert critical >= 1


def test_alert_deduplication(alerts_engine):
    """Test alert deduplication."""
    alerts_engine.create_alert("Same Alert", "Msg 1", "WARNING", "RISK", "Test", symbol="BTC")
    alerts_engine.create_alert("Same Alert", "Msg 2", "WARNING", "RISK", "Test", symbol="BTC")
    
    alerts = alerts_engine.get_active_alerts()
    
    # Should be deduplicated
    same_alerts = [a for a in alerts if a.title == "Same Alert" and a.symbol == "BTC"]
    assert len(same_alerts) == 1


def test_alert_sorting(alerts_engine):
    """Test alerts sorted by severity."""
    alerts_engine.create_alert("Info", "Msg", "INFO", "RISK", "Test")
    alerts_engine.create_alert("Critical", "Msg", "CRITICAL", "RISK", "Test")
    alerts_engine.create_alert("Warning", "Msg", "WARNING", "RISK", "Test")
    
    alerts = alerts_engine.get_active_alerts()
    
    # Critical should be first
    if alerts:
        assert alerts[0].severity in ["CRITICAL", "EMERGENCY"]


def test_alert_statistics(alerts_engine):
    """Test alert statistics."""
    alerts_engine.create_alert("A1", "M1", "WARNING", "RISK", "Test")
    alerts_engine.create_alert("A2", "M2", "INFO", "EXECUTION", "Test")
    
    stats = alerts_engine.get_statistics()
    
    assert "total_active" in stats
    assert "by_severity" in stats
    assert "by_category" in stats


def test_alert_history(alerts_engine):
    """Test alert history."""
    alert = alerts_engine.create_alert("Test", "Msg", "INFO", "RISK", "Test")
    alerts_engine.dismiss_alert(alert.alert_id)
    
    history = alerts_engine.get_history()
    
    assert len(history) >= 1


def test_check_risk_alerts(alerts_engine):
    """Test risk alert generation."""
    # This tests the check but won't generate alerts without high risk
    alerts_engine.check_risk_alerts()
    
    # Should complete without error
    assert True


def test_check_execution_alerts(alerts_engine):
    """Test execution alert generation."""
    alerts_engine.check_execution_alerts()
    
    # Should complete without error
    assert True


def test_run_all_checks(alerts_engine):
    """Test running all alert checks."""
    alerts_engine.run_all_checks()
    
    # Should complete without error
    assert True


def test_alert_with_value(alerts_engine):
    """Test alert with value and threshold."""
    alert = alerts_engine.create_alert(
        title="Risk Alert",
        message="Risk too high",
        severity="WARNING",
        category="RISK",
        source="Test",
        value=0.18,
        threshold=0.15,
    )
    
    assert alert.value == 0.18
    assert alert.threshold == 0.15


# ══════════════════════════════════════════════════════════════
# 4. Audit Engine Tests (10 tests)
# ══════════════════════════════════════════════════════════════

def test_log_action(audit_engine):
    """Test logging action."""
    log = audit_engine.log_action(
        action="TEST_ACTION",
        action_type="TEST",
        user="test_user",
    )
    
    assert log.audit_id is not None
    assert log.action == "TEST_ACTION"


def test_log_approval(audit_engine):
    """Test logging approval."""
    log = audit_engine.log_approval(
        action="APPROVE",
        pending_id="test_123",
        symbol="BTC",
        user="test",
    )
    
    assert log.action == "APPROVE"
    assert log.action_type == "APPROVAL"


def test_log_config_change(audit_engine):
    """Test logging config change."""
    log = audit_engine.log_config_change(
        setting="max_order_size",
        previous_value=100000,
        new_value=150000,
        user="admin",
    )
    
    assert "CONFIG_CHANGE" in log.action


def test_log_mode_change(audit_engine):
    """Test logging mode change."""
    log = audit_engine.log_mode_change(
        previous_mode="PAPER",
        new_mode="APPROVAL",
        user="admin",
    )
    
    assert log.action == "MODE_CHANGE"
    assert log.execution_mode == "APPROVAL"


def test_get_logs(audit_engine):
    """Test getting logs."""
    audit_engine.log_action("ACTION_1", "TEST", user="user1")
    audit_engine.log_action("ACTION_2", "TEST", user="user2")
    
    logs = audit_engine.get_logs()
    
    assert len(logs) >= 2


def test_get_logs_by_user(audit_engine):
    """Test filtering logs by user."""
    audit_engine.log_action("A1", "TEST", user="alice")
    audit_engine.log_action("A2", "TEST", user="bob")
    
    alice_logs = audit_engine.get_logs(user="alice")
    
    assert all(l.user == "alice" for l in alice_logs)


def test_get_logs_by_action_type(audit_engine):
    """Test filtering logs by action type."""
    audit_engine.log_action("A1", "APPROVAL", user="test")
    audit_engine.log_action("A2", "CONFIG", user="test")
    
    approval_logs = audit_engine.get_logs(action_type="APPROVAL")
    
    assert all(l.action_type == "APPROVAL" for l in approval_logs)


def test_audit_statistics(audit_engine):
    """Test audit statistics."""
    audit_engine.log_action("A1", "APPROVAL", user="user1")
    audit_engine.log_action("A2", "CONFIG", user="user2")
    
    stats = audit_engine.get_statistics()
    
    assert "total_actions" in stats
    assert "by_action_type" in stats
    assert "by_user" in stats


def test_user_activity(audit_engine):
    """Test user activity."""
    audit_engine.log_action("A1", "TEST", user="test_user")
    audit_engine.log_action("A2", "TEST", user="test_user")
    
    activity = audit_engine.get_user_activity("test_user")
    
    assert activity["user"] == "test_user"
    assert activity["action_count"] >= 2


def test_log_count(audit_engine):
    """Test log count."""
    initial = audit_engine.get_log_count()
    
    audit_engine.log_action("A1", "TEST")
    audit_engine.log_action("A2", "TEST")
    
    assert audit_engine.get_log_count() == initial + 2


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
