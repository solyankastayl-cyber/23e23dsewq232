"""
PHASE 3.3 — Diff Engine

Computes differences between adaptive states.
Shows exactly what changed between snapshots.
"""

from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass


@dataclass
class FieldDiff:
    """Single field difference."""
    field: str
    before: Any
    after: Any
    change_type: str  # "added", "removed", "modified"


class DiffEngine:
    """
    Computes and analyzes differences between states.
    
    Provides:
    - Field-level diff
    - List-level diff (added/removed items)
    - Change summary
    - Impact analysis
    """
    
    def compute_diff(self, old_state: Dict, new_state: Dict) -> Dict:
        """
        Compute full diff between two states.
        
        Args:
            old_state: Previous state
            new_state: Current state
        
        Returns:
            {
                "changes": {...},
                "summary": {...},
                "impact": {...}
            }
        """
        changes = {}
        
        all_keys = set(old_state.keys()) | set(new_state.keys())
        
        for key in all_keys:
            old_val = old_state.get(key)
            new_val = new_state.get(key)
            
            if old_val != new_val:
                changes[key] = self._compute_field_diff(key, old_val, new_val)
        
        summary = self._compute_summary(changes)
        impact = self._analyze_impact(changes)
        
        return {
            "changes": changes,
            "summary": summary,
            "impact": impact,
            "has_changes": len(changes) > 0
        }
    
    def _compute_field_diff(self, field: str, old_val: Any, new_val: Any) -> Dict:
        """Compute diff for a single field."""
        # Determine change type
        if old_val is None:
            change_type = "added"
        elif new_val is None:
            change_type = "removed"
        else:
            change_type = "modified"
        
        diff = {
            "before": old_val,
            "after": new_val,
            "change_type": change_type
        }
        
        # Special handling for lists
        if isinstance(old_val, list) and isinstance(new_val, list):
            diff["list_diff"] = self._compute_list_diff(old_val, new_val)
        
        # Special handling for dicts
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            diff["dict_diff"] = self._compute_dict_diff(old_val, new_val)
        
        return diff
    
    def _compute_list_diff(self, old_list: List, new_list: List) -> Dict:
        """Compute diff for lists (added/removed items)."""
        old_set = set(old_list) if all(isinstance(x, (str, int, float)) for x in old_list) else set()
        new_set = set(new_list) if all(isinstance(x, (str, int, float)) for x in new_list) else set()
        
        if old_set and new_set:
            return {
                "added": list(new_set - old_set),
                "removed": list(old_set - new_set),
                "unchanged": list(old_set & new_set)
            }
        
        return {
            "old_count": len(old_list),
            "new_count": len(new_list),
            "delta": len(new_list) - len(old_list)
        }
    
    def _compute_dict_diff(self, old_dict: Dict, new_dict: Dict) -> Dict:
        """Compute diff for nested dicts."""
        all_keys = set(old_dict.keys()) | set(new_dict.keys())
        
        added = []
        removed = []
        modified = []
        
        for key in all_keys:
            if key not in old_dict:
                added.append(key)
            elif key not in new_dict:
                removed.append(key)
            elif old_dict[key] != new_dict[key]:
                modified.append({
                    "key": key,
                    "before": old_dict[key],
                    "after": new_dict[key]
                })
        
        return {
            "added_keys": added,
            "removed_keys": removed,
            "modified": modified
        }
    
    def _compute_summary(self, changes: Dict) -> Dict:
        """Compute human-readable summary of changes."""
        summary = {
            "total_fields_changed": len(changes),
            "fields_added": 0,
            "fields_removed": 0,
            "fields_modified": 0,
            "changed_fields": list(changes.keys())
        }
        
        for field, diff in changes.items():
            change_type = diff.get("change_type", "modified")
            if change_type == "added":
                summary["fields_added"] += 1
            elif change_type == "removed":
                summary["fields_removed"] += 1
            else:
                summary["fields_modified"] += 1
        
        # Specific field summaries
        if "enabled_assets" in changes:
            list_diff = changes["enabled_assets"].get("list_diff", {})
            summary["assets_enabled"] = list_diff.get("added", [])
            summary["assets_disabled"] = list_diff.get("removed", [])
        
        if "risk_multipliers" in changes:
            dict_diff = changes["risk_multipliers"].get("dict_diff", {})
            summary["risk_changes"] = len(dict_diff.get("modified", [])) + len(dict_diff.get("added_keys", []))
        
        if "confidence_thresholds" in changes:
            dict_diff = changes["confidence_thresholds"].get("dict_diff", {})
            summary["threshold_changes"] = len(dict_diff.get("modified", [])) + len(dict_diff.get("added_keys", []))
        
        return summary
    
    def _analyze_impact(self, changes: Dict) -> Dict:
        """Analyze potential impact of changes."""
        impact = {
            "risk_level": "low",
            "warnings": [],
            "recommendations": []
        }
        
        # Check for high-impact changes
        if "enabled_assets" in changes:
            list_diff = changes["enabled_assets"].get("list_diff", {})
            disabled = list_diff.get("removed", [])
            
            if len(disabled) > 3:
                impact["risk_level"] = "high"
                impact["warnings"].append(f"Large number of assets disabled ({len(disabled)})")
            elif len(disabled) > 0:
                impact["risk_level"] = "medium"
        
        if "risk_multipliers" in changes:
            dict_diff = changes["risk_multipliers"].get("dict_diff", {})
            modified = dict_diff.get("modified", [])
            
            for mod in modified:
                if mod.get("after", 1) < 0.5:
                    impact["warnings"].append(f"Risk significantly reduced for {mod['key']}")
        
        # Check version jump
        if "version" in changes:
            version_diff = changes["version"].get("after", 0) - changes["version"].get("before", 0)
            if version_diff > 5:
                impact["warnings"].append(f"Large version jump ({version_diff})")
        
        # Recommendations
        if impact["risk_level"] == "high":
            impact["recommendations"].append("Consider monitoring closely after these changes")
            impact["recommendations"].append("Keep snapshot ID for potential rollback")
        
        return impact
    
    def get_field_changes(self, diff_result: Dict, field: str) -> Optional[Dict]:
        """Get changes for a specific field."""
        return diff_result.get("changes", {}).get(field)
    
    def has_significant_changes(self, diff_result: Dict) -> bool:
        """Check if diff contains significant changes."""
        summary = diff_result.get("summary", {})
        impact = diff_result.get("impact", {})
        
        return (
            summary.get("total_fields_changed", 0) > 2 or
            impact.get("risk_level") in ["medium", "high"] or
            len(impact.get("warnings", [])) > 0
        )
