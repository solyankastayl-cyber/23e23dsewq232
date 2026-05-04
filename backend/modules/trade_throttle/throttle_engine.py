"""
Trade Throttle Engine

PHASE 43.4 — Trade Throttle Engine

Execution rate limiter + risk throttle.

Prevents:
- Too frequent trading
- Excessive capital turnover
- Position churn
- Trading after loss streaks

Pipeline position:
Execution Brain → Trade Throttle → Safety Gate → Execution Gateway
"""

from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
from collections import deque

from .throttle_types import (
    ThrottleLevel,
    ThrottleReason,
    TradeThrottleState,
    ThrottleConfig,
    ThrottleCheckResult,
    TradeRecord,
    ThrottleQueuedTrade,
)


class TradeThrottleEngine:
    """
    Trade Throttle Engine — PHASE 43.4
    
    Rate limits and throttles trading activity.
    
    Default limits (pilot-safe):
    - max_trades_per_5min = 3
    - max_turnover_per_hour = 15% portfolio
    - max_position_change = 20%
    - cooldown_after_loss_streak = 10 min
    """
    
    def __init__(self, config: Optional[ThrottleConfig] = None):
        self._config = config or ThrottleConfig()
        
        # Trade history for rate tracking
        self._trade_history: deque = deque(maxlen=1000)
        self._trades_by_symbol: Dict[str, deque] = {}
        
        # Queued trades
        self._queued_trades: Dict[str, ThrottleQueuedTrade] = {}
        
        # Current state
        self._state = TradeThrottleState(
            trades_limit_5min=self._config.max_trades_per_5min,
            turnover_limit_hour_pct=self._config.max_turnover_per_hour_pct,
            position_change_limit=self._config.max_position_changes_per_hour,
        )
        
        # Portfolio value (for turnover calculation)
        self._portfolio_value_usd: float = 100000.0  # Default
        
        # Daily stats
        self._daily_turnover_usd: float = 0.0
        self._last_trade_time: Optional[datetime] = None
    
    # ═══════════════════════════════════════════════════════════
    # 1. Main Check Method
    # ═══════════════════════════════════════════════════════════
    
    def check_throttle(
        self,
        symbol: str,
        side: str,
        size_usd: float,
        strategy: str,
    ) -> ThrottleCheckResult:
        """
        Check if trade should be throttled.
        
        Called BEFORE execution.
        
        Returns:
            ThrottleCheckResult with:
            - allowed: bool
            - throttle_level
            - delay_seconds (if delayed)
            - reduced_size_pct (if size should be reduced)
        """
        now = datetime.now(timezone.utc)
        
        # Emergency block
        if self._config.emergency_block_enabled:
            return ThrottleCheckResult(
                allowed=False,
                throttle_level=ThrottleLevel.BLOCKED,
                reason=ThrottleReason.MANUAL,
                message="Emergency block active",
            )
        
        # Check loss streak cooldown
        if self._state.loss_streak_cooldown_active:
            if self._state.cooldown_ends_at and now < self._state.cooldown_ends_at:
                remaining = (self._state.cooldown_ends_at - now).total_seconds()
                return ThrottleCheckResult(
                    allowed=False,
                    throttle_level=ThrottleLevel.BLOCKED,
                    reason=ThrottleReason.LOSS_STREAK,
                    delay_seconds=int(remaining),
                    message=f"Loss streak cooldown: {int(remaining)}s remaining",
                )
            else:
                # Cooldown expired
                self._state.loss_streak_cooldown_active = False
                self._state.consecutive_losses = 0
        
        # Check minimum trade interval
        if self._last_trade_time:
            elapsed = (now - self._last_trade_time).total_seconds()
            if elapsed < self._config.min_trade_interval_seconds:
                delay = self._config.min_trade_interval_seconds - int(elapsed)
                return ThrottleCheckResult(
                    allowed=False,
                    throttle_level=ThrottleLevel.LOW,
                    reason=ThrottleReason.TRADE_RATE,
                    delay_seconds=delay,
                    message=f"Min interval: wait {delay}s",
                )
        
        # Check 5-minute trade rate
        trades_5min = self._count_trades_in_window(minutes=5)
        if trades_5min >= self._config.max_trades_per_5min:
            self._state.throttle_level = ThrottleLevel.MEDIUM
            self._state.throttle_reason = ThrottleReason.TRADE_RATE
            
            return ThrottleCheckResult(
                allowed=False,
                throttle_level=ThrottleLevel.MEDIUM,
                reason=ThrottleReason.TRADE_RATE,
                delay_seconds=60,  # Wait 1 minute
                message=f"Rate limit: {trades_5min}/{self._config.max_trades_per_5min} trades in 5min",
            )
        
        # Check hourly trade rate
        trades_1h = self._count_trades_in_window(minutes=60)
        if trades_1h >= self._config.max_trades_per_hour:
            return ThrottleCheckResult(
                allowed=False,
                throttle_level=ThrottleLevel.HIGH,
                reason=ThrottleReason.TRADE_RATE,
                delay_seconds=300,  # Wait 5 minutes
                message=f"Hourly limit: {trades_1h}/{self._config.max_trades_per_hour} trades",
            )
        
        # Check symbol-specific rate
        symbol_trades = self._count_symbol_trades_in_window(symbol, minutes=60)
        if symbol_trades >= self._config.max_trades_per_symbol_per_hour:
            return ThrottleCheckResult(
                allowed=False,
                throttle_level=ThrottleLevel.MEDIUM,
                reason=ThrottleReason.TRADE_RATE,
                delay_seconds=120,
                message=f"Symbol limit: {symbol_trades}/{self._config.max_trades_per_symbol_per_hour} for {symbol}",
            )
        
        # Check hourly turnover
        turnover_pct = self._calculate_hourly_turnover_pct()
        if turnover_pct + (size_usd / self._portfolio_value_usd * 100) > self._config.max_turnover_per_hour_pct:
            return ThrottleCheckResult(
                allowed=False,
                throttle_level=ThrottleLevel.HIGH,
                reason=ThrottleReason.TURNOVER_RATE,
                delay_seconds=300,
                message=f"Turnover limit: {turnover_pct:.1f}% + {size_usd/self._portfolio_value_usd*100:.1f}% exceeds {self._config.max_turnover_per_hour_pct}%",
            )
        
        # Check position change limit
        if self._state.position_changes_last_hour >= self._config.max_position_changes_per_hour:
            return ThrottleCheckResult(
                allowed=False,
                throttle_level=ThrottleLevel.MEDIUM,
                reason=ThrottleReason.POSITION_CHURN,
                delay_seconds=180,
                message=f"Position churn limit: {self._state.position_changes_last_hour}/{self._config.max_position_changes_per_hour}",
            )
        
        # All checks passed
        self._state.throttle_level = ThrottleLevel.NONE
        self._state.throttle_reason = ThrottleReason.NONE
        
        return ThrottleCheckResult(
            allowed=True,
            throttle_level=ThrottleLevel.NONE,
            reason=ThrottleReason.NONE,
            message="Trade allowed",
        )
    
    # ═══════════════════════════════════════════════════════════
    # 2. Trade Recording
    # ═══════════════════════════════════════════════════════════
    
    def record_trade(
        self,
        trade_id: str,
        symbol: str,
        side: str,
        size_usd: float,
        strategy: str,
        is_profit: Optional[bool] = None,
        pnl: Optional[float] = None,
    ):
        """
        Record a completed trade.
        
        Called AFTER execution.
        """
        now = datetime.now(timezone.utc)
        
        # Create record
        record = TradeRecord(
            trade_id=trade_id,
            timestamp=now,
            symbol=symbol,
            side=side,
            size_usd=size_usd,
            strategy=strategy,
            is_profit=is_profit,
            pnl=pnl,
        )
        
        # Add to history
        self._trade_history.append(record)
        
        # Track by symbol
        if symbol not in self._trades_by_symbol:
            self._trades_by_symbol[symbol] = deque(maxlen=100)
        self._trades_by_symbol[symbol].append(record)
        
        # Update state
        self._last_trade_time = now
        self._state.trades_allowed_today += 1
        self._state.position_changes_last_hour += 1
        self._daily_turnover_usd += size_usd
        
        # Update 5-min count
        self._state.trades_last_5min = self._count_trades_in_window(minutes=5)
        self._state.turnover_last_hour_pct = self._calculate_hourly_turnover_pct()
        
        # Track loss streak
        if is_profit is not None:
            if not is_profit:
                self._state.consecutive_losses += 1
                
                # Check if should activate cooldown
                if self._state.consecutive_losses >= self._config.loss_streak_threshold:
                    self._activate_loss_cooldown()
            else:
                self._state.consecutive_losses = 0
        
        self._state.updated_at = now
    
    def record_blocked_trade(
        self,
        request_id: str,
        symbol: str,
        side: str,
        size_usd: float,
        strategy: str,
        reason: ThrottleReason,
    ):
        """Record a blocked trade."""
        self._state.blocked_trades_count += 1
        self._state.trades_blocked_today += 1
    
    # ═══════════════════════════════════════════════════════════
    # 3. Queue Management
    # ═══════════════════════════════════════════════════════════
    
    def queue_trade(
        self,
        request_id: str,
        symbol: str,
        side: str,
        size_usd: float,
        strategy: str,
        throttle_reason: ThrottleReason,
        delay_seconds: int,
    ) -> ThrottleQueuedTrade:
        """Queue a trade for later execution."""
        now = datetime.now(timezone.utc)
        
        queued = ThrottleQueuedTrade(
            request_id=request_id,
            symbol=symbol,
            side=side,
            size_usd=size_usd,
            strategy=strategy,
            queued_at=now,
            throttle_reason=throttle_reason,
            estimated_release=now + timedelta(seconds=delay_seconds),
        )
        
        self._queued_trades[queued.queue_id] = queued
        self._state.queued_trades_count += 1
        
        return queued
    
    def release_queued_trade(self, queue_id: str) -> Optional[ThrottleQueuedTrade]:
        """Release a queued trade."""
        queued = self._queued_trades.get(queue_id)
        if queued and queued.status == "QUEUED":
            queued.status = "RELEASED"
            queued.released_at = datetime.now(timezone.utc)
            self._state.queued_trades_count -= 1
            return queued
        return None
    
    def get_ready_queued_trades(self) -> List[ThrottleQueuedTrade]:
        """Get queued trades ready for release."""
        now = datetime.now(timezone.utc)
        ready = []
        
        for queued in self._queued_trades.values():
            if queued.status == "QUEUED" and now >= queued.estimated_release:
                ready.append(queued)
        
        return ready
    
    # ═══════════════════════════════════════════════════════════
    # 4. Helper Methods
    # ═══════════════════════════════════════════════════════════
    
    def _count_trades_in_window(self, minutes: int) -> int:
        """Count trades in last N minutes."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        count = sum(1 for t in self._trade_history if t.timestamp > cutoff)
        return count
    
    def _count_symbol_trades_in_window(self, symbol: str, minutes: int) -> int:
        """Count trades for symbol in last N minutes."""
        if symbol not in self._trades_by_symbol:
            return 0
        
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        count = sum(1 for t in self._trades_by_symbol[symbol] if t.timestamp > cutoff)
        return count
    
    def _calculate_hourly_turnover_pct(self) -> float:
        """Calculate turnover in last hour as % of portfolio."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        turnover = sum(t.size_usd for t in self._trade_history if t.timestamp > cutoff)
        
        if self._portfolio_value_usd > 0:
            return (turnover / self._portfolio_value_usd) * 100
        return 0.0
    
    def _activate_loss_cooldown(self):
        """Activate loss streak cooldown."""
        now = datetime.now(timezone.utc)
        
        self._state.loss_streak_cooldown_active = True
        self._state.cooldown_ends_at = now + timedelta(minutes=self._config.cooldown_after_loss_streak_minutes)
        self._state.throttle_level = ThrottleLevel.BLOCKED
        self._state.throttle_reason = ThrottleReason.LOSS_STREAK
    
    # ═══════════════════════════════════════════════════════════
    # 5. State Management
    # ═══════════════════════════════════════════════════════════
    
    def set_portfolio_value(self, value_usd: float):
        """Set portfolio value for turnover calculations."""
        self._portfolio_value_usd = value_usd
    
    def get_state(self) -> TradeThrottleState:
        """Get current throttle state."""
        # Update counts
        self._state.trades_last_5min = self._count_trades_in_window(minutes=5)
        self._state.turnover_last_hour_pct = self._calculate_hourly_turnover_pct()
        self._state.updated_at = datetime.now(timezone.utc)
        
        return self._state
    
    def get_config(self) -> ThrottleConfig:
        """Get throttle configuration."""
        return self._config
    
    def update_config(self, config: ThrottleConfig):
        """Update throttle configuration."""
        self._config = config
        self._state.trades_limit_5min = config.max_trades_per_5min
        self._state.turnover_limit_hour_pct = config.max_turnover_per_hour_pct
        self._state.position_change_limit = config.max_position_changes_per_hour
    
    def reset_daily_stats(self):
        """Reset daily statistics."""
        self._state.trades_allowed_today = 0
        self._state.trades_blocked_today = 0
        self._state.trades_delayed_today = 0
        self._daily_turnover_usd = 0.0
    
    def set_emergency_block(self, enabled: bool):
        """Enable/disable emergency block."""
        self._config.emergency_block_enabled = enabled
        if enabled:
            self._state.throttle_level = ThrottleLevel.BLOCKED
            self._state.throttle_reason = ThrottleReason.MANUAL
        else:
            self._state.throttle_level = ThrottleLevel.NONE
            self._state.throttle_reason = ThrottleReason.NONE
    
    def get_summary(self) -> Dict:
        """Get throttle summary."""
        state = self.get_state()
        
        return {
            "phase": "43.4",
            "throttle_level": state.throttle_level.value,
            "throttle_reason": state.throttle_reason.value,
            "trades_5min": f"{state.trades_last_5min}/{state.trades_limit_5min}",
            "turnover_hour": f"{state.turnover_last_hour_pct:.1f}%/{state.turnover_limit_hour_pct}%",
            "position_changes": f"{state.position_changes_last_hour}/{state.position_change_limit}",
            "consecutive_losses": state.consecutive_losses,
            "cooldown_active": state.loss_streak_cooldown_active,
            "cooldown_ends_at": state.cooldown_ends_at.isoformat() if state.cooldown_ends_at else None,
            "blocked_today": state.trades_blocked_today,
            "queued_count": state.queued_trades_count,
            "emergency_block": self._config.emergency_block_enabled,
            "config": {
                "max_trades_per_5min": self._config.max_trades_per_5min,
                "max_trades_per_hour": self._config.max_trades_per_hour,
                "max_turnover_per_hour_pct": self._config.max_turnover_per_hour_pct,
                "max_position_change_pct": self._config.max_position_change_per_trade_pct,
                "loss_streak_threshold": self._config.loss_streak_threshold,
                "cooldown_minutes": self._config.cooldown_after_loss_streak_minutes,
            },
        }


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_throttle_engine: Optional[TradeThrottleEngine] = None


def get_trade_throttle_engine() -> TradeThrottleEngine:
    """Get singleton instance."""
    global _throttle_engine
    if _throttle_engine is None:
        _throttle_engine = TradeThrottleEngine()
    return _throttle_engine
