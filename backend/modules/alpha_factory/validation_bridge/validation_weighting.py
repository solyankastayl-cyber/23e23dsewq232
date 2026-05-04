"""
Validation Weighting - Scoring logic for combining alpha + validation metrics
"""
from typing import Dict, Any, List, Tuple


class ValidationWeighting:
    """
    Computes weighted confirmation scores from alpha (historical) 
    and validation (live) metrics.
    """
    
    # Thresholds
    PF_STRONG = 1.5
    PF_CONFIRMED = 1.4
    PF_WEAK = 1.1
    
    EXPECTANCY_POSITIVE = 0
    WRONG_EARLY_LOW = 0.12
    WRONG_EARLY_HIGH = 0.22
    EXPIRED_HIGH = 0.25
    
    WIN_RATE_STRONG = 0.55
    
    def score(self, alpha_metrics: Dict[str, Any], validation_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute weighted score and reasons from combined metrics.
        
        Returns:
            {
                "alpha_score": float,
                "validation_score": float,
                "combined_score": float,
                "reasons": list[str],
                "decay_detected": bool,
                "decay_severity": str
            }
        """
        alpha_score = 0.0
        validation_score = 0.0
        reasons = []
        
        # ============ Alpha (Historical) Scoring ============
        alpha_pf = alpha_metrics.get("profit_factor")
        alpha_expectancy = self._safe_float(alpha_metrics.get("expectancy", 0))
        alpha_win_rate = self._safe_float(alpha_metrics.get("win_rate", 0))
        alpha_stability = self._safe_float(alpha_metrics.get("stability", 0))
        
        # Historical PF
        if alpha_pf is not None:
            if alpha_pf > 2.0:
                alpha_score += 0.30
                reasons.append("historical_pf_excellent")
            elif alpha_pf > self.PF_STRONG:
                alpha_score += 0.25
                reasons.append("historical_pf_strong")
            elif alpha_pf > 1.2:
                alpha_score += 0.10
                reasons.append("historical_pf_moderate")
            else:
                alpha_score -= 0.10
                reasons.append("historical_pf_weak")
        
        # Historical Expectancy
        if alpha_expectancy > 50:
            alpha_score += 0.15
            reasons.append("historical_expectancy_strong")
        elif alpha_expectancy > self.EXPECTANCY_POSITIVE:
            alpha_score += 0.10
            reasons.append("historical_expectancy_positive")
        elif alpha_expectancy < -20:
            alpha_score -= 0.15
            reasons.append("historical_expectancy_negative")
        
        # Historical Win Rate
        if alpha_win_rate > 0.60:
            alpha_score += 0.10
            reasons.append("historical_win_rate_strong")
        elif alpha_win_rate > self.WIN_RATE_STRONG:
            alpha_score += 0.05
        
        # ============ Validation (Live) Scoring ============
        val_pf = validation_metrics.get("profit_factor")
        val_expectancy = self._safe_float(validation_metrics.get("expectancy", 0))
        val_win_rate = self._safe_float(validation_metrics.get("win_rate", 0))
        val_wrong_early = self._safe_float(validation_metrics.get("wrong_early_rate", 0))
        val_expired = self._safe_float(validation_metrics.get("expired_rate", 0))
        val_trades = validation_metrics.get("trades", 0)
        
        # Check if we have validation data
        has_validation_data = val_trades >= 1
        
        if has_validation_data:
            # Validation PF (most important live signal)
            if val_pf is not None:
                if val_pf > 2.0:
                    validation_score += 0.35
                    reasons.append("validation_pf_excellent")
                elif val_pf > self.PF_CONFIRMED:
                    validation_score += 0.30
                    reasons.append("validation_pf_confirmed")
                elif val_pf > self.PF_WEAK:
                    validation_score += 0.10
                    reasons.append("validation_pf_moderate")
                else:
                    validation_score -= 0.25
                    reasons.append("validation_pf_weak")
            
            # Validation Expectancy
            if val_expectancy > 30:
                validation_score += 0.20
                reasons.append("validation_expectancy_strong")
            elif val_expectancy > self.EXPECTANCY_POSITIVE:
                validation_score += 0.15
                reasons.append("validation_expectancy_positive")
            elif val_expectancy < -10:
                validation_score -= 0.20
                reasons.append("validation_expectancy_negative")
            
            # Validation Win Rate
            if val_win_rate > 0.60:
                validation_score += 0.10
                reasons.append("validation_win_rate_strong")
            elif val_win_rate < 0.40:
                validation_score -= 0.10
                reasons.append("validation_win_rate_poor")
            
            # Wrong Early (critical signal)
            if val_wrong_early < self.WRONG_EARLY_LOW:
                validation_score += 0.10
                reasons.append("validation_wrong_early_low")
            elif val_wrong_early > self.WRONG_EARLY_HIGH:
                validation_score -= 0.15
                reasons.append("validation_wrong_early_high")
            
            # Expired rate
            if val_expired > self.EXPIRED_HIGH:
                validation_score -= 0.10
                reasons.append("validation_expired_high")
        else:
            reasons.append("validation_insufficient_data")
        
        # ============ Decay Detection ============
        decay_detected = False
        decay_severity = "none"
        
        if alpha_pf is not None and val_pf is not None and has_validation_data:
            pf_delta = alpha_pf - val_pf
            
            if alpha_pf > self.PF_STRONG and val_pf < self.PF_WEAK:
                decay_detected = True
                decay_severity = "severe"
                reasons.append("edge_decay_severe")
            elif alpha_pf > 1.3 and val_pf < alpha_pf * 0.7:
                decay_detected = True
                decay_severity = "mild"
                reasons.append("edge_decay_mild")
        
        # Combined score (validation weighted more heavily if available)
        if has_validation_data:
            combined_score = alpha_score * 0.4 + validation_score * 0.6
        else:
            combined_score = alpha_score
        
        return {
            "alpha_score": round(alpha_score, 4),
            "validation_score": round(validation_score, 4),
            "combined_score": round(combined_score, 4),
            "reasons": reasons,
            "decay_detected": decay_detected,
            "decay_severity": decay_severity,
        }
    
    def _safe_float(self, val) -> float:
        try:
            return float(val) if val is not None else 0.0
        except (ValueError, TypeError):
            return 0.0
