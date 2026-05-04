"""
PHASE 4.7.1 — HTF Structure Engine

Evaluates higher timeframe structure (HH/HL/LH/LL, BOS, CHoCH).
"""

from typing import Dict


class HTFStructureEngine:
    """
    Evaluates HTF market structure.
    
    Determines:
    - Market phase (trend/range/transition/distribution)
    - Bullish/bearish structure score
    - Range and compression metrics
    """
    
    def evaluate(self, data: Dict) -> Dict:
        """
        Evaluate HTF structure.
        
        Args:
            data: Input with structure field containing HH/HL counts, BOS, etc.
        
        Returns:
            Structure context with phase and scores
        """
        s = data.get("structure", {})
        
        market_phase = s.get("market_phase", "transition")
        
        # Bullish structure score
        bullish_structure_score = (
            s.get("hh_count", 0) * 0.25 +
            s.get("hl_count", 0) * 0.25 +
            s.get("bos", 0) * 0.30 -
            s.get("lh_count", 0) * 0.15 -
            s.get("ll_count", 0) * 0.15 -
            s.get("choch", 0) * 0.20
        )
        
        # Bearish structure score
        bearish_structure_score = (
            s.get("lh_count", 0) * 0.25 +
            s.get("ll_count", 0) * 0.25 +
            s.get("bos", 0) * 0.10 -
            s.get("hh_count", 0) * 0.15 -
            s.get("hl_count", 0) * 0.15
        )
        
        return {
            "market_phase": market_phase,
            "bullish_structure_score": round(max(bullish_structure_score, 0), 3),
            "bearish_structure_score": round(max(bearish_structure_score, 0), 3),
            "range_score": s.get("range_score", 0),
            "compression_score": s.get("compression_score", 0)
        }
