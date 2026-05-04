"""
PHASE 22.4 — Correlation Aggregator
===================================
Aggregates all correlation components into CorrelationSpikeState.

Combines:
- Asset Correlation Engine
- Strategy Correlation Engine
- Factor Correlation Engine
- Correlation Spike Engine
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .correlation_types import (
    CorrelationState,
    CorrelationAction,
    CorrelationSpikeState,
    CORRELATION_MODIFIERS,
)
from .asset_correlation_engine import AssetCorrelationEngine
from .strategy_correlation_engine import StrategyCorrelationEngine
from .factor_correlation_engine import FactorCorrelationEngine
from .correlation_spike_engine import CorrelationSpikeEngine


class CorrelationAggregator:
    """
    Aggregates correlation components into unified state.
    
    Main entry point for Correlation Spike analysis.
    """
    
    def __init__(self):
        self.asset_engine = AssetCorrelationEngine()
        self.strategy_engine = StrategyCorrelationEngine()
        self.factor_engine = FactorCorrelationEngine()
        self.spike_engine = CorrelationSpikeEngine()
    
    def calculate(
        self,
        # Portfolio inputs
        asset_allocations: Optional[Dict[str, float]] = None,
        cluster_allocations: Optional[Dict[str, float]] = None,
        concentration_score: float = 0.3,
        
        # Strategy Brain inputs
        active_strategies: Optional[List[str]] = None,
        strategy_allocations: Optional[Dict[str, float]] = None,
        
        # Factor inputs
        factor_allocations: Optional[Dict[str, float]] = None,
        
        # Market State inputs
        volatility_state: str = "NORMAL",
        breadth_state: str = "NEUTRAL",
        dominance_regime: str = "NEUTRAL",
        
        # Risk inputs
        risk_state: str = "NORMAL",
        tail_risk_state: str = "LOW",
        
        # Optional real correlations
        real_correlations: Optional[Dict[str, float]] = None,
    ) -> CorrelationSpikeState:
        """
        Calculate complete correlation spike state.
        
        Args:
            asset_allocations: Dict of asset -> weight
            cluster_allocations: Dict of cluster -> weight
            concentration_score: Portfolio concentration
            active_strategies: List of active strategy IDs
            strategy_allocations: Dict of strategy -> weight
            factor_allocations: Dict of factor -> weight
            volatility_state: Current volatility regime
            breadth_state: Market breadth state
            dominance_regime: Market dominance regime
            risk_state: VaR risk state
            tail_risk_state: Tail risk state
            real_correlations: Optional real correlation values
            
        Returns:
            CorrelationSpikeState with full analysis
        """
        # Calculate asset correlation
        asset_result = self.asset_engine.calculate(
            asset_allocations=asset_allocations,
            cluster_allocations=cluster_allocations,
            volatility_state=volatility_state,
            real_correlations=real_correlations,
        )
        asset_correlation = asset_result["asset_correlation"]
        
        # Calculate strategy correlation
        strategy_result = self.strategy_engine.calculate(
            active_strategies=active_strategies,
            strategy_allocations=strategy_allocations,
            volatility_state=volatility_state,
        )
        strategy_correlation = strategy_result["strategy_correlation"]
        
        # Calculate factor correlation
        factor_result = self.factor_engine.calculate(
            factor_allocations=factor_allocations,
            volatility_state=volatility_state,
        )
        factor_correlation = factor_result["factor_correlation"]
        
        # Calculate spike intensity
        spike_result = self.spike_engine.calculate(
            asset_correlation=asset_correlation,
            strategy_correlation=strategy_correlation,
            factor_correlation=factor_correlation,
            volatility_state=volatility_state,
            risk_state=risk_state,
        )
        
        spike_intensity = spike_result["correlation_spike_intensity"]
        correlation_state = CorrelationState(spike_result["correlation_state"])
        dominant_correlation = spike_result["dominant_correlation"]
        
        # Calculate diversification score
        diversification_score = self.spike_engine.calculate_diversification_score(
            asset_correlation=asset_correlation,
            strategy_correlation=strategy_correlation,
            factor_correlation=factor_correlation,
        )
        
        # Get recommended action
        recommended_action = self.spike_engine.get_recommended_action(correlation_state)
        
        # Get modifiers
        modifiers = CORRELATION_MODIFIERS.get(correlation_state, CORRELATION_MODIFIERS[CorrelationState.NORMAL])
        confidence_modifier = modifiers["confidence_modifier"]
        capital_modifier = modifiers["capital_modifier"]
        
        # Build reason
        reason = self._build_reason(
            correlation_state=correlation_state,
            dominant_correlation=dominant_correlation,
            spike_intensity=spike_intensity,
            volatility_state=volatility_state,
            diversification_score=diversification_score,
        )
        
        return CorrelationSpikeState(
            asset_correlation=asset_correlation,
            strategy_correlation=strategy_correlation,
            factor_correlation=factor_correlation,
            diversification_score=diversification_score,
            correlation_spike_intensity=spike_intensity,
            correlation_state=correlation_state,
            recommended_action=recommended_action,
            confidence_modifier=confidence_modifier,
            capital_modifier=capital_modifier,
            dominant_correlation=dominant_correlation,
            reason=reason,
            volatility_state=volatility_state,
            breadth_state=breadth_state,
            dominance_regime=dominance_regime,
            risk_state=risk_state,
            tail_risk_state=tail_risk_state,
        )
    
    def _build_reason(
        self,
        correlation_state: CorrelationState,
        dominant_correlation: str,
        spike_intensity: float,
        volatility_state: str,
        diversification_score: float,
    ) -> str:
        """Build explanation reason."""
        state_reasons = {
            CorrelationState.NORMAL: "normal correlation levels, diversification effective",
            CorrelationState.ELEVATED: f"elevated {dominant_correlation} correlation, monitor diversification",
            CorrelationState.HIGH: f"high {dominant_correlation} correlation under {volatility_state.lower()} volatility regime",
            CorrelationState.SYSTEMIC: f"systemic correlation spike ({spike_intensity:.2f}), diversification breakdown",
        }
        
        base_reason = state_reasons.get(correlation_state, "correlation state unknown")
        
        if diversification_score < 0.35:
            base_reason += ", low diversification score"
        
        return base_reason
    
    def get_correlation_summary(self, state: CorrelationSpikeState) -> Dict[str, Any]:
        """Get compact summary for display."""
        return {
            "correlation_spike_intensity": state.correlation_spike_intensity,
            "correlation_state": state.correlation_state.value,
            "diversification_score": state.diversification_score,
            "dominant_correlation": state.dominant_correlation,
            "recommended_action": state.recommended_action.value,
            "modifiers": {
                "confidence": state.confidence_modifier,
                "capital": state.capital_modifier,
            },
        }
    
    def get_diversification_breakdown(self, state: CorrelationSpikeState) -> Dict[str, Any]:
        """Get diversification analysis breakdown."""
        return {
            "diversification_score": state.diversification_score,
            "components": {
                "asset_correlation": state.asset_correlation,
                "strategy_correlation": state.strategy_correlation,
                "factor_correlation": state.factor_correlation,
            },
            "dominant_correlation": state.dominant_correlation,
            "correlation_state": state.correlation_state.value,
            "is_diversified": state.diversification_score > 0.50,
            "breakdown_risk": state.correlation_state in [CorrelationState.HIGH, CorrelationState.SYSTEMIC],
        }
