"""
Geometry Layer — Pattern geometry building, validation, normalization, projection and render profiles.
"""

from .pattern_geometry_builder import PatternGeometryBuilder, get_pattern_geometry_builder
from .wedge_shape_validator import get_wedge_shape_validator
from .main_render_gate import get_main_render_gate
from .geometry_normalizer import (
    GeometryNormalizer,
    get_geometry_normalizer,
    normalize_pattern,
    normalize_patterns,
)
from .pattern_projection_engine import (
    PatternProjectionEngine,
    get_pattern_projection_engine,
    build_pattern_projection,
    PatternProjectionContract,
    PatternStage,
)
from .render_profile import (
    RenderProfile,
    RenderMode,
    get_render_profile,
    configure_pattern_render,
)

__all__ = [
    "PatternGeometryBuilder",
    "get_pattern_geometry_builder",
    "get_wedge_shape_validator",
    "get_main_render_gate",
    "GeometryNormalizer",
    "get_geometry_normalizer",
    "normalize_pattern",
    "normalize_patterns",
    "PatternProjectionEngine",
    "get_pattern_projection_engine",
    "build_pattern_projection",
    "PatternProjectionContract",
    "PatternStage",
    "RenderProfile",
    "RenderMode",
    "get_render_profile",
    "configure_pattern_render",
]
