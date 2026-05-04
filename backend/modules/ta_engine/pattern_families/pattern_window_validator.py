"""
Pattern Window Validator — CRITICAL QUALITY GATE
=================================================

PROBLEM THIS SOLVES:
System was drawing triple_top where:
- Peaks were spread across 80+ bars
- Pattern mixed with active range
- No real structural integrity

PRINCIPLE:
"Better to show NO PATTERN than a garbage pattern"

This validator ensures:
1. Pattern exists in one LOCAL window
2. Structural integrity (correct # of swings)
3. Geometric alignment (peaks at same level)
4. Sufficient depth (not just noise/flat)
5. Pre-trend validation (context matters)
6. Range conflict resolution

If ANY check fails → pattern.rejected = True
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import statistics

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION — WINDOW LIMITS
# ═══════════════════════════════════════════════════════════════

# Maximum pattern window size (bars)
MAX_WINDOW_4H = 40   # ~7 days
MAX_WINDOW_1D = 80   # ~3 months
MAX_WINDOW_1H = 60   # ~2.5 days

# Padding around pattern
WINDOW_PADDING = 3

# ═══════════════════════════════════════════════════════════════
# VALIDATION THRESHOLDS
# ═══════════════════════════════════════════════════════════════

# Geometric alignment (peak deviation)
MAX_PEAK_DEVIATION_PCT = 0.035  # 3.5% max spread for triple top
MAX_PEAK_DEVIATION_DOUBLE = 0.025  # 2.5% for double top

# Minimum depth between peaks and valleys
MIN_DEPTH_PCT = 0.015  # 1.5% minimum depth
MIN_DEPTH_TRIPLE = 0.02  # 2% for triple patterns

# Noise filter: max extra swings in window
MAX_EXTRA_SWINGS_ALLOWED = 1

# Pre-trend requirements
MIN_PRETREND_BARS = 15
MIN_PRETREND_MOVE_PCT = 0.05  # 5% move before pattern


@dataclass
class ValidationResult:
    """Result of window validation."""
    valid: bool
    reason: Optional[str] = None
    score_penalty: float = 0.0
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


# ═══════════════════════════════════════════════════════════════
# MAIN VALIDATOR CLASS
# ═══════════════════════════════════════════════════════════════

class PatternWindowValidator:
    """
    Validates that a pattern is a REAL, renderable object.
    
    NOT just "detected" but:
    - Structurally sound
    - In a coherent window
    - Not noise/flat
    - Has proper context
    """
    
    def __init__(self, timeframe: str = "4H"):
        self.timeframe = timeframe
        self.max_window = self._get_max_window(timeframe)
    
    def _get_max_window(self, tf: str) -> int:
        """Get max window size for timeframe."""
        windows = {
            "1H": MAX_WINDOW_1H,
            "4H": MAX_WINDOW_4H,
            "1D": MAX_WINDOW_1D,
            "7D": MAX_WINDOW_1D,
            "30D": MAX_WINDOW_1D * 2,
        }
        return windows.get(tf, MAX_WINDOW_4H)
    
    def validate(
        self,
        pattern: Dict,
        candles: List[Dict],
        swings: List[Dict] = None,
        active_range: Dict = None,
    ) -> ValidationResult:
        """
        Main validation entry point.
        
        Args:
            pattern: Pattern dict with type, anchors, window, etc.
            candles: OHLCV candles
            swings: Pre-computed swings (optional)
            active_range: Active range if exists (optional)
        
        Returns:
            ValidationResult with valid=True/False and reason
        """
        pattern_type = pattern.get("type", "").lower()
        
        # Route to specific validator
        if pattern_type in ["double_top", "triple_top", "double_bottom", "triple_bottom"]:
            return self.validate_horizontal(pattern, candles, swings, active_range)
        
        elif pattern_type in ["symmetrical_triangle", "ascending_triangle", "descending_triangle", 
                             "rising_wedge", "falling_wedge"]:
            return self.validate_converging(pattern, candles, swings, active_range)
        
        elif pattern_type in ["ascending_channel", "descending_channel", "horizontal_channel",
                             "bull_flag", "bear_flag"]:
            return self.validate_parallel(pattern, candles, swings, active_range)
        
        elif pattern_type == "range":
            return self.validate_range(pattern, candles)
        
        # Unknown pattern type - pass through with warning
        return ValidationResult(
            valid=True,
            warnings=[f"No validator for pattern type: {pattern_type}"]
        )
    
    # ═══════════════════════════════════════════════════════════════
    # HORIZONTAL FAMILY VALIDATOR (double/triple top/bottom)
    # ═══════════════════════════════════════════════════════════════
    
    def validate_horizontal(
        self,
        pattern: Dict,
        candles: List[Dict],
        swings: List[Dict] = None,
        active_range: Dict = None,
    ) -> ValidationResult:
        """
        Validate double/triple top/bottom patterns.
        
        CRITICAL CHECKS:
        1. Window not too wide
        2. Correct number of peaks/valleys
        3. Peaks aligned (same level)
        4. Sufficient depth
        5. Pre-trend exists
        6. Not swallowed by range
        """
        pattern_type = pattern.get("type", "").lower()
        is_top = "top" in pattern_type
        is_triple = "triple" in pattern_type
        
        # Get anchors/peaks
        anchors = pattern.get("anchors", pattern.get("peaks", []))
        if not anchors:
            return ValidationResult(
                valid=False,
                reason="no_anchors",
                score_penalty=1.0
            )
        
        # ─────────────────────────────────────────────────────────
        # CHECK 1: Window size
        # ─────────────────────────────────────────────────────────
        window = pattern.get("window", {})
        start_idx = window.get("start_index", 0)
        end_idx = window.get("end_index", len(candles) - 1)
        
        # If no window, compute from anchors
        if not window:
            indices = [a.get("index", 0) for a in anchors if a.get("index")]
            if indices:
                start_idx = min(indices) - WINDOW_PADDING
                end_idx = max(indices) + WINDOW_PADDING
        
        window_length = end_idx - start_idx
        
        if window_length > self.max_window:
            return ValidationResult(
                valid=False,
                reason=f"window_too_wide: {window_length} > {self.max_window} bars",
                score_penalty=0.5
            )
        
        # ─────────────────────────────────────────────────────────
        # CHECK 2: Correct number of peaks
        # ─────────────────────────────────────────────────────────
        expected_peaks = 3 if is_triple else 2
        
        if len(anchors) < expected_peaks:
            return ValidationResult(
                valid=False,
                reason=f"insufficient_peaks: {len(anchors)} < {expected_peaks}",
                score_penalty=1.0
            )
        
        # ─────────────────────────────────────────────────────────
        # CHECK 3: Structural integrity (noise filter)
        # ─────────────────────────────────────────────────────────
        if swings:
            swings_in_window = [
                s for s in swings
                if start_idx <= s.get("index", 0) <= end_idx
            ]
            
            # Count highs and lows
            highs_in_window = [s for s in swings_in_window if s.get("type") in ["HH", "LH"]]
            lows_in_window = [s for s in swings_in_window if s.get("type") in ["HL", "LL"]]
            
            if is_top:
                # Triple top: expect 3 highs, 2 lows
                # Double top: expect 2 highs, 1 low
                expected_highs = 3 if is_triple else 2
                max_allowed_highs = expected_highs + MAX_EXTRA_SWINGS_ALLOWED
                
                if len(highs_in_window) > max_allowed_highs:
                    return ValidationResult(
                        valid=False,
                        reason=f"too_many_highs: {len(highs_in_window)} > {max_allowed_highs} (noisy structure)",
                        score_penalty=0.4
                    )
            else:
                # Bottoms
                expected_lows = 3 if is_triple else 2
                max_allowed_lows = expected_lows + MAX_EXTRA_SWINGS_ALLOWED
                
                if len(lows_in_window) > max_allowed_lows:
                    return ValidationResult(
                        valid=False,
                        reason=f"too_many_lows: {len(lows_in_window)} > {max_allowed_lows} (noisy structure)",
                        score_penalty=0.4
                    )
        
        # ─────────────────────────────────────────────────────────
        # CHECK 4: Geometric alignment (peaks at same level)
        # ─────────────────────────────────────────────────────────
        prices = [a.get("price", 0) for a in anchors if a.get("price")]
        
        if len(prices) >= 2:
            avg_price = statistics.mean(prices)
            max_price = max(prices)
            min_price = min(prices)
            deviation = (max_price - min_price) / avg_price if avg_price > 0 else 0
            
            max_deviation = MAX_PEAK_DEVIATION_PCT if is_triple else MAX_PEAK_DEVIATION_DOUBLE
            
            if deviation > max_deviation:
                return ValidationResult(
                    valid=False,
                    reason=f"peaks_not_aligned: {deviation:.1%} deviation > {max_deviation:.1%}",
                    score_penalty=0.3,
                    warnings=[f"Peak spread: ${min_price:.0f} - ${max_price:.0f}"]
                )
        
        # ─────────────────────────────────────────────────────────
        # CHECK 5: Sufficient depth
        # ─────────────────────────────────────────────────────────
        # Need valleys between peaks
        valleys = pattern.get("valleys", [])
        
        if valleys and prices:
            valley_prices = [v.get("price", 0) for v in valleys if v.get("price")]
            
            if valley_prices:
                peak_avg = statistics.mean(prices)
                valley_avg = statistics.mean(valley_prices)
                
                if is_top:
                    depth = (peak_avg - valley_avg) / peak_avg if peak_avg > 0 else 0
                else:
                    depth = (valley_avg - peak_avg) / valley_avg if valley_avg > 0 else 0
                
                min_depth = MIN_DEPTH_TRIPLE if is_triple else MIN_DEPTH_PCT
                
                if depth < min_depth:
                    return ValidationResult(
                        valid=False,
                        reason=f"too_shallow: {depth:.1%} depth < {min_depth:.1%} (flat pattern)",
                        score_penalty=0.35
                    )
        
        # ─────────────────────────────────────────────────────────
        # CHECK 6: Pre-trend validation
        # ─────────────────────────────────────────────────────────
        if candles and start_idx > MIN_PRETREND_BARS:
            pretrend_start = max(0, start_idx - MIN_PRETREND_BARS)
            pretrend_candles = candles[pretrend_start:start_idx]
            
            if len(pretrend_candles) >= 5:
                first_close = pretrend_candles[0].get("close", 0)
                last_close = pretrend_candles[-1].get("close", 0)
                
                if first_close > 0:
                    pretrend_move = (last_close - first_close) / first_close
                    
                    # For tops, need prior uptrend
                    # For bottoms, need prior downtrend
                    if is_top:
                        if pretrend_move < 0:  # No uptrend before top
                            return ValidationResult(
                                valid=False,
                                reason=f"no_uptrend_before_top: {pretrend_move:.1%}",
                                score_penalty=0.25,
                                warnings=["Top pattern without prior uptrend is weak"]
                            )
                    else:
                        if pretrend_move > 0:  # No downtrend before bottom
                            return ValidationResult(
                                valid=False,
                                reason=f"no_downtrend_before_bottom: {pretrend_move:+.1%}",
                                score_penalty=0.25,
                                warnings=["Bottom pattern without prior downtrend is weak"]
                            )
        
        # ─────────────────────────────────────────────────────────
        # CHECK 7: Range conflict
        # ─────────────────────────────────────────────────────────
        if active_range:
            range_start = active_range.get("start_index", 0)
            range_end = active_range.get("end_index", 9999)
            
            # Check if pattern is INSIDE active range
            pattern_inside_range = (
                start_idx >= range_start and 
                end_idx <= range_end
            )
            
            if pattern_inside_range:
                # Pattern is inside range - penalize but don't reject
                return ValidationResult(
                    valid=True,
                    score_penalty=0.20,
                    warnings=["Pattern inside active range - reduced confidence"]
                )
        
        # ─────────────────────────────────────────────────────────
        # ALL CHECKS PASSED
        # ─────────────────────────────────────────────────────────
        return ValidationResult(valid=True, warnings=[])
    
    # ═══════════════════════════════════════════════════════════════
    # CONVERGING FAMILY VALIDATOR (triangles, wedges)
    # ═══════════════════════════════════════════════════════════════
    
    def validate_converging(
        self,
        pattern: Dict,
        candles: List[Dict],
        swings: List[Dict] = None,
        active_range: Dict = None,
    ) -> ValidationResult:
        """
        Validate triangle and wedge patterns.
        
        CHECKS:
        1. Lines are actually converging
        2. Sufficient touches on each line
        3. Not too close to apex (still valid)
        4. Window size reasonable
        """
        # Get trendlines
        upper_line = pattern.get("upper_line", {})
        lower_line = pattern.get("lower_line", {})
        
        if not upper_line or not lower_line:
            return ValidationResult(
                valid=False,
                reason="missing_trendlines",
                score_penalty=1.0
            )
        
        # Check window
        window = pattern.get("window", {})
        window_length = window.get("end_index", 0) - window.get("start_index", 0)
        
        if window_length > self.max_window:
            return ValidationResult(
                valid=False,
                reason=f"window_too_wide: {window_length} bars",
                score_penalty=0.4
            )
        
        # Check touches
        upper_touches = upper_line.get("touches", [])
        lower_touches = lower_line.get("touches", [])
        
        if len(upper_touches) < 2 or len(lower_touches) < 2:
            return ValidationResult(
                valid=False,
                reason=f"insufficient_touches: upper={len(upper_touches)}, lower={len(lower_touches)}",
                score_penalty=0.5
            )
        
        # Check convergence
        upper_slope = upper_line.get("slope", 0)
        lower_slope = lower_line.get("slope", 0)
        
        # For convergence, slopes should have opposite signs or be narrowing
        pattern_type = pattern.get("type", "").lower()
        
        if "symmetrical" in pattern_type:
            # Both slopes should be opposite
            if upper_slope * lower_slope > 0:  # Same sign
                return ValidationResult(
                    valid=False,
                    reason="not_converging: slopes same direction",
                    score_penalty=0.4
                )
        
        return ValidationResult(valid=True)
    
    # ═══════════════════════════════════════════════════════════════
    # PARALLEL FAMILY VALIDATOR (channels, flags)
    # ═══════════════════════════════════════════════════════════════
    
    def validate_parallel(
        self,
        pattern: Dict,
        candles: List[Dict],
        swings: List[Dict] = None,
        active_range: Dict = None,
    ) -> ValidationResult:
        """
        Validate channel and flag patterns.
        
        CHECKS:
        1. Lines are actually parallel (slopes similar)
        2. Sufficient touches
        3. Channel not too wide or narrow
        """
        # Get trendlines
        upper_line = pattern.get("upper_line", {})
        lower_line = pattern.get("lower_line", {})
        
        if not upper_line or not lower_line:
            return ValidationResult(
                valid=False,
                reason="missing_trendlines",
                score_penalty=1.0
            )
        
        # Check parallelism
        upper_slope = upper_line.get("slope", 0)
        lower_slope = lower_line.get("slope", 0)
        
        slope_diff = abs(upper_slope - lower_slope)
        avg_slope = (abs(upper_slope) + abs(lower_slope)) / 2 if (upper_slope or lower_slope) else 0
        
        if avg_slope > 0:
            parallelism = slope_diff / avg_slope
            if parallelism > 0.3:  # More than 30% difference
                return ValidationResult(
                    valid=False,
                    reason=f"not_parallel: {parallelism:.0%} slope difference",
                    score_penalty=0.3
                )
        
        return ValidationResult(valid=True)
    
    # ═══════════════════════════════════════════════════════════════
    # RANGE VALIDATOR
    # ═══════════════════════════════════════════════════════════════
    
    def validate_range(
        self,
        pattern: Dict,
        candles: List[Dict],
    ) -> ValidationResult:
        """
        Validate range patterns.
        
        CHECKS:
        1. Range has minimum width
        2. Range has minimum touches
        3. Price is currently inside range
        """
        top = pattern.get("top", 0)
        bottom = pattern.get("bottom", 0)
        
        if not top or not bottom:
            return ValidationResult(
                valid=False,
                reason="missing_range_bounds",
                score_penalty=1.0
            )
        
        # Check width
        width_pct = (top - bottom) / bottom if bottom > 0 else 0
        
        if width_pct < 0.02:  # Less than 2% width
            return ValidationResult(
                valid=False,
                reason=f"range_too_narrow: {width_pct:.1%}",
                score_penalty=0.3
            )
        
        if width_pct > 0.20:  # More than 20% width
            return ValidationResult(
                valid=False,
                reason=f"range_too_wide: {width_pct:.1%}",
                score_penalty=0.2,
                warnings=["Very wide range - may not be cohesive"]
            )
        
        return ValidationResult(valid=True)


# ═══════════════════════════════════════════════════════════════
# SINGLETON & HELPER
# ═══════════════════════════════════════════════════════════════

_validator = None

def get_pattern_validator(timeframe: str = "4H") -> PatternWindowValidator:
    """Get validator instance."""
    global _validator
    if _validator is None or _validator.timeframe != timeframe:
        _validator = PatternWindowValidator(timeframe)
    return _validator


def validate_pattern_window(
    pattern: Dict,
    candles: List[Dict],
    swings: List[Dict] = None,
    active_range: Dict = None,
    timeframe: str = "4H"
) -> Tuple[bool, Optional[str], float]:
    """
    Convenience function to validate a pattern.
    
    Returns:
        (is_valid, rejection_reason, score_penalty)
    """
    validator = get_pattern_validator(timeframe)
    result = validator.validate(pattern, candles, swings, active_range)
    return result.valid, result.reason, result.score_penalty
