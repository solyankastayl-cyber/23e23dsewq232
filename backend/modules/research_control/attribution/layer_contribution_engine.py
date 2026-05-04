"""
PHASE 17.4 — Layer Contribution Engine
=======================================
Calculates contribution of each system layer to a trade.

Layers:
- TA
- Exchange
- MarketState
- Ecology
- Interaction
- Governance
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from modules.research_control.attribution.attribution_types import (
    TradeContext,
    DecisionContext,
    SystemLayer,
    LayerContribution,
    DEFAULT_LAYER_WEIGHTS,
)


class LayerContributionEngine:
    """
    Layer Contribution Engine - PHASE 17.4
    
    Calculates how much each layer contributed to a trade decision.
    """
    
    def __init__(self):
        self.base_weights = DEFAULT_LAYER_WEIGHTS
    
    def calculate_contributions(
        self,
        decision_context: DecisionContext,
    ) -> Dict[str, float]:
        """
        Calculate normalized layer contributions.
        
        Returns:
            Dict mapping layer name to contribution (0-1)
        """
        # Raw scores from each layer
        raw_scores = {
            SystemLayer.TA: decision_context.ta_score,
            SystemLayer.EXCHANGE: decision_context.exchange_score,
            SystemLayer.MARKET_STATE: decision_context.market_state_score,
            SystemLayer.ECOLOGY: decision_context.ecology_score,
            SystemLayer.INTERACTION: decision_context.interaction_score,
            SystemLayer.GOVERNANCE: decision_context.governance_score,
        }
        
        # Weight-adjusted contributions
        weighted_scores = {
            layer: score * self.base_weights.get(layer, 0.1)
            for layer, score in raw_scores.items()
        }
        
        # Normalize to sum to 1
        total = sum(weighted_scores.values())
        if total == 0:
            total = 1
        
        normalized = {
            layer.value: score / total
            for layer, score in weighted_scores.items()
        }
        
        return normalized
    
    def get_detailed_contributions(
        self,
        decision_context: DecisionContext,
    ) -> List[LayerContribution]:
        """
        Get detailed contribution analysis for each layer.
        """
        contributions = self.calculate_contributions(decision_context)
        
        raw_scores = {
            SystemLayer.TA: decision_context.ta_score,
            SystemLayer.EXCHANGE: decision_context.exchange_score,
            SystemLayer.MARKET_STATE: decision_context.market_state_score,
            SystemLayer.ECOLOGY: decision_context.ecology_score,
            SystemLayer.INTERACTION: decision_context.interaction_score,
            SystemLayer.GOVERNANCE: decision_context.governance_score,
        }
        
        details = []
        for layer, score in raw_scores.items():
            influence = self._determine_influence(score)
            
            details.append(LayerContribution(
                layer=layer,
                contribution=contributions.get(layer.value, 0),
                score=score,
                influence=influence,
                details={
                    "base_weight": self.base_weights.get(layer, 0.1),
                    "raw_score": round(score, 4),
                },
            ))
        
        # Sort by contribution descending
        details.sort(key=lambda x: x.contribution, reverse=True)
        
        return details
    
    def identify_primary_secondary_drivers(
        self,
        decision_context: DecisionContext,
    ) -> tuple[str, str]:
        """
        Identify primary and secondary drivers.
        """
        contributions = self.calculate_contributions(decision_context)
        
        sorted_layers = sorted(
            contributions.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        primary = sorted_layers[0][0] if sorted_layers else "Unknown"
        secondary = sorted_layers[1][0] if len(sorted_layers) > 1 else "Unknown"
        
        return (primary, secondary)
    
    def _determine_influence(self, score: float) -> str:
        """Determine if layer had positive, negative, or neutral influence."""
        if score >= 0.65:
            return "POSITIVE"
        elif score >= 0.45:
            return "NEUTRAL"
        else:
            return "NEGATIVE"


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[LayerContributionEngine] = None


def get_layer_contribution_engine() -> LayerContributionEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = LayerContributionEngine()
    return _engine
