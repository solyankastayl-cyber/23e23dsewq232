"""
Unit tests for Pattern Projection Engine
"""
import pytest
from modules.ta_engine.geometry.pattern_projection_engine import (
    build_pattern_projection,
    build_double_top_projection,
    build_triangle_projection,
    build_range_projection,
    PatternProjectionEngine,
    get_pattern_projection_engine,
    PatternStage,
)


class TestDoubleTopProjection:
    """Tests for double top projection."""
    
    def test_creates_valid_contract(self):
        """Test that double top creates valid projection contract."""
        p1 = {"time": 100, "price": 72000}
        valley = {"time": 150, "price": 70000}
        p2 = {"time": 200, "price": 72000}
        
        result = build_double_top_projection(p1, valley, p2)
        
        assert result is not None
        assert result.pattern_type == "double_top"
        assert result.stage in [s.value for s in PatternStage]
    
    def test_computes_correct_targets(self):
        """Test that targets are computed correctly."""
        p1 = {"time": 100, "price": 72000}
        valley = {"time": 150, "price": 70000}
        p2 = {"time": 200, "price": 72000}
        
        result = build_double_top_projection(p1, valley, p2)
        
        # Height = 72000 - 70000 = 2000
        # Target down = 70000 - 2000 = 68000
        assert result.primary_projection is not None
        assert result.primary_projection.direction == "down"
        assert result.primary_projection.target == 68000
    
    def test_stage_forming_when_not_broken(self):
        """Test that stage is forming when neckline not broken."""
        p1 = {"time": 100, "price": 72000}
        valley = {"time": 150, "price": 70000}
        p2 = {"time": 200, "price": 72000}
        
        result = build_double_top_projection(p1, valley, p2, current_price=71000)
        
        assert result.stage == "forming"
    
    def test_has_secondary_projection(self):
        """Test that secondary (invalidation) projection exists."""
        p1 = {"time": 100, "price": 72000}
        valley = {"time": 150, "price": 70000}
        p2 = {"time": 200, "price": 72000}
        
        result = build_double_top_projection(p1, valley, p2)
        
        assert result.secondary_projection is not None
        assert result.secondary_projection.direction == "up"
    
    def test_to_dict_works(self):
        """Test that to_dict produces valid structure."""
        p1 = {"time": 100, "price": 72000}
        valley = {"time": 150, "price": 70000}
        p2 = {"time": 200, "price": 72000}
        
        result = build_double_top_projection(p1, valley, p2)
        d = result.to_dict()
        
        assert "type" in d
        assert "stage" in d
        assert "structure" in d
        assert "bounds" in d
        assert "completion" in d
        assert "projection" in d
        assert d["projection"]["primary"] is not None


class TestTriangleProjection:
    """Tests for triangle projection."""
    
    def test_creates_valid_contract(self):
        """Test triangle projection creation."""
        upper = [
            {"time": 100, "price": 72000},
            {"time": 200, "price": 71000}
        ]
        lower = [
            {"time": 100, "price": 70000},
            {"time": 200, "price": 70500}
        ]
        
        result = build_triangle_projection(upper, lower, "symmetrical")
        
        assert result is not None
        assert "triangle" in result.pattern_type
    
    def test_computes_apex(self):
        """Test that apex is computed."""
        upper = [
            {"time": 100, "price": 72000},
            {"time": 200, "price": 71000}
        ]
        lower = [
            {"time": 100, "price": 70000},
            {"time": 200, "price": 70500}
        ]
        
        result = build_triangle_projection(upper, lower, "symmetrical")
        
        assert result.apex is not None
    
    def test_ascending_bias_up(self):
        """Test ascending triangle has up bias."""
        upper = [
            {"time": 100, "price": 72000},
            {"time": 200, "price": 72000}  # Flat top
        ]
        lower = [
            {"time": 100, "price": 70000},
            {"time": 200, "price": 71000}  # Rising bottom
        ]
        
        result = build_triangle_projection(upper, lower, "ascending")
        
        assert result.primary_projection.direction == "up"


class TestRangeProjection:
    """Tests for range projection."""
    
    def test_creates_valid_contract(self):
        """Test range projection creation."""
        result = build_range_projection(
            resistance=72000,
            support=70000,
            start_time=100,
            end_time=200,
            touches=4
        )
        
        assert result is not None
        assert result.pattern_type == "range"
    
    def test_has_both_projections(self):
        """Test that range has both up and down projections."""
        result = build_range_projection(
            resistance=72000,
            support=70000,
            start_time=100,
            end_time=200
        )
        
        assert result.primary_projection is not None
        assert result.secondary_projection is not None
    
    def test_targets_are_measured_move(self):
        """Test that targets follow measured move."""
        result = build_range_projection(
            resistance=72000,
            support=70000,
            start_time=100,
            end_time=200
        )
        
        # Height = 2000
        # Target up = 72000 + 2000 = 74000
        # Target down = 70000 - 2000 = 68000
        assert result.primary_projection.target == 74000
        assert result.secondary_projection.target == 68000


class TestPatternProjectionEngine:
    """Tests for the engine class."""
    
    def test_singleton(self):
        """Test singleton pattern."""
        e1 = get_pattern_projection_engine()
        e2 = get_pattern_projection_engine()
        
        assert e1 is e2
    
    def test_build_double_top_from_dict(self):
        """Test building from raw pattern dict."""
        engine = PatternProjectionEngine()
        
        pattern = {
            "type": "double_top",
            "anchors": {
                "p1": {"time": 100, "price": 72000},
                "valley": {"time": 150, "price": 70000},
                "p2": {"time": 200, "price": 72000}
            }
        }
        
        result = engine.build(pattern)
        
        assert result is not None
        assert result["type"] == "double_top"
        assert result["projection"]["primary"]["direction"] == "down"
    
    def test_build_returns_none_for_unknown(self):
        """Test that unknown patterns return None."""
        engine = PatternProjectionEngine()
        
        pattern = {"type": "unknown_pattern"}
        result = engine.build(pattern)
        
        assert result is None


class TestMainBuildFunction:
    """Tests for main build_pattern_projection function."""
    
    def test_routes_double_top(self):
        """Test double top routing."""
        pattern = {
            "type": "double_top",
            "anchors": {
                "p1": {"time": 100, "price": 72000},
                "valley": {"time": 150, "price": 70000},
                "p2": {"time": 200, "price": 72000}
            }
        }
        
        result = build_pattern_projection(pattern)
        
        assert result is not None
        assert result.pattern_type == "double_top"
    
    def test_routes_range(self):
        """Test range routing."""
        pattern = {
            "type": "accumulation_range",
            "bounds": {"top": 72000, "bottom": 70000},
            "meta": {
                "boundaries": {
                    "upper": {"x1": 100, "y1": 72000, "x2": 200, "y2": 72000},
                    "lower": {"x1": 100, "y1": 70000, "x2": 200, "y2": 70000}
                }
            },
            "touches": 4
        }
        
        result = build_pattern_projection(pattern)
        
        assert result is not None
        assert result.pattern_type == "range"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
