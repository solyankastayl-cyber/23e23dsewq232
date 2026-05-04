"""
Pattern Priority System
========================

ГЛАВНАЯ ИДЕЯ:
нашли 5 паттернов → выбрали 1 ГЛАВНЫЙ → только его показали

КЛЮЧЕВОЕ ПРАВИЛО:
1 TF = 1 идея

НЕ ЛУЧШИЙ ИЗ НАЙДЕННЫХ — А ЛУЧШИЙ ИЗ ВИДИМЫХ

DOMINANCE FILTER:
- coverage < 0.2 → REJECT (убивает мусор)
- final_score < 0.6 → structure fallback
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass


# Pattern type priority (higher = more important)
PATTERN_PRIORITY = {
    "head_and_shoulders": 1.0,
    "inverse_head_and_shoulders": 1.0,
    "double_top": 0.95,
    "double_bottom": 0.95,
    "ascending_triangle": 0.9,
    "descending_triangle": 0.9,
    "symmetrical_triangle": 0.88,
    "falling_wedge": 0.85,
    "rising_wedge": 0.85,
    "bull_flag": 0.8,
    "bear_flag": 0.8,
    "ascending_channel": 0.6,
    "descending_channel": 0.6,
    "horizontal_channel": 0.55,
}

# Minimum thresholds
MIN_COVERAGE = 0.20  # Pattern must cover 20% of price range
MIN_TIME_COVERAGE = 0.15  # Pattern must cover 15% of bars
MIN_FINAL_SCORE = 0.55  # Below this = structure fallback
MIN_WINDOW_BARS = 15  # Minimum bars for pattern


@dataclass
class PatternScore:
    """Complete pattern scoring."""
    pattern_type: str
    coverage: float  # Price range coverage (0-1)
    time_coverage: float  # Bar coverage (0-1)
    dominance: float  # Combined dominance score
    geometry_score: float
    respect_score: float
    compression_score: float
    touch_score: float
    total_score: float
    type_priority: float
    final_score: float
    is_dominant: bool
    rejection_reason: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "type": self.pattern_type,
            "coverage": round(self.coverage, 3),
            "time_coverage": round(self.time_coverage, 3),
            "dominance": round(self.dominance, 3),
            "scores": {
                "geometry": round(self.geometry_score, 2),
                "respect": round(self.respect_score, 2),
                "compression": round(self.compression_score, 2),
                "touch": round(self.touch_score, 2),
            },
            "total_score": round(self.total_score, 3),
            "type_priority": round(self.type_priority, 2),
            "final_score": round(self.final_score, 3),
            "is_dominant": self.is_dominant,
            "rejection_reason": self.rejection_reason,
        }


class PatternPrioritySystem:
    """
    Selects the ONE primary pattern to display.
    
    Rules:
    1. Pattern must be DOMINANT (coverage > 0.2)
    2. Pattern must have high enough score (final > 0.55)
    3. Only ONE pattern per TF
    4. If no dominant pattern → structure fallback
    """
    
    def __init__(self, min_coverage: float = MIN_COVERAGE, min_score: float = MIN_FINAL_SCORE):
        self.min_coverage = min_coverage
        self.min_score = min_score
    
    def select_primary(
        self,
        candidates: List[Any],
        candles: List[Dict],
        timeframe: str = "1D",
    ) -> tuple:
        """
        Select the ONE primary pattern to display.
        
        Args:
            candidates: List of PatternCandidate objects
            candles: Price candles
            timeframe: Timeframe for context
        
        Returns:
            (primary_pattern, score_info, rejection_reasons)
            primary_pattern is None if no dominant pattern
        """
        if not candidates or not candles:
            return None, None, ["No candidates"]
        
        # Calculate chart dimensions
        total_range = self._calc_total_range(candles)
        total_bars = len(candles)
        
        if total_range <= 0 or total_bars < 20:
            return None, None, ["Insufficient data"]
        
        # Score all candidates
        scored = []
        rejections = []
        
        for c in candidates:
            score_result = self._score_pattern(c, candles, total_range, total_bars, timeframe)
            
            if score_result.is_dominant:
                scored.append((c, score_result))
            else:
                rejections.append(f"{c.type}: {score_result.rejection_reason}")
        
        if not scored:
            return None, None, rejections if rejections else ["No dominant patterns"]
        
        # Select best
        scored.sort(key=lambda x: x[1].final_score, reverse=True)
        best_candidate, best_score = scored[0]
        
        print(f"[PatternPriority] Selected: {best_candidate.type} (score={best_score.final_score:.2f}, coverage={best_score.coverage:.2f})")
        
        return best_candidate, best_score, rejections
    
    def _score_pattern(
        self,
        candidate: Any,
        candles: List[Dict],
        total_range: float,
        total_bars: int,
        timeframe: str,
    ) -> PatternScore:
        """Score a single pattern candidate."""
        
        pattern_type = getattr(candidate, 'type', 'unknown')
        
        # ═══════════════════════════════════════════════════════════════
        # 1. COVERAGE (most important - how big is the pattern)
        # ═══════════════════════════════════════════════════════════════
        pattern_range = self._calc_pattern_range(candidate, candles)
        coverage = pattern_range / total_range if total_range > 0 else 0
        
        # Hard reject if too small
        if coverage < self.min_coverage:
            return PatternScore(
                pattern_type=pattern_type,
                coverage=coverage,
                time_coverage=0,
                dominance=0,
                geometry_score=0,
                respect_score=0,
                compression_score=0,
                touch_score=0,
                total_score=0,
                type_priority=0,
                final_score=0,
                is_dominant=False,
                rejection_reason=f"Too small: coverage {coverage:.1%} < {self.min_coverage:.0%}",
            )
        
        # ═══════════════════════════════════════════════════════════════
        # 2. TIME COVERAGE (how much of chart does pattern span)
        # ═══════════════════════════════════════════════════════════════
        pattern_bars = self._calc_pattern_bars(candidate)
        time_coverage = pattern_bars / total_bars if total_bars > 0 else 0
        
        if pattern_bars < MIN_WINDOW_BARS:
            return PatternScore(
                pattern_type=pattern_type,
                coverage=coverage,
                time_coverage=time_coverage,
                dominance=0,
                geometry_score=0,
                respect_score=0,
                compression_score=0,
                touch_score=0,
                total_score=0,
                type_priority=0,
                final_score=0,
                is_dominant=False,
                rejection_reason=f"Too short: {pattern_bars} bars < {MIN_WINDOW_BARS}",
            )
        
        # ═══════════════════════════════════════════════════════════════
        # 3. DOMINANCE SCORE
        # ═══════════════════════════════════════════════════════════════
        # Normalize coverage to score
        if coverage < 0.15:
            coverage_score = 0.1
        elif coverage < 0.25:
            coverage_score = 0.4
        elif coverage < 0.4:
            coverage_score = 0.7
        else:
            coverage_score = 1.0
        
        dominance = coverage_score * 0.6 + time_coverage * 0.4
        
        # ═══════════════════════════════════════════════════════════════
        # 4. QUALITY SCORES
        # ═══════════════════════════════════════════════════════════════
        geometry_score = getattr(candidate, 'confidence', getattr(candidate, 'geometry_score', 0.5))
        respect_score = getattr(candidate, 'respect_score', 0.5) or 0.5
        compression_score = getattr(candidate, 'compression_score', 0.5) or 0.5
        touch_score = min(1.0, getattr(candidate, 'touch_count', 4) / 6)
        
        # ═══════════════════════════════════════════════════════════════
        # 5. TOTAL SCORE
        # ═══════════════════════════════════════════════════════════════
        total_score = (
            geometry_score * 0.25 +
            respect_score * 0.25 +
            compression_score * 0.15 +
            touch_score * 0.15 +
            dominance * 0.20
        )
        
        # ═══════════════════════════════════════════════════════════════
        # 6. TYPE PRIORITY
        # ═══════════════════════════════════════════════════════════════
        type_priority = PATTERN_PRIORITY.get(pattern_type, 0.5)
        
        # ═══════════════════════════════════════════════════════════════
        # 7. FINAL SCORE
        # ═══════════════════════════════════════════════════════════════
        final_score = total_score * type_priority
        
        # Check minimum score
        is_dominant = final_score >= self.min_score
        rejection = None if is_dominant else f"Low score: {final_score:.2f} < {self.min_score}"
        
        return PatternScore(
            pattern_type=pattern_type,
            coverage=coverage,
            time_coverage=time_coverage,
            dominance=dominance,
            geometry_score=geometry_score,
            respect_score=respect_score,
            compression_score=compression_score,
            touch_score=touch_score,
            total_score=total_score,
            type_priority=type_priority,
            final_score=final_score,
            is_dominant=is_dominant,
            rejection_reason=rejection,
        )
    
    def _calc_total_range(self, candles: List[Dict]) -> float:
        """Calculate total price range of chart."""
        if not candles:
            return 0
        highs = [c.get("high", 0) for c in candles]
        lows = [c.get("low", 0) for c in candles]
        return max(highs) - min(lows)
    
    def _calc_pattern_range(self, candidate: Any, candles: List[Dict]) -> float:
        """Calculate price range of pattern."""
        # Try to get from candidate attributes
        if hasattr(candidate, 'breakout_level') and hasattr(candidate, 'invalidation'):
            bl = getattr(candidate, 'breakout_level', 0) or 0
            inv = getattr(candidate, 'invalidation', 0) or 0
            if bl > 0 and inv > 0:
                return abs(bl - inv)
        
        # Try from points
        if hasattr(candidate, 'points'):
            points = candidate.points or {}
            all_values = []
            for key, pts in points.items():
                if isinstance(pts, list):
                    for p in pts:
                        if isinstance(p, dict):
                            all_values.append(p.get("value", 0))
            if all_values:
                return max(all_values) - min(all_values)
        
        # Try from anchor_points
        if hasattr(candidate, 'anchor_points'):
            anchors = candidate.anchor_points or {}
            all_values = []
            for key, pts in anchors.items():
                if isinstance(pts, list):
                    for p in pts:
                        if isinstance(p, (tuple, list)) and len(p) >= 2:
                            all_values.append(p[1])
                        elif isinstance(p, dict):
                            all_values.append(p.get("price", p.get("value", 0)))
            if all_values:
                return max(all_values) - min(all_values)
        
        # Fallback: use start/end indices
        start_idx = getattr(candidate, 'start_index', 0)
        end_idx = getattr(candidate, 'end_index', len(candles) - 1)
        
        if start_idx < len(candles) and end_idx < len(candles):
            subset = candles[start_idx:end_idx + 1]
            if subset:
                highs = [c.get("high", 0) for c in subset]
                lows = [c.get("low", 0) for c in subset]
                return max(highs) - min(lows)
        
        return 0
    
    def _calc_pattern_bars(self, candidate: Any) -> int:
        """Calculate number of bars pattern spans."""
        start_idx = getattr(candidate, 'start_index', 0)
        end_idx = getattr(candidate, 'end_index', start_idx + 20)
        return max(1, end_idx - start_idx)


# Singleton
_pattern_priority_system = None

def get_pattern_priority_system() -> PatternPrioritySystem:
    """Get singleton instance."""
    global _pattern_priority_system
    if _pattern_priority_system is None:
        _pattern_priority_system = PatternPrioritySystem()
    return _pattern_priority_system
