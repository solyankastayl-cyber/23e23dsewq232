"""
PHASE 4.4 — Entry Quality Engine

Main orchestrator for entry quality scoring.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from .entry_quality_factors import ENTRY_QUALITY_FACTORS, FACTOR_WEIGHTS, FACTOR_DESCRIPTIONS
from .entry_quality_grader import EntryQualityGrader


class EntryQualityEngine:
    """
    Computes entry quality score separate from setup quality.
    
    Key distinction:
    - setup_quality = Is the idea good?
    - entry_quality = Is the timing good?
    """
    
    def __init__(self):
        self.grader = EntryQualityGrader()
        self._history: List[Dict] = []
    
    def evaluate(self, data: Dict) -> Dict:
        """
        Evaluate entry quality.
        
        Args:
            data: Full trade context including prediction, setup, entry_mode, 
                  execution_strategy, context
        
        Returns:
            Entry quality score with factors breakdown
        """
        factors = self._compute_factors(data)
        score = self._aggregate(factors)
        grade_info = self.grader.grade_with_description(score)
        reasons = self._build_reasons(factors)
        
        result = {
            "entry_quality_score": score,
            "entry_quality_grade": grade_info["grade"],
            "grade_description": grade_info["description"],
            "grade_recommendation": grade_info["recommendation"],
            "factors": factors,
            "reasons": reasons,
            "use_as_skip_filter": score < 0.45,
            "size_modifier": self._compute_size_modifier(score),
            "evaluated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Record in history
        self._history.append({
            "score": score,
            "grade": grade_info["grade"],
            "timestamp": result["evaluated_at"]
        })
        
        return result
    
    def _compute_factors(self, data: Dict) -> Dict:
        """Compute all quality factors."""
        setup = data.get("setup", {})
        ctx = data.get("context", {})
        entry_mode = data.get("entry_mode", {})
        strategy = data.get("execution_strategy", {})
        
        mode = entry_mode.get("entry_mode") if isinstance(entry_mode, dict) else entry_mode
        strat = strategy.get("execution_strategy") if isinstance(strategy, dict) else strategy
        
        entry = setup.get("entry", 0)
        trigger = ctx.get("trigger_level", entry)
        
        return {
            "trigger_distance_score": self._score_trigger_distance(entry, trigger),
            "extension_score": self._score_extension(ctx.get("extension_atr", 0)),
            "confirmation_score": self._score_confirmation(ctx.get("close_confirmation", False)),
            "retest_score": self._score_retest(ctx.get("retest_completed", False), mode),
            "ltf_alignment_score": self._score_ltf_alignment(ctx.get("ltf_alignment", "neutral")),
            "volatility_score": self._score_volatility(ctx.get("volatility_state", "normal")),
            "structure_acceptance_score": self._score_structure_acceptance(ctx.get("structure_acceptance", False)),
            "execution_suitability_score": self._score_execution_suitability(strat, ctx)
        }
    
    def _aggregate(self, factors: Dict) -> float:
        """Compute weighted aggregate score."""
        score = 0.0
        for factor, value in factors.items():
            weight = FACTOR_WEIGHTS.get(factor, 0.1)
            score += value * weight
        return round(max(0.0, min(score, 1.0)), 3)
    
    def _build_reasons(self, factors: Dict) -> List[str]:
        """Build list of negative reasons."""
        reasons = []
        
        if factors["extension_score"] < 0.5:
            reasons.append("entry_too_extended")
        if factors["confirmation_score"] < 0.5:
            reasons.append("confirmation_missing")
        if factors["retest_score"] < 0.5:
            reasons.append("retest_not_completed")
        if factors["ltf_alignment_score"] < 0.5:
            reasons.append("ltf_conflict")
        if factors["volatility_score"] < 0.5:
            reasons.append("hostile_volatility")
        if factors["structure_acceptance_score"] < 0.5:
            reasons.append("structure_not_accepted")
        if factors["trigger_distance_score"] < 0.5:
            reasons.append("entry_far_from_trigger")
        
        return reasons
    
    def _compute_size_modifier(self, score: float) -> float:
        """Compute position size modifier based on quality."""
        if score >= 0.85:
            return 1.1  # 110% size for excellent entries
        if score >= 0.70:
            return 1.0  # 100% size
        if score >= 0.55:
            return 0.75  # 75% size
        if score >= 0.40:
            return 0.5  # 50% size
        return 0.0  # Skip
    
    # === Individual Factor Scoring ===
    
    def _score_trigger_distance(self, entry: float, trigger: float) -> float:
        """Score based on distance from trigger level."""
        if entry is None or trigger is None or trigger == 0:
            return 0.5
        
        dist = abs(entry - trigger) / trigger
        if dist <= 0.002:
            return 1.0
        if dist <= 0.005:
            return 0.8
        if dist <= 0.01:
            return 0.6
        return 0.35
    
    def _score_extension(self, extension_atr: float) -> float:
        """Score based on price extension from trigger."""
        if extension_atr <= 0.5:
            return 1.0
        if extension_atr <= 1.0:
            return 0.8
        if extension_atr <= 1.5:
            return 0.55
        return 0.2
    
    def _score_confirmation(self, close_confirmation: bool) -> float:
        """Score based on close confirmation."""
        return 1.0 if close_confirmation else 0.35
    
    def _score_retest(self, retest_completed: bool, entry_mode: str) -> float:
        """Score based on retest completion."""
        if entry_mode in ["WAIT_RETEST", "WAIT_PULLBACK"] and not retest_completed:
            return 0.3
        return 1.0 if retest_completed else 0.7
    
    def _score_ltf_alignment(self, ltf_alignment: str) -> float:
        """Score based on lower timeframe alignment."""
        if ltf_alignment == "aligned":
            return 1.0
        if ltf_alignment == "neutral":
            return 0.65
        if ltf_alignment == "conflict":
            return 0.2
        return 0.5
    
    def _score_volatility(self, volatility_state: str) -> float:
        """Score based on volatility conditions."""
        if volatility_state == "normal":
            return 1.0
        if volatility_state == "elevated":
            return 0.7
        if volatility_state == "high":
            return 0.4
        if volatility_state == "extreme":
            return 0.2
        return 0.6
    
    def _score_structure_acceptance(self, structure_acceptance: bool) -> float:
        """Score based on structure acceptance."""
        return 1.0 if structure_acceptance else 0.3
    
    def _score_execution_suitability(self, strategy: str, ctx: Dict) -> float:
        """Score based on execution strategy suitability."""
        slippage_bps = ctx.get("expected_slippage_bps", 0)
        
        if strategy == "FULL_ENTRY_NOW" and slippage_bps > 15:
            return 0.35
        
        if strategy in ["WAIT_RETEST_FULL", "WAIT_PULLBACK_LIMIT"]:
            return 0.9
        
        if strategy == "PARTIAL_NOW_PARTIAL_RETEST":
            return 0.8
        
        return 0.7
    
    def get_factors_info(self) -> Dict:
        """Get information about all factors."""
        return {
            "factors": ENTRY_QUALITY_FACTORS,
            "weights": FACTOR_WEIGHTS,
            "descriptions": FACTOR_DESCRIPTIONS
        }
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """Get recent evaluation history."""
        return self._history[-limit:]
    
    def health_check(self) -> Dict:
        """Health check."""
        return {
            "ok": True,
            "module": "entry_quality_score",
            "version": "4.4",
            "factors_count": len(ENTRY_QUALITY_FACTORS),
            "history_count": len(self._history),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Singleton
_engine: Optional[EntryQualityEngine] = None


def get_entry_quality_engine() -> EntryQualityEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = EntryQualityEngine()
    return _engine
