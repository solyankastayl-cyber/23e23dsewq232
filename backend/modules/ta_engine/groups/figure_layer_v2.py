"""
TA Engine - Figure Layer V2 (CORRECT IMPLEMENTATION)

KEY PRINCIPLE:
NOT: lines → figure
BUT: structure → figure → lines

Based on correct TA methodology.
"""

from typing import List, Dict, Optional, Tuple
from ..groups.base import (
    BaseLayer, GroupResult, Finding, Window, Geometry, Relevance, RenderData,
    GROUP_FIGURES, BIAS_BULLISH, BIAS_BEARISH, BIAS_NEUTRAL
)
from ..core.chart_basis import ChartBasis, Pivot


class FigureLayerV2(BaseLayer):
    """
    Correct figure detection using structure-first approach.
    
    Order:
    1. Extract pivots (swing highs/lows)
    2. Classify structure (HH/HL/LH/LL)
    3. Detect pattern from structure
    4. Build lines from anchors
    """
    
    GROUP_NAME = GROUP_FIGURES
    
    # Pattern bias mapping
    PATTERN_BIAS = {
        "ascending_triangle": BIAS_BULLISH,
        "descending_triangle": BIAS_BEARISH,
        "symmetrical_triangle": BIAS_NEUTRAL,
        "rising_wedge": BIAS_BEARISH,
        "falling_wedge": BIAS_BULLISH,
        "double_top": BIAS_BEARISH,
        "double_bottom": BIAS_BULLISH,
    }
    
    # Window constraints
    MIN_WINDOW = 10
    MAX_WINDOW = 50  # Penalty if exceeded
    HARD_MAX_WINDOW = 80  # Reject if exceeded
    
    def run(self, basis: ChartBasis) -> GroupResult:
        """Run figure detection using structure-first approach"""
        findings = []
        
        if len(basis.candles) < 15:
            return self._create_result(findings, {"reason": "insufficient_candles"})
        
        # STEP 1: Extract pivots from candles
        pivots = self._extract_pivots(basis.candles)
        
        if len(pivots) < 4:
            return self._create_result(findings, {"reason": "insufficient_pivots", "pivot_count": len(pivots)})
        
        print(f"[FigureV2] Extracted {len(pivots)} pivots")
        
        # STEP 2: Classify structure
        structure = self._classify_structure(pivots)
        print(f"[FigureV2] Structure: {structure[-6:]}")
        
        # STEP 3: Detect patterns from structure
        triangle = self._detect_triangle(pivots, basis)
        wedge = self._detect_wedge(pivots, basis)
        double_top = self._detect_double_top(pivots, basis)
        double_bottom = self._detect_double_bottom(pivots, basis)
        
        # STEP 4: Validate and collect
        for p in [triangle, wedge, double_top, double_bottom]:
            validated = self._validate_pattern(p)
            if validated:
                findings.append(validated)
        
        # Sort by score
        findings.sort(key=lambda f: f.score, reverse=True)
        
        # Log results
        if findings:
            best = findings[0]
            print(f"[FigureV2] SELECTED: {best.type} score={best.score:.2f}")
        else:
            print(f"[FigureV2] No valid patterns found")
        
        return self._create_result(findings, {
            "pivot_count": len(pivots),
            "structure_sample": structure[-6:],
            "candidates_found": len(findings),
        })
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 1: PIVOT EXTRACTION
    # ═══════════════════════════════════════════════════════════════
    
    def _extract_pivots(self, candles: List[Dict], lookback: int = 2) -> List[Dict]:
        """Extract swing highs and lows from candles"""
        pivots = []
        
        for i in range(lookback, len(candles) - lookback):
            high = candles[i].get("high", candles[i].get("h", 0))
            low = candles[i].get("low", candles[i].get("l", 0))
            time = candles[i].get("time", candles[i].get("t", 0))
            
            # Check for swing high
            is_high = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i:
                    other_high = candles[j].get("high", candles[j].get("h", 0))
                    if other_high >= high:
                        is_high = False
                        break
            
            if is_high:
                pivots.append({"type": "H", "index": i, "price": high, "time": time})
            
            # Check for swing low
            is_low = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i:
                    other_low = candles[j].get("low", candles[j].get("l", 0))
                    if other_low <= low:
                        is_low = False
                        break
            
            if is_low:
                pivots.append({"type": "L", "index": i, "price": low, "time": time})
        
        # Sort by index
        pivots.sort(key=lambda p: p["index"])
        return pivots
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 2: STRUCTURE CLASSIFICATION
    # ═══════════════════════════════════════════════════════════════
    
    def _classify_structure(self, pivots: List[Dict]) -> List[str]:
        """Classify pivot sequence as HH/HL/LH/LL"""
        structure = []
        
        last_high = None
        last_low = None
        
        for p in pivots:
            if p["type"] == "H":
                if last_high is not None:
                    if p["price"] > last_high:
                        structure.append("HH")
                    else:
                        structure.append("LH")
                last_high = p["price"]
            
            elif p["type"] == "L":
                if last_low is not None:
                    if p["price"] > last_low:
                        structure.append("HL")
                    else:
                        structure.append("LL")
                last_low = p["price"]
        
        return structure
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 3: PATTERN DETECTION (STRUCTURE-FIRST)
    # ═══════════════════════════════════════════════════════════════
    
    def _detect_triangle(self, pivots: List[Dict], basis: ChartBasis) -> Optional[Finding]:
        """Detect triangle from structure (NOT from lines)"""
        highs = [p for p in pivots if p["type"] == "H"]
        lows = [p for p in pivots if p["type"] == "L"]
        
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        # Take last 3 points (recent structure)
        recent_highs = highs[-3:] if len(highs) >= 3 else highs[-2:]
        recent_lows = lows[-3:] if len(lows) >= 3 else lows[-2:]
        
        # Calculate slopes from STRUCTURE (not regression)
        high_slope = recent_highs[-1]["price"] - recent_highs[0]["price"]
        low_slope = recent_lows[-1]["price"] - recent_lows[0]["price"]
        
        # Normalize slopes by price
        avg_price = (recent_highs[0]["price"] + recent_lows[0]["price"]) / 2
        high_slope_pct = high_slope / avg_price
        low_slope_pct = low_slope / avg_price
        
        # Debug log
        print(f"[FigureV2] Triangle check: high_slope={high_slope_pct:.4f}, low_slope={low_slope_pct:.4f}")
        
        # Triangle detection - LOWERED thresholds for crypto volatility
        triangle_type = None
        
        # Symmetrical: upper down, lower up (converging)
        if high_slope_pct < -0.002 and low_slope_pct > 0.002:
            triangle_type = "symmetrical_triangle"
        
        # Ascending: upper flat, lower up
        elif abs(high_slope_pct) < 0.015 and low_slope_pct > 0.002:
            triangle_type = "ascending_triangle"
        
        # Descending: upper down, lower flat
        elif high_slope_pct < -0.002 and abs(low_slope_pct) < 0.015:
            triangle_type = "descending_triangle"
        
        if not triangle_type:
            return None
        
        return self._build_pattern(
            pattern_type=triangle_type,
            upper_anchors=recent_highs,
            lower_anchors=recent_lows,
            basis=basis,
        )
    
    def _detect_wedge(self, pivots: List[Dict], basis: ChartBasis) -> Optional[Finding]:
        """Detect wedge from structure"""
        highs = [p for p in pivots if p["type"] == "H"]
        lows = [p for p in pivots if p["type"] == "L"]
        
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        recent_highs = highs[-3:] if len(highs) >= 3 else highs[-2:]
        recent_lows = lows[-3:] if len(lows) >= 3 else lows[-2:]
        
        high_slope = recent_highs[-1]["price"] - recent_highs[0]["price"]
        low_slope = recent_lows[-1]["price"] - recent_lows[0]["price"]
        
        avg_price = (recent_highs[0]["price"] + recent_lows[0]["price"]) / 2
        high_slope_pct = high_slope / avg_price
        low_slope_pct = low_slope / avg_price
        
        print(f"[FigureV2] Wedge check: high_slope={high_slope_pct:.4f}, low_slope={low_slope_pct:.4f}")
        
        wedge_type = None
        
        # Falling wedge: both down, converging (lower less steep)
        if high_slope_pct < -0.002 and low_slope_pct < -0.002:
            if abs(low_slope_pct) < abs(high_slope_pct):  # Converging
                wedge_type = "falling_wedge"
        
        # Rising wedge: both up, converging (upper less steep)
        elif high_slope_pct > 0.002 and low_slope_pct > 0.002:
            if abs(high_slope_pct) < abs(low_slope_pct):  # Converging
                wedge_type = "rising_wedge"
        
        if not wedge_type:
            return None
        
        return self._build_pattern(
            pattern_type=wedge_type,
            upper_anchors=recent_highs,
            lower_anchors=recent_lows,
            basis=basis,
        )
    
    def _detect_double_top(self, pivots: List[Dict], basis: ChartBasis) -> Optional[Finding]:
        """Detect double top - REQUIRES 2 SIMILAR PEAKS"""
        highs = [p for p in pivots if p["type"] == "H"]
        
        # CRITICAL: Must have at least 2 peaks
        if len(highs) < 2:
            return None
        
        p1 = highs[-2]
        p2 = highs[-1]
        
        # CRITICAL: Peaks must be similar (within 1.5%)
        diff = abs(p1["price"] - p2["price"]) / p1["price"]
        if diff > 0.015:
            return None
        
        # Must have some distance between peaks (not adjacent)
        if p2["index"] - p1["index"] < 5:
            return None
        
        return self._build_double_pattern(
            pattern_type="double_top",
            peak1=p1,
            peak2=p2,
            basis=basis,
        )
    
    def _detect_double_bottom(self, pivots: List[Dict], basis: ChartBasis) -> Optional[Finding]:
        """Detect double bottom - REQUIRES 2 SIMILAR TROUGHS"""
        lows = [p for p in pivots if p["type"] == "L"]
        
        if len(lows) < 2:
            return None
        
        p1 = lows[-2]
        p2 = lows[-1]
        
        # Peaks must be similar (within 1.5%)
        diff = abs(p1["price"] - p2["price"]) / p1["price"]
        if diff > 0.015:
            return None
        
        # Must have some distance between
        if p2["index"] - p1["index"] < 5:
            return None
        
        return self._build_double_pattern(
            pattern_type="double_bottom",
            peak1=p1,
            peak2=p2,
            basis=basis,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 4: BUILD PATTERN (LINES FROM ANCHORS)
    # ═══════════════════════════════════════════════════════════════
    
    def _build_pattern(
        self,
        pattern_type: str,
        upper_anchors: List[Dict],
        lower_anchors: List[Dict],
        basis: ChartBasis,
    ) -> Finding:
        """Build pattern finding from anchors"""
        all_anchors = upper_anchors + lower_anchors
        all_indices = [a["index"] for a in all_anchors]
        
        window_start = min(a["time"] for a in all_anchors)
        window_end = max(a["time"] for a in all_anchors)
        window_bars = max(all_indices) - min(all_indices)
        
        # Build lines FROM anchor points (not regression)
        upper_line = self._line_from_anchors(upper_anchors)
        lower_line = self._line_from_anchors(lower_anchors)
        
        # Calculate geometry
        touch_balance = min(len(upper_anchors), len(lower_anchors)) / max(len(upper_anchors), len(lower_anchors))
        
        # Convergence check
        start_width = upper_anchors[0]["price"] - lower_anchors[0]["price"]
        end_width = upper_anchors[-1]["price"] - lower_anchors[-1]["price"]
        convergence = 1.0 - abs(end_width / start_width) if start_width != 0 else 0
        convergence = max(0, min(1, convergence))  # Clamp to 0-1
        
        geometry = Geometry(
            valid=True,
            clean=convergence > 0.1,
            touches=len(upper_anchors) + len(lower_anchors),
            symmetry=touch_balance,
        )
        
        # Relevance
        current = basis.current_price
        distance = min(
            abs(current - upper_anchors[-1]["price"]) / current,
            abs(current - lower_anchors[-1]["price"]) / current,
        )
        
        relevance = Relevance(
            distance_to_price=distance,
            is_active=distance < 0.05,
            is_recent=all_anchors[-1]["index"] > len(basis.candles) - 15,
        )
        
        # Score - with window penalty
        raw_score = (
            touch_balance * 0.25 +
            (1.0 - min(distance, 0.3) / 0.3) * 0.25 +
            min(1.0, geometry.touches / 6) * 0.25 +
            convergence * 0.25
        )
        
        # Window penalty
        if window_bars > self.MAX_WINDOW:
            raw_score *= 0.7
        
        score = raw_score * 0.85  # Max ~0.85
        
        # Debug info
        debug = {
            "touch_upper": len(upper_anchors),
            "touch_lower": len(lower_anchors),
            "window_bars": window_bars,
            "geometry_cleanliness": convergence,
            "symmetry": touch_balance,
            "distance_to_price": distance,
            "raw_score": raw_score,
            "selected_by": "figure_layer_v2",
            "upper_slope": upper_line.get("slope", 0) if upper_line else 0,
            "lower_slope": lower_line.get("slope", 0) if lower_line else 0,
        }
        
        # Render data
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
            ] if upper_line and lower_line else [],
            anchors=[
                {"time": a["time"], "price": a["price"], "type": "upper", "reaction": True}
                for a in upper_anchors
            ] + [
                {"time": a["time"], "price": a["price"], "type": "lower", "reaction": True}
                for a in lower_anchors
            ],
        )
        
        return Finding(
            type=pattern_type,
            bias=self.PATTERN_BIAS.get(pattern_type, BIAS_NEUTRAL),
            score=score,
            confidence=score * 0.9,
            window=Window(start=window_start, end=window_end),
            geometry=geometry,
            relevance=relevance,
            render=render,
            meta={"debug": debug},
        )
    
    def _build_double_pattern(
        self,
        pattern_type: str,
        peak1: Dict,
        peak2: Dict,
        basis: ChartBasis,
    ) -> Finding:
        """Build double top/bottom finding"""
        window_bars = peak2["index"] - peak1["index"]
        level_price = (peak1["price"] + peak2["price"]) / 2
        
        # Geometry
        price_diff = abs(peak1["price"] - peak2["price"]) / peak1["price"]
        symmetry = 1.0 - price_diff / 0.015  # Max diff is 1.5%
        
        geometry = Geometry(
            valid=True,
            clean=True,
            touches=2,
            symmetry=symmetry,
        )
        
        # Distance
        distance = abs(basis.current_price - level_price) / basis.current_price
        
        relevance = Relevance(
            distance_to_price=distance,
            is_active=distance < 0.05,
            is_recent=peak2["index"] > len(basis.candles) - 15,
        )
        
        # Score
        raw_score = symmetry * 0.4 + (1.0 - min(distance, 0.3) / 0.3) * 0.4 + 0.2
        
        if window_bars > self.MAX_WINDOW:
            raw_score *= 0.7
        
        score = raw_score * 0.8
        
        debug = {
            "touch_upper": 2 if "top" in pattern_type else 0,
            "touch_lower": 2 if "bottom" in pattern_type else 0,
            "window_bars": window_bars,
            "geometry_cleanliness": symmetry,
            "symmetry": symmetry,
            "distance_to_price": distance,
            "raw_score": raw_score,
            "selected_by": "figure_layer_v2",
            "peak_diff_pct": price_diff * 100,
        }
        
        render = RenderData(
            levels=[
                {
                    "id": f"{pattern_type}_level",
                    "kind": "horizontal",
                    "price": level_price,
                    "start": peak1["time"],
                    "end": peak2["time"],
                }
            ],
            anchors=[
                {"time": peak1["time"], "price": peak1["price"], "type": "peak", "reaction": True},
                {"time": peak2["time"], "price": peak2["price"], "type": "peak", "reaction": True},
            ],
        )
        
        return Finding(
            type=pattern_type,
            bias=self.PATTERN_BIAS.get(pattern_type, BIAS_NEUTRAL),
            score=score,
            confidence=score * 0.85,
            window=Window(start=peak1["time"], end=peak2["time"]),
            geometry=geometry,
            relevance=relevance,
            render=render,
            meta={"debug": debug},
        )
    
    # ═══════════════════════════════════════════════════════════════
    # VALIDATION
    # ═══════════════════════════════════════════════════════════════
    
    def _validate_pattern(self, p: Optional[Finding]) -> Optional[Finding]:
        """Validate pattern meets minimum requirements"""
        if not p:
            return None
        
        debug = p.meta.get("debug", {}) if p.meta else {}
        
        touch_upper = debug.get("touch_upper", 0)
        touch_lower = debug.get("touch_lower", 0)
        window_bars = debug.get("window_bars", 0)
        
        # Double patterns need exactly 2 touches on one side
        if "double" in p.type:
            if touch_upper < 2 and touch_lower < 2:
                print(f"[FigureV2] REJECTED {p.type}: needs 2 peaks, has {max(touch_upper, touch_lower)}")
                return None
        else:
            # Other patterns need at least 2 touches per side
            if touch_upper < 2 or touch_lower < 2:
                print(f"[FigureV2] REJECTED {p.type}: needs 2+2 touches, has {touch_upper}+{touch_lower}")
                return None
        
        # Window constraints
        if window_bars < self.MIN_WINDOW:
            print(f"[FigureV2] REJECTED {p.type}: window {window_bars} < {self.MIN_WINDOW}")
            return None
        
        if window_bars > self.HARD_MAX_WINDOW:
            print(f"[FigureV2] REJECTED {p.type}: window {window_bars} > {self.HARD_MAX_WINDOW}")
            return None
        
        return p
    
    # ═══════════════════════════════════════════════════════════════
    # UTILITY
    # ═══════════════════════════════════════════════════════════════
    
    def _line_from_anchors(self, anchors: List[Dict]) -> Optional[Dict]:
        """Build line directly from anchor points (NOT regression)"""
        if len(anchors) < 2:
            return None
        
        first = anchors[0]
        last = anchors[-1]
        
        dx = last["index"] - first["index"]
        dy = last["price"] - first["price"]
        slope = dy / dx if dx != 0 else 0
        
        return {
            "x1": first["time"],
            "y1": first["price"],
            "x2": last["time"],
            "y2": last["price"],
            "slope": slope,
        }


# Singleton
_figure_layer_v2 = None

def get_figure_layer_v2() -> FigureLayerV2:
    global _figure_layer_v2
    if _figure_layer_v2 is None:
        _figure_layer_v2 = FigureLayerV2()
    return _figure_layer_v2
