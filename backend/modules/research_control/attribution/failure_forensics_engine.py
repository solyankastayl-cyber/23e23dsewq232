"""
PHASE 17.4 — Failure Forensics Engine
======================================
Analyzes why trades failed.

Failure Sources:
- ta_error
- market_regime_shift
- crowding_reversal
- false_breakout
- liquidity_trap
- execution_slippage
- governance_degradation
- structure_flow_conflict
- ecology_stress
- interaction_conflict

Classifications:
- MODEL_ERROR
- MARKET_REGIME_SHIFT
- EXECUTION_ERROR
- RISK_MODEL_ERROR
- EXTERNAL_SHOCK
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from modules.research_control.attribution.attribution_types import (
    TradeContext,
    DecisionContext,
    TradeOutcome,
    FailureClassification,
    FailureSource,
    SystemLayer,
)


class FailureForensicsEngine:
    """
    Failure Forensics Engine - PHASE 17.4
    
    Analyzes why trades failed and identifies responsible layers.
    """
    
    def __init__(self):
        pass
    
    def analyze_failure(
        self,
        trade_context: TradeContext,
        decision_context: DecisionContext,
        post_trade_context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a trade failure.
        
        Returns:
            Dict with failure analysis
        """
        if trade_context.outcome == TradeOutcome.WIN:
            return {
                "failure_reason": None,
                "failure_classification": FailureClassification.NONE,
                "responsible_layer": None,
                "analysis": "Trade was successful",
            }
        
        # Determine failure source
        failure_source, confidence = self._identify_failure_source(
            trade_context, decision_context, post_trade_context
        )
        
        # Classify the failure
        classification = self._classify_failure(failure_source)
        
        # Identify responsible layer
        responsible_layer = self._identify_responsible_layer(
            failure_source, decision_context
        )
        
        # Build analysis
        analysis = self._build_failure_analysis(
            failure_source, classification, responsible_layer,
            trade_context, decision_context
        )
        
        return {
            "failure_reason": failure_source,
            "failure_classification": classification,
            "responsible_layer": responsible_layer,
            "failure_confidence": confidence,
            "analysis": analysis,
        }
    
    def _identify_failure_source(
        self,
        trade_ctx: TradeContext,
        decision_ctx: DecisionContext,
        post_trade_ctx: Optional[Dict],
    ) -> Tuple[FailureSource, float]:
        """
        Identify the most likely failure source.
        """
        candidates = []
        
        # Check for TA error
        if decision_ctx.ta_score > 0.70 and trade_ctx.outcome == TradeOutcome.LOSS:
            candidates.append((FailureSource.TA_ERROR, 0.6))
        
        # Check for false breakout
        if decision_ctx.ta_score > 0.75 and abs(trade_ctx.pnl_percent) > 2:
            candidates.append((FailureSource.FALSE_BREAKOUT, 0.7))
        
        # Check for market regime shift
        if decision_ctx.market_state_score < 0.50:
            candidates.append((FailureSource.MARKET_REGIME_SHIFT, 0.65))
        
        # Check for ecology stress
        if decision_ctx.ecology_score < 0.50:
            candidates.append((FailureSource.ECOLOGY_STRESS, 0.6))
        
        # Check for interaction conflict
        if decision_ctx.interaction_score < 0.40:
            candidates.append((FailureSource.INTERACTION_CONFLICT, 0.55))
        
        # Check for structure vs flow conflict
        if decision_ctx.ta_score > 0.65 and decision_ctx.exchange_score < 0.45:
            candidates.append((FailureSource.STRUCTURE_FLOW_CONFLICT, 0.7))
        
        # Check for liquidity trap
        if decision_ctx.exchange_score < 0.40:
            candidates.append((FailureSource.LIQUIDITY_TRAP, 0.65))
        
        # Check for governance degradation
        if decision_ctx.governance_score < 0.50:
            candidates.append((FailureSource.GOVERNANCE_DEGRADATION, 0.5))
        
        # Check for crowding
        if post_trade_ctx and post_trade_ctx.get("crowding_detected", False):
            candidates.append((FailureSource.CROWDING_REVERSAL, 0.75))
        
        # Return highest confidence failure source
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0]
        
        # Default to model error
        return (FailureSource.TA_ERROR, 0.4)
    
    def _classify_failure(self, source: FailureSource) -> FailureClassification:
        """Classify the failure based on its source."""
        classification_map = {
            FailureSource.TA_ERROR: FailureClassification.MODEL_ERROR,
            FailureSource.FALSE_BREAKOUT: FailureClassification.MODEL_ERROR,
            FailureSource.MARKET_REGIME_SHIFT: FailureClassification.MARKET_REGIME_SHIFT,
            FailureSource.ECOLOGY_STRESS: FailureClassification.MARKET_REGIME_SHIFT,
            FailureSource.INTERACTION_CONFLICT: FailureClassification.MODEL_ERROR,
            FailureSource.STRUCTURE_FLOW_CONFLICT: FailureClassification.MODEL_ERROR,
            FailureSource.LIQUIDITY_TRAP: FailureClassification.EXECUTION_ERROR,
            FailureSource.EXECUTION_SLIPPAGE: FailureClassification.EXECUTION_ERROR,
            FailureSource.GOVERNANCE_DEGRADATION: FailureClassification.RISK_MODEL_ERROR,
            FailureSource.CROWDING_REVERSAL: FailureClassification.EXTERNAL_SHOCK,
        }
        return classification_map.get(source, FailureClassification.MODEL_ERROR)
    
    def _identify_responsible_layer(
        self,
        source: FailureSource,
        decision_ctx: DecisionContext,
    ) -> SystemLayer:
        """Identify which layer was primarily responsible."""
        layer_map = {
            FailureSource.TA_ERROR: SystemLayer.TA,
            FailureSource.FALSE_BREAKOUT: SystemLayer.TA,
            FailureSource.MARKET_REGIME_SHIFT: SystemLayer.MARKET_STATE,
            FailureSource.ECOLOGY_STRESS: SystemLayer.ECOLOGY,
            FailureSource.INTERACTION_CONFLICT: SystemLayer.INTERACTION,
            FailureSource.STRUCTURE_FLOW_CONFLICT: SystemLayer.EXCHANGE,
            FailureSource.LIQUIDITY_TRAP: SystemLayer.EXCHANGE,
            FailureSource.EXECUTION_SLIPPAGE: SystemLayer.EXECUTION,
            FailureSource.GOVERNANCE_DEGRADATION: SystemLayer.GOVERNANCE,
            FailureSource.CROWDING_REVERSAL: SystemLayer.EXCHANGE,
        }
        return layer_map.get(source, SystemLayer.TA)
    
    def _build_failure_analysis(
        self,
        source: FailureSource,
        classification: FailureClassification,
        responsible_layer: SystemLayer,
        trade_ctx: TradeContext,
        decision_ctx: DecisionContext,
    ) -> str:
        """Build human-readable failure analysis."""
        analyses = {
            FailureSource.TA_ERROR: "Technical analysis signal was incorrect. Pattern recognition may have misidentified the setup.",
            FailureSource.FALSE_BREAKOUT: "Breakout signal was false. Price reversed after initial move.",
            FailureSource.MARKET_REGIME_SHIFT: "Market regime shifted during the trade, invalidating the original thesis.",
            FailureSource.ECOLOGY_STRESS: "Alpha ecology was stressed, reducing factor effectiveness.",
            FailureSource.INTERACTION_CONFLICT: "Factor interactions were in conflict, leading to signal degradation.",
            FailureSource.STRUCTURE_FLOW_CONFLICT: "Market structure conflicted with order flow, creating trap setup.",
            FailureSource.LIQUIDITY_TRAP: "Trade caught in liquidity trap. Insufficient depth to exit cleanly.",
            FailureSource.EXECUTION_SLIPPAGE: "Execution slippage exceeded expectations due to market conditions.",
            FailureSource.GOVERNANCE_DEGRADATION: "Factor governance indicated degradation that was not properly weighted.",
            FailureSource.CROWDING_REVERSAL: "Crowded trade reversed as participants exited simultaneously.",
        }
        
        return analyses.get(source, "Unknown failure cause.")


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[FailureForensicsEngine] = None


def get_failure_forensics_engine() -> FailureForensicsEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FailureForensicsEngine()
    return _engine
