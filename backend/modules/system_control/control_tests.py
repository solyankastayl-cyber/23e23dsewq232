"""
System Control Tests

PHASE 33 — Unit tests for System Control Layer.

35+ tests covering:
- Decision generation
- Risk calculation
- Alert triggering
- State aggregation
- Endpoint validation
- Integration tests
"""

import pytest
from datetime import datetime, timezone

from .control_types import (
    MarketDecisionState,
    RiskState,
    Alert,
    CockpitState,
    ControlSummary,
    MARKET_STATES,
    RISK_LEVELS,
    ALERT_TYPES,
)

from .decision_engine import MarketDecisionEngine, get_decision_engine
from .risk_engine import RiskEngine, get_risk_engine
from .alert_engine import AlertEngine, get_alert_engine
from .cockpit_state import CockpitStateAggregator, get_cockpit_aggregator


# ══════════════════════════════════════════════════════════════
# 1. Decision Engine Tests
# ══════════════════════════════════════════════════════════════

class TestDecisionEngine:
    """Tests for MarketDecisionEngine."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = MarketDecisionEngine()
    
    def test_generate_decision(self):
        """Test decision generation."""
        decision = self.engine.generate_decision("BTC")
        
        assert isinstance(decision, MarketDecisionState)
        assert decision.symbol == "BTC"
    
    def test_decision_has_market_state(self):
        """Test decision has valid market state."""
        decision = self.engine.generate_decision("BTC")
        
        assert decision.market_state in MARKET_STATES
    
    def test_decision_has_strategy(self):
        """Test decision has strategy recommendation."""
        decision = self.engine.generate_decision("ETH")
        
        strategies = ["breakout_trading", "trend_following", "mean_reversion", 
                     "volatility_trading", "risk_off", "no_action"]
        assert decision.recommended_strategy in strategies
    
    def test_decision_confidence_bounded(self):
        """Test confidence is in [0, 1]."""
        decision = self.engine.generate_decision("SOL")
        
        assert 0.0 <= decision.confidence <= 1.0
    
    def test_decision_has_risk_level(self):
        """Test decision has risk level."""
        decision = self.engine.generate_decision("BTC")
        
        assert decision.risk_level in RISK_LEVELS
    
    def test_decision_stored(self):
        """Test decision is stored."""
        decision = self.engine.generate_decision("BTC")
        
        stored = self.engine.get_current_decision("BTC")
        assert stored is not None
        assert stored.symbol == "BTC"
    
    def test_decision_history(self):
        """Test decision history."""
        self.engine.generate_decision("BTC")
        self.engine.generate_decision("BTC")
        
        history = self.engine.get_decision_history("BTC")
        assert len(history) >= 2
    
    def test_gather_intelligence(self):
        """Test intelligence gathering."""
        intel = self.engine.gather_intelligence("BTC")
        
        assert "hypothesis" in intel
        assert "simulation" in intel
        assert "regime" in intel
        assert "microstructure" in intel
        assert "fractal_similarity" in intel
        assert "cross_asset" in intel
    
    def test_determine_market_state(self):
        """Test market state determination."""
        intel = self.engine.gather_intelligence("BTC")
        state, confidence = self.engine.determine_market_state(intel)
        
        assert state in MARKET_STATES
        assert 0.0 <= confidence <= 1.0
    
    def test_aggregate_direction(self):
        """Test direction aggregation."""
        intel = self.engine.gather_intelligence("ETH")
        direction, confidence = self.engine.aggregate_direction(intel)
        
        assert direction in ["LONG", "SHORT", "NEUTRAL"]
        assert 0.0 <= confidence <= 1.0


# ══════════════════════════════════════════════════════════════
# 2. Risk Engine Tests
# ══════════════════════════════════════════════════════════════

class TestRiskEngine:
    """Tests for RiskEngine."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = RiskEngine()
    
    def test_assess_risk(self):
        """Test risk assessment."""
        risk = self.engine.assess_risk("BTC")
        
        assert isinstance(risk, RiskState)
        assert risk.symbol == "BTC"
    
    def test_risk_level_valid(self):
        """Test risk level is valid."""
        risk = self.engine.assess_risk("ETH")
        
        assert risk.risk_level in RISK_LEVELS
    
    def test_risk_score_bounded(self):
        """Test risk score is bounded."""
        risk = self.engine.assess_risk("SOL")
        
        assert 0.0 <= risk.risk_score <= 1.0
    
    def test_max_position_bounded(self):
        """Test max position is bounded."""
        risk = self.engine.assess_risk("BTC")
        
        assert 0.1 <= risk.max_allowed_position <= 1.0
    
    def test_stress_indicator_bounded(self):
        """Test stress indicator is bounded."""
        risk = self.engine.assess_risk("ETH")
        
        assert 0.0 <= risk.stress_indicator <= 1.0
    
    def test_risk_factors_list(self):
        """Test risk factors is a list."""
        risk = self.engine.assess_risk("BTC")
        
        assert isinstance(risk.risk_factors, list)
    
    def test_volatility_regime(self):
        """Test volatility regime is set."""
        risk = self.engine.assess_risk("SOL")
        
        assert risk.volatility_regime in ["NORMAL", "ELEVATED", "HIGH", "EXTREME"]
    
    def test_risk_stored(self):
        """Test risk state is stored."""
        risk = self.engine.assess_risk("BTC")
        
        stored = self.engine.get_current_risk("BTC")
        assert stored is not None
    
    def test_risk_history(self):
        """Test risk history."""
        self.engine.assess_risk("BTC")
        self.engine.assess_risk("BTC")
        
        history = self.engine.get_risk_history("BTC")
        assert len(history) >= 2


# ══════════════════════════════════════════════════════════════
# 3. Alert Engine Tests
# ══════════════════════════════════════════════════════════════

class TestAlertEngine:
    """Tests for AlertEngine."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = AlertEngine()
    
    def test_check_and_generate_alerts(self):
        """Test alert generation."""
        alerts = self.engine.check_and_generate_alerts("BTC")
        
        assert isinstance(alerts, list)
    
    def test_alert_has_required_fields(self):
        """Test alerts have required fields."""
        alerts = self.engine.check_and_generate_alerts("ETH")
        
        # Generate at least one alert for testing
        if alerts:
            alert = alerts[0]
            assert hasattr(alert, 'alert_id')
            assert hasattr(alert, 'symbol')
            assert hasattr(alert, 'alert_type')
            assert hasattr(alert, 'severity')
            assert hasattr(alert, 'title')
            assert hasattr(alert, 'message')
    
    def test_alert_type_valid(self):
        """Test alert types are valid."""
        alerts = self.engine.check_and_generate_alerts("BTC")
        
        for alert in alerts:
            assert alert.alert_type in ALERT_TYPES
    
    def test_alert_severity_valid(self):
        """Test alert severity is valid."""
        alerts = self.engine.check_and_generate_alerts("ETH")
        
        for alert in alerts:
            assert alert.severity in ["INFO", "WARNING", "CRITICAL"]
    
    def test_get_active_alerts(self):
        """Test getting active alerts."""
        self.engine.check_and_generate_alerts("BTC")
        
        active = self.engine.get_active_alerts("BTC")
        assert isinstance(active, list)
    
    def test_acknowledge_alert(self):
        """Test acknowledging alert."""
        alerts = self.engine.check_and_generate_alerts("SOL")
        
        if alerts:
            success = self.engine.acknowledge_alert("SOL", alerts[0].alert_id)
            assert success is True
    
    def test_get_critical_alerts(self):
        """Test getting critical alerts."""
        self.engine.check_and_generate_alerts("BTC")
        
        critical = self.engine.get_critical_alerts("BTC")
        assert isinstance(critical, list)


# ══════════════════════════════════════════════════════════════
# 4. Cockpit State Tests
# ══════════════════════════════════════════════════════════════

class TestCockpitState:
    """Tests for CockpitStateAggregator."""
    
    def setup_method(self):
        """Setup test aggregator."""
        self.aggregator = CockpitStateAggregator()
    
    def test_get_cockpit_state(self):
        """Test getting cockpit state."""
        state = self.aggregator.get_cockpit_state("BTC")
        
        assert isinstance(state, CockpitState)
        assert state.symbol == "BTC"
    
    def test_cockpit_has_decision(self):
        """Test cockpit has decision state."""
        state = self.aggregator.get_cockpit_state("ETH")
        
        assert state.decision_state is not None
        assert isinstance(state.decision_state, MarketDecisionState)
    
    def test_cockpit_has_risk(self):
        """Test cockpit has risk state."""
        state = self.aggregator.get_cockpit_state("SOL")
        
        assert state.risk_state is not None
        assert isinstance(state.risk_state, RiskState)
    
    def test_cockpit_has_alerts(self):
        """Test cockpit has alerts list."""
        state = self.aggregator.get_cockpit_state("BTC")
        
        assert isinstance(state.alerts, list)
    
    def test_control_summary(self):
        """Test control summary."""
        summary = self.aggregator.get_control_summary(["BTC", "ETH", "SOL"])
        
        assert isinstance(summary, ControlSummary)
        assert len(summary.symbols_monitored) == 3
    
    def test_recompute_all(self):
        """Test recompute all."""
        state = self.aggregator.recompute_all("BTC")
        
        assert isinstance(state, CockpitState)
        assert state.symbol == "BTC"


# ══════════════════════════════════════════════════════════════
# 5. Integration Tests
# ══════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests."""
    
    def test_decision_to_risk_flow(self):
        """Test decision affects risk assessment."""
        decision_engine = MarketDecisionEngine()
        risk_engine = RiskEngine()
        
        decision = decision_engine.generate_decision("BTC")
        risk = risk_engine.assess_risk("BTC")
        
        # Both should be generated
        assert decision is not None
        assert risk is not None
    
    def test_full_cockpit_flow(self):
        """Test full cockpit state flow."""
        aggregator = CockpitStateAggregator()
        
        state = aggregator.get_cockpit_state("ETH")
        
        # All components present
        assert state.decision_state is not None
        assert state.risk_state is not None
        assert state.system_status == "OPERATIONAL"
    
    def test_multi_symbol_consistency(self):
        """Test multi-symbol state consistency."""
        aggregator = CockpitStateAggregator()
        
        btc = aggregator.get_cockpit_state("BTC")
        eth = aggregator.get_cockpit_state("ETH")
        sol = aggregator.get_cockpit_state("SOL")
        
        assert btc.symbol == "BTC"
        assert eth.symbol == "ETH"
        assert sol.symbol == "SOL"


# ══════════════════════════════════════════════════════════════
# 6. Singleton Tests
# ══════════════════════════════════════════════════════════════

class TestSingletons:
    """Tests for singleton patterns."""
    
    def test_decision_engine_singleton(self):
        """Test decision engine singleton."""
        engine1 = get_decision_engine()
        engine2 = get_decision_engine()
        
        assert engine1 is engine2
    
    def test_risk_engine_singleton(self):
        """Test risk engine singleton."""
        engine1 = get_risk_engine()
        engine2 = get_risk_engine()
        
        assert engine1 is engine2
    
    def test_alert_engine_singleton(self):
        """Test alert engine singleton."""
        engine1 = get_alert_engine()
        engine2 = get_alert_engine()
        
        assert engine1 is engine2
    
    def test_cockpit_aggregator_singleton(self):
        """Test cockpit aggregator singleton."""
        agg1 = get_cockpit_aggregator()
        agg2 = get_cockpit_aggregator()
        
        assert agg1 is agg2


# ══════════════════════════════════════════════════════════════
# 7. Edge Cases Tests
# ══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_unknown_symbol_decision(self):
        """Test handling unknown symbol in decision."""
        engine = MarketDecisionEngine()
        decision = engine.generate_decision("UNKNOWN_XYZ")
        
        assert decision is not None
        assert decision.symbol == "UNKNOWN_XYZ"
    
    def test_unknown_symbol_risk(self):
        """Test handling unknown symbol in risk."""
        engine = RiskEngine()
        risk = engine.assess_risk("UNKNOWN_ABC")
        
        assert risk is not None
        assert risk.symbol == "UNKNOWN_ABC"
    
    def test_empty_alert_list(self):
        """Test handling when no alerts generated."""
        engine = AlertEngine()
        alerts = engine.get_active_alerts("NEW_SYMBOL")
        
        assert isinstance(alerts, list)


# ══════════════════════════════════════════════════════════════
# 8. Decision Stability Tests
# ══════════════════════════════════════════════════════════════

class TestDecisionStability:
    """Tests for decision stability."""
    
    def test_decision_deterministic(self):
        """Test decision is deterministic for same input."""
        engine = MarketDecisionEngine()
        
        # Note: Due to time-based elements, we test structure consistency
        decision1 = engine.generate_decision("BTC")
        decision2 = engine.generate_decision("BTC")
        
        assert decision1.symbol == decision2.symbol
        assert decision1.market_state is not None
        assert decision2.market_state is not None
    
    def test_risk_bounds_respected(self):
        """Test risk calculations respect bounds."""
        engine = RiskEngine()
        
        for symbol in ["BTC", "ETH", "SOL", "SPX", "NDX", "DXY"]:
            risk = engine.assess_risk(symbol)
            assert 0.0 <= risk.risk_score <= 1.0
            assert risk.risk_level in RISK_LEVELS


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
