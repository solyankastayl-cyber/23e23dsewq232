"""
PHASE 3.1 — Adaptive State Registry

Stores and manages current adaptive state.
This is the "live" configuration after all adaptations.

State structure:
- enabled_assets: Active trading assets
- disabled_assets: Disabled by calibration
- risk_multipliers: Per-asset risk scaling
- confidence_thresholds: Per-asset confidence requirements
- allocations: Per-asset allocation weights
- cluster_exposures: Per-cluster exposure limits
- applied_actions: History of applied actions
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
import json


# Default state - starting point before any adaptations
DEFAULT_ADAPTIVE_STATE = {
    "enabled_assets": [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT",
        "DOTUSDT", "ATOMUSDT", "NEARUSDT", "MATICUSDT", "ARBUSDT"
    ],
    "disabled_assets": [],
    "risk_multipliers": {},
    "confidence_thresholds": {},
    "allocations": {},
    "cluster_exposures": {
        "btc": 0.25,
        "eth": 0.20,
        "alt_l1": 0.20,
        "defi": 0.15,
        "infra": 0.10,
        "other": 0.10
    },
    "enabled_strategies": ["trend_momentum", "mean_reversion", "breakout"],
    "applied_actions": [],
    "version": 1,
    "last_updated": None
}


class AdaptiveStateRegistry:
    """
    Manages adaptive state storage and retrieval.
    
    State is stored in MongoDB for persistence.
    Provides snapshot/restore capabilities.
    """
    
    def __init__(self, db=None):
        self.db = db
        self._ensure_db()
        self._cached_state: Optional[Dict] = None
    
    def _ensure_db(self):
        """Ensure database connection."""
        if self.db is None:
            try:
                from core.database import get_database
                self.db = get_database()
            except Exception:
                self.db = None
    
    def get_state(self, use_cache: bool = True) -> Dict:
        """
        Get current adaptive state.
        
        Returns cached state if available, otherwise loads from DB.
        Falls back to default state if no saved state exists.
        """
        if use_cache and self._cached_state:
            return self._deep_copy(self._cached_state)
        
        state = self._load_from_db()
        
        if state:
            self._cached_state = state
            return self._deep_copy(state)
        
        # Return default state
        return self._deep_copy(DEFAULT_ADAPTIVE_STATE)
    
    def update(self, new_state: Dict, action: Optional[Dict] = None):
        """
        Update adaptive state.
        
        Args:
            new_state: New state dict
            action: Optional action that triggered update
        """
        # Record action in state
        if action:
            applied = list(new_state.get("applied_actions", []))
            applied.append({
                "target_type": action.get("target_type"),
                "target_id": action.get("target_id"),
                "action": action.get("action"),
                "reason": action.get("reason", ""),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            new_state["applied_actions"] = applied
        
        # Update metadata
        new_state["last_updated"] = datetime.now(timezone.utc).isoformat()
        new_state["version"] = new_state.get("version", 0) + 1
        
        # Save to DB
        self._save_to_db(new_state)
        
        # Update cache
        self._cached_state = self._deep_copy(new_state)
    
    def reset(self) -> Dict:
        """Reset to default state."""
        default = self._deep_copy(DEFAULT_ADAPTIVE_STATE)
        default["last_updated"] = datetime.now(timezone.utc).isoformat()
        default["applied_actions"] = []
        default["version"] = 1
        
        self._save_to_db(default)
        self._cached_state = default
        
        return default
    
    def get_snapshot(self) -> Dict:
        """Get a snapshot of current state for backup."""
        state = self.get_state()
        return {
            "snapshot_time": datetime.now(timezone.utc).isoformat(),
            "state": state
        }
    
    def restore_snapshot(self, snapshot: Dict) -> Dict:
        """Restore state from snapshot."""
        if "state" not in snapshot:
            raise ValueError("Invalid snapshot format")
        
        state = snapshot["state"]
        state["restored_from"] = snapshot.get("snapshot_time")
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        self._save_to_db(state)
        self._cached_state = self._deep_copy(state)
        
        return state
    
    def get_applied_actions(self, limit: int = 50) -> List[Dict]:
        """Get recent applied actions."""
        state = self.get_state()
        actions = state.get("applied_actions", [])
        return actions[-limit:] if len(actions) > limit else actions
    
    def is_asset_enabled(self, asset: str) -> bool:
        """Check if asset is enabled."""
        state = self.get_state()
        return asset in state.get("enabled_assets", [])
    
    def get_risk_multiplier(self, asset: str) -> float:
        """Get risk multiplier for asset."""
        state = self.get_state()
        return state.get("risk_multipliers", {}).get(asset, 1.0)
    
    def get_confidence_threshold(self, asset: str) -> float:
        """Get confidence threshold for asset."""
        state = self.get_state()
        return state.get("confidence_thresholds", {}).get(asset, 0.5)
    
    def get_allocation(self, asset: str) -> float:
        """Get allocation for asset."""
        state = self.get_state()
        return state.get("allocations", {}).get(asset, 0.1)
    
    def get_summary(self) -> Dict:
        """Get summary of current adaptive state."""
        state = self.get_state()
        
        return {
            "enabled_assets_count": len(state.get("enabled_assets", [])),
            "disabled_assets_count": len(state.get("disabled_assets", [])),
            "custom_risk_multipliers": len(state.get("risk_multipliers", {})),
            "custom_thresholds": len(state.get("confidence_thresholds", {})),
            "custom_allocations": len(state.get("allocations", {})),
            "applied_actions_count": len(state.get("applied_actions", [])),
            "version": state.get("version", 0),
            "last_updated": state.get("last_updated")
        }
    
    def _load_from_db(self) -> Optional[Dict]:
        """Load state from database."""
        if self.db is None:
            return None
        
        try:
            doc = self.db.adaptive_state.find_one({"_id": "current"})
            if doc is not None:
                doc.pop("_id", None)
                return doc
            return None
        except Exception as e:
            print(f"[AdaptiveState] Load error: {e}")
            return None
    
    def _save_to_db(self, state: Dict):
        """Save state to database."""
        if self.db is None:
            return
        
        try:
            self.db.adaptive_state.update_one(
                {"_id": "current"},
                {"$set": state},
                upsert=True
            )
        except Exception as e:
            print(f"[AdaptiveState] Save error: {e}")
    
    def _deep_copy(self, state: Dict) -> Dict:
        """Deep copy state dict."""
        import copy
        return copy.deepcopy(state)
