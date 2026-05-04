"""
PHASE 24.3 — Fractal Hint Tests

Test suite for Fractal Hint integration into Strategy Brain.
"""

import pytest
from datetime import datetime, timezone

from modules.strategy_brain.fractal_hint.fractal_hint_types import (
    FractalHintInput,
    FractalHintScore,
    FractalPhase,
    FRACTAL_PHASE_STRATEGY_MAP,
    REGIME_CONFIDENCE_WEIGHTS_WITH_FRACTAL,
)
from modules.strategy_brain.fractal_hint.fractal_hint_engine import (
    FractalHintEngine,
    get_fractal_hint_engine,
)


def make_fractal_hint(
    phase: FractalPhase = FractalPhase.MARKUP,
    phase_confidence: float = 0.65,
    fractal_strength: float = 0.60,
    context_state: str = "SUPPORTIVE",
    direction: str = "LONG",
) -> FractalHintInput:
    """Helper to create fractal hint."""
    return FractalHintInput(
        phase=phase,
        phase_confidence=phase_confidence,
        fractal_strength=fractal_strength,
        context_state=context_state,
        direction=direction,
    )


class TestFractalHintInput:
    """Tests for FractalHintInput."""
    
    def test_is_active_supportive(self):
        """Active hint with SUPPORTIVE state."""
        hint = make_fractal_hint(context_state="SUPPORTIVE")
        assert hint.is_active() is True
    
    def test_is_active_blocked(self):
        """BLOCKED hint is not active."""
        hint = make_fractal_hint(context_state="BLOCKED")
        assert hint.is_active() is False
    
    def test_is_active_low_strength(self):
        """Low strength hint is not active."""
        hint = make_fractal_hint(fractal_strength=0.2)
        assert hint.is_active() is False
    
    def test_is_active_unknown_phase(self):
        """UNKNOWN phase is not active."""
        hint = make_fractal_hint(phase=FractalPhase.UNKNOWN)
        assert hint.is_active() is False
    
    def test_get_supported_strategies_markup(self):
        """MARKUP supports trend_following."""
        hint = make_fractal_hint(phase=FractalPhase.MARKUP)
        supported = hint.get_supported_strategies()
        assert "trend_following" in supported
        assert "breakout" in supported
    
    def test_get_anti_strategies_markup(self):
        """MARKUP is anti mean_reversion."""
        hint = make_fractal_hint(phase=FractalPhase.MARKUP)
        anti = hint.get_anti_strategies()
        assert "mean_reversion" in anti
    
    def test_get_regime_hint(self):
        """Regime hint from phase."""
        hint = make_fractal_hint(phase=FractalPhase.MARKDOWN)
        assert hint.get_regime_hint() == "bearish_trend"


class TestFractalHintEngine:
    """Tests for FractalHintEngine."""
    
    def get_engine(self) -> FractalHintEngine:
        return FractalHintEngine()
    
    def test_compute_hint_score_supported(self):
        """Supported strategy gets bonus."""
        engine = self.get_engine()
        hint = make_fractal_hint(phase=FractalPhase.MARKUP, fractal_strength=0.70)
        
        score = engine.compute_hint_score("trend_following", hint)
        
        assert score.fractal_score > 0.5  # Above neutral
        assert score.is_supported is True
        assert score.phase_alignment > 0
    
    def test_compute_hint_score_anti(self):
        """Anti strategy gets penalty."""
        engine = self.get_engine()
        hint = make_fractal_hint(phase=FractalPhase.MARKUP, fractal_strength=0.70)
        
        score = engine.compute_hint_score("mean_reversion", hint)
        
        assert score.fractal_score < 0.5  # Below neutral
        assert score.is_anti is True
        assert score.phase_alignment < 0
    
    def test_compute_hint_score_neutral_when_blocked(self):
        """BLOCKED fractal gives neutral score."""
        engine = self.get_engine()
        hint = make_fractal_hint(context_state="BLOCKED")
        
        score = engine.compute_hint_score("trend_following", hint)
        
        assert score.fractal_score == 0.5  # Neutral
    
    def test_compute_hint_score_neutral_strategy(self):
        """Strategy not in supported/anti gets neutral."""
        engine = self.get_engine()
        hint = make_fractal_hint(phase=FractalPhase.MARKUP)
        
        score = engine.compute_hint_score("funding_arb", hint)
        
        # funding_arb is not in MARKUP supported/anti
        assert score.is_supported is False
        assert score.is_anti is False
    
    def test_direction_alignment_bonus(self):
        """Direction alignment gives bonus."""
        engine = self.get_engine()
        hint = make_fractal_hint(
            phase=FractalPhase.ACCUMULATION,
            direction="LONG",
            fractal_strength=0.70,
        )
        
        score = engine.compute_hint_score("mean_reversion", hint, strategy_direction="LONG")
        
        assert score.direction_alignment > 0
    
    def test_compute_all_strategy_hints(self):
        """Compute hints for all strategies."""
        engine = self.get_engine()
        hint = make_fractal_hint(phase=FractalPhase.MARKUP)
        
        results = engine.compute_all_strategy_hints(hint)
        
        assert "trend_following" in results
        assert "mean_reversion" in results
        assert results["trend_following"].fractal_score > results["mean_reversion"].fractal_score
    
    def test_get_regime_hint_active(self):
        """Active fractal returns regime hint."""
        engine = self.get_engine()
        # Note: This would need fractal service to be active
        # For unit test, we test with manual hint
        hint = make_fractal_hint(phase=FractalPhase.MARKUP)
        
        regime_hint = engine.get_regime_hint.__self__._compute_regime_fractal_score(hint)
        
        assert regime_hint > 0.5  # MARKUP gives high score


class TestRegimeConfidenceWeights:
    """Tests for regime confidence weights with fractal."""
    
    def test_weights_sum_to_one(self):
        """Weights should sum to approximately 1.0."""
        total = sum(REGIME_CONFIDENCE_WEIGHTS_WITH_FRACTAL.values())
        assert abs(total - 1.0) < 0.01
    
    def test_fractal_weight_limited(self):
        """Fractal weight should be ≤10%."""
        fractal_weight = REGIME_CONFIDENCE_WEIGHTS_WITH_FRACTAL["fractal"]
        assert fractal_weight <= 0.10
    
    def test_fractal_weight_positive(self):
        """Fractal weight should be positive."""
        fractal_weight = REGIME_CONFIDENCE_WEIGHTS_WITH_FRACTAL["fractal"]
        assert fractal_weight > 0


class TestFractalPhaseMapping:
    """Tests for fractal phase to strategy mapping."""
    
    def test_markup_supports_trend(self):
        """MARKUP should support trend strategies."""
        config = FRACTAL_PHASE_STRATEGY_MAP[FractalPhase.MARKUP]
        assert "trend_following" in config["supported"]
    
    def test_markdown_supports_trend(self):
        """MARKDOWN should support trend strategies."""
        config = FRACTAL_PHASE_STRATEGY_MAP[FractalPhase.MARKDOWN]
        assert "trend_following" in config["supported"]
    
    def test_accumulation_supports_mr(self):
        """ACCUMULATION should support mean reversion."""
        config = FRACTAL_PHASE_STRATEGY_MAP[FractalPhase.ACCUMULATION]
        assert "mean_reversion" in config["supported"]
    
    def test_capitulation_supports_liquidation(self):
        """CAPITULATION should support liquidation capture."""
        config = FRACTAL_PHASE_STRATEGY_MAP[FractalPhase.CAPITULATION]
        assert "liquidation_capture" in config["supported"]
    
    def test_all_phases_have_regime_hint(self):
        """All phases should have regime hint."""
        for phase in FractalPhase:
            config = FRACTAL_PHASE_STRATEGY_MAP.get(phase, {})
            assert "regime_hint" in config


def run_tests():
    """Run all tests and return results."""
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": [],
    }
    
    test_classes = [
        TestFractalHintInput,
        TestFractalHintEngine,
        TestRegimeConfidenceWeights,
        TestFractalPhaseMapping,
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
    print("PHASE 24.3 — Fractal Hint Tests")
    print("="*60 + "\n")
    
    results = run_tests()
    
    print("\n" + "="*60)
    print(f"Results: {results['passed']}/{results['total']} passed")
    if results["errors"]:
        print("\nErrors:")
        for err in results["errors"]:
            print(f"  - {err}")
    print("="*60 + "\n")
