"""
PHASE 4.7.2 — LTF Structure Engine

Evaluates lower timeframe micro structure.
"""

from typing import Dict


class LTFStructureEngine:
    """
    Evaluates LTF micro structure for entry timing.
    
    Determines:
    - Micro phase (impulse/pullback/breakout/rejection/chop)
    - Pullback readiness
    - Structure strength
    """
    
    def evaluate(self, data: Dict) -> Dict:
        """
        Evaluate LTF structure.
        
        Args:
            data: LTF input with structure field
        
        Returns:
            Structure context
        """
        s = data.get("structure", {})
        
        micro_phase = s.get("micro_phase", "chop")
        
        # Check if pullback is ready for entry
        pullback_ready = (
            s.get("retest_completed", False) and
            s.get("acceptance", False)
        )
        
        # Calculate structure strength
        structure_strength = (
            s.get("hh_count", 0) * 0.20 +
            s.get("hl_count", 0) * 0.20 +
            s.get("bos", 0) * 0.25 -
            s.get("lh_count", 0) * 0.15 -
            s.get("ll_count", 0) * 0.15 -
            s.get("choch", 0) * 0.20
        )
        
        return {
            "micro_phase": micro_phase,
            "pullback_ready": pullback_ready,
            "structure_strength": round(max(structure_strength, 0), 3),
            "acceptance": s.get("acceptance", False),
            "retest_completed": s.get("retest_completed", False)
        }
