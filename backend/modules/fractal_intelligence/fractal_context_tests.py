"""
PHASE 24.1 — Fractal Context Tests

Test suite for Fractal Intelligence module.
Covers: adapter, engine, context states, fallbacks.
"""

import pytest
from datetime import datetime
from typing import Dict

from .fractal_context_types import (
    FractalContext,
    HorizonBias,
    RawFractalSignal,
    RawFractalDecision,
    RawFractalGovernance,
    RawPhaseResponse,
)
from .fractal_context_adapter import FractalContextAdapter
from .fractal_context_engine import FractalContextEngine


class TestFractalContextAdapter:
    """Tests for FractalContextAdapter."""
    
    def test_map_direction_long(self):
        """Test mapping BUY -> LONG."""
        adapter = FractalContextAdapter()
        assert adapter.map_direction("BUY") == "LONG"
        assert adapter.map_direction("LONG") == "LONG"
        assert adapter.map_direction("buy") == "LONG"
    
    def test_map_direction_short(self):
        """Test mapping SELL -> SHORT."""
        adapter = FractalContextAdapter()
        assert adapter.map_direction("SELL") == "SHORT"
        assert adapter.map_direction("SHORT") == "SHORT"
        assert adapter.map_direction("sell") == "SHORT"
    
    def test_map_direction_hold(self):
        """Test mapping HOLD/NEUTRAL -> HOLD."""
        adapter = FractalContextAdapter()
        assert adapter.map_direction("HOLD") == "HOLD"
        assert adapter.map_direction("NEUTRAL") == "HOLD"
        assert adapter.map_direction("unknown") == "HOLD"
        assert adapter.map_direction("") == "HOLD"
    
    def test_adapt_basic_signal(self):
        """Test adapting a basic signal."""
        adapter = FractalContextAdapter()
        
        signal = RawFractalSignal(
            decision=RawFractalDecision(
                action="BUY",
                confidence=0.72,
                reliability=0.68,
            ),
            horizons=[
                {"h": 7, "confidence": 0.65, "weight": 0.25, "expectedReturn": 0.021},
                {"h": 14, "confidence": 0.72, "weight": 0.45, "expectedReturn": 0.048},
                {"h": 30, "confidence": 0.58, "weight": 0.30, "expectedReturn": 0.071},
            ],
            governance=RawFractalGovernance(mode="NORMAL"),
        )
        
        result = adapter.adapt(signal)
        
        assert result["direction"] == "LONG"
        assert result["confidence"] == 0.72
        assert result["reliability"] == 0.68
        assert result["dominant_horizon"] == 14  # highest conf * weight
        assert result["governance_mode"] == "NORMAL"
    
    def test_adapt_with_phase(self):
        """Test adapting with phase response."""
        adapter = FractalContextAdapter()
        
        signal = RawFractalSignal(
            decision=RawFractalDecision(action="SELL", confidence=0.65, reliability=0.70),
            horizons=[],
            governance=RawFractalGovernance(mode="PROTECTION"),
        )
        
        phase = RawPhaseResponse(ok=True, phase="MARKDOWN", confidence=0.78)
        
        result = adapter.adapt(signal, phase_response=phase)
        
        assert result["direction"] == "SHORT"
        assert result["phase"] == "MARKDOWN"
        assert result["phase_confidence_raw"] == 0.78
        assert result["governance_mode"] == "PROTECTION"


class TestFractalContextEngine:
    """Tests for FractalContextEngine."""
    
    def get_engine(self) -> FractalContextEngine:
        """Create engine without client for sync tests."""
        return FractalContextEngine()
    
    def test_compute_fractal_strength(self):
        """Test fractal strength calculation."""
        engine = self.get_engine()
        
        # Formula: 0.45 * conf + 0.35 * rel + 0.20 * phase_conf
        strength = engine.compute_fractal_strength(
            confidence=0.68,
            reliability=0.72,
            phase_confidence=0.49,
        )
        
        expected = 0.45 * 0.68 + 0.35 * 0.72 + 0.20 * 0.49
        assert abs(strength - expected) < 0.001
    
    def test_compute_fractal_strength_clamped(self):
        """Test that strength is clamped to 0..1."""
        engine = self.get_engine()
        
        # High values should be clamped
        strength = engine.compute_fractal_strength(1.5, 1.2, 1.1)
        assert 0.0 <= strength <= 1.0
        
        # Low values should be clamped
        strength = engine.compute_fractal_strength(-0.1, -0.2, -0.3)
        assert 0.0 <= strength <= 1.0
    
    def test_context_state_supportive(self):
        """Test SUPPORTIVE state classification."""
        engine = self.get_engine()
        
        state = engine.determine_context_state(
            direction="LONG",
            confidence=0.68,
            reliability=0.72,
            governance_mode="NORMAL",
            expected_return=0.05,
        )
        
        assert state == "SUPPORTIVE"
    
    def test_context_state_neutral_hold(self):
        """Test NEUTRAL state for HOLD direction."""
        engine = self.get_engine()
        
        state = engine.determine_context_state(
            direction="HOLD",
            confidence=0.50,
            reliability=0.60,
            governance_mode="NORMAL",
            expected_return=None,
        )
        
        assert state == "NEUTRAL"
    
    def test_context_state_neutral_low_confidence(self):
        """Test NEUTRAL state for low confidence."""
        engine = self.get_engine()
        
        state = engine.determine_context_state(
            direction="LONG",
            confidence=0.45,  # Below SUPPORTIVE threshold
            reliability=0.70,
            governance_mode="NORMAL",
            expected_return=0.03,
        )
        
        assert state == "NEUTRAL"
    
    def test_context_state_conflicted_low_reliability(self):
        """Test CONFLICTED state for low reliability."""
        engine = self.get_engine()
        
        state = engine.determine_context_state(
            direction="LONG",
            confidence=0.65,  # Above CONFLICTED threshold
            reliability=0.35,  # Below CONFLICTED reliability threshold
            governance_mode="NORMAL",
            expected_return=0.03,
        )
        
        assert state == "CONFLICTED"
    
    def test_context_state_conflicted_return_mismatch(self):
        """Test CONFLICTED state when direction conflicts with expected return."""
        engine = self.get_engine()
        
        # LONG direction but negative expected return
        state = engine.determine_context_state(
            direction="LONG",
            confidence=0.65,
            reliability=0.70,
            governance_mode="NORMAL",
            expected_return=-0.02,  # Negative = conflicting with LONG
        )
        
        assert state == "CONFLICTED"
    
    def test_context_state_blocked_halt(self):
        """Test BLOCKED state for HALT governance."""
        engine = self.get_engine()
        
        state = engine.determine_context_state(
            direction="LONG",
            confidence=0.80,
            reliability=0.85,
            governance_mode="HALT",
            expected_return=0.05,
        )
        
        assert state == "BLOCKED"
    
    def test_context_state_blocked_frozen(self):
        """Test BLOCKED state for FROZEN_ONLY governance."""
        engine = self.get_engine()
        
        state = engine.determine_context_state(
            direction="SHORT",
            confidence=0.75,
            reliability=0.80,
            governance_mode="FROZEN_ONLY",
            expected_return=-0.03,
        )
        
        assert state == "BLOCKED"
    
    def test_context_state_blocked_low_reliability(self):
        """Test BLOCKED state for very low reliability."""
        engine = self.get_engine()
        
        state = engine.determine_context_state(
            direction="LONG",
            confidence=0.70,
            reliability=0.15,  # Below BLOCKED threshold (0.20)
            governance_mode="NORMAL",
            expected_return=0.05,
        )
        
        assert state == "BLOCKED"
    
    def test_build_context_sync(self):
        """Test synchronous context building."""
        engine = self.get_engine()
        
        horizon_bias = {
            "7": HorizonBias(expected_return=0.021, confidence=0.61, weight=0.25),
            "14": HorizonBias(expected_return=0.048, confidence=0.72, weight=0.45),
            "30": HorizonBias(expected_return=0.071, confidence=0.58, weight=0.30),
        }
        
        context = engine.build_context_sync(
            direction="LONG",
            confidence=0.68,
            reliability=0.72,
            horizon_bias=horizon_bias,
            dominant_horizon=14,
            expected_return=0.048,
            phase="MARKUP",
            governance_mode="NORMAL",
        )
        
        assert context.direction == "LONG"
        assert context.confidence == 0.68
        assert context.reliability == 0.72
        assert context.dominant_horizon == 14
        assert context.phase == "MARKUP"
        assert context.context_state == "SUPPORTIVE"
        assert 0.0 <= context.fractal_strength <= 1.0
        assert "strong long fractal" in context.reason.lower()
    
    def test_generate_reason_supportive(self):
        """Test reason generation for SUPPORTIVE state."""
        engine = self.get_engine()
        
        reason = engine.generate_reason(
            context_state="SUPPORTIVE",
            direction="LONG",
            confidence=0.68,
            reliability=0.72,
            phase="MARKUP",
            dominant_horizon=14,
            governance_mode="NORMAL",
        )
        
        assert "long" in reason.lower()
        assert "14d" in reason
        assert "markup" in reason.lower()
    
    def test_generate_reason_blocked(self):
        """Test reason generation for BLOCKED state."""
        engine = self.get_engine()
        
        reason = engine.generate_reason(
            context_state="BLOCKED",
            direction="LONG",
            confidence=0.70,
            reliability=0.15,
            phase=None,
            dominant_horizon=None,
            governance_mode="NORMAL",
        )
        
        assert "reliability" in reason.lower() or "low" in reason.lower()
    
    def test_summary_extraction(self):
        """Test summary extraction from full context."""
        engine = self.get_engine()
        
        context = engine.build_context_sync(
            direction="SHORT",
            confidence=0.65,
            reliability=0.60,
            horizon_bias={},
            dominant_horizon=30,
            expected_return=-0.03,
            phase="MARKDOWN",
            governance_mode="NORMAL",
        )
        
        summary = engine.get_summary(context)
        
        assert summary.direction == "SHORT"
        assert summary.confidence == 0.65
        assert summary.phase == "MARKDOWN"
        assert summary.dominant_horizon == 30


class TestFallbackBehavior:
    """Tests for fallback behavior when fractal service unavailable."""
    
    def test_fallback_signal_returns_hold(self):
        """Test that fallback signal returns HOLD."""
        from .fractal_context_client import FractalClient
        
        client = FractalClient()
        fallback = client._get_fallback_signal()
        
        assert fallback.decision.action == "HOLD"
        assert fallback.decision.confidence == 0.0
        assert fallback.decision.reliability == 0.0
        assert fallback.governance.mode == "HALT"
    
    def test_fallback_produces_blocked_context(self):
        """Test that fallback signal produces BLOCKED context."""
        engine = FractalContextEngine()
        adapter = FractalContextAdapter()
        
        from .fractal_context_client import FractalClient
        client = FractalClient()
        fallback = client._get_fallback_signal()
        
        adapted = adapter.adapt(fallback)
        
        assert adapted["direction"] == "HOLD"
        assert adapted["confidence"] == 0.0
        assert adapted["governance_mode"] == "HALT"
        
        # Building context should produce BLOCKED state
        context = engine.build_context_sync(
            direction=adapted["direction"],
            confidence=adapted["confidence"],
            reliability=adapted["reliability"],
            horizon_bias={},
            governance_mode=adapted["governance_mode"],
        )
        
        assert context.context_state == "BLOCKED"


class TestDominantHorizonSelection:
    """Tests for dominant horizon selection logic."""
    
    def test_dominant_horizon_by_confidence_weight(self):
        """Test that dominant horizon is selected by confidence * weight."""
        adapter = FractalContextAdapter()
        
        signal = RawFractalSignal(
            decision=RawFractalDecision(action="LONG", confidence=0.70, reliability=0.65),
            horizons=[
                {"h": 7, "confidence": 0.80, "weight": 0.20, "expectedReturn": 0.02},   # score: 0.16
                {"h": 14, "confidence": 0.65, "weight": 0.35, "expectedReturn": 0.04},  # score: 0.2275
                {"h": 30, "confidence": 0.55, "weight": 0.45, "expectedReturn": 0.06},  # score: 0.2475
            ],
            governance=RawFractalGovernance(mode="NORMAL"),
        )
        
        result = adapter.adapt(signal)
        
        # 30d has highest conf * weight (0.55 * 0.45 = 0.2475)
        assert result["dominant_horizon"] == 30
        assert result["expected_return"] == 0.06
    
    def test_empty_horizons_returns_none(self):
        """Test that empty horizons returns None for dominant."""
        adapter = FractalContextAdapter()
        
        signal = RawFractalSignal(
            decision=RawFractalDecision(action="HOLD", confidence=0.40, reliability=0.50),
            horizons=[],
            governance=RawFractalGovernance(mode="NORMAL"),
        )
        
        result = adapter.adapt(signal)
        
        assert result["dominant_horizon"] is None
        assert result["expected_return"] is None


def run_tests():
    """Run all tests and return results."""
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": [],
    }
    
    test_classes = [
        TestFractalContextAdapter,
        TestFractalContextEngine,
        TestFallbackBehavior,
        TestDominantHorizonSelection,
    ]
    
    for test_class in test_classes:
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                results["total"] += 1
                try:
                    getattr(instance, method_name)()
                    results["passed"] += 1
                    print(f"  PASS: {test_class.__name__}.{method_name}")
                except AssertionError as e:
                    results["failed"] += 1
                    results["errors"].append(f"{test_class.__name__}.{method_name}: {e}")
                    print(f"  FAIL: {test_class.__name__}.{method_name} - {e}")
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"{test_class.__name__}.{method_name}: {e}")
                    print(f"  ERROR: {test_class.__name__}.{method_name} - {e}")
    
    return results


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PHASE 24.1 — Fractal Intelligence Tests")
    print("="*60 + "\n")
    
    results = run_tests()
    
    print("\n" + "="*60)
    print(f"Results: {results['passed']}/{results['total']} passed")
    if results["errors"]:
        print("\nErrors:")
        for err in results["errors"]:
            print(f"  - {err}")
    print("="*60 + "\n")
