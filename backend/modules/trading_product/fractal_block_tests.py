"""
PHASE 24.4 — Trading Product Fractal Block Tests

Test suite for Fractal Intelligence integration into Trading Product.
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from modules.trading_product.trading_product_types import (
    TradingProductSnapshot,
    ProductStatus,
    OverlayEffect,
    PortfolioOverlayEffect,
)


def make_snapshot(fractal: Dict[str, Any] = None) -> TradingProductSnapshot:
    """Helper to create snapshot with fractal block."""
    default_fractal = {
        "is_active": False,
        "direction": "HOLD",
        "confidence": 0.0,
        "reliability": 0.0,
        "phase": "UNKNOWN",
        "dominant_horizon": None,
        "context_state": "BLOCKED",
        "strength": 0.0,
    }
    
    return TradingProductSnapshot(
        symbol="BTC",
        timestamp=datetime.now(timezone.utc),
        final_action="ALLOW",
        final_direction="LONG",
        final_confidence=0.65,
        final_size_pct=0.02,
        final_execution_mode="NORMAL",
        product_status=ProductStatus.READY,
        reason="valid_setup_ready_for_execution",
        fractal=fractal or default_fractal,
    )


class TestSnapshotContainsFractal:
    """Test that snapshot contains fractal block."""
    
    def test_snapshot_has_fractal_field(self):
        """Snapshot should have fractal field."""
        snapshot = make_snapshot()
        assert hasattr(snapshot, "fractal")
        assert isinstance(snapshot.fractal, dict)
    
    def test_to_dict_includes_fractal(self):
        """to_dict() should include fractal."""
        snapshot = make_snapshot()
        result = snapshot.to_dict()
        assert "fractal" in result
    
    def test_to_summary_dict_includes_fractal_active(self):
        """to_summary_dict() should include fractal_active."""
        snapshot = make_snapshot()
        result = snapshot.to_summary_dict()
        assert "fractal_active" in result


class TestFractalInactive:
    """Test fractal inactive behavior."""
    
    def test_inactive_fractal_values_neutral(self):
        """Inactive fractal should have neutral values."""
        fractal = {
            "is_active": False,
            "direction": "HOLD",
            "confidence": 0.0,
            "reliability": 0.0,
            "phase": "UNKNOWN",
            "dominant_horizon": None,
            "context_state": "BLOCKED",
            "strength": 0.0,
        }
        snapshot = make_snapshot(fractal)
        
        assert snapshot.fractal["is_active"] is False
        assert snapshot.fractal["direction"] == "HOLD"
        assert snapshot.fractal["confidence"] == 0.0
        assert snapshot.fractal["context_state"] == "BLOCKED"
    
    def test_inactive_fractal_in_summary(self):
        """Summary should show fractal_active=False."""
        snapshot = make_snapshot()
        summary = snapshot.to_summary_dict()
        assert summary["fractal_active"] is False


class TestFractalActive:
    """Test fractal active behavior."""
    
    def test_active_fractal_values(self):
        """Active fractal should have proper values."""
        fractal = {
            "is_active": True,
            "direction": "LONG",
            "confidence": 0.67,
            "reliability": 0.71,
            "phase": "MARKUP",
            "dominant_horizon": 14,
            "context_state": "SUPPORTIVE",
            "strength": 0.63,
        }
        snapshot = make_snapshot(fractal)
        
        assert snapshot.fractal["is_active"] is True
        assert snapshot.fractal["direction"] == "LONG"
        assert snapshot.fractal["confidence"] == 0.67
        assert snapshot.fractal["phase"] == "MARKUP"
        assert snapshot.fractal["dominant_horizon"] == 14
        assert snapshot.fractal["context_state"] == "SUPPORTIVE"
    
    def test_active_fractal_in_summary(self):
        """Summary should show fractal_active=True."""
        fractal = {
            "is_active": True,
            "direction": "LONG",
            "confidence": 0.67,
            "reliability": 0.71,
            "phase": "MARKUP",
            "dominant_horizon": 14,
            "context_state": "SUPPORTIVE",
            "strength": 0.63,
        }
        snapshot = make_snapshot(fractal)
        summary = snapshot.to_summary_dict()
        assert summary["fractal_active"] is True


class TestSnapshotWithoutFractal:
    """Test that snapshot doesn't break without fractal."""
    
    def test_snapshot_with_empty_fractal(self):
        """Snapshot with empty fractal should work."""
        snapshot = make_snapshot(fractal={})
        assert snapshot.fractal == {}
    
    def test_to_dict_with_empty_fractal(self):
        """to_dict() with empty fractal should work."""
        snapshot = make_snapshot(fractal={})
        result = snapshot.to_dict()
        assert result["fractal"] == {}
    
    def test_summary_with_empty_fractal(self):
        """Summary with empty fractal should default to False."""
        snapshot = make_snapshot(fractal={})
        summary = snapshot.to_summary_dict()
        assert summary["fractal_active"] is False  # .get() default


class TestDirectionNotChanged:
    """Test that fractal doesn't change system direction."""
    
    def test_direction_independent_of_fractal(self):
        """Final direction should be independent of fractal."""
        # System says LONG, fractal says SHORT
        fractal = {
            "is_active": True,
            "direction": "SHORT",
            "confidence": 0.80,
            "reliability": 0.85,
            "phase": "MARKDOWN",
            "dominant_horizon": 14,
            "context_state": "SUPPORTIVE",
            "strength": 0.75,
        }
        
        snapshot = TradingProductSnapshot(
            symbol="BTC",
            timestamp=datetime.now(timezone.utc),
            final_action="ALLOW",
            final_direction="LONG",  # System direction
            final_confidence=0.65,
            final_size_pct=0.02,
            final_execution_mode="NORMAL",
            product_status=ProductStatus.READY,
            reason="valid_setup_ready_for_execution",
            fractal=fractal,
        )
        
        # System direction should be LONG, not SHORT
        assert snapshot.final_direction == "LONG"
        assert snapshot.fractal["direction"] == "SHORT"


class TestModifiersNotChanged:
    """Test that fractal doesn't change system modifiers."""
    
    def test_confidence_independent_of_fractal(self):
        """Final confidence should be set by system, not fractal."""
        fractal = {
            "is_active": True,
            "direction": "LONG",
            "confidence": 0.90,  # High fractal confidence
            "reliability": 0.85,
            "phase": "MARKUP",
            "dominant_horizon": 14,
            "context_state": "SUPPORTIVE",
            "strength": 0.80,
        }
        
        snapshot = TradingProductSnapshot(
            symbol="BTC",
            timestamp=datetime.now(timezone.utc),
            final_action="ALLOW",
            final_direction="LONG",
            final_confidence=0.55,  # Lower system confidence
            final_size_pct=0.02,
            final_execution_mode="NORMAL",
            product_status=ProductStatus.READY,
            reason="valid_setup_ready_for_execution",
            fractal=fractal,
        )
        
        # System confidence should be 0.55, not 0.90
        assert snapshot.final_confidence == 0.55


class TestAPISchemaValid:
    """Test API schema validity."""
    
    def test_full_dict_valid(self):
        """Full dict should have all required fields."""
        fractal = {
            "is_active": True,
            "direction": "LONG",
            "confidence": 0.67,
            "reliability": 0.71,
            "phase": "MARKUP",
            "dominant_horizon": 14,
            "context_state": "SUPPORTIVE",
            "strength": 0.63,
        }
        snapshot = make_snapshot(fractal)
        result = snapshot.to_full_dict()
        
        # Check all required fields
        required_fields = [
            "symbol", "timestamp", "final_action", "final_direction",
            "final_confidence", "final_size_pct", "final_execution_mode",
            "product_status", "reason", "fractal",
        ]
        for field in required_fields:
            assert field in result
        
        # Check fractal block fields
        fractal_fields = [
            "is_active", "direction", "confidence", "reliability",
            "phase", "dominant_horizon", "context_state", "strength",
        ]
        for field in fractal_fields:
            assert field in result["fractal"]


def run_tests():
    """Run all tests and return results."""
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": [],
    }
    
    test_classes = [
        TestSnapshotContainsFractal,
        TestFractalInactive,
        TestFractalActive,
        TestSnapshotWithoutFractal,
        TestDirectionNotChanged,
        TestModifiersNotChanged,
        TestAPISchemaValid,
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
    print("PHASE 24.4 — Trading Product Fractal Block Tests")
    print("="*60 + "\n")
    
    results = run_tests()
    
    print("\n" + "="*60)
    print(f"Results: {results['passed']}/{results['total']} passed")
    if results["errors"]:
        print("\nErrors:")
        for err in results["errors"]:
            print(f"  - {err}")
    print("="*60 + "\n")
