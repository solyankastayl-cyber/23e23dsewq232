"""
Trading Pause Service (TR5)
===========================

Handles trading pause/resume from admin panel.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .control_types import (
    StrategyControlEvent,
    ControlAction,
    ActorType
)
from .control_repository import control_repository


class TradingPauseService:
    """
    Manages trading pause/resume.
    
    Pause:
    - Blocks new signal processing
    - Allows existing orders to complete
    - Does NOT cancel open orders
    - Does NOT close positions
    
    Resume:
    - Restores normal signal processing
    """
    
    def __init__(self):
        self._paused = False
        self._paused_at: Optional[datetime] = None
        self._paused_by: str = ""
        self._pause_reason: str = ""
        
        print("[TradingPauseService] Initialized")
    
    def pause(
        self,
        reason: str = "",
        actor: str = "admin",
        actor_type: ActorType = ActorType.ADMIN
    ) -> Dict[str, Any]:
        """
        Pause trading.
        
        Args:
            reason: Reason for pause
            actor: Who initiated
            actor_type: Type of actor
        
        Returns:
            Pause result
        """
        if self._paused:
            return {
                "success": True,
                "message": "Trading already paused",
                "paused": True,
                "paused_at": self._paused_at.isoformat() if self._paused_at else None,
                "changed": False
            }
        
        # Create event
        event = StrategyControlEvent(
            action=ControlAction.TRADING_PAUSE,
            actor=actor,
            actor_type=actor_type,
            reason=reason or "Manual trading pause",
            details={"action": "pause"},
            previous_state={"paused": False},
            new_state={"paused": True}
        )
        
        # Execute pause
        self._paused = True
        self._paused_at = datetime.now(timezone.utc)
        self._paused_by = actor
        self._pause_reason = reason
        
        event.success = True
        
        # Save event
        control_repository.save_event(event)
        
        print(f"[TradingPauseService] Trading PAUSED by {actor}: {reason}")
        
        return {
            "success": True,
            "message": "Trading paused",
            "paused": True,
            "paused_at": self._paused_at.isoformat(),
            "paused_by": self._paused_by,
            "reason": self._pause_reason,
            "event_id": event.event_id,
            "changed": True
        }
    
    def resume(
        self,
        reason: str = "",
        actor: str = "admin",
        actor_type: ActorType = ActorType.ADMIN
    ) -> Dict[str, Any]:
        """
        Resume trading.
        
        Args:
            reason: Reason for resume
            actor: Who initiated
            actor_type: Type of actor
        
        Returns:
            Resume result
        """
        if not self._paused:
            return {
                "success": True,
                "message": "Trading not paused",
                "paused": False,
                "changed": False
            }
        
        # Calculate pause duration
        pause_duration = None
        if self._paused_at:
            pause_duration = (datetime.now(timezone.utc) - self._paused_at).total_seconds()
        
        # Create event
        event = StrategyControlEvent(
            action=ControlAction.TRADING_RESUME,
            actor=actor,
            actor_type=actor_type,
            reason=reason or "Manual trading resume",
            details={
                "action": "resume",
                "pause_duration_seconds": pause_duration
            },
            previous_state={"paused": True, "paused_at": self._paused_at.isoformat() if self._paused_at else None},
            new_state={"paused": False}
        )
        
        # Execute resume
        self._paused = False
        self._paused_at = None
        self._paused_by = ""
        self._pause_reason = ""
        
        event.success = True
        
        # Save event
        control_repository.save_event(event)
        
        print(f"[TradingPauseService] Trading RESUMED by {actor}: {reason}")
        
        return {
            "success": True,
            "message": "Trading resumed",
            "paused": False,
            "pause_duration_seconds": pause_duration,
            "event_id": event.event_id,
            "changed": True
        }
    
    def is_paused(self) -> bool:
        """Check if trading is paused"""
        return self._paused
    
    def get_pause_state(self) -> Dict[str, Any]:
        """Get pause state"""
        return {
            "paused": self._paused,
            "paused_at": self._paused_at.isoformat() if self._paused_at else None,
            "paused_by": self._paused_by,
            "reason": self._pause_reason
        }
    
    def set_paused(self, paused: bool):
        """Internal method to set pause state without logging"""
        self._paused = paused
        if paused:
            self._paused_at = datetime.now(timezone.utc)
        else:
            self._paused_at = None


# Global singleton
trading_pause_service = TradingPauseService()
