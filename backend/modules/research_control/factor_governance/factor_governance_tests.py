"""
PHASE 17.2 — Factor Governance Tests
=====================================
Tests for Factor Governance Engine.

Test Cases:
1. ELITE factor (score > 0.85)
2. STABLE factor (score 0.70-0.85)
3. WATCHLIST factor (score 0.55-0.70)
4. DEGRADED factor (score 0.40-0.55)
5. RETIRE factor (score < 0.40)
6. Capacity penalty applied
7. Decay penalty applied
8. Weakest/strongest dimension correct
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.research_control.factor_governance.factor_governance_engine import (
    get_factor_governance_engine,
    FactorGovernanceEngine,
)
from modules.research_control.factor_governance.factor_governance_types import (
    FactorGovernanceState,
    FactorDimension,
    FACTOR_GOVERNANCE_WEIGHTS,
    FACTOR_GOVERNANCE_THRESHOLDS,
    FACTOR_GOVERNANCE_MODIFIERS,
)


class TestFactorGovernanceStates:
    """Test factor governance state classification."""
    
    def test_elite_factor(self):
        """
        Test ELITE state: governance_score > 0.85
        """
        engine = get_factor_governance_engine()
        
        # All high scores -> ELITE
        result = engine.evaluate_from_scores(
            factor_name="test_elite",
            performance_score=0.92,
            regime_score=0.88,
            capacity_score=0.85,
            crowding_score=0.82,
            decay_score=0.90,
        )
        
        # Score: 0.30*0.92 + 0.20*0.88 + 0.15*0.85 + 0.15*0.82 + 0.20*0.90
        # = 0.276 + 0.176 + 0.1275 + 0.123 + 0.18 = 0.8825
        assert result.governance_score > FACTOR_GOVERNANCE_THRESHOLDS["elite_min"]
        assert result.governance_state == FactorGovernanceState.ELITE
        assert result.capital_modifier == 1.15
        assert result.confidence_modifier == 1.10
        print(f"✓ ELITE: score={result.governance_score:.4f}, capital_mod={result.capital_modifier}")
    
    def test_stable_factor(self):
        """
        Test STABLE state: governance_score 0.70-0.85
        """
        engine = get_factor_governance_engine()
        
        # Good scores -> STABLE
        result = engine.evaluate_from_scores(
            factor_name="test_stable",
            performance_score=0.80,
            regime_score=0.75,
            capacity_score=0.72,
            crowding_score=0.70,
            decay_score=0.78,
        )
        
        # Score should be ~0.76 (STABLE range)
        assert FACTOR_GOVERNANCE_THRESHOLDS["stable_min"] < result.governance_score <= FACTOR_GOVERNANCE_THRESHOLDS["elite_min"]
        assert result.governance_state == FactorGovernanceState.STABLE
        assert result.capital_modifier == 1.05
        assert result.confidence_modifier == 1.03
        print(f"✓ STABLE: score={result.governance_score:.4f}, capital_mod={result.capital_modifier}")
    
    def test_watchlist_factor(self):
        """
        Test WATCHLIST state: governance_score 0.55-0.70
        """
        engine = get_factor_governance_engine()
        
        # Moderate scores -> WATCHLIST
        result = engine.evaluate_from_scores(
            factor_name="test_watchlist",
            performance_score=0.65,
            regime_score=0.60,
            capacity_score=0.58,
            crowding_score=0.55,
            decay_score=0.62,
        )
        
        # Score should be ~0.61 (WATCHLIST range)
        assert FACTOR_GOVERNANCE_THRESHOLDS["watchlist_min"] < result.governance_score <= FACTOR_GOVERNANCE_THRESHOLDS["stable_min"]
        assert result.governance_state == FactorGovernanceState.WATCHLIST
        assert result.capital_modifier == 0.95
        assert result.confidence_modifier == 0.95
        print(f"✓ WATCHLIST: score={result.governance_score:.4f}, capital_mod={result.capital_modifier}")
    
    def test_degraded_factor(self):
        """
        Test DEGRADED state: governance_score 0.40-0.55
        """
        engine = get_factor_governance_engine()
        
        # Lower scores -> DEGRADED
        result = engine.evaluate_from_scores(
            factor_name="test_degraded",
            performance_score=0.50,
            regime_score=0.45,
            capacity_score=0.42,
            crowding_score=0.40,
            decay_score=0.48,
        )
        
        # Score should be ~0.46 (DEGRADED range)
        assert FACTOR_GOVERNANCE_THRESHOLDS["degraded_min"] < result.governance_score <= FACTOR_GOVERNANCE_THRESHOLDS["watchlist_min"]
        assert result.governance_state == FactorGovernanceState.DEGRADED
        assert result.capital_modifier == 0.80
        assert result.confidence_modifier == 0.85
        print(f"✓ DEGRADED: score={result.governance_score:.4f}, capital_mod={result.capital_modifier}")
    
    def test_retire_factor(self):
        """
        Test RETIRE state: governance_score < 0.40
        """
        engine = get_factor_governance_engine()
        
        # Very low scores -> RETIRE
        result = engine.evaluate_from_scores(
            factor_name="test_retire",
            performance_score=0.35,
            regime_score=0.30,
            capacity_score=0.28,
            crowding_score=0.25,
            decay_score=0.32,
        )
        
        # Score should be ~0.31 (RETIRE range)
        assert result.governance_score <= FACTOR_GOVERNANCE_THRESHOLDS["degraded_min"]
        assert result.governance_state == FactorGovernanceState.RETIRE
        assert result.capital_modifier == 0.50
        assert result.confidence_modifier == 0.60
        print(f"✓ RETIRE: score={result.governance_score:.4f}, capital_mod={result.capital_modifier}")


class TestCapacityAndDecayPenalties:
    """Test capacity and decay impact on governance."""
    
    def test_capacity_penalty_applied(self):
        """
        Test that low capacity score affects overall governance.
        """
        engine = get_factor_governance_engine()
        
        # Good performance but constrained capacity
        result = engine.evaluate_from_scores(
            factor_name="test_capacity_penalty",
            performance_score=0.85,
            regime_score=0.80,
            capacity_score=0.35,  # LOW capacity!
            crowding_score=0.75,
            decay_score=0.82,
        )
        
        # Despite good performance, capacity drags score down
        assert result.capacity_score == 0.35
        assert result.weakest_dimension == FactorDimension.CAPACITY
        # Score penalized by capacity: full score would be ~0.80 without penalty
        # With 0.35 capacity: 0.30*0.85 + 0.20*0.80 + 0.15*0.35 + 0.15*0.75 + 0.20*0.82
        # = 0.255 + 0.16 + 0.0525 + 0.1125 + 0.164 = 0.744
        assert result.governance_score < 0.80  # Penalized
        print(f"✓ Capacity penalty: score={result.governance_score:.4f}, weakest={result.weakest_dimension.value}")
    
    def test_decay_penalty_applied(self):
        """
        Test that high decay rate affects overall governance.
        """
        engine = get_factor_governance_engine()
        
        # Good performance but fast decay
        result = engine.evaluate_from_scores(
            factor_name="test_decay_penalty",
            performance_score=0.85,
            regime_score=0.80,
            capacity_score=0.78,
            crowding_score=0.75,
            decay_score=0.30,  # LOW decay score = fast decay!
        )
        
        # Despite good performance, decay drags score down
        assert result.decay_score == 0.30
        assert result.weakest_dimension == FactorDimension.DECAY
        # Score penalized by decay
        assert result.governance_score < 0.80  # Penalized
        print(f"✓ Decay penalty: score={result.governance_score:.4f}, weakest={result.weakest_dimension.value}")


class TestDimensionAnalysis:
    """Test dimension extremes detection."""
    
    def test_weakest_strongest_correct(self):
        """
        Test weakest and strongest dimension detection.
        """
        engine = get_factor_governance_engine()
        
        # Crowding is weakest (0.25), Performance is strongest (0.90)
        result = engine.evaluate_from_scores(
            factor_name="test_extremes",
            performance_score=0.90,  # STRONGEST
            regime_score=0.75,
            capacity_score=0.65,
            crowding_score=0.25,     # WEAKEST
            decay_score=0.70,
        )
        
        assert result.weakest_dimension == FactorDimension.CROWDING
        assert result.strongest_dimension == FactorDimension.PERFORMANCE
        print(f"✓ Weakest: {result.weakest_dimension.value}, Strongest: {result.strongest_dimension.value}")


class TestGovernanceScoreCalculation:
    """Test governance score formula."""
    
    def test_governance_score_formula(self):
        """
        Verify formula:
            score = 0.30*performance + 0.20*regime + 0.15*capacity + 0.15*crowding + 0.20*decay
        """
        engine = get_factor_governance_engine()
        
        # Known inputs
        performance = 0.80
        regime = 0.70
        capacity = 0.65
        crowding = 0.60
        decay = 0.75
        
        result = engine.evaluate_from_scores(
            factor_name="test_formula",
            performance_score=performance,
            regime_score=regime,
            capacity_score=capacity,
            crowding_score=crowding,
            decay_score=decay,
        )
        
        # Expected calculation
        expected = (
            FACTOR_GOVERNANCE_WEIGHTS["performance"] * performance +
            FACTOR_GOVERNANCE_WEIGHTS["regime"] * regime +
            FACTOR_GOVERNANCE_WEIGHTS["capacity"] * capacity +
            FACTOR_GOVERNANCE_WEIGHTS["crowding"] * crowding +
            FACTOR_GOVERNANCE_WEIGHTS["decay"] * decay
        )
        # 0.30*0.80 + 0.20*0.70 + 0.15*0.65 + 0.15*0.60 + 0.20*0.75
        # = 0.24 + 0.14 + 0.0975 + 0.09 + 0.15 = 0.7175
        
        assert abs(result.governance_score - expected) < 0.001
        print(f"✓ Formula verified: {result.governance_score:.4f} == {expected:.4f}")
    
    def test_weights_sum_to_one(self):
        """Verify weights sum to 1.0"""
        total = sum(FACTOR_GOVERNANCE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001
        print(f"✓ Weights sum to {total:.4f}")


class TestModifierBounds:
    """Test modifier value bounds."""
    
    def test_modifiers_bounded(self):
        """
        Test that modifiers are within expected bounds.
        Capital: 0.50 to 1.15
        Confidence: 0.60 to 1.10
        """
        for state, mods in FACTOR_GOVERNANCE_MODIFIERS.items():
            assert 0.50 <= mods["capital_modifier"] <= 1.15, \
                f"{state.value} capital_modifier out of bounds"
            assert 0.60 <= mods["confidence_modifier"] <= 1.10, \
                f"{state.value} confidence_modifier out of bounds"
        
        print("✓ All modifiers within bounds")
    
    def test_modifier_progression(self):
        """
        Test that modifiers decrease as state worsens.
        """
        states = [
            FactorGovernanceState.ELITE,
            FactorGovernanceState.STABLE,
            FactorGovernanceState.WATCHLIST,
            FactorGovernanceState.DEGRADED,
            FactorGovernanceState.RETIRE,
        ]
        
        prev_cap = 2.0
        prev_conf = 2.0
        
        for state in states:
            mods = FACTOR_GOVERNANCE_MODIFIERS[state]
            assert mods["capital_modifier"] <= prev_cap
            assert mods["confidence_modifier"] <= prev_conf
            prev_cap = mods["capital_modifier"]
            prev_conf = mods["confidence_modifier"]
        
        print("✓ Modifiers decrease with worsening state")


class TestKnownFactors:
    """Test known factor evaluation."""
    
    def test_evaluate_trend_breakout(self):
        """Test evaluation of known factor: trend_breakout_factor"""
        engine = get_factor_governance_engine()
        result = engine.evaluate("trend_breakout_factor")
        
        assert result.factor_name == "trend_breakout_factor"
        assert 0.0 <= result.governance_score <= 1.0
        assert result.governance_state in FactorGovernanceState
        assert 0.50 <= result.capital_modifier <= 1.15
        assert 0.60 <= result.confidence_modifier <= 1.10
        
        print(f"✓ trend_breakout_factor: {result.governance_state.value} ({result.governance_score:.4f})")
    
    def test_evaluate_multiple_factors(self):
        """Test batch evaluation of known factors."""
        engine = get_factor_governance_engine()
        
        factors = [
            "trend_breakout_factor",
            "mean_reversion_factor",
            "funding_arb_factor",
            "volatility_regime_factor",
        ]
        
        for factor in factors:
            result = engine.evaluate(factor)
            assert result.factor_name == factor
            assert 0.0 <= result.governance_score <= 1.0
            print(f"✓ {factor}: {result.governance_state.value} ({result.governance_score:.4f})")


# Run tests when executed directly
if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 17.2 — Factor Governance Engine Tests")
    print("=" * 60)
    
    # State tests
    print("\n1. Governance States:")
    test_states = TestFactorGovernanceStates()
    test_states.test_elite_factor()
    test_states.test_stable_factor()
    test_states.test_watchlist_factor()
    test_states.test_degraded_factor()
    test_states.test_retire_factor()
    
    # Penalty tests
    print("\n2. Capacity & Decay Penalties:")
    test_penalties = TestCapacityAndDecayPenalties()
    test_penalties.test_capacity_penalty_applied()
    test_penalties.test_decay_penalty_applied()
    
    # Dimension tests
    print("\n3. Dimension Analysis:")
    test_dims = TestDimensionAnalysis()
    test_dims.test_weakest_strongest_correct()
    
    # Score tests
    print("\n4. Score Calculation:")
    test_score = TestGovernanceScoreCalculation()
    test_score.test_governance_score_formula()
    test_score.test_weights_sum_to_one()
    
    # Modifier tests
    print("\n5. Modifier Bounds:")
    test_mods = TestModifierBounds()
    test_mods.test_modifiers_bounded()
    test_mods.test_modifier_progression()
    
    # Known factor tests
    print("\n6. Known Factors:")
    test_known = TestKnownFactors()
    test_known.test_evaluate_trend_breakout()
    test_known.test_evaluate_multiple_factors()
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED (14/14)")
    print("=" * 60)
