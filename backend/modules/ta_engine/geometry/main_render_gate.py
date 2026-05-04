"""
Main Render Gate
=================

Последний фильтр перед показом паттерна.

Паттерн можно показывать как main overlay ТОЛЬКО если:
1. Geometry valid
2. Shape validator passed
3. Coverage >= tf_threshold
4. Window bars >= tf_min_window
5. Touches >= 2/2
6. Cleanliness >= 0.55

ЕСЛИ НЕ ПРОХОДИТ → analysis_mode = "structure", pattern hidden
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class RenderGateResult:
    """Result of render gate check."""
    should_render: bool = False
    reason: Optional[str] = None
    
    # Individual checks
    geometry_valid: bool = False
    shape_valid: bool = False
    coverage_valid: bool = False
    window_valid: bool = False
    touches_valid: bool = False
    cleanliness_valid: bool = False
    
    # Scores used
    coverage_ratio: float = 0.0
    required_coverage: float = 0.0
    window_bars: int = 0
    required_window: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "should_render": self.should_render,
            "reason": self.reason,
            "checks": {
                "geometry": self.geometry_valid,
                "shape": self.shape_valid,
                "coverage": self.coverage_valid,
                "window": self.window_valid,
                "touches": self.touches_valid,
                "cleanliness": self.cleanliness_valid,
            },
            "values": {
                "coverage_ratio": round(self.coverage_ratio, 3),
                "required_coverage": round(self.required_coverage, 3),
                "window_bars": self.window_bars,
                "required_window": self.required_window,
            }
        }


class MainRenderGate:
    """
    Final gate before rendering pattern.
    
    STRICT RULES - must pass ALL checks to render.
    """
    
    def __init__(self):
        # TF-specific thresholds - STRICT VALUES
        self.coverage_thresholds = {
            "4H": 0.20,
            "1D": 0.25,
            "7D": 0.30,
            "1M": 0.35,
            "3M": 0.40,
            "6M": 0.45,
            "1Y": 0.50,
        }
        
        self.window_thresholds = {
            "4H": 15,
            "1D": 20,
            "7D": 15,
            "1M": 10,
            "3M": 8,
            "6M": 6,
            "1Y": 5,
        }
        
        self.min_touches = 2
        self.min_cleanliness = 0.60  # STRICT: price must respect boundaries
    
    def check(
        self,
        timeframe: str,
        geometry_contract: Optional[Dict],
        shape_validation: Optional[Dict],
        coverage_ratio: float,
        window_bars: int,
        touches_upper: int,
        touches_lower: int,
        cleanliness: float,
    ) -> RenderGateResult:
        """
        Check if pattern should be rendered.
        
        Returns RenderGateResult with detailed breakdown.
        """
        result = RenderGateResult()
        result.coverage_ratio = coverage_ratio
        result.window_bars = window_bars
        
        # Get TF thresholds
        tf_key = timeframe.upper()
        required_coverage = self.coverage_thresholds.get(tf_key, 0.20)
        required_window = self.window_thresholds.get(tf_key, 15)
        
        result.required_coverage = required_coverage
        result.required_window = required_window
        
        # 1. GEOMETRY CHECK
        if not geometry_contract:
            result.reason = "No geometry contract"
            return result
        if not geometry_contract.get("is_valid", False):
            result.reason = f"Geometry invalid: {geometry_contract.get('rejection_reason', 'unknown')}"
            return result
        result.geometry_valid = True
        
        # 2. SHAPE CHECK
        if not shape_validation:
            result.reason = "No shape validation"
            return result
        if not shape_validation.get("is_valid", False):
            result.reason = f"Shape invalid: {shape_validation.get('reason', 'unknown')}"
            return result
        result.shape_valid = True
        
        # 3. COVERAGE CHECK
        if coverage_ratio < required_coverage:
            result.reason = f"Coverage too low: {coverage_ratio:.1%} < {required_coverage:.0%}"
            return result
        result.coverage_valid = True
        
        # 4. WINDOW CHECK
        if window_bars < required_window:
            result.reason = f"Window too short: {window_bars} < {required_window} bars"
            return result
        result.window_valid = True
        
        # 5. TOUCHES CHECK
        if touches_upper < self.min_touches or touches_lower < self.min_touches:
            result.reason = f"Not enough touches: {touches_upper}/{touches_lower} < {self.min_touches}/{self.min_touches}"
            return result
        result.touches_valid = True
        
        # 6. CLEANLINESS CHECK
        if cleanliness < self.min_cleanliness:
            result.reason = f"Too dirty: cleanliness {cleanliness:.2f} < {self.min_cleanliness}"
            return result
        result.cleanliness_valid = True
        
        # ALL PASSED!
        result.should_render = True
        return result
    
    def get_coverage_threshold(self, timeframe: str) -> float:
        """Get coverage threshold for timeframe."""
        return self.coverage_thresholds.get(timeframe.upper(), 0.20)
    
    def get_window_threshold(self, timeframe: str) -> int:
        """Get window threshold for timeframe."""
        return self.window_thresholds.get(timeframe.upper(), 15)


def get_main_render_gate() -> MainRenderGate:
    return MainRenderGate()
