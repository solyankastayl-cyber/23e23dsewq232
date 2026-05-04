"""
Chart Composer — PHASE 50

Composes final chart view based on:
- Market regime
- Preset configuration
- Object priorities
- Visual limits
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from .presets import ChartPreset, PresetType, get_preset_for_regime, REGIME_PRESETS
from ..visual_objects.models import ChartObject, ObjectCategory
from ..visual_objects.builder import ChartObjectBuilder


# ═══════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════

class ComposedChart(BaseModel):
    """Final composed chart for frontend."""
    
    # Context
    symbol: str
    timeframe: str
    timestamp: datetime
    
    # Market state
    market_regime: str
    capital_flow_bias: str = "neutral"
    
    # Price data
    candles: List[Dict[str, Any]] = Field(default_factory=list)
    volume: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Visual objects (filtered and prioritized)
    objects: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Indicators (pre-calculated)
    indicators: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Hypothesis (if enabled)
    hypothesis: Optional[Dict[str, Any]] = None
    
    # Fractal matches (if enabled)
    fractal_matches: List[Dict[str, Any]] = Field(default_factory=list)
    
    # UI configuration
    suggested_indicators: List[str] = Field(default_factory=list)
    active_preset: str = "default"
    
    # NEW: Feature vector for multi-factor analysis
    feature_vector: Optional[Dict[str, Any]] = None
    
    # NEW: Top indicator signal drivers
    indicator_signals: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Statistics
    stats: Dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# Composer
# ═══════════════════════════════════════════════════════════════

class ChartComposer:
    """Composes final chart view."""
    
    def __init__(self):
        self._object_builder = ChartObjectBuilder()
    
    async def compose(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict[str, Any]],
        volume: List[Dict[str, Any]],
        patterns: List[Dict[str, Any]],
        support_resistance: List[Dict[str, Any]],
        liquidity_zones: List[Dict[str, Any]],
        indicators: List[Dict[str, Any]],
        hypothesis: Optional[Dict[str, Any]],
        fractal_matches: List[Dict[str, Any]],
        market_regime: str,
        capital_flow_bias: str = "neutral",
        preset: Optional[ChartPreset] = None,
        user_config: Optional[Dict[str, Any]] = None,
    ) -> ComposedChart:
        """Compose final chart with all objects."""
        
        # Get preset for regime if not provided
        if preset is None:
            preset = get_preset_for_regime(market_regime)
        
        # Clear builder
        self._object_builder.clear()
        
        # Convert research data to visual objects
        all_objects = []
        
        # Patterns -> Objects
        if preset.show_patterns and patterns:
            pattern_objects = self._object_builder.from_patterns(
                patterns[:preset.max_patterns],
                symbol, timeframe
            )
            all_objects.extend(pattern_objects)
        
        # S/R -> Objects
        if preset.show_support_resistance and support_resistance:
            sr_objects = self._object_builder.from_support_resistance(
                support_resistance[:preset.max_sr_levels],
                symbol, timeframe, candles
            )
            all_objects.extend(sr_objects)
        
        # Liquidity zones -> Objects
        if preset.show_liquidity_zones and liquidity_zones:
            liq_objects = self._object_builder.from_liquidity_zones(
                liquidity_zones[:preset.max_liquidity_zones],
                symbol, timeframe, candles
            )
            all_objects.extend(liq_objects)
        
        # Hypothesis -> Objects
        hypothesis_data = None
        if preset.show_hypothesis and hypothesis:
            hyp_objects = self._object_builder.from_hypothesis(
                hypothesis, symbol, timeframe
            )
            all_objects.extend(hyp_objects)
            hypothesis_data = hypothesis
        
        # Fractals -> Objects
        fractal_data = []
        if preset.show_fractals and fractal_matches:
            frac_objects = self._object_builder.from_fractals(
                fractal_matches[:preset.max_fractal_matches],
                symbol, timeframe
            )
            all_objects.extend(frac_objects)
            fractal_data = fractal_matches[:preset.max_fractal_matches]
        
        # Indicators -> Objects
        ind_objects = []
        if indicators:
            # Filter indicators based on preset
            filtered_indicators = indicators[:preset.max_indicators]
            ind_objects = self._object_builder.from_indicators(
                filtered_indicators, symbol, timeframe
            )
            all_objects.extend(ind_objects)
        
        # Apply filtering and prioritization
        filtered_objects = self._filter_and_prioritize(
            all_objects, preset
        )
        
        # Build suggested indicators list based on regime
        suggested = self._get_suggested_indicators(market_regime)
        
        # Calculate stats
        stats = {
            "total_objects": len(filtered_objects),
            "patterns_shown": sum(1 for o in filtered_objects if o.category == ObjectCategory.PATTERN),
            "levels_shown": sum(1 for o in filtered_objects if o.category == ObjectCategory.LIQUIDITY),
            "hypothesis_shown": sum(1 for o in filtered_objects if o.category == ObjectCategory.HYPOTHESIS),
            "fractals_shown": sum(1 for o in filtered_objects if o.category == ObjectCategory.FRACTAL),
            "indicators_shown": sum(1 for o in filtered_objects if o.category == ObjectCategory.INDICATOR),
        }
        
        return ComposedChart(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now(timezone.utc),
            market_regime=market_regime,
            capital_flow_bias=capital_flow_bias,
            candles=candles,
            volume=volume,
            objects=[self._serialize_object(o) for o in filtered_objects],
            indicators=[self._serialize_object(o) for o in ind_objects],
            hypothesis=hypothesis_data,
            fractal_matches=fractal_data,
            suggested_indicators=suggested,
            active_preset=preset.preset_id,
            stats=stats,
        )
    
    def _filter_and_prioritize(
        self,
        objects: List[ChartObject],
        preset: ChartPreset
    ) -> List[ChartObject]:
        """Filter and prioritize objects based on preset."""
        
        # Score objects
        scored = []
        for obj in objects:
            score = obj.priority / 10.0  # Normalize to 0-1
            
            # Apply preset weights
            if obj.category == ObjectCategory.PATTERN:
                score *= preset.pattern_priority
            elif obj.category == ObjectCategory.LIQUIDITY:
                score *= preset.sr_priority
            elif obj.category == ObjectCategory.HYPOTHESIS:
                score *= preset.hypothesis_priority
            elif obj.category == ObjectCategory.FRACTAL:
                score *= preset.fractal_priority
            
            # Boost confirmed patterns
            if obj.metadata.get("status") == "confirmed":
                score *= 1.2
            
            # Boost high confidence
            if obj.confidence and obj.confidence > 0.7:
                score *= 1.1
            
            scored.append((score, obj))
        
        # Sort by score
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Apply limits per category
        result = []
        category_counts = {c: 0 for c in ObjectCategory}
        
        category_limits = {
            ObjectCategory.PATTERN: preset.max_patterns,
            ObjectCategory.LIQUIDITY: preset.max_sr_levels + preset.max_liquidity_zones,
            ObjectCategory.HYPOTHESIS: preset.max_hypothesis_paths * 3,  # Entry, SL, TPs
            ObjectCategory.FRACTAL: preset.max_fractal_matches * 2,  # Ref + projection
            ObjectCategory.INDICATOR: preset.max_indicators,
            ObjectCategory.GEOMETRY: 10,
        }
        
        for score, obj in scored:
            limit = category_limits.get(obj.category, 10)
            
            if category_counts[obj.category] < limit:
                result.append(obj)
                category_counts[obj.category] += 1
        
        return result
    
    def _serialize_object(self, obj: ChartObject) -> Dict[str, Any]:
        """Serialize chart object for JSON response."""
        return {
            "id": obj.id,
            "type": obj.type.value,
            "category": obj.category.value,
            "symbol": obj.symbol,
            "timeframe": obj.timeframe,
            "points": [
                {"timestamp": p.timestamp, "price": p.price}
                for p in obj.points
            ],
            "series": obj.series,
            "timestamps": obj.timestamps,
            "upper_band": obj.upper_band,
            "lower_band": obj.lower_band,
            "middle_band": obj.middle_band,
            "style": obj.style.model_dump(),
            "label": obj.label,
            "confidence": obj.confidence,
            "priority": obj.priority,
            "metadata": obj.metadata,
        }
    
    def _get_suggested_indicators(self, market_regime: str) -> List[str]:
        """Get suggested indicators based on market regime."""
        regime = market_regime.lower()
        
        if "trend" in regime or "bullish" in regime or "bearish" in regime:
            return ["ema", "supertrend", "ichimoku", "macd", "parabolic_sar"]
        elif "rang" in regime or "sideways" in regime:
            return ["bollinger", "rsi", "cci", "williams_r", "donchian"]
        elif "volat" in regime or "breakout" in regime:
            return ["atr", "keltner", "bollinger", "rsi", "donchian"]
        elif "compress" in regime or "squeeze" in regime:
            return ["bollinger", "keltner", "atr", "rsi", "macd"]
        else:
            return ["ema", "bollinger", "rsi", "atr", "ichimoku"]
    
    def get_available_presets(self) -> List[Dict[str, Any]]:
        """Get all available presets."""
        return [
            {
                "preset_id": p.preset_id,
                "name": p.name,
                "description": p.description,
                "type": p.preset_type.value,
            }
            for p in REGIME_PRESETS.values()
        ]


# Singleton
_chart_composer: Optional[ChartComposer] = None

def get_chart_composer() -> ChartComposer:
    global _chart_composer
    if _chart_composer is None:
        _chart_composer = ChartComposer()
    return _chart_composer
