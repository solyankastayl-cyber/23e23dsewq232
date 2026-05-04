"""
AF1 - Alpha Evaluator
=====================
Evaluates metrics and produces verdicts: STRONG_EDGE, WEAK_EDGE, UNSTABLE_EDGE, NO_EDGE.
"""

from typing import List, Tuple, Dict, Any
from .alpha_models import AlphaEvaluation, utc_now


class AlphaEvaluator:
    """Evaluates alpha metrics and produces edge verdicts"""
    
    # Thresholds
    MIN_SAMPLE = 8          # Minimum trades for reliable verdict
    MIN_SAMPLE_WEAK = 5     # Minimum for any verdict
    
    PF_STRONG = 1.5         # Profit factor for strong edge
    PF_WEAK = 1.0           # Minimum acceptable PF
    
    STABILITY_STRONG = 0.65
    STABILITY_WEAK = 0.50
    
    WRONG_EARLY_THRESHOLD = 0.15  # Max acceptable wrong_early rate

    def evaluate(self, metrics_items: List[Dict[str, Any]]) -> List[AlphaEvaluation]:
        """Evaluate all metrics and return verdicts"""
        evaluations = []
        
        for m in metrics_items:
            verdict, confidence, reasons = self._evaluate_one(m)
            sample_size = int(m.get("trades", 0) or 0)
            
            evaluations.append(
                AlphaEvaluation(
                    scope=m["scope"],
                    scope_key=m["scope_key"],
                    verdict=verdict,
                    confidence=confidence,
                    reasons=reasons,
                    sample_size=sample_size,
                    is_actionable=sample_size >= self.MIN_SAMPLE_WEAK,
                    created_at=utc_now(),
                )
            )
            
        return evaluations

    def _evaluate_one(self, m: Dict[str, Any]) -> Tuple[str, float, List[str]]:
        """Evaluate single metric and return (verdict, confidence, reasons)"""
        reasons = []
        
        # Extract values
        trades = int(m.get("trades", 0) or 0)
        pf = m.get("profit_factor")
        expectancy = float(m.get("expectancy", 0) or 0)
        stability = float(m.get("stability", 0) or 0)
        wrong_early = float(m.get("wrong_early_rate", 0) or 0)
        win_rate = float(m.get("win_rate", 0) or 0)

        # Low sample - immediately return unstable
        if trades < self.MIN_SAMPLE_WEAK:
            reasons.append("very_low_sample")
            return "UNSTABLE_EDGE", 0.25, reasons
            
        if trades < self.MIN_SAMPLE:
            reasons.append("low_sample")

        # Build reasons list for positive signals
        if pf is not None and pf > self.PF_STRONG:
            reasons.append("pf_above_threshold")
        if expectancy > 0:
            reasons.append("expectancy_positive")
        if wrong_early < self.WRONG_EARLY_THRESHOLD:
            reasons.append("wrong_early_low")
        if stability > self.STABILITY_STRONG:
            reasons.append("stability_high")
        if win_rate > 0.55:
            reasons.append("win_rate_above_average")

        # === STRONG_EDGE ===
        if (
            trades >= self.MIN_SAMPLE
            and pf is not None and pf > self.PF_STRONG
            and expectancy > 0
            and wrong_early < self.WRONG_EARLY_THRESHOLD
            and stability > self.STABILITY_STRONG
        ):
            conf = min(0.95, 0.55 + (trades / 100))
            return "STRONG_EDGE", round(conf, 4), reasons

        # === NO_EDGE ===
        if (pf is not None and pf <= self.PF_WEAK) or expectancy <= 0:
            reasons.append("edge_not_positive")
            conf = min(0.90, 0.45 + (trades / 120))
            return "NO_EDGE", round(conf, 4), reasons

        # === UNSTABLE_EDGE ===
        if stability < self.STABILITY_WEAK or wrong_early > 0.22:
            reasons.append("stability_low_or_timing_bad")
            return "UNSTABLE_EDGE", 0.62, reasons

        # === WEAK_EDGE ===
        if win_rate > 0.5 and expectancy > 0:
            reasons.append("edge_present_but_not_strong")
            return "WEAK_EDGE", 0.58, reasons

        # Default to unstable
        return "UNSTABLE_EDGE", 0.50, reasons

    def get_verdict_priority(self, verdict: str) -> int:
        """Get priority for sorting (lower = more urgent)"""
        priorities = {
            "NO_EDGE": 1,
            "UNSTABLE_EDGE": 2,
            "WEAK_EDGE": 3,
            "STRONG_EDGE": 4,
        }
        return priorities.get(verdict, 5)
