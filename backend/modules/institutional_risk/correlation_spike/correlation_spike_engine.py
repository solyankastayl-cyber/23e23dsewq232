"""
PHASE 22.4 — Correlation Spike Engine
=====================================
Detects correlation spike intensity and diversification breakdown.

Core formula:
correlation_spike_intensity = 
    0.40 * asset_correlation +
    0.35 * strategy_correlation +
    0.25 * factor_correlation
"""

from typing import Dict, Any, Optional
from .correlation_types import (
    CorrelationState,
    CorrelationAction,
    CORRELATION_THRESHOLDS,
    CORRELATION_SPIKE_WEIGHTS,
)


class CorrelationSpikeEngine:
    """
    Detects correlation spike intensity.
    
    When spike intensity is high, diversification fails.
    """
    
    def __init__(self):
        self.weights = CORRELATION_SPIKE_WEIGHTS
        self.thresholds = CORRELATION_THRESHOLDS
    
    def calculate(
        self,
        asset_correlation: float,
        strategy_correlation: float,
        factor_correlation: float,
        volatility_state: str = "NORMAL",
        risk_state: str = "NORMAL",
    ) -> Dict[str, Any]:
        """
        Calculate correlation spike intensity.
        
        Args:
            asset_correlation: Asset-level correlation (0-1)
            strategy_correlation: Strategy-level correlation (0-1)
            factor_correlation: Factor-level correlation (0-1)
            volatility_state: Current volatility regime
            risk_state: Current risk state
            
        Returns:
            Correlation spike metrics
        """
        # Bound inputs
        asset_corr = max(0, min(1, asset_correlation))
        strategy_corr = max(0, min(1, strategy_correlation))
        factor_corr = max(0, min(1, factor_correlation))
        
        # Calculate weighted intensity
        spike_intensity = (
            self.weights["asset_correlation"] * asset_corr +
            self.weights["strategy_correlation"] * strategy_corr +
            self.weights["factor_correlation"] * factor_corr
        )
        
        # Apply regime adjustments
        if volatility_state.upper() in ["EXTREME", "CRISIS"]:
            spike_intensity = min(1.0, spike_intensity * 1.15)
        elif volatility_state.upper() in ["HIGH", "EXPANDING"]:
            spike_intensity = min(1.0, spike_intensity * 1.08)
        
        if risk_state.upper() in ["CRITICAL", "HIGH"]:
            spike_intensity = min(1.0, spike_intensity * 1.10)
        
        # Determine state
        state = self._get_state(spike_intensity)
        
        # Determine dominant correlation
        correlations = {
            "asset": asset_corr,
            "strategy": strategy_corr,
            "factor": factor_corr,
        }
        dominant = max(correlations, key=correlations.get)
        
        return {
            "correlation_spike_intensity": round(spike_intensity, 4),
            "correlation_state": state.value,
            "dominant_correlation": dominant,
            "correlations": {
                "asset": round(asset_corr, 4),
                "strategy": round(strategy_corr, 4),
                "factor": round(factor_corr, 4),
            },
            "weights_applied": self.weights,
        }
    
    def _get_state(self, spike_intensity: float) -> CorrelationState:
        """Determine correlation state from spike intensity."""
        if spike_intensity < self.thresholds[CorrelationState.NORMAL]:
            return CorrelationState.NORMAL
        elif spike_intensity < self.thresholds[CorrelationState.ELEVATED]:
            return CorrelationState.ELEVATED
        elif spike_intensity < self.thresholds[CorrelationState.HIGH]:
            return CorrelationState.HIGH
        else:
            return CorrelationState.SYSTEMIC
    
    def calculate_diversification_score(
        self,
        asset_correlation: float,
        strategy_correlation: float,
        factor_correlation: float,
    ) -> float:
        """
        Calculate diversification score.
        
        diversification_score = 1 - avg(asset_corr, strategy_corr, factor_corr)
        
        Higher = better diversification.
        """
        avg_correlation = (asset_correlation + strategy_correlation + factor_correlation) / 3
        return round(max(0, min(1, 1 - avg_correlation)), 4)
    
    def get_recommended_action(self, state: CorrelationState) -> CorrelationAction:
        """Get recommended action for correlation state."""
        action_map = {
            CorrelationState.NORMAL: CorrelationAction.HOLD,
            CorrelationState.ELEVATED: CorrelationAction.REDUCE_RISK,
            CorrelationState.HIGH: CorrelationAction.REDUCE_DIVERSIFICATION,
            CorrelationState.SYSTEMIC: CorrelationAction.DELEVER,
        }
        return action_map.get(state, CorrelationAction.HOLD)
