"""
PHASE 22.5 — Crisis Exposure Engine
===================================
Core engine that aggregates all institutional risk modules.

Formula:
crisis_score = 0.30*var + 0.25*tail + 0.25*contagion + 0.20*correlation

Modifiers use conservative min() logic across all dimensions.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .crisis_types import (
    CrisisState,
    CrisisAction,
    CrisisExposureState,
    CRISIS_THRESHOLDS,
    CRISIS_MODIFIERS,
    STATE_SCORES,
    CRISIS_SCORE_WEIGHTS,
    RISK_DIMENSIONS,
)


class CrisisExposureEngine:
    """
    Aggregates all institutional risk dimensions into unified crisis state.
    
    This is the top-level institutional risk overlay for the platform.
    """
    
    def __init__(self):
        self.weights = CRISIS_SCORE_WEIGHTS
        self.state_scores = STATE_SCORES
        self.thresholds = CRISIS_THRESHOLDS
    
    def calculate(
        self,
        # VaR inputs
        var_state: str = "NORMAL",
        var_ratio: float = 0.0,
        var_confidence_modifier: float = 1.0,
        var_capital_modifier: float = 1.0,
        
        # Tail Risk inputs
        tail_state: str = "LOW",
        tail_risk_score: float = 0.0,
        tail_confidence_modifier: float = 1.0,
        tail_capital_modifier: float = 1.0,
        
        # Contagion inputs
        contagion_state: str = "LOW",
        systemic_risk_score: float = 0.0,
        contagion_confidence_modifier: float = 1.0,
        contagion_capital_modifier: float = 1.0,
        
        # Correlation inputs
        correlation_state: str = "NORMAL",
        correlation_spike_intensity: float = 0.0,
        correlation_confidence_modifier: float = 1.0,
        correlation_capital_modifier: float = 1.0,
    ) -> CrisisExposureState:
        """
        Calculate unified crisis exposure state.
        
        Args:
            var_state: VaR risk state
            var_ratio: VaR ratio value
            var_confidence_modifier: VaR confidence modifier
            var_capital_modifier: VaR capital modifier
            
            tail_state: Tail risk state
            tail_risk_score: Tail risk score
            tail_confidence_modifier: Tail confidence modifier
            tail_capital_modifier: Tail capital modifier
            
            contagion_state: Contagion state
            systemic_risk_score: Systemic risk score
            contagion_confidence_modifier: Contagion confidence modifier
            contagion_capital_modifier: Contagion capital modifier
            
            correlation_state: Correlation state
            correlation_spike_intensity: Correlation spike intensity
            correlation_confidence_modifier: Correlation confidence modifier
            correlation_capital_modifier: Correlation capital modifier
            
        Returns:
            CrisisExposureState with unified analysis
        """
        # Normalize states to scores
        var_score = self._normalize_state("var", var_state.upper())
        tail_score = self._normalize_state("tail", tail_state.upper())
        contagion_score = self._normalize_state("contagion", contagion_state.upper())
        correlation_score = self._normalize_state("correlation", correlation_state.upper())
        
        # Calculate weighted crisis score
        crisis_score = (
            self.weights["var"] * var_score +
            self.weights["tail"] * tail_score +
            self.weights["contagion"] * contagion_score +
            self.weights["correlation"] * correlation_score
        )
        
        # Bound to [0, 1]
        crisis_score = max(0, min(1, crisis_score))
        
        # Determine crisis state
        crisis_state = self._get_state(crisis_score)
        
        # Get recommended action
        recommended_action = self._get_action(crisis_state)
        
        # Conservative min() logic for combined modifiers
        confidence_modifier = min(
            var_confidence_modifier,
            tail_confidence_modifier,
            contagion_confidence_modifier,
            correlation_confidence_modifier,
        )
        
        capital_modifier = min(
            var_capital_modifier,
            tail_capital_modifier,
            contagion_capital_modifier,
            correlation_capital_modifier,
        )
        
        # Determine strongest and weakest risk dimensions
        scores = {
            "var": var_score,
            "tail": tail_score,
            "contagion": contagion_score,
            "correlation": correlation_score,
        }
        
        strongest_risk = max(scores, key=scores.get)
        weakest_risk = min(scores, key=scores.get)
        
        # Build component modifiers for reference
        component_modifiers = {
            "var": {
                "confidence": round(var_confidence_modifier, 4),
                "capital": round(var_capital_modifier, 4),
            },
            "tail": {
                "confidence": round(tail_confidence_modifier, 4),
                "capital": round(tail_capital_modifier, 4),
            },
            "contagion": {
                "confidence": round(contagion_confidence_modifier, 4),
                "capital": round(contagion_capital_modifier, 4),
            },
            "correlation": {
                "confidence": round(correlation_confidence_modifier, 4),
                "capital": round(correlation_capital_modifier, 4),
            },
        }
        
        # Build reason
        reason = self._build_reason(
            crisis_state=crisis_state,
            strongest_risk=strongest_risk,
            scores=scores,
        )
        
        return CrisisExposureState(
            var_state=var_state.upper(),
            tail_state=tail_state.upper(),
            contagion_state=contagion_state.upper(),
            correlation_state=correlation_state.upper(),
            var_score=var_score,
            tail_score=tail_score,
            contagion_score=contagion_score,
            correlation_score=correlation_score,
            crisis_score=crisis_score,
            crisis_state=crisis_state,
            recommended_action=recommended_action,
            confidence_modifier=confidence_modifier,
            capital_modifier=capital_modifier,
            strongest_risk=strongest_risk,
            weakest_risk=weakest_risk,
            reason=reason,
            component_modifiers=component_modifiers,
        )
    
    def _normalize_state(self, dimension: str, state: str) -> float:
        """Normalize state string to numerical score."""
        scores = self.state_scores.get(dimension, {})
        return scores.get(state, 0.20)  # Default to low if unknown
    
    def _get_state(self, crisis_score: float) -> CrisisState:
        """Determine crisis state from score."""
        if crisis_score < self.thresholds[CrisisState.NORMAL]:
            return CrisisState.NORMAL
        elif crisis_score < self.thresholds[CrisisState.GUARDED]:
            return CrisisState.GUARDED
        elif crisis_score < self.thresholds[CrisisState.STRESSED]:
            return CrisisState.STRESSED
        else:
            return CrisisState.CRISIS
    
    def _get_action(self, state: CrisisState) -> CrisisAction:
        """Get recommended action for crisis state."""
        action_map = {
            CrisisState.NORMAL: CrisisAction.HOLD,
            CrisisState.GUARDED: CrisisAction.REDUCE_RISK,
            CrisisState.STRESSED: CrisisAction.DELEVER,
            CrisisState.CRISIS: CrisisAction.EMERGENCY_MODE,
        }
        return action_map.get(state, CrisisAction.HOLD)
    
    def _build_reason(
        self,
        crisis_state: CrisisState,
        strongest_risk: str,
        scores: Dict[str, float],
    ) -> str:
        """Build explanation reason."""
        dimension_name = RISK_DIMENSIONS.get(strongest_risk, strongest_risk)
        
        # Find secondary high risks
        high_risks = [k for k, v in scores.items() if v >= 0.60 and k != strongest_risk]
        
        if crisis_state == CrisisState.NORMAL:
            return "all risk dimensions within normal bounds"
        
        elif crisis_state == CrisisState.GUARDED:
            if high_risks:
                return f"{dimension_name} elevated, monitor {', '.join(high_risks)}"
            return f"{dimension_name} showing early stress signals"
        
        elif crisis_state == CrisisState.STRESSED:
            if high_risks:
                return f"{dimension_name} and {', '.join(high_risks)} jointly stressing portfolio resilience"
            return f"{dimension_name} creating significant stress on portfolio"
        
        else:  # CRISIS
            return f"critical exposure across multiple dimensions, {dimension_name} dominant"
    
    def get_drivers(self, state: CrisisExposureState) -> Dict[str, Any]:
        """Get detailed breakdown of crisis drivers."""
        scores = {
            "var": state.var_score,
            "tail": state.tail_score,
            "contagion": state.contagion_score,
            "correlation": state.correlation_score,
        }
        
        # Sort by score descending
        sorted_risks = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "ranked_risks": [
                {
                    "dimension": k,
                    "label": RISK_DIMENSIONS.get(k, k),
                    "score": round(v, 4),
                    "weight": self.weights[k],
                    "contribution": round(v * self.weights[k], 4),
                }
                for k, v in sorted_risks
            ],
            "strongest_risk": state.strongest_risk,
            "weakest_risk": state.weakest_risk,
            "total_crisis_score": round(state.crisis_score, 4),
        }
    
    def calculate_from_engines(
        self,
        var_state_obj: Optional[Any] = None,
        tail_state_obj: Optional[Any] = None,
        contagion_state_obj: Optional[Any] = None,
        correlation_state_obj: Optional[Any] = None,
    ) -> CrisisExposureState:
        """
        Calculate from engine state objects directly.
        
        Convenience method when working with actual engine outputs.
        """
        # Extract VaR params
        var_params = {}
        if var_state_obj:
            var_params = {
                "var_state": getattr(var_state_obj, "risk_state", "NORMAL"),
                "var_ratio": getattr(var_state_obj, "var_ratio", 0.0),
                "var_confidence_modifier": getattr(var_state_obj, "confidence_modifier", 1.0),
                "var_capital_modifier": getattr(var_state_obj, "capital_modifier", 1.0),
            }
            # Handle enum
            if hasattr(var_params["var_state"], "value"):
                var_params["var_state"] = var_params["var_state"].value
        
        # Extract Tail Risk params
        tail_params = {}
        if tail_state_obj:
            tail_params = {
                "tail_state": getattr(tail_state_obj, "tail_risk_state", "LOW"),
                "tail_risk_score": getattr(tail_state_obj, "tail_risk_score", 0.0),
                "tail_confidence_modifier": getattr(tail_state_obj, "confidence_modifier", 1.0),
                "tail_capital_modifier": getattr(tail_state_obj, "capital_modifier", 1.0),
            }
            if hasattr(tail_params["tail_state"], "value"):
                tail_params["tail_state"] = tail_params["tail_state"].value
        
        # Extract Contagion params
        contagion_params = {}
        if contagion_state_obj:
            contagion_params = {
                "contagion_state": getattr(contagion_state_obj, "contagion_state", "LOW"),
                "systemic_risk_score": getattr(contagion_state_obj, "systemic_risk_score", 0.0),
                "contagion_confidence_modifier": getattr(contagion_state_obj, "confidence_modifier", 1.0),
                "contagion_capital_modifier": getattr(contagion_state_obj, "capital_modifier", 1.0),
            }
            if hasattr(contagion_params["contagion_state"], "value"):
                contagion_params["contagion_state"] = contagion_params["contagion_state"].value
        
        # Extract Correlation params
        correlation_params = {}
        if correlation_state_obj:
            correlation_params = {
                "correlation_state": getattr(correlation_state_obj, "correlation_state", "NORMAL"),
                "correlation_spike_intensity": getattr(correlation_state_obj, "correlation_spike_intensity", 0.0),
                "correlation_confidence_modifier": getattr(correlation_state_obj, "confidence_modifier", 1.0),
                "correlation_capital_modifier": getattr(correlation_state_obj, "capital_modifier", 1.0),
            }
            if hasattr(correlation_params["correlation_state"], "value"):
                correlation_params["correlation_state"] = correlation_params["correlation_state"].value
        
        # Merge and calculate
        params = {**var_params, **tail_params, **contagion_params, **correlation_params}
        return self.calculate(**params)
