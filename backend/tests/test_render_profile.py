"""
Unit tests for Render Profile System
"""
import pytest
from modules.ta_engine.geometry.render_profile import (
    get_render_profile,
    configure_pattern_render,
    RenderProfile,
    RenderMode,
)


class TestRenderProfileSelection:
    """Tests for profile selection logic."""
    
    def test_loose_pattern_disables_projection(self):
        """Loose patterns should have projection disabled."""
        profile = get_render_profile("double_top", mode="loose", stage="confirmed")
        
        assert profile.draw_projection is False
        assert profile.draw_fill is False
        assert profile.use_dashed is True
    
    def test_strict_forming_disables_projection(self):
        """Strict forming should disable projection."""
        profile = get_render_profile("double_top", mode="strict", stage="forming")
        
        assert profile.draw_projection is False
        assert profile.draw_structure is True
        assert profile.draw_bounds is True
    
    def test_strict_confirmed_enables_projection(self):
        """Strict confirmed should enable projection."""
        profile = get_render_profile("double_top", mode="strict", stage="confirmed")
        
        assert profile.draw_projection is True
        assert profile.draw_fill is True
        assert profile.draw_labels is True
    
    def test_range_uses_box_mode(self):
        """Range patterns should use box mode."""
        profile = get_render_profile("accumulation_range", mode="strict", stage="forming")
        
        assert profile.draw_structure is True
        assert profile.draw_fill is True
        assert profile.draw_projection is False
    
    def test_range_confirmed_gets_projection(self):
        """Range confirmed should get projection."""
        profile = get_render_profile("range", mode="strict", stage="confirmed")
        
        assert profile.draw_projection is True
    
    def test_invalidated_is_faded(self):
        """Invalidated patterns should be faded."""
        profile = get_render_profile("double_top", mode="strict", stage="invalidated")
        
        assert profile.draw_projection is False
        assert profile.use_dashed is True
        assert profile.stroke_width < 2.0
    
    def test_loose_in_type_triggers_loose_mode(self):
        """Pattern types with 'loose' should use loose mode."""
        profile = get_render_profile("loose_range", mode="strict", stage="confirmed")
        
        # Should still be treated as loose because type contains 'loose'
        assert profile.draw_projection is False


class TestConfigurePatternRender:
    """Tests for main configure function."""
    
    def test_adds_render_profile_to_pattern(self):
        """Should add render_profile to pattern."""
        pattern = {
            "type": "double_top",
            "mode": "strict",
            "stage": "forming"
        }
        
        result = configure_pattern_render(pattern)
        
        assert "render_profile" in result
        assert result["render_profile"]["draw_structure"] is True
    
    def test_removes_projection_for_loose(self):
        """Should remove projection for loose patterns."""
        pattern = {
            "type": "double_top",
            "mode": "loose",
            "projection_contract": {"projection": {"primary": {"target": 68000}}}
        }
        
        result = configure_pattern_render(pattern)
        
        assert result["projection_contract"] is None
    
    def test_keeps_projection_for_confirmed(self):
        """Should keep projection for strict confirmed."""
        pattern = {
            "type": "double_top",
            "mode": "strict",
            "projection_contract": {
                "stage": "confirmed",
                "projection": {"primary": {"target": 68000}}
            }
        }
        
        result = configure_pattern_render(pattern)
        
        # Projection should be kept
        assert result["render_profile"]["draw_projection"] is True
    
    def test_reads_stage_from_projection_contract(self):
        """Should read stage from projection_contract if available."""
        pattern = {
            "type": "double_top",
            "mode": "strict",
            "stage": "forming",  # Default stage
            "projection_contract": {
                "stage": "confirmed",  # Real stage from projection
                "projection": {"primary": {"target": 68000}}
            }
        }
        
        result = configure_pattern_render(pattern)
        
        # Should use confirmed stage from projection_contract
        assert result["render_profile"]["draw_projection"] is True


class TestRenderProfileValues:
    """Tests for profile values."""
    
    def test_loose_has_thinner_strokes(self):
        """Loose should have thinner strokes."""
        loose = get_render_profile("triangle", mode="loose", stage="forming")
        strict = get_render_profile("triangle", mode="strict", stage="forming")
        
        assert loose.stroke_width < strict.stroke_width
    
    def test_loose_has_lower_fill_opacity(self):
        """Loose should have lower fill opacity."""
        loose = get_render_profile("range", mode="loose", stage="forming")
        strict = get_render_profile("range", mode="strict", stage="forming")
        
        assert loose.fill_opacity < strict.fill_opacity
    
    def test_to_dict_works(self):
        """Profile to_dict should work."""
        profile = RenderProfile(
            draw_structure=True,
            draw_projection=False,
            stroke_width=2.5
        )
        
        d = profile.to_dict()
        
        assert d["draw_structure"] is True
        assert d["draw_projection"] is False
        assert d["stroke_width"] == 2.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
