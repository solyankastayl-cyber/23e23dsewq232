"""
TA Composition Engine — Core Logic
====================================

This is NOT a structure debug view.
This is a TECHNICAL SETUP VIEW.

The chart should answer:
"What is the current technical setup?"

NOT:
"Here's the swing history"

Components:
1. ActiveFigure — Primary TA figure on current price action (triangle, wedge, channel, etc)
2. ActiveFib — One relevant fibonacci context
3. RelevantOverlays — 2-3 overlays that support the setup (EMA, BB, etc)
4. BreakoutLogic — Breakout level, invalidation, confirmation zone
5. TAComposition — The complete visual composition for chart

Pipeline:
    patterns + fib + S/R + indicators + liquidity + POI + structure
    → select_primary_figure
    → select_active_fib
    → select_relevant_overlays
    → build_breakout_logic
    → TAComposition
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone


@dataclass
class ActiveFigure:
    """
    Primary TA figure attached to current price action.
    
    Must be:
    - One of: triangle, wedge, channel, flag, double_top, double_bottom, head_shoulders, range
    - Currently active (not historical)
    - Visually attached to price (points on candles)
    """
    figure_type: str  # triangle_ascending, wedge_falling, channel_up, etc
    direction: str  # bullish, bearish, neutral
    confidence: float  # 0.0-1.0
    
    # Visual attachment points (time, price)
    points: Dict[str, List[Dict]]  # upper, lower, neckline, etc
    
    # Where the figure starts/ends on chart
    start_time: int
    end_time: int
    
    # Key levels
    breakout_level: float
    invalidation_level: float
    
    # Why this figure is important
    reason: str
    
    def to_dict(self) -> Dict:
        return {
            "type": self.figure_type,
            "direction": self.direction,
            "confidence": round(self.confidence, 3),
            "points": self.points,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "breakout_level": round(self.breakout_level, 2),
            "invalidation_level": round(self.invalidation_level, 2),
            "reason": self.reason,
        }


@dataclass
class ActiveFib:
    """
    One active fibonacci context.
    
    Not all fibs visible — only THE ONE that matters now.
    """
    swing_type: str  # bullish_retracement, bearish_retracement, extension
    swing_high: float
    swing_low: float
    
    # Key levels (only show 2-3 most relevant)
    key_levels: List[Dict]  # [{level: 0.618, price: 95000, status: "holding"}, ...]
    
    # Current price position
    current_position: str  # above_618, between_382_618, below_786, etc
    
    # Start/end times for chart drawing
    start_time: int
    end_time: int
    
    # Why this fib matters
    reason: str
    
    def to_dict(self) -> Dict:
        return {
            "swing_type": self.swing_type,
            "swing_high": round(self.swing_high, 2),
            "swing_low": round(self.swing_low, 2),
            "key_levels": self.key_levels,
            "current_position": self.current_position,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "reason": self.reason,
        }


@dataclass
class RelevantOverlay:
    """
    One overlay that supports the current setup.
    
    Not all overlays — only 2-3 that are TOP DRIVERS for the decision.
    """
    indicator_id: str  # ema_20, ema_50, bollinger_bands, vwap
    display_name: str  # EMA 20, BB, VWAP
    
    # Current value/state
    current_value: float
    
    # Why it's relevant (connection to setup)
    relevance: str  # "price_rejection", "dynamic_support", "squeeze_forming", etc
    
    # Visual data for chart
    series: List[Dict]  # [{time, value}, ...] — for drawing
    
    # Optional: additional lines (for BB upper/lower, etc)
    additional_series: Dict[str, List[Dict]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "indicator_id": self.indicator_id,
            "display_name": self.display_name,
            "current_value": round(self.current_value, 2) if self.current_value else None,
            "relevance": self.relevance,
            "series": self.series[-50:] if self.series else [],  # Last 50 points
            "additional_series": {k: v[-50:] for k, v in self.additional_series.items()},
        }


@dataclass
class BreakoutLogic:
    """
    Clear breakout/invalidation logic for the setup.
    
    Not just a level — but a LOGIC:
    - What confirms the setup?
    - What invalidates it?
    - Where is the confirmation zone?
    """
    direction: str  # long, short, neutral
    
    # Confirmation
    breakout_level: float
    breakout_type: str  # resistance_break, support_break, pattern_break, fib_reclaim
    confirmation_zone: Dict[str, float]  # {upper, lower}
    
    # Invalidation
    invalidation_level: float
    invalidation_type: str  # below_support, above_resistance, pattern_fail
    
    # Risk/Reward context
    risk_pct: float  # % to invalidation
    
    def to_dict(self) -> Dict:
        return {
            "direction": self.direction,
            "breakout_level": round(self.breakout_level, 2),
            "breakout_type": self.breakout_type,
            "confirmation_zone": {k: round(v, 2) for k, v in self.confirmation_zone.items()},
            "invalidation_level": round(self.invalidation_level, 2),
            "invalidation_type": self.invalidation_type,
            "risk_pct": round(self.risk_pct, 2),
        }


@dataclass
class TAComposition:
    """
    Complete TA Composition for chart rendering.
    
    This is what goes on the chart — NOT structure markup,
    but a TECHNICAL SETUP VIEW.
    """
    # Status
    has_active_setup: bool
    setup_quality: str  # high, medium, low, none
    
    # Core components
    active_figure: Optional[ActiveFigure]
    active_fib: Optional[ActiveFib]
    relevant_overlays: List[RelevantOverlay]
    breakout_logic: Optional[BreakoutLogic]
    
    # Active POI/Zone (if relevant to setup)
    active_zone: Optional[Dict]  # {type, upper, lower, strength}
    
    # One-line summary
    setup_summary: str
    
    # What structure says (for context, not for display)
    structure_context: str  # bullish_continuation, bearish_reversal, range_play, etc
    
    # Metadata
    timestamp: str
    
    def to_dict(self) -> Dict:
        return {
            "has_active_setup": self.has_active_setup,
            "setup_quality": self.setup_quality,
            "active_figure": self.active_figure.to_dict() if self.active_figure else None,
            "active_fib": self.active_fib.to_dict() if self.active_fib else None,
            "relevant_overlays": [o.to_dict() for o in self.relevant_overlays],
            "breakout_logic": self.breakout_logic.to_dict() if self.breakout_logic else None,
            "active_zone": self.active_zone,
            "setup_summary": self.setup_summary,
            "structure_context": self.structure_context,
            "timestamp": self.timestamp,
        }


class TACompositionEngine:
    """
    TA Composition Engine — The Brain-to-Chart Translator
    
    Takes all TA components and builds ONE coherent visual setup.
    """
    
    # Figure type priority (most TA-significant first)
    FIGURE_PRIORITY = [
        "head_shoulders", "inverse_head_shoulders",
        "double_top", "double_bottom",
        "ascending_triangle", "descending_triangle", "symmetrical_triangle",
        "rising_wedge", "falling_wedge",
        "ascending_channel", "descending_channel",
        "bull_flag", "bear_flag",
        "range",
    ]
    
    # Overlay priority for different setups
    OVERLAY_PRIORITY = {
        "trend": ["ema_20", "ema_50", "ema_200", "vwap"],
        "reversal": ["bollinger_bands", "ema_20", "vwap"],
        "range": ["bollinger_bands", "vwap", "ema_50"],
        "breakout": ["ema_20", "vwap", "ema_50"],
    }
    
    def build(
        self,
        candles: List[Dict],
        primary_pattern: Optional[Dict],
        alternative_patterns: List[Dict],
        fibonacci: Dict,
        indicators_data: Dict,
        ta_context: Dict,
        structure_context: Dict,
        liquidity: Dict,
        poi: Dict,
        decision: Dict,
        current_price: float,
    ) -> TAComposition:
        """
        Build complete TA composition.
        
        Pipeline:
        1. Determine setup type from structure + decision
        2. Select primary figure (or None if no valid figure)
        3. Select active fib context
        4. Select 2-3 relevant overlays
        5. Build breakout logic
        6. Compose final view
        """
        # 1. Determine setup type
        setup_type = self._determine_setup_type(structure_context, decision)
        
        # 2. Select primary figure
        active_figure = self._select_primary_figure(
            primary_pattern,
            alternative_patterns,
            candles,
            setup_type,
            current_price,
        )
        
        # 3. Select active fib
        active_fib = self._select_active_fib(
            fibonacci,
            candles,
            current_price,
            setup_type,
        )
        
        # 4. Select relevant overlays (max 3)
        relevant_overlays = self._select_relevant_overlays(
            indicators_data,
            ta_context,
            setup_type,
            current_price,
        )
        
        # 5. Build breakout logic
        breakout_logic = self._build_breakout_logic(
            active_figure,
            active_fib,
            structure_context,
            current_price,
            setup_type,
        )
        
        # 6. Select active zone (POI/liquidity if relevant)
        active_zone = self._select_active_zone(
            poi,
            liquidity,
            current_price,
        )
        
        # 7. Determine quality
        setup_quality = self._assess_setup_quality(
            active_figure,
            active_fib,
            breakout_logic,
            ta_context,
        )
        
        # 8. Build summary
        setup_summary = self._build_summary(
            active_figure,
            active_fib,
            breakout_logic,
            setup_type,
            current_price,
        )
        
        # 9. Structure context label
        structure_label = self._get_structure_label(structure_context, decision)
        
        has_setup = active_figure is not None or active_fib is not None
        
        return TAComposition(
            has_active_setup=has_setup,
            setup_quality=setup_quality,
            active_figure=active_figure,
            active_fib=active_fib,
            relevant_overlays=relevant_overlays,
            breakout_logic=breakout_logic,
            active_zone=active_zone,
            setup_summary=setup_summary,
            structure_context=structure_label,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    
    def _determine_setup_type(self, structure_context: Dict, decision: Dict) -> str:
        """Determine setup type: trend, reversal, range, or breakout."""
        regime = structure_context.get("regime", "unknown")
        decision_direction = decision.get("direction", "neutral")
        
        if regime == "trending":
            return "trend"
        elif regime == "reversal" or "choch" in str(structure_context).lower():
            return "reversal"
        elif regime in ["range", "accumulation", "distribution"]:
            return "range"
        elif "breakout" in str(decision).lower() or decision_direction != "neutral":
            return "breakout"
        else:
            return "trend"  # default
    
    def _select_primary_figure(
        self,
        primary_pattern: Optional[Dict],
        alternative_patterns: List[Dict],
        candles: List[Dict],
        setup_type: str,
        current_price: float,
    ) -> Optional[ActiveFigure]:
        """
        Select ONE primary figure for the chart.
        
        Criteria:
        - Must be currently active (not historical)
        - Must have visual points attachable to candles
        - Must have clear breakout/invalidation
        """
        if not primary_pattern:
            # Try alternatives
            for alt in alternative_patterns[:3]:
                if alt and self._is_figure_active(alt, candles, current_price):
                    primary_pattern = alt
                    break
        
        if not primary_pattern:
            return None
        
        if not self._is_figure_active(primary_pattern, candles, current_price):
            return None
        
        # Extract figure type
        raw_type = primary_pattern.get("type", "unknown")
        figure_type = self._normalize_figure_type(raw_type)
        
        # Get direction
        direction = primary_pattern.get("direction", "neutral")
        
        # Get points
        points = primary_pattern.get("points", {})
        if not points:
            # Try to extract from anchor_points
            points = primary_pattern.get("anchor_points", {})
        
        # Get times
        start_time = candles[-100]["time"] if len(candles) > 100 else candles[0]["time"]
        end_time = candles[-1]["time"]
        
        # If points have time info, use them
        for line_points in points.values():
            if isinstance(line_points, list) and line_points:
                first_pt = line_points[0]
                if isinstance(first_pt, dict) and "time" in first_pt:
                    start_time = min(start_time, first_pt["time"])
                last_pt = line_points[-1] if len(line_points) > 1 else first_pt
                if isinstance(last_pt, dict) and "time" in last_pt:
                    end_time = max(end_time, last_pt["time"])
        
        # Get levels
        breakout_level = primary_pattern.get("breakout_level", current_price * 1.02)
        invalidation_level = primary_pattern.get("invalidation", current_price * 0.98)
        
        # Confidence
        confidence = primary_pattern.get("confidence", 0.5)
        
        # Reason
        reason = f"{figure_type.replace('_', ' ').title()} forming — {direction} bias"
        
        return ActiveFigure(
            figure_type=figure_type,
            direction=direction,
            confidence=confidence,
            points=points,
            start_time=start_time,
            end_time=end_time,
            breakout_level=breakout_level,
            invalidation_level=invalidation_level,
            reason=reason,
        )
    
    def _is_figure_active(self, pattern: Dict, candles: List[Dict], current_price: float) -> bool:
        """Check if figure is currently active (not historical)."""
        if not pattern:
            return False
        
        confidence = pattern.get("confidence", 0)
        if confidence < 0.5:
            return False
        
        # Check if pattern is recent
        end_index = pattern.get("end_index", 0)
        if end_index < len(candles) * 0.8:
            return False
        
        # Check if price is within pattern bounds
        breakout = pattern.get("breakout_level", 0)
        invalidation = pattern.get("invalidation", 0)
        
        if breakout and invalidation:
            upper = max(breakout, invalidation)
            lower = min(breakout, invalidation)
            buffer = (upper - lower) * 0.1
            
            if current_price < lower - buffer or current_price > upper + buffer:
                return False
        
        return True
    
    def _normalize_figure_type(self, raw_type: str) -> str:
        """Normalize pattern type to standard figure name."""
        type_map = {
            "triangle": "symmetrical_triangle",
            "ascending_triangle": "ascending_triangle",
            "descending_triangle": "descending_triangle",
            "symmetrical_triangle": "symmetrical_triangle",
            "rising_wedge": "rising_wedge",
            "falling_wedge": "falling_wedge",
            "wedge": "wedge",
            "channel": "channel",
            "ascending_channel": "ascending_channel",
            "descending_channel": "descending_channel",
            "flag": "flag",
            "bull_flag": "bull_flag",
            "bear_flag": "bear_flag",
            "double_top": "double_top",
            "double_bottom": "double_bottom",
            "head_and_shoulders": "head_shoulders",
            "head_shoulders": "head_shoulders",
            "inverse_head_shoulders": "inverse_head_shoulders",
            "range": "range",
            "compression": "compression",
            "breakout_up": "breakout_up",
            "breakdown": "breakdown",
        }
        
        raw_lower = raw_type.lower().replace(" ", "_").replace("-", "_")
        return type_map.get(raw_lower, raw_type)
    
    def _select_active_fib(
        self,
        fibonacci: Dict,
        candles: List[Dict],
        current_price: float,
        setup_type: str,
    ) -> Optional[ActiveFib]:
        """Select ONE active fibonacci context."""
        if not fibonacci:
            return None
        
        # Get primary swing
        primary_swing = fibonacci.get("primary_swing", {})
        if not primary_swing:
            # Try retracement
            retracement = fibonacci.get("retracement", {})
            if retracement:
                primary_swing = {
                    "high": retracement.get("swing_high", 0),
                    "low": retracement.get("swing_low", 0),
                    "levels": retracement.get("levels", []),
                }
        
        swing_high = primary_swing.get("high", 0)
        swing_low = primary_swing.get("low", 0)
        
        if not swing_high or not swing_low:
            return None
        
        # Determine swing type
        if current_price > (swing_high + swing_low) / 2:
            swing_type = "bullish_retracement"
        else:
            swing_type = "bearish_retracement"
        
        # Get key levels (filter to 2-3 most relevant)
        all_levels = primary_swing.get("levels", []) or fibonacci.get("levels", [])
        key_fib_ratios = [0.382, 0.5, 0.618, 0.786]
        
        key_levels = []
        for level in all_levels:
            ratio = level.get("level", level.get("ratio", 0))
            price = level.get("price", 0)
            
            if ratio in key_fib_ratios or abs(ratio - 0.618) < 0.01:
                # Determine status
                if abs(current_price - price) / price < 0.01:
                    status = "testing"
                elif current_price > price:
                    status = "above"
                else:
                    status = "below"
                
                key_levels.append({
                    "level": ratio,
                    "price": round(price, 2),
                    "status": status,
                })
        
        # Keep only top 3
        key_levels = key_levels[:3]
        
        if not key_levels:
            return None
        
        # Determine current position
        fib_618 = swing_low + (swing_high - swing_low) * 0.618
        fib_382 = swing_low + (swing_high - swing_low) * 0.382
        
        if current_price > fib_618:
            current_position = "above_618"
        elif current_price > fib_382:
            current_position = "between_382_618"
        else:
            current_position = "below_382"
        
        # Get times
        start_time = candles[-100]["time"] if len(candles) > 100 else candles[0]["time"]
        end_time = candles[-1]["time"]
        
        reason = f"Price at {current_position.replace('_', ' ')}"
        
        return ActiveFib(
            swing_type=swing_type,
            swing_high=swing_high,
            swing_low=swing_low,
            key_levels=key_levels,
            current_position=current_position,
            start_time=start_time,
            end_time=end_time,
            reason=reason,
        )
    
    def _select_relevant_overlays(
        self,
        indicators_data: Dict,
        ta_context: Dict,
        setup_type: str,
        current_price: float,
    ) -> List[RelevantOverlay]:
        """Select 2-3 most relevant overlays for the setup."""
        overlays = []
        
        # Get priority list for this setup type
        priority = self.OVERLAY_PRIORITY.get(setup_type, self.OVERLAY_PRIORITY["trend"])
        
        # Get top drivers from ta_context
        top_drivers = ta_context.get("top_drivers", [])
        driver_ids = [d.get("source_id", "") for d in top_drivers]
        
        # Prioritize indicators that are top drivers
        for driver_id in driver_ids[:3]:
            if driver_id in indicators_data:
                ind_data = indicators_data[driver_id]
                overlay = self._build_overlay(driver_id, ind_data, current_price)
                if overlay:
                    overlays.append(overlay)
        
        # Fill remaining slots from priority list
        for ind_id in priority:
            if len(overlays) >= 3:
                break
            if ind_id in indicators_data and not any(o.indicator_id == ind_id for o in overlays):
                ind_data = indicators_data[ind_id]
                overlay = self._build_overlay(ind_id, ind_data, current_price)
                if overlay:
                    overlays.append(overlay)
        
        return overlays[:3]
    
    def _build_overlay(self, ind_id: str, ind_data: Dict, current_price: float) -> Optional[RelevantOverlay]:
        """Build RelevantOverlay from indicator data."""
        display_names = {
            "ema_20": "EMA 20",
            "ema_50": "EMA 50",
            "ema_200": "EMA 200",
            "bollinger_bands": "Bollinger Bands",
            "vwap": "VWAP",
        }
        
        display_name = display_names.get(ind_id, ind_id.upper())
        
        # Get series data
        series = ind_data.get("series", [])
        if not series and "values" in ind_data:
            series = ind_data["values"]
        
        # Get current value
        current_value = ind_data.get("current_value")
        if not current_value and series:
            last = series[-1] if series else {}
            current_value = last.get("value", last.get("close", 0))
        
        # Determine relevance
        if current_value:
            if abs(current_price - current_value) / current_price < 0.01:
                relevance = "price_testing"
            elif current_price > current_value:
                relevance = "price_above"
            else:
                relevance = "price_below"
        else:
            relevance = "reference"
        
        # Additional series (for BB)
        additional_series = {}
        if ind_id == "bollinger_bands":
            if "upper" in ind_data:
                additional_series["upper"] = ind_data["upper"]
            if "lower" in ind_data:
                additional_series["lower"] = ind_data["lower"]
        
        return RelevantOverlay(
            indicator_id=ind_id,
            display_name=display_name,
            current_value=current_value or 0,
            relevance=relevance,
            series=series,
            additional_series=additional_series,
        )
    
    def _build_breakout_logic(
        self,
        active_figure: Optional[ActiveFigure],
        active_fib: Optional[ActiveFib],
        structure_context: Dict,
        current_price: float,
        setup_type: str,
    ) -> Optional[BreakoutLogic]:
        """Build clear breakout/invalidation logic."""
        # Start from figure if available
        if active_figure:
            breakout = active_figure.breakout_level
            invalidation = active_figure.invalidation_level
            direction = active_figure.direction
        elif active_fib:
            # Use fib levels
            fib_618 = active_fib.swing_low + (active_fib.swing_high - active_fib.swing_low) * 0.618
            if current_price > fib_618:
                breakout = active_fib.swing_high
                invalidation = fib_618
                direction = "bullish"
            else:
                breakout = fib_618
                invalidation = active_fib.swing_low
                direction = "bearish"
        else:
            # Use structure levels
            supports = structure_context.get("active_supports", [])
            resistances = structure_context.get("active_resistances", [])
            
            if resistances:
                breakout = resistances[0].get("price", current_price * 1.02)
            else:
                breakout = current_price * 1.02
            
            if supports:
                invalidation = supports[0].get("price", current_price * 0.98)
            else:
                invalidation = current_price * 0.98
            
            bias = structure_context.get("bias", "neutral")
            direction = "bullish" if bias == "bullish" else "bearish" if bias == "bearish" else "neutral"
        
        # Determine types
        if direction == "bullish":
            breakout_type = "resistance_break"
            invalidation_type = "below_support"
        elif direction == "bearish":
            breakout_type = "support_break"
            invalidation_type = "above_resistance"
        else:
            breakout_type = "range_break"
            invalidation_type = "range_fail"
        
        # Confirmation zone (small buffer around breakout)
        buffer = abs(breakout - current_price) * 0.1
        confirmation_zone = {
            "upper": breakout + buffer,
            "lower": breakout - buffer,
        }
        
        # Risk %
        risk_pct = abs(current_price - invalidation) / current_price * 100 if current_price else 0
        
        return BreakoutLogic(
            direction=direction,
            breakout_level=breakout,
            breakout_type=breakout_type,
            confirmation_zone=confirmation_zone,
            invalidation_level=invalidation,
            invalidation_type=invalidation_type,
            risk_pct=risk_pct,
        )
    
    def _select_active_zone(
        self,
        poi: Dict,
        liquidity: Dict,
        current_price: float,
    ) -> Optional[Dict]:
        """Select active POI/liquidity zone if price is near one."""
        # Check POI zones
        zones = poi.get("zones", [])
        for zone in zones:
            upper = zone.get("upper", zone.get("price_high", 0))
            lower = zone.get("lower", zone.get("price_low", 0))
            
            if lower <= current_price <= upper:
                return {
                    "type": zone.get("type", "poi"),
                    "upper": round(upper, 2),
                    "lower": round(lower, 2),
                    "strength": zone.get("strength", 0.5),
                }
            
            # Check if price is near (within 2%)
            mid = (upper + lower) / 2
            if abs(current_price - mid) / current_price < 0.02:
                return {
                    "type": zone.get("type", "poi"),
                    "upper": round(upper, 2),
                    "lower": round(lower, 2),
                    "strength": zone.get("strength", 0.5),
                }
        
        # Check liquidity pools
        pools = liquidity.get("pools", [])
        for pool in pools[:3]:
            price = pool.get("price", 0)
            if abs(current_price - price) / current_price < 0.02:
                return {
                    "type": "liquidity_" + pool.get("type", "pool"),
                    "upper": round(price * 1.005, 2),
                    "lower": round(price * 0.995, 2),
                    "strength": pool.get("strength", 0.5),
                }
        
        return None
    
    def _assess_setup_quality(
        self,
        active_figure: Optional[ActiveFigure],
        active_fib: Optional[ActiveFib],
        breakout_logic: Optional[BreakoutLogic],
        ta_context: Dict,
    ) -> str:
        """Assess overall setup quality."""
        score = 0
        
        # Figure adds 30 points
        if active_figure:
            score += 30 * active_figure.confidence
        
        # Fib adds 20 points
        if active_fib:
            score += 20
        
        # Breakout logic adds 20 points
        if breakout_logic:
            score += 20
        
        # Top drivers consensus adds 30 points
        top_drivers = ta_context.get("top_drivers", [])
        if len(top_drivers) >= 3:
            directions = [d.get("contribution", 0) for d in top_drivers[:5]]
            pos = sum(1 for d in directions if d > 0)
            neg = sum(1 for d in directions if d < 0)
            if pos >= 4 or neg >= 4:
                score += 30
            elif pos >= 3 or neg >= 3:
                score += 20
        
        if score >= 70:
            return "high"
        elif score >= 40:
            return "medium"
        elif score >= 20:
            return "low"
        else:
            return "none"
    
    def _build_summary(
        self,
        active_figure: Optional[ActiveFigure],
        active_fib: Optional[ActiveFib],
        breakout_logic: Optional[BreakoutLogic],
        setup_type: str,
        current_price: float,
    ) -> str:
        """Build one-line setup summary."""
        parts = []
        
        if active_figure:
            fig_name = active_figure.figure_type.replace("_", " ").title()
            parts.append(fig_name)
        
        if active_fib:
            parts.append(f"Fib {active_fib.current_position.replace('_', ' ')}")
        
        if breakout_logic:
            if breakout_logic.direction == "bullish":
                parts.append(f"Break above {breakout_logic.breakout_level:.0f}")
            elif breakout_logic.direction == "bearish":
                parts.append(f"Break below {breakout_logic.breakout_level:.0f}")
        
        if not parts:
            return "No clear technical setup"
        
        return " | ".join(parts)
    
    def _get_structure_label(self, structure_context: Dict, decision: Dict) -> str:
        """Get structure context label."""
        regime = structure_context.get("regime", "unknown")
        bias = structure_context.get("bias", "neutral")
        
        if regime == "trending":
            return f"{bias}_continuation"
        elif regime == "reversal":
            return f"{bias}_reversal"
        elif regime == "range":
            return "range_play"
        else:
            return f"{bias}_{regime}"


# Singleton
_composition_engine: Optional[TACompositionEngine] = None


def get_composition_engine() -> TACompositionEngine:
    """Get singleton composition engine."""
    global _composition_engine
    if _composition_engine is None:
        _composition_engine = TACompositionEngine()
    return _composition_engine
