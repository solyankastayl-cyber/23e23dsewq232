"""
PHASE 3.2 — Policy Guard

Main orchestrator for policy enforcement.
Integrates with Calibration Layer and Action Application Engine.

Pipeline:
Calibration → PolicyGuard → ActionEngine → State

Features:
- Applies policy filter to calibration actions
- Handles emergency mode detection
- Coordinates with application engine
- Provides policy status and metrics
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

from .policy_config import PolicyConfig, DEFAULT_POLICY_CONFIG
from .policy_evaluator import PolicyEvaluator, PolicyDecision


@dataclass
class PolicyResult:
    """Result of policy guard filtering."""
    allowed_actions: List[Dict]
    blocked_actions: List[Dict]
    deferred_actions: List[Dict]
    emergency_mode: bool
    policy_summary: Dict


class PolicyGuard:
    """
    Main policy guard orchestrator.
    
    Sits between Calibration Layer and Action Application Engine.
    Filters actions based on policy rules.
    """
    
    def __init__(self, config: Optional[PolicyConfig] = None, db=None):
        self.config = config or DEFAULT_POLICY_CONFIG
        self.evaluator = PolicyEvaluator(self.config)
        self.db = db
        self._ensure_db()
        self._emergency_mode = False
        self._policy_history: List[Dict] = []
    
    def _ensure_db(self):
        """Ensure database connection."""
        if self.db is None:
            try:
                from core.database import get_database
                self.db = get_database()
            except Exception:
                self.db = None
    
    def apply_policy(
        self,
        actions: List[Dict],
        current_state: Dict,
        degradation_info: Optional[Dict] = None,
        force_emergency: bool = False
    ) -> PolicyResult:
        """
        Apply policy filter to calibration actions.
        
        Args:
            actions: Actions from Calibration Layer
            current_state: Current adaptive state
            degradation_info: Optional degradation data for emergency mode
            force_emergency: Force emergency mode on
        
        Returns:
            PolicyResult with filtered actions
        """
        # Check cycle cooldown
        can_start, reason = self.evaluator.can_start_cycle()
        if not can_start:
            return PolicyResult(
                allowed_actions=[],
                blocked_actions=[],
                deferred_actions=[{"action": a, "reason": reason} for a in actions],
                emergency_mode=False,
                policy_summary={
                    "status": "cooldown",
                    "reason": reason,
                    "total_deferred": len(actions)
                }
            )
        
        # Check emergency mode
        emergency_mode = force_emergency or self._detect_emergency_mode(
            degradation_info, current_state
        )
        self._emergency_mode = emergency_mode
        
        # Trim batch if needed
        if len(actions) > self.config.max_batch_size:
            actions = actions[:self.config.max_batch_size]
        
        # Evaluate all actions
        result = self.evaluator.evaluate_batch(actions, current_state, emergency_mode)
        
        # Extract allowed action dicts
        allowed = [item["action"] for item in result["allowed"]]
        blocked = result["blocked"]
        deferred = result["deferred"]
        
        # Record policy result
        self._record_policy_result(result, emergency_mode)
        
        # Record cycle
        if allowed:
            self.evaluator.record_cycle()
        
        return PolicyResult(
            allowed_actions=allowed,
            blocked_actions=blocked,
            deferred_actions=deferred,
            emergency_mode=emergency_mode,
            policy_summary=result["summary"]
        )
    
    def _detect_emergency_mode(
        self,
        degradation_info: Optional[Dict],
        state: Dict
    ) -> bool:
        """Detect if system should enter emergency mode."""
        if not self.config.enable_emergency_mode:
            return False
        
        if degradation_info is None:
            return False
        
        # Check degradation rate
        total_analyzed = degradation_info.get("total_analyzed", 0)
        degrading_count = degradation_info.get("degrading_count", 0)
        
        if total_analyzed == 0:
            return False
        
        degradation_rate = degrading_count / total_analyzed
        
        if degradation_rate >= self.config.emergency_trigger_degradation_rate:
            return True
        
        # Check severe degradations
        severe_count = degradation_info.get("severe_count", 0)
        if severe_count >= 3:
            return True
        
        return False
    
    def _record_policy_result(self, result: Dict, emergency_mode: bool):
        """Record policy result for history."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": result["summary"],
            "emergency_mode": emergency_mode,
            "allowed_count": len(result["allowed"]),
            "blocked_count": len(result["blocked"]),
            "deferred_count": len(result["deferred"])
        }
        
        self._policy_history.append(record)
        
        # Trim history
        if len(self._policy_history) > 100:
            self._policy_history = self._policy_history[-100:]
        
        # Save to DB
        if self.db is not None:
            try:
                self.db.policy_history.insert_one(record)
            except Exception as e:
                print(f"[PolicyGuard] DB save error: {e}")
    
    def get_status(self) -> Dict:
        """Get current policy status."""
        can_start, cooldown_reason = self.evaluator.can_start_cycle()
        
        return {
            "emergency_mode": self._emergency_mode,
            "can_start_cycle": can_start,
            "cooldown_reason": cooldown_reason,
            "config": self.config.to_dict(),
            "recent_history_count": len(self._policy_history)
        }
    
    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get recent policy history."""
        # First try in-memory
        in_memory = self._policy_history[-limit:]
        
        # Try to load from DB if needed
        if self.db is not None and len(in_memory) < limit:
            try:
                records = list(
                    self.db.policy_history.find({}, {"_id": 0})
                    .sort("timestamp", -1)
                    .limit(limit)
                )
                return records if records else in_memory
            except Exception as e:
                print(f"[PolicyGuard] Load history error: {e}")
        
        return in_memory
    
    def set_emergency_mode(self, enabled: bool):
        """Manually set emergency mode."""
        self._emergency_mode = enabled
    
    def update_config(self, new_config: Dict):
        """Update policy configuration."""
        self.config = PolicyConfig.from_dict(new_config)
        self.evaluator = PolicyEvaluator(self.config)
    
    def reset(self):
        """Reset policy guard state."""
        self.evaluator.reset_counters()
        self._emergency_mode = False
        self._policy_history = []
    
    def force_cycle_reset(self):
        """Force reset cycle cooldown (admin only)."""
        self.evaluator._last_cycle_time = None
        self.evaluator.reset_counters()


# Integration function for easy use
def apply_policy_to_calibration(
    calibration_actions: List[Dict],
    adaptive_state: Dict,
    degradation_info: Optional[Dict] = None,
    config: Optional[PolicyConfig] = None
) -> PolicyResult:
    """
    Convenience function to apply policy to calibration actions.
    
    Usage:
        from modules.adaptive.policy import apply_policy_to_calibration
        
        result = apply_policy_to_calibration(
            calibration_actions=actions,
            adaptive_state=state,
            degradation_info=degradation
        )
        
        if result.allowed_actions:
            engine.apply(result.allowed_actions)
    """
    guard = PolicyGuard(config)
    return guard.apply_policy(
        calibration_actions,
        adaptive_state,
        degradation_info
    )


# Singleton instance
_policy_guard: Optional[PolicyGuard] = None


def get_policy_guard() -> PolicyGuard:
    """Get singleton policy guard instance."""
    global _policy_guard
    if _policy_guard is None:
        _policy_guard = PolicyGuard()
    return _policy_guard
