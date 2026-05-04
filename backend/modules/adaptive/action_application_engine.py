"""
PHASE 3.1 — Action Application Engine

Main orchestrator for applying calibration actions.
Coordinates validation, execution, state management, and history.

Pipeline:
1. Receive actions from Calibration Layer
2. Validate each action
3. Execute valid actions
4. Update adaptive state
5. Record to history
6. Return results
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from .action_validator import ActionValidator
from .action_executor import ActionExecutor
from .adaptive_state_registry import AdaptiveStateRegistry
from .action_history import ActionHistory


class ActionApplicationEngine:
    """
    Main engine for applying calibration actions.
    
    Orchestrates the full pipeline:
    Calibration Actions → Validation → Execution → State Update → Audit
    """
    
    def __init__(self, db=None):
        self.validator = ActionValidator()
        self.executor = ActionExecutor()
        self.registry = AdaptiveStateRegistry(db)
        self.history = ActionHistory(db)
    
    def apply(self, actions: List[Dict], dry_run: bool = False) -> Dict:
        """
        Apply calibration actions to system.
        
        Args:
            actions: List of calibration action dicts
            dry_run: If True, validate but don't apply
        
        Returns:
            {
                "applied": [...],
                "rejected": [...],
                "state": current state,
                "summary": {...}
            }
        """
        # Get current state
        current_state = self.registry.get_state()
        state_before = self._deep_copy(current_state)
        
        applied = []
        rejected = []
        
        for action in actions:
            # Validate
            validation = self.validator.validate(action, current_state)
            
            if not validation["allowed"]:
                rejected.append({
                    "action": action,
                    "reason": validation["reason"],
                    "details": validation.get("details", {})
                })
                
                # Record rejected action
                if not dry_run:
                    self.history.record(
                        action=action,
                        status="rejected",
                        validation_result=validation,
                        state_before=state_before
                    )
                continue
            
            if dry_run:
                # For dry run, just simulate
                applied.append({
                    "action": action,
                    "would_apply": True,
                    "validation": validation
                })
                current_state = self.executor.execute(action, current_state)
                continue
            
            # Execute
            new_state = self.executor.execute(action, current_state)
            
            # Update registry
            self.registry.update(new_state, action)
            
            # Record to history
            self.history.record(
                action=action,
                status="applied",
                validation_result=validation,
                state_before=state_before,
                state_after=new_state
            )
            
            # Update cooldown
            self.validator.record_action(action.get("target_id", ""))
            
            applied.append({
                "action": action,
                "applied": True,
                "description": self.executor.get_action_description(action)
            })
            
            # Update current state for next iteration
            current_state = new_state
            state_before = self._deep_copy(current_state)
        
        return {
            "ok": True,
            "dry_run": dry_run,
            "applied": applied,
            "rejected": rejected,
            "state": current_state,
            "summary": {
                "total_actions": len(actions),
                "applied_count": len(applied),
                "rejected_count": len(rejected),
                "success_rate": len(applied) / len(actions) if actions else 0
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def apply_single(self, action: Dict, dry_run: bool = False) -> Dict:
        """Apply a single action."""
        return self.apply([action], dry_run=dry_run)
    
    def get_state(self) -> Dict:
        """Get current adaptive state."""
        return self.registry.get_state()
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """Get action history."""
        return self.history.get_history(limit=limit)
    
    def reset(self) -> Dict:
        """Reset to default state."""
        state = self.registry.reset()
        self.validator.clear_cooldowns()
        
        return {
            "ok": True,
            "state": state,
            "message": "Adaptive state reset to defaults"
        }
    
    def get_summary(self) -> Dict:
        """Get full adaptive system summary."""
        state = self.registry.get_state()
        state_summary = self.registry.get_summary()
        history_summary = self.history.get_summary()
        
        return {
            "ok": True,
            "state_summary": state_summary,
            "history_summary": history_summary,
            "current_configuration": {
                "enabled_assets": state.get("enabled_assets", []),
                "disabled_assets": state.get("disabled_assets", []),
                "custom_risk_targets": list(state.get("risk_multipliers", {}).keys()),
                "custom_threshold_targets": list(state.get("confidence_thresholds", {}).keys())
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def check_asset(self, asset: str) -> Dict:
        """Check adaptive configuration for specific asset."""
        return {
            "asset": asset,
            "enabled": self.registry.is_asset_enabled(asset),
            "risk_multiplier": self.registry.get_risk_multiplier(asset),
            "confidence_threshold": self.registry.get_confidence_threshold(asset),
            "allocation": self.registry.get_allocation(asset),
            "recent_actions": self.history.get_recent_for_target(asset, limit=5)
        }
    
    def validate_batch(self, actions: List[Dict]) -> Dict:
        """Validate a batch of actions without applying."""
        current_state = self.registry.get_state()
        return self.validator.validate_batch(actions, current_state)
    
    def _deep_copy(self, state: Dict) -> Dict:
        """Deep copy state dict."""
        import copy
        return copy.deepcopy(state)


# Singleton instance
_engine: Optional[ActionApplicationEngine] = None


def get_action_application_engine() -> ActionApplicationEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = ActionApplicationEngine()
    return _engine
