"""
Display Gate - Textbook Quality Filter
======================================

PRINCIPLE:
Better to show NO pattern than to show garbage.

This gate decides:
- Should pattern be displayed to user?
- Or kept as internal candidate only?

A pattern passes Display Gate ONLY if:
1. It would be recognized by a trader in < 2 seconds
2. It looks like a textbook example
3. All quality metrics are HIGH (not just "acceptable")

If pattern fails Display Gate:
- Backend still returns it as "candidate"
- But frontend should NOT render it
- Instead show: "No dominant pattern" or "Structure developing"
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DisplayGateResult:
    """Result of display gate validation."""
    should_display: bool
    reason: str
    gate_scores: Dict[str, float]
    fallback_message: str


class DisplayGate:
    """
    Decides if pattern should be shown to user.
    
    STRICT thresholds - better to under-show than over-show.
    """
    
    # ═══════════════════════════════════════════════════════════════
    # DISPLAY THRESHOLDS - LOWERED for V2 pipeline compatibility
    # V2 pipeline uses different scoring, thresholds adjusted
    # ═══════════════════════════════════════════════════════════════
    
    THRESHOLDS = {
        "geometry_score": 0.40,    # Lowered for V2
        "touch_score": 0.25,       # Lowered for V2 (double_top has 1+1 touches)
        "visual_score": 0.40,      # Lowered for V2
        "render_quality": 0.40,    # Lowered for V2
        "combined_score": 0.45,    # Lowered for V2
    }
    
    # Pattern-specific requirements
    PATTERN_REQUIREMENTS = {
        "falling_wedge": {
            "min_touches_upper": 2,
            "min_touches_lower": 2,
            "must_converge": True,
            "min_window_candles": 20,
            "max_angle_diff": 15,
        },
        "rising_wedge": {
            "min_touches_upper": 2,
            "min_touches_lower": 2,
            "must_converge": True,
            "min_window_candles": 20,
            "max_angle_diff": 15,
        },
        "ascending_triangle": {
            "min_touches_upper": 2,  # Flat resistance
            "min_touches_lower": 2,  # Rising support
            "upper_must_be_flat": True,
            "min_window_candles": 12,  # Lowered
        },
        "descending_triangle": {
            "min_touches_upper": 2,  # Falling resistance
            "min_touches_lower": 2,  # Flat support
            "lower_must_be_flat": True,
            "min_window_candles": 12,  # Lowered
        },
        "symmetrical_triangle": {
            "min_touches_upper": 2,
            "min_touches_lower": 2,
            "must_converge": True,
            "min_window_candles": 20,
        },
        "ascending_channel": {
            "min_touches_upper": 2,
            "min_touches_lower": 2,
            "must_be_parallel": True,
            "min_window_candles": 15,  # LOWERED: was 25, now accepts shorter 4H patterns
        },
        "descending_channel": {
            "min_touches_upper": 2,
            "min_touches_lower": 2,
            "must_be_parallel": True,
            "min_window_candles": 15,  # LOWERED: was 25
        },
        "horizontal_channel": {
            "min_touches_upper": 3,  # Range needs more touches
            "min_touches_lower": 3,
            "must_be_horizontal": True,
            "min_window_candles": 20,
        },
    }
    
    # Fallback messages when pattern rejected
    FALLBACK_MESSAGES = {
        "low_scores": "Market structure is developing. No dominant pattern detected.",
        "insufficient_touches": "Price consolidating. Pattern not yet confirmed.",
        "geometry_invalid": "Structure in transition. Awaiting clearer formation.",
        "too_small": "Localized price action. No tradeable pattern.",
        "forced_fit": "No clean textbook pattern. Treating as range/consolidation.",
    }
    
    def __init__(self):
        pass
    
    def evaluate(self, pattern: Dict) -> DisplayGateResult:
        """
        Evaluate if pattern should be displayed.
        
        Returns:
            DisplayGateResult with decision and reasoning
        """
        if not pattern:
            return DisplayGateResult(
                should_display=False,
                reason="No pattern provided",
                gate_scores={},
                fallback_message=self.FALLBACK_MESSAGES["low_scores"]
            )
        
        pattern_type = pattern.get("type", "unknown")
        
        # ═══════════════════════════════════════════════════════════════
        # SPECIAL CASE: Structure fallback from History Scanner
        # Always display structure context (it's not a pattern, it's context)
        # ═══════════════════════════════════════════════════════════════
        if pattern.get("is_fallback") or pattern_type == "structure_context":
            return DisplayGateResult(
                should_display=True,
                reason="Structure context always displayable",
                gate_scores={"structure": 1.0},
                fallback_message=""
            )
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 1: Check base score thresholds
        # ═══════════════════════════════════════════════════════════════
        gate_scores = {
            "geometry_score": self._get_geometry_score(pattern),
            "touch_score": pattern.get("touch_score", 0),
            "visual_score": pattern.get("visual_score", 0),
            "render_quality": pattern.get("render_quality", 0),
            "combined_score": pattern.get("combined_score", 0),
        }
        
        failed_thresholds = []
        for metric, threshold in self.THRESHOLDS.items():
            if gate_scores.get(metric, 0) < threshold:
                failed_thresholds.append(f"{metric}={gate_scores.get(metric, 0):.2f}<{threshold}")
        
        if failed_thresholds:
            return DisplayGateResult(
                should_display=False,
                reason=f"Failed thresholds: {', '.join(failed_thresholds)}",
                gate_scores=gate_scores,
                fallback_message=self.FALLBACK_MESSAGES["low_scores"]
            )
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 2: Check pattern-specific requirements
        # ═══════════════════════════════════════════════════════════════
        requirements = self.PATTERN_REQUIREMENTS.get(pattern_type, {})
        
        if requirements:
            req_result = self._check_pattern_requirements(pattern, requirements)
            if not req_result[0]:
                return DisplayGateResult(
                    should_display=False,
                    reason=f"Pattern requirement failed: {req_result[1]}",
                    gate_scores=gate_scores,
                    fallback_message=self._get_fallback_for_failure(req_result[1])
                )
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 3: Textbook readability check
        # ═══════════════════════════════════════════════════════════════
        textbook_result = self._check_textbook_readability(pattern)
        if not textbook_result[0]:
            return DisplayGateResult(
                should_display=False,
                reason=f"Textbook check failed: {textbook_result[1]}",
                gate_scores=gate_scores,
                fallback_message=self.FALLBACK_MESSAGES["forced_fit"]
            )
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 4: Lifecycle check - don't show invalidated patterns
        # ═══════════════════════════════════════════════════════════════
        lifecycle = pattern.get("lifecycle", {})
        if lifecycle.get("stage") == "invalidated":
            return DisplayGateResult(
                should_display=False,
                reason="Pattern invalidated",
                gate_scores=gate_scores,
                fallback_message="Previous pattern invalidated. Analyzing new structure."
            )
        
        # ═══════════════════════════════════════════════════════════════
        # PASSED ALL GATES
        # ═══════════════════════════════════════════════════════════════
        return DisplayGateResult(
            should_display=True,
            reason="Pattern passes display gate",
            gate_scores=gate_scores,
            fallback_message=""
        )
    
    def _get_geometry_score(self, pattern: Dict) -> float:
        """Extract or compute geometry score."""
        # Check visual breakdown first
        visual_breakdown = pattern.get("visual_breakdown", {})
        if "symmetry" in visual_breakdown:
            return visual_breakdown["symmetry"]
        
        # Fall back to combined score
        return pattern.get("combined_score", 0) * 0.9
    
    def _check_pattern_requirements(
        self,
        pattern: Dict,
        requirements: Dict
    ) -> Tuple[bool, str]:
        """
        Check pattern-specific requirements.
        
        Returns (passed, failure_reason)
        """
        touches = pattern.get("touches", {})
        upper_touches = touches.get("upper", [])
        lower_touches = touches.get("lower", [])
        
        # Also check debug for V2 pipeline patterns
        debug = pattern.get("debug", {})
        debug_touch_upper = debug.get("touch_upper", 0)
        debug_touch_lower = debug.get("touch_lower", 0)
        
        # Use whichever is greater (V2 uses debug, V1 uses touches)
        upper_count = max(len(upper_touches), debug_touch_upper)
        lower_count = max(len(lower_touches), debug_touch_lower)
        
        window = pattern.get("window", {})
        candle_count = window.get("candle_count", debug.get("window_bars", 0))
        
        slopes = pattern.get("slopes", {})
        upper_slope = slopes.get("upper", 0)
        lower_slope = slopes.get("lower", 0)
        
        # Check minimum touches
        min_upper = requirements.get("min_touches_upper", 2)
        min_lower = requirements.get("min_touches_lower", 2)
        
        if upper_count < min_upper:
            return False, f"Upper touches {upper_count} < {min_upper}"
        
        if lower_count < min_lower:
            return False, f"Lower touches {lower_count} < {min_lower}"
        
        # Check window size
        min_window = requirements.get("min_window_candles", 15)
        if candle_count > 0 and candle_count < min_window:
            return False, f"Window {candle_count} candles < {min_window}"
        
        # Check convergence (for wedge/triangle)
        if requirements.get("must_converge"):
            if not self._lines_converge(upper_slope, lower_slope):
                return False, "Lines do not converge"
        
        # Check parallel (for channel)
        if requirements.get("must_be_parallel"):
            if not self._lines_parallel(upper_slope, lower_slope):
                return False, "Lines are not parallel"
        
        # Check flat requirements (for triangles)
        if requirements.get("upper_must_be_flat"):
            if abs(upper_slope) > 0.00005:  # Very small tolerance
                return False, "Upper line not flat enough"
        
        if requirements.get("lower_must_be_flat"):
            if abs(lower_slope) > 0.00005:
                return False, "Lower line not flat enough"
        
        if requirements.get("must_be_horizontal"):
            if abs(upper_slope) > 0.00003 or abs(lower_slope) > 0.00003:
                return False, "Channel not horizontal enough"
        
        return True, ""
    
    def _lines_converge(self, upper_slope: float, lower_slope: float) -> bool:
        """Check if lines converge (for wedge/triangle)."""
        # Both slopes same sign = converging
        # Or one flat and other moving toward it
        if upper_slope == 0 and lower_slope == 0:
            return False
        
        # For falling wedge: both negative, lower less steep
        # For rising wedge: both positive, upper less steep
        if upper_slope * lower_slope > 0:
            return True
        
        # For triangles: opposite signs
        if upper_slope < 0 and lower_slope > 0:
            return True  # Symmetrical
        
        # One flat, other converging
        if abs(upper_slope) < 0.00005 and lower_slope != 0:
            return True  # Ascending/descending triangle
        if abs(lower_slope) < 0.00005 and upper_slope != 0:
            return True
        
        return False
    
    def _lines_parallel(self, upper_slope: float, lower_slope: float) -> bool:
        """Check if lines are parallel (for channel)."""
        if upper_slope == 0 and lower_slope == 0:
            return True
        
        if lower_slope == 0:
            return abs(upper_slope) < 0.00005
        
        ratio = upper_slope / lower_slope
        return 0.85 <= ratio <= 1.15
    
    def _check_textbook_readability(self, pattern: Dict) -> Tuple[bool, str]:
        """
        Check if pattern would be recognized by trader.
        
        RELAXED: Per user request - pattern from history is ALWAYS shown.
        We just check for severe issues, not perfection.
        """
        pattern_type = pattern.get("type", "").lower()
        
        # Get all quality scores
        touch_score = pattern.get("touch_score", 0)
        visual_score = pattern.get("visual_score", 0)
        render_quality = pattern.get("render_quality", 0)
        
        # Average check - RELAXED to 0.35 for V2 pipeline compatibility
        avg_quality = (touch_score + visual_score + render_quality) / 3
        
        if avg_quality < 0.35:
            return False, f"Average quality {avg_quality:.2f} < 0.35"
        
        # Visual breakdown checks
        visual_breakdown = pattern.get("visual_breakdown", {})
        
        # Touch balance check - SKIP for double patterns (they only have one side)
        touch_balance = visual_breakdown.get("touch_balance", 0.5)
        is_double_pattern = "double" in pattern_type
        
        if not is_double_pattern and touch_balance < 0.15:
            return False, f"Touch balance {touch_balance:.2f} < 0.15 (severely unbalanced)"
        
        # Price must respect boundaries - relaxed
        respect = visual_breakdown.get("respect", 0.5)
        if respect < 0.30:
            return False, f"Price respect {respect:.2f} < 0.30"
        
        # Lines must not cross too much inside pattern
        cleanliness = visual_breakdown.get("cleanliness", 1.0)
        if cleanliness < 0.15:
            return False, f"Cleanliness {cleanliness:.2f} < 0.15"
        
        return True, ""
    
    def _get_fallback_for_failure(self, failure_reason: str) -> str:
        """Get appropriate fallback message for failure type."""
        if "touches" in failure_reason.lower():
            return self.FALLBACK_MESSAGES["insufficient_touches"]
        if "converge" in failure_reason.lower() or "parallel" in failure_reason.lower():
            return self.FALLBACK_MESSAGES["geometry_invalid"]
        if "window" in failure_reason.lower():
            return self.FALLBACK_MESSAGES["too_small"]
        return self.FALLBACK_MESSAGES["forced_fit"]


# Singleton
_display_gate = None

def get_display_gate() -> DisplayGate:
    """Get display gate singleton."""
    global _display_gate
    if _display_gate is None:
        _display_gate = DisplayGate()
    return _display_gate
