"""
Config Switch Service (TR5)
===========================

Handles strategy configuration switching from admin panel.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from .control_types import (
    StrategyControlEvent,
    ControlAction,
    ActorType
)
from .control_repository import control_repository


class ConfigSwitchService:
    """
    Manages strategy config switching.
    
    Allows admin to switch between different strategy configurations.
    """
    
    def __init__(self):
        self._current_config_id = ""
        self._config_history: List[str] = []
        
        # Mock available configs
        self._available_configs = {
            "config_default": {
                "name": "Default Config",
                "description": "Standard parameters",
                "parameters": {"risk_per_trade": 0.01, "max_positions": 5}
            },
            "config_conservative": {
                "name": "Conservative Config",
                "description": "Reduced risk parameters",
                "parameters": {"risk_per_trade": 0.005, "max_positions": 3}
            },
            "config_aggressive": {
                "name": "Aggressive Config",
                "description": "Higher risk parameters",
                "parameters": {"risk_per_trade": 0.02, "max_positions": 8}
            }
        }
        
        print("[ConfigSwitchService] Initialized")
    
    def switch_config(
        self,
        config_id: str,
        reason: str = "",
        actor: str = "admin",
        actor_type: ActorType = ActorType.ADMIN
    ) -> Dict[str, Any]:
        """
        Switch to target config.
        
        Args:
            config_id: Configuration ID to switch to
            reason: Reason for switch
            actor: Who initiated
            actor_type: Type of actor
        
        Returns:
            Switch result
        """
        # Validate config exists (or allow new configs)
        if config_id not in self._available_configs:
            # For flexibility, allow switching to any config_id
            print(f"[ConfigSwitchService] Config {config_id} not in predefined list, allowing anyway")
        
        # Check if already on target
        if self._current_config_id == config_id:
            return {
                "success": True,
                "message": f"Already using config {config_id}",
                "config_id": config_id,
                "changed": False
            }
        
        # Create event
        previous_config = self._current_config_id
        event = StrategyControlEvent(
            action=ControlAction.CONFIG_SWITCH,
            actor=actor,
            actor_type=actor_type,
            reason=reason or f"Manual switch to {config_id}",
            details={
                "from_config": previous_config,
                "to_config": config_id
            },
            previous_state={"config_id": previous_config},
            new_state={"config_id": config_id}
        )
        
        # Execute switch
        self._current_config_id = config_id
        self._config_history.append(config_id)
        if len(self._config_history) > 100:
            self._config_history = self._config_history[-100:]
        
        event.success = True
        
        # Save event
        control_repository.save_event(event)
        
        print(f"[ConfigSwitchService] Switched config: {previous_config or 'none'} -> {config_id}")
        
        return {
            "success": True,
            "message": f"Switched to config {config_id}",
            "from_config": previous_config,
            "to_config": config_id,
            "event_id": event.event_id,
            "changed": True
        }
    
    def get_current_config(self) -> str:
        """Get current config ID"""
        return self._current_config_id
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get config information"""
        current_details = self._available_configs.get(self._current_config_id, {})
        
        return {
            "current": self._current_config_id,
            "current_details": current_details,
            "available": list(self._available_configs.keys()),
            "configs": self._available_configs
        }
    
    def get_config_history(self, limit: int = 20) -> List[str]:
        """Get recent config history"""
        return list(reversed(self._config_history[-limit:]))
    
    def register_config(
        self,
        config_id: str,
        name: str,
        description: str,
        parameters: Dict[str, Any]
    ) -> bool:
        """Register a new config"""
        self._available_configs[config_id] = {
            "name": name,
            "description": description,
            "parameters": parameters
        }
        return True
    
    def set_config(self, config_id: str):
        """Internal method to set config without logging"""
        self._current_config_id = config_id


# Global singleton
config_switch_service = ConfigSwitchService()
