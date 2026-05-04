"""
PHASE 15.7 — Ecology Integration Tests
========================================
Tests for Alpha Ecology integration into the trading pipeline.

Tests:
    1. HEALTHY ecology → size increased (boost)
    2. STABLE ecology → no change (neutral)
    3. STRESSED ecology → size decreased (penalty)
    4. CRITICAL ecology → AGGRESSIVE execution forbidden
    5. TradingProductSnapshot contains ecology data
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.trading.ecology_overlay import (
    EcologyOverlay,
    get_ecology_overlay,
    EcologyOverlayResult,
)
from modules.trading_decision.execution_mode.execution_mode_types import ExecutionMode
from modules.alpha_ecology.alpha_ecology_engine import (
    EcologyState,
    AlphaEcologyResult,
    ECOLOGY_MODIFIERS,
)
from modules.alpha_ecology.alpha_ecology_types import (
    DecayState,
    CrowdingState,
    CorrelationState,
    RedundancyState,
    SurvivalState,
)


# ══════════════════════════════════════════════════════════════
# MOCK ECOLOGY RESULTS
# ══════════════════════════════════════════════════════════════

def create_mock_ecology_result(
    symbol: str,
    ecology_state: EcologyState,
    ecology_score: float,
    confidence_modifier: float,
    size_modifier: float,
    weakest: str = "decay",
) -> AlphaEcologyResult:
    """Create mock AlphaEcologyResult for testing."""
    return AlphaEcologyResult(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc),
        decay_state=DecayState.STABLE,
        crowding_state=CrowdingState.LOW_CROWDING,
        correlation_state=CorrelationState.UNIQUE,
        redundancy_state=RedundancyState.DIVERSIFIED,
        survival_state=SurvivalState.STABLE,
        decay_modifier=1.0,
        crowding_modifier=1.0,
        correlation_modifier=1.0,
        redundancy_modifier=1.0,
        survival_modifier=1.0,
        ecology_score=ecology_score,
        ecology_state=ecology_state,
        confidence_modifier=confidence_modifier,
        size_modifier=size_modifier,
        drivers={
            "decay": "STABLE",
            "crowding": "LOW_CROWDING",
            "correlation": "UNIQUE",
            "redundancy": "DIVERSIFIED",
            "survival": "STABLE",
        },
        component_scores={
            "decay": 1.0,
            "crowding": 1.0,
            "correlation": 1.0,
            "redundancy": 1.0,
            "survival": 1.0,
        },
        weakest_component=weakest,
        strongest_component="survival",
    )


# ══════════════════════════════════════════════════════════════
# TEST 1: HEALTHY ECOLOGY → SIZE INCREASED
# ══════════════════════════════════════════════════════════════

def test_healthy_ecology_size_boost():
    """
    Test 1: HEALTHY ecology → size modifier > 1.0 (boost).
    
    When ecology is HEALTHY, position size should be increased.
    """
    overlay = EcologyOverlay()
    
    # Mock HEALTHY ecology result
    mock_result = create_mock_ecology_result(
        symbol="BTC",
        ecology_state=EcologyState.HEALTHY,
        ecology_score=1.08,
        confidence_modifier=1.05,
        size_modifier=1.05,  # HEALTHY boost
    )
    
    with patch.object(overlay, '_ecology_engine', None):
        overlay._ecology_engine = Mock()
        overlay._ecology_engine.analyze = Mock(return_value=mock_result)
        
        result = overlay.apply_to_position(
            position_size=1.0,
            execution_mode=ExecutionMode.NORMAL,
            symbol="BTC"
        )
        
        # Verify size increased
        assert result.adjusted_size > result.original_size, \
            "HEALTHY ecology should increase position size"
        assert result.adjusted_size == 1.05, \
            f"Expected size 1.05, got {result.adjusted_size}"
        assert result.ecology_state == EcologyState.HEALTHY
        assert result.size_adjustment_applied is True
        assert result.mode_downgrade_applied is False
        
    print("TEST 1 PASSED: HEALTHY ecology → size increased")


# ══════════════════════════════════════════════════════════════
# TEST 2: STABLE ECOLOGY → NO CHANGE
# ══════════════════════════════════════════════════════════════

def test_stable_ecology_no_change():
    """
    Test 2: STABLE ecology → size modifier = 1.0 (neutral).
    
    When ecology is STABLE, position size should remain unchanged.
    """
    overlay = EcologyOverlay()
    
    # Mock STABLE ecology result
    mock_result = create_mock_ecology_result(
        symbol="ETH",
        ecology_state=EcologyState.STABLE,
        ecology_score=0.95,
        confidence_modifier=1.0,
        size_modifier=1.0,  # STABLE neutral
    )
    
    with patch.object(overlay, '_ecology_engine', None):
        overlay._ecology_engine = Mock()
        overlay._ecology_engine.analyze = Mock(return_value=mock_result)
        
        result = overlay.apply_to_position(
            position_size=1.0,
            execution_mode=ExecutionMode.NORMAL,
            symbol="ETH"
        )
        
        # Verify size unchanged
        assert result.adjusted_size == result.original_size, \
            "STABLE ecology should not change position size"
        assert result.adjusted_size == 1.0, \
            f"Expected size 1.0, got {result.adjusted_size}"
        assert result.ecology_state == EcologyState.STABLE
        assert result.size_adjustment_applied is False
        assert result.mode_downgrade_applied is False
        
    print("TEST 2 PASSED: STABLE ecology → no change")


# ══════════════════════════════════════════════════════════════
# TEST 3: STRESSED ECOLOGY → SIZE DECREASED
# ══════════════════════════════════════════════════════════════

def test_stressed_ecology_size_penalty():
    """
    Test 3: STRESSED ecology → size modifier < 1.0 (penalty).
    
    When ecology is STRESSED, position size should be reduced.
    """
    overlay = EcologyOverlay()
    
    # Mock STRESSED ecology result
    mock_result = create_mock_ecology_result(
        symbol="SOL",
        ecology_state=EcologyState.STRESSED,
        ecology_score=0.82,
        confidence_modifier=0.85,
        size_modifier=0.85,  # STRESSED penalty
        weakest="crowding",
    )
    
    with patch.object(overlay, '_ecology_engine', None):
        overlay._ecology_engine = Mock()
        overlay._ecology_engine.analyze = Mock(return_value=mock_result)
        
        result = overlay.apply_to_position(
            position_size=1.0,
            execution_mode=ExecutionMode.NORMAL,
            symbol="SOL"
        )
        
        # Verify size decreased
        assert result.adjusted_size < result.original_size, \
            "STRESSED ecology should reduce position size"
        assert result.adjusted_size == 0.85, \
            f"Expected size 0.85, got {result.adjusted_size}"
        assert result.ecology_state == EcologyState.STRESSED
        assert result.size_adjustment_applied is True
        assert result.mode_downgrade_applied is False
        
    print("TEST 3 PASSED: STRESSED ecology → size decreased")


# ══════════════════════════════════════════════════════════════
# TEST 4: CRITICAL ECOLOGY → AGGRESSIVE FORBIDDEN
# ══════════════════════════════════════════════════════════════

def test_critical_ecology_aggressive_forbidden():
    """
    Test 4: CRITICAL ecology → AGGRESSIVE execution mode forbidden.
    
    When ecology is CRITICAL and mode is AGGRESSIVE, it should
    be downgraded to NORMAL.
    """
    overlay = EcologyOverlay()
    
    # Mock CRITICAL ecology result
    mock_result = create_mock_ecology_result(
        symbol="AVAX",
        ecology_state=EcologyState.CRITICAL,
        ecology_score=0.68,
        confidence_modifier=0.65,
        size_modifier=0.65,  # CRITICAL strong penalty
        weakest="correlation",
    )
    
    with patch.object(overlay, '_ecology_engine', None):
        overlay._ecology_engine = Mock()
        overlay._ecology_engine.analyze = Mock(return_value=mock_result)
        
        result = overlay.apply_to_position(
            position_size=1.0,
            execution_mode=ExecutionMode.AGGRESSIVE,  # Should be downgraded
            symbol="AVAX"
        )
        
        # Verify AGGRESSIVE forbidden
        assert result.original_mode == ExecutionMode.AGGRESSIVE
        assert result.adjusted_mode == ExecutionMode.NORMAL, \
            "CRITICAL ecology should forbid AGGRESSIVE mode"
        assert result.mode_downgrade_applied is True
        assert "forbid_aggressive" in result.downgrade_reason
        
        # Also verify size was reduced
        assert result.adjusted_size < result.original_size
        assert result.adjusted_size == 0.65
        
    print("TEST 4 PASSED: CRITICAL ecology → AGGRESSIVE forbidden")


# ══════════════════════════════════════════════════════════════
# TEST 5: TRADING PRODUCT SNAPSHOT CONTAINS ECOLOGY
# ══════════════════════════════════════════════════════════════

def test_trading_product_snapshot_contains_ecology():
    """
    Test 5: TradingProductSnapshot contains ecology data.
    
    Verify that the ecology data is properly included in the
    trading product snapshot.
    """
    overlay = EcologyOverlay()
    
    # Mock STRESSED ecology result
    mock_result = create_mock_ecology_result(
        symbol="LINK",
        ecology_state=EcologyState.STRESSED,
        ecology_score=0.80,
        confidence_modifier=0.85,
        size_modifier=0.85,
        weakest="redundancy",
    )
    
    with patch.object(overlay, '_ecology_engine', None):
        overlay._ecology_engine = Mock()
        overlay._ecology_engine.analyze = Mock(return_value=mock_result)
        
        ecology_data = overlay.get_trading_product_ecology("LINK")
        
        # Verify all required fields present
        required_fields = [
            "state",
            "score",
            "confidence_modifier",
            "size_modifier",
            "weakest",
            "strongest",
            "components",
        ]
        
        for field in required_fields:
            assert field in ecology_data, \
                f"Missing required field: {field}"
        
        # Verify values
        assert ecology_data["state"] == "STRESSED"
        assert ecology_data["score"] == 0.80
        assert ecology_data["size_modifier"] == 0.85
        assert ecology_data["weakest"] == "redundancy"
        
        # Verify components dict present
        assert "components" in ecology_data
        assert isinstance(ecology_data["components"], dict)
        
    print("TEST 5 PASSED: TradingProductSnapshot contains ecology")


# ══════════════════════════════════════════════════════════════
# ADDITIONAL INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════

def test_ecology_overlay_singleton():
    """Test that get_ecology_overlay returns singleton."""
    overlay1 = get_ecology_overlay()
    overlay2 = get_ecology_overlay()
    
    # Reset singleton for test isolation
    import modules.trading.ecology_overlay as eco_module
    eco_module._overlay = None
    
    overlay1 = get_ecology_overlay()
    overlay2 = get_ecology_overlay()
    
    assert overlay1 is overlay2, "get_ecology_overlay should return singleton"
    print("ADDITIONAL TEST PASSED: Singleton pattern works")


def test_ecology_does_not_upgrade_mode():
    """
    Test that ecology NEVER upgrades execution mode.
    
    Even with HEALTHY ecology, NORMAL should stay NORMAL.
    """
    overlay = EcologyOverlay()
    
    # Mock HEALTHY ecology result
    mock_result = create_mock_ecology_result(
        symbol="BTC",
        ecology_state=EcologyState.HEALTHY,
        ecology_score=1.10,
        confidence_modifier=1.05,
        size_modifier=1.05,
    )
    
    with patch.object(overlay, '_ecology_engine', None):
        overlay._ecology_engine = Mock()
        overlay._ecology_engine.analyze = Mock(return_value=mock_result)
        
        result = overlay.apply_to_position(
            position_size=1.0,
            execution_mode=ExecutionMode.NORMAL,
            symbol="BTC"
        )
        
        # NORMAL should stay NORMAL (not upgraded to AGGRESSIVE)
        assert result.adjusted_mode == ExecutionMode.NORMAL
        assert result.mode_downgrade_applied is False
        
    print("ADDITIONAL TEST PASSED: Ecology does not upgrade mode")


def test_critical_ecology_allows_non_aggressive():
    """
    Test that CRITICAL ecology only forbids AGGRESSIVE.
    
    Other modes (NORMAL, PASSIVE, etc.) should remain unchanged.
    """
    overlay = EcologyOverlay()
    
    # Mock CRITICAL ecology result
    mock_result = create_mock_ecology_result(
        symbol="DOT",
        ecology_state=EcologyState.CRITICAL,
        ecology_score=0.70,
        confidence_modifier=0.65,
        size_modifier=0.65,
    )
    
    test_modes = [
        ExecutionMode.NORMAL,
        ExecutionMode.PASSIVE,
        ExecutionMode.PARTIAL_ENTRY,
        ExecutionMode.DELAYED,
        ExecutionMode.NONE,
    ]
    
    with patch.object(overlay, '_ecology_engine', None):
        overlay._ecology_engine = Mock()
        overlay._ecology_engine.analyze = Mock(return_value=mock_result)
        
        for mode in test_modes:
            result = overlay.apply_to_position(
                position_size=1.0,
                execution_mode=mode,
                symbol="DOT"
            )
            
            # Mode should not change
            assert result.adjusted_mode == mode, \
                f"CRITICAL ecology should not change {mode.value}"
            assert result.mode_downgrade_applied is False
        
    print("ADDITIONAL TEST PASSED: CRITICAL only forbids AGGRESSIVE")


# ══════════════════════════════════════════════════════════════
# RUN TESTS
# ══════════════════════════════════════════════════════════════

def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("PHASE 15.7 — ECOLOGY INTEGRATION TESTS")
    print("="*60 + "\n")
    
    tests = [
        ("Test 1: HEALTHY ecology → size boost", test_healthy_ecology_size_boost),
        ("Test 2: STABLE ecology → no change", test_stable_ecology_no_change),
        ("Test 3: STRESSED ecology → size penalty", test_stressed_ecology_size_penalty),
        ("Test 4: CRITICAL → AGGRESSIVE forbidden", test_critical_ecology_aggressive_forbidden),
        ("Test 5: Snapshot contains ecology", test_trading_product_snapshot_contains_ecology),
        ("Additional: Singleton", test_ecology_overlay_singleton),
        ("Additional: No mode upgrade", test_ecology_does_not_upgrade_mode),
        ("Additional: CRITICAL allows non-AGGRESSIVE", test_critical_ecology_allows_non_aggressive),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"FAILED: {name}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {name}")
            print(f"  Exception: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
