"""
Override Service (TR5)
======================

Manual override mode for full manual control.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .control_types import (
    StrategyControlEvent,
    ControlAction,
    ActorType,
    OverrideSettings
)
from .control_repository import control_repository


class OverrideService:
    """
    Manages manual override mode.
    
    Override mode allows:
    - Manual order routing
    - Disable auto profile switching
    - Disable strategy runtime
    
    Use when operator needs full manual control.
    """
    
    def __init__(self):
        self._enabled = False
        self._enabled_at: Optional[datetime] = None
        self._enabled_by: str = ""
        self._settings: Optional[OverrideSettings] = None
        
        print("[OverrideService] Initialized")
    
    def enable(
        self,
        reason: str = "",
        actor: str = "admin",
        actor_type: ActorType = ActorType.ADMIN,
        settings: Optional[OverrideSettings] = None
    ) -> Dict[str, Any]:
        """
        Enable override mode.
        
        Args:
            reason: Reason for enabling
            actor: Who initiated
            actor_type: Type of actor
            settings: Override settings
        
        Returns:
            Result
        """
        if self._enabled:
            return {
                "success": True,
                "message": "Override mode already enabled",
                "enabled": True,
                "changed": False
            }
        
        # Use default settings if none provided
        if settings is None:
            settings = OverrideSettings()
        
        # Create event
        event = StrategyControlEvent(
            action=ControlAction.OVERRIDE_ENABLE,
            actor=actor,
            actor_type=actor_type,
            reason=reason or "Manual override enabled",
            details={"settings": settings.to_dict()},
            previous_state={"override_enabled": False},
            new_state={"override_enabled": True, "settings": settings.to_dict()}
        )
        
        # Enable
        self._enabled = True
        self._enabled_at = datetime.now(timezone.utc)
        self._enabled_by = actor
        self._settings = settings
        
        event.success = True
        
        # Save event
        control_repository.save_event(event)
        
        print(f"[OverrideService] Override mode ENABLED by {actor}: {reason}")
        
        return {
            "success": True,
            "message": "Override mode enabled",
            "enabled": True,
            "enabled_at": self._enabled_at.isoformat(),
            "settings": settings.to_dict(),
            "event_id": event.event_id,
            "changed": True
        }
    
    def disable(
        self,
        reason: str = "",
        actor: str = "admin",
        actor_type: ActorType = ActorType.ADMIN
    ) -> Dict[str, Any]:
        """
        Disable override mode.
        
        Args:
            reason: Reason for disabling
            actor: Who initiated
            actor_type: Type of actor
        
        Returns:
            Result
        """
        if not self._enabled:
            return {
                "success": True,
                "message": "Override mode not enabled",
                "enabled": False,
                "changed": False
            }
        
        # Calculate duration
        duration = None
        if self._enabled_at:
            duration = (datetime.now(timezone.utc) - self._enabled_at).total_seconds()
        
        # Create event
        event = StrategyControlEvent(
            action=ControlAction.OVERRIDE_DISABLE,
            actor=actor,
            actor_type=actor_type,
            reason=reason or "Manual override disabled",
            details={
                "duration_seconds": duration,
                "previous_settings": self._settings.to_dict() if self._settings else None
            },
            previous_state={"override_enabled": True},
            new_state={"override_enabled": False}
        )
        
        # Disable
        self._enabled = False
        self._enabled_at = None
        self._enabled_by = ""
        self._settings = None
        
        event.success = True
        
        # Save event
        control_repository.save_event(event)
        
        print(f"[OverrideService] Override mode DISABLED by {actor}: {reason}")
        
        return {
            "success": True,
            "message": "Override mode disabled",
            "enabled": False,
            "duration_seconds": duration,
            "event_id": event.event_id,
            "changed": True
        }
    
    def is_enabled(self) -> bool:
        """Check if override mode is enabled"""
        return self._enabled
    
    def get_state(self) -> Dict[str, Any]:
        """Get override state"""
        return {
            "enabled": self._enabled,
            "enabled_at": self._enabled_at.isoformat() if self._enabled_at else None,
            "enabled_by": self._enabled_by,
            "settings": self._settings.to_dict() if self._settings else None
        }
    
    def get_settings(self) -> Optional[OverrideSettings]:
        """Get current override settings"""
        return self._settings
    
    def is_auto_switching_disabled(self) -> bool:
        """Check if auto switching is disabled"""
        if not self._enabled:
            return False
        if self._settings:
            return self._settings.disable_auto_switching
        return True
    
    def is_strategy_runtime_disabled(self) -> bool:
        """Check if strategy runtime is disabled"""
        if not self._enabled:
            return False
        if self._settings:
            return self._settings.disable_strategy_runtime
        return True
    
    def is_manual_routing_enabled(self) -> bool:
        """Check if manual order routing is enabled"""
        if not self._enabled:
            return False
        if self._settings:
            return self._settings.manual_order_routing
        return True


# Global singleton
override_service = OverrideService()
