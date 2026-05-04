"""
PHASE 3.3 — State Snapshot

Creates immutable snapshots of adaptive state.
Used for audit trail and rollback.
"""

from typing import Dict, Optional
from datetime import datetime, timezone
from copy import deepcopy
import hashlib
import json


class StateSnapshot:
    """
    Creates and manages state snapshots.
    
    Each snapshot contains:
    - timestamp: When snapshot was created
    - state: Deep copy of adaptive state
    - hash: MD5 hash of state for integrity
    - metadata: Optional context (trigger, reason, etc.)
    """
    
    def create_snapshot(
        self,
        state: Dict,
        trigger: str = "manual",
        reason: str = "",
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create a snapshot of current state.
        
        Args:
            state: Adaptive state to snapshot
            trigger: What triggered snapshot ("manual", "pre_apply", "post_apply", "scheduled")
            reason: Human-readable reason
            metadata: Additional context
        
        Returns:
            Snapshot dict with state, hash, timestamp
        """
        state_copy = deepcopy(state)
        state_hash = self._hash_state(state_copy)
        
        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": state_copy,
            "hash": state_hash,
            "trigger": trigger,
            "reason": reason,
            "metadata": metadata or {},
            "version": state.get("version", 0)
        }
        
        return snapshot
    
    def _hash_state(self, state: Dict) -> str:
        """Compute MD5 hash of state for integrity checking."""
        # Exclude volatile fields from hash
        state_for_hash = {
            k: v for k, v in state.items() 
            if k not in ["last_updated", "applied_actions"]
        }
        
        try:
            state_json = json.dumps(state_for_hash, sort_keys=True, default=str)
            return hashlib.md5(state_json.encode()).hexdigest()
        except Exception:
            return "invalid_hash"
    
    def verify_integrity(self, snapshot: Dict) -> bool:
        """Verify snapshot integrity using hash."""
        if "state" not in snapshot or "hash" not in snapshot:
            return False
        
        computed_hash = self._hash_state(snapshot["state"])
        return computed_hash == snapshot["hash"]
    
    def get_state_summary(self, state: Dict) -> Dict:
        """Get summary of state for quick comparison."""
        return {
            "enabled_assets_count": len(state.get("enabled_assets", [])),
            "disabled_assets_count": len(state.get("disabled_assets", [])),
            "custom_risk_count": len(state.get("risk_multipliers", {})),
            "custom_threshold_count": len(state.get("confidence_thresholds", {})),
            "applied_actions_count": len(state.get("applied_actions", [])),
            "version": state.get("version", 0)
        }
    
    def compare_summaries(self, old_summary: Dict, new_summary: Dict) -> Dict:
        """Quick comparison of two state summaries."""
        changes = {}
        
        for key in old_summary:
            old_val = old_summary.get(key, 0)
            new_val = new_summary.get(key, 0)
            
            if old_val != new_val:
                changes[key] = {
                    "before": old_val,
                    "after": new_val,
                    "delta": new_val - old_val if isinstance(new_val, (int, float)) else None
                }
        
        return changes
