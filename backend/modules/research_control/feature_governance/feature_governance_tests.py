"""
PHASE 17.1 — Feature Governance Tests
======================================
Tests for Feature Governance Engine.

Test Cases:
1. HEALTHY feature (score > 0.80)
2. WATCHLIST feature (score 0.65-0.80)
3. DEGRADED feature (score 0.45-0.65)
4. RETIRE feature (score < 0.45)
5. Weakest/strongest dimension correct
6. Governance score calculation correct
7. Modifiers bounded (0.70-1.00)
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.research_control.feature_governance.feature_governance_engine import (
    get_feature_governance_engine,
    FeatureGovernanceEngine,
)
from modules.research_control.feature_governance.feature_governance_types import (
    GovernanceState,
    GovernanceDimension,
    GOVERNANCE_WEIGHTS,
    GOVERNANCE_THRESHOLDS,
    GOVERNANCE_MODIFIERS,
)


class TestGovernanceStates:
    """Test governance state classification."""
    
    def test_healthy_feature(self):
        """
        Test HEALTHY state: governance_score > 0.80
        """
        engine = get_feature_governance_engine()
        
        # All high scores -> HEALTHY
        result = engine.evaluate_from_scores(
            feature_name="test_healthy",
            stability_score=0.90,
            drift_score=0.85,
            coverage_score=0.95,
            redundancy_score=0.80,
            utility_score=0.88,
        )
        
        # Score: 0.25*0.90 + 0.20*0.85 + 0.15*0.95 + 0.15*0.80 + 0.25*0.88
        # = 0.225 + 0.17 + 0.1425 + 0.12 + 0.22 = 0.8775
        assert result.governance_score > GOVERNANCE_THRESHOLDS["healthy_min"]
        assert result.governance_state == GovernanceState.HEALTHY
        assert result.confidence_modifier == 1.00
        assert result.size_modifier == 1.00
        print(f"✓ HEALTHY: score={result.governance_score:.4f}, state={result.governance_state.value}")
    
    def test_watchlist_feature(self):
        """
        Test WATCHLIST state: governance_score 0.65-0.80
        """
        engine = get_feature_governance_engine()
        
        # Mix of scores -> WATCHLIST
        result = engine.evaluate_from_scores(
            feature_name="test_watchlist",
            stability_score=0.75,
            drift_score=0.70,
            coverage_score=0.80,
            redundancy_score=0.65,
            utility_score=0.72,
        )
        
        # Score should be ~0.72 (WATCHLIST range)
        assert GOVERNANCE_THRESHOLDS["watchlist_min"] < result.governance_score <= GOVERNANCE_THRESHOLDS["healthy_min"]
        assert result.governance_state == GovernanceState.WATCHLIST
        assert result.confidence_modifier == 0.95
        assert result.size_modifier == 0.95
        print(f"✓ WATCHLIST: score={result.governance_score:.4f}, state={result.governance_state.value}")
    
    def test_degraded_feature(self):
        """
        Test DEGRADED state: governance_score 0.45-0.65
        """
        engine = get_feature_governance_engine()
        
        # Lower scores -> DEGRADED
        result = engine.evaluate_from_scores(
            feature_name="test_degraded",
            stability_score=0.55,
            drift_score=0.50,
            coverage_score=0.60,
            redundancy_score=0.45,
            utility_score=0.55,
        )
        
        # Score should be ~0.53 (DEGRADED range)
        assert GOVERNANCE_THRESHOLDS["degraded_min"] < result.governance_score <= GOVERNANCE_THRESHOLDS["watchlist_min"]
        assert result.governance_state == GovernanceState.DEGRADED
        assert result.confidence_modifier == 0.85
        assert result.size_modifier == 0.85
        print(f"✓ DEGRADED: score={result.governance_score:.4f}, state={result.governance_state.value}")
    
    def test_retire_feature(self):
        """
        Test RETIRE state: governance_score < 0.45
        """
        engine = get_feature_governance_engine()
        
        # Very low scores -> RETIRE
        result = engine.evaluate_from_scores(
            feature_name="test_retire",
            stability_score=0.30,
            drift_score=0.35,
            coverage_score=0.40,
            redundancy_score=0.25,
            utility_score=0.35,
        )
        
        # Score should be ~0.33 (RETIRE range)
        assert result.governance_score <= GOVERNANCE_THRESHOLDS["degraded_min"]
        assert result.governance_state == GovernanceState.RETIRE
        assert result.confidence_modifier == 0.70
        assert result.size_modifier == 0.70
        print(f"✓ RETIRE: score={result.governance_score:.4f}, state={result.governance_state.value}")


class TestDimensionAnalysis:
    """Test dimension extremes detection."""
    
    def test_weakest_strongest_correct(self):
        """
        Test weakest and strongest dimension detection.
        """
        engine = get_feature_governance_engine()
        
        # Utility is weakest (0.30), Coverage is strongest (0.95)
        result = engine.evaluate_from_scores(
            feature_name="test_extremes",
            stability_score=0.70,
            drift_score=0.65,
            coverage_score=0.95,  # STRONGEST
            redundancy_score=0.60,
            utility_score=0.30,   # WEAKEST
        )
        
        assert result.weakest_dimension == GovernanceDimension.UTILITY
        assert result.strongest_dimension == GovernanceDimension.COVERAGE
        print(f"✓ Weakest: {result.weakest_dimension.value}, Strongest: {result.strongest_dimension.value}")
    
    def test_dimension_ranking_accuracy(self):
        """
        Test that all dimensions are correctly ranked.
        """
        engine = get_feature_governance_engine()
        
        # Clear ranking: stability(0.9) > drift(0.8) > coverage(0.7) > utility(0.6) > redundancy(0.5)
        result = engine.evaluate_from_scores(
            feature_name="test_ranking",
            stability_score=0.90,
            drift_score=0.80,
            coverage_score=0.70,
            redundancy_score=0.50,
            utility_score=0.60,
        )
        
        assert result.strongest_dimension == GovernanceDimension.STABILITY
        assert result.weakest_dimension == GovernanceDimension.REDUNDANCY
        print(f"✓ Ranking verified: {result.strongest_dimension.value} > ... > {result.weakest_dimension.value}")


class TestGovernanceScoreCalculation:
    """Test governance score formula."""
    
    def test_governance_score_formula(self):
        """
        Verify formula:
            score = 0.25*stability + 0.20*drift + 0.15*coverage + 0.15*redundancy + 0.25*utility
        """
        engine = get_feature_governance_engine()
        
        # Known inputs
        stability = 0.80
        drift = 0.70
        coverage = 0.90
        redundancy = 0.60
        utility = 0.75
        
        result = engine.evaluate_from_scores(
            feature_name="test_formula",
            stability_score=stability,
            drift_score=drift,
            coverage_score=coverage,
            redundancy_score=redundancy,
            utility_score=utility,
        )
        
        # Expected calculation
        expected = (
            GOVERNANCE_WEIGHTS["stability"] * stability +
            GOVERNANCE_WEIGHTS["drift"] * drift +
            GOVERNANCE_WEIGHTS["coverage"] * coverage +
            GOVERNANCE_WEIGHTS["redundancy"] * redundancy +
            GOVERNANCE_WEIGHTS["utility"] * utility
        )
        # 0.25*0.80 + 0.20*0.70 + 0.15*0.90 + 0.15*0.60 + 0.25*0.75
        # = 0.20 + 0.14 + 0.135 + 0.09 + 0.1875 = 0.7525
        
        assert abs(result.governance_score - expected) < 0.001
        print(f"✓ Formula verified: {result.governance_score:.4f} == {expected:.4f}")
    
    def test_weights_sum_to_one(self):
        """Verify weights sum to 1.0"""
        total = sum(GOVERNANCE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001
        print(f"✓ Weights sum to {total:.4f}")


class TestModifierBounds:
    """Test modifier value bounds."""
    
    def test_modifiers_bounded(self):
        """
        Test that modifiers are always within bounds (0.70-1.00).
        """
        # Check all states
        for state, mods in GOVERNANCE_MODIFIERS.items():
            assert 0.70 <= mods["confidence_modifier"] <= 1.00, \
                f"{state.value} confidence_modifier out of bounds"
            assert 0.70 <= mods["size_modifier"] <= 1.00, \
                f"{state.value} size_modifier out of bounds"
        
        print("✓ All modifiers within bounds [0.70, 1.00]")
    
    def test_modifier_progression(self):
        """
        Test that modifiers decrease as state worsens.
        """
        states = [
            GovernanceState.HEALTHY,
            GovernanceState.WATCHLIST,
            GovernanceState.DEGRADED,
            GovernanceState.RETIRE,
        ]
        
        prev_conf = 2.0
        prev_size = 2.0
        
        for state in states:
            mods = GOVERNANCE_MODIFIERS[state]
            assert mods["confidence_modifier"] <= prev_conf
            assert mods["size_modifier"] <= prev_size
            prev_conf = mods["confidence_modifier"]
            prev_size = mods["size_modifier"]
        
        print("✓ Modifiers decrease with worsening state")


class TestKnownFeatures:
    """Test known feature evaluation."""
    
    def test_evaluate_funding_skew(self):
        """Test evaluation of known feature: funding_skew"""
        engine = get_feature_governance_engine()
        result = engine.evaluate("funding_skew")
        
        assert result.feature_name == "funding_skew"
        assert 0.0 <= result.governance_score <= 1.0
        assert result.governance_state in GovernanceState
        assert 0.70 <= result.confidence_modifier <= 1.00
        assert 0.70 <= result.size_modifier <= 1.00
        
        print(f"✓ funding_skew: {result.governance_state.value} ({result.governance_score:.4f})")
    
    def test_evaluate_multiple_features(self):
        """Test batch evaluation of known features."""
        engine = get_feature_governance_engine()
        
        features = ["funding_skew", "rsi_14", "atr_normalized", "trend_strength"]
        
        for feature in features:
            result = engine.evaluate(feature)
            assert result.feature_name == feature
            assert 0.0 <= result.governance_score <= 1.0
            print(f"✓ {feature}: {result.governance_state.value} ({result.governance_score:.4f})")
    
    def test_unknown_feature_defaults(self):
        """Test that unknown features get default evaluation."""
        engine = get_feature_governance_engine()
        result = engine.evaluate("unknown_feature_xyz")
        
        assert result.feature_name == "unknown_feature_xyz"
        # Should have reasonable defaults, not fail
        assert 0.0 <= result.governance_score <= 1.0
        print(f"✓ Unknown feature handled: {result.governance_state.value}")


# Run tests when executed directly
if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 17.1 — Feature Governance Engine Tests")
    print("=" * 60)
    
    # State tests
    print("\n1. Governance States:")
    test_states = TestGovernanceStates()
    test_states.test_healthy_feature()
    test_states.test_watchlist_feature()
    test_states.test_degraded_feature()
    test_states.test_retire_feature()
    
    # Dimension tests
    print("\n2. Dimension Analysis:")
    test_dims = TestDimensionAnalysis()
    test_dims.test_weakest_strongest_correct()
    test_dims.test_dimension_ranking_accuracy()
    
    # Score tests
    print("\n3. Score Calculation:")
    test_score = TestGovernanceScoreCalculation()
    test_score.test_governance_score_formula()
    test_score.test_weights_sum_to_one()
    
    # Modifier tests
    print("\n4. Modifier Bounds:")
    test_mods = TestModifierBounds()
    test_mods.test_modifiers_bounded()
    test_mods.test_modifier_progression()
    
    # Known feature tests
    print("\n5. Known Features:")
    test_known = TestKnownFeatures()
    test_known.test_evaluate_funding_skew()
    test_known.test_evaluate_multiple_features()
    test_known.test_unknown_feature_defaults()
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
