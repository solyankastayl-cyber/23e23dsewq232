"""
PHASE 4.7 — MTF Decision Engine

Main orchestrator that combines HTF + MTF + LTF into final entry decision.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from .htf_analyzer import HTFAnalyzer, get_htf_analyzer
from .ltf_refinement_engine import LTFRefinementEngine, get_ltf_engine
from .mtf_alignment_engine import MTFAlignmentEngine, get_mtf_alignment_engine


# Extended entry modes for MTF
MTF_ENTRY_MODES = [
    "ENTER_NOW",
    "ENTER_ON_CLOSE",
    "WAIT_RETEST",
    "WAIT_PULLBACK",
    "WAIT_CONFIRMATION",
    "SKIP_HTF_CONFLICT",
    "SKIP_LTF_CONFLICT",
    "WAIT_LTF_CONFIRMATION",
    "ENTER_HTF_PULLBACK",
    "ENTER_LTF_BREAKOUT",
    "ENTER_AGGRESSIVE"
]


class MTFDecisionEngine:
    """
    Multi-Timeframe Decision Engine.
    
    The final MTF layer that decides:
    - Should we enter?
    - How aggressive?
    - What mode?
    
    Pipeline:
    HTF (permission) + MTF (signal) + LTF (timing) → Entry Decision
    """
    
    def __init__(self):
        self.htf_analyzer = get_htf_analyzer()
        self.ltf_engine = get_ltf_engine()
        self.alignment_engine = get_mtf_alignment_engine()
        self._history: List[Dict] = []
    
    def decide(
        self,
        htf_data: Dict,
        mtf_data: Dict,
        ltf_data: Dict
    ) -> Dict:
        """
        Make MTF-aware entry decision.
        
        Args:
            htf_data: HTF input for analyzer
            mtf_data: MTF prediction (direction, confidence)
            ltf_data: LTF input for refinement
        
        Returns:
            Entry decision with mode, confidence, reasons
        """
        # Step 1: Analyze HTF
        htf = self.htf_analyzer.analyze(htf_data)
        
        # Step 2: Analyze LTF
        ltf = self.ltf_engine.analyze(ltf_data)
        
        # Step 3: Compute alignment
        alignment = self.alignment_engine.compute(htf, mtf_data, ltf)
        
        # Step 4: Make decision
        decision = self._build_decision(htf, mtf_data, ltf, alignment)
        
        # Record history
        self._history.append({
            "decision": decision["entry_mode"],
            "alignment": alignment["mtf_alignment"],
            "timestamp": decision["decided_at"]
        })
        
        return decision
    
    def _build_decision(
        self,
        htf: Dict,
        mtf: Dict,
        ltf: Dict,
        alignment: Dict
    ) -> Dict:
        """Build the final decision."""
        reasons: List[str] = []
        
        mtf_direction = mtf.get("direction", "").upper()
        mtf_confidence = mtf.get("confidence", 0.5)
        
        htf_bias = htf.get("htf_bias", "neutral")
        htf_strength = htf.get("htf_strength", 0.5)
        
        ltf_timing = ltf.get("ltf_timing_score", 0.5)
        ltf_alignment = ltf.get("ltf_alignment", "neutral")
        
        # === SKIP CONDITIONS ===
        
        # 1. HTF Conflict - Skip countertrend
        if alignment.get("htf_conflict", False):
            return self._result(
                mode="SKIP_HTF_CONFLICT",
                confidence=0.15,
                reasons=["htf_conflict", f"htf_{htf_bias}_vs_{mtf_direction.lower()}"],
                htf=htf, mtf=mtf, ltf=ltf, alignment=alignment
            )
        
        # 2. LTF Conflict - Skip bad timing
        if ltf.get("ltf_conflict", False):
            conflict_reasons = ltf.get("reasons", [])
            return self._result(
                mode="SKIP_LTF_CONFLICT",
                confidence=0.20,
                reasons=["ltf_conflict"] + conflict_reasons[:3],
                htf=htf, mtf=mtf, ltf=ltf, alignment=alignment
            )
        
        # === WAIT CONDITIONS ===
        
        # 3. LTF not aligned - Wait for confirmation
        if ltf_alignment != "aligned" and ltf_timing < 0.55:
            return self._result(
                mode="WAIT_LTF_CONFIRMATION",
                confidence=0.45,
                reasons=["ltf_not_ready", f"ltf_timing_{ltf_timing}"],
                htf=htf, mtf=mtf, ltf=ltf, alignment=alignment
            )
        
        # 4. Extension too high - Wait pullback
        extension = ltf.get("reasons", [])
        if "entry_too_extended" in extension:
            return self._result(
                mode="WAIT_PULLBACK",
                confidence=0.50,
                reasons=["extension_high", "wait_for_pullback"],
                htf=htf, mtf=mtf, ltf=ltf, alignment=alignment
            )
        
        # === ENTER CONDITIONS ===
        
        # 5. Perfect alignment - Enter aggressive
        if alignment.get("mtf_alignment") == "full" and alignment.get("alignment_score", 0) > 0.75:
            reasons.append("full_mtf_alignment")
            reasons.append(f"score_{alignment['alignment_score']}")
            
            return self._result(
                mode="ENTER_AGGRESSIVE",
                confidence=alignment["alignment_score"] * 1.1,
                reasons=reasons,
                htf=htf, mtf=mtf, ltf=ltf, alignment=alignment
            )
        
        # 6. HTF pullback entry
        if ltf.get("micro_phase") == "pullback" and ltf.get("pullback_ready", False):
            reasons.append("pullback_ready")
            reasons.append("retest_completed")
            
            return self._result(
                mode="ENTER_HTF_PULLBACK",
                confidence=ltf_timing * 0.9 + htf_strength * 0.1,
                reasons=reasons,
                htf=htf, mtf=mtf, ltf=ltf, alignment=alignment
            )
        
        # 7. LTF breakout entry
        if ltf.get("micro_phase") == "breakout" and ltf_alignment == "aligned":
            reasons.append("ltf_breakout_confirmed")
            
            return self._result(
                mode="ENTER_LTF_BREAKOUT",
                confidence=ltf_timing,
                reasons=reasons,
                htf=htf, mtf=mtf, ltf=ltf, alignment=alignment
            )
        
        # 8. Close confirmation needed
        if not ltf.get("ltf_confirmation", False):
            return self._result(
                mode="ENTER_ON_CLOSE",
                confidence=mtf_confidence * 0.85,
                reasons=["needs_close_confirmation"],
                htf=htf, mtf=mtf, ltf=ltf, alignment=alignment
            )
        
        # 9. Default - Enter now
        return self._result(
            mode="ENTER_NOW",
            confidence=alignment.get("alignment_score", mtf_confidence),
            reasons=["standard_entry"],
            htf=htf, mtf=mtf, ltf=ltf, alignment=alignment
        )
    
    def _result(
        self,
        mode: str,
        confidence: float,
        reasons: List[str],
        htf: Dict,
        mtf: Dict,
        ltf: Dict,
        alignment: Dict
    ) -> Dict:
        """Build result object."""
        confidence = round(max(0.0, min(confidence, 1.0)), 3)
        
        allows_entry = mode not in ["SKIP_HTF_CONFLICT", "SKIP_LTF_CONFLICT"]
        requires_wait = mode.startswith("WAIT_")
        
        return {
            "entry_mode": mode,
            "confidence": confidence,
            "allows_entry": allows_entry,
            "requires_wait": requires_wait,
            "reasons": reasons,
            # MTF context
            "mtf_alignment": alignment.get("mtf_alignment"),
            "alignment_score": alignment.get("alignment_score"),
            # HTF summary
            "htf_bias": htf.get("htf_bias"),
            "htf_strength": htf.get("htf_strength"),
            "htf_allows": alignment.get("htf_allows"),
            # LTF summary
            "ltf_alignment": ltf.get("ltf_alignment"),
            "ltf_timing_score": ltf.get("ltf_timing_score"),
            "ltf_entry_type": ltf.get("ltf_entry_type"),
            # Direction
            "direction": mtf.get("direction"),
            "mtf_confidence": mtf.get("confidence"),
            "decided_at": datetime.now(timezone.utc).isoformat()
        }
    
    def decide_with_mock(self, scenario: str = "aligned") -> Dict:
        """Run decision with mock data for testing."""
        scenarios = {
            "aligned": {
                "htf": "bullish_trend",
                "mtf": {"direction": "LONG", "confidence": 0.78},
                "ltf": "aligned"
            },
            "htf_conflict": {
                "htf": "bearish_trend",
                "mtf": {"direction": "LONG", "confidence": 0.75},
                "ltf": "aligned"
            },
            "ltf_conflict": {
                "htf": "bullish_trend",
                "mtf": {"direction": "LONG", "confidence": 0.80},
                "ltf": "conflict"
            },
            "wait_confirmation": {
                "htf": "bullish_trend",
                "mtf": {"direction": "LONG", "confidence": 0.70},
                "ltf": "neutral"
            }
        }
        
        config = scenarios.get(scenario, scenarios["aligned"])
        
        htf_data = self.htf_analyzer.generate_mock_input(config["htf"])
        ltf_data = self.ltf_engine.generate_mock_input(config["ltf"])
        mtf_data = config["mtf"]
        
        result = self.decide(htf_data, mtf_data, ltf_data)
        result["scenario"] = scenario
        
        return result
    
    def get_available_modes(self) -> List[str]:
        """Get all available MTF entry modes."""
        return MTF_ENTRY_MODES
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """Get recent decision history."""
        return self._history[-limit:]
    
    def get_stats(self) -> Dict:
        """Get decision statistics."""
        if not self._history:
            return {"total": 0, "by_mode": {}, "by_alignment": {}}
        
        total = len(self._history)
        by_mode: Dict[str, int] = {}
        by_alignment: Dict[str, int] = {}
        
        for record in self._history:
            mode = record.get("decision", "UNKNOWN")
            alignment = record.get("alignment", "UNKNOWN")
            
            by_mode[mode] = by_mode.get(mode, 0) + 1
            by_alignment[alignment] = by_alignment.get(alignment, 0) + 1
        
        return {
            "total": total,
            "by_mode": by_mode,
            "by_alignment": by_alignment
        }
    
    def health_check(self) -> Dict:
        """Health check."""
        return {
            "ok": True,
            "module": "mtf_decision_engine",
            "version": "4.7",
            "modes_count": len(MTF_ENTRY_MODES),
            "history_count": len(self._history),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Singleton
_decision_engine: Optional[MTFDecisionEngine] = None


def get_mtf_decision_engine() -> MTFDecisionEngine:
    """Get singleton decision engine."""
    global _decision_engine
    if _decision_engine is None:
        _decision_engine = MTFDecisionEngine()
    return _decision_engine
