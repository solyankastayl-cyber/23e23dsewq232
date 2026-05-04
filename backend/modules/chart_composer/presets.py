"""
Chart Presets — PHASE 50

Regime-based presets for chart composition.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class PresetType(str, Enum):
    """Preset types."""
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    RANGE = "range"
    VOLATILE = "volatile"
    COMPRESSION = "compression"
    BREAKOUT = "breakout"
    SCALPING = "scalping"
    SWING = "swing"
    CUSTOM = "custom"


class ChartPreset(BaseModel):
    """Chart composition preset."""
    
    preset_id: str
    name: str
    description: str
    preset_type: PresetType
    
    # Indicator configuration
    indicators: List[Dict[str, Any]] = Field(default_factory=list)
    max_indicators: int = 5
    
    # Object limits
    max_patterns: int = 5
    max_sr_levels: int = 8
    max_liquidity_zones: int = 4
    max_hypothesis_paths: int = 3
    max_fractal_matches: int = 2
    
    # Feature flags
    show_patterns: bool = True
    show_support_resistance: bool = True
    show_liquidity_zones: bool = False
    show_hypothesis: bool = True
    show_fractals: bool = False
    show_volume_profile: bool = False
    show_liquidations: bool = False
    show_funding: bool = False
    
    # Priority weights (for filtering)
    pattern_priority: float = 0.7
    sr_priority: float = 0.6
    hypothesis_priority: float = 0.8
    fractal_priority: float = 0.5
    
    # Visual settings
    theme: str = "default"
    object_opacity: float = 0.8


# ═══════════════════════════════════════════════════════════════
# Default Presets
# ═══════════════════════════════════════════════════════════════

REGIME_PRESETS: Dict[PresetType, ChartPreset] = {
    
    PresetType.TREND_UP: ChartPreset(
        preset_id="trend_up",
        name="Trending Up",
        description="Optimal for bullish trending markets",
        preset_type=PresetType.TREND_UP,
        indicators=[
            {"name": "ema", "params": {"period": 50}, "color": "#10B981"},
            {"name": "ema", "params": {"period": 200}, "color": "#F59E0B"},
            {"name": "rsi", "params": {"period": 14}, "color": "#8B5CF6"},
            {"name": "ichimoku", "params": {}, "color": "#059669"},
            {"name": "parabolic_sar", "params": {}, "color": "#EF4444"},
        ],
        max_indicators=6,
        max_patterns=3,
        max_sr_levels=6,
        max_hypothesis_paths=2,
        show_patterns=True,
        show_support_resistance=True,
        show_hypothesis=True,
        show_fractals=True,
        pattern_priority=0.8,
        hypothesis_priority=0.9,
    ),
    
    PresetType.TREND_DOWN: ChartPreset(
        preset_id="trend_down",
        name="Trending Down",
        description="Optimal for bearish trending markets",
        preset_type=PresetType.TREND_DOWN,
        indicators=[
            {"name": "ema", "params": {"period": 50}, "color": "#10B981"},
            {"name": "ema", "params": {"period": 200}, "color": "#F59E0B"},
            {"name": "rsi", "params": {"period": 14}, "color": "#8B5CF6"},
            {"name": "ichimoku", "params": {}, "color": "#059669"},
            {"name": "parabolic_sar", "params": {}, "color": "#EF4444"},
        ],
        max_indicators=6,
        max_patterns=3,
        max_sr_levels=6,
        max_hypothesis_paths=2,
        show_patterns=True,
        show_support_resistance=True,
        show_hypothesis=True,
        show_fractals=True,
        pattern_priority=0.8,
        hypothesis_priority=0.9,
    ),
    
    PresetType.RANGE: ChartPreset(
        preset_id="range",
        name="Range Bound",
        description="Optimal for ranging/mean reversion markets",
        preset_type=PresetType.RANGE,
        indicators=[
            {"name": "bollinger", "params": {"period": 20, "std_dev": 2}, "color": "#06B6D4"},
            {"name": "rsi", "params": {"period": 14}, "color": "#8B5CF6"},
            {"name": "atr", "params": {"period": 14}, "color": "#F97316"},
            {"name": "cci", "params": {"period": 20}, "color": "#F59E0B"},
            {"name": "donchian", "params": {"period": 20}, "color": "#0EA5E9"},
        ],
        max_indicators=6,
        max_patterns=4,
        max_sr_levels=10,
        max_liquidity_zones=6,
        max_hypothesis_paths=2,
        show_patterns=True,
        show_support_resistance=True,
        show_liquidity_zones=True,
        show_hypothesis=True,
        show_volume_profile=True,
        sr_priority=0.9,
        pattern_priority=0.6,
    ),
    
    PresetType.VOLATILE: ChartPreset(
        preset_id="volatile",
        name="High Volatility",
        description="For volatile/stress market conditions",
        preset_type=PresetType.VOLATILE,
        indicators=[
            {"name": "atr", "params": {"period": 14}, "color": "#EF4444"},
            {"name": "bollinger", "params": {"period": 20, "std_dev": 2.5}, "color": "#06B6D4"},
        ],
        max_indicators=3,
        max_patterns=2,
        max_sr_levels=6,
        max_liquidity_zones=6,
        max_hypothesis_paths=3,
        show_patterns=True,
        show_support_resistance=True,
        show_liquidity_zones=True,
        show_hypothesis=True,
        show_liquidations=True,
        show_funding=True,
        hypothesis_priority=0.7,
        pattern_priority=0.5,
    ),
    
    PresetType.COMPRESSION: ChartPreset(
        preset_id="compression",
        name="Compression Setup",
        description="For low volatility compression before breakout",
        preset_type=PresetType.COMPRESSION,
        indicators=[
            {"name": "bollinger", "params": {"period": 20, "std_dev": 2}, "color": "#06B6D4"},
            {"name": "atr", "params": {"period": 14}, "color": "#F97316"},
        ],
        max_indicators=3,
        max_patterns=5,
        max_sr_levels=8,
        max_hypothesis_paths=3,
        show_patterns=True,
        show_support_resistance=True,
        show_hypothesis=True,
        show_volume_profile=True,
        pattern_priority=0.9,
        hypothesis_priority=0.8,
    ),
    
    PresetType.BREAKOUT: ChartPreset(
        preset_id="breakout",
        name="Breakout Setup",
        description="For breakout trading",
        preset_type=PresetType.BREAKOUT,
        indicators=[
            {"name": "ema", "params": {"period": 20}, "color": "#10B981"},
            {"name": "vwap", "params": {}, "color": "#EC4899"},
            {"name": "atr", "params": {"period": 14}, "color": "#F97316"},
        ],
        max_indicators=4,
        max_patterns=3,
        max_sr_levels=6,
        max_hypothesis_paths=2,
        show_patterns=True,
        show_support_resistance=True,
        show_hypothesis=True,
        show_fractals=True,
        pattern_priority=0.95,
        hypothesis_priority=0.85,
    ),
    
    PresetType.SCALPING: ChartPreset(
        preset_id="scalping",
        name="Scalping Mode",
        description="For short-term scalping",
        preset_type=PresetType.SCALPING,
        indicators=[
            {"name": "ema", "params": {"period": 9}, "color": "#10B981"},
            {"name": "ema", "params": {"period": 21}, "color": "#F59E0B"},
            {"name": "vwap", "params": {}, "color": "#EC4899"},
            {"name": "rsi", "params": {"period": 7}, "color": "#8B5CF6"},
        ],
        max_indicators=5,
        max_patterns=2,
        max_sr_levels=4,
        max_liquidity_zones=4,
        max_hypothesis_paths=1,
        show_patterns=True,
        show_support_resistance=True,
        show_liquidity_zones=True,
        show_hypothesis=False,
        show_liquidations=True,
        show_funding=True,
        sr_priority=0.9,
    ),
    
    PresetType.SWING: ChartPreset(
        preset_id="swing",
        name="Swing Trading",
        description="For multi-day swing trading",
        preset_type=PresetType.SWING,
        indicators=[
            {"name": "ema", "params": {"period": 50}, "color": "#10B981"},
            {"name": "ema", "params": {"period": 200}, "color": "#F59E0B"},
            {"name": "rsi", "params": {"period": 14}, "color": "#8B5CF6"},
            {"name": "macd", "params": {"fast": 12, "slow": 26, "signal": 9}, "color": "#EF4444"},
        ],
        max_indicators=5,
        max_patterns=5,
        max_sr_levels=8,
        max_hypothesis_paths=3,
        max_fractal_matches=3,
        show_patterns=True,
        show_support_resistance=True,
        show_hypothesis=True,
        show_fractals=True,
        hypothesis_priority=0.85,
        fractal_priority=0.75,
    ),
}


def get_preset_for_regime(regime: str) -> ChartPreset:
    """Get appropriate preset for market regime."""
    regime_lower = regime.lower()
    
    if "trend_up" in regime_lower or "trending_up" in regime_lower:
        return REGIME_PRESETS[PresetType.TREND_UP]
    elif "trend_down" in regime_lower or "trending_down" in regime_lower:
        return REGIME_PRESETS[PresetType.TREND_DOWN]
    elif "range" in regime_lower or "ranging" in regime_lower:
        return REGIME_PRESETS[PresetType.RANGE]
    elif "volatile" in regime_lower or "volatil" in regime_lower:
        return REGIME_PRESETS[PresetType.VOLATILE]
    elif "compress" in regime_lower:
        return REGIME_PRESETS[PresetType.COMPRESSION]
    elif "breakout" in regime_lower:
        return REGIME_PRESETS[PresetType.BREAKOUT]
    else:
        return REGIME_PRESETS[PresetType.RANGE]  # Default
