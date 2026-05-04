"""
Cockpit State Aggregator

PHASE 33 — System Control Layer

Aggregates all system state for UI cockpit display.
"""

from typing import Optional, Dict, List
from datetime import datetime, timezone

from .control_types import (
    CockpitState,
    ControlSummary,
    MarketDecisionState,
    RiskState,
    Alert,
)

from .decision_engine import get_decision_engine
from .risk_engine import get_risk_engine
from .alert_engine import get_alert_engine


# ══════════════════════════════════════════════════════════════
# Cockpit State Aggregator
# ══════════════════════════════════════════════════════════════

class CockpitStateAggregator:
    """
    Cockpit State Aggregator — PHASE 33
    
    Aggregates decision, risk, and alert state into a unified
    cockpit state for UI display.
    """
    
    def __init__(self):
        self._states: Dict[str, CockpitState] = {}
    
    def get_cockpit_state(
        self,
        symbol: str,
    ) -> CockpitState:
        """
        Get complete cockpit state for symbol.
        """
        symbol = symbol.upper()
        
        # Get decision engine
        decision_engine = get_decision_engine()
        decision = decision_engine.get_current_decision(symbol)
        if decision is None:
            decision = decision_engine.generate_decision(symbol)
        
        # Get risk engine
        risk_engine = get_risk_engine()
        risk = risk_engine.get_current_risk(symbol)
        if risk is None:
            risk = risk_engine.assess_risk(symbol)
        
        # Get alert engine
        alert_engine = get_alert_engine()
        alerts = alert_engine.check_and_generate_alerts(symbol)
        active_alerts = alert_engine.get_active_alerts(symbol)
        
        # Get capital allocation
        allocation = self._get_capital_allocation(symbol)
        
        cockpit = CockpitState(
            symbol=symbol,
            decision_state=decision,
            risk_state=risk,
            top_hypothesis=decision.hypothesis_type,
            top_scenario=decision.top_scenario_type,
            capital_allocation=allocation,
            alerts=active_alerts,
            active_alert_count=len(active_alerts),
            system_status="OPERATIONAL",
        )
        
        self._states[symbol] = cockpit
        
        return cockpit
    
    def _get_capital_allocation(self, symbol: str) -> Dict[str, float]:
        """Get capital allocation for symbol."""
        try:
            from modules.capital_allocation import get_capital_allocation_engine
            engine = get_capital_allocation_engine()
            allocation = engine.get_current_allocation(symbol)
            if allocation:
                return {
                    "weight": allocation.weight if hasattr(allocation, 'weight') else 0.5,
                    "long_weight": allocation.long_weight if hasattr(allocation, 'long_weight') else 0.5,
                    "short_weight": allocation.short_weight if hasattr(allocation, 'short_weight') else 0.0,
                }
        except Exception:
            pass
        
        return {
            "weight": 0.5,
            "long_weight": 0.5,
            "short_weight": 0.0,
        }
    
    def get_control_summary(
        self,
        symbols: List[str],
    ) -> ControlSummary:
        """
        Get summary across multiple symbols.
        """
        high_risk = []
        extreme_risk = []
        opportunities = []
        total_alerts = 0
        critical_alerts = 0
        
        for symbol in symbols:
            symbol = symbol.upper()
            
            # Get or create state
            if symbol in self._states:
                cockpit = self._states[symbol]
            else:
                cockpit = self.get_cockpit_state(symbol)
            
            # Count alerts
            total_alerts += cockpit.active_alert_count
            critical_alerts += len([a for a in cockpit.alerts if a.severity == "CRITICAL"])
            
            # Categorize by risk
            if cockpit.risk_state.risk_level == "EXTREME":
                extreme_risk.append(symbol)
            elif cockpit.risk_state.risk_level == "HIGH":
                high_risk.append(symbol)
            
            # Find opportunities
            if (cockpit.decision_state.market_state in ["BREAKOUT_SETUP", "TRENDING"]
                and cockpit.decision_state.confidence > 0.65
                and cockpit.risk_state.risk_level in ["LOW", "MEDIUM"]):
                opportunities.append(symbol)
        
        return ControlSummary(
            symbols_monitored=symbols,
            total_alerts=total_alerts,
            critical_alerts=critical_alerts,
            high_risk_symbols=high_risk,
            extreme_risk_symbols=extreme_risk,
            opportunity_symbols=opportunities,
            system_status="OPERATIONAL",
        )
    
    def recompute_all(
        self,
        symbol: str,
    ) -> CockpitState:
        """
        Force recomputation of all states.
        """
        symbol = symbol.upper()
        
        # Recompute decision
        decision_engine = get_decision_engine()
        decision = decision_engine.generate_decision(symbol)
        
        # Recompute risk
        risk_engine = get_risk_engine()
        risk = risk_engine.assess_risk(symbol)
        
        # Generate fresh alerts
        alert_engine = get_alert_engine()
        alerts = alert_engine.check_and_generate_alerts(symbol)
        active_alerts = alert_engine.get_active_alerts(symbol)
        
        # Get capital allocation
        allocation = self._get_capital_allocation(symbol)
        
        cockpit = CockpitState(
            symbol=symbol,
            decision_state=decision,
            risk_state=risk,
            top_hypothesis=decision.hypothesis_type,
            top_scenario=decision.top_scenario_type,
            capital_allocation=allocation,
            alerts=active_alerts,
            active_alert_count=len(active_alerts),
            system_status="OPERATIONAL",
        )
        
        self._states[symbol] = cockpit
        
        return cockpit


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_cockpit_aggregator: Optional[CockpitStateAggregator] = None


def get_cockpit_aggregator() -> CockpitStateAggregator:
    """Get singleton instance of CockpitStateAggregator."""
    global _cockpit_aggregator
    if _cockpit_aggregator is None:
        _cockpit_aggregator = CockpitStateAggregator()
    return _cockpit_aggregator
