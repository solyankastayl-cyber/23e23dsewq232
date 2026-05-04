"""
Strategy Control Service (TR5)
==============================

Main service for Strategy Control module.

Coordinates:
- Profile switching
- Config switching
- Trading pause/resume
- Kill switch (soft/hard)
- Override mode

Pipeline position:
    Signals → Strategy Runtime → STR3 Switching → TR5 Control → Execution
    
TR5 can override any automatic behavior.
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from copy import deepcopy

from .control_types import (
    ControlMode,
    KillSwitchMode,
    StrategyControlState,
    StrategyControlEvent,
    ControlAction,
    ActorType,
    KillSwitchConfig,
    OverrideSettings
)
from .control_repository import control_repository
from .profile_switch_service import profile_switch_service
from .config_switch_service import config_switch_service
from .trading_pause_service import trading_pause_service
from .kill_switch_service import kill_switch_service
from .override_service import override_service


class StrategyControlService:
    """
    Main Strategy Control Service.
    
    Provides unified control interface for:
    - Profile management
    - Config management  
    - Trading pause/resume
    - Kill switch (soft/hard)
    - Override mode
    
    State hierarchy:
        NORMAL → PAUSED → SOFT_KILL → HARD_KILL
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
        
        # Initialize state
        self._state = StrategyControlState()
        
        # Sub-services
        self._profile_service = profile_switch_service
        self._config_service = config_switch_service
        self._pause_service = trading_pause_service
        self._kill_switch_service = kill_switch_service
        self._override_service = override_service
        
        self._initialized = True
        print("[StrategyControlService] Initialized (TR5)")
    
    # ===========================================
    # State Management
    # ===========================================
    
    def get_state(self) -> StrategyControlState:
        """Get current control state"""
        self._sync_state()
        return self._state
    
    def _sync_state(self):
        """Sync state from sub-services"""
        # Profile & Config
        self._state.active_profile = self._profile_service.get_current_profile()
        self._state.active_config = self._config_service.get_current_config()
        
        # Pause
        pause_state = self._pause_service.get_pause_state()
        self._state.paused = pause_state["paused"]
        self._state.paused_at = datetime.fromisoformat(pause_state["paused_at"]) if pause_state["paused_at"] else None
        
        # Kill switch
        ks_state = self._kill_switch_service.get_state()
        self._state.kill_switch_active = ks_state["active"]
        self._state.kill_switch_mode = KillSwitchMode(ks_state["mode"]) if ks_state["mode"] else None
        self._state.kill_switch_at = datetime.fromisoformat(ks_state["activated_at"]) if ks_state["activated_at"] else None
        if ks_state["config"]:
            self._state.kill_switch_config = KillSwitchConfig(
                mode=KillSwitchMode(ks_state["config"]["mode"]),
                cancel_open_orders=ks_state["config"]["cancel_open_orders"],
                block_new_entries=ks_state["config"]["block_new_entries"],
                allow_reductions=ks_state["config"]["allow_reductions"],
                force_close_positions=ks_state["config"]["force_close_positions"]
            )
        else:
            self._state.kill_switch_config = None
        
        # Override
        override_state = self._override_service.get_state()
        self._state.override_mode = override_state["enabled"]
        self._state.override_at = datetime.fromisoformat(override_state["enabled_at"]) if override_state["enabled_at"] else None
        
        # Determine control mode
        self._state.mode = self._determine_mode()
        
        # Trading enabled
        self._state.trading_enabled = not (
            self._state.paused or 
            self._state.kill_switch_active
        )
        
        # Update timestamp
        self._state.updated_at = datetime.now(timezone.utc)
    
    def _determine_mode(self) -> ControlMode:
        """Determine current control mode based on hierarchy"""
        if self._state.kill_switch_active:
            if self._state.kill_switch_mode == KillSwitchMode.HARD:
                return ControlMode.HARD_KILL
            return ControlMode.SOFT_KILL
        
        if self._state.paused:
            return ControlMode.PAUSED
        
        return ControlMode.NORMAL
    
    # ===========================================
    # Profile Control
    # ===========================================
    
    def switch_profile(
        self,
        profile: str,
        reason: str = "",
        actor: str = "admin"
    ) -> Dict[str, Any]:
        """Switch strategy profile"""
        result = self._profile_service.switch_profile(
            target_profile=profile,
            reason=reason,
            actor=actor
        )
        
        if result.get("success") and result.get("changed"):
            self._state.active_profile = profile.upper()
            self._state.last_actor = actor
            self._state.last_action = "PROFILE_SWITCH"
            self._state.last_reason = reason
            self._save_state_snapshot()
        
        return result
    
    def get_profile(self) -> Dict[str, Any]:
        """Get current profile info"""
        return self._profile_service.get_profile_info()
    
    # ===========================================
    # Config Control
    # ===========================================
    
    def switch_config(
        self,
        config_id: str,
        reason: str = "",
        actor: str = "admin"
    ) -> Dict[str, Any]:
        """Switch strategy config"""
        result = self._config_service.switch_config(
            config_id=config_id,
            reason=reason,
            actor=actor
        )
        
        if result.get("success") and result.get("changed"):
            self._state.active_config = config_id
            self._state.last_actor = actor
            self._state.last_action = "CONFIG_SWITCH"
            self._state.last_reason = reason
            self._save_state_snapshot()
        
        return result
    
    def get_config(self) -> Dict[str, Any]:
        """Get current config info"""
        return self._config_service.get_config_info()
    
    # ===========================================
    # Trading Pause/Resume
    # ===========================================
    
    def pause_trading(
        self,
        reason: str = "",
        actor: str = "admin"
    ) -> Dict[str, Any]:
        """Pause trading"""
        result = self._pause_service.pause(reason=reason, actor=actor)
        
        if result.get("success") and result.get("changed"):
            self._state.paused = True
            self._state.last_actor = actor
            self._state.last_action = "TRADING_PAUSE"
            self._state.last_reason = reason
            self._save_state_snapshot()
        
        return result
    
    def resume_trading(
        self,
        reason: str = "",
        actor: str = "admin"
    ) -> Dict[str, Any]:
        """Resume trading"""
        result = self._pause_service.resume(reason=reason, actor=actor)
        
        if result.get("success") and result.get("changed"):
            self._state.paused = False
            self._state.last_actor = actor
            self._state.last_action = "TRADING_RESUME"
            self._state.last_reason = reason
            self._save_state_snapshot()
        
        return result
    
    # ===========================================
    # Kill Switch
    # ===========================================
    
    def trigger_soft_kill(
        self,
        reason: str = "",
        actor: str = "admin"
    ) -> Dict[str, Any]:
        """Trigger SOFT kill switch"""
        result = self._kill_switch_service.trigger_soft_kill(
            reason=reason,
            actor=actor
        )
        
        if result.get("success"):
            self._state.kill_switch_active = True
            self._state.kill_switch_mode = KillSwitchMode.SOFT
            self._state.last_actor = actor
            self._state.last_action = "SOFT_KILL_SWITCH"
            self._state.last_reason = reason
            self._save_state_snapshot()
        
        return result
    
    def trigger_hard_kill(
        self,
        reason: str = "",
        actor: str = "admin",
        close_method: str = "market"
    ) -> Dict[str, Any]:
        """Trigger HARD kill switch"""
        result = self._kill_switch_service.trigger_hard_kill(
            reason=reason,
            actor=actor,
            close_method=close_method
        )
        
        if result.get("success"):
            self._state.kill_switch_active = True
            self._state.kill_switch_mode = KillSwitchMode.HARD
            self._state.last_actor = actor
            self._state.last_action = "HARD_KILL_SWITCH"
            self._state.last_reason = reason
            self._save_state_snapshot()
        
        return result
    
    def reset_kill_switch(
        self,
        reason: str = "",
        actor: str = "admin"
    ) -> Dict[str, Any]:
        """Reset kill switch"""
        result = self._kill_switch_service.reset(reason=reason, actor=actor)
        
        if result.get("success") and result.get("changed"):
            self._state.kill_switch_active = False
            self._state.kill_switch_mode = None
            self._state.last_actor = actor
            self._state.last_action = "KILL_SWITCH_RESET"
            self._state.last_reason = reason
            self._save_state_snapshot()
        
        return result
    
    def get_kill_switch_state(self) -> Dict[str, Any]:
        """Get kill switch state"""
        return self._kill_switch_service.get_state()
    
    # ===========================================
    # Override Mode
    # ===========================================
    
    def enable_override(
        self,
        reason: str = "",
        actor: str = "admin",
        settings: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """Enable override mode"""
        override_settings = None
        if settings:
            override_settings = OverrideSettings(
                manual_order_routing=settings.get("manual_order_routing", True),
                disable_auto_switching=settings.get("disable_auto_switching", True),
                disable_strategy_runtime=settings.get("disable_strategy_runtime", True)
            )
        
        result = self._override_service.enable(
            reason=reason,
            actor=actor,
            settings=override_settings
        )
        
        if result.get("success") and result.get("changed"):
            self._state.override_mode = True
            self._state.last_actor = actor
            self._state.last_action = "OVERRIDE_ENABLE"
            self._state.last_reason = reason
            self._save_state_snapshot()
        
        return result
    
    def disable_override(
        self,
        reason: str = "",
        actor: str = "admin"
    ) -> Dict[str, Any]:
        """Disable override mode"""
        result = self._override_service.disable(reason=reason, actor=actor)
        
        if result.get("success") and result.get("changed"):
            self._state.override_mode = False
            self._state.last_actor = actor
            self._state.last_action = "OVERRIDE_DISABLE"
            self._state.last_reason = reason
            self._save_state_snapshot()
        
        return result
    
    def get_override_state(self) -> Dict[str, Any]:
        """Get override state"""
        return self._override_service.get_state()
    
    # ===========================================
    # Event History
    # ===========================================
    
    def get_events(
        self,
        limit: int = 100,
        action: Optional[str] = None
    ) -> List[StrategyControlEvent]:
        """Get control events"""
        action_enum = None
        if action:
            try:
                action_enum = ControlAction(action)
            except ValueError:
                pass
        
        return control_repository.get_events(limit=limit, action=action_enum)
    
    def get_kill_switch_events(self, limit: int = 20) -> List[StrategyControlEvent]:
        """Get recent kill switch events"""
        return control_repository.get_recent_kill_switch_events(limit=limit)
    
    # ===========================================
    # Dashboard
    # ===========================================
    
    def get_dashboard(self) -> Dict[str, Any]:
        """Get dashboard data"""
        self._sync_state()
        
        return {
            "state": self._state.to_dashboard_dict(),
            "profile": self._profile_service.get_profile_info(),
            "config": self._config_service.get_config_info(),
            "pause": self._pause_service.get_pause_state(),
            "kill_switch": self._kill_switch_service.get_state(),
            "override": self._override_service.get_state(),
            "mode_hierarchy": ["NORMAL", "PAUSED", "SOFT_KILL", "HARD_KILL"],
            "current_mode": self._state.mode.value,
            "trading_enabled": self._state.trading_enabled
        }
    
    # ===========================================
    # Validation Helpers
    # ===========================================
    
    def can_trade(self) -> tuple:
        """
        Check if trading is allowed.
        
        Returns (can_trade, reason)
        """
        if self._pause_service.is_paused():
            return False, "Trading is paused"
        
        can_place, reason = self._kill_switch_service.can_place_order()
        if not can_place:
            return False, reason
        
        return True, ""
    
    def can_enter_position(self) -> tuple:
        """
        Check if new position entries are allowed.
        
        Returns (can_enter, reason)
        """
        can_trade, reason = self.can_trade()
        if not can_trade:
            return False, reason
        
        if self._override_service.is_strategy_runtime_disabled():
            return False, "Override mode: strategy runtime disabled"
        
        return True, ""
    
    def is_auto_switching_allowed(self) -> bool:
        """Check if auto profile switching is allowed"""
        return not self._override_service.is_auto_switching_disabled()
    
    # ===========================================
    # State Persistence
    # ===========================================
    
    def _save_state_snapshot(self):
        """Save state snapshot for audit"""
        self._sync_state()
        control_repository.save_state(self._state.to_dict())
    
    def get_state_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get state history"""
        return control_repository.get_state_history(limit=limit)
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        self._sync_state()
        repo_stats = control_repository.get_stats()
        
        return {
            "module": "Strategy Control Service",
            "phase": "TR5",
            "status": "healthy",
            "current_mode": self._state.mode.value,
            "trading_enabled": self._state.trading_enabled,
            "active_profile": self._state.active_profile,
            "services": {
                "profile_switch": {"status": "healthy", "profile": self._profile_service.get_current_profile()},
                "config_switch": {"status": "healthy", "config": self._config_service.get_current_config()},
                "trading_pause": {"status": "healthy", "paused": self._pause_service.is_paused()},
                "kill_switch": {"status": "healthy", "active": self._kill_switch_service.is_active()},
                "override": {"status": "healthy", "enabled": self._override_service.is_enabled()}
            },
            "repository": repo_stats
        }


# Global singleton
strategy_control_service = StrategyControlService()
