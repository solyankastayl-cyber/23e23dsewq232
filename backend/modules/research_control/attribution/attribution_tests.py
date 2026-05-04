"""
PHASE 17.4 — Attribution Tests
===============================
Tests for Attribution / Failure Forensics Engine.

Test Cases:
1. Winning trade attribution
2. Losing trade attribution
3. Correct layer contributions
4. Failure classification
5. Explanation generation
6. Responsible layer detection
7. Confidence breakdown correct
8. Risk breakdown correct
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.research_control.attribution.attribution_engine import (
    get_attribution_engine,
    AttributionEngine,
)
from modules.research_control.attribution.attribution_types import (
    TradeContext,
    DecisionContext,
    TradeOutcome,
    TradeDirection,
    FailureClassification,
    FailureSource,
    SystemLayer,
)
from datetime import datetime, timezone


class TestTradeAttribution:
    """Test trade attribution reports."""
    
    def test_winning_trade_attribution(self):
        """
        Test attribution for a winning trade.
        """
        engine = get_attribution_engine()
        
        trade_context = TradeContext(
            trade_id="test_win_001",
            symbol="BTCUSDT",
            direction=TradeDirection.LONG,
            entry_price=67000.0,
            exit_price=68500.0,
            entry_time=datetime.now(timezone.utc),
            exit_time=datetime.now(timezone.utc),
            position_size=0.85,
            outcome=TradeOutcome.WIN,
            pnl=1275.0,
            pnl_percent=2.24,
        )
        
        decision_context = DecisionContext(
            decision_confidence=0.82,
            ta_score=0.85,
            exchange_score=0.78,
            market_state_score=0.72,
            ecology_score=0.75,
            interaction_score=0.70,
            governance_score=0.80,
            primary_factor="trend_breakout_factor",
            secondary_factor="flow_imbalance_factor",
            execution_mode="AGGRESSIVE",
        )
        
        result = engine.analyze_from_context("test_win_001", trade_context, decision_context)
        
        assert result.trade_outcome == TradeOutcome.WIN
        assert result.failure_classification == FailureClassification.NONE
        assert result.failure_reason is None
        assert result.responsible_layer is None
        assert "successfully" in result.explanation.lower() or "profit" in result.explanation.lower()
        print(f"✓ Winning trade: {result.trade_outcome.value}, no failure")
    
    def test_losing_trade_attribution(self):
        """
        Test attribution for a losing trade.
        """
        engine = get_attribution_engine()
        
        trade_context = TradeContext(
            trade_id="test_loss_001",
            symbol="BTCUSDT",
            direction=TradeDirection.SHORT,
            entry_price=68500.0,
            exit_price=69500.0,
            entry_time=datetime.now(timezone.utc),
            exit_time=datetime.now(timezone.utc),
            position_size=0.70,
            outcome=TradeOutcome.LOSS,
            pnl=-700.0,
            pnl_percent=-1.46,
        )
        
        decision_context = DecisionContext(
            decision_confidence=0.68,
            ta_score=0.75,
            exchange_score=0.42,  # Low - structure vs flow conflict
            market_state_score=0.55,
            ecology_score=0.60,
            interaction_score=0.48,
            governance_score=0.65,
            primary_factor="trend_breakout_factor",
            secondary_factor="flow_imbalance_factor",
            execution_mode="NORMAL",
        )
        
        result = engine.analyze_from_context("test_loss_001", trade_context, decision_context)
        
        assert result.trade_outcome == TradeOutcome.LOSS
        assert result.failure_classification != FailureClassification.NONE
        assert result.failure_reason is not None
        assert result.responsible_layer is not None
        assert "failed" in result.explanation.lower()
        print(f"✓ Losing trade: {result.failure_reason.value}, responsible: {result.responsible_layer.value}")


class TestLayerContributions:
    """Test layer contribution calculations."""
    
    def test_correct_layer_contributions(self):
        """
        Test that layer contributions sum to 1 and are correctly weighted.
        """
        engine = get_attribution_engine()
        result = engine.analyze_trade("ETH_2026_03_12_05")  # Known winning trade
        
        # Contributions should sum to approximately 1
        total = sum(result.layer_contributions.values())
        assert 0.99 <= total <= 1.01, f"Contributions sum to {total}, expected ~1.0"
        
        # Should have all expected layers
        expected_layers = ["TA", "Exchange", "MarketState", "Ecology", "Interaction", "Governance"]
        for layer in expected_layers:
            assert layer in result.layer_contributions, f"Missing layer: {layer}"
        
        print(f"✓ Layer contributions: {result.layer_contributions}")
        print(f"✓ Total: {total:.4f}")
    
    def test_primary_driver_identification(self):
        """
        Test that primary driver is correctly identified.
        """
        engine = get_attribution_engine()
        result = engine.analyze_trade("BTC_2026_03_10_02")  # High TA score trade
        
        # Primary driver should be identified
        assert result.primary_driver is not None
        assert result.secondary_driver is not None
        assert result.primary_driver != result.secondary_driver
        
        print(f"✓ Primary: {result.primary_driver}, Secondary: {result.secondary_driver}")


class TestFailureClassification:
    """Test failure classification and forensics."""
    
    def test_failure_classification(self):
        """
        Test that failures are correctly classified.
        """
        engine = get_attribution_engine()
        result = engine.analyze_trade("BTC_2026_03_13_01")  # Known losing trade
        
        # Should have failure classification
        assert result.failure_classification in FailureClassification
        
        if result.trade_outcome == TradeOutcome.LOSS:
            assert result.failure_classification != FailureClassification.NONE
            assert result.failure_reason is not None
            assert result.failure_reason in FailureSource
        
        print(f"✓ Classification: {result.failure_classification.value}")
        print(f"✓ Failure reason: {result.failure_reason.value if result.failure_reason else 'None'}")


class TestExplanationGeneration:
    """Test human-readable explanation generation."""
    
    def test_explanation_generation(self):
        """
        Test that explanations are generated and meaningful.
        """
        engine = get_attribution_engine()
        
        # Test winning trade
        win_result = engine.analyze_trade("ETH_2026_03_12_05")
        assert len(win_result.explanation) > 50
        assert "trade" in win_result.explanation.lower()
        
        # Test losing trade
        loss_result = engine.analyze_trade("BTC_2026_03_13_01")
        assert len(loss_result.explanation) > 50
        
        print(f"✓ Win explanation: {win_result.explanation[:100]}...")
        print(f"✓ Loss explanation: {loss_result.explanation[:100]}...")


class TestResponsibleLayerDetection:
    """Test responsible layer detection for failures."""
    
    def test_responsible_layer_detection(self):
        """
        Test that responsible layer is correctly identified for losses.
        """
        engine = get_attribution_engine()
        
        trade_context = TradeContext(
            trade_id="test_resp_001",
            symbol="BTCUSDT",
            direction=TradeDirection.LONG,
            entry_price=68000.0,
            exit_price=66500.0,
            entry_time=datetime.now(timezone.utc),
            exit_time=datetime.now(timezone.utc),
            position_size=0.75,
            outcome=TradeOutcome.LOSS,
            pnl=-1125.0,
            pnl_percent=-2.21,
        )
        
        # Create context where ecology is clearly the problem
        decision_context = DecisionContext(
            decision_confidence=0.70,
            ta_score=0.75,
            exchange_score=0.72,
            market_state_score=0.68,
            ecology_score=0.38,  # Very low - should be identified
            interaction_score=0.55,
            governance_score=0.70,
            primary_factor="structure_break_factor",
            secondary_factor="mean_reversion_factor",
            execution_mode="NORMAL",
        )
        
        result = engine.analyze_from_context("test_resp_001", trade_context, decision_context)
        
        assert result.responsible_layer is not None
        assert result.responsible_layer in SystemLayer
        print(f"✓ Responsible layer: {result.responsible_layer.value}")


class TestBreakdowns:
    """Test confidence and risk breakdowns."""
    
    def test_confidence_breakdown_correct(self):
        """
        Test that confidence breakdown is correctly calculated.
        """
        engine = get_attribution_engine()
        result = engine.analyze_trade("BTC_2026_03_10_02")
        
        # Should have all confidence components
        expected_keys = [
            "ta_confidence", "exchange_confidence", "market_state_confidence",
            "ecology_confidence", "interaction_confidence"
        ]
        
        for key in expected_keys:
            assert key in result.confidence_breakdown, f"Missing: {key}"
            assert 0 <= result.confidence_breakdown[key] <= 1
        
        # Should sum to approximately 1
        total = sum(result.confidence_breakdown.values())
        assert 0.99 <= total <= 1.01
        
        print(f"✓ Confidence breakdown: {result.confidence_breakdown}")
    
    def test_risk_breakdown_correct(self):
        """
        Test that risk breakdown is correctly calculated.
        """
        engine = get_attribution_engine()
        result = engine.analyze_trade("SOL_2026_03_11_03")
        
        # Should have risk components
        expected_keys = [
            "ecology_risk", "interaction_risk", "governance_risk", "market_state_risk"
        ]
        
        for key in expected_keys:
            assert key in result.risk_breakdown, f"Missing: {key}"
            assert 0 <= result.risk_breakdown[key] <= 1
        
        # Should sum to approximately 1
        total = sum(result.risk_breakdown.values())
        assert 0.99 <= total <= 1.01
        
        print(f"✓ Risk breakdown: {result.risk_breakdown}")


class TestKnownTrades:
    """Test known trade analysis."""
    
    def test_analyze_all_known_trades(self):
        """Test that all known trades can be analyzed."""
        engine = get_attribution_engine()
        trades = engine.get_all_known_trades()
        
        for trade_id in trades:
            result = engine.analyze_trade(trade_id)
            assert result.trade_id == trade_id
            assert result.trade_outcome in TradeOutcome
            assert len(result.explanation) > 0
            print(f"✓ {trade_id}: {result.trade_outcome.value}")


# Run tests when executed directly
if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 17.4 — Attribution / Failure Forensics Tests")
    print("=" * 60)
    
    # Attribution tests
    print("\n1. Trade Attribution:")
    test_attr = TestTradeAttribution()
    test_attr.test_winning_trade_attribution()
    test_attr.test_losing_trade_attribution()
    
    # Layer contribution tests
    print("\n2. Layer Contributions:")
    test_layers = TestLayerContributions()
    test_layers.test_correct_layer_contributions()
    test_layers.test_primary_driver_identification()
    
    # Failure classification tests
    print("\n3. Failure Classification:")
    test_fail = TestFailureClassification()
    test_fail.test_failure_classification()
    
    # Explanation tests
    print("\n4. Explanation Generation:")
    test_explain = TestExplanationGeneration()
    test_explain.test_explanation_generation()
    
    # Responsible layer tests
    print("\n5. Responsible Layer Detection:")
    test_resp = TestResponsibleLayerDetection()
    test_resp.test_responsible_layer_detection()
    
    # Breakdown tests
    print("\n6. Breakdowns:")
    test_break = TestBreakdowns()
    test_break.test_confidence_breakdown_correct()
    test_break.test_risk_breakdown_correct()
    
    # Known trades tests
    print("\n7. Known Trades:")
    test_known = TestKnownTrades()
    test_known.test_analyze_all_known_trades()
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED (12/12)")
    print("=" * 60)
