"""
Alpha Validation Evaluator - Combined verdict logic
"""
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

from .alpha_validation_models import CombinedAlphaTruth
from .validation_weighting import ValidationWeighting


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AlphaValidationEvaluator:
    """
    Evaluates combined alpha (historical) + validation (live) metrics
    to produce verdicts:
    
    - STRONG_CONFIRMED_EDGE: Historical edge confirmed by live validation
    - STRONG_BUT_DECAYING: Historical edge exists but NOT confirmed live
    - WEAK_EDGE: Some edge present but not convincing
    - NO_EDGE: No edge detected in history or live
    """
    
    # Score thresholds for verdicts
    STRONG_CONFIRMED_THRESHOLD = 0.50
    WEAK_EDGE_THRESHOLD = 0.15
    NO_EDGE_THRESHOLD = 0.0
    
    def __init__(self):
        self.weighting = ValidationWeighting()
    
    def evaluate(
        self, 
        scope: str, 
        scope_key: str, 
        alpha_metrics: Dict[str, Any], 
        validation_metrics: Dict[str, Any]
    ) -> CombinedAlphaTruth:
        """
        Evaluate combined truth from alpha and validation metrics.
        """
        # Compute weighted scores
        weighted = self.weighting.score(alpha_metrics, validation_metrics)
        
        alpha_score = weighted["alpha_score"]
        validation_score = weighted["validation_score"]
        combined_score = weighted["combined_score"]
        reasons = weighted["reasons"]
        decay_detected = weighted["decay_detected"]
        decay_severity = weighted["decay_severity"]
        
        # Resolve verdict
        verdict, confidence = self._resolve_verdict(
            combined_score=combined_score,
            alpha_metrics=alpha_metrics,
            validation_metrics=validation_metrics,
            decay_detected=decay_detected,
            decay_severity=decay_severity,
            reasons=reasons
        )
        
        return CombinedAlphaTruth(
            scope=scope,
            scope_key=scope_key,
            alpha_metrics=alpha_metrics,
            validation_metrics=validation_metrics,
            combined_verdict=verdict,
            confidence=confidence,
            reasons=reasons,
            alpha_score=alpha_score,
            validation_score=validation_score,
            combined_score=combined_score,
            decay_detected=decay_detected,
            decay_severity=decay_severity,
            timestamp=utc_now(),
        )
    
    def _resolve_verdict(
        self,
        combined_score: float,
        alpha_metrics: Dict[str, Any],
        validation_metrics: Dict[str, Any],
        decay_detected: bool,
        decay_severity: str,
        reasons: list
    ) -> Tuple[str, float]:
        """
        Resolve final verdict based on scores and decay.
        
        Returns: (verdict, confidence)
        """
        alpha_pf = alpha_metrics.get("profit_factor")
        val_pf = validation_metrics.get("profit_factor")
        val_expectancy = float(validation_metrics.get("expectancy", 0) or 0)
        val_trades = validation_metrics.get("trades", 0)
        
        has_validation_data = val_trades >= 1
        
        # STRONG_CONFIRMED_EDGE
        # Both historical and live are strong
        if combined_score >= self.STRONG_CONFIRMED_THRESHOLD:
            if has_validation_data and val_pf is not None and val_pf > 1.3:
                confidence = min(0.95, 0.65 + combined_score * 0.3)
                return "STRONG_CONFIRMED_EDGE", round(confidence, 2)
        
        # STRONG_BUT_DECAYING  
        # Historical strong but live weak - edge decay detected
        if decay_detected:
            if decay_severity == "severe":
                if "edge_decay_severe" not in reasons:
                    reasons.append("edge_decay_severe")
                return "STRONG_BUT_DECAYING", 0.82
            elif decay_severity == "mild":
                if "edge_decay_mild" not in reasons:
                    reasons.append("edge_decay_mild")
                return "STRONG_BUT_DECAYING", 0.75
        
        # Also decay if historical PF strong but validation negative expectancy
        if (alpha_pf is not None and alpha_pf > 1.5 
            and has_validation_data 
            and val_expectancy <= 0):
            if "edge_decay_detected" not in reasons:
                reasons.append("edge_decay_detected")
            return "STRONG_BUT_DECAYING", 0.78
        
        # NO_EDGE
        # Both historical and live are weak
        if combined_score <= self.NO_EDGE_THRESHOLD:
            return "NO_EDGE", 0.80
        
        # Additional NO_EDGE conditions
        if (alpha_pf is not None and alpha_pf < 1.0 
            and has_validation_data 
            and val_pf is not None and val_pf < 1.0):
            return "NO_EDGE", 0.85
        
        # WEAK_EDGE
        # Some edge present but not convincing
        if combined_score > self.NO_EDGE_THRESHOLD and combined_score < self.STRONG_CONFIRMED_THRESHOLD:
            confidence = 0.50 + combined_score * 0.3
            return "WEAK_EDGE", round(confidence, 2)
        
        # Default to WEAK_EDGE if can't determine
        return "WEAK_EDGE", 0.55
    
    def evaluate_batch(
        self, 
        items: list[Dict[str, Any]]
    ) -> list[CombinedAlphaTruth]:
        """
        Evaluate multiple items.
        Each item should have: scope, scope_key, alpha_metrics, validation_metrics
        """
        return [
            self.evaluate(
                scope=item["scope"],
                scope_key=item["scope_key"],
                alpha_metrics=item["alpha_metrics"],
                validation_metrics=item["validation_metrics"],
            )
            for item in items
        ]
