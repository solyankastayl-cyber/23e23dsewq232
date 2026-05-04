"""
Indicator Engine Package
========================
Full Technical Analysis Indicators with Visualization Data.

Provides:
- IndicatorRegistry: 100+ indicator definitions
- IndicatorVisualizationEngine: computes values for chart overlays and panes
- ConfluenceEngine: aggregates bullish/bearish/neutral signals
"""

from .indicator_registry import (
    get_indicator_registry,
    IndicatorRegistry,
    IndicatorType,
    IndicatorCategory,
)

from .indicator_visualization import (
    get_indicator_visualization_engine,
    IndicatorVisualizationEngine,
)

from .confluence_engine import (
    get_confluence_engine,
    ConfluenceEngine,
)

__all__ = [
    'get_indicator_registry',
    'IndicatorRegistry',
    'IndicatorType',
    'IndicatorCategory',
    'get_indicator_visualization_engine',
    'IndicatorVisualizationEngine',
    'get_confluence_engine',
    'ConfluenceEngine',
]
