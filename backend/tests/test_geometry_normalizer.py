"""
Unit tests for Geometry Normalizer
"""
import pytest
from modules.ta_engine.geometry.geometry_normalizer import (
    normalize_pattern,
    normalize_double_top,
    normalize_range,
    normalize_lines,
    GeometryNormalizer,
    get_geometry_normalizer,
)


class TestDoubleTopNormalization:
    """Tests for double top normalization."""
    
    def test_peaks_are_aligned(self):
        """Test that P1 and P2 are aligned to average level."""
        pattern = {
            "type": "double_top",
            "anchors": {
                "p1": {"time": 100, "price": 72000},
                "p2": {"time": 200, "price": 71800},
                "valley": {"time": 150, "price": 70000}
            }
        }
        
        result = normalize_double_top(pattern)
        
        # Check peaks are aligned
        assert result["anchors"]["p1"]["price"] == result["anchors"]["p2"]["price"]
        assert result["anchors"]["p1"]["price"] == 71900  # Average of 72000 and 71800
    
    def test_time_symmetry_applied(self):
        """Test that time symmetry is applied around valley."""
        pattern = {
            "type": "double_top",
            "anchors": {
                "p1": {"time": 100, "price": 72000},
                "p2": {"time": 200, "price": 71800},
                "valley": {"time": 150, "price": 70000}
            }
        }
        
        result = normalize_double_top(pattern)
        
        # P1 should be symmetric to P2 around valley
        valley_time = result["anchors"]["valley"]["time"]
        p1_dist = abs(result["anchors"]["p1"]["time"] - valley_time)
        p2_dist = abs(result["anchors"]["p2"]["time"] - valley_time)
        
        assert abs(p1_dist - p2_dist) < 0.001
    
    def test_valley_is_reinforced(self):
        """Test that valley is pushed lower."""
        pattern = {
            "type": "double_top",
            "anchors": {
                "p1": {"time": 100, "price": 72000},
                "p2": {"time": 200, "price": 71800},
                "valley": {"time": 150, "price": 71000}
            }
        }
        
        result = normalize_double_top(pattern)
        
        # Valley should be lower than peaks * 0.995
        avg_peaks = (72000 + 71800) / 2
        expected_valley = min(71000, avg_peaks) * 0.995
        assert result["anchors"]["valley"]["price"] == expected_valley


class TestRangeNormalization:
    """Tests for range normalization."""
    
    def test_padding_applied(self):
        """Test that padding is applied to bounds."""
        pattern = {
            "type": "range",
            "bounds": {"top": 72000, "bottom": 70000},
            "touches": 4
        }
        
        result = normalize_range(pattern)
        
        # Check padding was applied
        original_height = 72000 - 70000
        padding = original_height * 0.01
        
        assert result["bounds"]["top"] == 72000 + padding
        assert result["bounds"]["bottom"] == 70000 - padding
    
    def test_confidence_from_touches(self):
        """Test that confidence is calculated from touches."""
        pattern = {
            "type": "range",
            "bounds": {"top": 72000, "bottom": 70000},
            "touches": 6
        }
        
        result = normalize_range(pattern)
        
        # Confidence should be 6/6 = 1.0 (clamped)
        assert result["confidence"] == 1.0
    
    def test_low_touches_low_confidence(self):
        """Test that few touches give low confidence."""
        pattern = {
            "type": "range",
            "bounds": {"top": 72000, "bottom": 70000},
            "touches": 1
        }
        
        result = normalize_range(pattern)
        
        # Confidence should be 1/6 ~= 0.167, clamped to 0.2
        assert result["confidence"] == 0.2


class TestWedgeNormalization:
    """Tests for wedge/triangle normalization."""
    
    def test_parallel_lines_converged(self):
        """Test that parallel lines are made to converge."""
        pattern = {
            "type": "wedge",
            "lines": {
                "upper": {"x1": 100, "y1": 72000, "x2": 200, "y2": 72000},
                "lower": {"x1": 100, "y1": 70000, "x2": 200, "y2": 70000}
            }
        }
        
        result = normalize_lines(pattern)
        
        # Lines should now converge (y2 values should be adjusted)
        assert result["lines"]["upper"]["y2"] == 72000 * 0.995
        assert result["lines"]["lower"]["y2"] == 70000 * 1.005


class TestMainNormalizer:
    """Tests for main normalize_pattern function."""
    
    def test_double_top_routing(self):
        """Test that double_top is routed correctly."""
        pattern = {
            "type": "double_top",
            "anchors": {
                "p1": {"time": 100, "price": 72000},
                "p2": {"time": 200, "price": 71800},
                "valley": {"time": 150, "price": 70000}
            }
        }
        
        result = normalize_pattern(pattern)
        
        assert result.get("_normalized") is True
        assert "symmetry" in result.get("_normalization_type", "")
    
    def test_range_routing(self):
        """Test that range is routed correctly."""
        pattern = {
            "type": "accumulation_range",
            "bounds": {"top": 72000, "bottom": 70000},
            "touches": 4
        }
        
        result = normalize_pattern(pattern)
        
        assert result.get("_normalized") is True
        assert "padding" in result.get("_normalization_type", "")
    
    def test_unknown_pattern_passthrough(self):
        """Test that unknown patterns are passed through unchanged."""
        pattern = {"type": "some_unknown_pattern", "data": "test"}
        
        result = normalize_pattern(pattern)
        
        assert result == pattern


class TestGeometryNormalizerClass:
    """Tests for OOP interface."""
    
    def test_singleton(self):
        """Test that get_geometry_normalizer returns singleton."""
        n1 = get_geometry_normalizer()
        n2 = get_geometry_normalizer()
        
        assert n1 is n2
    
    def test_normalize_returns_result(self):
        """Test that normalize returns NormalizationResult."""
        normalizer = GeometryNormalizer()
        pattern = {
            "type": "double_top",
            "anchors": {
                "p1": {"time": 100, "price": 72000},
                "p2": {"time": 200, "price": 71800},
                "valley": {"time": 150, "price": 70000}
            }
        }
        
        result = normalizer.normalize(pattern)
        
        assert result.was_normalized is True
        assert result.normalization_type is not None
        assert len(result.changes) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
