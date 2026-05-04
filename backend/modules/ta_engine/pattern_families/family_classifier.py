"""
Family Classifier — Routes to Correct Pattern Family
=====================================================

Instead of running ALL detectors, we:
1. Analyze geometry ONCE
2. Route to the most likely family
3. Run only that family's detector

This prevents the "fallback to loose_range" problem.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .swing_engine import SwingEngine, SwingPoint, get_swing_engine
from .geometry_engine import GeometryEngine, GeometryResult, LineRelation, get_geometry_engine
from .pattern_family_matrix import PatternFamily, PATTERNS_BY_FAMILY


@dataclass
class ClassificationResult:
    """Result of family classification."""
    primary_family: Optional[PatternFamily]
    secondary_family: Optional[PatternFamily]
    family_scores: Dict[str, float] = field(default_factory=dict)
    geometry: Optional[GeometryResult] = None
    reason: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "primary_family": self.primary_family.value if self.primary_family else None,
            "secondary_family": self.secondary_family.value if self.secondary_family else None,
            "family_scores": {k: round(v, 3) for k, v in self.family_scores.items()},
            "geometry": self.geometry.to_dict() if self.geometry else None,
            "reason": self.reason,
        }


class FamilyClassifier:
    """
    Classifies market structure into pattern families.
    
    Logic:
    1. Get swing points
    2. Analyze geometry
    3. Score each family based on geometry
    4. Return most likely family (or None if no clear pattern)
    
    KEY PRINCIPLE: Better to return None than to force a fallback
    """
    
    def __init__(self, config: Dict = None):
        config = config or {}
        
        self.min_score_threshold = config.get("min_score_threshold", 0.3)  # Below this = no pattern
        self.swing_engine = get_swing_engine(config.get("swing_config"))
        self.geometry_engine = get_geometry_engine(config)
    
    def classify(
        self,
        candles: List[Dict],
        swing_highs: List[SwingPoint] = None,
        swing_lows: List[SwingPoint] = None
    ) -> ClassificationResult:
        """
        Classify the market structure into a pattern family.
        
        Returns:
            ClassificationResult with primary/secondary family and scores
        """
        # Get swings if not provided
        if swing_highs is None or swing_lows is None:
            swing_highs, swing_lows = self.swing_engine.find_swings(candles)
        
        # Not enough data
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return ClassificationResult(
                primary_family=None,
                secondary_family=None,
                reason="insufficient_swings"
            )
        
        # Analyze geometry
        recent_highs = swing_highs[-5:]
        recent_lows = swing_lows[-5:]
        geometry = self.geometry_engine.analyze_geometry(recent_highs, recent_lows, candles)
        
        if not geometry:
            return ClassificationResult(
                primary_family=None,
                secondary_family=None,
                reason="geometry_analysis_failed"
            )
        
        # Score each family
        scores = {}
        
        scores["horizontal"] = self._score_horizontal(geometry, recent_highs, recent_lows)
        scores["converging"] = self._score_converging(geometry)
        scores["parallel"] = self._score_parallel(geometry)
        scores["swing_composite"] = self._score_swing_composite(swing_highs, swing_lows)
        scores["regime"] = self._score_regime(geometry, candles)
        
        # Find primary and secondary
        sorted_families = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        primary = None
        secondary = None
        reason = ""
        
        if sorted_families[0][1] >= self.min_score_threshold:
            primary = PatternFamily(sorted_families[0][0])
            reason = f"best_match: {sorted_families[0][0]} ({sorted_families[0][1]:.2f})"
            
            if len(sorted_families) > 1 and sorted_families[1][1] >= self.min_score_threshold:
                secondary = PatternFamily(sorted_families[1][0])
        else:
            reason = f"no_clear_pattern (best: {sorted_families[0][0]} at {sorted_families[0][1]:.2f})"
        
        return ClassificationResult(
            primary_family=primary,
            secondary_family=secondary,
            family_scores=scores,
            geometry=geometry,
            reason=reason,
        )
    
    def _score_horizontal(
        self,
        geometry: GeometryResult,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint]
    ) -> float:
        """Score for horizontal family (double/triple top/bottom, range)."""
        score = 0.0
        
        # Check if lines are horizontal
        if geometry.relation == LineRelation.HORIZONTAL:
            score += 0.4
        
        # Check for equal highs
        high_prices = [h.price for h in swing_highs]
        if high_prices:
            avg_high = sum(high_prices) / len(high_prices)
            high_variance = max(abs(p - avg_high) / avg_high for p in high_prices) if avg_high > 0 else 1
            if high_variance < 0.04:  # 4% variance
                score += 0.3
        
        # Check for equal lows
        low_prices = [l.price for l in swing_lows]
        if low_prices:
            avg_low = sum(low_prices) / len(low_prices)
            low_variance = max(abs(p - avg_low) / avg_low for p in low_prices) if avg_low > 0 else 1
            if low_variance < 0.04:
                score += 0.3
        
        return min(score, 1.0)
    
    def _score_converging(self, geometry: GeometryResult) -> float:
        """Score for converging family (triangles, wedges)."""
        score = 0.0
        
        # Must have compression
        if geometry.compression_ratio >= 0.15:
            score += 0.4
            
            # More compression = higher score
            score += min(geometry.compression_ratio, 0.4)
        
        # Lines must be converging
        if geometry.relation == LineRelation.CONVERGING:
            score += 0.2
        
        return min(score, 1.0)
    
    def _score_parallel(self, geometry: GeometryResult) -> float:
        """Score for parallel family (channels, flags)."""
        score = 0.0
        
        # Lines should be parallel
        if geometry.relation in [LineRelation.PARALLEL_UP, LineRelation.PARALLEL_DOWN]:
            score += 0.5
        
        # Should NOT have compression
        if geometry.compression_ratio < 0.1:
            score += 0.3
        
        # Symmetry helps
        score += geometry.symmetry_score * 0.2
        
        return min(score, 1.0)
    
    def _score_swing_composite(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint]
    ) -> float:
        """
        Score for swing composite family (H&S patterns).
        
        Look for the characteristic H-L-H (higher middle) or L-H-L (lower middle) sequence.
        """
        score = 0.0
        
        # Need at least 5 alternating swings for H&S
        all_swings = sorted(swing_highs + swing_lows, key=lambda s: s.index)
        
        if len(all_swings) < 5:
            return 0.0
        
        # Check for H&S sequence: H-L-H-L-H where middle H is highest
        for i in range(len(swing_highs) - 2):
            h1 = swing_highs[i]
            h2 = swing_highs[i + 1] if i + 1 < len(swing_highs) else None
            h3 = swing_highs[i + 2] if i + 2 < len(swing_highs) else None
            
            if h2 and h3:
                # Head should be highest
                if h2.price > h1.price and h2.price > h3.price:
                    # Shoulders should be similar
                    shoulder_diff = abs(h1.price - h3.price) / h1.price
                    if shoulder_diff < 0.05:  # 5% tolerance
                        score = max(score, 0.7)
        
        # Check for inverse H&S: L-H-L-H-L where middle L is lowest
        for i in range(len(swing_lows) - 2):
            l1 = swing_lows[i]
            l2 = swing_lows[i + 1] if i + 1 < len(swing_lows) else None
            l3 = swing_lows[i + 2] if i + 2 < len(swing_lows) else None
            
            if l2 and l3:
                if l2.price < l1.price and l2.price < l3.price:
                    shoulder_diff = abs(l1.price - l3.price) / l1.price
                    if shoulder_diff < 0.05:
                        score = max(score, 0.7)
        
        return min(score, 1.0)
    
    def _score_regime(self, geometry: GeometryResult, candles: List[Dict]) -> float:
        """Score for regime family (squeeze, compression states)."""
        score = 0.0
        
        # High compression = potential squeeze
        if geometry.compression_ratio >= 0.25:
            score += 0.4
        
        # Calculate ATR trend (decreasing = squeeze)
        if len(candles) >= 20:
            atr_early = self._calculate_atr(candles[:20])
            atr_late = self._calculate_atr(candles[-20:])
            
            if atr_early > 0 and atr_late < atr_early * 0.7:  # 30% reduction
                score += 0.4
        
        return min(score, 1.0)
    
    def _calculate_atr(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate ATR."""
        if len(candles) < period + 1:
            return 0
        
        tr_sum = 0
        for i in range(1, min(period + 1, len(candles))):
            high = candles[i].get("high", candles[i].get("close", 0))
            low = candles[i].get("low", candles[i].get("close", 0))
            prev_close = candles[i-1].get("close", 0)
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_sum += tr
        
        return tr_sum / period


# Singleton
_family_classifier = None

def get_family_classifier(config: Dict = None) -> FamilyClassifier:
    global _family_classifier
    if _family_classifier is None or config:
        _family_classifier = FamilyClassifier(config)
    return _family_classifier
