"""
Strategy Switch Service (STR3)
==============================

Main service for Strategy Switching & Policy Logic.

Integrates:
- Policy Engine
- Scheduler
- Profile Service (STR1)
- Config Service (STR2)

API:
- manual_switch(): Explicit admin switch
- scheduled_switch(): Time-based switch
- evaluate_and_switch(): Rule-based auto switch
- get_active_profile(): Current state
- get_switch_history(): Event audit trail
"""

import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from copy import deepcopy

from .switch_types import (
    SwitchPolicy,
    SwitchContext,
    SwitchEvent,
    SwitchDecision,
    ActiveProfileState,
    SwitchTriggerType,
    PolicyStatus
)
from .switch_policy_registry import (
    get_policy,
    get_all_policies,
    get_enabled_policies,
    enable_policy,
    disable_policy,
    register_policy,
    get_policy_summary
)
from .switch_policy_engine import switch_policy_engine
from .switch_scheduler import switch_scheduler


class StrategySwitchService:
    """
    Main Strategy Switch Service.
    
    Coordinates all switching logic:
    - Manual switches (admin control)
    - Scheduled switches (time-based)
    - Rule-based switches (condition-based)
    
    Integrates with STR1 (profiles) and STR2 (configs).
    """
    
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
        
        # Active profile state
        self._active_state = ActiveProfileState(
            profile_mode="BALANCED",
            activated_by="system",
            activation_reason="System initialization"
        )
        
        # Switch event history
        self._switch_history: List[SwitchEvent] = []
        
        # Change listeners
        self._listeners: List[callable] = []
        
        # Start scheduler with our switch callback
        switch_scheduler.start(self._execute_switch)
        
        self._initialized = True
        print(f"[StrategySwitchService] Initialized with {self._active_state.profile_mode} profile")
    
    # ===========================================
    # Manual Switch (Priority 1)
    # ===========================================
    
    def manual_switch(
        self,
        target_profile: str,
        reason: str = "",
        initiated_by: str = "admin"
    ) -> Dict[str, Any]:
        """
        Manually switch to a target profile.
        
        This is the highest priority switch type.
        
        Args:
            target_profile: CONSERVATIVE, BALANCED, or AGGRESSIVE
            reason: Reason for switch
            initiated_by: Who initiated (admin username)
        
        Returns:
            Switch result
        """
        # Validate target
        valid_profiles = ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]
        target = target_profile.upper()
        
        if target not in valid_profiles:
            return {
                "success": False,
                "error": f"Invalid profile: {target_profile}. Valid: {valid_profiles}"
            }
        
        # Check if already on target
        if self._active_state.profile_mode == target:
            return {
                "success": True,
                "message": f"Already on {target} profile",
                "active_state": self._active_state.to_dict()
            }
        
        # Execute switch
        from_profile = self._active_state.profile_mode
        
        result = self._execute_switch(
            target_profile=target,
            reason=reason or f"Manual switch by {initiated_by}",
            policy_id="policy_manual_override",
            trigger_type=SwitchTriggerType.MANUAL,
            initiated_by=initiated_by
        )
        
        return result
    
    # ===========================================
    # Scheduled Switch
    # ===========================================
    
    def scheduled_switch(
        self,
        target_profile: str,
        reason: str = "",
        policy_id: str = ""
    ) -> Dict[str, Any]:
        """
        Execute a scheduled switch.
        
        Called by the scheduler when a schedule is active.
        """
        return self._execute_switch(
            target_profile=target_profile,
            reason=reason,
            policy_id=policy_id,
            trigger_type=SwitchTriggerType.SCHEDULE,
            initiated_by="scheduler"
        )
    
    # ===========================================
    # Rule-Based Switch
    # ===========================================
    
    def evaluate_and_switch(
        self,
        context: Optional[SwitchContext] = None,
        portfolio_metrics: Optional[Dict[str, float]] = None,
        market_metrics: Optional[Dict[str, Any]] = None,
        activity_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate all policies and switch if needed.
        
        Args:
            context: Pre-built SwitchContext, or build from metrics
            portfolio_metrics: Portfolio metrics for context building
            market_metrics: Market metrics for context building
            activity_metrics: Activity metrics for context building
        
        Returns:
            Evaluation result with switch decision
        """
        # Build context if not provided
        if context is None:
            context = switch_policy_engine.build_context(
                current_profile=self._active_state.profile_mode,
                current_config_id=self._active_state.config_id,
                portfolio_metrics=portfolio_metrics,
                market_metrics=market_metrics,
                activity_metrics=activity_metrics
            )
        
        # Evaluate policies
        decision = switch_policy_engine.evaluate(context)
        
        result = {
            "evaluated": True,
            "context": context.to_dict(),
            "decision": decision.to_dict()
        }
        
        # Execute switch if needed
        if decision.should_switch:
            # Check if already on target
            if self._active_state.profile_mode == decision.target_profile:
                result["switch_executed"] = False
                result["reason"] = f"Already on {decision.target_profile}"
            else:
                switch_result = self._execute_switch(
                    target_profile=decision.target_profile,
                    reason=decision.reason,
                    policy_id=decision.triggered_by_policy_id,
                    trigger_type=decision.trigger_type,
                    initiated_by=f"policy:{decision.triggered_by_policy_name}"
                )
                result["switch_result"] = switch_result
                result["switch_executed"] = switch_result.get("success", False)
                
                # Schedule auto-revert if policy has it enabled
                policy = get_policy(decision.triggered_by_policy_id)
                if policy and policy.auto_revert and policy.revert_delay_minutes > 0:
                    revert_at = datetime.now(timezone.utc) + timedelta(minutes=policy.revert_delay_minutes)
                    task_id = switch_scheduler.schedule_revert(
                        revert_at=revert_at,
                        target_profile=policy.revert_profile,
                        reason=f"Auto-revert from {policy.name}"
                    )
                    result["scheduled_revert"] = {
                        "task_id": task_id,
                        "revert_at": revert_at.isoformat(),
                        "revert_to": policy.revert_profile
                    }
        else:
            result["switch_executed"] = False
        
        return result
    
    # ===========================================
    # Core Switch Execution
    # ===========================================
    
    def _execute_switch(
        self,
        target_profile: str,
        reason: str,
        policy_id: str,
        trigger_type: SwitchTriggerType = SwitchTriggerType.MANUAL,
        initiated_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Execute the actual profile switch.
        
        This is the central switch execution point.
        """
        with self._lock:
            from_profile = self._active_state.profile_mode
            from_config_id = self._active_state.config_id
            
            # Create switch event
            event = SwitchEvent(
                from_profile=from_profile,
                to_profile=target_profile,
                from_config_id=from_config_id,
                trigger_type=trigger_type,
                triggered_by_policy_id=policy_id,
                reason=reason,
                initiated_by=initiated_by,
                context_snapshot={
                    "from_profile": from_profile,
                    "to_profile": target_profile
                }
            )
            
            try:
                # Update active state
                self._active_state = ActiveProfileState(
                    profile_mode=target_profile,
                    activated_at=datetime.now(timezone.utc),
                    activated_by=initiated_by,
                    activation_reason=reason,
                    activation_trigger_type=trigger_type,
                    activated_by_policy_id=policy_id
                )
                
                event.success = True
                
                # Log event
                self._switch_history.append(event)
                if len(self._switch_history) > 1000:
                    self._switch_history = self._switch_history[-1000:]
                
                # Notify listeners
                self._notify_listeners(event)
                
                print(f"[StrategySwitchService] Switched {from_profile} -> {target_profile} ({reason})")
                
                return {
                    "success": True,
                    "message": f"Switched to {target_profile}",
                    "from_profile": from_profile,
                    "to_profile": target_profile,
                    "event": event.to_dict(),
                    "active_state": self._active_state.to_dict()
                }
                
            except Exception as e:
                event.success = False
                event.error_message = str(e)
                self._switch_history.append(event)
                
                print(f"[StrategySwitchService] Switch failed: {e}")
                
                return {
                    "success": False,
                    "error": str(e),
                    "event": event.to_dict()
                }
    
    # ===========================================
    # Active State
    # ===========================================
    
    def get_active_state(self) -> ActiveProfileState:
        """Get current active profile state"""
        return self._active_state
    
    def get_active_profile(self) -> str:
        """Get active profile mode"""
        return self._active_state.profile_mode
    
    # ===========================================
    # Policy Management
    # ===========================================
    
    def get_policies(self) -> List[Dict[str, Any]]:
        """Get all policies"""
        return [p.to_dict() for p in get_all_policies()]
    
    def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get specific policy"""
        policy = get_policy(policy_id)
        return policy.to_dict() if policy else None
    
    def enable_policy(self, policy_id: str) -> bool:
        """Enable a policy"""
        return enable_policy(policy_id)
    
    def disable_policy(self, policy_id: str) -> bool:
        """Disable a policy"""
        return disable_policy(policy_id)
    
    def create_policy(
        self,
        name: str,
        trigger_type: str,
        target_profile: str,
        conditions: List[Dict[str, Any]] = None,
        schedule: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a custom policy.
        
        Args:
            name: Policy name
            trigger_type: MANUAL, SCHEDULE, or RULE
            target_profile: Target profile mode
            conditions: List of condition dicts (for RULE type)
            schedule: Schedule config (for SCHEDULE type)
        """
        from .switch_types import PolicyCondition, ScheduleConfig, ConditionOperator
        
        try:
            # Parse trigger type
            ttype = SwitchTriggerType[trigger_type.upper()]
            
            # Parse conditions
            parsed_conditions = []
            if conditions:
                for c in conditions:
                    op = ConditionOperator[c.get("operator", ">=").replace(">", "GREATER").replace("<", "LESS").replace("=", "_EQUAL").replace("==", "EQUAL")]
                    parsed_conditions.append(PolicyCondition(
                        field=c.get("field", ""),
                        operator=op,
                        value=c.get("value"),
                        description=c.get("description", "")
                    ))
            
            # Parse schedule
            parsed_schedule = None
            if schedule:
                parsed_schedule = ScheduleConfig(
                    days=schedule.get("days", []),
                    start_time=schedule.get("start_time", "00:00"),
                    end_time=schedule.get("end_time", "23:59"),
                    timezone=schedule.get("timezone", "UTC")
                )
            
            # Create policy
            policy = SwitchPolicy(
                name=name,
                trigger_type=ttype,
                target_profile=target_profile.upper(),
                conditions=parsed_conditions,
                schedule=parsed_schedule,
                status=PolicyStatus.ENABLED,
                created_by=kwargs.get("created_by", "admin"),
                **{k: v for k, v in kwargs.items() if hasattr(SwitchPolicy, k)}
            )
            
            if register_policy(policy):
                return {
                    "success": True,
                    "policy": policy.to_dict()
                }
            else:
                return {
                    "success": False,
                    "error": f"Policy with name '{name}' already exists"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    # ===========================================
    # Switch History
    # ===========================================
    
    def get_switch_history(self, limit: int = 50) -> List[SwitchEvent]:
        """Get switch event history"""
        return list(reversed(self._switch_history[-limit:]))
    
    def get_switch_history_by_type(
        self, 
        trigger_type: str, 
        limit: int = 50
    ) -> List[SwitchEvent]:
        """Get switch history filtered by trigger type"""
        try:
            ttype = SwitchTriggerType[trigger_type.upper()]
            filtered = [e for e in self._switch_history if e.trigger_type == ttype]
            return list(reversed(filtered[-limit:]))
        except KeyError:
            return []
    
    # ===========================================
    # Listeners
    # ===========================================
    
    def add_listener(self, callback: callable) -> None:
        """Add listener for switch events"""
        self._listeners.append(callback)
    
    def _notify_listeners(self, event: SwitchEvent) -> None:
        """Notify all listeners"""
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                print(f"[StrategySwitchService] Listener error: {e}")
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        policy_summary = get_policy_summary()
        scheduler_health = switch_scheduler.get_health()
        engine_health = switch_policy_engine.get_health()
        
        return {
            "module": "Strategy Switch Service",
            "phase": "STR3",
            "status": "healthy",
            "active_profile": self._active_state.profile_mode,
            "total_switches": len(self._switch_history),
            "services": {
                "switch_service": {"status": "healthy"},
                "policy_engine": engine_health,
                "scheduler": scheduler_health
            },
            "policies": policy_summary
        }


# Global singleton
strategy_switch_service = StrategySwitchService()
