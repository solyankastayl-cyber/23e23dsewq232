"""
Visual Quality Engine - Pattern Quality Filter
===============================================

Kills garbage patterns that "technically fit" but look like trash.

KEY PRINCIPLE:
If a pattern doesn't read in 1-2 seconds → it doesn't exist.

Checks:
1. Touch Balance (upper vs lower)
2. Symmetry (convergence for wedge, parallel for channel)
3. Price Respect (actual reactions, not just touches)
4. Window Clarity (not too small, not noise)
5. Cleanliness (no overlaps, no crossed lines)
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math


@dataclass
class VisualQualityResult:
    """Result of visual quality validation."""
    passed: bool
    score: float
    breakdown: Dict[str, float]
    rejection_reason: Optional[str] = None


class VisualQualityEngine:
    """
    Validates patterns for visual quality.
    
    Kills patterns that look like garbage.
    """
    
    # Minimum thresholds
    MIN_TOUCHES_PER_SIDE = 2
    MIN_WINDOW_SIZE = 15  # candles
    MIN_VISUAL_SCORE = 0.65
    
    # Weights for scoring
    WEIGHTS = {
        "touch_balance": 0.25,
        "symmetry": 0.20,
        "respect": 0.25,
        "clarity": 0.15,
        "cleanliness": 0.15,
    }
    
    def __init__(self):
        pass
    
    def validate(self, pattern: Dict) -> VisualQualityResult:
        """
        Validate pattern visual quality.
        
        Returns:
            VisualQualityResult with pass/fail and breakdown
        """
        # ═══════════════════════════════════════════════════════════════
        # HARD REJECTION — immediate kill
        # ═══════════════════════════════════════════════════════════════
        rejection = self._hard_reject(pattern)
        if rejection:
            return VisualQualityResult(
                passed=False,
                score=0.0,
                breakdown={},
                rejection_reason=rejection
            )
        
        # ═══════════════════════════════════════════════════════════════
        # SCORING — soft validation
        # ═══════════════════════════════════════════════════════════════
        breakdown = {
            "touch_balance": self._score_touch_balance(pattern),
            "symmetry": self._score_symmetry(pattern),
            "respect": self._score_price_respect(pattern),
            "clarity": self._score_window_clarity(pattern),
            "cleanliness": self._score_cleanliness(pattern),
        }
        
        # Calculate weighted score
        score = sum(
            breakdown[k] * self.WEIGHTS[k]
            for k in breakdown
        )
        
        # Pass/fail
        passed = score >= self.MIN_VISUAL_SCORE
        
        return VisualQualityResult(
            passed=passed,
            score=round(score, 3),
            breakdown={k: round(v, 3) for k, v in breakdown.items()},
            rejection_reason=None if passed else f"Visual score {score:.2f} < {self.MIN_VISUAL_SCORE}"
        )
    
    # ═══════════════════════════════════════════════════════════════
    # HARD REJECTION
    # ═══════════════════════════════════════════════════════════════
    
    def _hard_reject(self, pattern: Dict) -> Optional[str]:
        """
        Hard rejection rules. If any fail, pattern is killed.
        
        Returns rejection reason or None.
        """
        # Get touches
        touches = pattern.get("touches", {})
        upper_touches = touches.get("upper", [])
        lower_touches = touches.get("lower", [])
        
        # Rule 1: Minimum touches per side
        if len(upper_touches) < self.MIN_TOUCHES_PER_SIDE:
            return f"Not enough upper touches: {len(upper_touches)} < {self.MIN_TOUCHES_PER_SIDE}"
        
        if len(lower_touches) < self.MIN_TOUCHES_PER_SIDE:
            return f"Not enough lower touches: {len(lower_touches)} < {self.MIN_TOUCHES_PER_SIDE}"
        
        # Rule 2: Minimum window size
        window = pattern.get("window", {})
        window_size = window.get("candle_count", 0)
        if window_size < self.MIN_WINDOW_SIZE:
            return f"Window too small: {window_size} < {self.MIN_WINDOW_SIZE} candles"
        
        # Rule 3: Pattern-specific geometry
        pattern_type = pattern.get("type", "")
        
        # Wedge must converge
        if "wedge" in pattern_type.lower():
            if not self._check_convergence(pattern):
                return "Wedge lines do not converge"
        
        # Channel must be parallel
        if "channel" in pattern_type.lower():
            if not self._check_parallel(pattern):
                return "Channel lines are not parallel enough"
        
        # Triangle checks
        if "triangle" in pattern_type.lower():
            if not self._check_triangle_geometry(pattern):
                return "Triangle geometry invalid"
        
        return None
    
    def _check_convergence(self, pattern: Dict) -> bool:
        """Check if wedge lines converge."""
        slopes = pattern.get("slopes", {})
        upper_slope = slopes.get("upper", 0)
        lower_slope = slopes.get("lower", 0)
        
        # Both slopes should be same direction (both negative for falling, both positive for rising)
        # But converging means they're getting closer
        
        # For falling wedge: both negative, lower less steep
        # For rising wedge: both positive, upper less steep
        
        if upper_slope == 0 and lower_slope == 0:
            return False
        
        # Simple check: slopes should have same sign (both going same direction)
        # And magnitude difference should show convergence
        if upper_slope * lower_slope > 0:
            # Same direction
            diff = abs(upper_slope) - abs(lower_slope)
            # There should be some difference (convergence)
            return abs(diff) > 0.00001
        
        # Different signs could still converge
        return True
    
    def _check_parallel(self, pattern: Dict) -> bool:
        """Check if channel lines are parallel enough."""
        slopes = pattern.get("slopes", {})
        upper_slope = slopes.get("upper", 0)
        lower_slope = slopes.get("lower", 0)
        
        if upper_slope == 0 and lower_slope == 0:
            return True  # Horizontal channel
        
        # Allow 15% difference in slope for "parallel"
        if upper_slope == 0 or lower_slope == 0:
            return abs(upper_slope - lower_slope) < 0.0001
        
        ratio = upper_slope / lower_slope if lower_slope != 0 else 0
        return 0.85 <= ratio <= 1.15
    
    def _check_triangle_geometry(self, pattern: Dict) -> bool:
        """Check triangle-specific geometry."""
        pattern_type = pattern.get("type", "")
        slopes = pattern.get("slopes", {})
        upper_slope = slopes.get("upper", 0)
        lower_slope = slopes.get("lower", 0)
        
        if "ascending" in pattern_type:
            # Upper should be flat (near 0), lower rising (positive)
            return abs(upper_slope) < 0.0001 or lower_slope > 0
        
        if "descending" in pattern_type:
            # Lower should be flat (near 0), upper falling (negative)
            return abs(lower_slope) < 0.0001 or upper_slope < 0
        
        if "symmetrical" in pattern_type:
            # Converging from both directions
            return upper_slope < 0 and lower_slope > 0
        
        return True
    
    # ═══════════════════════════════════════════════════════════════
    # SCORING FUNCTIONS
    # ═══════════════════════════════════════════════════════════════
    
    def _score_touch_balance(self, pattern: Dict) -> float:
        """
        Score touch balance between upper and lower.
        
        Perfect: 2:2, 3:3
        Good: 2:3, 3:4
        Weak: 2:5, 5:2
        """
        touches = pattern.get("touches", {})
        upper = len(touches.get("upper", []))
        lower = len(touches.get("lower", []))
        
        if upper < 2 or lower < 2:
            return 0.0
        
        diff = abs(upper - lower)
        
        if diff == 0:
            return 1.0
        elif diff == 1:
            return 0.85
        elif diff == 2:
            return 0.6
        else:
            return 0.4
    
    def _score_symmetry(self, pattern: Dict) -> float:
        """
        Score geometric symmetry.
        
        Wedge: convergence quality
        Channel: parallelism
        Triangle: appropriate shape
        """
        pattern_type = pattern.get("type", "")
        slopes = pattern.get("slopes", {})
        upper_slope = slopes.get("upper", 0)
        lower_slope = slopes.get("lower", 0)
        
        if "wedge" in pattern_type.lower():
            # Convergence score
            if upper_slope * lower_slope <= 0:
                return 0.3  # Not converging properly
            
            # Both should be same direction with different magnitudes
            diff = abs(abs(upper_slope) - abs(lower_slope))
            if diff > 0.0001:
                return min(1.0, 0.5 + diff * 1000)
            return 0.5
        
        elif "channel" in pattern_type.lower():
            # Parallelism score
            if upper_slope == 0 and lower_slope == 0:
                return 1.0
            
            if lower_slope == 0:
                return 0.3 if abs(upper_slope) < 0.0001 else 0.5
            
            ratio = upper_slope / lower_slope
            if 0.9 <= ratio <= 1.1:
                return 1.0
            elif 0.8 <= ratio <= 1.2:
                return 0.75
            elif 0.7 <= ratio <= 1.3:
                return 0.5
            else:
                return 0.3
        
        elif "triangle" in pattern_type.lower():
            # Triangle shape appropriateness
            if "ascending" in pattern_type:
                # Upper should be flat
                flatness = 1.0 - min(1.0, abs(upper_slope) * 10000)
                return max(0.3, flatness)
            
            elif "descending" in pattern_type:
                # Lower should be flat
                flatness = 1.0 - min(1.0, abs(lower_slope) * 10000)
                return max(0.3, flatness)
            
            elif "symmetrical" in pattern_type:
                # Both converging
                if upper_slope < 0 and lower_slope > 0:
                    return 0.9
                return 0.4
        
        return 0.5
    
    def _score_price_respect(self, pattern: Dict) -> float:
        """
        Score how much price respects the boundaries.
        
        Best: all touches have reactions (bounces)
        Worst: touches with no reaction
        """
        touches = pattern.get("touches", {})
        upper_touches = touches.get("upper", [])
        lower_touches = touches.get("lower", [])
        
        all_touches = upper_touches + lower_touches
        if not all_touches:
            return 0.0
        
        # Count reactions
        reactions = 0
        for touch in all_touches:
            if isinstance(touch, dict):
                if touch.get("reaction") or touch.get("is_reaction"):
                    reactions += 1
            else:
                # Touch might be a simple value
                pass
        
        # If no reaction info, estimate based on touch quality
        if reactions == 0:
            # Fall back to touch score if available
            touch_score = pattern.get("touch_score", 0.5)
            return touch_score
        
        ratio = reactions / len(all_touches)
        return ratio
    
    def _score_window_clarity(self, pattern: Dict) -> float:
        """
        Score pattern window clarity.
        
        Too small = noise
        Too large = possibly stale
        """
        window = pattern.get("window", {})
        candle_count = window.get("candle_count", 0)
        
        if candle_count < 15:
            return 0.2
        elif candle_count < 25:
            return 0.5
        elif candle_count < 50:
            return 0.8
        elif candle_count < 100:
            return 1.0
        elif candle_count < 150:
            return 0.9
        else:
            return 0.7  # Very old pattern
    
    def _score_cleanliness(self, pattern: Dict) -> float:
        """
        Score pattern cleanliness.
        
        Checks for:
        - Lines crossing inside pattern
        - Overlaps with other structures
        """
        # Check if lines cross inside the pattern window
        render = pattern.get("render", {})
        boundaries = render.get("boundaries", [])
        
        if len(boundaries) < 2:
            return 0.5
        
        # Simple check: do boundaries cross?
        upper = None
        lower = None
        for b in boundaries:
            if "upper" in b.get("id", "").lower():
                upper = b
            elif "lower" in b.get("id", "").lower():
                lower = b
        
        if upper and lower:
            # Check if they cross within the window
            # Upper should always be above lower at any given time
            upper_start = upper.get("y1", 0)
            upper_end = upper.get("y2", 0)
            lower_start = lower.get("y1", 0)
            lower_end = lower.get("y2", 0)
            
            # If upper ever goes below lower, that's a cross
            if upper_start < lower_start or upper_end < lower_end:
                return 0.2  # Lines crossed
        
        return 1.0


# Singleton
_visual_quality_engine = None

def get_visual_quality_engine() -> VisualQualityEngine:
    """Get visual quality engine singleton."""
    global _visual_quality_engine
    if _visual_quality_engine is None:
        _visual_quality_engine = VisualQualityEngine()
    return _visual_quality_engine
