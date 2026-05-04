"""
Circuit Breaker Engine

PHASE 41.4 — Circuit Breaker Engine

Automatic risk-control system that monitors market and portfolio
conditions and triggers protective actions.

Integration:
- Checked before Execution Brain and Exchange Gateway
- Can trigger Kill Switch on critical conditions
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta

from .breaker_types import (
    BreakerState,
    BreakerRuleType,
    BreakerAction,
    BreakerSeverity,
    BreakerRule,
    BreakerEvent,
    BreakerStatus,
    BreakerConfig,
    BreakerCheckResult,
)


class CircuitBreakerEngine:
    """
    Circuit Breaker Engine — PHASE 41.4

    Monitors conditions and triggers protective actions.
    """

    def __init__(self, config: Optional[BreakerConfig] = None):
        self._config = config or BreakerConfig()
        self._rules: Dict[str, BreakerRule] = {}
        self._events: List[BreakerEvent] = []
        self._execution_errors: List[datetime] = []
        self._loss_streak: int = 0
        self._total_trips: int = 0

        self._init_default_rules()

    def _init_default_rules(self):
        """Initialize default circuit breaker rules."""
        c = self._config

        self._rules["DRAWDOWN"] = BreakerRule(
            rule_id="DRAWDOWN",
            rule_type=BreakerRuleType.PORTFOLIO_DRAWDOWN,
            name="Portfolio Drawdown",
            description="Triggers on portfolio drawdown",
            warning_threshold=c.drawdown_warning,
            trigger_threshold=c.drawdown_trigger,
            critical_threshold=c.drawdown_critical,
            warning_actions=[BreakerAction.ALERT_ONLY],
            trigger_actions=[BreakerAction.REDUCE_POSITION_SIZE, BreakerAction.SWITCH_SAFE_MODE],
            critical_actions=[BreakerAction.TRIGGER_KILL_SWITCH],
            size_modifier_warning=0.75,
            size_modifier_trigger=0.5,
            size_modifier_critical=0.0,
            recovery_threshold=c.drawdown_warning * 0.5,
        )

        self._rules["DAILY_LOSS"] = BreakerRule(
            rule_id="DAILY_LOSS",
            rule_type=BreakerRuleType.DAILY_LOSS,
            name="Daily Loss Limit",
            description="Triggers on daily P&L loss",
            warning_threshold=c.daily_loss_warning,
            trigger_threshold=c.daily_loss_trigger,
            critical_threshold=c.daily_loss_critical,
            warning_actions=[BreakerAction.ALERT_ONLY],
            trigger_actions=[BreakerAction.BLOCK_NEW_ENTRIES],
            critical_actions=[BreakerAction.TRIGGER_KILL_SWITCH],
            size_modifier_warning=0.8,
            size_modifier_trigger=0.0,
            size_modifier_critical=0.0,
            recovery_threshold=c.daily_loss_warning * 0.5,
        )

        self._rules["SLIPPAGE"] = BreakerRule(
            rule_id="SLIPPAGE",
            rule_type=BreakerRuleType.SLIPPAGE,
            name="Slippage Limit",
            description="Triggers on excessive slippage",
            warning_threshold=c.slippage_warning_bps,
            trigger_threshold=c.slippage_trigger_bps,
            critical_threshold=c.slippage_critical_bps,
            warning_actions=[BreakerAction.ALERT_ONLY],
            trigger_actions=[BreakerAction.LIMIT_ONLY, BreakerAction.REDUCE_POSITION_SIZE],
            critical_actions=[BreakerAction.BLOCK_NEW_ENTRIES],
            size_modifier_warning=0.9,
            size_modifier_trigger=0.5,
            size_modifier_critical=0.0,
            recovery_threshold=c.slippage_warning_bps * 0.5,
            cooldown_seconds=120,
        )

        self._rules["LOSS_STREAK"] = BreakerRule(
            rule_id="LOSS_STREAK",
            rule_type=BreakerRuleType.LOSS_STREAK,
            name="Loss Streak",
            description="Triggers on consecutive losing trades",
            warning_threshold=float(c.loss_streak_warning),
            trigger_threshold=float(c.loss_streak_trigger),
            critical_threshold=float(c.loss_streak_critical),
            warning_actions=[BreakerAction.ALERT_ONLY],
            trigger_actions=[BreakerAction.PAUSE_STRATEGY, BreakerAction.REDUCE_POSITION_SIZE],
            critical_actions=[BreakerAction.BLOCK_NEW_ENTRIES, BreakerAction.TRIGGER_KILL_SWITCH],
            size_modifier_warning=0.75,
            size_modifier_trigger=0.5,
            size_modifier_critical=0.0,
            recovery_threshold=0,
            cooldown_seconds=600,
        )

        self._rules["VOLATILITY_SPIKE"] = BreakerRule(
            rule_id="VOLATILITY_SPIKE",
            rule_type=BreakerRuleType.VOLATILITY_SPIKE,
            name="Volatility Spike",
            description="Triggers on sudden volatility increase (multiplier of normal)",
            warning_threshold=c.volatility_spike_warning,
            trigger_threshold=c.volatility_spike_trigger,
            critical_threshold=c.volatility_spike_critical,
            warning_actions=[BreakerAction.REDUCE_POSITION_SIZE],
            trigger_actions=[BreakerAction.REDUCE_POSITION_SIZE, BreakerAction.LIMIT_ONLY],
            critical_actions=[BreakerAction.BLOCK_NEW_ENTRIES, BreakerAction.SWITCH_SAFE_MODE],
            size_modifier_warning=0.7,
            size_modifier_trigger=0.4,
            size_modifier_critical=0.0,
            recovery_threshold=c.volatility_spike_warning * 0.8,
            cooldown_seconds=180,
        )

        self._rules["EXEC_ERRORS"] = BreakerRule(
            rule_id="EXEC_ERRORS",
            rule_type=BreakerRuleType.EXECUTION_ERRORS,
            name="Execution Errors",
            description="Triggers on too many execution errors",
            warning_threshold=float(c.max_execution_errors * 0.6),
            trigger_threshold=float(c.max_execution_errors),
            critical_threshold=float(c.max_execution_errors * 2),
            warning_actions=[BreakerAction.ALERT_ONLY],
            trigger_actions=[BreakerAction.LIMIT_ONLY],
            critical_actions=[BreakerAction.TRIGGER_KILL_SWITCH],
            size_modifier_warning=1.0,
            size_modifier_trigger=0.5,
            size_modifier_critical=0.0,
            recovery_threshold=0,
            cooldown_seconds=120,
        )

    # ═══════════════════════════════════════════════════════════
    # 1. Rule Management
    # ═══════════════════════════════════════════════════════════

    def add_rule(self, rule: BreakerRule):
        """Add or update a circuit breaker rule."""
        self._rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a circuit breaker rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False
            return True
        return False

    def get_rules(self) -> List[BreakerRule]:
        return list(self._rules.values())

    def get_rule(self, rule_id: str) -> Optional[BreakerRule]:
        return self._rules.get(rule_id)

    # ═══════════════════════════════════════════════════════════
    # 2. Core Check — Called before every order
    # ═══════════════════════════════════════════════════════════

    def check_order_allowed(self, symbol: str = "", size_usd: float = 0, side: str = "BUY") -> BreakerCheckResult:
        """
        Check if order is allowed based on all circuit breaker rules.
        Called by Execution Gateway before every order.
        """
        if not self._config.enabled:
            return BreakerCheckResult()

        result = BreakerCheckResult()
        min_size_modifier = 1.0

        # Update rule values from live data
        self._update_rule_values()

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            # Check if in cooldown
            if rule.last_triggered_at and rule.state != BreakerState.CLOSED:
                elapsed = (datetime.now(timezone.utc) - rule.last_triggered_at).total_seconds()
                if elapsed < rule.cooldown_seconds and rule.state == BreakerState.OPEN:
                    # Still in cooldown
                    result.tripped_rules.append(rule.rule_id)
                    min_size_modifier = min(min_size_modifier, rule.size_modifier_trigger)
                    continue

            value = rule.current_value

            if value >= rule.critical_threshold:
                # CRITICAL
                event = self._trip_rule(rule, value, BreakerSeverity.CRITICAL)
                self._execute_actions(rule.critical_actions)
                min_size_modifier = min(min_size_modifier, rule.size_modifier_critical)
                result.tripped_rules.append(rule.rule_id)
                if BreakerAction.BLOCK_NEW_ENTRIES in rule.critical_actions or BreakerAction.TRIGGER_KILL_SWITCH in rule.critical_actions:
                    result.new_entries_blocked = True

            elif value >= rule.trigger_threshold:
                # TRIGGER
                event = self._trip_rule(rule, value, BreakerSeverity.HIGH)
                self._execute_actions(rule.trigger_actions)
                min_size_modifier = min(min_size_modifier, rule.size_modifier_trigger)
                result.tripped_rules.append(rule.rule_id)
                if BreakerAction.BLOCK_NEW_ENTRIES in rule.trigger_actions:
                    result.new_entries_blocked = True
                if BreakerAction.LIMIT_ONLY in rule.trigger_actions:
                    result.limit_only = True

            elif value >= rule.warning_threshold:
                # WARNING
                if rule.state == BreakerState.CLOSED:
                    self._record_warning(rule, value)
                min_size_modifier = min(min_size_modifier, rule.size_modifier_warning)
                result.warnings.append(f"{rule.name}: {value:.4f} >= {rule.warning_threshold:.4f}")

            else:
                # RECOVERY check
                if rule.state != BreakerState.CLOSED:
                    self._try_recovery(rule, value)

        result.size_modifier = min_size_modifier
        if result.new_entries_blocked:
            result.allowed = False
            result.blocked_reason = f"Circuit breaker tripped: {', '.join(result.tripped_rules)}"
            result.state = BreakerState.OPEN
        elif result.tripped_rules:
            result.state = BreakerState.HALF_OPEN

        return result

    # ═══════════════════════════════════════════════════════════
    # 3. Run All Checks (periodic)
    # ═══════════════════════════════════════════════════════════

    def run_checks(self) -> BreakerStatus:
        """Run all circuit breaker checks and return status."""
        self._update_rule_values()
        check = self.check_order_allowed()
        return self.get_status()

    # ═══════════════════════════════════════════════════════════
    # 4. Data Feed — Record events
    # ═══════════════════════════════════════════════════════════

    def record_fill(self, pnl: float):
        """Record a trade fill for loss streak tracking."""
        if pnl < 0:
            self._loss_streak += 1
        else:
            self._loss_streak = 0

    def record_execution_error(self, error: str = ""):
        """Record execution error."""
        self._execution_errors.append(datetime.now(timezone.utc))
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._config.error_window_seconds)
        self._execution_errors = [e for e in self._execution_errors if e > cutoff]

    def record_slippage(self, slippage_bps: float):
        """Record slippage for tracking."""
        if "SLIPPAGE" in self._rules:
            self._rules["SLIPPAGE"].current_value = slippage_bps

    # ═══════════════════════════════════════════════════════════
    # 5. Status & Events
    # ═══════════════════════════════════════════════════════════

    def get_status(self) -> BreakerStatus:
        """Get overall circuit breaker status."""
        tripped = [r for r in self._rules.values() if r.state != BreakerState.CLOSED]
        enabled = [r for r in self._rules.values() if r.enabled]

        overall_state = BreakerState.CLOSED
        if any(r.state == BreakerState.OPEN for r in tripped):
            overall_state = BreakerState.OPEN
        elif tripped:
            overall_state = BreakerState.HALF_OPEN

        # Aggregate modifiers
        size_mod = 1.0
        entries_blocked = False
        limit_only = False
        kill_triggered = False

        for r in tripped:
            if r.state == BreakerState.OPEN:
                sev = self._get_current_severity(r)
                if sev == BreakerSeverity.CRITICAL:
                    size_mod = min(size_mod, r.size_modifier_critical)
                    if BreakerAction.TRIGGER_KILL_SWITCH in r.critical_actions:
                        kill_triggered = True
                    if BreakerAction.BLOCK_NEW_ENTRIES in r.critical_actions:
                        entries_blocked = True
                else:
                    size_mod = min(size_mod, r.size_modifier_trigger)
                    if BreakerAction.BLOCK_NEW_ENTRIES in r.trigger_actions:
                        entries_blocked = True
                    if BreakerAction.LIMIT_ONLY in r.trigger_actions:
                        limit_only = True

        now = datetime.now(timezone.utc)
        trips_24h = len([e for e in self._events if (now - e.timestamp).total_seconds() < 86400])

        return BreakerStatus(
            state=overall_state,
            active_rules=len(enabled),
            tripped_rules=len(tripped),
            total_rules=len(self._rules),
            size_modifier=size_mod,
            new_entries_blocked=entries_blocked,
            limit_only=limit_only,
            kill_switch_triggered=kill_triggered,
            tripped_rule_ids=[r.rule_id for r in tripped],
            tripped_details=[
                {"rule_id": r.rule_id, "name": r.name, "value": r.current_value, "state": r.state.value}
                for r in tripped
            ],
            total_trips=self._total_trips,
            trips_last_24h=trips_24h,
            last_trip_at=self._events[-1].timestamp if self._events else None,
            last_check=now,
        )

    def get_events(self, limit: int = 100) -> List[BreakerEvent]:
        return self._events[-limit:]

    def get_config(self) -> BreakerConfig:
        return self._config

    # ═══════════════════════════════════════════════════════════
    # 6. Reset
    # ═══════════════════════════════════════════════════════════

    def reset_all(self):
        """Reset all circuit breakers to CLOSED."""
        for rule in self._rules.values():
            rule.state = BreakerState.CLOSED
            rule.current_value = 0.0
        self._loss_streak = 0
        self._execution_errors.clear()

    def reset_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            self._rules[rule_id].state = BreakerState.CLOSED
            self._rules[rule_id].current_value = 0.0
            return True
        return False

    # ═══════════════════════════════════════════════════════════
    # Internal Methods
    # ═══════════════════════════════════════════════════════════

    def _update_rule_values(self):
        """Update rule values from live data sources."""
        # Drawdown
        if "DRAWDOWN" in self._rules:
            self._rules["DRAWDOWN"].current_value = self._get_drawdown()

        # Daily loss
        if "DAILY_LOSS" in self._rules:
            self._rules["DAILY_LOSS"].current_value = self._get_daily_loss()

        # Loss streak
        if "LOSS_STREAK" in self._rules:
            self._rules["LOSS_STREAK"].current_value = float(self._loss_streak)

        # Volatility spike
        if "VOLATILITY_SPIKE" in self._rules:
            self._rules["VOLATILITY_SPIKE"].current_value = self._get_volatility_multiplier()

        # Execution errors
        if "EXEC_ERRORS" in self._rules:
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._config.error_window_seconds)
            recent = [e for e in self._execution_errors if e > cutoff]
            self._rules["EXEC_ERRORS"].current_value = float(len(recent))

    def _trip_rule(self, rule: BreakerRule, value: float, severity: BreakerSeverity) -> BreakerEvent:
        """Trip a circuit breaker rule."""
        prev_state = rule.state
        rule.state = BreakerState.OPEN
        rule.current_value = value
        rule.last_triggered_at = datetime.now(timezone.utc)
        rule.trip_count += 1
        self._total_trips += 1

        threshold = rule.critical_threshold if severity == BreakerSeverity.CRITICAL else rule.trigger_threshold
        actions = rule.critical_actions if severity == BreakerSeverity.CRITICAL else rule.trigger_actions
        modifier = rule.size_modifier_critical if severity == BreakerSeverity.CRITICAL else rule.size_modifier_trigger

        event = BreakerEvent(
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            severity=severity,
            previous_state=prev_state,
            new_state=BreakerState.OPEN,
            current_value=value,
            threshold=threshold,
            actions_taken=actions,
            size_modifier=modifier,
            message=f"{rule.name}: {value:.4f} >= {threshold:.4f} [{severity.value}]",
        )

        self._events.append(event)
        self._save_event(event)
        return event

    def _record_warning(self, rule: BreakerRule, value: float):
        """Record a warning-level event."""
        event = BreakerEvent(
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            severity=BreakerSeverity.LOW,
            previous_state=rule.state,
            new_state=rule.state,
            current_value=value,
            threshold=rule.warning_threshold,
            actions_taken=rule.warning_actions,
            size_modifier=rule.size_modifier_warning,
            message=f"{rule.name} WARNING: {value:.4f} >= {rule.warning_threshold:.4f}",
        )
        self._events.append(event)

    def _try_recovery(self, rule: BreakerRule, value: float):
        """Try to recover a tripped rule."""
        if not self._config.auto_recovery:
            return

        if value <= rule.recovery_threshold:
            prev_state = rule.state
            rule.state = BreakerState.CLOSED
            event = BreakerEvent(
                rule_id=rule.rule_id,
                rule_type=rule.rule_type,
                severity=BreakerSeverity.LOW,
                previous_state=prev_state,
                new_state=BreakerState.CLOSED,
                current_value=value,
                threshold=rule.recovery_threshold,
                message=f"{rule.name} RECOVERED: {value:.4f} <= {rule.recovery_threshold:.4f}",
            )
            self._events.append(event)

    def _execute_actions(self, actions: List[BreakerAction]):
        """Execute breaker actions."""
        for action in actions:
            if action == BreakerAction.TRIGGER_KILL_SWITCH:
                self._trigger_kill_switch()
            elif action == BreakerAction.SWITCH_SAFE_MODE:
                self._switch_safe_mode()

    def _trigger_kill_switch(self):
        """Trigger the kill switch from circuit breaker."""
        try:
            from modules.safety_kill_switch.kill_switch_engine import get_kill_switch
            from modules.safety_kill_switch.kill_switch_types import (
                ActivateKillSwitchRequest,
                KillSwitchTrigger,
            )
            ks = get_kill_switch()
            ks.activate(ActivateKillSwitchRequest(
                trigger=KillSwitchTrigger.CIRCUIT_BREAKER,
                reason="Circuit breaker critical threshold reached",
                user="circuit_breaker",
                cancel_pending=True,
                reduce_exposure=True,
                emergency=False,
            ))
        except Exception as e:
            print(f"[CircuitBreaker] Error triggering kill switch: {e}")

    def _switch_safe_mode(self):
        """Switch system to safe mode."""
        try:
            from modules.safety_kill_switch.kill_switch_engine import get_kill_switch
            ks = get_kill_switch()
            ks.enter_safe_mode(reason="Circuit breaker triggered safe mode", user="circuit_breaker")
        except Exception as e:
            print(f"[CircuitBreaker] Error switching to safe mode: {e}")

    def _get_current_severity(self, rule: BreakerRule) -> BreakerSeverity:
        if rule.current_value >= rule.critical_threshold:
            return BreakerSeverity.CRITICAL
        if rule.current_value >= rule.trigger_threshold:
            return BreakerSeverity.HIGH
        if rule.current_value >= rule.warning_threshold:
            return BreakerSeverity.MEDIUM
        return BreakerSeverity.LOW

    # ═══════════════════════════════════════════════════════════
    # Data Sources
    # ═══════════════════════════════════════════════════════════

    def _get_drawdown(self) -> float:
        try:
            from modules.portfolio_manager import get_portfolio_engine
            engine = get_portfolio_engine()
            state = engine.get_portfolio_state()
            return state.max_drawdown
        except Exception:
            return 0.0

    def _get_daily_loss(self) -> float:
        try:
            from modules.portfolio_manager import get_portfolio_engine
            engine = get_portfolio_engine()
            state = engine.get_portfolio_state()
            if state.total_value > 0:
                return max(0, -state.daily_pnl / state.total_value)
            return 0.0
        except Exception:
            return 0.0

    def _get_volatility_multiplier(self) -> float:
        try:
            from modules.risk_budget import get_risk_budget_engine
            engine = get_risk_budget_engine()
            budget = engine.get_portfolio_risk_budget()
            return budget.total_risk / 0.15 if budget.total_risk > 0 else 1.0
        except Exception:
            return 1.0

    def _save_event(self, event: BreakerEvent):
        try:
            from core.database import get_database
            db = get_database()
            if db is not None:
                db.circuit_breaker_events.insert_one({
                    "event_id": event.event_id,
                    "rule_id": event.rule_id,
                    "rule_type": event.rule_type.value,
                    "severity": event.severity.value,
                    "previous_state": event.previous_state.value,
                    "new_state": event.new_state.value,
                    "current_value": event.current_value,
                    "threshold": event.threshold,
                    "actions_taken": [a.value for a in event.actions_taken],
                    "size_modifier": event.size_modifier,
                    "message": event.message,
                    "timestamp": event.timestamp.isoformat(),
                })
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_circuit_breaker: Optional[CircuitBreakerEngine] = None


def get_circuit_breaker() -> CircuitBreakerEngine:
    """Get singleton instance."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreakerEngine()
    return _circuit_breaker
