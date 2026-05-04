"""
Wedge Shape Validator
=====================

Validates that geometry actually forms a valid wedge.
NOT just "found something that looks like wedge".

Falling Wedge Rules:
1. Both boundaries slope DOWN
2. Lower boundary less steep than upper (convergence)
3. Compression ratio < 0.8
4. Min 2 touches per side
5. Boundaries don't cut through candle bodies

Rising Wedge Rules:
1. Both boundaries slope UP
2. Upper boundary less steep than lower (convergence)
3. Compression ratio < 0.8
4. Min 2 touches per side
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Shape validation result."""
    is_valid: bool = False
    reason: Optional[str] = None
    
    # Detailed scores
    slope_valid: bool = False
    convergence_valid: bool = False
    compression_valid: bool = False
    touches_valid: bool = False
    cleanliness_valid: bool = False
    apex_valid: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "reason": self.reason,
            "checks": {
                "slope": self.slope_valid,
                "convergence": self.convergence_valid,
                "compression": self.compression_valid,
                "touches": self.touches_valid,
                "cleanliness": self.cleanliness_valid,
                "apex": self.apex_valid,
            }
        }


class WedgeShapeValidator:
    """
    Validates wedge geometry shape.
    
    Strict rules - if any fails, wedge is rejected.
    """
    
    # Thresholds
    MAX_COMPRESSION_RATIO = 0.85  # Must compress to less than 85% of original width
    MIN_COMPRESSION_RATIO = 0.10  # Can't compress too much (or lines cross)
    MIN_TOUCHES = 2  # Per side
    MIN_CLEANLINESS = 0.55  # 55% of candles must respect boundaries
    MAX_APEX_DISTANCE_RATIO = 0.8  # Apex can't be too far in future
    
    def validate_falling_wedge(
        self,
        upper_slope: float,
        lower_slope: float,
        compression_ratio: float,
        touches_upper: int,
        touches_lower: int,
        cleanliness: float,
        apex_distance_bars: int = 0,
        window_bars: int = 1,
    ) -> ValidationResult:
        """
        Validate falling wedge geometry.
        
        Falling Wedge:
        - Both slopes negative (going down)
        - Upper slope MORE negative (steeper down)
        - Lines converging (compression)
        """
        result = ValidationResult()
        
        # 1. SLOPE CHECK: Both must go DOWN
        if upper_slope >= 0 or lower_slope >= 0:
            result.reason = f"Slopes not both negative: upper={upper_slope:.4f}, lower={lower_slope:.4f}"
            return result
        result.slope_valid = True
        
        # 2. CONVERGENCE CHECK: Upper falls faster (more negative) than lower
        # For falling wedge: upper_slope < lower_slope (both negative)
        # e.g., upper=-0.003 (steep), lower=-0.001 (shallow) → converging
        if upper_slope >= lower_slope:
            result.reason = f"Not converging: upper={upper_slope:.4f} >= lower={lower_slope:.4f}"
            return result
        result.convergence_valid = True
        
        # 3. COMPRESSION CHECK
        if compression_ratio > self.MAX_COMPRESSION_RATIO:
            result.reason = f"No compression: ratio={compression_ratio:.2f} > {self.MAX_COMPRESSION_RATIO}"
            return result
        if compression_ratio < self.MIN_COMPRESSION_RATIO:
            result.reason = f"Over-compressed: ratio={compression_ratio:.2f} < {self.MIN_COMPRESSION_RATIO}"
            return result
        result.compression_valid = True
        
        # 4. TOUCHES CHECK
        if touches_upper < self.MIN_TOUCHES or touches_lower < self.MIN_TOUCHES:
            result.reason = f"Not enough touches: upper={touches_upper}, lower={touches_lower}"
            return result
        result.touches_valid = True
        
        # 5. CLEANLINESS CHECK
        if cleanliness < self.MIN_CLEANLINESS:
            result.reason = f"Dirty geometry: cleanliness={cleanliness:.2f} < {self.MIN_CLEANLINESS}"
            return result
        result.cleanliness_valid = True
        
        # 6. APEX CHECK (optional but good)
        if apex_distance_bars > 0 and window_bars > 0:
            apex_ratio = apex_distance_bars / window_bars
            if apex_ratio > self.MAX_APEX_DISTANCE_RATIO:
                result.reason = f"Apex too far: {apex_ratio:.2f} > {self.MAX_APEX_DISTANCE_RATIO}"
                return result
        result.apex_valid = True
        
        # ALL PASSED
        result.is_valid = True
        return result
    
    def validate_rising_wedge(
        self,
        upper_slope: float,
        lower_slope: float,
        compression_ratio: float,
        touches_upper: int,
        touches_lower: int,
        cleanliness: float,
        apex_distance_bars: int = 0,
        window_bars: int = 1,
    ) -> ValidationResult:
        """
        Validate rising wedge geometry.
        
        Rising Wedge:
        - Both slopes positive (going up)
        - Lower slope MORE positive (steeper up)
        - Lines converging (compression)
        """
        result = ValidationResult()
        
        # 1. SLOPE CHECK: Both must go UP
        if upper_slope <= 0 or lower_slope <= 0:
            result.reason = f"Slopes not both positive: upper={upper_slope:.4f}, lower={lower_slope:.4f}"
            return result
        result.slope_valid = True
        
        # 2. CONVERGENCE CHECK: Lower rises faster (more positive) than upper
        # For rising wedge: lower_slope > upper_slope (both positive)
        # e.g., lower=0.003 (steep), upper=0.001 (shallow) → converging
        if lower_slope <= upper_slope:
            result.reason = f"Not converging: lower={lower_slope:.4f} <= upper={upper_slope:.4f}"
            return result
        result.convergence_valid = True
        
        # 3. COMPRESSION CHECK
        if compression_ratio > self.MAX_COMPRESSION_RATIO:
            result.reason = f"No compression: ratio={compression_ratio:.2f} > {self.MAX_COMPRESSION_RATIO}"
            return result
        if compression_ratio < self.MIN_COMPRESSION_RATIO:
            result.reason = f"Over-compressed: ratio={compression_ratio:.2f} < {self.MIN_COMPRESSION_RATIO}"
            return result
        result.compression_valid = True
        
        # 4. TOUCHES CHECK
        if touches_upper < self.MIN_TOUCHES or touches_lower < self.MIN_TOUCHES:
            result.reason = f"Not enough touches: upper={touches_upper}, lower={touches_lower}"
            return result
        result.touches_valid = True
        
        # 5. CLEANLINESS CHECK
        if cleanliness < self.MIN_CLEANLINESS:
            result.reason = f"Dirty geometry: cleanliness={cleanliness:.2f} < {self.MIN_CLEANLINESS}"
            return result
        result.cleanliness_valid = True
        
        # 6. APEX CHECK
        if apex_distance_bars > 0 and window_bars > 0:
            apex_ratio = apex_distance_bars / window_bars
            if apex_ratio > self.MAX_APEX_DISTANCE_RATIO:
                result.reason = f"Apex too far: {apex_ratio:.2f} > {self.MAX_APEX_DISTANCE_RATIO}"
                return result
        result.apex_valid = True
        
        # ALL PASSED
        result.is_valid = True
        return result
    
    def validate(
        self,
        pattern_type: str,
        upper_slope: float,
        lower_slope: float,
        compression_ratio: float,
        touches_upper: int = 2,
        touches_lower: int = 2,
        cleanliness: float = 0.6,
        apex_distance_bars: int = 0,
        window_bars: int = 1,
    ) -> ValidationResult:
        """Validate wedge by type."""
        if pattern_type == "falling_wedge":
            return self.validate_falling_wedge(
                upper_slope, lower_slope, compression_ratio,
                touches_upper, touches_lower, cleanliness,
                apex_distance_bars, window_bars
            )
        elif pattern_type == "rising_wedge":
            return self.validate_rising_wedge(
                upper_slope, lower_slope, compression_ratio,
                touches_upper, touches_lower, cleanliness,
                apex_distance_bars, window_bars
            )
        else:
            return ValidationResult(reason=f"Unknown wedge type: {pattern_type}")


def get_wedge_shape_validator() -> WedgeShapeValidator:
    return WedgeShapeValidator()
