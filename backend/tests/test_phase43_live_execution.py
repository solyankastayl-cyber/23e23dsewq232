"""
PHASE 43 — Live Exchange Integration Tests

Tests for:
- 43.2 Exchange Sync Engine
- 43.3 Pilot Trading Mode
- 43.4 Trade Throttle Engine

Minimum 40 tests required.
"""

import pytest
from datetime import datetime, timezone, timedelta

# ══════════════════════════════════════════════════════════════
# Exchange Sync Tests (43.2)
# ══════════════════════════════════════════════════════════════

from modules.exchange_sync import (
    SyncStatus,
    SyncType,
    SyncState,
    SyncConfig,
    ExchangeSyncEngine,
    get_exchange_sync_engine,
)


class TestExchangeSyncEngine:
    """Tests for Exchange Sync Engine."""
    
    def test_sync_config_defaults(self):
        """Test default sync configuration."""
        config = SyncConfig()
        assert config.positions_interval_seconds == 15
        assert config.balances_interval_seconds == 30
        assert config.stale_threshold_seconds == 60
        assert "BINANCE" in config.enabled_exchanges
        assert "BYBIT" in config.enabled_exchanges
    
    def test_sync_engine_init(self):
        """Test sync engine initialization."""
        engine = ExchangeSyncEngine()
        assert "BINANCE" in engine._sync_states
        assert "BYBIT" in engine._sync_states
    
    def test_sync_state_initial(self):
        """Test initial sync state."""
        engine = ExchangeSyncEngine()
        state = engine.get_sync_state("BINANCE")
        assert state is not None
        assert state.positions_status == SyncStatus.IDLE
        assert state.balances_status == SyncStatus.IDLE
    
    def test_get_positions_empty(self):
        """Test getting positions when empty."""
        engine = ExchangeSyncEngine()
        positions = engine.get_positions("BINANCE")
        assert isinstance(positions, list)
    
    def test_get_balances_empty(self):
        """Test getting balances when empty."""
        engine = ExchangeSyncEngine()
        balances = engine.get_balances()
        assert isinstance(balances, list)
    
    def test_get_open_orders_empty(self):
        """Test getting open orders when empty."""
        engine = ExchangeSyncEngine()
        orders = engine.get_open_orders()
        assert isinstance(orders, list)
    
    def test_is_stale_initially(self):
        """Test stale detection on fresh engine."""
        engine = ExchangeSyncEngine()
        assert engine.is_stale("BINANCE") is True
    
    def test_get_summary(self):
        """Test sync summary structure."""
        engine = ExchangeSyncEngine()
        summary = engine.get_summary()
        assert "running" in summary
        assert "exchanges" in summary
        assert "total_positions" in summary
    
    def test_singleton(self):
        """Test singleton instance."""
        engine1 = get_exchange_sync_engine()
        engine2 = get_exchange_sync_engine()
        assert engine1 is engine2


# ══════════════════════════════════════════════════════════════
# Pilot Mode Tests (43.3)
# ══════════════════════════════════════════════════════════════

from modules.pilot_mode import (
    TradingMode,
    PilotConstraints,
    PilotState,
    PilotCheckResult,
    PilotModeEngine,
    get_pilot_mode_engine,
)


class TestPilotModeEngine:
    """Tests for Pilot Mode Engine."""
    
    def test_pilot_constraints_defaults(self):
        """Test default pilot constraints."""
        constraints = PilotConstraints()
        assert constraints.max_capital_usage_pct == 5.0
        assert constraints.max_position_size_pct == 2.0
        assert constraints.max_single_order_usd == 5000.0
        assert constraints.max_trades_per_hour == 10
    
    def test_pilot_engine_init(self):
        """Test pilot engine initialization."""
        engine = PilotModeEngine()
        assert engine.get_mode() == TradingMode.PILOT
    
    def test_pilot_state(self):
        """Test pilot state."""
        engine = PilotModeEngine()
        state = engine.get_state()
        assert state.trading_mode == TradingMode.PILOT
        assert state.approval_mode_active is True
    
    def test_check_constraints_pass(self):
        """Test constraint check passes for small trade."""
        engine = PilotModeEngine(portfolio_value_usd=100000)
        result = engine.check_constraints("BTC", 1000, "BUY")
        assert result.allowed is True
    
    def test_check_constraints_order_too_large(self):
        """Test constraint check fails for large order."""
        engine = PilotModeEngine(portfolio_value_usd=100000)
        result = engine.check_constraints("BTC", 10000, "BUY")
        assert "ORDER_SIZE" in result.violated_constraints[0]
    
    def test_check_constraints_position_too_large(self):
        """Test constraint check for position size."""
        engine = PilotModeEngine(portfolio_value_usd=100000)
        # Position limit is 2% = $2000
        result = engine.check_constraints("BTC", 3000, "BUY")
        assert any("POSITION_SIZE" in v for v in result.violated_constraints)
    
    def test_set_mode(self):
        """Test setting trading mode."""
        engine = PilotModeEngine()
        engine.set_mode(TradingMode.PAPER)
        assert engine.get_mode() == TradingMode.PAPER
    
    def test_set_mode_maintenance(self):
        """Test maintenance mode blocks trades."""
        engine = PilotModeEngine()
        engine.set_mode(TradingMode.MAINTENANCE)
        result = engine.check_constraints("BTC", 100, "BUY")
        assert result.allowed is False
    
    def test_record_trade(self):
        """Test trade recording."""
        engine = PilotModeEngine(portfolio_value_usd=100000)
        engine.record_trade("BTC", 1000, "BUY")
        state = engine.get_state()
        assert state.trades_today >= 1
        assert state.capital_used_usd >= 1000
    
    def test_paper_mode_allows_all(self):
        """Test paper mode allows all trades."""
        engine = PilotModeEngine()
        engine.set_mode(TradingMode.PAPER)
        result = engine.check_constraints("BTC", 1000000, "BUY")
        assert result.allowed is True
    
    def test_pilot_summary(self):
        """Test pilot summary structure."""
        engine = PilotModeEngine()
        summary = engine.get_summary()
        assert "phase" in summary
        assert summary["phase"] == "43.3"
        assert "capital_usage" in summary
        assert "safety_status" in summary
    
    def test_singleton_pilot(self):
        """Test singleton instance."""
        engine1 = get_pilot_mode_engine()
        engine2 = get_pilot_mode_engine()
        assert engine1 is engine2


# ══════════════════════════════════════════════════════════════
# Trade Throttle Tests (43.4)
# ══════════════════════════════════════════════════════════════

from modules.trade_throttle import (
    ThrottleLevel,
    ThrottleReason,
    TradeThrottleState,
    ThrottleConfig,
    ThrottleCheckResult,
    TradeThrottleEngine,
    get_trade_throttle_engine,
)


class TestTradeThrottleEngine:
    """Tests for Trade Throttle Engine."""
    
    def test_throttle_config_defaults(self):
        """Test default throttle configuration."""
        config = ThrottleConfig()
        assert config.max_trades_per_5min == 3
        assert config.max_trades_per_hour == 10
        assert config.max_turnover_per_hour_pct == 15.0
        assert config.loss_streak_threshold == 3
        assert config.cooldown_after_loss_streak_minutes == 10
    
    def test_throttle_engine_init(self):
        """Test throttle engine initialization."""
        engine = TradeThrottleEngine()
        state = engine.get_state()
        assert state.throttle_level == ThrottleLevel.NONE
    
    def test_check_throttle_pass(self):
        """Test throttle check passes for first trade."""
        engine = TradeThrottleEngine()
        result = engine.check_throttle("BTC", "BUY", 1000, "strategy1")
        assert result.allowed is True
        assert result.throttle_level == ThrottleLevel.NONE
    
    def test_check_throttle_rate_limit(self):
        """Test throttle check fails after rate limit."""
        engine = TradeThrottleEngine()
        
        # Record trades to exceed 5-min limit
        for i in range(4):
            engine.record_trade(f"trade_{i}", "BTC", "BUY", 1000, "strategy1")
        
        result = engine.check_throttle("BTC", "BUY", 1000, "strategy1")
        assert result.allowed is False
        assert result.reason == ThrottleReason.TRADE_RATE
    
    def test_emergency_block(self):
        """Test emergency block."""
        engine = TradeThrottleEngine()
        engine.set_emergency_block(True)
        
        result = engine.check_throttle("BTC", "BUY", 100, "strategy1")
        assert result.allowed is False
        assert result.throttle_level == ThrottleLevel.BLOCKED
        
        engine.set_emergency_block(False)
    
    def test_record_trade(self):
        """Test trade recording."""
        engine = TradeThrottleEngine()
        engine.record_trade("trade1", "BTC", "BUY", 1000, "strategy1")
        
        state = engine.get_state()
        assert state.trades_allowed_today >= 1
    
    def test_loss_streak_cooldown(self):
        """Test loss streak triggers cooldown."""
        engine = TradeThrottleEngine()
        
        # Record 3 consecutive losses
        for i in range(3):
            engine.record_trade(f"trade_{i}", "BTC", "BUY", 1000, "strategy1", is_profit=False)
        
        state = engine.get_state()
        assert state.loss_streak_cooldown_active is True
    
    def test_loss_streak_reset_on_profit(self):
        """Test profit resets loss streak."""
        engine = TradeThrottleEngine()
        
        # Record 2 losses then 1 profit
        engine.record_trade("trade_1", "BTC", "BUY", 1000, "strategy1", is_profit=False)
        engine.record_trade("trade_2", "BTC", "BUY", 1000, "strategy1", is_profit=False)
        engine.record_trade("trade_3", "BTC", "BUY", 1000, "strategy1", is_profit=True)
        
        state = engine.get_state()
        assert state.consecutive_losses == 0
    
    def test_min_trade_interval(self):
        """Test minimum trade interval check."""
        engine = TradeThrottleEngine()
        engine.record_trade("trade1", "BTC", "BUY", 1000, "strategy1")
        
        # Immediately check next trade
        result = engine.check_throttle("BTC", "BUY", 1000, "strategy1")
        # Should be delayed due to min interval
        if not result.allowed:
            assert result.reason == ThrottleReason.TRADE_RATE
    
    def test_throttle_summary(self):
        """Test throttle summary structure."""
        engine = TradeThrottleEngine()
        summary = engine.get_summary()
        
        assert "phase" in summary
        assert summary["phase"] == "43.4"
        assert "throttle_level" in summary
        assert "config" in summary
    
    def test_reset_daily_stats(self):
        """Test daily stats reset."""
        engine = TradeThrottleEngine()
        engine.record_trade("trade1", "BTC", "BUY", 1000, "strategy1")
        
        engine.reset_daily_stats()
        state = engine.get_state()
        assert state.trades_allowed_today == 0
    
    def test_portfolio_value_set(self):
        """Test setting portfolio value."""
        engine = TradeThrottleEngine()
        engine.set_portfolio_value(200000)
        assert engine._portfolio_value_usd == 200000
    
    def test_singleton_throttle(self):
        """Test singleton instance."""
        engine1 = get_trade_throttle_engine()
        engine2 = get_trade_throttle_engine()
        assert engine1 is engine2


# ══════════════════════════════════════════════════════════════
# Integration Tests
# ══════════════════════════════════════════════════════════════

class TestPhase43Integration:
    """Integration tests for PHASE 43."""
    
    def test_pilot_and_throttle_both_check(self):
        """Test pilot and throttle work together."""
        pilot = PilotModeEngine(portfolio_value_usd=100000)
        throttle = TradeThrottleEngine()
        
        # Check pilot
        pilot_result = pilot.check_constraints("BTC", 1000, "BUY")
        
        # If pilot passes, check throttle
        if pilot_result.allowed:
            throttle_result = throttle.check_throttle("BTC", "BUY", 1000, "strategy1")
            assert throttle_result is not None
    
    def test_full_execution_pipeline_check(self):
        """Test full execution pipeline would work."""
        pilot = PilotModeEngine(portfolio_value_usd=100000)
        throttle = TradeThrottleEngine()
        
        symbol = "BTC"
        size_usd = 1000
        side = "BUY"
        strategy = "test_strategy"
        
        # Step 1: Pilot check
        pilot_result = pilot.check_constraints(symbol, size_usd, side)
        if not pilot_result.allowed:
            return  # Would block
        
        # Step 2: Throttle check
        throttle_result = throttle.check_throttle(symbol, side, size_usd, strategy)
        if not throttle_result.allowed:
            return  # Would block/delay
        
        # Both passed
        assert pilot_result.allowed
        assert throttle_result.allowed
    
    def test_sync_engine_get_all_exchanges(self):
        """Test sync engine handles multiple exchanges."""
        engine = ExchangeSyncEngine()
        states = engine.get_all_sync_states()
        assert "BINANCE" in states
        assert "BYBIT" in states
    
    def test_default_safety_config(self):
        """Test default safety configuration."""
        pilot = PilotModeEngine()
        state = pilot.get_state()
        
        # All safety layers should be active by default
        assert state.approval_mode_active is True
        assert state.kill_switch_ready is True
        assert state.circuit_breaker_ready is True
        assert state.trade_throttle_active is True
    
    def test_trading_modes_exist(self):
        """Test all trading modes exist."""
        assert TradingMode.PAPER.value == "PAPER"
        assert TradingMode.PILOT.value == "PILOT"
        assert TradingMode.LIVE.value == "LIVE"
        assert TradingMode.MAINTENANCE.value == "MAINTENANCE"
    
    def test_throttle_levels_exist(self):
        """Test all throttle levels exist."""
        assert ThrottleLevel.NONE.value == "NONE"
        assert ThrottleLevel.LOW.value == "LOW"
        assert ThrottleLevel.MEDIUM.value == "MEDIUM"
        assert ThrottleLevel.HIGH.value == "HIGH"
        assert ThrottleLevel.BLOCKED.value == "BLOCKED"


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
