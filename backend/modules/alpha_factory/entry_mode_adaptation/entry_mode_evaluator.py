"""
Entry Mode Evaluator - Evaluates entry modes and assigns verdicts
"""
from typing import List, Dict, Any, Tuple

from .entry_mode_models import EntryModeEvaluation


class EntryModeEvaluator:
    """
    Evaluates entry modes based on their metrics and assigns verdicts:
    - STRONG_ENTRY_MODE: Confirmed working well
    - WEAK_ENTRY_MODE: Some edge but not convincing
    - UNSTABLE_ENTRY_MODE: Insufficient data or unstable performance
    - BROKEN_ENTRY_MODE: No longer working, should be disabled
    """
    
    # Thresholds
    MIN_SAMPLE = 3  # Minimum trades for reliable verdict
    
    PF_STRONG = 1.5
    PF_BROKEN = 1.05
    
    WRONG_EARLY_LOW = 0.12
    WRONG_EARLY_HIGH = 0.25
    
    STABILITY_STRONG = 0.65
    STABILITY_UNSTABLE = 0.40
    
    def evaluate(self, metrics_items: List[Dict[str, Any]]) -> List[EntryModeEvaluation]:
        """Evaluate all entry modes and return verdicts."""
        evaluations = []
        
        for m in metrics_items:
            verdict, confidence, reasons, quality_score, risk_score = self._evaluate_one(m)
            
            evaluations.append(EntryModeEvaluation(
                entry_mode=m["entry_mode"],
                verdict=verdict,
                confidence=confidence,
                reasons=reasons,
                quality_score=quality_score,
                risk_score=risk_score,
            ))
        
        return evaluations
    
    def _evaluate_one(self, m: Dict[str, Any]) -> Tuple[str, float, List[str], float, float]:
        """Evaluate a single entry mode."""
        reasons = []
        quality_score = 0.0
        risk_score = 0.0
        
        # Extract metrics
        trades = int(m.get("trades", 0) or 0)
        pf = m.get("profit_factor")
        expectancy = float(m.get("expectancy", 0) or 0)
        win_rate = float(m.get("win_rate", 0) or 0)
        wrong_early_rate = float(m.get("wrong_early_rate", 0) or 0)
        expired_rate = float(m.get("expired_rate", 0) or 0)
        stability = float(m.get("stability", 0) or 0)
        avg_rr = float(m.get("avg_rr", 0) or 0)
        
        # Check sample size
        if trades < self.MIN_SAMPLE:
            reasons.append("insufficient_sample_size")
            return "UNSTABLE_ENTRY_MODE", 0.35, reasons, 0.0, 0.5
        
        # Quality scoring
        if pf is not None and pf > self.PF_STRONG:
            quality_score += 0.3
            reasons.append("pf_strong")
        elif pf is not None and pf > 1.2:
            quality_score += 0.15
            reasons.append("pf_moderate")
        elif pf is not None and pf < self.PF_BROKEN:
            quality_score -= 0.25
            reasons.append("pf_below_one")
        
        if expectancy > 30:
            quality_score += 0.25
            reasons.append("expectancy_strong")
        elif expectancy > 0:
            quality_score += 0.10
            reasons.append("expectancy_positive")
        elif expectancy < -20:
            quality_score -= 0.20
            reasons.append("expectancy_negative")
        
        if win_rate > 0.58:
            quality_score += 0.15
            reasons.append("win_rate_strong")
        elif win_rate < 0.40:
            quality_score -= 0.10
            reasons.append("win_rate_poor")
        
        if avg_rr > 2.0:
            quality_score += 0.10
            reasons.append("avg_rr_excellent")
        
        # Risk scoring
        if wrong_early_rate > self.WRONG_EARLY_HIGH:
            risk_score += 0.35
            reasons.append("wrong_early_high")
        elif wrong_early_rate > self.WRONG_EARLY_LOW:
            risk_score += 0.15
            reasons.append("wrong_early_moderate")
        else:
            reasons.append("wrong_early_low")
        
        if expired_rate > 0.25:
            risk_score += 0.20
            reasons.append("expired_rate_high")
        elif expired_rate > 0.15:
            risk_score += 0.10
        
        if stability < self.STABILITY_UNSTABLE:
            risk_score += 0.25
            reasons.append("stability_low")
        elif stability > self.STABILITY_STRONG:
            quality_score += 0.15
            reasons.append("stability_strong")
        
        # Determine verdict
        verdict, confidence = self._resolve_verdict(
            quality_score=quality_score,
            risk_score=risk_score,
            pf=pf,
            expectancy=expectancy,
            wrong_early_rate=wrong_early_rate,
            stability=stability,
            reasons=reasons
        )
        
        return verdict, confidence, reasons, round(quality_score, 4), round(risk_score, 4)
    
    def _resolve_verdict(
        self,
        quality_score: float,
        risk_score: float,
        pf: float | None,
        expectancy: float,
        wrong_early_rate: float,
        stability: float,
        reasons: List[str]
    ) -> Tuple[str, float]:
        """Resolve final verdict based on scores."""
        
        # STRONG_ENTRY_MODE
        if (quality_score >= 0.50 
            and risk_score < 0.30 
            and pf is not None and pf > self.PF_STRONG
            and expectancy > 0
            and wrong_early_rate < self.WRONG_EARLY_LOW
            and stability > self.STABILITY_STRONG):
            return "STRONG_ENTRY_MODE", 0.85
        
        # BROKEN_ENTRY_MODE
        if (quality_score < 0.0 
            or (pf is not None and pf < self.PF_BROKEN)
            or expectancy < -10
            or wrong_early_rate > self.WRONG_EARLY_HIGH):
            if "entry_mode_broken" not in reasons:
                reasons.append("entry_mode_broken")
            return "BROKEN_ENTRY_MODE", 0.82
        
        # UNSTABLE_ENTRY_MODE
        if risk_score > 0.40 or stability < self.STABILITY_UNSTABLE:
            return "UNSTABLE_ENTRY_MODE", 0.65
        
        # WEAK_ENTRY_MODE (default)
        return "WEAK_ENTRY_MODE", 0.58
