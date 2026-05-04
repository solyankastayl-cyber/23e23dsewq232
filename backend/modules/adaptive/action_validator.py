"""
PHASE 3.1 — Action Validator

Validates calibration actions before applying.
Prevents destructive or unsafe changes.

Guards:
- minimum_enabled_assets: Can't disable all assets
- max_allocation: Single asset can't exceed 50%
- max_risk_reduction: Can't reduce below 0.3x
- max_threshold_increase: Can't exceed 0.95
- cooldown: Same target can't be modified twice in short period
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta


class ActionValidator:
    """
    Validates actions before execution.
    Ensures system doesn't apply destructive changes.
    """
    
    def __init__(
        self,
        min_enabled_assets: int = 3,
        max_allocation: float = 0.5,
        min_risk_multiplier: float = 0.3,
        max_threshold: float = 0.95,
        cooldown_minutes: int = 60
    ):
        self.min_enabled_assets = min_enabled_assets
        self.max_allocation = max_allocation
        self.min_risk_multiplier = min_risk_multiplier
        self.max_threshold = max_threshold
        self.cooldown_minutes = cooldown_minutes
        self._recent_actions: Dict[str, datetime] = {}
    
    def validate(self, action: Dict, current_state: Dict) -> Dict:
        """
        Validate a single action against current state.
        
        Args:
            action: Calibration action dict
            current_state: Current adaptive state
        
        Returns:
            {"allowed": bool, "reason": str, "details": dict}
        """
        target_type = action.get("target_type", "asset")
        target_id = action.get("target_id", "")
        action_type = action.get("action", "")
        
        # Check cooldown
        cooldown_result = self._check_cooldown(target_id)
        if not cooldown_result["allowed"]:
            return cooldown_result
        
        # Validate based on action type
        if action_type == "disable":
            return self._validate_disable(target_type, target_id, current_state)
        
        elif action_type == "reduce_risk":
            return self._validate_reduce_risk(target_id, current_state)
        
        elif action_type == "increase_threshold":
            return self._validate_increase_threshold(target_id, current_state)
        
        elif action_type == "increase_allocation":
            return self._validate_increase_allocation(target_id, current_state)
        
        elif action_type == "keep":
            return {"allowed": True, "reason": "no_change_needed", "details": {}}
        
        elif action_type == "cut_cluster_exposure":
            return self._validate_cut_cluster(target_id, current_state)
        
        else:
            return {"allowed": False, "reason": "unknown_action_type", "details": {"action": action_type}}
    
    def validate_batch(self, actions: List[Dict], current_state: Dict) -> Dict:
        """
        Validate a batch of actions.
        
        Returns:
            {"valid": [...], "invalid": [...], "summary": {...}}
        """
        valid = []
        invalid = []
        
        # Simulate state changes for batch validation
        simulated_state = dict(current_state)
        
        for action in actions:
            result = self.validate(action, simulated_state)
            
            if result["allowed"]:
                valid.append({"action": action, "validation": result})
                # Update simulated state for next validation
                simulated_state = self._simulate_apply(action, simulated_state)
            else:
                invalid.append({"action": action, "validation": result})
        
        return {
            "valid": valid,
            "invalid": invalid,
            "summary": {
                "total": len(actions),
                "valid_count": len(valid),
                "invalid_count": len(invalid),
                "approval_rate": len(valid) / len(actions) if actions else 0
            }
        }
    
    def _check_cooldown(self, target_id: str) -> Dict:
        """Check if target is in cooldown period."""
        now = datetime.now(timezone.utc)
        
        if target_id in self._recent_actions:
            last_action = self._recent_actions[target_id]
            cooldown_end = last_action + timedelta(minutes=self.cooldown_minutes)
            
            if now < cooldown_end:
                remaining = (cooldown_end - now).total_seconds() / 60
                return {
                    "allowed": False,
                    "reason": "cooldown_active",
                    "details": {
                        "target": target_id,
                        "cooldown_remaining_minutes": round(remaining, 1)
                    }
                }
        
        return {"allowed": True, "reason": "ok", "details": {}}
    
    def _validate_disable(self, target_type: str, target_id: str, state: Dict) -> Dict:
        """Validate disable action."""
        if target_type == "asset":
            enabled_assets = state.get("enabled_assets", [])
            
            # Check if already disabled
            if target_id not in enabled_assets:
                return {
                    "allowed": False,
                    "reason": "already_disabled",
                    "details": {"target": target_id}
                }
            
            # Check minimum enabled assets
            if len(enabled_assets) <= self.min_enabled_assets:
                return {
                    "allowed": False,
                    "reason": "minimum_enabled_assets_guard",
                    "details": {
                        "current_count": len(enabled_assets),
                        "minimum": self.min_enabled_assets
                    }
                }
        
        return {"allowed": True, "reason": "ok", "details": {}}
    
    def _validate_reduce_risk(self, target_id: str, state: Dict) -> Dict:
        """Validate reduce_risk action."""
        risk_map = state.get("risk_multipliers", {})
        current_risk = risk_map.get(target_id, 1.0)
        
        # Standard reduction is 0.8x
        new_risk = current_risk * 0.8
        
        if new_risk < self.min_risk_multiplier:
            return {
                "allowed": False,
                "reason": "min_risk_multiplier_guard",
                "details": {
                    "current": current_risk,
                    "proposed": new_risk,
                    "minimum": self.min_risk_multiplier
                }
            }
        
        return {"allowed": True, "reason": "ok", "details": {"new_risk": new_risk}}
    
    def _validate_increase_threshold(self, target_id: str, state: Dict) -> Dict:
        """Validate increase_threshold action."""
        thresholds = state.get("confidence_thresholds", {})
        current = thresholds.get(target_id, 0.5)
        
        # Standard increase is +0.05
        new_threshold = current + 0.05
        
        if new_threshold > self.max_threshold:
            return {
                "allowed": False,
                "reason": "max_threshold_guard",
                "details": {
                    "current": current,
                    "proposed": new_threshold,
                    "maximum": self.max_threshold
                }
            }
        
        return {"allowed": True, "reason": "ok", "details": {"new_threshold": new_threshold}}
    
    def _validate_increase_allocation(self, target_id: str, state: Dict) -> Dict:
        """Validate increase_allocation action."""
        allocations = state.get("allocations", {})
        current = allocations.get(target_id, 0.1)
        
        # Standard increase is +0.05
        new_allocation = current + 0.05
        
        if new_allocation > self.max_allocation:
            return {
                "allowed": False,
                "reason": "max_allocation_guard",
                "details": {
                    "current": current,
                    "proposed": new_allocation,
                    "maximum": self.max_allocation
                }
            }
        
        # Check total allocation doesn't exceed 100%
        total_alloc = sum(allocations.values()) + 0.05
        if total_alloc > 1.0:
            return {
                "allowed": False,
                "reason": "total_allocation_exceeded",
                "details": {"total": total_alloc}
            }
        
        return {"allowed": True, "reason": "ok", "details": {"new_allocation": new_allocation}}
    
    def _validate_cut_cluster(self, target_id: str, state: Dict) -> Dict:
        """Validate cut_cluster_exposure action."""
        cluster_exposures = state.get("cluster_exposures", {})
        current = cluster_exposures.get(target_id, 0.2)
        
        # Standard cut is 0.7x
        new_exposure = current * 0.7
        
        if new_exposure < 0.05:
            return {
                "allowed": False,
                "reason": "min_cluster_exposure_guard",
                "details": {
                    "current": current,
                    "proposed": new_exposure,
                    "minimum": 0.05
                }
            }
        
        return {"allowed": True, "reason": "ok", "details": {"new_exposure": new_exposure}}
    
    def _simulate_apply(self, action: Dict, state: Dict) -> Dict:
        """Simulate applying action to state (for batch validation)."""
        state = dict(state)
        target_id = action.get("target_id")
        action_type = action.get("action")
        
        if action_type == "disable":
            enabled = state.get("enabled_assets", [])
            state["enabled_assets"] = [a for a in enabled if a != target_id]
        
        elif action_type == "reduce_risk":
            risk_map = dict(state.get("risk_multipliers", {}))
            risk_map[target_id] = risk_map.get(target_id, 1.0) * 0.8
            state["risk_multipliers"] = risk_map
        
        elif action_type == "increase_threshold":
            thresholds = dict(state.get("confidence_thresholds", {}))
            thresholds[target_id] = thresholds.get(target_id, 0.5) + 0.05
            state["confidence_thresholds"] = thresholds
        
        elif action_type == "increase_allocation":
            alloc = dict(state.get("allocations", {}))
            alloc[target_id] = alloc.get(target_id, 0.1) + 0.05
            state["allocations"] = alloc
        
        return state
    
    def record_action(self, target_id: str):
        """Record that an action was applied to target."""
        self._recent_actions[target_id] = datetime.now(timezone.utc)
    
    def clear_cooldowns(self):
        """Clear all cooldowns (for testing/reset)."""
        self._recent_actions = {}
