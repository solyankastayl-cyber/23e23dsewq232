"""
Chart Object Builder — PHASE 49

Converts research findings into chart objects.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import uuid
import numpy as np

from .models import (
    ChartObject,
    ObjectType,
    ObjectCategory,
    ObjectStyle,
    GeometryPoint,
    get_default_color,
    get_category_for_type,
)


class ChartObjectBuilder:
    """Builds chart objects from research data."""
    
    def __init__(self):
        self._objects: List[ChartObject] = []
    
    def clear(self):
        """Clear all objects."""
        self._objects = []
    
    def get_objects(self) -> List[ChartObject]:
        """Get all built objects."""
        return self._objects
    
    # ═══════════════════════════════════════════════════════════════
    # From Research Analytics
    # ═══════════════════════════════════════════════════════════════
    
    def from_patterns(
        self,
        patterns: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> List[ChartObject]:
        """Convert detected patterns to chart objects."""
        objects = []
        
        for pattern in patterns:
            obj_type = self._pattern_type_to_object_type(
                pattern.get("pattern_type", "")
            )
            
            # Build points
            points = []
            for p in pattern.get("points", []):
                points.append(GeometryPoint(
                    timestamp=p.get("timestamp", ""),
                    price=p.get("price", 0),
                ))
            
            # Create object
            obj = ChartObject(
                id=pattern.get("pattern_id", str(uuid.uuid4())),
                type=obj_type,
                category=get_category_for_type(obj_type),
                symbol=symbol,
                timeframe=timeframe,
                points=points,
                style=ObjectStyle(
                    color=get_default_color(obj_type),
                    opacity=0.8,
                    fill_opacity=0.15,
                ),
                label=pattern.get("pattern_type", "").replace("_", " ").title(),
                confidence=pattern.get("confidence"),
                priority=7 if pattern.get("status") == "confirmed" else 5,
                metadata={
                    "direction": pattern.get("direction"),
                    "status": pattern.get("status"),
                    "upper_bound": pattern.get("upper_bound"),
                    "lower_bound": pattern.get("lower_bound"),
                },
            )
            
            objects.append(obj)
        
        self._objects.extend(objects)
        return objects
    
    def from_support_resistance(
        self,
        levels: List[Dict[str, Any]],
        symbol: str,
        timeframe: str,
        candles: List[Dict[str, Any]]
    ) -> List[ChartObject]:
        """Convert S/R levels to chart objects."""
        objects = []
        
        if not candles:
            return objects
        
        start_ts = candles[0].get("timestamp", "")
        end_ts = candles[-1].get("timestamp", "")
        
        for level in levels:
            level_type = level.get("type", "support")
            obj_type = (
                ObjectType.SUPPORT_CLUSTER 
                if level_type == "support" 
                else ObjectType.RESISTANCE_CLUSTER
            )
            
            price = level.get("price", 0)
            
            obj = ChartObject(
                id=level.get("level_id", str(uuid.uuid4())),
                type=obj_type,
                category=ObjectCategory.LIQUIDITY,
                symbol=symbol,
                timeframe=timeframe,
                points=[
                    GeometryPoint(timestamp=start_ts, price=price),
                    GeometryPoint(timestamp=end_ts, price=price),
                ],
                style=ObjectStyle(
                    color="#10B981" if level_type == "support" else "#F43F5E",
                    opacity=min(0.5 + level.get("strength", 0) * 0.5, 1.0),
                    line_width=2,
                    line_style="dashed",
                ),
                label=f"{level_type.title()} {price:.0f}",
                confidence=level.get("strength"),
                priority=int(5 + level.get("touches", 0)),
                metadata={
                    "touches": level.get("touches"),
                    "strength": level.get("strength"),
                },
            )
            
            objects.append(obj)
        
        self._objects.extend(objects)
        return objects
    
    def from_hypothesis(
        self,
        hypothesis: Dict[str, Any],
        symbol: str,
        timeframe: str
    ) -> List[ChartObject]:
        """Convert hypothesis visualization to chart objects."""
        objects = []
        
        # Entry zone
        entry_zone = hypothesis.get("entry_zone", (0, 0))
        if entry_zone[0] > 0 and entry_zone[1] > 0:
            current_ts = datetime.now(timezone.utc).isoformat()
            future_ts = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
            
            objects.append(ChartObject(
                id=f"{hypothesis.get('hypothesis_id', 'hyp')}_entry",
                type=ObjectType.ENTRY_ZONE,
                category=ObjectCategory.HYPOTHESIS,
                symbol=symbol,
                timeframe=timeframe,
                points=[
                    GeometryPoint(timestamp=current_ts, price=entry_zone[0]),
                    GeometryPoint(timestamp=future_ts, price=entry_zone[1]),
                ],
                style=ObjectStyle(
                    color="#22C55E",
                    fill_color="#22C55E",
                    fill_opacity=0.1,
                ),
                label="Entry Zone",
                metadata={"zone_low": entry_zone[0], "zone_high": entry_zone[1]},
            ))
        
        # Stop loss
        stop_loss = hypothesis.get("stop_loss")
        if stop_loss:
            objects.append(ChartObject(
                id=f"{hypothesis.get('hypothesis_id', 'hyp')}_sl",
                type=ObjectType.STOP_LOSS,
                category=ObjectCategory.HYPOTHESIS,
                symbol=symbol,
                timeframe=timeframe,
                points=[
                    GeometryPoint(timestamp=current_ts, price=stop_loss),
                ],
                style=ObjectStyle(
                    color="#EF4444",
                    line_style="dashed",
                ),
                label=f"SL {stop_loss:.0f}",
                priority=8,
            ))
        
        # Take profit levels
        take_profits = hypothesis.get("take_profit", [])
        for i, tp in enumerate(take_profits):
            objects.append(ChartObject(
                id=f"{hypothesis.get('hypothesis_id', 'hyp')}_tp{i+1}",
                type=ObjectType.TAKE_PROFIT,
                category=ObjectCategory.HYPOTHESIS,
                symbol=symbol,
                timeframe=timeframe,
                points=[
                    GeometryPoint(timestamp=current_ts, price=tp),
                ],
                style=ObjectStyle(
                    color="#10B981",
                    line_style="dotted",
                    opacity=0.8 - i * 0.2,
                ),
                label=f"TP{i+1} {tp:.0f}",
                priority=7 - i,
            ))
        
        # Scenarios as hypothesis paths
        for scenario in hypothesis.get("scenarios", []):
            path_points = []
            for p in scenario.get("expected_path", []):
                path_points.append(GeometryPoint(
                    timestamp=p.get("timestamp", ""),
                    price=p.get("price", 0),
                ))
            
            if path_points:
                color = scenario.get("color", "#A78BFA")
                probability = scenario.get("probability", 0)
                
                objects.append(ChartObject(
                    id=scenario.get("scenario_id", str(uuid.uuid4())),
                    type=ObjectType.HYPOTHESIS_PATH,
                    category=ObjectCategory.HYPOTHESIS,
                    symbol=symbol,
                    timeframe=timeframe,
                    points=path_points,
                    upper_band=scenario.get("upper_band", []),
                    lower_band=scenario.get("lower_band", []),
                    style=ObjectStyle(
                        color=color,
                        opacity=0.3 + probability * 0.5,
                        fill_opacity=0.1,
                    ),
                    label=f"{scenario.get('type', 'Scenario').title()} ({probability*100:.0f}%)",
                    confidence=probability,
                    priority=int(5 + probability * 5),
                    metadata={
                        "scenario_type": scenario.get("type"),
                        "target_price": scenario.get("target_price"),
                    },
                ))
        
        self._objects.extend(objects)
        return objects
    
    def from_fractals(
        self,
        fractal_matches: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> List[ChartObject]:
        """Convert fractal matches to chart objects."""
        objects = []
        
        for match in fractal_matches:
            # Reference pattern (historical)
            ref_points = []
            for p in match.get("reference_pattern", []):
                ref_points.append(GeometryPoint(
                    timestamp=p.get("timestamp", ""),
                    price=p.get("price", 0),
                ))
            
            if ref_points:
                objects.append(ChartObject(
                    id=f"{match.get('match_id', str(uuid.uuid4()))}_ref",
                    type=ObjectType.FRACTAL_REFERENCE,
                    category=ObjectCategory.FRACTAL,
                    symbol=symbol,
                    timeframe=timeframe,
                    points=ref_points,
                    style=ObjectStyle(
                        color="#A855F7",
                        opacity=0.5,
                        line_style="dashed",
                    ),
                    label=match.get("reference_context", "Reference"),
                    confidence=match.get("similarity"),
                    metadata={
                        "reference_symbol": match.get("reference_symbol"),
                        "reference_start": match.get("reference_start"),
                        "reference_end": match.get("reference_end"),
                    },
                ))
            
            # Projected path
            proj_points = []
            for p in match.get("projected_path", []):
                proj_points.append(GeometryPoint(
                    timestamp=p.get("timestamp", ""),
                    price=p.get("price", 0),
                ))
            
            if proj_points:
                objects.append(ChartObject(
                    id=f"{match.get('match_id', str(uuid.uuid4()))}_proj",
                    type=ObjectType.FRACTAL_PROJECTION,
                    category=ObjectCategory.FRACTAL,
                    symbol=symbol,
                    timeframe=timeframe,
                    points=proj_points,
                    upper_band=match.get("upper_projection", []),
                    lower_band=match.get("lower_projection", []),
                    style=ObjectStyle(
                        color="#D946EF",
                        opacity=0.7,
                        fill_opacity=0.1,
                    ),
                    label=f"Projection ({match.get('similarity', 0)*100:.0f}%)",
                    confidence=match.get("similarity"),
                    priority=int(6 + match.get("similarity", 0) * 4),
                    metadata={
                        "projected_target": match.get("projected_target"),
                    },
                ))
        
        self._objects.extend(objects)
        return objects
    
    def from_indicators(
        self,
        indicators: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> List[ChartObject]:
        """Convert indicator series to chart objects."""
        objects = []
        
        for ind in indicators:
            ind_name = ind.get("name", "indicator")
            ind_type = ind.get("type", "line")
            
            # Determine object type
            obj_type = self._indicator_name_to_object_type(ind_name)
            
            # Extract values
            values = []
            timestamps = []
            for v in ind.get("values", []):
                if isinstance(v, dict):
                    values.append(v.get("value", 0))
                    timestamps.append(v.get("timestamp", ""))
                else:
                    values.append(float(v))
            
            obj = ChartObject(
                id=ind.get("indicator_id", str(uuid.uuid4())),
                type=obj_type,
                category=ObjectCategory.INDICATOR,
                symbol=symbol,
                timeframe=timeframe,
                series=values,
                timestamps=timestamps,
                upper_band=ind.get("upper_band", []),
                lower_band=ind.get("lower_band", []),
                middle_band=ind.get("middle_band", []),
                style=ObjectStyle(
                    color=ind.get("color", get_default_color(obj_type)),
                    line_width=2,
                ),
                label=ind.get("name", "Indicator"),
                priority=4,
                metadata=ind.get("params", {}),
            )
            
            objects.append(obj)
        
        self._objects.extend(objects)
        return objects
    
    def from_liquidity_zones(
        self,
        zones: List[Dict[str, Any]],
        symbol: str,
        timeframe: str,
        candles: List[Dict[str, Any]]
    ) -> List[ChartObject]:
        """Convert liquidity zones to chart objects."""
        objects = []
        
        if not candles:
            return objects
        
        start_ts = candles[0].get("timestamp", "")
        end_ts = candles[-1].get("timestamp", "")
        
        for zone in zones:
            zone_type = zone.get("type", "bid")
            
            obj = ChartObject(
                id=zone.get("zone_id", str(uuid.uuid4())),
                type=ObjectType.LIQUIDITY_ZONE,
                category=ObjectCategory.LIQUIDITY,
                symbol=symbol,
                timeframe=timeframe,
                points=[
                    GeometryPoint(timestamp=start_ts, price=zone.get("price_low", 0)),
                    GeometryPoint(timestamp=end_ts, price=zone.get("price_high", 0)),
                ],
                style=ObjectStyle(
                    color="#3B82F6" if zone_type == "bid" else "#EF4444",
                    fill_color="#3B82F6" if zone_type == "bid" else "#EF4444",
                    fill_opacity=0.15,
                    opacity=0.6,
                ),
                label=f"Liquidity ({zone_type.upper()})",
                confidence=zone.get("significance"),
                metadata={
                    "volume": zone.get("volume"),
                    "zone_type": zone_type,
                },
            )
            
            objects.append(obj)
        
        self._objects.extend(objects)
        return objects
    
    # ═══════════════════════════════════════════════════════════════
    # Custom Object Creation
    # ═══════════════════════════════════════════════════════════════
    
    def create_trend_line(
        self,
        symbol: str,
        timeframe: str,
        point1: tuple,  # (timestamp, price)
        point2: tuple,
        label: Optional[str] = None,
        color: str = "#F59E0B",
        extend_right: bool = True
    ) -> ChartObject:
        """Create a trend line object."""
        obj = ChartObject(
            id=str(uuid.uuid4()),
            type=ObjectType.TREND_LINE,
            category=ObjectCategory.GEOMETRY,
            symbol=symbol,
            timeframe=timeframe,
            points=[
                GeometryPoint(timestamp=point1[0], price=point1[1]),
                GeometryPoint(timestamp=point2[0], price=point2[1]),
            ],
            style=ObjectStyle(color=color),
            label=label,
            metadata={"extend_right": extend_right},
        )
        
        self._objects.append(obj)
        return obj
    
    def create_zone(
        self,
        symbol: str,
        timeframe: str,
        price_low: float,
        price_high: float,
        start_ts: str,
        end_ts: str,
        zone_type: str = "support",
        label: Optional[str] = None
    ) -> ChartObject:
        """Create a zone object."""
        color = "#10B981" if zone_type == "support" else "#F43F5E"
        
        obj = ChartObject(
            id=str(uuid.uuid4()),
            type=ObjectType.ZONE,
            category=ObjectCategory.GEOMETRY,
            symbol=symbol,
            timeframe=timeframe,
            points=[
                GeometryPoint(timestamp=start_ts, price=price_low),
                GeometryPoint(timestamp=end_ts, price=price_high),
            ],
            style=ObjectStyle(
                color=color,
                fill_color=color,
                fill_opacity=0.15,
            ),
            label=label or f"{zone_type.title()} Zone",
            metadata={"zone_type": zone_type, "price_low": price_low, "price_high": price_high},
        )
        
        self._objects.append(obj)
        return obj
    
    # ═══════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════
    
    def _pattern_type_to_object_type(self, pattern_type: str) -> ObjectType:
        """Map pattern type to object type."""
        mapping = {
            "triangle_symmetric": ObjectType.TRIANGLE,
            "triangle_ascending": ObjectType.TRIANGLE,
            "triangle_descending": ObjectType.TRIANGLE,
            "channel_ascending": ObjectType.CHANNEL,
            "channel_descending": ObjectType.CHANNEL,
            "channel_horizontal": ObjectType.CHANNEL,
            "compression": ObjectType.COMPRESSION_PATTERN,
            "breakout_bullish": ObjectType.BREAKOUT_PATTERN,
            "breakout_bearish": ObjectType.BREAKOUT_PATTERN,
            "wedge": ObjectType.WEDGE,
            "wedge_rising": ObjectType.WEDGE_RISING,
            "wedge_falling": ObjectType.WEDGE_FALLING,
            "head_shoulders": ObjectType.HEAD_SHOULDERS,
            "head_shoulders_inverse": ObjectType.HEAD_SHOULDERS,
            "double_top": ObjectType.DOUBLE_TOP,
            "double_bottom": ObjectType.DOUBLE_BOTTOM,
            "cup_handle": ObjectType.CUP_HANDLE,
            "harmonic_gartley": ObjectType.HARMONIC_GARTLEY,
            "harmonic_bat": ObjectType.HARMONIC_BAT,
        }
        return mapping.get(pattern_type, ObjectType.BREAKOUT_PATTERN)
    
    def _indicator_name_to_object_type(self, name: str) -> ObjectType:
        """Map indicator name to object type."""
        name_lower = name.lower()
        
        if "ema" in name_lower:
            return ObjectType.EMA_SERIES
        elif "sma" in name_lower:
            return ObjectType.SMA_SERIES
        elif "vwap" in name_lower:
            return ObjectType.VWAP_SERIES
        elif "bollinger" in name_lower:
            return ObjectType.BOLLINGER_BAND
        elif "atr" in name_lower:
            return ObjectType.ATR_BAND
        elif "rsi" in name_lower:
            return ObjectType.RSI_SERIES
        elif "macd" in name_lower:
            return ObjectType.MACD_SERIES
        elif "volume" in name_lower:
            return ObjectType.VOLUME_PROFILE
        elif "cci" in name_lower:
            return ObjectType.CCI_SERIES
        elif "williams" in name_lower:
            return ObjectType.WILLIAMS_R_SERIES
        elif "ichimoku" in name_lower:
            return ObjectType.ICHIMOKU_CLOUD
        elif "parabolic" in name_lower or "psar" in name_lower:
            return ObjectType.PSAR_SERIES
        elif "donchian" in name_lower:
            return ObjectType.DONCHIAN_CHANNEL
        elif "keltner" in name_lower:
            return ObjectType.KELTNER_CHANNEL
        else:
            return ObjectType.CUSTOM_INDICATOR


# Singleton
_object_builder: Optional[ChartObjectBuilder] = None

def get_object_builder() -> ChartObjectBuilder:
    global _object_builder
    if _object_builder is None:
        _object_builder = ChartObjectBuilder()
    return _object_builder
