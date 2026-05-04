"""
Entry Mode Query Service - Read-only queries for AF4 data
"""
from typing import List, Dict, Any

from .entry_mode_models import EntryModeSummary


class EntryModeQueryService:
    """Service for querying entry mode data."""
    
    def summarize(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build summary from evaluations."""
        verdicts = [e.get("verdict", "UNKNOWN") for e in evaluations]
        
        return {
            "strong": sum(1 for v in verdicts if v == "STRONG_ENTRY_MODE"),
            "weak": sum(1 for v in verdicts if v == "WEAK_ENTRY_MODE"),
            "unstable": sum(1 for v in verdicts if v == "UNSTABLE_ENTRY_MODE"),
            "broken": sum(1 for v in verdicts if v == "BROKEN_ENTRY_MODE"),
            "total_modes": len(evaluations),
        }
    
    def get_broken_modes(self, evaluations: List[Dict[str, Any]]) -> List[str]:
        """Get list of broken entry modes."""
        return [e["entry_mode"] for e in evaluations if e.get("verdict") == "BROKEN_ENTRY_MODE"]
    
    def get_strong_modes(self, evaluations: List[Dict[str, Any]]) -> List[str]:
        """Get list of strong entry modes."""
        return [e["entry_mode"] for e in evaluations if e.get("verdict") == "STRONG_ENTRY_MODE"]
    
    def get_urgent_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get only urgent actions."""
        return [a for a in actions if a.get("urgent", False)]
    
    def get_actions_by_type(self, actions: List[Dict[str, Any]], action_type: str) -> List[Dict[str, Any]]:
        """Get actions filtered by type."""
        return [a for a in actions if a.get("action") == action_type]
