"""
PHASE 17.4 — Attribution Engine
================================
Main engine for trade attribution and failure forensics.

Transforms the system from "black box" to explainable trading system.

Analyzes:
- TAHypothesis
- ExchangeContext
- MarketState
- Alpha Ecology
- Alpha Interaction
- Decision Layer
- Position Sizing
- Execution Mode

Answers:
- WHY TRADE HAPPENED
- WHY TRADE FAILED
- WHICH LAYER WAS RESPONSIBLE
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import random

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")

from modules.research_control.attribution.attribution_types import (
    TradeAttributionReport,
    TradeContext,
    DecisionContext,
    TradeOutcome,
    TradeDirection,
    FailureClassification,
    FailureSource,
    SystemLayer,
    LayerContribution,
)
from modules.research_control.attribution.decision_trace_engine import get_decision_trace_engine
from modules.research_control.attribution.layer_contribution_engine import get_layer_contribution_engine
from modules.research_control.attribution.failure_forensics_engine import get_failure_forensics_engine
from modules.research_control.attribution.trade_explanation_engine import get_trade_explanation_engine


# ══════════════════════════════════════════════════════════════
# SIMULATED TRADE DATABASE
# ══════════════════════════════════════════════════════════════

SIMULATED_TRADES = {
    "BTC_2026_03_13_01": {
        "trade": TradeContext(
            trade_id="BTC_2026_03_13_01",
            symbol="BTCUSDT",
            direction=TradeDirection.SHORT,
            entry_price=68500.0,
            exit_price=69200.0,
            entry_time=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
            exit_time=datetime(2026, 3, 13, 14, 30, tzinfo=timezone.utc),
            position_size=0.75,
            outcome=TradeOutcome.LOSS,
            pnl=-525.0,
            pnl_percent=-1.02,
        ),
        "decision": DecisionContext(
            decision_confidence=0.72,
            ta_score=0.78,
            exchange_score=0.45,
            market_state_score=0.62,
            ecology_score=0.68,
            interaction_score=0.55,
            governance_score=0.70,
            primary_factor="trend_breakout_factor",
            secondary_factor="flow_imbalance_factor",
            execution_mode="NORMAL",
        ),
    },
    "ETH_2026_03_12_05": {
        "trade": TradeContext(
            trade_id="ETH_2026_03_12_05",
            symbol="ETHUSDT",
            direction=TradeDirection.LONG,
            entry_price=3850.0,
            exit_price=3980.0,
            entry_time=datetime(2026, 3, 12, 8, 0, tzinfo=timezone.utc),
            exit_time=datetime(2026, 3, 12, 16, 0, tzinfo=timezone.utc),
            position_size=0.85,
            outcome=TradeOutcome.WIN,
            pnl=1105.0,
            pnl_percent=3.38,
        ),
        "decision": DecisionContext(
            decision_confidence=0.82,
            ta_score=0.85,
            exchange_score=0.78,
            market_state_score=0.72,
            ecology_score=0.75,
            interaction_score=0.70,
            governance_score=0.80,
            primary_factor="structure_break_factor",
            secondary_factor="funding_arb_factor",
            execution_mode="AGGRESSIVE",
        ),
    },
    "SOL_2026_03_11_03": {
        "trade": TradeContext(
            trade_id="SOL_2026_03_11_03",
            symbol="SOLUSDT",
            direction=TradeDirection.LONG,
            entry_price=145.0,
            exit_price=138.5,
            entry_time=datetime(2026, 3, 11, 12, 0, tzinfo=timezone.utc),
            exit_time=datetime(2026, 3, 11, 18, 0, tzinfo=timezone.utc),
            position_size=0.60,
            outcome=TradeOutcome.LOSS,
            pnl=-390.0,
            pnl_percent=-4.48,
        ),
        "decision": DecisionContext(
            decision_confidence=0.65,
            ta_score=0.70,
            exchange_score=0.55,
            market_state_score=0.48,
            ecology_score=0.52,
            interaction_score=0.45,
            governance_score=0.58,
            primary_factor="divergence_factor",
            secondary_factor="volatility_regime_factor",
            execution_mode="NORMAL",
        ),
    },
    "BTC_2026_03_10_02": {
        "trade": TradeContext(
            trade_id="BTC_2026_03_10_02",
            symbol="BTCUSDT",
            direction=TradeDirection.LONG,
            entry_price=67000.0,
            exit_price=68200.0,
            entry_time=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
            exit_time=datetime(2026, 3, 10, 15, 0, tzinfo=timezone.utc),
            position_size=0.90,
            outcome=TradeOutcome.WIN,
            pnl=1080.0,
            pnl_percent=1.79,
        ),
        "decision": DecisionContext(
            decision_confidence=0.88,
            ta_score=0.90,
            exchange_score=0.82,
            market_state_score=0.78,
            ecology_score=0.80,
            interaction_score=0.75,
            governance_score=0.85,
            primary_factor="trend_breakout_factor",
            secondary_factor="funding_arb_factor",
            execution_mode="AGGRESSIVE",
        ),
    },
    "ETH_2026_03_09_01": {
        "trade": TradeContext(
            trade_id="ETH_2026_03_09_01",
            symbol="ETHUSDT",
            direction=TradeDirection.SHORT,
            entry_price=3920.0,
            exit_price=3920.0,
            entry_time=datetime(2026, 3, 9, 14, 0, tzinfo=timezone.utc),
            exit_time=datetime(2026, 3, 9, 18, 0, tzinfo=timezone.utc),
            position_size=0.50,
            outcome=TradeOutcome.BREAKEVEN,
            pnl=0.0,
            pnl_percent=0.0,
        ),
        "decision": DecisionContext(
            decision_confidence=0.60,
            ta_score=0.62,
            exchange_score=0.58,
            market_state_score=0.55,
            ecology_score=0.60,
            interaction_score=0.52,
            governance_score=0.65,
            primary_factor="mean_reversion_factor",
            secondary_factor="dominance_shift_factor",
            execution_mode="CONSERVATIVE",
        ),
    },
}


# ══════════════════════════════════════════════════════════════
# ATTRIBUTION ENGINE
# ══════════════════════════════════════════════════════════════

class AttributionEngine:
    """
    Attribution Engine - PHASE 17.4
    
    Final layer of Research Control Fabric.
    Transforms system from "black box" to explainable trading system.
    
    Key Functions:
    1. Explains WHY trade happened
    2. Explains WHY trade failed
    3. Shows WHICH LAYER was responsible
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        # Sub-engines
        self.decision_trace = get_decision_trace_engine()
        self.layer_contribution = get_layer_contribution_engine()
        self.failure_forensics = get_failure_forensics_engine()
        self.trade_explanation = get_trade_explanation_engine()
    
    # ═══════════════════════════════════════════════════════════
    # MAIN ATTRIBUTION
    # ═══════════════════════════════════════════════════════════
    
    def analyze_trade(self, trade_id: str) -> TradeAttributionReport:
        """
        Generate full attribution report for a trade.
        
        Args:
            trade_id: ID of the trade to analyze
        
        Returns:
            TradeAttributionReport with full analysis
        """
        now = datetime.now(timezone.utc)
        
        # Get trade and decision context
        trade_data = self._get_trade_data(trade_id)
        trade_context = trade_data["trade"]
        decision_context = trade_data["decision"]
        
        # Calculate layer contributions
        layer_contributions = self.layer_contribution.calculate_contributions(decision_context)
        layer_details = self.layer_contribution.get_detailed_contributions(decision_context)
        
        # Identify primary and secondary drivers
        primary_driver, secondary_driver = self.layer_contribution.identify_primary_secondary_drivers(
            decision_context
        )
        
        # Analyze failure (if applicable)
        failure_analysis = self.failure_forensics.analyze_failure(
            trade_context, decision_context
        )
        
        failure_source = failure_analysis.get("failure_reason")
        failure_classification = failure_analysis.get("failure_classification", FailureClassification.NONE)
        responsible_layer = failure_analysis.get("responsible_layer")
        
        # Generate explanation
        explanation = self.trade_explanation.generate_explanation(
            trade_context, decision_context, layer_contributions,
            failure_source, responsible_layer
        )
        
        # Generate breakdowns
        confidence_breakdown = self.trade_explanation.generate_confidence_breakdown(decision_context)
        risk_breakdown = self.trade_explanation.generate_risk_breakdown(decision_context)
        
        # Build drivers
        drivers = self._build_drivers(
            trade_context, decision_context, failure_analysis
        )
        
        return TradeAttributionReport(
            trade_id=trade_id,
            timestamp=now,
            trade_direction=trade_context.direction,
            trade_outcome=trade_context.outcome,
            decision_confidence=decision_context.decision_confidence,
            position_size=trade_context.position_size,
            primary_driver=decision_context.primary_factor,
            secondary_driver=decision_context.secondary_factor,
            layer_contributions=layer_contributions,
            failure_reason=failure_source,
            failure_classification=failure_classification,
            responsible_layer=responsible_layer,
            confidence_breakdown=confidence_breakdown,
            risk_breakdown=risk_breakdown,
            explanation=explanation,
            layer_details=layer_details,
            drivers=drivers,
        )
    
    def analyze_from_context(
        self,
        trade_id: str,
        trade_context: TradeContext,
        decision_context: DecisionContext,
    ) -> TradeAttributionReport:
        """
        Generate attribution report from provided context (for testing).
        """
        now = datetime.now(timezone.utc)
        
        # Calculate layer contributions
        layer_contributions = self.layer_contribution.calculate_contributions(decision_context)
        layer_details = self.layer_contribution.get_detailed_contributions(decision_context)
        
        # Identify drivers
        primary_driver, secondary_driver = self.layer_contribution.identify_primary_secondary_drivers(
            decision_context
        )
        
        # Analyze failure
        failure_analysis = self.failure_forensics.analyze_failure(
            trade_context, decision_context
        )
        
        failure_source = failure_analysis.get("failure_reason")
        failure_classification = failure_analysis.get("failure_classification", FailureClassification.NONE)
        responsible_layer = failure_analysis.get("responsible_layer")
        
        # Generate explanation
        explanation = self.trade_explanation.generate_explanation(
            trade_context, decision_context, layer_contributions,
            failure_source, responsible_layer
        )
        
        # Generate breakdowns
        confidence_breakdown = self.trade_explanation.generate_confidence_breakdown(decision_context)
        risk_breakdown = self.trade_explanation.generate_risk_breakdown(decision_context)
        
        return TradeAttributionReport(
            trade_id=trade_id,
            timestamp=now,
            trade_direction=trade_context.direction,
            trade_outcome=trade_context.outcome,
            decision_confidence=decision_context.decision_confidence,
            position_size=trade_context.position_size,
            primary_driver=decision_context.primary_factor,
            secondary_driver=decision_context.secondary_factor,
            layer_contributions=layer_contributions,
            failure_reason=failure_source,
            failure_classification=failure_classification,
            responsible_layer=responsible_layer,
            confidence_breakdown=confidence_breakdown,
            risk_breakdown=risk_breakdown,
            explanation=explanation,
            layer_details=layer_details,
            drivers={},
        )
    
    # ═══════════════════════════════════════════════════════════
    # DATA GATHERING
    # ═══════════════════════════════════════════════════════════
    
    def _get_trade_data(self, trade_id: str) -> Dict[str, Any]:
        """Get trade and decision data."""
        if trade_id in SIMULATED_TRADES:
            return SIMULATED_TRADES[trade_id]
        
        # Generate random trade for unknown IDs
        return self._generate_random_trade(trade_id)
    
    def _generate_random_trade(self, trade_id: str) -> Dict[str, Any]:
        """Generate a random trade for testing."""
        direction = random.choice([TradeDirection.LONG, TradeDirection.SHORT])
        outcome = random.choice([TradeOutcome.WIN, TradeOutcome.LOSS, TradeOutcome.BREAKEVEN])
        
        pnl_percent = 0.0
        if outcome == TradeOutcome.WIN:
            pnl_percent = random.uniform(0.5, 5.0)
        elif outcome == TradeOutcome.LOSS:
            pnl_percent = random.uniform(-5.0, -0.5)
        
        return {
            "trade": TradeContext(
                trade_id=trade_id,
                symbol="BTCUSDT",
                direction=direction,
                entry_price=68000.0,
                exit_price=68000.0 * (1 + pnl_percent/100),
                entry_time=datetime.now(timezone.utc),
                exit_time=datetime.now(timezone.utc),
                position_size=random.uniform(0.5, 1.0),
                outcome=outcome,
                pnl=pnl_percent * 100,
                pnl_percent=pnl_percent,
            ),
            "decision": DecisionContext(
                decision_confidence=random.uniform(0.55, 0.85),
                ta_score=random.uniform(0.50, 0.90),
                exchange_score=random.uniform(0.45, 0.85),
                market_state_score=random.uniform(0.45, 0.80),
                ecology_score=random.uniform(0.50, 0.80),
                interaction_score=random.uniform(0.40, 0.75),
                governance_score=random.uniform(0.55, 0.85),
                primary_factor="trend_breakout_factor",
                secondary_factor="flow_imbalance_factor",
                execution_mode="NORMAL",
            ),
        }
    
    def _build_drivers(
        self,
        trade_ctx: TradeContext,
        decision_ctx: DecisionContext,
        failure_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build explainability drivers."""
        return {
            "symbol": trade_ctx.symbol,
            "entry_price": trade_ctx.entry_price,
            "exit_price": trade_ctx.exit_price,
            "pnl": trade_ctx.pnl,
            "pnl_percent": trade_ctx.pnl_percent,
            "execution_mode": decision_ctx.execution_mode,
            "failure_analysis": failure_analysis.get("analysis"),
            "failure_confidence": failure_analysis.get("failure_confidence"),
        }
    
    # ═══════════════════════════════════════════════════════════
    # BATCH AND PUBLIC API
    # ═══════════════════════════════════════════════════════════
    
    def analyze_batch(self, trade_ids: List[str]) -> Dict[str, TradeAttributionReport]:
        """Analyze multiple trades at once."""
        results = {}
        for trade_id in trade_ids:
            results[trade_id] = self.analyze_trade(trade_id)
        return results
    
    def get_all_known_trades(self) -> List[str]:
        """Get list of all known trades."""
        return list(SIMULATED_TRADES.keys())


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[AttributionEngine] = None


def get_attribution_engine() -> AttributionEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = AttributionEngine()
    return _engine
