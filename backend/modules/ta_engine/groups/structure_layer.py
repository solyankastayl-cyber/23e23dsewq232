"""
TA Engine - Structure Layer (Group 1)
Market structure analysis: HH/HL/LH/LL, BOS, CHOCH, trend.

THIS IS THE FOUNDATION - everything else builds on this.
"""

from typing import List, Dict, Optional
from ..groups.base import (
    BaseLayer, GroupResult, Finding, Window, Geometry, Relevance, RenderData,
    GROUP_STRUCTURE, BIAS_BULLISH, BIAS_BEARISH, BIAS_NEUTRAL
)
from ..core.chart_basis import ChartBasis, Pivot, Swing


class StructureLayer(BaseLayer):
    """
    Analyzes market structure.
    
    Detects:
    - HH (Higher High), HL (Higher Low)
    - LH (Lower High), LL (Lower Low)
    - BOS (Break of Structure)
    - CHOCH (Change of Character)
    - Overall trend state
    """
    
    GROUP_NAME = GROUP_STRUCTURE
    
    def run(self, basis: ChartBasis) -> GroupResult:
        """Run structure analysis"""
        findings = []
        
        if len(basis.pivots) < 4:
            return self._create_result(findings, {
                "state": "undefined",
                "trend": "unknown",
                "reason": "insufficient_pivots",
            })
        
        # Analyze structure
        structure = self._analyze_structure(basis)
        
        # Create structure finding
        finding = Finding(
            type=structure["state"],
            bias=self._state_to_bias(structure["state"]),
            score=structure["strength"],
            confidence=structure["strength"] * 0.9,
            meta={
                "trend": structure["trend"],
                "last_bos": structure.get("last_bos"),
                "last_choch": structure.get("last_choch"),
                "swing_sequence": structure.get("swing_sequence", []),
            },
        )
        findings.append(finding)
        
        return self._create_result(findings, {
            "state": structure["state"],
            "trend": structure["trend"],
            "strength": structure["strength"],
        })
    
    def _analyze_structure(self, basis: ChartBasis) -> Dict:
        """Analyze market structure from pivots"""
        highs = [p for p in basis.pivots if p.type == "high"]
        lows = [p for p in basis.pivots if p.type == "low"]
        
        if len(highs) < 2 or len(lows) < 2:
            return {"state": "undefined", "trend": "unknown", "strength": 0.0}
        
        # Analyze swing sequence
        swing_seq = self._get_swing_sequence(highs, lows)
        
        # Count HH/HL vs LH/LL
        hh_count = swing_seq.count("HH")
        hl_count = swing_seq.count("HL")
        lh_count = swing_seq.count("LH")
        ll_count = swing_seq.count("LL")
        
        bullish_points = hh_count + hl_count
        bearish_points = lh_count + ll_count
        total = bullish_points + bearish_points
        
        if total == 0:
            return {"state": "ranging", "trend": "sideways", "strength": 0.5}
        
        bullish_ratio = bullish_points / total
        bearish_ratio = bearish_points / total
        
        # Determine state
        if bullish_ratio > 0.7:
            state = "bullish_trend"
            trend = "up"
            strength = bullish_ratio
        elif bearish_ratio > 0.7:
            state = "bearish_trend"
            trend = "down"
            strength = bearish_ratio
        elif bullish_ratio > 0.5:
            state = "bullish_transition"
            trend = "up_weak"
            strength = bullish_ratio * 0.8
        elif bearish_ratio > 0.5:
            state = "bearish_transition"
            trend = "down_weak"
            strength = bearish_ratio * 0.8
        else:
            state = "ranging"
            trend = "sideways"
            strength = 0.5
        
        # Detect BOS/CHOCH
        last_bos = self._detect_bos(highs, lows)
        last_choch = self._detect_choch(highs, lows, swing_seq)
        
        return {
            "state": state,
            "trend": trend,
            "strength": strength,
            "last_bos": last_bos,
            "last_choch": last_choch,
            "swing_sequence": swing_seq[-6:],  # Last 6 swings
        }
    
    def _get_swing_sequence(self, highs: List[Pivot], lows: List[Pivot]) -> List[str]:
        """Get sequence of HH/HL/LH/LL"""
        sequence = []
        
        # Compare consecutive highs
        for i in range(1, len(highs)):
            if highs[i].price > highs[i-1].price:
                sequence.append("HH")
            else:
                sequence.append("LH")
        
        # Compare consecutive lows
        for i in range(1, len(lows)):
            if lows[i].price > lows[i-1].price:
                sequence.append("HL")
            else:
                sequence.append("LL")
        
        return sequence
    
    def _detect_bos(self, highs: List[Pivot], lows: List[Pivot]) -> Optional[Dict]:
        """Detect Break of Structure"""
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        # Bullish BOS: price breaks above previous high
        last_high = highs[-1]
        prev_high = highs[-2] if len(highs) >= 2 else None
        
        if prev_high and last_high.price > prev_high.price * 1.005:  # 0.5% above
            return {
                "type": "bullish_bos",
                "level": prev_high.price,
                "time": last_high.time,
            }
        
        # Bearish BOS: price breaks below previous low
        last_low = lows[-1]
        prev_low = lows[-2] if len(lows) >= 2 else None
        
        if prev_low and last_low.price < prev_low.price * 0.995:  # 0.5% below
            return {
                "type": "bearish_bos",
                "level": prev_low.price,
                "time": last_low.time,
            }
        
        return None
    
    def _detect_choch(self, highs: List[Pivot], lows: List[Pivot], seq: List[str]) -> Optional[Dict]:
        """Detect Change of Character (trend reversal signal)"""
        if len(seq) < 4:
            return None
        
        recent = seq[-4:]
        
        # Bullish CHOCH: was making LL, now made HL
        if "LL" in recent[:2] and "HL" in recent[2:]:
            return {"type": "bullish_choch", "signal": "potential_reversal_up"}
        
        # Bearish CHOCH: was making HH, now made LH
        if "HH" in recent[:2] and "LH" in recent[2:]:
            return {"type": "bearish_choch", "signal": "potential_reversal_down"}
        
        return None
    
    def _state_to_bias(self, state: str) -> str:
        """Convert state to bias"""
        if "bullish" in state:
            return BIAS_BULLISH
        elif "bearish" in state:
            return BIAS_BEARISH
        return BIAS_NEUTRAL


# Singleton
_structure_layer = None

def get_structure_layer() -> StructureLayer:
    global _structure_layer
    if _structure_layer is None:
        _structure_layer = StructureLayer()
    return _structure_layer
