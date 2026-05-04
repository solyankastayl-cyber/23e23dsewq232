"""
Visual Objects Models — PHASE 49

Universal chart object model for frontend rendering.
"""

from typing import Dict, List, Optional, Any, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


# ═══════════════════════════════════════════════════════════════
# Object Types
# ═══════════════════════════════════════════════════════════════

class ObjectType(str, Enum):
    """All supported chart object types."""
    
    # Geometry
    TREND_LINE = "trend_line"
    HORIZONTAL_LEVEL = "horizontal_level"
    ZONE = "zone"
    CHANNEL = "channel"
    TRIANGLE = "triangle"
    WEDGE = "wedge"
    RANGE_BOX = "range_box"
    RAY = "ray"
    FIBONACCI = "fibonacci"
    
    # Patterns
    BREAKOUT_PATTERN = "breakout_pattern"
    REVERSAL_PATTERN = "reversal_pattern"
    CONTINUATION_PATTERN = "continuation_pattern"
    COMPRESSION_PATTERN = "compression_pattern"
    
    # Liquidity / Structure
    SUPPORT_CLUSTER = "support_cluster"
    RESISTANCE_CLUSTER = "resistance_cluster"
    LIQUIDITY_ZONE = "liquidity_zone"
    IMBALANCE_ZONE = "imbalance_zone"
    INVALIDATION_LINE = "invalidation_line"
    TARGET_BAND = "target_band"
    
    # Hypothesis
    HYPOTHESIS_PATH = "hypothesis_path"
    CONFIDENCE_CORRIDOR = "confidence_corridor"
    SCENARIO_BRANCH = "scenario_branch"
    ENTRY_ZONE = "entry_zone"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    
    # Fractal
    FRACTAL_PROJECTION = "fractal_projection"
    FRACTAL_REFERENCE = "fractal_reference"
    FRACTAL_SIMILARITY_ZONE = "fractal_similarity_zone"
    
    # Indicators
    EMA_SERIES = "ema_series"
    SMA_SERIES = "sma_series"
    VWAP_SERIES = "vwap_series"
    BOLLINGER_BAND = "bollinger_band"
    ATR_BAND = "atr_band"
    RSI_SERIES = "rsi_series"
    MACD_SERIES = "macd_series"
    VOLUME_PROFILE = "volume_profile"
    CCI_SERIES = "cci_series"
    WILLIAMS_R_SERIES = "williams_r_series"
    ICHIMOKU_CLOUD = "ichimoku_cloud"
    PSAR_SERIES = "psar_series"
    DONCHIAN_CHANNEL = "donchian_channel"
    KELTNER_CHANNEL = "keltner_channel"
    CUSTOM_INDICATOR = "custom_indicator"
    
    # Advanced Patterns
    HEAD_SHOULDERS = "head_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    CUP_HANDLE = "cup_handle"
    WEDGE_RISING = "wedge_rising"
    WEDGE_FALLING = "wedge_falling"
    HARMONIC_GARTLEY = "harmonic_gartley"
    HARMONIC_BAT = "harmonic_bat"


class ObjectCategory(str, Enum):
    """Object categories for filtering."""
    GEOMETRY = "geometry"
    PATTERN = "pattern"
    LIQUIDITY = "liquidity"
    HYPOTHESIS = "hypothesis"
    FRACTAL = "fractal"
    INDICATOR = "indicator"


# ═══════════════════════════════════════════════════════════════
# Style Models
# ═══════════════════════════════════════════════════════════════

class ObjectStyle(BaseModel):
    """Rendering style for chart object."""
    color: str = "#3B82F6"
    fill_color: Optional[str] = None
    opacity: float = 1.0
    fill_opacity: float = 0.2
    line_width: int = 2
    line_style: str = "solid"  # solid, dashed, dotted
    font_size: int = 12
    show_label: bool = True
    z_index: int = 1


class GeometryPoint(BaseModel):
    """Point in chart coordinates."""
    timestamp: str  # ISO timestamp
    price: float
    index: Optional[int] = None  # Candle index if applicable


# ═══════════════════════════════════════════════════════════════
# Main Chart Object Model
# ═══════════════════════════════════════════════════════════════

class ChartObject(BaseModel):
    """Universal chart object for frontend rendering."""
    
    # Identity
    id: str
    type: ObjectType
    category: ObjectCategory
    
    # Context
    symbol: str
    timeframe: str
    
    # Geometry
    points: List[GeometryPoint] = Field(default_factory=list)
    
    # For series data (indicators)
    series: List[float] = Field(default_factory=list)
    timestamps: List[str] = Field(default_factory=list)
    
    # For bands (Bollinger, ATR, etc.)
    upper_band: List[float] = Field(default_factory=list)
    lower_band: List[float] = Field(default_factory=list)
    middle_band: List[float] = Field(default_factory=list)
    
    # Style
    style: ObjectStyle = Field(default_factory=ObjectStyle)
    
    # Metadata
    label: Optional[str] = None
    confidence: Optional[float] = None
    priority: int = 5  # 1-10, higher = more important
    source: str = "system"  # system, user, indicator
    
    # Time
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    
    # Additional data
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if object has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


# ═══════════════════════════════════════════════════════════════
# Specialized Object Models
# ═══════════════════════════════════════════════════════════════

class TrendLineObject(ChartObject):
    """Trend line with slope."""
    slope: float = 0.0
    intercept: float = 0.0
    extend_left: bool = False
    extend_right: bool = True


class ZoneObject(ChartObject):
    """Price zone (support/resistance)."""
    price_high: float = 0.0
    price_low: float = 0.0
    strength: float = 0.0
    touches: int = 0


class HypothesisPathObject(ChartObject):
    """Hypothesis price path."""
    direction: str = "neutral"
    probability: float = 0.0
    target_price: float = 0.0
    invalidation_price: Optional[float] = None


class FractalObject(ChartObject):
    """Fractal projection."""
    reference_symbol: str = ""
    reference_period: str = ""
    similarity: float = 0.0
    projected_target: Optional[float] = None


# ═══════════════════════════════════════════════════════════════
# Color Palettes
# ═══════════════════════════════════════════════════════════════

DEFAULT_COLORS = {
    # Geometry
    ObjectType.TREND_LINE: "#F59E0B",
    ObjectType.HORIZONTAL_LEVEL: "#6366F1",
    ObjectType.ZONE: "#8B5CF6",
    ObjectType.CHANNEL: "#06B6D4",
    ObjectType.TRIANGLE: "#EC4899",
    
    # Patterns
    ObjectType.BREAKOUT_PATTERN: "#22C55E",
    ObjectType.REVERSAL_PATTERN: "#EF4444",
    ObjectType.COMPRESSION_PATTERN: "#F97316",
    ObjectType.HEAD_SHOULDERS: "#E11D48",
    ObjectType.DOUBLE_TOP: "#DC2626",
    ObjectType.DOUBLE_BOTTOM: "#059669",
    ObjectType.CUP_HANDLE: "#7C3AED",
    ObjectType.WEDGE_RISING: "#F97316",
    ObjectType.WEDGE_FALLING: "#0EA5E9",
    ObjectType.HARMONIC_GARTLEY: "#D946EF",
    ObjectType.HARMONIC_BAT: "#A855F7",
    
    # Liquidity
    ObjectType.SUPPORT_CLUSTER: "#10B981",
    ObjectType.RESISTANCE_CLUSTER: "#F43F5E",
    ObjectType.LIQUIDITY_ZONE: "#3B82F6",
    
    # Hypothesis
    ObjectType.HYPOTHESIS_PATH: "#A78BFA",
    ObjectType.CONFIDENCE_CORRIDOR: "#818CF8",
    ObjectType.ENTRY_ZONE: "#22C55E",
    ObjectType.STOP_LOSS: "#EF4444",
    ObjectType.TAKE_PROFIT: "#10B981",
    
    # Fractal
    ObjectType.FRACTAL_PROJECTION: "#D946EF",
    ObjectType.FRACTAL_REFERENCE: "#A855F7",
    
    # Indicators
    ObjectType.EMA_SERIES: "#10B981",
    ObjectType.SMA_SERIES: "#F59E0B",
    ObjectType.VWAP_SERIES: "#EC4899",
    ObjectType.BOLLINGER_BAND: "#06B6D4",
    ObjectType.RSI_SERIES: "#8B5CF6",
    ObjectType.CCI_SERIES: "#F59E0B",
    ObjectType.WILLIAMS_R_SERIES: "#6366F1",
    ObjectType.ICHIMOKU_CLOUD: "#059669",
    ObjectType.PSAR_SERIES: "#EF4444",
    ObjectType.DONCHIAN_CHANNEL: "#0EA5E9",
    ObjectType.KELTNER_CHANNEL: "#D97706",
}


def get_default_color(obj_type: ObjectType) -> str:
    """Get default color for object type."""
    return DEFAULT_COLORS.get(obj_type, "#3B82F6")


def get_category_for_type(obj_type: ObjectType) -> ObjectCategory:
    """Get category for object type."""
    geometry_types = {
        ObjectType.TREND_LINE, ObjectType.HORIZONTAL_LEVEL,
        ObjectType.ZONE, ObjectType.CHANNEL, ObjectType.TRIANGLE,
        ObjectType.WEDGE, ObjectType.RANGE_BOX, ObjectType.RAY,
        ObjectType.FIBONACCI,
    }
    pattern_types = {
        ObjectType.BREAKOUT_PATTERN, ObjectType.REVERSAL_PATTERN,
        ObjectType.CONTINUATION_PATTERN, ObjectType.COMPRESSION_PATTERN,
        ObjectType.HEAD_SHOULDERS, ObjectType.DOUBLE_TOP,
        ObjectType.DOUBLE_BOTTOM, ObjectType.CUP_HANDLE,
        ObjectType.WEDGE_RISING, ObjectType.WEDGE_FALLING,
        ObjectType.HARMONIC_GARTLEY, ObjectType.HARMONIC_BAT,
    }
    liquidity_types = {
        ObjectType.SUPPORT_CLUSTER, ObjectType.RESISTANCE_CLUSTER,
        ObjectType.LIQUIDITY_ZONE, ObjectType.IMBALANCE_ZONE,
        ObjectType.INVALIDATION_LINE, ObjectType.TARGET_BAND,
    }
    hypothesis_types = {
        ObjectType.HYPOTHESIS_PATH, ObjectType.CONFIDENCE_CORRIDOR,
        ObjectType.SCENARIO_BRANCH, ObjectType.ENTRY_ZONE,
        ObjectType.STOP_LOSS, ObjectType.TAKE_PROFIT,
    }
    fractal_types = {
        ObjectType.FRACTAL_PROJECTION, ObjectType.FRACTAL_REFERENCE,
        ObjectType.FRACTAL_SIMILARITY_ZONE,
    }
    
    if obj_type in geometry_types:
        return ObjectCategory.GEOMETRY
    elif obj_type in pattern_types:
        return ObjectCategory.PATTERN
    elif obj_type in liquidity_types:
        return ObjectCategory.LIQUIDITY
    elif obj_type in hypothesis_types:
        return ObjectCategory.HYPOTHESIS
    elif obj_type in fractal_types:
        return ObjectCategory.FRACTAL
    else:
        return ObjectCategory.INDICATOR
