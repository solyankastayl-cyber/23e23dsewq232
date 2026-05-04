"""
Research Presets Engine — PHASE 48.6

User-Selectable Research API:
- Suggested indicators per regime
- User-selected overlays
- Combined chart payload
- Research presets by market state
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

class MarketRegime(str, Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    COMPRESSION = "compression"
    BREAKOUT = "breakout"


class ResearchPreset(BaseModel):
    """Research visualization preset."""
    preset_id: str
    name: str
    description: str
    
    # Regime this preset is designed for
    target_regime: MarketRegime
    
    # Recommended indicators
    indicators: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Recommended overlays
    overlays: List[str] = Field(default_factory=list)
    
    # Feature flags
    show_hypotheses: bool = True
    show_fractals: bool = False
    show_volume_profile: bool = False
    show_liquidations: bool = False
    show_funding: bool = False
    
    # Colors and styling
    theme: str = "default"


class UserChartConfig(BaseModel):
    """User's chart configuration."""
    user_id: str = "default"
    symbol: str
    timeframe: str
    
    # Selected indicators
    indicators: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Selected overlays
    overlays: List[str] = Field(default_factory=list)
    
    # Features
    show_hypotheses: bool = True
    show_fractals: bool = False
    show_patterns: bool = True
    show_support_resistance: bool = True
    
    # Applied preset (if any)
    preset_id: Optional[str] = None


class ChartSuggestion(BaseModel):
    """System suggestion for chart configuration."""
    regime: MarketRegime
    confidence: float
    
    suggested_indicators: List[Dict[str, Any]] = Field(default_factory=list)
    suggested_overlays: List[str] = Field(default_factory=list)
    
    reason: str = ""


# ═══════════════════════════════════════════════════════════════
# Presets
# ═══════════════════════════════════════════════════════════════

DEFAULT_PRESETS = {
    "trending_btc": ResearchPreset(
        preset_id="trending_btc",
        name="Trending BTC",
        description="Optimal for trending BTC markets",
        target_regime=MarketRegime.TRENDING_UP,
        indicators=[
            {"name": "ema", "params": {"period": 50}, "color": "#10B981"},
            {"name": "ema", "params": {"period": 200}, "color": "#F59E0B"},
            {"name": "rsi", "params": {"period": 14}, "color": "#8B5CF6"},
            {"name": "atr", "params": {"period": 14}, "color": "#EF4444"},
        ],
        overlays=["trend_channel", "breakout_zones", "fractal_projection", "capital_flow_bias"],
        show_hypotheses=True,
        show_fractals=True,
    ),
    
    "mean_reversion": ResearchPreset(
        preset_id="mean_reversion",
        name="Mean Reversion",
        description="Optimal for ranging markets",
        target_regime=MarketRegime.RANGING,
        indicators=[
            {"name": "bollinger", "params": {"period": 20, "std_dev": 2}, "color": "#06B6D4"},
            {"name": "rsi", "params": {"period": 14}, "color": "#8B5CF6"},
            {"name": "atr", "params": {"period": 14}, "color": "#EF4444"},
        ],
        overlays=["support_resistance", "liquidity_zones", "reversal_hypotheses"],
        show_hypotheses=True,
        show_volume_profile=True,
    ),
    
    "volatile_stress": ResearchPreset(
        preset_id="volatile_stress",
        name="Volatile / Stress",
        description="For high volatility conditions",
        target_regime=MarketRegime.VOLATILE,
        indicators=[
            {"name": "atr", "params": {"period": 14}, "color": "#EF4444"},
            {"name": "bollinger", "params": {"period": 20, "std_dev": 2.5}, "color": "#06B6D4"},
        ],
        overlays=["liquidity_zones", "cascade_risk", "invalidation_lines", "simulation_cones"],
        show_hypotheses=True,
        show_liquidations=True,
        show_funding=True,
    ),
    
    "compression_setup": ResearchPreset(
        preset_id="compression_setup",
        name="Compression Setup",
        description="For low volatility compression",
        target_regime=MarketRegime.COMPRESSION,
        indicators=[
            {"name": "bollinger", "params": {"period": 20, "std_dev": 2}, "color": "#06B6D4"},
            {"name": "atr", "params": {"period": 14}, "color": "#EF4444"},
        ],
        overlays=["compression_zone", "breakout_levels", "volume_profile"],
        show_hypotheses=True,
        show_volume_profile=True,
    ),
    
    "scalping": ResearchPreset(
        preset_id="scalping",
        name="Scalping Mode",
        description="For short-term trading",
        target_regime=MarketRegime.TRENDING_UP,
        indicators=[
            {"name": "ema", "params": {"period": 9}, "color": "#10B981"},
            {"name": "ema", "params": {"period": 21}, "color": "#F59E0B"},
            {"name": "vwap", "params": {}, "color": "#EC4899"},
            {"name": "rsi", "params": {"period": 7}, "color": "#8B5CF6"},
        ],
        overlays=["support_resistance", "liquidation_markers"],
        show_liquidations=True,
        show_funding=True,
    ),
}


# ═══════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════

class ResearchPresetsService:
    """Service for research presets and suggestions."""
    
    def __init__(self):
        self.presets = DEFAULT_PRESETS.copy()
    
    def get_all_presets(self) -> List[ResearchPreset]:
        """Get all available presets."""
        return list(self.presets.values())
    
    def get_preset(self, preset_id: str) -> Optional[ResearchPreset]:
        """Get a specific preset."""
        return self.presets.get(preset_id)
    
    def detect_regime(self, candles: List[Dict[str, Any]]) -> MarketRegime:
        """Detect current market regime."""
        if not candles or len(candles) < 20:
            return MarketRegime.RANGING
        
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        
        # Calculate metrics
        import numpy as np
        
        # Trend strength
        price_change = (closes[-1] - closes[-20]) / closes[-20] if closes[-20] > 0 else 0
        
        # Volatility (ATR-based)
        atr_values = []
        for i in range(1, len(candles)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            atr_values.append(tr)
        
        recent_atr = np.mean(atr_values[-14:]) if len(atr_values) >= 14 else np.mean(atr_values)
        historical_atr = np.mean(atr_values[-50:-14]) if len(atr_values) >= 50 else recent_atr
        
        volatility_ratio = recent_atr / historical_atr if historical_atr > 0 else 1.0
        
        # Determine regime
        if volatility_ratio < 0.6:
            return MarketRegime.COMPRESSION
        elif volatility_ratio > 1.5:
            return MarketRegime.VOLATILE
        elif price_change > 0.05:
            return MarketRegime.TRENDING_UP
        elif price_change < -0.05:
            return MarketRegime.TRENDING_DOWN
        else:
            return MarketRegime.RANGING
    
    def get_suggestions(
        self,
        candles: List[Dict[str, Any]],
        symbol: str = "BTCUSDT"
    ) -> ChartSuggestion:
        """Get system suggestions based on market state."""
        
        regime = self.detect_regime(candles)
        
        # Select appropriate preset
        if regime == MarketRegime.TRENDING_UP:
            preset = self.presets.get("trending_btc")
        elif regime == MarketRegime.TRENDING_DOWN:
            preset = self.presets.get("trending_btc")  # Same indicators, different context
        elif regime == MarketRegime.VOLATILE:
            preset = self.presets.get("volatile_stress")
        elif regime == MarketRegime.COMPRESSION:
            preset = self.presets.get("compression_setup")
        else:
            preset = self.presets.get("mean_reversion")
        
        reason_map = {
            MarketRegime.TRENDING_UP: "Strong uptrend detected. Using trend-following indicators.",
            MarketRegime.TRENDING_DOWN: "Downtrend detected. Using trend-following indicators.",
            MarketRegime.VOLATILE: "High volatility detected. Using risk-focused overlays.",
            MarketRegime.COMPRESSION: "Low volatility compression. Watching for breakout.",
            MarketRegime.RANGING: "Range-bound market. Using mean reversion setup.",
        }
        
        return ChartSuggestion(
            regime=regime,
            confidence=0.75,
            suggested_indicators=preset.indicators if preset else [],
            suggested_overlays=preset.overlays if preset else [],
            reason=reason_map.get(regime, ""),
        )
    
    def build_combined_config(
        self,
        system_suggestions: ChartSuggestion,
        user_config: Optional[UserChartConfig] = None
    ) -> Dict[str, Any]:
        """Build combined chart config from system + user preferences."""
        
        # Start with system suggestions
        combined = {
            "indicators": list(system_suggestions.suggested_indicators),
            "overlays": list(system_suggestions.suggested_overlays),
            "regime": system_suggestions.regime.value,
            "source": "system",
        }
        
        # Merge user preferences
        if user_config:
            # Add user indicators not in system suggestions
            for ind in user_config.indicators:
                if ind not in combined["indicators"]:
                    combined["indicators"].append(ind)
            
            # Add user overlays
            for overlay in user_config.overlays:
                if overlay not in combined["overlays"]:
                    combined["overlays"].append(overlay)
            
            # User feature flags
            combined["show_hypotheses"] = user_config.show_hypotheses
            combined["show_fractals"] = user_config.show_fractals
            combined["show_patterns"] = user_config.show_patterns
            combined["show_support_resistance"] = user_config.show_support_resistance
            
            combined["source"] = "merged"
        else:
            # Default feature flags from suggestion
            combined["show_hypotheses"] = True
            combined["show_fractals"] = system_suggestions.regime in [
                MarketRegime.TRENDING_UP, 
                MarketRegime.TRENDING_DOWN
            ]
            combined["show_patterns"] = True
            combined["show_support_resistance"] = True
        
        return combined
    
    def get_available_indicators(self) -> List[Dict[str, Any]]:
        """Get all available indicators."""
        return [
            {"name": "sma", "display": "SMA", "params": ["period"]},
            {"name": "ema", "display": "EMA", "params": ["period"]},
            {"name": "vwap", "display": "VWAP", "params": []},
            {"name": "rsi", "display": "RSI", "params": ["period"]},
            {"name": "macd", "display": "MACD", "params": ["fast", "slow", "signal"]},
            {"name": "bollinger", "display": "Bollinger Bands", "params": ["period", "std_dev"]},
            {"name": "atr", "display": "ATR", "params": ["period"]},
            {"name": "supertrend", "display": "Supertrend", "params": ["period", "multiplier"]},
            {"name": "volume_profile", "display": "Volume Profile", "params": ["bins"]},
        ]
    
    def get_available_overlays(self) -> List[Dict[str, Any]]:
        """Get all available overlays."""
        return [
            {"name": "support_resistance", "display": "Support/Resistance"},
            {"name": "trend_lines", "display": "Trend Lines"},
            {"name": "trend_channel", "display": "Trend Channel"},
            {"name": "liquidity_zones", "display": "Liquidity Zones"},
            {"name": "patterns", "display": "Chart Patterns"},
            {"name": "hypotheses", "display": "Hypothesis Paths"},
            {"name": "fractals", "display": "Fractal Projections"},
            {"name": "breakout_zones", "display": "Breakout Zones"},
            {"name": "invalidation_lines", "display": "Invalidation Lines"},
        ]


# Singleton
_presets_service: Optional[ResearchPresetsService] = None

def get_presets_service() -> ResearchPresetsService:
    global _presets_service
    if _presets_service is None:
        _presets_service = ResearchPresetsService()
    return _presets_service
