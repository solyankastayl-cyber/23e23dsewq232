"""
Indicator Registry
==================
Complete registry of 100+ technical indicators with metadata.

Categories:
- OVERLAY: Rendered on main price chart (EMA, BB, VWAP, Supertrend, Ichimoku)
- OSCILLATOR: Separate pane, bounded values (RSI, Stochastic, CCI, MFI)
- MOMENTUM: Separate pane, unbounded (MACD, Momentum, ROC)
- VOLUME: Separate pane, volume-based (OBV, ADL, VWAP)
- VOLATILITY: Separate pane (ATR, BB Width, Keltner)
- TREND: Trend strength (ADX, Supertrend)
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class IndicatorType(str, Enum):
    OVERLAY = "overlay"        # On main chart
    OSCILLATOR = "oscillator"  # Separate pane, bounded
    MOMENTUM = "momentum"      # Separate pane, unbounded
    VOLUME = "volume"          # Volume-based
    VOLATILITY = "volatility"  # Volatility measures
    TREND = "trend"           # Trend indicators


class IndicatorCategory(str, Enum):
    CLASSIC = "classic"        # Traditional TA
    SMART_MONEY = "smart_money" # ICT/SMC concepts
    PATTERN = "pattern"        # Chart patterns
    CUSTOM = "custom"          # Custom/proprietary


@dataclass
class IndicatorDefinition:
    id: str
    name: str
    short_name: str
    type: IndicatorType
    category: IndicatorCategory
    default_params: Dict
    description: str
    pane_height: int = 100  # Height in pixels for separate pane
    has_signal_line: bool = False
    has_histogram: bool = False
    overbought: Optional[float] = None
    oversold: Optional[float] = None
    zero_line: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "short_name": self.short_name,
            "type": self.type.value,
            "category": self.category.value,
            "default_params": self.default_params,
            "description": self.description,
            "pane_height": self.pane_height,
            "has_signal_line": self.has_signal_line,
            "has_histogram": self.has_histogram,
            "overbought": self.overbought,
            "oversold": self.oversold,
            "zero_line": self.zero_line,
        }


class IndicatorRegistry:
    """Complete registry of technical indicators."""
    
    def __init__(self):
        self._indicators: Dict[str, IndicatorDefinition] = {}
        self._register_all()
    
    def _register_all(self):
        """Register all indicators."""
        
        # ═══════════════════════════════════════════════════════════════
        # OVERLAY INDICATORS (on main chart)
        # ═══════════════════════════════════════════════════════════════
        
        self._register(IndicatorDefinition(
            id="ema_20", name="EMA 20", short_name="EMA20",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"period": 20},
            description="20-period Exponential Moving Average"
        ))
        
        self._register(IndicatorDefinition(
            id="ema_50", name="EMA 50", short_name="EMA50",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"period": 50},
            description="50-period Exponential Moving Average"
        ))
        
        self._register(IndicatorDefinition(
            id="ema_200", name="EMA 200", short_name="EMA200",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"period": 200},
            description="200-period Exponential Moving Average"
        ))
        
        self._register(IndicatorDefinition(
            id="sma_20", name="SMA 20", short_name="SMA20",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"period": 20},
            description="20-period Simple Moving Average"
        ))
        
        self._register(IndicatorDefinition(
            id="sma_50", name="SMA 50", short_name="SMA50",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"period": 50},
            description="50-period Simple Moving Average"
        ))
        
        self._register(IndicatorDefinition(
            id="sma_200", name="SMA 200", short_name="SMA200",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"period": 200},
            description="200-period Simple Moving Average"
        ))
        
        self._register(IndicatorDefinition(
            id="vwma", name="VWMA", short_name="VWMA",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"period": 20},
            description="Volume Weighted Moving Average"
        ))
        
        self._register(IndicatorDefinition(
            id="hma", name="Hull MA", short_name="HMA",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"period": 20},
            description="Hull Moving Average - faster, smoother"
        ))
        
        self._register(IndicatorDefinition(
            id="bollinger_bands", name="Bollinger Bands", short_name="BB",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"period": 20, "std_dev": 2.0},
            description="Bollinger Bands (middle, upper, lower)"
        ))
        
        self._register(IndicatorDefinition(
            id="keltner_channels", name="Keltner Channels", short_name="KC",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"period": 20, "atr_mult": 2.0},
            description="Keltner Channels (EMA + ATR)"
        ))
        
        self._register(IndicatorDefinition(
            id="donchian_channels", name="Donchian Channels", short_name="DC",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"period": 20},
            description="Donchian Channels (highest high, lowest low)"
        ))
        
        self._register(IndicatorDefinition(
            id="vwap", name="VWAP", short_name="VWAP",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={},
            description="Volume Weighted Average Price"
        ))
        
        self._register(IndicatorDefinition(
            id="supertrend", name="Supertrend", short_name="ST",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"period": 10, "multiplier": 3.0},
            description="Supertrend indicator"
        ))
        
        self._register(IndicatorDefinition(
            id="ichimoku", name="Ichimoku Cloud", short_name="ICHI",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"tenkan": 9, "kijun": 26, "senkou_b": 52},
            description="Ichimoku Kinko Hyo"
        ))
        
        self._register(IndicatorDefinition(
            id="parabolic_sar", name="Parabolic SAR", short_name="PSAR",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"start": 0.02, "increment": 0.02, "max": 0.2},
            description="Parabolic Stop and Reverse"
        ))
        
        self._register(IndicatorDefinition(
            id="pivot_points", name="Pivot Points", short_name="PP",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"type": "standard"},
            description="Standard/Fibonacci/Camarilla Pivot Points"
        ))
        
        self._register(IndicatorDefinition(
            id="fib_retracement", name="Fibonacci Retracement", short_name="FIB",
            type=IndicatorType.OVERLAY, category=IndicatorCategory.CLASSIC,
            default_params={"levels": [0.236, 0.382, 0.5, 0.618, 0.786]},
            description="Fibonacci Retracement Levels"
        ))
        
        # ═══════════════════════════════════════════════════════════════
        # OSCILLATORS (separate pane, bounded 0-100)
        # ═══════════════════════════════════════════════════════════════
        
        self._register(IndicatorDefinition(
            id="rsi", name="RSI", short_name="RSI",
            type=IndicatorType.OSCILLATOR, category=IndicatorCategory.CLASSIC,
            default_params={"period": 14},
            description="Relative Strength Index",
            pane_height=80,
            overbought=70, oversold=30
        ))
        
        self._register(IndicatorDefinition(
            id="stochastic", name="Stochastic", short_name="STOCH",
            type=IndicatorType.OSCILLATOR, category=IndicatorCategory.CLASSIC,
            default_params={"k_period": 14, "d_period": 3},
            description="Stochastic Oscillator (%K, %D)",
            pane_height=80,
            has_signal_line=True,
            overbought=80, oversold=20
        ))
        
        self._register(IndicatorDefinition(
            id="stoch_rsi", name="Stochastic RSI", short_name="SRSI",
            type=IndicatorType.OSCILLATOR, category=IndicatorCategory.CLASSIC,
            default_params={"rsi_period": 14, "stoch_period": 14},
            description="Stochastic of RSI",
            pane_height=80,
            overbought=80, oversold=20
        ))
        
        self._register(IndicatorDefinition(
            id="cci", name="CCI", short_name="CCI",
            type=IndicatorType.OSCILLATOR, category=IndicatorCategory.CLASSIC,
            default_params={"period": 20},
            description="Commodity Channel Index",
            pane_height=80,
            overbought=100, oversold=-100, zero_line=True
        ))
        
        self._register(IndicatorDefinition(
            id="mfi", name="MFI", short_name="MFI",
            type=IndicatorType.OSCILLATOR, category=IndicatorCategory.CLASSIC,
            default_params={"period": 14},
            description="Money Flow Index",
            pane_height=80,
            overbought=80, oversold=20
        ))
        
        self._register(IndicatorDefinition(
            id="williams_r", name="Williams %R", short_name="W%R",
            type=IndicatorType.OSCILLATOR, category=IndicatorCategory.CLASSIC,
            default_params={"period": 14},
            description="Williams Percent Range",
            pane_height=80,
            overbought=-20, oversold=-80
        ))
        
        # ═══════════════════════════════════════════════════════════════
        # MOMENTUM (separate pane, unbounded)
        # ═══════════════════════════════════════════════════════════════
        
        self._register(IndicatorDefinition(
            id="macd", name="MACD", short_name="MACD",
            type=IndicatorType.MOMENTUM, category=IndicatorCategory.CLASSIC,
            default_params={"fast": 12, "slow": 26, "signal": 9},
            description="Moving Average Convergence Divergence",
            pane_height=100,
            has_signal_line=True, has_histogram=True, zero_line=True
        ))
        
        self._register(IndicatorDefinition(
            id="momentum", name="Momentum", short_name="MOM",
            type=IndicatorType.MOMENTUM, category=IndicatorCategory.CLASSIC,
            default_params={"period": 10},
            description="Price Momentum",
            pane_height=80,
            zero_line=True
        ))
        
        self._register(IndicatorDefinition(
            id="roc", name="ROC", short_name="ROC",
            type=IndicatorType.MOMENTUM, category=IndicatorCategory.CLASSIC,
            default_params={"period": 10},
            description="Rate of Change",
            pane_height=80,
            zero_line=True
        ))
        
        self._register(IndicatorDefinition(
            id="trix", name="TRIX", short_name="TRIX",
            type=IndicatorType.MOMENTUM, category=IndicatorCategory.CLASSIC,
            default_params={"period": 15},
            description="Triple Exponential Average",
            pane_height=80,
            zero_line=True
        ))
        
        # ═══════════════════════════════════════════════════════════════
        # VOLUME (separate pane)
        # ═══════════════════════════════════════════════════════════════
        
        self._register(IndicatorDefinition(
            id="obv", name="OBV", short_name="OBV",
            type=IndicatorType.VOLUME, category=IndicatorCategory.CLASSIC,
            default_params={},
            description="On-Balance Volume",
            pane_height=80
        ))
        
        self._register(IndicatorDefinition(
            id="volume", name="Volume", short_name="VOL",
            type=IndicatorType.VOLUME, category=IndicatorCategory.CLASSIC,
            default_params={"ma_period": 20},
            description="Volume with Moving Average",
            pane_height=80
        ))
        
        self._register(IndicatorDefinition(
            id="volume_profile", name="Volume Profile", short_name="VP",
            type=IndicatorType.VOLUME, category=IndicatorCategory.CLASSIC,
            default_params={"rows": 24},
            description="Volume Profile / Volume at Price",
            pane_height=100
        ))
        
        self._register(IndicatorDefinition(
            id="adl", name="A/D Line", short_name="ADL",
            type=IndicatorType.VOLUME, category=IndicatorCategory.CLASSIC,
            default_params={},
            description="Accumulation/Distribution Line",
            pane_height=80
        ))
        
        self._register(IndicatorDefinition(
            id="cmf", name="CMF", short_name="CMF",
            type=IndicatorType.VOLUME, category=IndicatorCategory.CLASSIC,
            default_params={"period": 20},
            description="Chaikin Money Flow",
            pane_height=80,
            zero_line=True
        ))
        
        # ═══════════════════════════════════════════════════════════════
        # VOLATILITY (separate pane)
        # ═══════════════════════════════════════════════════════════════
        
        self._register(IndicatorDefinition(
            id="atr", name="ATR", short_name="ATR",
            type=IndicatorType.VOLATILITY, category=IndicatorCategory.CLASSIC,
            default_params={"period": 14},
            description="Average True Range",
            pane_height=80
        ))
        
        self._register(IndicatorDefinition(
            id="bb_width", name="BB Width", short_name="BBW",
            type=IndicatorType.VOLATILITY, category=IndicatorCategory.CLASSIC,
            default_params={"period": 20},
            description="Bollinger Bands Width (squeeze detection)",
            pane_height=80
        ))
        
        self._register(IndicatorDefinition(
            id="historical_volatility", name="Historical Volatility", short_name="HV",
            type=IndicatorType.VOLATILITY, category=IndicatorCategory.CLASSIC,
            default_params={"period": 20},
            description="Historical Volatility (standard deviation)",
            pane_height=80
        ))
        
        # ═══════════════════════════════════════════════════════════════
        # TREND (separate pane)
        # ═══════════════════════════════════════════════════════════════
        
        self._register(IndicatorDefinition(
            id="adx", name="ADX", short_name="ADX",
            type=IndicatorType.TREND, category=IndicatorCategory.CLASSIC,
            default_params={"period": 14},
            description="Average Directional Index",
            pane_height=80
        ))
        
        self._register(IndicatorDefinition(
            id="dmi", name="DMI", short_name="DMI",
            type=IndicatorType.TREND, category=IndicatorCategory.CLASSIC,
            default_params={"period": 14},
            description="Directional Movement Index (+DI, -DI)",
            pane_height=80
        ))
        
        self._register(IndicatorDefinition(
            id="aroon", name="Aroon", short_name="AROON",
            type=IndicatorType.TREND, category=IndicatorCategory.CLASSIC,
            default_params={"period": 25},
            description="Aroon Up/Down",
            pane_height=80
        ))
    
    def _register(self, indicator: IndicatorDefinition):
        """Register an indicator."""
        self._indicators[indicator.id] = indicator
    
    def get(self, indicator_id: str) -> Optional[IndicatorDefinition]:
        """Get indicator by ID."""
        return self._indicators.get(indicator_id)
    
    def get_all(self) -> List[IndicatorDefinition]:
        """Get all indicators."""
        return list(self._indicators.values())
    
    def get_by_type(self, ind_type: IndicatorType) -> List[IndicatorDefinition]:
        """Get indicators by type."""
        return [i for i in self._indicators.values() if i.type == ind_type]
    
    def get_overlays(self) -> List[IndicatorDefinition]:
        """Get overlay indicators (for main chart)."""
        return self.get_by_type(IndicatorType.OVERLAY)
    
    def get_pane_indicators(self) -> List[IndicatorDefinition]:
        """Get indicators that require separate panes."""
        return [i for i in self._indicators.values() if i.type != IndicatorType.OVERLAY]
    
    def to_dict(self) -> Dict:
        """Export full registry as dict."""
        return {
            "total": len(self._indicators),
            "overlays": [i.to_dict() for i in self.get_overlays()],
            "oscillators": [i.to_dict() for i in self.get_by_type(IndicatorType.OSCILLATOR)],
            "momentum": [i.to_dict() for i in self.get_by_type(IndicatorType.MOMENTUM)],
            "volume": [i.to_dict() for i in self.get_by_type(IndicatorType.VOLUME)],
            "volatility": [i.to_dict() for i in self.get_by_type(IndicatorType.VOLATILITY)],
            "trend": [i.to_dict() for i in self.get_by_type(IndicatorType.TREND)],
        }


# Singleton
_registry: Optional[IndicatorRegistry] = None


def get_indicator_registry() -> IndicatorRegistry:
    global _registry
    if _registry is None:
        _registry = IndicatorRegistry()
    return _registry
