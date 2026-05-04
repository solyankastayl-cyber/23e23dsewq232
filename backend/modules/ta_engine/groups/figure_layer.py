"""
TA Engine - Figure Layer (Group 4)
Classical chart patterns: triangles, wedges, flags, H&S, etc.

THIS IS THE PRIMARY PATTERN SOURCE.
Channels are fallback, not primary.
"""

from typing import List, Dict, Optional, Tuple
from ..groups.base import (
    BaseLayer, GroupResult, Finding, Window, Geometry, Relevance, RenderData,
    GROUP_FIGURES, BIAS_BULLISH, BIAS_BEARISH, BIAS_NEUTRAL
)
from ..core.chart_basis import ChartBasis, Pivot
import math


class FigureLayer(BaseLayer):
    """
    Detects classical chart patterns.
    
    Patterns detected:
    - Triangles: ascending, descending, symmetrical
    - Wedges: rising, falling
    - Flags: bull, bear
    - Double top/bottom
    - Head & Shoulders (basic)
    """
    
    GROUP_NAME = GROUP_FIGURES
    
    # Pattern bias mapping
    PATTERN_BIAS = {
        "ascending_triangle": BIAS_BULLISH,
        "descending_triangle": BIAS_BEARISH,
        "symmetrical_triangle": BIAS_NEUTRAL,
        "rising_wedge": BIAS_BEARISH,  # Bearish reversal
        "falling_wedge": BIAS_BULLISH,  # Bullish reversal
        "bull_flag": BIAS_BULLISH,
        "bear_flag": BIAS_BEARISH,
        "double_top": BIAS_BEARISH,
        "double_bottom": BIAS_BULLISH,
        "head_shoulders": BIAS_BEARISH,
        "inverse_head_shoulders": BIAS_BULLISH,
    }
    
    def __init__(self):
        self.min_touches = 2  # Per side
        self.min_candles = 10
        self.convergence_threshold = 0.15  # For wedges
    
    def run(self, basis: ChartBasis) -> GroupResult:
        """Run figure detection on chart basis"""
        findings = []
        
        if len(basis.candles) < self.min_candles or len(basis.pivots) < 4:
            return self._create_result(findings, {"reason": "insufficient_data"})
        
        # Detect each pattern type
        findings.extend(self._detect_triangles(basis))
        findings.extend(self._detect_wedges(basis))
        findings.extend(self._detect_double_patterns(basis))
        
        # Sort by score descending
        findings.sort(key=lambda f: f.score, reverse=True)
        
        # Keep only best candidates (no overlap)
        findings = self._remove_overlapping(findings)
        
        return self._create_result(findings, {
            "total_candidates": len(findings),
            "pattern_types": list(set(f.type for f in findings)),
        })
    
    # ═══════════════════════════════════════════════════════════════
    # TRIANGLE DETECTION
    # ═══════════════════════════════════════════════════════════════
    
    def _detect_triangles(self, basis: ChartBasis) -> List[Finding]:
        """Detect triangle patterns"""
        findings = []
        
        highs = [p for p in basis.pivots if p.type == "high"]
        lows = [p for p in basis.pivots if p.type == "low"]
        
        if len(highs) < 2 or len(lows) < 2:
            return findings
        
        # Get recent pivots for analysis
        recent_highs = highs[-4:] if len(highs) >= 4 else highs
        recent_lows = lows[-4:] if len(lows) >= 4 else lows
        
        # Check ascending triangle: flat top, rising bottom
        upper_slope = self._calc_slope(recent_highs)
        lower_slope = self._calc_slope(recent_lows)
        
        if upper_slope is not None and lower_slope is not None:
            # Ascending: upper flat, lower rising
            if abs(upper_slope) < 0.001 and lower_slope > 0.0005:
                finding = self._build_triangle_finding(
                    "ascending_triangle", basis, recent_highs, recent_lows
                )
                if finding:
                    findings.append(finding)
            
            # Descending: upper falling, lower flat
            elif upper_slope < -0.0005 and abs(lower_slope) < 0.001:
                finding = self._build_triangle_finding(
                    "descending_triangle", basis, recent_highs, recent_lows
                )
                if finding:
                    findings.append(finding)
            
            # Symmetrical: both converging
            elif upper_slope < -0.0003 and lower_slope > 0.0003:
                finding = self._build_triangle_finding(
                    "symmetrical_triangle", basis, recent_highs, recent_lows
                )
                if finding:
                    findings.append(finding)
        
        return findings
    
    def _build_triangle_finding(
        self, 
        pattern_type: str, 
        basis: ChartBasis,
        highs: List[Pivot],
        lows: List[Pivot]
    ) -> Optional[Finding]:
        """Build a triangle finding with proper geometry"""
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        # Window from first to last pivot
        all_pivots = sorted(highs + lows, key=lambda p: p.index)
        window = Window(
            start=all_pivots[0].time,
            end=all_pivots[-1].time,
        )
        
        # Build trendlines
        upper_line = self._fit_line(highs)
        lower_line = self._fit_line(lows)
        
        if not upper_line or not lower_line:
            return None
        
        # Calculate geometry quality
        upper_touches = len(highs)
        lower_touches = len(lows)
        touch_balance = min(upper_touches, lower_touches) / max(upper_touches, lower_touches)
        
        # Convergence check
        start_width = upper_line["y1"] - lower_line["y1"]
        end_width = upper_line["y2"] - lower_line["y2"]
        convergence = 1.0 - (end_width / start_width) if start_width > 0 else 0
        
        geometry = Geometry(
            valid=True,
            clean=convergence > 0.1,  # Must be converging
            touches=upper_touches + lower_touches,
            symmetry=touch_balance,
        )
        
        # Relevance to current price
        current = basis.current_price
        distance = min(
            abs(current - upper_line["y2"]) / current,
            abs(current - lower_line["y2"]) / current,
        )
        
        relevance = Relevance(
            distance_to_price=distance,
            is_active=distance < 0.05,  # Within 5% of pattern
            is_recent=all_pivots[-1].index > len(basis.candles) - 10,
            recency_score=1.0 - (len(basis.candles) - all_pivots[-1].index) / len(basis.candles),
        )
        
        # Score calculation - CALIBRATED (no more 0.99-1.00!)
        # Real TA scores should be 0.5-0.85 range typically
        raw_score = (
            geometry.symmetry * 0.25 +
            (1.0 - min(distance, 0.3) / 0.3) * 0.25 +  # Cap distance impact
            min(1.0, geometry.touches / 8) * 0.25 +  # Harder to get full touch score
            convergence * 0.25
        )
        # Apply penalty for imperfect patterns
        score = raw_score * 0.85  # Max possible ~0.85
        
        # Calculate window_bars from pivot indices
        window_bars = 0
        if all_pivots:
            first_idx = all_pivots[0].index
            last_idx = all_pivots[-1].index
            window_bars = last_idx - first_idx
        
        # Add debug info with slopes for Display Gate
        upper_slope = upper_line.get("slope", 0)
        lower_slope = lower_line.get("slope", 0)
        
        debug = {
            "touch_upper": upper_touches,
            "touch_lower": lower_touches,
            "window_bars": window_bars,
            "geometry_cleanliness": convergence,
            "symmetry": touch_balance,
            "distance_to_price": distance,
            "raw_score": raw_score,
            "selected_by": "figure_layer",
            "upper_slope": upper_slope,
            "lower_slope": lower_slope,
        }
        
        # Build render data
        render = RenderData(
            boundaries=[
                {
                    "id": "upper_boundary",
                    "kind": "trendline",
                    "style": "primary",
                    "x1": upper_line["x1"],
                    "y1": upper_line["y1"],
                    "x2": upper_line["x2"],
                    "y2": upper_line["y2"],
                },
                {
                    "id": "lower_boundary",
                    "kind": "trendline",
                    "style": "primary",
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
            type=pattern_type,
            bias=self.PATTERN_BIAS.get(pattern_type, BIAS_NEUTRAL),
            score=score,
            confidence=score * 0.9,
            window=window,
            geometry=geometry,
            relevance=relevance,
            render=render,
            meta={"debug": debug},
        )
    
    # ═══════════════════════════════════════════════════════════════
    # WEDGE DETECTION
    # ═══════════════════════════════════════════════════════════════
    
    def _detect_wedges(self, basis: ChartBasis) -> List[Finding]:
        """Detect wedge patterns (rising/falling)"""
        findings = []
        
        highs = [p for p in basis.pivots if p.type == "high"]
        lows = [p for p in basis.pivots if p.type == "low"]
        
        if len(highs) < 2 or len(lows) < 2:
            return findings
        
        recent_highs = highs[-4:] if len(highs) >= 4 else highs
        recent_lows = lows[-4:] if len(lows) >= 4 else lows
        
        upper_slope = self._calc_slope(recent_highs)
        lower_slope = self._calc_slope(recent_lows)
        
        if upper_slope is None or lower_slope is None:
            return findings
        
        # Both lines must have same direction but converging
        both_rising = upper_slope > 0 and lower_slope > 0
        both_falling = upper_slope < 0 and lower_slope < 0
        
        # Rising wedge: both rising, upper slower than lower (converging)
        if both_rising and upper_slope < lower_slope:
            finding = self._build_wedge_finding(
                "rising_wedge", basis, recent_highs, recent_lows
            )
            if finding:
                findings.append(finding)
        
        # Falling wedge: both falling, lower slower (less steep) than upper
        elif both_falling and lower_slope > upper_slope:
            finding = self._build_wedge_finding(
                "falling_wedge", basis, recent_highs, recent_lows
            )
            if finding:
                findings.append(finding)
        
        return findings
    
    def _build_wedge_finding(
        self,
        pattern_type: str,
        basis: ChartBasis,
        highs: List[Pivot],
        lows: List[Pivot]
    ) -> Optional[Finding]:
        """Build a wedge finding"""
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        all_pivots = sorted(highs + lows, key=lambda p: p.index)
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
        
        # Check convergence
        start_width = upper_line["y1"] - lower_line["y1"]
        end_width = upper_line["y2"] - lower_line["y2"]
        convergence = 1.0 - abs(end_width / start_width) if start_width != 0 else 0
        
        geometry = Geometry(
            valid=True,
            clean=convergence > 0.1,
            touches=upper_touches + lower_touches,
            symmetry=touch_balance,
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
            recency_score=1.0 - (len(basis.candles) - all_pivots[-1].index) / len(basis.candles),
        )
        
        # Score - CALIBRATED
        raw_score = (
            geometry.symmetry * 0.25 +
            (1.0 - min(distance, 0.3) / 0.3) * 0.25 +
            min(1.0, geometry.touches / 8) * 0.25 +
            convergence * 0.25
        )
        score = raw_score * 0.85  # Max ~0.85
        
        # Window bars calculation
        window_bars = 0
        if all_pivots:
            first_idx = all_pivots[0].index
            last_idx = all_pivots[-1].index
            window_bars = last_idx - first_idx
        
        # Debug info with slopes
        upper_slope = upper_line.get("slope", 0)
        lower_slope = lower_line.get("slope", 0)
        
        debug = {
            "touch_upper": upper_touches,
            "touch_lower": lower_touches,
            "window_bars": window_bars,
            "geometry_cleanliness": convergence,
            "symmetry": touch_balance,
            "distance_to_price": distance,
            "raw_score": raw_score,
            "selected_by": "figure_layer",
            "upper_slope": upper_slope,
            "lower_slope": lower_slope,
        }
        
        # Render
        render = RenderData(
            boundaries=[
                {
                    "id": "upper_boundary",
                    "kind": "trendline",
                    "style": "primary",
                    "x1": upper_line["x1"],
                    "y1": upper_line["y1"],
                    "x2": upper_line["x2"],
                    "y2": upper_line["y2"],
                },
                {
                    "id": "lower_boundary",
                    "kind": "trendline",
                    "style": "primary",
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
            type=pattern_type,
            bias=self.PATTERN_BIAS.get(pattern_type, BIAS_NEUTRAL),
            score=score,
            confidence=score * 0.9,
            window=window,
            geometry=geometry,
            relevance=relevance,
            render=render,
            meta={"debug": debug},
        )
    
    # ═══════════════════════════════════════════════════════════════
    # DOUBLE TOP/BOTTOM DETECTION
    # ═══════════════════════════════════════════════════════════════
    
    def _detect_double_patterns(self, basis: ChartBasis) -> List[Finding]:
        """Detect double top and double bottom patterns"""
        findings = []
        
        highs = [p for p in basis.pivots if p.type == "high"]
        lows = [p for p in basis.pivots if p.type == "low"]
        
        # Double top: two similar highs
        if len(highs) >= 2:
            for i in range(len(highs) - 1):
                h1 = highs[i]
                h2 = highs[i + 1]
                
                # Check if prices are similar (within 2%)
                diff = abs(h1.price - h2.price) / max(h1.price, h2.price)
                if diff < 0.02:
                    finding = self._build_double_finding(
                        "double_top", basis, h1, h2, BIAS_BEARISH
                    )
                    if finding:
                        findings.append(finding)
        
        # Double bottom: two similar lows
        if len(lows) >= 2:
            for i in range(len(lows) - 1):
                l1 = lows[i]
                l2 = lows[i + 1]
                
                diff = abs(l1.price - l2.price) / max(l1.price, l2.price)
                if diff < 0.02:
                    finding = self._build_double_finding(
                        "double_bottom", basis, l1, l2, BIAS_BULLISH
                    )
                    if finding:
                        findings.append(finding)
        
        return findings
    
    def _build_double_finding(
        self,
        pattern_type: str,
        basis: ChartBasis,
        p1: Pivot,
        p2: Pivot,
        bias: str
    ) -> Optional[Finding]:
        """Build double top/bottom finding"""
        window = Window(start=p1.time, end=p2.time)
        window_bars = p2.index - p1.index
        
        level_price = (p1.price + p2.price) / 2
        
        geometry = Geometry(
            valid=True,
            clean=True,
            touches=2,
            symmetry=1.0 - abs(p1.price - p2.price) / max(p1.price, p2.price),
        )
        
        distance = abs(basis.current_price - level_price) / basis.current_price
        
        relevance = Relevance(
            distance_to_price=distance,
            is_active=distance < 0.05,
            is_recent=p2.index > len(basis.candles) - 10,
        )
        
        # Score - CALIBRATED
        raw_score = geometry.symmetry * 0.4 + (1.0 - min(distance, 0.3) / 0.3) * 0.4 + 0.2 * (window_bars > 5)
        score = raw_score * 0.80
        
        # Debug info
        debug = {
            "touch_upper": 1 if "top" in pattern_type else 0,
            "touch_lower": 1 if "bottom" in pattern_type else 0,
            "window_bars": window_bars,
            "geometry_cleanliness": geometry.symmetry,
            "symmetry": geometry.symmetry,
            "distance_to_price": distance,
            "raw_score": raw_score,
            "selected_by": "figure_layer",
        }
        
        render = RenderData(
            levels=[
                {
                    "id": f"{pattern_type}_level",
                    "kind": "horizontal",
                    "price": level_price,
                    "start": p1.time,
                    "end": p2.time,
                }
            ],
            anchors=[
                {"time": p1.time, "price": p1.price, "type": "peak", "reaction": True},
                {"time": p2.time, "price": p2.price, "type": "peak", "reaction": True},
            ],
        )
        
        return Finding(
            type=pattern_type,
            bias=bias,
            score=score,
            confidence=score * 0.85,
            window=window,
            geometry=geometry,
            relevance=relevance,
            render=render,
            meta={"debug": debug},
        )
    
    # ═══════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════
    
    def _calc_slope(self, pivots: List[Pivot]) -> Optional[float]:
        """Calculate slope of line through pivots (price per time unit)"""
        if len(pivots) < 2:
            return None
        
        # Simple linear regression
        n = len(pivots)
        sum_x = sum(p.time for p in pivots)
        sum_y = sum(p.price for p in pivots)
        sum_xy = sum(p.time * p.price for p in pivots)
        sum_x2 = sum(p.time ** 2 for p in pivots)
        
        denom = n * sum_x2 - sum_x ** 2
        if denom == 0:
            return None
        
        slope = (n * sum_xy - sum_x * sum_y) / denom
        return slope
    
    def _fit_line(self, pivots: List[Pivot]) -> Optional[Dict]:
        """Fit a line through pivots, return {x1, y1, x2, y2}"""
        if len(pivots) < 2:
            return None
        
        slope = self._calc_slope(pivots)
        if slope is None:
            return None
        
        # Calculate intercept
        avg_x = sum(p.time for p in pivots) / len(pivots)
        avg_y = sum(p.price for p in pivots) / len(pivots)
        intercept = avg_y - slope * avg_x
        
        # Line from first to last pivot
        x1 = pivots[0].time
        x2 = pivots[-1].time
        y1 = slope * x1 + intercept
        y2 = slope * x2 + intercept
        
        return {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "slope": slope}
    
    def _remove_overlapping(self, findings: List[Finding], max_count: int = 3) -> List[Finding]:
        """Remove overlapping patterns, keep best ones"""
        if len(findings) <= max_count:
            return findings
        
        result = []
        for f in findings:
            # Check overlap with already selected
            overlaps = False
            for selected in result:
                if self._patterns_overlap(f, selected):
                    overlaps = True
                    break
            
            if not overlaps:
                result.append(f)
            
            if len(result) >= max_count:
                break
        
        return result
    
    def _patterns_overlap(self, f1: Finding, f2: Finding) -> bool:
        """Check if two patterns overlap significantly"""
        if not f1.window or not f2.window:
            return False
        
        # Check time overlap
        start1, end1 = f1.window.start, f1.window.end
        start2, end2 = f2.window.start, f2.window.end
        
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)
        
        if overlap_start >= overlap_end:
            return False
        
        # If >50% overlap, consider them overlapping
        overlap_duration = overlap_end - overlap_start
        f1_duration = end1 - start1
        f2_duration = end2 - start2
        
        if f1_duration > 0 and f2_duration > 0:
            overlap_ratio = overlap_duration / min(f1_duration, f2_duration)
            return overlap_ratio > 0.5
        
        return False


# Singleton
_figure_layer = None

def get_figure_layer() -> FigureLayer:
    global _figure_layer
    if _figure_layer is None:
        _figure_layer = FigureLayer()
    return _figure_layer
