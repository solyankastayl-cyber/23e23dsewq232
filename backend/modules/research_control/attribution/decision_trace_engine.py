"""
PHASE 17.4 — Decision Trace Engine
===================================
Traces the decision path that led to a trade.

Analyzes:
- What signals triggered the trade
- What confirmations were present
- What was the decision confidence
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from modules.research_control.attribution.attribution_types import (
    TradeContext,
    DecisionContext,
    SystemLayer,
    TradeDirection,
)


class DecisionTraceEngine:
    """
    Decision Trace Engine - PHASE 17.4
    
    Traces the decision path that led to a trade.
    """
    
    def __init__(self):
        pass
    
    def trace_decision(
        self,
        trade_context: TradeContext,
        decision_context: DecisionContext,
    ) -> Dict[str, Any]:
        """
        Trace the decision path for a trade.
        
        Returns:
            Dict with decision trace details
        """
        # Calculate signal strength
        signal_strength = self._calculate_signal_strength(decision_context)
        
        # Identify triggers
        triggers = self._identify_triggers(decision_context)
        
        # Identify confirmations
        confirmations = self._identify_confirmations(decision_context)
        
        # Calculate confidence composition
        confidence_composition = self._calculate_confidence_composition(decision_context)
        
        return {
            "trade_id": trade_context.trade_id,
            "direction": trade_context.direction.value,
            "signal_strength": round(signal_strength, 4),
            "triggers": triggers,
            "confirmations": confirmations,
            "confidence_composition": confidence_composition,
            "primary_factor": decision_context.primary_factor,
            "secondary_factor": decision_context.secondary_factor,
            "execution_mode": decision_context.execution_mode,
        }
    
    def _calculate_signal_strength(self, ctx: DecisionContext) -> float:
        """Calculate overall signal strength."""
        return (
            0.35 * ctx.ta_score +
            0.25 * ctx.exchange_score +
            0.20 * ctx.market_state_score +
            0.10 * ctx.ecology_score +
            0.10 * ctx.interaction_score
        )
    
    def _identify_triggers(self, ctx: DecisionContext) -> List[str]:
        """Identify what triggered the trade."""
        triggers = []
        
        if ctx.ta_score > 0.70:
            triggers.append("Strong TA signal")
        if ctx.exchange_score > 0.70:
            triggers.append("Exchange flow confirmation")
        if ctx.market_state_score > 0.65:
            triggers.append("Favorable market state")
        
        if not triggers:
            triggers.append("Moderate multi-factor signal")
        
        return triggers
    
    def _identify_confirmations(self, ctx: DecisionContext) -> List[str]:
        """Identify confirming factors."""
        confirmations = []
        
        if ctx.ecology_score > 0.65:
            confirmations.append("Ecology stable")
        if ctx.interaction_score > 0.60:
            confirmations.append("Positive interaction")
        if ctx.governance_score > 0.70:
            confirmations.append("Factor governance healthy")
        
        return confirmations
    
    def _calculate_confidence_composition(self, ctx: DecisionContext) -> Dict[str, float]:
        """Calculate how confidence was composed."""
        total = (
            ctx.ta_score + ctx.exchange_score + ctx.market_state_score +
            ctx.ecology_score + ctx.interaction_score
        )
        
        if total == 0:
            total = 1
        
        return {
            "ta_contribution": round(ctx.ta_score / total, 4),
            "exchange_contribution": round(ctx.exchange_score / total, 4),
            "market_state_contribution": round(ctx.market_state_score / total, 4),
            "ecology_contribution": round(ctx.ecology_score / total, 4),
            "interaction_contribution": round(ctx.interaction_score / total, 4),
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[DecisionTraceEngine] = None


def get_decision_trace_engine() -> DecisionTraceEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = DecisionTraceEngine()
    return _engine
