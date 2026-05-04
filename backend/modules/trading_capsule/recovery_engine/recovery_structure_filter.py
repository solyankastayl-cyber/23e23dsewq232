"""
Recovery Structure Filter
=========================

Structure filter for Recovery Engine (PHASE 1.4)
"""

from typing import Dict, List, Optional, Any

from .recovery_types import StructureFilterResult


class RecoveryStructureFilter:
    """
    Filters recovery based on market structure.
    
    Recovery is only allowed when market structure
    supports mean reversion thesis.
    """
    
    def __init__(self):
        pass
    
    def check_structure(
        self,
        support_holding: bool = True,
        range_boundary_valid: bool = True,
        structure_broken: bool = False,
        trend_acceleration: bool = False,
        liquidity_cascade: bool = False,
        vwap_distance_pct: Optional[float] = None
    ) -> StructureFilterResult:
        """
        Check if market structure supports recovery.
        
        Args:
            support_holding: Is support level holding
            range_boundary_valid: Is range structure valid
            structure_broken: Has structure been broken
            trend_acceleration: Is trend accelerating
            liquidity_cascade: Is there liquidity cascade
            vwap_distance_pct: Distance from VWAP in %
        """
        
        notes = []
        deny_reasons = []
        
        # Check structure break
        if structure_broken:
            deny_reasons.append("Structure broken")
            notes.append("Market structure invalidated - recovery denied")
        
        # Check trend acceleration
        if trend_acceleration:
            deny_reasons.append("Trend acceleration detected")
            notes.append("Price accelerating away - recovery too risky")
        
        # Check liquidity cascade
        if liquidity_cascade:
            deny_reasons.append("Liquidity cascade in progress")
            notes.append("Liquidity sweep ongoing - wait for stabilization")
        
        # Check support
        if not support_holding:
            deny_reasons.append("Support not holding")
            notes.append("Key support level broken")
        
        # Check range validity
        if not range_boundary_valid:
            deny_reasons.append("Range boundary invalid")
            notes.append("Range structure no longer valid")
        
        # Check VWAP distance
        if vwap_distance_pct is not None:
            if abs(vwap_distance_pct) > 2.0:
                notes.append(f"Far from VWAP ({vwap_distance_pct:.1f}%) - reversion less likely")
                if abs(vwap_distance_pct) > 3.0:
                    deny_reasons.append("Too far from VWAP")
        
        # Determine if structure is intact
        structure_intact = len(deny_reasons) == 0
        
        # Build reason string
        if deny_reasons:
            reason = "; ".join(deny_reasons)
        else:
            reason = "Structure intact - recovery allowed"
            notes.append("Support holding, range valid, no structure break")
        
        return StructureFilterResult(
            allowed=structure_intact,
            structure_intact=not structure_broken,
            support_holding=support_holding,
            range_valid=range_boundary_valid,
            reason=reason,
            notes=notes
        )
    
    def get_structure_requirements(self) -> Dict[str, Any]:
        """Get structure requirements for recovery"""
        return {
            "required": {
                "support_holding": "Support level must be holding",
                "range_boundary_valid": "Range structure must be intact",
                "no_structure_break": "No recent structure break"
            },
            "forbidden": {
                "trend_acceleration": "Price accelerating in trend direction",
                "liquidity_cascade": "Active liquidity sweep/cascade",
                "vwap_extreme": "Price > 3% from VWAP"
            },
            "indicators": [
                "Swing low/high holding",
                "Range boundaries respected",
                "VWAP proximity",
                "Volume profile support"
            ]
        }


# Global singleton
recovery_structure_filter = RecoveryStructureFilter()
