"""
PHASE 4.7.2 — LTF Conflict Engine

Detects conditions where entry should be avoided.
"""

from typing import Dict, List


class LTFConflictEngine:
    """
    Detects LTF conflicts that prevent entry.
    
    Conflicts:
    - Trigger rejection
    - Momentum exhaustion
    - Extension too high
    - Wick rejection
    - Hostile volatility
    """
    
    def compute(
        self,
        trigger: Dict,
        momentum: Dict,
        volatility: Dict,
        quality: Dict
    ) -> Dict:
        """
        Detect LTF conflicts.
        
        Returns:
            Conflict status and reasons
        """
        reasons: List[str] = []
        conflict = False
        
        # Check trigger rejection
        if trigger.get("trigger_rejected", False):
            conflict = True
            reasons.append("trigger_rejected")
        
        # Check momentum exhaustion
        if momentum.get("momentum_exhausted", False):
            conflict = True
            reasons.append("momentum_exhausted")
        
        # Check extension
        extension = volatility.get("extension_atr", 0)
        if extension > 1.5:
            conflict = True
            reasons.append("entry_too_extended")
        
        # Check wick rejection
        if volatility.get("wick_rejection", False):
            conflict = True
            reasons.append("wick_rejection")
        
        # Check volatility state
        vol_state = volatility.get("volatility_state", "normal")
        if vol_state in ["high", "extreme"]:
            conflict = True
            reasons.append("hostile_volatility")
        
        # Check quality conflict score
        if quality.get("conflict_score", 0) > 0.45:
            conflict = True
            reasons.append("high_local_conflict")
        
        return {
            "ltf_conflict": conflict,
            "reasons": reasons
        }
