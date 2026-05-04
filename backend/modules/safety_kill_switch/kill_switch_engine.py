"""
Kill Switch Engine

PHASE 41.3 — Kill Switch Engine

Emergency stop system for trading operations.

Key features:
1. Manual emergency stop
2. Automatic triggers based on risk/PnL
3. Order blocking and cancellation
4. Position reduction
5. Safe mode transition

Integration:
- Execution Gateway
- Portfolio Manager
- Risk Budget Engine
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta

from .kill_switch_types import (
    KillSwitchState,
    KillSwitchTrigger,
    KillSwitchAction,
    KillSwitchStatus,
    KillSwitchEvent,
    KillSwitchConfig,
    KillSwitchCheckResult,
    ActivateKillSwitchRequest,
    DeactivateKillSwitchRequest,
)


# ══════════════════════════════════════════════════════════════
# Kill Switch Engine
# ══════════════════════════════════════════════════════════════

class KillSwitchEngine:
    """
    Kill Switch Engine — PHASE 41.3
    
    Emergency stop system for trading operations.
    
    States:
    - ACTIVE: Normal operation
    - SAFE_MODE: Reduced operations
    - DISABLED: All new operations blocked
    - EMERGENCY_STOP: Immediate halt, close positions
    """
    
    def __init__(self, config: Optional[KillSwitchConfig] = None):
        self._config = config or KillSwitchConfig()
        
        # Current state
        self._state = KillSwitchState.ACTIVE
        self._status = KillSwitchStatus()
        
        # Event history
        self._events: List[KillSwitchEvent] = []
        
        # Error tracking
        self._execution_errors: List[datetime] = []
        
        # Blocked stats
        self._blocked_count = 0
        self._cancelled_count = 0
    
    # ═══════════════════════════════════════════════════════════
    # 1. Activation / Deactivation
    # ═══════════════════════════════════════════════════════════
    
    def activate(self, request: ActivateKillSwitchRequest) -> KillSwitchEvent:
        """
        Activate kill switch.
        
        Actions:
        - Block new orders
        - Cancel pending orders (optional)
        - Close positions (optional, dangerous)
        - Reduce exposure (optional)
        """
        previous_state = self._state
        
        # Determine new state
        if request.emergency:
            new_state = KillSwitchState.EMERGENCY_STOP
        else:
            new_state = KillSwitchState.DISABLED
        
        self._state = new_state
        
        # Take actions
        actions_taken = [KillSwitchAction.BLOCK_NEW_ORDERS]
        
        if request.cancel_pending:
            self._cancel_pending_orders()
            actions_taken.append(KillSwitchAction.CANCEL_PENDING)
        
        if request.close_positions:
            self._close_all_positions()
            actions_taken.append(KillSwitchAction.CLOSE_POSITIONS)
        
        if request.reduce_exposure:
            self._reduce_exposure()
            actions_taken.append(KillSwitchAction.REDUCE_EXPOSURE)
        
        # Update status
        self._status.state = new_state
        self._status.is_active = False
        self._status.is_safe_mode = False
        self._status.last_trigger = request.trigger
        self._status.last_trigger_reason = request.reason
        self._status.last_triggered_at = datetime.now(timezone.utc)
        self._status.triggered_by = request.user
        self._status.actions_taken = actions_taken
        
        # Create event
        event = KillSwitchEvent(
            event_type="ACTIVATED",
            previous_state=previous_state,
            new_state=new_state,
            trigger=request.trigger,
            trigger_reason=request.reason,
            actions_taken=actions_taken,
            triggered_by=request.user,
            portfolio_risk=self._get_portfolio_risk(),
            drawdown=self._get_drawdown(),
        )
        
        self._events.append(event)
        self._save_event(event)
        
        return event
    
    def deactivate(self, request: DeactivateKillSwitchRequest) -> KillSwitchEvent:
        """
        Deactivate kill switch and return to ACTIVE state.
        
        Requires confirmation that conditions are safe.
        """
        if not request.confirm_safe:
            raise ValueError("Must confirm safe to deactivate kill switch")
        
        previous_state = self._state
        new_state = KillSwitchState.ACTIVE
        
        self._state = new_state
        
        # Update status
        self._status.state = new_state
        self._status.is_active = True
        self._status.is_safe_mode = False
        self._status.actions_taken = []
        self._status.blocked_orders_count = 0
        self._status.cancelled_orders_count = 0
        self._status.uptime_since = datetime.now(timezone.utc)
        
        # Create event
        event = KillSwitchEvent(
            event_type="DEACTIVATED",
            previous_state=previous_state,
            new_state=new_state,
            trigger_reason=request.reason,
            triggered_by=request.user,
        )
        
        self._events.append(event)
        self._save_event(event)
        
        return event
    
    def enter_safe_mode(self, reason: str = "", user: str = "system") -> KillSwitchEvent:
        """
        Enter safe mode - reduced operations.
        
        New orders allowed but with size reduction.
        """
        previous_state = self._state
        new_state = KillSwitchState.SAFE_MODE
        
        self._state = new_state
        
        # Update status
        self._status.state = new_state
        self._status.is_active = True
        self._status.is_safe_mode = True
        self._status.last_trigger_reason = reason
        self._status.last_triggered_at = datetime.now(timezone.utc)
        self._status.actions_taken = [KillSwitchAction.SWITCH_TO_SAFE_MODE]
        
        # Create event
        event = KillSwitchEvent(
            event_type="STATE_CHANGE",
            previous_state=previous_state,
            new_state=new_state,
            trigger_reason=reason,
            actions_taken=[KillSwitchAction.SWITCH_TO_SAFE_MODE],
            triggered_by=user,
        )
        
        self._events.append(event)
        
        return event
    
    # ═══════════════════════════════════════════════════════════
    # 2. Order Check
    # ═══════════════════════════════════════════════════════════
    
    def check_order_allowed(
        self,
        symbol: str,
        size_usd: float,
        side: str,
    ) -> KillSwitchCheckResult:
        """
        Check if order is allowed based on kill switch state.
        
        Called by Execution Gateway before every order.
        """
        result = KillSwitchCheckResult(state=self._state)
        
        # EMERGENCY_STOP or DISABLED - block all
        if self._state in [KillSwitchState.EMERGENCY_STOP, KillSwitchState.DISABLED]:
            result.allowed = False
            result.blocked_reason = f"Kill switch active: {self._state.value}"
            self._blocked_count += 1
            self._status.blocked_orders_count = self._blocked_count
            return result
        
        # SAFE_MODE - allow with reduction
        if self._state == KillSwitchState.SAFE_MODE:
            result.allowed = True
            result.size_modified = True
            result.size_modifier = self._config.exposure_reduction_factor
            result.warnings.append(f"Safe mode: size reduced to {self._config.exposure_reduction_factor*100:.0f}%")
            return result
        
        # ACTIVE - check automatic triggers
        should_trigger, trigger, reason = self._check_automatic_triggers()
        
        if should_trigger:
            # Trigger kill switch
            self.activate(ActivateKillSwitchRequest(
                trigger=trigger,
                reason=reason,
                user="automatic",
                cancel_pending=self._config.auto_cancel_pending,
                reduce_exposure=self._config.auto_reduce_exposure,
            ))
            
            result.allowed = False
            result.state = self._state
            result.blocked_reason = f"Kill switch triggered: {reason}"
            return result
        
        # All clear
        result.allowed = True
        return result
    
    def _check_automatic_triggers(self) -> tuple:
        """
        Check for automatic trigger conditions.
        
        Returns: (should_trigger, trigger_type, reason)
        """
        # Check portfolio risk
        risk = self._get_portfolio_risk()
        if risk > self._config.portfolio_risk_emergency:
            return True, KillSwitchTrigger.PORTFOLIO_RISK_BREACH, f"Portfolio risk {risk*100:.1f}% exceeds emergency limit"
        
        # Check drawdown
        drawdown = self._get_drawdown()
        if drawdown > self._config.drawdown_emergency:
            return True, KillSwitchTrigger.DRAWDOWN_LIMIT, f"Drawdown {drawdown*100:.1f}% exceeds emergency limit"
        
        # Check execution errors
        if self._check_execution_error_loop():
            return True, KillSwitchTrigger.EXECUTION_ERROR_LOOP, "Too many execution errors"
        
        # Check daily loss
        daily_loss = self._get_daily_loss()
        if daily_loss > self._config.daily_loss_emergency:
            return True, KillSwitchTrigger.PNL_COLLAPSE, f"Daily loss {daily_loss*100:.1f}% exceeds emergency limit"
        
        return False, None, ""
    
    # ═══════════════════════════════════════════════════════════
    # 3. Error Tracking
    # ═══════════════════════════════════════════════════════════
    
    def record_execution_error(self, error_message: str = ""):
        """Record execution error for error loop detection."""
        self._execution_errors.append(datetime.now(timezone.utc))
        
        # Clean old errors
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._config.error_window_seconds)
        self._execution_errors = [e for e in self._execution_errors if e > cutoff]
    
    def _check_execution_error_loop(self) -> bool:
        """Check if too many execution errors."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._config.error_window_seconds)
        recent_errors = [e for e in self._execution_errors if e > cutoff]
        return len(recent_errors) >= self._config.max_execution_errors
    
    # ═══════════════════════════════════════════════════════════
    # 4. Actions
    # ═══════════════════════════════════════════════════════════
    
    def _cancel_pending_orders(self):
        """Cancel all pending orders."""
        try:
            from modules.execution_gateway import get_execution_gateway
            from modules.control_dashboard import get_approval_engine
            
            gateway = get_execution_gateway()
            approval = get_approval_engine()
            
            # Cancel pending approvals
            pending = approval.get_pending_executions()
            for p in pending:
                approval.reject_execution(p.pending_id, user="kill_switch", reason="Kill switch activated")
                self._cancelled_count += 1
            
            self._status.cancelled_orders_count = self._cancelled_count
            
        except Exception as e:
            print(f"[KillSwitch] Error cancelling orders: {e}")
    
    def _close_all_positions(self):
        """Close all positions (dangerous!)."""
        # This is a placeholder - actual implementation would
        # send market orders to close all positions
        print("[KillSwitch] WARNING: Close all positions requested")
        self._status.closed_positions_count = 0
    
    def _reduce_exposure(self):
        """Reduce portfolio exposure."""
        # This sets a flag that Execution Gateway will use
        # to reduce all new position sizes
        self._status.is_safe_mode = True
    
    # ═══════════════════════════════════════════════════════════
    # 5. State Getters
    # ═══════════════════════════════════════════════════════════
    
    def get_state(self) -> KillSwitchState:
        """Get current state."""
        return self._state
    
    def get_status(self) -> KillSwitchStatus:
        """Get full status."""
        self._status.state = self._state
        self._status.last_check = datetime.now(timezone.utc)
        return self._status
    
    def is_active(self) -> bool:
        """Check if system is active (not killed)."""
        return self._state == KillSwitchState.ACTIVE
    
    def is_safe_mode(self) -> bool:
        """Check if in safe mode."""
        return self._state == KillSwitchState.SAFE_MODE
    
    def is_disabled(self) -> bool:
        """Check if disabled."""
        return self._state in [KillSwitchState.DISABLED, KillSwitchState.EMERGENCY_STOP]
    
    def get_size_modifier(self) -> float:
        """Get position size modifier based on state."""
        if self._state == KillSwitchState.SAFE_MODE:
            return self._config.exposure_reduction_factor
        if self._state in [KillSwitchState.DISABLED, KillSwitchState.EMERGENCY_STOP]:
            return 0.0
        return 1.0
    
    def get_events(self, limit: int = 100) -> List[KillSwitchEvent]:
        """Get event history."""
        return self._events[-limit:]
    
    def get_config(self) -> KillSwitchConfig:
        """Get configuration."""
        return self._config
    
    # ═══════════════════════════════════════════════════════════
    # 6. Helper Methods
    # ═══════════════════════════════════════════════════════════
    
    def _get_portfolio_risk(self) -> float:
        """Get current portfolio risk."""
        try:
            from modules.risk_budget import get_risk_budget_engine
            engine = get_risk_budget_engine()
            state = engine.get_portfolio_risk_budget()
            return state.total_risk
        except Exception:
            return 0.0
    
    def _get_drawdown(self) -> float:
        """Get current drawdown."""
        try:
            from modules.portfolio_manager import get_portfolio_engine
            engine = get_portfolio_engine()
            state = engine.get_portfolio_state()
            return state.max_drawdown
        except Exception:
            return 0.0
    
    def _get_daily_loss(self) -> float:
        """Get daily loss percentage."""
        try:
            from modules.portfolio_manager import get_portfolio_engine
            engine = get_portfolio_engine()
            state = engine.get_portfolio_state()
            if state.total_value > 0:
                return max(0, -state.daily_pnl / state.total_value)
            return 0.0
        except Exception:
            return 0.0
    
    def _save_event(self, event: KillSwitchEvent):
        """Save event to database."""
        try:
            from core.database import get_database
            db = get_database()
            if db is not None:
                db.safety_kill_switch_events.insert_one({
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "previous_state": event.previous_state.value,
                    "new_state": event.new_state.value,
                    "trigger": event.trigger.value if event.trigger else None,
                    "trigger_reason": event.trigger_reason,
                    "actions_taken": [a.value for a in event.actions_taken],
                    "triggered_by": event.triggered_by,
                    "portfolio_risk": event.portfolio_risk,
                    "drawdown": event.drawdown,
                    "timestamp": event.timestamp,
                })
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_kill_switch: Optional[KillSwitchEngine] = None


def get_kill_switch() -> KillSwitchEngine:
    """Get singleton instance."""
    global _kill_switch
    if _kill_switch is None:
        _kill_switch = KillSwitchEngine()
    return _kill_switch
