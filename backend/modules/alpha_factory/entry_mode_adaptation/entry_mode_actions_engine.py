"""
Entry Mode Actions Engine - Generates actions from evaluations
"""
from typing import List, Dict, Any

from .entry_mode_models import EntryModeAction


class EntryModeActionsEngine:
    """
    Generates actions based on entry mode evaluations.
    
    Actions:
    - UPGRADE_ENTRY_MODE: Increase usage/allocation for confirmed modes
    - DOWNGRADE_ENTRY_MODE: Reduce usage for decaying modes
    - DISABLE_ENTRY_MODE: Disable broken modes entirely
    - INCREASE_THRESHOLD: Require higher confirmation for unstable modes
    - KEEP: Continue observing without changes
    """
    
    def build(self, evaluations: List[Dict[str, Any]]) -> List[EntryModeAction]:
        """Generate actions from evaluations."""
        actions = []
        
        for e in evaluations:
            verdict = e.get("verdict", "WEAK_ENTRY_MODE")
            mode = e.get("entry_mode", "UNKNOWN")
            confidence = float(e.get("confidence", 0.5))
            reasons = e.get("reasons", [])
            
            action = self._verdict_to_action(
                verdict=verdict,
                mode=mode,
                confidence=confidence,
                reasons=reasons
            )
            
            if action:
                actions.append(action)
        
        return actions
    
    def _verdict_to_action(
        self, 
        verdict: str, 
        mode: str, 
        confidence: float,
        reasons: List[str]
    ) -> EntryModeAction:
        """Convert verdict to action."""
        
        if verdict == "STRONG_ENTRY_MODE":
            return EntryModeAction(
                scope="entry_mode",
                scope_key=mode,
                action="UPGRADE_ENTRY_MODE",
                magnitude=0.15,
                reason="entry_mode_confirmed_live",
                urgent=False,
                requires_approval=False,
            )
        
        elif verdict == "WEAK_ENTRY_MODE":
            return EntryModeAction(
                scope="entry_mode",
                scope_key=mode,
                action="KEEP",
                magnitude=0.0,
                reason="entry_mode_weak_continue_observing",
                urgent=False,
                requires_approval=False,
            )
        
        elif verdict == "UNSTABLE_ENTRY_MODE":
            # Increase threshold - require more confirmation
            return EntryModeAction(
                scope="entry_mode",
                scope_key=mode,
                action="INCREASE_THRESHOLD",
                magnitude=0.15,
                reason="entry_mode_unstable_increase_confirmation",
                urgent=False,
                requires_approval=False,
            )
        
        elif verdict == "BROKEN_ENTRY_MODE":
            # Disable the entry mode
            urgent = "wrong_early_high" in reasons or "pf_below_one" in reasons
            return EntryModeAction(
                scope="entry_mode",
                scope_key=mode,
                action="DISABLE_ENTRY_MODE",
                magnitude=1.0,
                reason="entry_mode_broken_live",
                urgent=urgent,
                requires_approval=urgent,
            )
        
        # Default: keep observing
        return EntryModeAction(
            scope="entry_mode",
            scope_key=mode,
            action="KEEP",
            magnitude=0.0,
            reason="default_keep",
            urgent=False,
            requires_approval=False,
        )
