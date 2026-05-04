"""
PHASE 4.7.2 — LTF Confirmation Engine

Checks for entry confirmation signals on LTF.
"""

from typing import Dict, List


class LTFConfirmationEngine:
    """
    Checks for LTF entry confirmation.
    
    Looks for:
    - Close above/below trigger
    - Retest completion
    - Acceptance confirmation
    - Breakout strength
    """
    
    def compute(
        self,
        structure_ctx: Dict,
        trigger: Dict,
        momentum: Dict
    ) -> Dict:
        """
        Check for entry confirmation.
        
        Returns:
            Confirmation status and reasons
        """
        reasons: List[str] = []
        confirmation = False
        
        # Check trigger conditions
        if trigger.get("close_above_trigger", False):
            reasons.append("close_above_trigger")
        
        # Check structure conditions
        if structure_ctx.get("retest_completed", False):
            reasons.append("retest_completed")
        
        if structure_ctx.get("acceptance", False):
            reasons.append("acceptance_confirmed")
        
        # Check momentum conditions
        if momentum.get("breakout_strength", 0) > 0.6:
            reasons.append("breakout_strength_good")
        
        # Confirmation requires close + acceptance
        if (
            trigger.get("close_above_trigger", False) and
            structure_ctx.get("acceptance", False)
        ):
            confirmation = True
        
        # Alternative: retest completed with acceptance
        if (
            structure_ctx.get("retest_completed", False) and
            structure_ctx.get("acceptance", False)
        ):
            confirmation = True
        
        return {
            "ltf_confirmation": confirmation,
            "reasons": reasons
        }
