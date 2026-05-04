"""
PHASE 4.7.2 — LTF Refinement Engine

Main LTF engine that combines all LTF components.
Provides timing confirmation/rejection for entry.
"""

from typing import Dict, Optional, List
from datetime import datetime, timezone

from .ltf_structure_engine import LTFStructureEngine
from .ltf_confirmation_engine import LTFConfirmationEngine
from .ltf_conflict_engine import LTFConflictEngine
from .ltf_timing_engine import LTFTimingEngine


class LTFRefinementEngine:
    """
    Lower Timeframe Refinement Engine.
    
    Answers: "Is now the right time to enter?"
    
    Does NOT:
    - Override HTF bias
    - Replace Prediction direction
    - Build targets/stops
    
    Role: timing refinement only
    """
    
    def __init__(self):
        self.structure_engine = LTFStructureEngine()
        self.confirmation_engine = LTFConfirmationEngine()
        self.conflict_engine = LTFConflictEngine()
        self.timing_engine = LTFTimingEngine()
    
    def analyze(self, data: Dict) -> Dict:
        """
        Analyze LTF for entry timing.
        
        Args:
            data: LTF input with structure, trigger, momentum, volatility, quality
        
        Returns:
            LTF analysis with alignment, timing score, confirmation, conflict
        """
        # Step 1: Evaluate structure
        structure_ctx = self.structure_engine.evaluate(data)
        
        # Step 2: Check confirmation
        trigger = data.get("trigger", {})
        momentum = data.get("momentum", {})
        
        confirmation_ctx = self.confirmation_engine.compute(
            structure_ctx=structure_ctx,
            trigger=trigger,
            momentum=momentum
        )
        
        # Step 3: Check conflicts
        volatility = data.get("volatility", {})
        quality = data.get("quality", {})
        
        conflict_ctx = self.conflict_engine.compute(
            trigger=trigger,
            momentum=momentum,
            volatility=volatility,
            quality=quality
        )
        
        # Step 4: Compute timing score
        timing_score = self.timing_engine.compute(
            structure_ctx=structure_ctx,
            confirmation_ctx=confirmation_ctx,
            conflict_ctx=conflict_ctx,
            volatility=volatility,
            quality=quality
        )
        
        # Determine alignment
        alignment = "neutral"
        if conflict_ctx["ltf_conflict"]:
            alignment = "conflict"
        elif confirmation_ctx["ltf_confirmation"] and timing_score > 0.65:
            alignment = "aligned"
        
        # Determine entry type
        entry_type = structure_ctx["micro_phase"]
        if entry_type not in ["impulse", "pullback", "breakout"]:
            entry_type = "confirmation"
        
        # Collect all reasons
        reasons: List[str] = []
        reasons.extend(confirmation_ctx["reasons"])
        reasons.extend(conflict_ctx["reasons"])
        
        return {
            "ltf_alignment": alignment,
            "ltf_timing_score": timing_score,
            "ltf_entry_type": entry_type,
            "ltf_confirmation": confirmation_ctx["ltf_confirmation"],
            "ltf_conflict": conflict_ctx["ltf_conflict"],
            "micro_phase": structure_ctx["micro_phase"],
            "pullback_ready": structure_ctx["pullback_ready"],
            "reasons": reasons,
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }
    
    def generate_mock_input(self, scenario: str = "aligned") -> Dict:
        """Generate mock LTF input for testing."""
        scenarios = {
            "aligned": {
                "structure": {
                    "micro_phase": "pullback",
                    "hh_count": 2, "hl_count": 2,
                    "lh_count": 0, "ll_count": 0,
                    "bos": 1, "choch": 0,
                    "retest_completed": True,
                    "acceptance": True
                },
                "trigger": {
                    "entry_level": 62410,
                    "close_above_trigger": True,
                    "trigger_touched": True,
                    "trigger_rejected": False
                },
                "momentum": {
                    "impulse_strength": 0.72,
                    "momentum_exhausted": False,
                    "breakout_strength": 0.75
                },
                "volatility": {
                    "volatility_state": "normal",
                    "extension_atr": 0.6,
                    "wick_rejection": False
                },
                "quality": {"noise_score": 0.15, "conflict_score": 0.12}
            },
            "conflict": {
                "structure": {
                    "micro_phase": "rejection",
                    "hh_count": 1, "hl_count": 1,
                    "lh_count": 2, "ll_count": 1,
                    "bos": 0, "choch": 1,
                    "retest_completed": False,
                    "acceptance": False
                },
                "trigger": {
                    "entry_level": 62410,
                    "close_above_trigger": False,
                    "trigger_touched": True,
                    "trigger_rejected": True
                },
                "momentum": {
                    "impulse_strength": 0.35,
                    "momentum_exhausted": True,
                    "breakout_strength": 0.30
                },
                "volatility": {
                    "volatility_state": "high",
                    "extension_atr": 1.8,
                    "wick_rejection": True
                },
                "quality": {"noise_score": 0.45, "conflict_score": 0.55}
            },
            "neutral": {
                "structure": {
                    "micro_phase": "chop",
                    "hh_count": 1, "hl_count": 1,
                    "lh_count": 1, "ll_count": 1,
                    "bos": 0, "choch": 0,
                    "retest_completed": False,
                    "acceptance": False
                },
                "trigger": {
                    "entry_level": 62410,
                    "close_above_trigger": False,
                    "trigger_touched": False,
                    "trigger_rejected": False
                },
                "momentum": {
                    "impulse_strength": 0.50,
                    "momentum_exhausted": False,
                    "breakout_strength": 0.50
                },
                "volatility": {
                    "volatility_state": "elevated",
                    "extension_atr": 1.0,
                    "wick_rejection": False
                },
                "quality": {"noise_score": 0.30, "conflict_score": 0.25}
            }
        }
        return scenarios.get(scenario, scenarios["aligned"])
    
    def health_check(self) -> Dict:
        """Health check."""
        return {
            "ok": True,
            "module": "ltf_refinement_engine",
            "version": "4.7.2",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Singleton
_ltf_engine: Optional[LTFRefinementEngine] = None


def get_ltf_engine() -> LTFRefinementEngine:
    """Get singleton LTF engine."""
    global _ltf_engine
    if _ltf_engine is None:
        _ltf_engine = LTFRefinementEngine()
    return _ltf_engine
