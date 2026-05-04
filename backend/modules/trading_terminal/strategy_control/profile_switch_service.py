"""
Profile Switch Service (TR5)
============================

Handles manual profile switching from admin panel.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .control_types import (
    StrategyControlEvent,
    ControlAction,
    ActorType,
    ProfileSwitchRequest
)
from .control_repository import control_repository


class ProfileSwitchService:
    """
    Manages profile switching.
    
    Allows admin to manually switch between:
    - CONSERVATIVE
    - BALANCED
    - AGGRESSIVE
    """
    
    VALID_PROFILES = ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]
    
    def __init__(self):
        self._current_profile = "BALANCED"
        print("[ProfileSwitchService] Initialized")
    
    def switch_profile(
        self,
        target_profile: str,
        reason: str = "",
        actor: str = "admin",
        actor_type: ActorType = ActorType.ADMIN
    ) -> Dict[str, Any]:
        """
        Switch to target profile.
        
        Args:
            target_profile: CONSERVATIVE, BALANCED, or AGGRESSIVE
            reason: Reason for switch
            actor: Who initiated
            actor_type: Type of actor
        
        Returns:
            Switch result
        """
        target = target_profile.upper()
        
        # Validate
        if target not in self.VALID_PROFILES:
            return {
                "success": False,
                "error": f"Invalid profile: {target_profile}. Valid: {self.VALID_PROFILES}"
            }
        
        # Check if already on target
        if self._current_profile == target:
            return {
                "success": True,
                "message": f"Already on {target} profile",
                "profile": target,
                "changed": False
            }
        
        # Create event
        previous_profile = self._current_profile
        event = StrategyControlEvent(
            action=ControlAction.PROFILE_SWITCH,
            actor=actor,
            actor_type=actor_type,
            reason=reason or f"Manual switch to {target}",
            details={
                "from_profile": previous_profile,
                "to_profile": target
            },
            previous_state={"profile": previous_profile},
            new_state={"profile": target}
        )
        
        # Execute switch
        self._current_profile = target
        event.success = True
        
        # Save event
        control_repository.save_event(event)
        
        print(f"[ProfileSwitchService] Switched {previous_profile} -> {target} ({reason})")
        
        return {
            "success": True,
            "message": f"Switched to {target}",
            "from_profile": previous_profile,
            "to_profile": target,
            "event_id": event.event_id,
            "changed": True
        }
    
    def get_current_profile(self) -> str:
        """Get current active profile"""
        return self._current_profile
    
    def get_profile_info(self) -> Dict[str, Any]:
        """Get profile information"""
        return {
            "current": self._current_profile,
            "available": self.VALID_PROFILES,
            "descriptions": {
                "CONSERVATIVE": "Low risk, reduced position sizing, tight stops",
                "BALANCED": "Moderate risk, standard parameters",
                "AGGRESSIVE": "Higher risk, larger positions, wider stops"
            }
        }
    
    def set_profile(self, profile: str):
        """Internal method to set profile without logging"""
        if profile.upper() in self.VALID_PROFILES:
            self._current_profile = profile.upper()


# Global singleton
profile_switch_service = ProfileSwitchService()
