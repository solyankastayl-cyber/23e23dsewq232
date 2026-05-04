"""
Visual Research Objects Engine — PHASE 49

Converts research findings into ready-to-render chart objects.
Frontend only draws, no logic on UI.

Object Types:
- Geometry: trend_line, horizontal_level, zone, channel, triangle, wedge, range_box, ray
- Pattern: breakout_pattern, reversal_pattern, continuation_pattern, compression_pattern
- Liquidity: support_cluster, resistance_cluster, liquidity_zone, imbalance_zone
- Hypothesis: hypothesis_path, confidence_corridor, scenario_branch
- Fractal: fractal_projection, fractal_reference_window
- Indicator: ema_series, vwap_series, bollinger_band, atr_band
"""

from .models import (
    ChartObject,
    ObjectType,
    ObjectStyle,
    GeometryPoint,
)
from .builder import ChartObjectBuilder, get_object_builder
from .routes import visual_objects_router

__all__ = [
    "ChartObject",
    "ObjectType",
    "ObjectStyle",
    "GeometryPoint",
    "ChartObjectBuilder",
    "get_object_builder",
    "visual_objects_router",
]
