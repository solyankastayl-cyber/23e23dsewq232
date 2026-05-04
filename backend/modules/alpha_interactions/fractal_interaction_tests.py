"""
PHASE 24.2 — Fractal Interaction Tests

Test suite for Fractal Intelligence integration into Alpha Interaction Layer.
"""

import pytest
from datetime import datetime, timezone

from modules.alpha_interactions.fractal_interaction_types import (
    FractalInputForInteraction,
    FractalInteractionResult,
    FractalInteractionState,
    DominantSignal,
    MODIFIER_BOUNDS,
)
from modules.alpha_interactions.fractal_interaction_engine import (
    FractalInteractionEngine,
    get_fractal_interaction_engine,
)
from modules.alpha_interactions.alpha_interaction_types import (
    TAInputForInteraction,
    ExchangeInputForInteraction,
)


def make_ta_input(direction: str = "LONG", conviction: float = 0.65) -> TAInputForInteraction:
    """Helper to create TA input."""
    return TAInputForInteraction(
        direction=direction,
        conviction=conviction,
        trend_strength=0.60,
        setup_quality=0.70,
        regime="TREND_UP" if direction == "LONG" else "TREND_DOWN",
    )


def make_exchange_input(bias: str = "BULLISH", confidence: float = 0.60) -> ExchangeInputForInteraction:
    """Helper to create Exchange input."""
    return ExchangeInputForInteraction(
        bias=bias,
        confidence=confidence,
        dominant_signal="flow",
        conflict_ratio=0.2,
    )


def make_fractal_input(
    direction: str = "LONG",
    confidence: float = 0.68,
    reliability: float = 0.72,
    phase: str = "MARKUP",
    context_state: str = "SUPPORTIVE",
    fractal_strength: float = 0.65,
) -> FractalInputForInteraction:
    """Helper to create Fractal input."""
    return FractalInputForInteraction(
        direction=direction,
        confidence=confidence,
        reliability=reliability,
        phase=phase,
        context_state=context_state,
        fractal_strength=fractal_strength,
        dominant_horizon=14,
        expected_return=0.048,
    )


class TestTAFractalAlignment:
    """Test Pattern 1: TA ↔ Fractal Alignment."""
    
    def test_ta_fractal_alignment_boosts_confidence(self):
        """TA + Fractal alignment with SUPPORTIVE state boosts confidence."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input(direction="LONG", conviction=0.65)
        exchange = make_exchange_input(bias="BULLISH")
        fractal = make_fractal_input(
            direction="LONG",
            context_state="SUPPORTIVE",
            fractal_strength=0.65,
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        assert "ta_fractal_alignment" in result.patterns_detected
        assert result.confidence_modifier > 1.0
        assert result.capital_modifier > 1.0
    
    def test_ta_fractal_alignment_requires_supportive(self):
        """Alignment pattern requires SUPPORTIVE context state."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input(direction="LONG")
        exchange = make_exchange_input()
        fractal = make_fractal_input(
            direction="LONG",
            context_state="NEUTRAL",  # Not SUPPORTIVE
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        assert "ta_fractal_alignment" not in result.patterns_detected


class TestExchangeFractalAlignment:
    """Test Pattern 2: Exchange ↔ Fractal Alignment."""
    
    def test_exchange_fractal_alignment_boosts_confidence(self):
        """Exchange + Fractal alignment with strength > 0.55 boosts confidence."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input(direction="LONG")
        exchange = make_exchange_input(bias="BULLISH")
        fractal = make_fractal_input(
            direction="LONG",
            context_state="NEUTRAL",  # Not SUPPORTIVE
            fractal_strength=0.60,     # Above 0.55
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        assert "exchange_fractal_alignment" in result.patterns_detected
    
    def test_exchange_fractal_alignment_requires_strength(self):
        """Alignment requires fractal_strength > 0.55."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input()
        exchange = make_exchange_input(bias="BULLISH")
        fractal = make_fractal_input(
            direction="LONG",
            fractal_strength=0.50,  # Below threshold
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        assert "exchange_fractal_alignment" not in result.patterns_detected


class TestFractalConflict:
    """Test Pattern 3: Fractal Conflict."""
    
    def test_fractal_conflict_reduces_confidence(self):
        """TA vs Fractal conflict with strength >= 0.60 reduces confidence."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input(direction="LONG")
        exchange = make_exchange_input(bias="BULLISH")
        fractal = make_fractal_input(
            direction="SHORT",          # Opposite of TA
            context_state="SUPPORTIVE",
            fractal_strength=0.65,      # >= 0.60
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        assert "fractal_conflict" in result.patterns_detected
        assert result.confidence_modifier < 1.0
        assert result.capital_modifier < 1.0
        assert result.interaction_state == FractalInteractionState.CONFLICTED
    
    def test_fractal_conflict_requires_strength(self):
        """Conflict requires fractal_strength >= 0.60."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input(direction="LONG")
        exchange = make_exchange_input()
        fractal = make_fractal_input(
            direction="SHORT",
            fractal_strength=0.55,  # Below threshold
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        assert "fractal_conflict" not in result.patterns_detected


class TestPhaseDirectionSupport:
    """Test Pattern 4: Phase Direction Support."""
    
    def test_markup_supports_long(self):
        """MARKUP phase supports LONG direction."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input(direction="LONG")
        exchange = make_exchange_input()
        fractal = make_fractal_input(
            direction="LONG",
            phase="MARKUP",
            fractal_strength=0.55,
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        assert "phase_direction_support" in result.patterns_detected
    
    def test_markdown_supports_short(self):
        """MARKDOWN phase supports SHORT direction."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input(direction="SHORT")
        exchange = make_exchange_input(bias="BEARISH")
        fractal = make_fractal_input(
            direction="SHORT",
            phase="MARKDOWN",
            fractal_strength=0.55,
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        assert "phase_direction_support" in result.patterns_detected
    
    def test_phase_mismatch_no_support(self):
        """Phase that doesn't match direction gives no support."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input(direction="LONG")
        exchange = make_exchange_input()
        fractal = make_fractal_input(
            direction="LONG",
            phase="MARKDOWN",  # Doesn't support LONG
            fractal_strength=0.60,
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        assert "phase_direction_support" not in result.patterns_detected


class TestNeutralFractal:
    """Test NEUTRAL fractal behavior."""
    
    def test_neutral_fractal_no_effect(self):
        """NEUTRAL fractal with HOLD has no effect."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input(direction="LONG")
        exchange = make_exchange_input()
        fractal = FractalInputForInteraction(
            direction="HOLD",
            context_state="NEUTRAL",
            fractal_strength=0.0,
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        # No patterns should be detected
        assert len(result.patterns_detected) == 0
        assert result.confidence_modifier == 1.0
        assert result.capital_modifier == 1.0


class TestBlockedFractal:
    """Test BLOCKED fractal behavior."""
    
    def test_blocked_fractal_ignored(self):
        """BLOCKED fractal is completely ignored."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input(direction="LONG")
        exchange = make_exchange_input()
        fractal = FractalInputForInteraction(
            direction="LONG",
            confidence=0.80,
            reliability=0.85,
            context_state="BLOCKED",  # Blocked!
            fractal_strength=0.0,
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        # No patterns despite same direction
        assert len(result.patterns_detected) == 0
        assert result.confidence_modifier == 1.0
        assert result.fractal_context_state == "BLOCKED"


class TestDominantSignal:
    """Test dominant signal determination."""
    
    def test_dominant_signal_ta(self):
        """TA dominates when it has highest support."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input(direction="LONG", conviction=0.90)
        exchange = make_exchange_input(confidence=0.50)
        fractal = make_fractal_input(
            context_state="BLOCKED",  # Low support
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        assert result.dominant_signal == DominantSignal.TA
    
    def test_dominant_signal_mixed(self):
        """MIXED when multiple signals have similar support."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input(conviction=0.65)
        exchange = make_exchange_input(confidence=0.65)
        fractal = make_fractal_input(
            context_state="SUPPORTIVE",
            fractal_strength=0.65,
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        # All support scores should be similar
        assert result.dominant_signal in [DominantSignal.MIXED, DominantSignal.TA, DominantSignal.FRACTAL]


class TestInteractionState:
    """Test interaction state classification."""
    
    def test_aligned_state(self):
        """ALIGNED when all three legs agree."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input(direction="LONG")
        exchange = make_exchange_input(bias="BULLISH")
        fractal = make_fractal_input(direction="LONG")
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        assert result.interaction_state == FractalInteractionState.ALIGNED
    
    def test_conflicted_state(self):
        """CONFLICTED when fractal_conflict pattern detected."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input(direction="LONG")
        exchange = make_exchange_input()
        fractal = make_fractal_input(
            direction="SHORT",
            fractal_strength=0.65,
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        assert result.interaction_state == FractalInteractionState.CONFLICTED


class TestModifierBounds:
    """Test that modifiers stay within bounds."""
    
    def test_confidence_modifier_bounds(self):
        """Confidence modifier stays in [0.75, 1.25]."""
        engine = FractalInteractionEngine()
        
        # Maximum boost scenario
        ta = make_ta_input(direction="LONG")
        exchange = make_exchange_input(bias="BULLISH")
        fractal = make_fractal_input(
            direction="LONG",
            context_state="SUPPORTIVE",
            phase="MARKUP",
            fractal_strength=0.70,
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        assert MODIFIER_BOUNDS["confidence_min"] <= result.confidence_modifier <= MODIFIER_BOUNDS["confidence_max"]
    
    def test_capital_modifier_bounds(self):
        """Capital modifier stays in [0.70, 1.15]."""
        engine = FractalInteractionEngine()
        
        # Maximum penalty scenario
        ta = make_ta_input(direction="LONG")
        exchange = make_exchange_input()
        fractal = make_fractal_input(
            direction="SHORT",
            fractal_strength=0.70,
        )
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        assert MODIFIER_BOUNDS["capital_min"] <= result.capital_modifier <= MODIFIER_BOUNDS["capital_max"]


class TestDirectionNotChanged:
    """Test that direction is NEVER changed by fractal."""
    
    def test_direction_from_ta(self):
        """Final direction always comes from TA, not fractal."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input(direction="LONG")
        exchange = make_exchange_input(bias="BEARISH")
        fractal = make_fractal_input(direction="SHORT", fractal_strength=0.90)
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        
        # Direction must be from TA (LONG), NOT from fractal (SHORT)
        assert result.final_direction == "LONG"
        assert result.fractal_direction == "SHORT"


class TestSummaryEndpoint:
    """Test summary/snapshot output."""
    
    def test_to_snapshot(self):
        """Snapshot contains all required fields."""
        engine = FractalInteractionEngine()
        
        ta = make_ta_input()
        exchange = make_exchange_input()
        fractal = make_fractal_input()
        
        result = engine.analyze("BTC", ta, exchange, fractal)
        snapshot = result.to_snapshot()
        
        required_fields = [
            "final_direction",
            "ta_support",
            "exchange_support",
            "fractal_support",
            "confidence_modifier",
            "capital_modifier",
            "interaction_state",
            "dominant_signal",
        ]
        
        for field in required_fields:
            assert field in snapshot


def run_tests():
    """Run all tests and return results."""
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": [],
    }
    
    test_classes = [
        TestTAFractalAlignment,
        TestExchangeFractalAlignment,
        TestFractalConflict,
        TestPhaseDirectionSupport,
        TestNeutralFractal,
        TestBlockedFractal,
        TestDominantSignal,
        TestInteractionState,
        TestModifierBounds,
        TestDirectionNotChanged,
        TestSummaryEndpoint,
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
    print("PHASE 24.2 — Fractal Interaction Tests")
    print("="*60 + "\n")
    
    results = run_tests()
    
    print("\n" + "="*60)
    print(f"Results: {results['passed']}/{results['total']} passed")
    if results["errors"]:
        print("\nErrors:")
        for err in results["errors"]:
            print(f"  - {err}")
    print("="*60 + "\n")
