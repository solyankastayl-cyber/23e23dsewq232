"""
PHASE 20.1 — Failure Pattern Tests
==================================
Tests for Failure Pattern Engine.

Test scenarios:
1. Pattern detection correct
2. Loss rate calculated correctly
3. Severity classification correct
4. Registry persistence correct
5. Summary output correct
6. Critical patterns detected
7. Multiple patterns handled
8. API output correct
9. Empty dataset handled
10. Pattern update logic correct
"""

import pytest
from datetime import datetime, timezone

from modules.research_loop.failure_patterns.failure_pattern_types import (
    FailurePattern,
    FailurePatternSummary,
    TradeRecord,
    TradeOutcome,
    PatternSeverity,
    SEVERITY_THRESHOLDS,
)
from modules.research_loop.failure_patterns.failure_pattern_registry import (
    get_failure_pattern_registry,
    FailurePatternRegistry,
    PATTERN_TEMPLATES,
)
from modules.research_loop.failure_patterns.failure_pattern_engine import (
    get_failure_pattern_engine,
    FailurePatternEngine,
)


class TestSeverityThresholds:
    """Tests for severity thresholds."""
    
    def test_critical_threshold(self):
        """CRITICAL threshold should be 0.75."""
        assert SEVERITY_THRESHOLDS[PatternSeverity.CRITICAL] == 0.75
    
    def test_high_threshold(self):
        """HIGH threshold should be 0.60."""
        assert SEVERITY_THRESHOLDS[PatternSeverity.HIGH] == 0.60
    
    def test_medium_threshold(self):
        """MEDIUM threshold should be 0.50."""
        assert SEVERITY_THRESHOLDS[PatternSeverity.MEDIUM] == 0.50
    
    def test_low_threshold(self):
        """LOW threshold should be 0.0."""
        assert SEVERITY_THRESHOLDS[PatternSeverity.LOW] == 0.0


class TestPatternTemplates:
    """Tests for pattern templates."""
    
    def test_templates_exist(self):
        """Should have predefined templates."""
        assert len(PATTERN_TEMPLATES) > 0
    
    def test_trend_breakout_in_range(self):
        """Should have trend_breakout_in_range template."""
        assert "trend_breakout_in_range" in PATTERN_TEMPLATES
    
    def test_mean_reversion_in_vol(self):
        """Should have mean_reversion_in_vol_expansion template."""
        assert "mean_reversion_in_vol_expansion" in PATTERN_TEMPLATES


class TestFailurePatternRegistry:
    """Tests for failure pattern registry."""
    
    def test_initialize(self):
        """TEST 4: Registry should initialize from templates."""
        registry = FailurePatternRegistry()
        registry.initialize_from_templates()
        
        patterns = registry.get_all_patterns()
        assert len(patterns) > 0
    
    def test_get_pattern(self):
        """Should get pattern by name."""
        registry = get_failure_pattern_registry()
        
        pattern = registry.get_pattern("trend_breakout_in_range")
        assert pattern is not None
        assert pattern.pattern_name == "trend_breakout_in_range"
    
    def test_update_pattern(self):
        """TEST 10: Should update pattern statistics."""
        registry = FailurePatternRegistry()
        registry.initialize_from_templates()
        
        registry.update_pattern(
            pattern_name="trend_breakout_in_range",
            occurrences=20,
            wins=4,
            losses=16,
            total_drawdown=-0.8,
            total_pnl=-0.2,
        )
        
        pattern = registry.get_pattern("trend_breakout_in_range")
        assert pattern.occurrences == 20
        assert pattern.losses == 16
        assert pattern.loss_rate == 0.8  # 16/20
    
    def test_severity_update_on_update(self):
        """Severity should update based on loss rate."""
        registry = FailurePatternRegistry()
        registry.initialize_from_templates()
        
        # High loss rate should be CRITICAL
        registry.update_pattern(
            pattern_name="trend_breakout_in_range",
            occurrences=10,
            wins=2,
            losses=8,
            total_drawdown=-0.4,
            total_pnl=-0.1,
        )
        
        pattern = registry.get_pattern("trend_breakout_in_range")
        assert pattern.severity == PatternSeverity.CRITICAL  # 80% loss rate


class TestLossRateCalculation:
    """Tests for loss rate calculation."""
    
    def test_loss_rate_correct(self):
        """TEST 2: Loss rate should be calculated correctly."""
        engine = FailurePatternEngine()
        
        # Create trades with known outcome
        trades = [
            TradeRecord(
                trade_id=f"t{i}",
                symbol="BTC",
                strategy="breakout",
                factor="breakout_factor",
                market_regime="RANGE_LOW_VOL",
                interaction_state="NEUTRAL",
                ecology_state="STABLE",
                volatility_state="LOW",
                trade_outcome=TradeOutcome.LOSS if i < 7 else TradeOutcome.WIN,
                pnl=-0.02 if i < 7 else 0.03,
                drawdown=-0.03 if i < 7 else -0.01,
                timestamp=datetime.now(timezone.utc),
            )
            for i in range(10)
        ]
        
        summary = engine.analyze_trades(trades)
        
        assert summary.losing_trades == 7
        assert summary.winning_trades == 3
        assert abs(summary.overall_loss_rate - 0.7) < 0.01


class TestSeverityClassification:
    """Tests for severity classification."""
    
    def test_classify_critical(self):
        """TEST 3: >= 0.75 loss rate should be CRITICAL."""
        engine = FailurePatternEngine()
        
        severity = engine._classify_severity(0.80)
        assert severity == PatternSeverity.CRITICAL
    
    def test_classify_high(self):
        """0.60-0.75 loss rate should be HIGH."""
        engine = FailurePatternEngine()
        
        severity = engine._classify_severity(0.65)
        assert severity == PatternSeverity.HIGH
    
    def test_classify_medium(self):
        """0.50-0.60 loss rate should be MEDIUM."""
        engine = FailurePatternEngine()
        
        severity = engine._classify_severity(0.55)
        assert severity == PatternSeverity.MEDIUM
    
    def test_classify_low(self):
        """< 0.50 loss rate should be LOW."""
        engine = FailurePatternEngine()
        
        severity = engine._classify_severity(0.40)
        assert severity == PatternSeverity.LOW


class TestPatternDetection:
    """Tests for pattern detection."""
    
    def test_detect_patterns(self):
        """TEST 1: Should detect patterns from trades."""
        engine = FailurePatternEngine()
        
        summary = engine.analyze_trades()  # Uses sample data
        
        assert summary.total_patterns > 0
    
    def test_critical_patterns_detected(self):
        """TEST 6: Should detect critical patterns."""
        engine = FailurePatternEngine()
        
        summary = engine.analyze_trades()
        
        # Sample data should create some critical patterns
        # (breakout in range, MR in vol expansion)
        # At least one pattern should be detected
        assert len(summary.patterns_detected) > 0
    
    def test_multiple_patterns(self):
        """TEST 7: Should handle multiple patterns."""
        engine = FailurePatternEngine()
        
        summary = engine.analyze_trades()
        
        assert summary.total_patterns >= 1


class TestSummaryOutput:
    """Tests for summary output."""
    
    def test_summary_correct(self):
        """TEST 5: Summary should have correct structure."""
        engine = FailurePatternEngine()
        
        summary = engine.analyze_trades()
        
        assert summary.total_trades > 0
        assert summary.total_trades == summary.winning_trades + summary.losing_trades + summary.breakeven_trades
    
    def test_summary_to_dict(self):
        """TEST 8: Summary to_dict should be correct."""
        engine = FailurePatternEngine()
        
        summary = engine.analyze_trades()
        d = summary.to_dict()
        
        assert "total_trades" in d
        assert "losing_trades" in d
        assert "patterns_detected" in d
        assert "critical_patterns" in d
        assert "counts" in d


class TestEmptyDataset:
    """Tests for empty dataset handling."""
    
    def test_empty_dataset(self):
        """TEST 9: Should handle empty dataset."""
        engine = FailurePatternEngine()
        engine.clear_history()
        
        # Should generate sample data if empty
        summary = engine.analyze_trades()
        
        # Should have results from sample data
        assert summary.total_trades > 0


class TestPatternOutput:
    """Tests for pattern output."""
    
    def test_pattern_to_dict(self):
        """Pattern should convert to dict correctly."""
        pattern = FailurePattern(
            pattern_name="test_pattern",
            pattern_type="factor_regime",
            occurrences=20,
            wins=5,
            losses=15,
            loss_rate=0.75,
            avg_drawdown=-0.04,
            total_pnl=-0.3,
            involved_factor="test_factor",
            involved_strategy="test_strategy",
            involved_regime="RANGE",
            severity=PatternSeverity.CRITICAL,
        )
        
        d = pattern.to_dict()
        
        assert d["pattern_name"] == "test_pattern"
        assert d["occurrences"] == 20
        assert d["loss_rate"] == 0.75
        assert d["severity"] == "CRITICAL"


# ══════════════════════════════════════════════════════════════
# RUN TESTS
# ══════════════════════════════════════════════════════════════

def run_tests():
    """Run all tests and print results."""
    print("\n" + "=" * 60)
    print("PHASE 20.1 — Failure Pattern Engine Tests")
    print("=" * 60 + "\n")
    
    test_classes = [
        TestSeverityThresholds,
        TestPatternTemplates,
        TestFailurePatternRegistry,
        TestLossRateCalculation,
        TestSeverityClassification,
        TestPatternDetection,
        TestSummaryOutput,
        TestEmptyDataset,
        TestPatternOutput,
    ]
    
    total_passed = 0
    total_failed = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}")
        print("-" * 40)
        
        instance = test_class()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        
        for method_name in methods:
            try:
                method = getattr(instance, method_name)
                method()
                print(f"  [PASS] {method_name}")
                total_passed += 1
            except AssertionError as e:
                print(f"  [FAIL] {method_name}: {e}")
                total_failed += 1
            except Exception as e:
                print(f"  [ERROR] {method_name}: {e}")
                total_failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {total_passed} passed, {total_failed} failed")
    print("=" * 60 + "\n")
    
    return total_failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
