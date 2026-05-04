"""
PHASE 3.1 — Action Executor

Executes validated calibration actions on adaptive state.
Actually modifies system configuration.

Supported actions:
- disable: Remove asset from enabled list
- reduce_risk: Lower risk multiplier (0.8x)
- increase_threshold: Raise confidence threshold (+0.05)
- increase_allocation: Boost allocation (+0.05)
- cut_cluster_exposure: Reduce cluster weight (0.7x)
- keep: No change
"""

from typing import Dict, Optional
from datetime import datetime, timezone


class ActionExecutor:
    """
    Executes calibration actions on adaptive state.
    Transforms action commands into state changes.
    """
    
    def __init__(
        self,
        risk_reduction_factor: float = 0.8,
        threshold_increment: float = 0.05,
        allocation_increment: float = 0.05,
        cluster_cut_factor: float = 0.7
    ):
        self.risk_reduction_factor = risk_reduction_factor
        self.threshold_increment = threshold_increment
        self.allocation_increment = allocation_increment
        self.cluster_cut_factor = cluster_cut_factor
    
    def execute(self, action: Dict, state: Dict) -> Dict:
        """
        Execute a single action on state.
        
        Args:
            action: Calibration action dict
            state: Current adaptive state
        
        Returns:
            New state after action applied
        """
        # Deep copy to avoid mutation
        state = self._deep_copy_state(state)
        
        target_type = action.get("target_type", "asset")
        target_id = action.get("target_id", "")
        action_type = action.get("action", "")
        
        if action_type == "disable":
            return self._execute_disable(target_type, target_id, state, action)
        
        elif action_type == "reduce_risk":
            return self._execute_reduce_risk(target_id, state, action)
        
        elif action_type == "increase_threshold":
            return self._execute_increase_threshold(target_id, state, action)
        
        elif action_type == "increase_allocation":
            return self._execute_increase_allocation(target_id, state, action)
        
        elif action_type == "cut_cluster_exposure":
            return self._execute_cut_cluster(target_id, state, action)
        
        elif action_type == "keep":
            # No change, but record that we evaluated this
            return state
        
        else:
            # Unknown action type - return unchanged
            return state
    
    def execute_batch(self, actions: list, state: Dict) -> Dict:
        """
        Execute multiple actions sequentially.
        
        Args:
            actions: List of action dicts
            state: Initial state
        
        Returns:
            Final state after all actions applied
        """
        current_state = state
        
        for action in actions:
            current_state = self.execute(action, current_state)
        
        return current_state
    
    def _execute_disable(self, target_type: str, target_id: str, state: Dict, action: Dict) -> Dict:
        """Execute disable action."""
        if target_type == "asset":
            enabled = list(state.get("enabled_assets", []))
            if target_id in enabled:
                enabled.remove(target_id)
                state["enabled_assets"] = enabled
                
                # Add to disabled list
                disabled = list(state.get("disabled_assets", []))
                if target_id not in disabled:
                    disabled.append(target_id)
                state["disabled_assets"] = disabled
        
        elif target_type == "strategy":
            enabled_strategies = list(state.get("enabled_strategies", []))
            if target_id in enabled_strategies:
                enabled_strategies.remove(target_id)
                state["enabled_strategies"] = enabled_strategies
        
        elif target_type == "cluster":
            # Disable entire cluster by setting exposure to 0
            exposures = dict(state.get("cluster_exposures", {}))
            exposures[target_id] = 0.0
            state["cluster_exposures"] = exposures
        
        return state
    
    def _execute_reduce_risk(self, target_id: str, state: Dict, action: Dict) -> Dict:
        """Execute reduce_risk action."""
        risk_map = dict(state.get("risk_multipliers", {}))
        current = risk_map.get(target_id, 1.0)
        
        # Apply reduction factor
        new_risk = max(0.3, current * self.risk_reduction_factor)
        risk_map[target_id] = round(new_risk, 4)
        
        state["risk_multipliers"] = risk_map
        return state
    
    def _execute_increase_threshold(self, target_id: str, state: Dict, action: Dict) -> Dict:
        """Execute increase_threshold action."""
        thresholds = dict(state.get("confidence_thresholds", {}))
        current = thresholds.get(target_id, 0.5)
        
        # Apply increment
        new_threshold = min(0.95, current + self.threshold_increment)
        thresholds[target_id] = round(new_threshold, 4)
        
        state["confidence_thresholds"] = thresholds
        return state
    
    def _execute_increase_allocation(self, target_id: str, state: Dict, action: Dict) -> Dict:
        """Execute increase_allocation action."""
        allocations = dict(state.get("allocations", {}))
        current = allocations.get(target_id, 0.1)
        
        # Apply increment
        new_allocation = min(0.5, current + self.allocation_increment)
        allocations[target_id] = round(new_allocation, 4)
        
        state["allocations"] = allocations
        return state
    
    def _execute_cut_cluster(self, target_id: str, state: Dict, action: Dict) -> Dict:
        """Execute cut_cluster_exposure action."""
        exposures = dict(state.get("cluster_exposures", {}))
        current = exposures.get(target_id, 0.2)
        
        # Apply cut factor
        new_exposure = max(0.05, current * self.cluster_cut_factor)
        exposures[target_id] = round(new_exposure, 4)
        
        state["cluster_exposures"] = exposures
        return state
    
    def _deep_copy_state(self, state: Dict) -> Dict:
        """Deep copy state dict."""
        import copy
        return copy.deepcopy(state)
    
    def get_action_description(self, action: Dict) -> str:
        """Get human-readable description of action."""
        target_id = action.get("target_id", "unknown")
        action_type = action.get("action", "unknown")
        
        descriptions = {
            "disable": f"Disable {target_id}",
            "reduce_risk": f"Reduce risk for {target_id} by {(1 - self.risk_reduction_factor) * 100:.0f}%",
            "increase_threshold": f"Raise confidence threshold for {target_id} by {self.threshold_increment}",
            "increase_allocation": f"Increase allocation for {target_id} by {self.allocation_increment}",
            "cut_cluster_exposure": f"Cut cluster {target_id} exposure by {(1 - self.cluster_cut_factor) * 100:.0f}%",
            "keep": f"No change for {target_id}"
        }
        
        return descriptions.get(action_type, f"Unknown action on {target_id}")
