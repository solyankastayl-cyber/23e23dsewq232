"""
Chart Composition Engine — PHASE 50

Decides what to show on chart:
- Filtering
- Priorities
- Object limits
- Presets per regime

Without this layer, chart becomes unreadable with too many objects.
"""

from .composer import ChartComposer, get_chart_composer
from .presets import (
    ChartPreset,
    PresetType,
    REGIME_PRESETS,
    get_preset_for_regime,
)
from .routes import chart_composer_router

__all__ = [
    "ChartComposer",
    "get_chart_composer",
    "ChartPreset",
    "PresetType",
    "REGIME_PRESETS",
    "get_preset_for_regime",
    "chart_composer_router",
]
