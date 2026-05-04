"""
PHASE 4.7.3 — MTF Alignment Engine

Combines HTF + MTF + LTF into unified alignment decision.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone


class MTFAlignmentEngine:
    """
    Multi-Timeframe Alignment Engine.
    
    Combines:
    - HTF (1D): Permission layer
    - MTF (4H): Base signal
    - LTF (1H): Timing refinement
    
    Outputs alignment score and status.
    """
    
    def compute(
        self,
        htf: Dict,
        mtf: Dict,
        ltf: Dict
    ) -> Dict:
        """
        Compute MTF alignment.
        
        Args:
            htf: HTF analysis result
            mtf: MTF prediction (direction, confidence)
            ltf: LTF refinement result
        
        Returns:
            Alignment status and score
        """
        reasons: List[str] = []
        
        # Extract values
        htf_bias = htf.get("htf_bias", "neutral")
        htf_strength = htf.get("htf_strength", 0.5)
        htf_permission = htf.get("htf_permission", {})
        
        mtf_direction = mtf.get("direction", "").upper()
        mtf_confidence = mtf.get("confidence", 0.5)
        
        ltf_alignment = ltf.get("ltf_alignment", "neutral")
        ltf_timing = ltf.get("ltf_timing_score", 0.5)
        ltf_conflict = ltf.get("ltf_conflict", False)
        
        # Check HTF permission
        htf_allows = False
        if mtf_direction == "LONG":
            htf_allows = htf_permission.get("allow_long", False)
        elif mtf_direction == "SHORT":
            htf_allows = htf_permission.get("allow_short", False)
        
        # Check HTF alignment
        htf_aligned = False
        if htf_bias == "bullish" and mtf_direction == "LONG":
            htf_aligned = True
            reasons.append("htf_bullish_aligned")
        elif htf_bias == "bearish" and mtf_direction == "SHORT":
            htf_aligned = True
            reasons.append("htf_bearish_aligned")
        elif htf_bias == "neutral":
            htf_aligned = True
            reasons.append("htf_neutral")
        
        # Check for HTF conflict
        htf_conflict = False
        if htf_bias == "bullish" and mtf_direction == "SHORT" and htf_strength > 0.60:
            htf_conflict = True
            reasons.append("htf_conflict_short_vs_bullish")
        elif htf_bias == "bearish" and mtf_direction == "LONG" and htf_strength > 0.60:
            htf_conflict = True
            reasons.append("htf_conflict_long_vs_bearish")
        
        # Determine full alignment
        full_alignment = "partial"
        
        if htf_conflict or ltf_conflict:
            full_alignment = "conflict"
            reasons.append("timeframe_conflict")
        elif htf_aligned and ltf_alignment == "aligned" and htf_allows:
            full_alignment = "full"
            reasons.append("full_mtf_alignment")
        elif htf_allows and not ltf_conflict:
            full_alignment = "partial"
            reasons.append("partial_alignment")
        
        # Compute alignment score
        alignment_score = self._compute_score(
            htf_aligned=htf_aligned,
            htf_allows=htf_allows,
            htf_strength=htf_strength,
            mtf_confidence=mtf_confidence,
            ltf_alignment=ltf_alignment,
            ltf_timing=ltf_timing,
            htf_conflict=htf_conflict,
            ltf_conflict=ltf_conflict
        )
        
        return {
            "mtf_alignment": full_alignment,
            "alignment_score": alignment_score,
            "htf_aligned": htf_aligned,
            "htf_allows": htf_allows,
            "htf_conflict": htf_conflict,
            "ltf_aligned": ltf_alignment == "aligned",
            "ltf_conflict": ltf_conflict,
            "direction": mtf_direction,
            "reasons": reasons,
            "computed_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _compute_score(
        self,
        htf_aligned: bool,
        htf_allows: bool,
        htf_strength: float,
        mtf_confidence: float,
        ltf_alignment: str,
        ltf_timing: float,
        htf_conflict: bool,
        ltf_conflict: bool
    ) -> float:
        """Compute overall alignment score."""
        score = 0.0
        
        # HTF contribution (35%)
        if htf_aligned and htf_allows:
            score += htf_strength * 0.35
        elif htf_allows:
            score += 0.15
        
        # MTF contribution (35%)
        score += mtf_confidence * 0.35
        
        # LTF contribution (30%)
        if ltf_alignment == "aligned":
            score += ltf_timing * 0.30
        elif ltf_alignment == "neutral":
            score += ltf_timing * 0.15
        
        # Conflict penalties
        if htf_conflict:
            score *= 0.3
        
        if ltf_conflict:
            score *= 0.4
        
        return round(max(0.0, min(score, 1.0)), 3)
    
    def health_check(self) -> Dict:
        """Health check."""
        return {
            "ok": True,
            "module": "mtf_alignment_engine",
            "version": "4.7.3",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Singleton
_alignment_engine: Optional[MTFAlignmentEngine] = None


def get_mtf_alignment_engine() -> MTFAlignmentEngine:
    """Get singleton alignment engine."""
    global _alignment_engine
    if _alignment_engine is None:
        _alignment_engine = MTFAlignmentEngine()
    return _alignment_engine
