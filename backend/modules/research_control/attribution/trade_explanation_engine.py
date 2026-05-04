"""
PHASE 17.4 — Trade Explanation Engine
======================================
Generates human-readable explanations for trades.

Explains:
- Why trade was entered
- What confirmed the entry
- Why trade succeeded/failed
- What could be improved
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from modules.research_control.attribution.attribution_types import (
    TradeContext,
    DecisionContext,
    TradeOutcome,
    TradeDirection,
    FailureSource,
    SystemLayer,
)


class TradeExplanationEngine:
    """
    Trade Explanation Engine - PHASE 17.4
    
    Generates human-readable explanations for trades.
    """
    
    def __init__(self):
        pass
    
    def generate_explanation(
        self,
        trade_context: TradeContext,
        decision_context: DecisionContext,
        layer_contributions: Dict[str, float],
        failure_source: Optional[FailureSource],
        responsible_layer: Optional[SystemLayer],
    ) -> str:
        """
        Generate complete trade explanation.
        """
        parts = []
        
        # Entry explanation
        entry_explanation = self._explain_entry(
            trade_context, decision_context, layer_contributions
        )
        parts.append(entry_explanation)
        
        # Confirmation explanation
        confirmation_explanation = self._explain_confirmations(decision_context)
        if confirmation_explanation:
            parts.append(confirmation_explanation)
        
        # Risk/sizing explanation
        sizing_explanation = self._explain_sizing(trade_context, decision_context)
        parts.append(sizing_explanation)
        
        # Outcome explanation
        outcome_explanation = self._explain_outcome(
            trade_context, failure_source, responsible_layer
        )
        parts.append(outcome_explanation)
        
        return " ".join(parts)
    
    def _explain_entry(
        self,
        trade_ctx: TradeContext,
        decision_ctx: DecisionContext,
        contributions: Dict[str, float],
    ) -> str:
        """Explain why trade was entered."""
        direction = "long" if trade_ctx.direction == TradeDirection.LONG else "short"
        
        # Find top contributors
        sorted_contrib = sorted(
            contributions.items(),
            key=lambda x: x[1],
            reverse=True
        )
        top_two = sorted_contrib[:2]
        
        # Build entry reason
        if decision_ctx.ta_score > 0.70:
            ta_reason = "strong TA trend signal"
        elif decision_ctx.ta_score > 0.55:
            ta_reason = "moderate TA signal"
        else:
            ta_reason = "weak TA indication"
        
        if decision_ctx.exchange_score > 0.65:
            exchange_reason = "confirmed by exchange flow"
        else:
            exchange_reason = "with mixed exchange signals"
        
        return f"Trade entered {direction} due to {ta_reason} {exchange_reason}."
    
    def _explain_confirmations(self, decision_ctx: DecisionContext) -> str:
        """Explain what confirmed the trade."""
        confirmations = []
        
        if decision_ctx.ecology_score > 0.65:
            confirmations.append("ecology stable")
        
        if decision_ctx.interaction_score > 0.60:
            confirmations.append("positive interaction patterns")
        
        if decision_ctx.market_state_score > 0.65:
            confirmations.append("favorable market state")
        
        if decision_ctx.governance_score > 0.70:
            confirmations.append("factor governance healthy")
        
        if confirmations:
            return f"Entry confirmed by: {', '.join(confirmations)}."
        
        return ""
    
    def _explain_sizing(
        self,
        trade_ctx: TradeContext,
        decision_ctx: DecisionContext,
    ) -> str:
        """Explain position sizing."""
        if trade_ctx.position_size < 0.5:
            size_reason = "reduced due to elevated risk"
        elif trade_ctx.position_size > 0.8:
            size_reason = "full size due to high conviction"
        else:
            size_reason = "moderate size based on risk parameters"
        
        if decision_ctx.ecology_score < 0.55:
            size_reason += " with ecology stress adjustment"
        
        return f"Position sized at {trade_ctx.position_size:.0%}, {size_reason}."
    
    def _explain_outcome(
        self,
        trade_ctx: TradeContext,
        failure_source: Optional[FailureSource],
        responsible_layer: Optional[SystemLayer],
    ) -> str:
        """Explain trade outcome."""
        if trade_ctx.outcome == TradeOutcome.WIN:
            return f"Trade closed successfully with {trade_ctx.pnl_percent:.2f}% profit."
        
        elif trade_ctx.outcome == TradeOutcome.BREAKEVEN:
            return "Trade closed at breakeven."
        
        elif trade_ctx.outcome == TradeOutcome.LOSS:
            failure_explanations = {
                FailureSource.TA_ERROR: "TA signal was incorrect",
                FailureSource.FALSE_BREAKOUT: "breakout was false",
                FailureSource.MARKET_REGIME_SHIFT: "market regime shifted",
                FailureSource.ECOLOGY_STRESS: "ecology stress intensified",
                FailureSource.INTERACTION_CONFLICT: "factor interactions conflicted",
                FailureSource.STRUCTURE_FLOW_CONFLICT: "structure turned against flow",
                FailureSource.LIQUIDITY_TRAP: "liquidity trap detected post-entry",
                FailureSource.CROWDING_REVERSAL: "crowded position reversed",
                FailureSource.GOVERNANCE_DEGRADATION: "factor governance degraded",
            }
            
            reason = failure_explanations.get(failure_source, "unexpected market move")
            layer = responsible_layer.value if responsible_layer else "Unknown"
            
            return f"Trade failed ({trade_ctx.pnl_percent:.2f}%) due to {reason}. Primary failure source: {layer} layer."
        
        return "Trade status unknown."
    
    def generate_risk_breakdown(
        self,
        decision_context: DecisionContext,
    ) -> Dict[str, float]:
        """Generate risk contribution breakdown."""
        total_risk_factors = (
            (1 - decision_context.ecology_score) +
            (1 - decision_context.interaction_score) +
            (1 - decision_context.governance_score) +
            (1 - decision_context.market_state_score)
        )
        
        if total_risk_factors == 0:
            total_risk_factors = 1
        
        return {
            "ecology_risk": round((1 - decision_context.ecology_score) / total_risk_factors, 4),
            "interaction_risk": round((1 - decision_context.interaction_score) / total_risk_factors, 4),
            "governance_risk": round((1 - decision_context.governance_score) / total_risk_factors, 4),
            "market_state_risk": round((1 - decision_context.market_state_score) / total_risk_factors, 4),
        }
    
    def generate_confidence_breakdown(
        self,
        decision_context: DecisionContext,
    ) -> Dict[str, float]:
        """Generate confidence contribution breakdown."""
        total = (
            decision_context.ta_score +
            decision_context.exchange_score +
            decision_context.market_state_score +
            decision_context.ecology_score +
            decision_context.interaction_score
        )
        
        if total == 0:
            total = 1
        
        return {
            "ta_confidence": round(decision_context.ta_score / total, 4),
            "exchange_confidence": round(decision_context.exchange_score / total, 4),
            "market_state_confidence": round(decision_context.market_state_score / total, 4),
            "ecology_confidence": round(decision_context.ecology_score / total, 4),
            "interaction_confidence": round(decision_context.interaction_score / total, 4),
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[TradeExplanationEngine] = None


def get_trade_explanation_engine() -> TradeExplanationEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = TradeExplanationEngine()
    return _engine
