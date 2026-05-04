"""
Research Analytics API Layer — PHASE 48

Unified backend analytics layer for charts.
Frontend renders, backend computes.

Components:
- 48.1 Chart Data API
- 48.2 Indicator API  
- 48.3 Pattern Detection API
- 48.4 Hypothesis Visualization API
- 48.5 Fractal Visualization API
- 48.6 User-Selectable Research API
"""

from .chart_data import ChartDataService, get_chart_data_service
from .indicators import IndicatorService, get_indicator_service
from .patterns import PatternDetectionService, get_pattern_service
from .hypothesis_viz import HypothesisVisualizationService, get_hypothesis_viz_service
from .fractal_viz import FractalVisualizationService, get_fractal_viz_service
from .research_presets import ResearchPresetsService, get_presets_service
from .routes import research_analytics_router

__all__ = [
    # Services
    "ChartDataService",
    "IndicatorService", 
    "PatternDetectionService",
    "HypothesisVisualizationService",
    "FractalVisualizationService",
    "ResearchPresetsService",
    # Getters
    "get_chart_data_service",
    "get_indicator_service",
    "get_pattern_service",
    "get_hypothesis_viz_service",
    "get_fractal_viz_service",
    "get_presets_service",
    # Router
    "research_analytics_router",
]
