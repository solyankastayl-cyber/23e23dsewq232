"""
TT5 - Control Policy
====================
Policy rules for determining what actions are allowed.
"""

from typing import Dict, Any


class ControlPolicy:
    """
    Main control gate determining what actions are allowed.
    
    Rules:
    - HARD_KILL: Nothing runs, everything stops
    - SOFT_KILL: No new entries, existing positions managed
    - PAUSED: No new trades, system observes only
    - EMERGENCY: Same as HARD_KILL but with alerting
    - ACTIVE: Normal operation
    
    Alpha modes:
    - AUTO: Actions auto-apply if confidence threshold met
    - MANUAL: All actions go to pending queue
    - OFF: Alpha Factory disabled, only observation
    """
    
    # Thresholds
    AUTO_APPLY_CONFIDENCE = 0.75  # Minimum confidence for auto-apply
    
    def can_trade(self, state: Dict[str, Any]) -> bool:
        """Check if trading is allowed at all"""
        if state.get("hard_kill", False):
            return False
        if state.get("emergency", False):
            return False
        return state.get("trading_enabled", False)

    def can_open_new_entries(self, state: Dict[str, Any]) -> bool:
        """Check if new position entries are allowed"""
        if not self.can_trade(state):
            return False
        if state.get("soft_kill", False):
            return False
        if state.get("system_state") == "PAUSED":
            return False
        return state.get("new_entries_enabled", False)

    def can_manage_positions(self, state: Dict[str, Any]) -> bool:
        """Check if existing positions can be managed"""
        if state.get("hard_kill", False):
            return False
        if state.get("emergency", False):
            return False
        return state.get("position_management_enabled", True)

    def get_alpha_mode(self, state: Dict[str, Any]) -> str:
        """Get current alpha mode"""
        return state.get("alpha_mode", "MANUAL")

    def should_auto_apply(self, state: Dict[str, Any], action: Dict[str, Any]) -> bool:
        """
        Determine if an action should be auto-applied.
        
        Requirements:
        - Alpha mode is AUTO
        - Action is marked as auto_apply
        - Confidence meets threshold
        - Action is not too risky
        """
        if self.get_alpha_mode(state) != "AUTO":
            return False
        
        if not action.get("auto_apply", False):
            return False
            
        confidence = float(action.get("confidence", 0.0))
        if confidence < self.AUTO_APPLY_CONFIDENCE:
            return False
        
        # High-risk actions always require manual approval
        high_risk_actions = ["HARD_KILL", "DISABLE_SYMBOL"]
        if action.get("action") in high_risk_actions:
            # Even in AUTO mode, require very high confidence
            if confidence < 0.90:
                return False
        
        return True

    def get_system_status(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get human-readable system status"""
        sys_state = state.get("system_state", "UNKNOWN")
        
        status_map = {
            "ACTIVE": {"level": "normal", "message": "System operating normally"},
            "PAUSED": {"level": "warning", "message": "System paused - observing only"},
            "SOFT_KILL": {"level": "critical", "message": "Soft kill active - no new entries"},
            "HARD_KILL": {"level": "emergency", "message": "Hard kill active - all trading stopped"},
            "EMERGENCY": {"level": "emergency", "message": "Emergency mode - system halted"},
        }
        
        return status_map.get(sys_state, {"level": "unknown", "message": "Unknown state"})
