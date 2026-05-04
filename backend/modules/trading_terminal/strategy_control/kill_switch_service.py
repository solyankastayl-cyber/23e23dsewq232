"""
Kill Switch Service (TR5)
=========================

Emergency stop functionality with two levels:
- SOFT: Block new entries, cancel orders, allow reductions only
- HARD: All of SOFT + force close all positions
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from .control_types import (
    StrategyControlEvent,
    ControlAction,
    ActorType,
    KillSwitchMode,
    KillSwitchConfig
)
from .control_repository import control_repository


class KillSwitchService:
    """
    Manages kill switch functionality.
    
    Two-level kill switch:
    
    SOFT Kill Switch (Level 1):
    - Stops new entries
    - Cancels open orders
    - Allows position reductions
    - Does NOT force close positions
    - Use for: bugs, strange behavior, high volatility
    
    HARD Kill Switch (Level 2):
    - Everything from SOFT
    - Force closes all positions
    - Complete emergency stop
    - Use for: key compromise, runaway execution, extreme drawdown
    """
    
    def __init__(self):
        self._active = False
        self._mode: Optional[KillSwitchMode] = None
        self._config: Optional[KillSwitchConfig] = None
        self._activated_at: Optional[datetime] = None
        self._activated_by: str = ""
        self._activation_reason: str = ""
        
        # Track actions taken
        self._orders_cancelled: int = 0
        self._positions_closed: int = 0
        
        print("[KillSwitchService] Initialized")
    
    def trigger_soft_kill(
        self,
        reason: str = "",
        actor: str = "admin",
        actor_type: ActorType = ActorType.ADMIN
    ) -> Dict[str, Any]:
        """
        Trigger SOFT kill switch.
        
        Actions:
        - Block new entries
        - Cancel open orders
        - Allow reductions only
        """
        if self._active and self._mode == KillSwitchMode.HARD:
            return {
                "success": False,
                "error": "HARD kill switch already active. Reset first.",
                "current_mode": KillSwitchMode.HARD.value
            }
        
        config = KillSwitchConfig.soft()
        return self._trigger_kill_switch(
            mode=KillSwitchMode.SOFT,
            config=config,
            reason=reason or "SOFT kill switch activated",
            actor=actor,
            actor_type=actor_type
        )
    
    def trigger_hard_kill(
        self,
        reason: str = "",
        actor: str = "admin",
        actor_type: ActorType = ActorType.ADMIN,
        close_method: str = "market"
    ) -> Dict[str, Any]:
        """
        Trigger HARD kill switch.
        
        Actions:
        - All SOFT actions
        - Force close all positions
        """
        config = KillSwitchConfig.hard()
        config.close_method = close_method
        
        return self._trigger_kill_switch(
            mode=KillSwitchMode.HARD,
            config=config,
            reason=reason or "HARD kill switch activated - EMERGENCY",
            actor=actor,
            actor_type=actor_type
        )
    
    def _trigger_kill_switch(
        self,
        mode: KillSwitchMode,
        config: KillSwitchConfig,
        reason: str,
        actor: str,
        actor_type: ActorType
    ) -> Dict[str, Any]:
        """Internal method to trigger kill switch"""
        
        previous_state = {
            "active": self._active,
            "mode": self._mode.value if self._mode else None
        }
        
        # Create event
        action = ControlAction.SOFT_KILL_SWITCH if mode == KillSwitchMode.SOFT else ControlAction.HARD_KILL_SWITCH
        event = StrategyControlEvent(
            action=action,
            actor=actor,
            actor_type=actor_type,
            reason=reason,
            details={
                "mode": mode.value,
                "config": config.to_dict()
            },
            previous_state=previous_state,
            new_state={
                "active": True,
                "mode": mode.value
            }
        )
        
        # Activate
        self._active = True
        self._mode = mode
        self._config = config
        self._activated_at = datetime.now(timezone.utc)
        self._activated_by = actor
        self._activation_reason = reason
        
        # Execute kill switch actions (mock for now)
        execution_result = self._execute_kill_switch_actions(mode, config)
        
        event.details["execution_result"] = execution_result
        event.success = True
        
        # Save event
        control_repository.save_event(event)
        
        level = "SOFT" if mode == KillSwitchMode.SOFT else "HARD"
        print(f"[KillSwitchService] {level} KILL SWITCH TRIGGERED by {actor}: {reason}")
        
        return {
            "success": True,
            "message": f"{level} kill switch activated",
            "mode": mode.value,
            "config": config.to_dict(),
            "activated_at": self._activated_at.isoformat(),
            "execution_result": execution_result,
            "event_id": event.event_id
        }
    
    def _execute_kill_switch_actions(
        self,
        mode: KillSwitchMode,
        config: KillSwitchConfig
    ) -> Dict[str, Any]:
        """Execute kill switch actions (mock implementation)"""
        result = {
            "orders_cancelled": 0,
            "positions_closed": 0,
            "errors": []
        }
        
        # Cancel open orders (mock)
        if config.cancel_open_orders:
            # In real implementation, would call order service
            result["orders_cancelled"] = 3  # Mock
            self._orders_cancelled += 3
            print("[KillSwitchService] Cancelled 3 open orders (mock)")
        
        # Force close positions (mock)
        if config.force_close_positions:
            # In real implementation, would call position service
            result["positions_closed"] = 2  # Mock
            self._positions_closed += 2
            print(f"[KillSwitchService] Closed 2 positions via {config.close_method} (mock)")
        
        return result
    
    def reset(
        self,
        reason: str = "",
        actor: str = "admin",
        actor_type: ActorType = ActorType.ADMIN
    ) -> Dict[str, Any]:
        """
        Reset kill switch.
        
        Returns system to normal state.
        """
        if not self._active:
            return {
                "success": True,
                "message": "Kill switch not active",
                "changed": False
            }
        
        # Calculate duration
        duration = None
        if self._activated_at:
            duration = (datetime.now(timezone.utc) - self._activated_at).total_seconds()
        
        previous_mode = self._mode
        
        # Create event
        event = StrategyControlEvent(
            action=ControlAction.KILL_SWITCH_RESET,
            actor=actor,
            actor_type=actor_type,
            reason=reason or "Kill switch reset",
            details={
                "previous_mode": previous_mode.value if previous_mode else None,
                "duration_seconds": duration,
                "orders_cancelled": self._orders_cancelled,
                "positions_closed": self._positions_closed
            },
            previous_state={
                "active": True,
                "mode": previous_mode.value if previous_mode else None
            },
            new_state={
                "active": False,
                "mode": None
            }
        )
        
        # Reset state
        self._active = False
        self._mode = None
        self._config = None
        self._activated_at = None
        self._activated_by = ""
        self._activation_reason = ""
        self._orders_cancelled = 0
        self._positions_closed = 0
        
        event.success = True
        
        # Save event
        control_repository.save_event(event)
        
        print(f"[KillSwitchService] Kill switch RESET by {actor}: {reason}")
        
        return {
            "success": True,
            "message": "Kill switch reset",
            "previous_mode": previous_mode.value if previous_mode else None,
            "duration_seconds": duration,
            "event_id": event.event_id,
            "changed": True
        }
    
    def is_active(self) -> bool:
        """Check if kill switch is active"""
        return self._active
    
    def get_mode(self) -> Optional[KillSwitchMode]:
        """Get current mode"""
        return self._mode
    
    def get_state(self) -> Dict[str, Any]:
        """Get kill switch state"""
        return {
            "active": self._active,
            "mode": self._mode.value if self._mode else None,
            "config": self._config.to_dict() if self._config else None,
            "activated_at": self._activated_at.isoformat() if self._activated_at else None,
            "activated_by": self._activated_by,
            "reason": self._activation_reason,
            "stats": {
                "orders_cancelled": self._orders_cancelled,
                "positions_closed": self._positions_closed
            }
        }
    
    def can_place_order(self) -> tuple:
        """
        Check if new orders can be placed.
        
        Returns (can_place, reason)
        """
        if not self._active:
            return True, ""
        
        if self._config and self._config.block_new_entries:
            return False, f"Kill switch active ({self._mode.value}): new entries blocked"
        
        return True, ""
    
    def can_reduce_position(self) -> tuple:
        """
        Check if position reductions are allowed.
        
        Returns (can_reduce, reason)
        """
        if not self._active:
            return True, ""
        
        if self._config and self._config.allow_reductions:
            return True, ""
        
        return False, "Kill switch active: reductions not allowed"


# Global singleton
kill_switch_service = KillSwitchService()
