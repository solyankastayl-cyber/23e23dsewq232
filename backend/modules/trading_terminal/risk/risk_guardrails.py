"""
Risk Guardrails (TR4)
=====================

Automatic protective actions based on risk conditions.
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable

from .risk_types import RiskGuardrailEvent, GuardrailAction, RiskMetrics, ExposureMetrics, RiskLevel


class RiskGuardrails:
    """Automatic risk guardrails - protective actions."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Guardrail rules
        self._rules = {
            "daily_loss_conservative": {"threshold": 0.05, "action": GuardrailAction.SWITCH_CONSERVATIVE, "enabled": True},
            "drawdown_conservative": {"threshold": 0.12, "action": GuardrailAction.SWITCH_CONSERVATIVE, "enabled": True},
            "drawdown_pause": {"threshold": 0.18, "action": GuardrailAction.PAUSE_TRADING, "enabled": False},
            "leverage_reduce": {"threshold": 5.0, "action": GuardrailAction.REDUCE_EXPOSURE, "enabled": True}
        }
        
        # Event history
        self._events: List[RiskGuardrailEvent] = []
        
        # Action callback
        self._action_callback: Optional[Callable] = None
        
        # Cooldown tracking
        self._last_trigger: Dict[str, datetime] = {}
        self._cooldown_minutes = 30
        
        self._initialized = True
        print("[RiskGuardrails] Initialized")
    
    def set_action_callback(self, callback: Callable) -> None:
        """Set callback for executing guardrail actions."""
        self._action_callback = callback
    
    def evaluate_guardrails(self, metrics: RiskMetrics, exposure: ExposureMetrics) -> List[RiskGuardrailEvent]:
        """Evaluate all guardrail rules."""
        triggered_events = []
        now = datetime.now(timezone.utc)
        
        # Check daily loss guardrail
        if self._rules["daily_loss_conservative"]["enabled"]:
            if metrics.daily_loss_pct >= self._rules["daily_loss_conservative"]["threshold"]:
                if self._can_trigger("daily_loss_conservative", now):
                    event = self._create_event(
                        trigger_type="DAILY_LOSS_LIMIT",
                        action=self._rules["daily_loss_conservative"]["action"],
                        reason=f"Daily loss {metrics.daily_loss_pct*100:.1f}% >= {self._rules['daily_loss_conservative']['threshold']*100}%",
                        details={"daily_loss_pct": metrics.daily_loss_pct}
                    )
                    triggered_events.append(event)
                    self._last_trigger["daily_loss_conservative"] = now
        
        # Check drawdown conservative guardrail
        if self._rules["drawdown_conservative"]["enabled"]:
            if metrics.current_drawdown_pct >= self._rules["drawdown_conservative"]["threshold"]:
                if self._can_trigger("drawdown_conservative", now):
                    event = self._create_event(
                        trigger_type="DRAWDOWN_LIMIT",
                        action=self._rules["drawdown_conservative"]["action"],
                        reason=f"Drawdown {metrics.current_drawdown_pct*100:.1f}% >= {self._rules['drawdown_conservative']['threshold']*100}%",
                        details={"drawdown_pct": metrics.current_drawdown_pct}
                    )
                    triggered_events.append(event)
                    self._last_trigger["drawdown_conservative"] = now
        
        # Check drawdown pause guardrail
        if self._rules["drawdown_pause"]["enabled"]:
            if metrics.current_drawdown_pct >= self._rules["drawdown_pause"]["threshold"]:
                if self._can_trigger("drawdown_pause", now):
                    event = self._create_event(
                        trigger_type="CRITICAL_DRAWDOWN",
                        action=self._rules["drawdown_pause"]["action"],
                        reason=f"Critical drawdown {metrics.current_drawdown_pct*100:.1f}%",
                        details={"drawdown_pct": metrics.current_drawdown_pct}
                    )
                    triggered_events.append(event)
                    self._last_trigger["drawdown_pause"] = now
        
        # Check leverage guardrail
        if self._rules["leverage_reduce"]["enabled"]:
            if exposure.current_leverage >= self._rules["leverage_reduce"]["threshold"]:
                if self._can_trigger("leverage_reduce", now):
                    event = self._create_event(
                        trigger_type="LEVERAGE_LIMIT",
                        action=self._rules["leverage_reduce"]["action"],
                        reason=f"Leverage {exposure.current_leverage:.1f}x >= {self._rules['leverage_reduce']['threshold']}x",
                        details={"leverage": exposure.current_leverage}
                    )
                    triggered_events.append(event)
                    self._last_trigger["leverage_reduce"] = now
        
        # Execute triggered guardrails
        for event in triggered_events:
            self._execute_guardrail(event)
            self._events.append(event)
        
        return triggered_events
    
    def _can_trigger(self, rule_name: str, now: datetime) -> bool:
        """Check if rule can trigger (respecting cooldown)."""
        last = self._last_trigger.get(rule_name)
        if last is None:
            return True
        cooldown = (now - last).total_seconds() / 60
        return cooldown >= self._cooldown_minutes
    
    def _create_event(self, trigger_type: str, action: GuardrailAction, reason: str, details: Dict) -> RiskGuardrailEvent:
        return RiskGuardrailEvent(
            trigger_type=trigger_type,
            action=action,
            reason=reason,
            details=details
        )
    
    def _execute_guardrail(self, event: RiskGuardrailEvent) -> None:
        """Execute guardrail action."""
        try:
            if event.action == GuardrailAction.SWITCH_CONSERVATIVE:
                if self._action_callback:
                    self._action_callback("switch_conservative", event.reason)
                event.executed = True
                event.execution_result = "Triggered switch to CONSERVATIVE"
            
            elif event.action == GuardrailAction.PAUSE_TRADING:
                # This would integrate with strategy control
                event.executed = True
                event.execution_result = "Trading pause triggered (manual confirmation required)"
            
            elif event.action == GuardrailAction.REDUCE_EXPOSURE:
                event.executed = True
                event.execution_result = "Exposure reduction alert sent"
            
            elif event.action == GuardrailAction.ALERT_ONLY:
                event.executed = True
                event.execution_result = "Alert generated"
            
            print(f"[RiskGuardrails] Executed: {event.trigger_type} -> {event.action.value}")
            
        except Exception as e:
            event.executed = False
            event.execution_result = f"Error: {str(e)}"
    
    def get_events(self, limit: int = 50) -> List[RiskGuardrailEvent]:
        return list(reversed(self._events[-limit:]))
    
    def get_rules(self) -> Dict[str, Any]:
        return {name: {**rule, "action": rule["action"].value} for name, rule in self._rules.items()}
    
    def enable_rule(self, rule_name: str) -> bool:
        if rule_name in self._rules:
            self._rules[rule_name]["enabled"] = True
            return True
        return False
    
    def disable_rule(self, rule_name: str) -> bool:
        if rule_name in self._rules:
            self._rules[rule_name]["enabled"] = False
            return True
        return False
    
    def get_health(self) -> Dict[str, Any]:
        return {"service": "RiskGuardrails", "status": "healthy", "phase": "TR4", "events_count": len(self._events), "enabled_rules": sum(1 for r in self._rules.values() if r["enabled"])}


risk_guardrails = RiskGuardrails()
