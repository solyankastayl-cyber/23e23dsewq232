"""
PHASE 45+ Production Infrastructure Tests

Tests for:
- Meta-Alpha Portfolio Engine (PHASE 45)
- Execution Reconciliation
- System Metrics
- Chaos Testing
- Stress Testing

40+ tests required.
"""

import pytest
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# Meta-Alpha Portfolio Tests (PHASE 45)
# ══════════════════════════════════════════════════════════════

from modules.meta_alpha_portfolio import (
    AlphaFamily,
    PatternClass,
    MetaAlphaWeight,
    MetaAlphaPortfolioState,
    MetaAlphaPortfolioEngine,
    get_meta_alpha_engine,
    META_SCORE_WEIGHTS,
    PATTERN_THRESHOLDS,
)


class TestMetaAlphaPortfolio:
    """Tests for Meta-Alpha Portfolio Engine."""
    
    def test_alpha_families_exist(self):
        """Test all alpha families exist."""
        assert AlphaFamily.TREND_BREAKOUT.value == "TREND_BREAKOUT"
        assert AlphaFamily.MEAN_REVERSION.value == "MEAN_REVERSION"
        assert AlphaFamily.FRACTAL.value == "FRACTAL"
        assert AlphaFamily.CAPITAL_FLOW.value == "CAPITAL_FLOW"
        assert AlphaFamily.REFLEXIVITY.value == "REFLEXIVITY"
    
    def test_pattern_classes(self):
        """Test pattern class thresholds."""
        assert PATTERN_THRESHOLDS["STRONG"] == 0.70
        assert PATTERN_THRESHOLDS["MODERATE"] == 0.55
    
    def test_meta_score_weights_sum(self):
        """Test meta score weights sum to 1."""
        total = sum(META_SCORE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001
    
    def test_engine_init(self):
        """Test engine initialization."""
        engine = MetaAlphaPortfolioEngine()
        assert len(engine._alpha_weights) == 5
    
    def test_engine_get_state(self):
        """Test getting portfolio state."""
        engine = MetaAlphaPortfolioEngine()
        state = engine.get_state()
        assert state.dominant_alpha_family is not None
        assert len(state.alpha_weights) == 5
    
    def test_engine_record_outcome(self):
        """Test recording trade outcome."""
        engine = MetaAlphaPortfolioEngine()
        outcome = engine.record_outcome(
            hypothesis_id="test_hyp",
            alpha_family=AlphaFamily.TREND_BREAKOUT,
            symbol="BTC",
            pnl_pct=2.5,
        )
        assert outcome.is_winner is True
        assert outcome.pnl_pct == 2.5
    
    def test_engine_recompute_weights(self):
        """Test weight recomputation."""
        engine = MetaAlphaPortfolioEngine()
        
        # Record some outcomes
        for i in range(15):
            engine.record_outcome(
                hypothesis_id=f"hyp_{i}",
                alpha_family=AlphaFamily.TREND_BREAKOUT,
                symbol="BTC",
                pnl_pct=1.0 if i % 2 == 0 else -0.5,
            )
        
        state = engine.recompute_weights()
        assert state.total_signals_tracked == 15
    
    def test_hypothesis_modifier(self):
        """Test hypothesis modifier."""
        engine = MetaAlphaPortfolioEngine()
        result = engine.get_hypothesis_modifier(AlphaFamily.TREND_BREAKOUT)
        assert "modifier" in result
        assert "meta_score" in result
    
    def test_portfolio_allocation_weights(self):
        """Test portfolio allocation weights."""
        engine = MetaAlphaPortfolioEngine()
        weights = engine.get_portfolio_allocation_weights()
        assert len(weights) == 5
        assert abs(sum(weights.values()) - 1.0) < 0.01
    
    def test_risk_budget_weights(self):
        """Test risk budget weights."""
        engine = MetaAlphaPortfolioEngine()
        weights = engine.get_risk_budget_weights()
        assert len(weights) == 5
    
    def test_meta_weight_compute_score(self):
        """Test MetaAlphaWeight score computation."""
        weight = MetaAlphaWeight(
            alpha_family=AlphaFamily.TREND_BREAKOUT,
            recent_success_rate=0.7,
            recent_avg_pnl=2.0,
            regime_fit_score=0.8,
            decay_adjusted_score=0.75,
        )
        score = weight.compute_meta_score()
        assert 0 <= score <= 1
    
    def test_singleton(self):
        """Test singleton instance."""
        e1 = get_meta_alpha_engine()
        e2 = get_meta_alpha_engine()
        assert e1 is e2


# ══════════════════════════════════════════════════════════════
# Execution Reconciliation Tests
# ══════════════════════════════════════════════════════════════

from modules.execution_reconciliation import (
    MismatchType,
    ReconciliationResult,
    ReconciliationState,
    ReconciliationConfig,
    ExecutionReconciliationEngine,
    get_reconciliation_engine,
)


class TestExecutionReconciliation:
    """Tests for Execution Reconciliation."""
    
    def test_mismatch_types(self):
        """Test mismatch types exist."""
        assert MismatchType.POSITION_SIZE.value == "POSITION_SIZE"
        assert MismatchType.BALANCE_MISMATCH.value == "BALANCE_MISMATCH"
        assert MismatchType.ORDER_ORPHAN.value == "ORDER_ORPHAN"
    
    def test_config_defaults(self):
        """Test default configuration."""
        config = ReconciliationConfig()
        assert config.check_interval_seconds == 15
        assert config.auto_correct_enabled is True
    
    def test_engine_init(self):
        """Test engine initialization."""
        engine = ExecutionReconciliationEngine()
        assert engine._state.is_synced is True
    
    def test_engine_get_state(self):
        """Test getting state."""
        engine = ExecutionReconciliationEngine()
        state = engine.get_state()
        assert isinstance(state, ReconciliationState)
    
    def test_engine_get_summary(self):
        """Test getting summary."""
        engine = ExecutionReconciliationEngine()
        summary = engine.get_summary()
        assert "is_synced" in summary
        assert "total_checks" in summary
    
    def test_singleton_reconciliation(self):
        """Test singleton instance."""
        e1 = get_reconciliation_engine()
        e2 = get_reconciliation_engine()
        assert e1 is e2


# ══════════════════════════════════════════════════════════════
# System Metrics Tests
# ══════════════════════════════════════════════════════════════

from modules.system_metrics import (
    MetricType,
    MetricSample,
    SystemMetrics,
    SystemHealth,
    SystemMetricsEngine,
    get_metrics_engine,
)


class TestSystemMetrics:
    """Tests for System Metrics."""
    
    def test_metric_types(self):
        """Test metric types."""
        assert MetricType.LATENCY == "latency"
        assert MetricType.SLIPPAGE == "slippage"
    
    def test_engine_init(self):
        """Test engine initialization."""
        engine = SystemMetricsEngine()
        assert engine._total_signals == 0
    
    def test_record_latency(self):
        """Test recording latency."""
        engine = SystemMetricsEngine()
        engine.record_latency(50.0, "test_endpoint")
        assert len(engine._latency_samples) == 1
    
    def test_record_signal(self):
        """Test recording signal."""
        engine = SystemMetricsEngine()
        engine.record_signal()
        assert engine._total_signals == 1
    
    def test_record_error(self):
        """Test recording error."""
        engine = SystemMetricsEngine()
        engine.record_error("test_error")
        assert engine._total_errors == 1
    
    def test_get_metrics(self):
        """Test getting metrics."""
        engine = SystemMetricsEngine()
        metrics = engine.get_metrics()
        assert isinstance(metrics, SystemMetrics)
        assert metrics.memory_usage_pct >= 0
    
    def test_get_health(self):
        """Test getting health."""
        engine = SystemMetricsEngine()
        health = engine.get_health()
        assert isinstance(health, SystemHealth)
        assert health.status in ["HEALTHY", "DEGRADED", "UNHEALTHY"]
    
    def test_get_summary(self):
        """Test getting summary."""
        engine = SystemMetricsEngine()
        summary = engine.get_summary()
        assert "health_status" in summary
        assert "metrics" in summary
    
    def test_singleton_metrics(self):
        """Test singleton instance."""
        e1 = get_metrics_engine()
        e2 = get_metrics_engine()
        assert e1 is e2


# ══════════════════════════════════════════════════════════════
# Chaos Testing Tests
# ══════════════════════════════════════════════════════════════

from modules.system_chaos import (
    ChaosType,
    ChaosConfig,
    ChaosResult,
    ChaosState,
    SystemChaosEngine,
    get_chaos_engine,
)


class TestChaosEngine:
    """Tests for Chaos Engine."""
    
    def test_chaos_types(self):
        """Test chaos types exist."""
        assert ChaosType.EXCHANGE_DISCONNECT.value == "EXCHANGE_DISCONNECT"
        assert ChaosType.LATENCY_SPIKE.value == "LATENCY_SPIKE"
        assert ChaosType.SIGNAL_STORM.value == "SIGNAL_STORM"
    
    def test_chaos_config(self):
        """Test chaos config."""
        config = ChaosConfig(
            chaos_type=ChaosType.LATENCY_SPIKE,
            duration_seconds=10,
            intensity=0.5,
        )
        assert config.duration_seconds == 10
    
    def test_engine_init(self):
        """Test engine initialization."""
        engine = SystemChaosEngine()
        assert engine._state.is_chaos_active is False
    
    def test_engine_get_state(self):
        """Test getting state."""
        engine = SystemChaosEngine()
        state = engine.get_state()
        assert isinstance(state, ChaosState)
    
    def test_engine_get_summary(self):
        """Test getting summary."""
        engine = SystemChaosEngine()
        summary = engine.get_summary()
        assert "available_chaos_types" in summary
        assert len(summary["available_chaos_types"]) == 8
    
    def test_singleton_chaos(self):
        """Test singleton instance."""
        e1 = get_chaos_engine()
        e2 = get_chaos_engine()
        assert e1 is e2


# ══════════════════════════════════════════════════════════════
# Stress Testing Tests
# ══════════════════════════════════════════════════════════════

from modules.stress_testing import (
    StressTestType,
    StressTestConfig,
    StressTestMetrics,
    StressTestResult,
    StressTestEngine,
    get_stress_engine,
)


class TestStressEngine:
    """Tests for Stress Engine."""
    
    def test_stress_types(self):
        """Test stress test types."""
        assert StressTestType.SIGNAL_THROUGHPUT.value == "SIGNAL_THROUGHPUT"
        assert StressTestType.SIGNAL_BURST.value == "SIGNAL_BURST"
        assert StressTestType.FULL_SYSTEM.value == "FULL_SYSTEM"
    
    def test_stress_config(self):
        """Test stress config."""
        config = StressTestConfig(
            test_type=StressTestType.SIGNAL_THROUGHPUT,
            duration_seconds=30,
            target_rate=50,
        )
        assert config.target_rate == 50
    
    def test_engine_init(self):
        """Test engine initialization."""
        engine = StressTestEngine()
        assert engine._is_running is False
    
    def test_engine_get_summary(self):
        """Test getting summary."""
        engine = StressTestEngine()
        summary = engine.get_summary()
        assert "available_tests" in summary
        assert len(summary["available_tests"]) == 7
    
    def test_thresholds(self):
        """Test default thresholds."""
        engine = StressTestEngine()
        assert engine._latency_threshold_ms == 1000
        assert engine._error_threshold_pct == 1.0
    
    def test_singleton_stress(self):
        """Test singleton instance."""
        e1 = get_stress_engine()
        e2 = get_stress_engine()
        assert e1 is e2


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
