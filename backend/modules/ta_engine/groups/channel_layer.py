"""
TA Engine - Channel Layer (Group 3)
Detects price channels: ascending, descending, horizontal.

IMPORTANT: Channels are CONTEXT, not the main figure.
They become main only when Figure Layer has no findings.
"""

from typing import List, Dict, Optional
from ..groups.base import (
    BaseLayer, GroupResult, Finding, Window, Geometry, Relevance, RenderData,
    GROUP_CHANNELS, BIAS_BULLISH, BIAS_BEARISH, BIAS_NEUTRAL
)
from ..core.chart_basis import ChartBasis, Pivot
import math


class ChannelLayer(BaseLayer):
    """
    Detects channel patterns.
    
    STRICT RULES:
    - min_touches_per_side = 2
    - parallel_tolerance = 0.1 (10%)
    - Channel is FALLBACK, not primary
    """
    
    GROUP_NAME = GROUP_CHANNELS
    
    PATTERN_BIAS = {
        "ascending_channel": BIAS_BULLISH,
        "descending_channel": BIAS_BEARISH,
        "horizontal_channel": BIAS_NEUTRAL,
    }
    
    def __init__(self):
        self.min_touches_per_side = 2
        self.parallel_tolerance = 0.15  # 15% slope difference allowed
    
    def run(self, basis: ChartBasis) -> GroupResult:
        """Run channel detection"""
        findings = []
        
        if len(basis.candles) < 15 or len(basis.pivots) < 4:
            return self._create_result(findings, {"reason": "insufficient_data"})
        
        findings.extend(self._detect_channels(basis))
        
        # Sort by score
        findings.sort(key=lambda f: f.score, reverse=True)
        
        return self._create_result(findings, {
            "total_candidates": len(findings),
            "is_fallback_layer": True,  # Mark as fallback
        })
    
    def _detect_channels(self, basis: ChartBasis) -> List[Finding]:
        """Detect all channel types"""
        findings = []
        
        highs = [p for p in basis.pivots if p.type == "high"]
        lows = [p for p in basis.pivots if p.type == "low"]
        
        if len(highs) < self.min_touches_per_side or len(lows) < self.min_touches_per_side:
            return findings
        
        recent_highs = highs[-4:] if len(highs) >= 4 else highs
        recent_lows = lows[-4:] if len(lows) >= 4 else lows
        
        upper_slope = self._calc_slope(recent_highs)
        lower_slope = self._calc_slope(recent_lows)
        
        if upper_slope is None or lower_slope is None:
            return findings
        
        # Check if slopes are parallel (within tolerance)
        if upper_slope != 0:
            slope_diff = abs(upper_slope - lower_slope) / abs(upper_slope)
        else:
            slope_diff = abs(lower_slope)
        
        is_parallel = slope_diff < self.parallel_tolerance
        
        if not is_parallel:
            return findings  # Not a channel if not parallel
        
        # Determine channel type
        avg_slope = (upper_slope + lower_slope) / 2
        
        if avg_slope > 0.0002:
            channel_type = "ascending_channel"
        elif avg_slope < -0.0002:
            channel_type = "descending_channel"
        else:
            channel_type = "horizontal_channel"
        
        finding = self._build_channel_finding(
            channel_type, basis, recent_highs, recent_lows, slope_diff
        )
        
        if finding:
            findings.append(finding)
        
        return findings
    
    def _build_channel_finding(
        self,
        channel_type: str,
        basis: ChartBasis,
        highs: List[Pivot],
        lows: List[Pivot],
        parallel_score: float
    ) -> Optional[Finding]:
        """Build a channel finding"""
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        all_pivots = sorted(highs + lows, key=lambda p: p.index)
        
        # Window: first to last anchor
        window = Window(
            start=all_pivots[0].time,
            end=all_pivots[-1].time,
        )
        
        upper_line = self._fit_line(highs)
        lower_line = self._fit_line(lows)
        
        if not upper_line or not lower_line:
            return None
        
        # Geometry
        upper_touches = len(highs)
        lower_touches = len(lows)
        touch_balance = min(upper_touches, lower_touches) / max(upper_touches, lower_touches)
        
        geometry = Geometry(
            valid=True,
            clean=True,
            touches=upper_touches + lower_touches,
            symmetry=touch_balance,
            parallel=1.0 - parallel_score,  # Higher is better
        )
        
        # Relevance
        current = basis.current_price
        distance = min(
            abs(current - upper_line["y2"]) / current,
            abs(current - lower_line["y2"]) / current,
        )
        
        relevance = Relevance(
            distance_to_price=distance,
            is_active=distance < 0.05,
            is_recent=all_pivots[-1].index > len(basis.candles) - 10,
        )
        
        # Score - CALIBRATED (channels are fallback, score lower than figures)
        raw_score = (
            geometry.parallel * 0.25 +
            geometry.symmetry * 0.25 +
            (1.0 - min(distance, 0.3) / 0.3) * 0.25 +
            min(1.0, geometry.touches / 8) * 0.25
        )
        score = raw_score * 0.75  # Max ~0.75 (lower than figures)
        
        # Window bars
        window_bars = 0
        if all_pivots:
            first_idx = all_pivots[0].index
            last_idx = all_pivots[-1].index
            window_bars = last_idx - first_idx
        
        # Debug info
        debug = {
            "touch_upper": upper_touches,
            "touch_lower": lower_touches,
            "window_bars": window_bars,
            "geometry_cleanliness": 1.0 - parallel_score,
            "symmetry": touch_balance,
            "distance_to_price": distance,
            "raw_score": raw_score,
            "selected_by": "channel_layer",
            "is_fallback": True,
        }
        
        # Render
        render = RenderData(
            boundaries=[
                {
                    "id": "upper_boundary",
                    "kind": "trendline",
                    "style": "channel",
                    "x1": upper_line["x1"],
                    "y1": upper_line["y1"],
                    "x2": upper_line["x2"],
                    "y2": upper_line["y2"],
                },
                {
                    "id": "lower_boundary",
                    "kind": "trendline",
                    "style": "channel",
                    "x1": lower_line["x1"],
                    "y1": lower_line["y1"],
                    "x2": lower_line["x2"],
                    "y2": lower_line["y2"],
                },
            ],
            anchors=[
                {"time": p.time, "price": p.price, "type": "upper", "reaction": True}
                for p in highs
            ] + [
                {"time": p.time, "price": p.price, "type": "lower", "reaction": True}
                for p in lows
            ],
        )
        
        return Finding(
            type=channel_type,
            bias=self.PATTERN_BIAS.get(channel_type, BIAS_NEUTRAL),
            score=score,
            confidence=score * 0.85,
            window=window,
            geometry=geometry,
            relevance=relevance,
            render=render,
            meta={"is_fallback": True, "debug": debug},
        )
    
    def _calc_slope(self, pivots: List[Pivot]) -> Optional[float]:
        """Calculate slope of line through pivots"""
        if len(pivots) < 2:
            return None
        
        n = len(pivots)
        sum_x = sum(p.time for p in pivots)
        sum_y = sum(p.price for p in pivots)
        sum_xy = sum(p.time * p.price for p in pivots)
        sum_x2 = sum(p.time ** 2 for p in pivots)
        
        denom = n * sum_x2 - sum_x ** 2
        if denom == 0:
            return None
        
        return (n * sum_xy - sum_x * sum_y) / denom
    
    def _fit_line(self, pivots: List[Pivot]) -> Optional[Dict]:
        """Fit a line through pivots"""
        if len(pivots) < 2:
            return None
        
        slope = self._calc_slope(pivots)
        if slope is None:
            return None
        
        avg_x = sum(p.time for p in pivots) / len(pivots)
        avg_y = sum(p.price for p in pivots) / len(pivots)
        intercept = avg_y - slope * avg_x
        
        x1 = pivots[0].time
        x2 = pivots[-1].time
        y1 = slope * x1 + intercept
        y2 = slope * x2 + intercept
        
        return {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "slope": slope}


# Singleton
_channel_layer = None

def get_channel_layer() -> ChannelLayer:
    global _channel_layer
    if _channel_layer is None:
        _channel_layer = ChannelLayer()
    return _channel_layer
