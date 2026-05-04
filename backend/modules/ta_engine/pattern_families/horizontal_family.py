"""
Horizontal Family Detector
==========================

CLOSES 6 PATTERNS AT ONCE:
- double_top
- double_bottom
- triple_top
- triple_bottom
- range
- rectangle

ALL use the same geometric primitive: EQUAL PRICES
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .swing_engine import SwingEngine, SwingPoint, get_swing_engine
from .geometry_engine import GeometryEngine, get_geometry_engine
from .pattern_family_matrix import PatternFamily, PatternBias, PATTERN_FAMILY_MATRIX


@dataclass
class HorizontalPattern:
    """Detected horizontal pattern."""
    type: str
    family: str = "horizontal"
    bias: str = "neutral"
    confidence: float = 0.0
    
    # Key levels for rendering
    peaks: List[Dict] = None      # For tops
    troughs: List[Dict] = None    # For bottoms
    neckline: float = None
    resistance: float = None
    support: float = None
    
    # For targets
    height: float = None
    target: float = None
    
    # Metadata
    start_index: int = None
    end_index: int = None
    touches_top: int = 0
    touches_bottom: int = 0
    
    # WINDOW INFO (for validator)
    window: Dict = None           # {start_index, end_index, length}
    anchors: List[Dict] = None    # Same as peaks for tops, troughs for bottoms
    valleys: List[Dict] = None    # Valleys between peaks (for tops)
    
    def __post_init__(self):
        # Build window from indices
        if self.window is None and self.start_index is not None and self.end_index is not None:
            self.window = {
                "start_index": self.start_index,
                "end_index": self.end_index,
                "length": self.end_index - self.start_index
            }
        
        # Build anchors from peaks/troughs
        if self.anchors is None:
            if self.peaks:
                self.anchors = self.peaks
            elif self.troughs:
                self.anchors = self.troughs
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "family": self.family,
            "bias": self.bias,
            "confidence": round(self.confidence, 2),
            "peaks": self.peaks,
            "troughs": self.troughs,
            "valleys": self.valleys,
            "neckline": round(self.neckline, 2) if self.neckline else None,
            "resistance": round(self.resistance, 2) if self.resistance else None,
            "support": round(self.support, 2) if self.support else None,
            "height": round(self.height, 2) if self.height else None,
            "target": round(self.target, 2) if self.target else None,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "touches_top": self.touches_top,
            "touches_bottom": self.touches_bottom,
            "window": self.window,
            "anchors": self.anchors,
        }


class HorizontalFamilyDetector:
    """
    Detects ALL horizontal patterns using unified geometry.
    
    Config thresholds:
    - equal_threshold: % for "equal" prices (default 4%)
    - min_depth: minimum pullback % (default 2%)
    - min_spacing: minimum bars between peaks (default 5)
    - min_touches: minimum touches for range (default 4)
    """
    
    def __init__(self, config: Dict = None):
        config = config or {}
        
        self.equal_threshold = config.get("equal_threshold", 0.04)   # 4% — more lenient!
        self.min_depth = config.get("min_depth", 0.02)               # 2% pullback
        self.min_spacing = config.get("min_spacing", 5)              # 5 bars
        self.min_touches = config.get("min_touches", 4)              # 4 touches for range
        
        self.swing_engine = get_swing_engine(config.get("swing_config"))
        self.geometry_engine = get_geometry_engine({
            "equal_threshold": self.equal_threshold,
        })
    
    def detect(
        self,
        candles: List[Dict],
        swing_highs: List[SwingPoint] = None,
        swing_lows: List[SwingPoint] = None
    ) -> List[HorizontalPattern]:
        """
        Detect all horizontal family patterns.
        
        Returns list of candidates sorted by confidence.
        """
        # Get swings if not provided
        if swing_highs is None or swing_lows is None:
            swing_highs, swing_lows = self.swing_engine.find_swings(candles)
        
        candidates = []
        
        # Try each pattern type
        # 1. Double Top
        dt = self._detect_double_top(swing_highs, swing_lows, candles)
        if dt:
            candidates.append(dt)
        
        # 2. Double Bottom
        db = self._detect_double_bottom(swing_highs, swing_lows, candles)
        if db:
            candidates.append(db)
        
        # 3. Triple Top
        tt = self._detect_triple_top(swing_highs, swing_lows, candles)
        if tt:
            candidates.append(tt)
        
        # 4. Triple Bottom
        tb = self._detect_triple_bottom(swing_highs, swing_lows, candles)
        if tb:
            candidates.append(tb)
        
        # 5. Range / Rectangle
        rng = self._detect_range(swing_highs, swing_lows, candles)
        if rng:
            candidates.append(rng)
        
        # Sort by confidence
        candidates.sort(key=lambda p: p.confidence, reverse=True)
        
        return candidates
    
    # =========================================================================
    # DOUBLE TOP
    # =========================================================================
    
    def _detect_double_top(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        candles: List[Dict]
    ) -> Optional[HorizontalPattern]:
        """
        Double Top:
        - Two peaks at similar level
        - Valley between them (neckline)
        - Second peak does NOT exceed first significantly
        """
        if len(swing_highs) < 2:
            return None
        
        # Get recent peaks
        recent_highs = swing_highs[-5:]  # Last 5 swing highs
        
        # Find best double top candidate
        best_candidate = None
        best_confidence = 0
        
        for i in range(len(recent_highs) - 1):
            p1 = recent_highs[i]
            p2 = recent_highs[i + 1]
            
            # Check spacing
            spacing = p2.index - p1.index
            if spacing < self.min_spacing:
                continue
            
            # Check price equality
            price_diff = abs(p1.price - p2.price) / p1.price
            if price_diff > self.equal_threshold:
                continue
            
            # Second peak should not exceed first by more than threshold
            if p2.price > p1.price * (1 + self.equal_threshold):
                continue
            
            # Find valley between peaks
            valley = self._find_valley_between(swing_lows, p1.index, p2.index)
            if not valley:
                continue
            
            # Check depth
            depth = (p1.price - valley.price) / p1.price
            if depth < self.min_depth:
                continue
            
            # Calculate confidence
            symmetry = 1 - price_diff / self.equal_threshold
            depth_score = min(depth / 0.05, 1.0)  # 5% depth = max score
            spacing_score = min(spacing / 20, 1.0)
            
            confidence = min(symmetry * 0.4 + depth_score * 0.35 + spacing_score * 0.25, 0.92)
            
            if confidence > best_confidence:
                best_confidence = confidence
                
                # Calculate target
                height = p1.price - valley.price
                target = valley.price - height
                
                best_candidate = HorizontalPattern(
                    type="double_top",
                    bias="bearish",
                    confidence=confidence,
                    peaks=[p1.to_dict(), p2.to_dict()],
                    troughs=[valley.to_dict()],
                    valleys=[valley.to_dict()],  # Valleys for window validator
                    neckline=valley.price,
                    resistance=max(p1.price, p2.price),
                    height=height,
                    target=target,
                    start_index=p1.index,
                    end_index=p2.index,
                    touches_top=2,
                    touches_bottom=1,
                )
        
        return best_candidate
    
    # =========================================================================
    # DOUBLE BOTTOM
    # =========================================================================
    
    def _detect_double_bottom(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        candles: List[Dict]
    ) -> Optional[HorizontalPattern]:
        """
        Double Bottom:
        - Two troughs at similar level
        - Peak between them (neckline)
        - Second trough does NOT go below first significantly
        """
        if len(swing_lows) < 2:
            return None
        
        recent_lows = swing_lows[-5:]
        
        best_candidate = None
        best_confidence = 0
        
        for i in range(len(recent_lows) - 1):
            t1 = recent_lows[i]
            t2 = recent_lows[i + 1]
            
            # Check spacing
            spacing = t2.index - t1.index
            if spacing < self.min_spacing:
                continue
            
            # Check price equality
            price_diff = abs(t1.price - t2.price) / t1.price
            if price_diff > self.equal_threshold:
                continue
            
            # Second trough should not be significantly lower
            if t2.price < t1.price * (1 - self.equal_threshold):
                continue
            
            # Find peak between
            peak = self._find_peak_between(swing_highs, t1.index, t2.index)
            if not peak:
                continue
            
            # Check depth
            depth = (peak.price - t1.price) / t1.price
            if depth < self.min_depth:
                continue
            
            # Confidence
            symmetry = 1 - price_diff / self.equal_threshold
            depth_score = min(depth / 0.05, 1.0)
            spacing_score = min(spacing / 20, 1.0)
            
            confidence = min(symmetry * 0.4 + depth_score * 0.35 + spacing_score * 0.25, 0.92)
            
            if confidence > best_confidence:
                best_confidence = confidence
                
                height = peak.price - t1.price
                target = peak.price + height
                
                best_candidate = HorizontalPattern(
                    type="double_bottom",
                    bias="bullish",
                    confidence=confidence,
                    peaks=[peak.to_dict()],
                    troughs=[t1.to_dict(), t2.to_dict()],
                    neckline=peak.price,
                    support=min(t1.price, t2.price),
                    height=height,
                    target=target,
                    start_index=t1.index,
                    end_index=t2.index,
                    touches_top=1,
                    touches_bottom=2,
                )
        
        return best_candidate
    
    # =========================================================================
    # TRIPLE TOP
    # =========================================================================
    
    def _detect_triple_top(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        candles: List[Dict]
    ) -> Optional[HorizontalPattern]:
        """
        Triple Top:
        - Three peaks at similar level
        - Two valleys between them
        """
        if len(swing_highs) < 3:
            return None
        
        recent_highs = swing_highs[-6:]
        
        best_candidate = None
        best_confidence = 0
        
        for i in range(len(recent_highs) - 2):
            p1 = recent_highs[i]
            p2 = recent_highs[i + 1]
            p3 = recent_highs[i + 2]
            
            # Check all three are at similar level
            prices = [p1.price, p2.price, p3.price]
            avg = sum(prices) / 3
            max_diff = max(abs(p - avg) / avg for p in prices)
            
            if max_diff > self.equal_threshold:
                continue
            
            # Find valleys
            v1 = self._find_valley_between(swing_lows, p1.index, p2.index)
            v2 = self._find_valley_between(swing_lows, p2.index, p3.index)
            
            if not v1 or not v2:
                continue
            
            # Neckline is lower valley
            neckline = min(v1.price, v2.price)
            
            # Depth check
            depth = (avg - neckline) / avg
            if depth < self.min_depth:
                continue
            
            # Confidence
            symmetry = 1 - max_diff / self.equal_threshold
            depth_score = min(depth / 0.05, 1.0)
            
            confidence = min(symmetry * 0.5 + depth_score * 0.3 + 0.2, 0.92)  # Bonus for triple
            
            if confidence > best_confidence:
                best_confidence = confidence
                
                height = avg - neckline
                target = neckline - height
                
                best_candidate = HorizontalPattern(
                    type="triple_top",
                    bias="bearish",
                    confidence=confidence,
                    peaks=[p1.to_dict(), p2.to_dict(), p3.to_dict()],
                    troughs=[v1.to_dict(), v2.to_dict()],
                    valleys=[v1.to_dict(), v2.to_dict()],  # For window validator
                    neckline=neckline,
                    resistance=avg,
                    height=height,
                    target=target,
                    start_index=p1.index,
                    end_index=p3.index,
                    touches_top=3,
                    touches_bottom=2,
                )
        
        return best_candidate
    
    # =========================================================================
    # TRIPLE BOTTOM
    # =========================================================================
    
    def _detect_triple_bottom(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        candles: List[Dict]
    ) -> Optional[HorizontalPattern]:
        """
        Triple Bottom:
        - Three troughs at similar level
        - Two peaks between them
        """
        if len(swing_lows) < 3:
            return None
        
        recent_lows = swing_lows[-6:]
        
        best_candidate = None
        best_confidence = 0
        
        for i in range(len(recent_lows) - 2):
            t1 = recent_lows[i]
            t2 = recent_lows[i + 1]
            t3 = recent_lows[i + 2]
            
            prices = [t1.price, t2.price, t3.price]
            avg = sum(prices) / 3
            max_diff = max(abs(p - avg) / avg for p in prices)
            
            if max_diff > self.equal_threshold:
                continue
            
            pk1 = self._find_peak_between(swing_highs, t1.index, t2.index)
            pk2 = self._find_peak_between(swing_highs, t2.index, t3.index)
            
            if not pk1 or not pk2:
                continue
            
            neckline = max(pk1.price, pk2.price)
            
            depth = (neckline - avg) / avg
            if depth < self.min_depth:
                continue
            
            symmetry = 1 - max_diff / self.equal_threshold
            depth_score = min(depth / 0.05, 1.0)
            
            confidence = min(symmetry * 0.5 + depth_score * 0.3 + 0.2, 0.92)
            
            if confidence > best_confidence:
                best_confidence = confidence
                
                height = neckline - avg
                target = neckline + height
                
                best_candidate = HorizontalPattern(
                    type="triple_bottom",
                    bias="bullish",
                    confidence=confidence,
                    peaks=[pk1.to_dict(), pk2.to_dict()],
                    troughs=[t1.to_dict(), t2.to_dict(), t3.to_dict()],
                    neckline=neckline,
                    support=avg,
                    height=height,
                    target=target,
                    start_index=t1.index,
                    end_index=t3.index,
                    touches_top=2,
                    touches_bottom=3,
                )
        
        return best_candidate
    
    # =========================================================================
    # RANGE / RECTANGLE
    # =========================================================================
    
    def _detect_range(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        candles: List[Dict]
    ) -> Optional[HorizontalPattern]:
        """
        Range:
        - Multiple touches of support/resistance
        - Both lines approximately horizontal
        """
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None
        
        recent_highs = swing_highs[-5:]
        recent_lows = swing_lows[-5:]
        
        # Check if highs are at similar level
        high_prices = [h.price for h in recent_highs]
        high_avg = sum(high_prices) / len(high_prices)
        high_max_diff = max(abs(p - high_avg) / high_avg for p in high_prices)
        
        # Check if lows are at similar level
        low_prices = [l.price for l in recent_lows]
        low_avg = sum(low_prices) / len(low_prices)
        low_max_diff = max(abs(p - low_avg) / low_avg for p in low_prices)
        
        # Both should be relatively horizontal
        if high_max_diff > self.equal_threshold * 1.5:  # Slightly more lenient
            return None
        if low_max_diff > self.equal_threshold * 1.5:
            return None
        
        # Count total touches
        touches_top = len(recent_highs)
        touches_bottom = len(recent_lows)
        total_touches = touches_top + touches_bottom
        
        if total_touches < self.min_touches:
            return None
        
        # Range should have meaningful height
        height = high_avg - low_avg
        height_pct = height / low_avg
        
        if height_pct < 0.02:  # Less than 2% range is noise
            return None
        
        # Confidence
        horizontal_score = 1 - (high_max_diff + low_max_diff) / (self.equal_threshold * 2)
        touch_score = min(total_touches / 8, 1.0)
        
        confidence = min(horizontal_score * 0.5 + touch_score * 0.5, 0.92)
        
        # Determine if it's a proper rectangle (more touches) or just range
        pattern_type = "rectangle" if total_touches >= 6 else "range"
        
        return HorizontalPattern(
            type=pattern_type,
            bias="neutral",
            confidence=confidence,
            peaks=[h.to_dict() for h in recent_highs],
            troughs=[l.to_dict() for l in recent_lows],
            resistance=high_avg,
            support=low_avg,
            height=height,
            start_index=min(h.index for h in recent_highs + recent_lows),
            end_index=max(h.index for h in recent_highs + recent_lows),
            touches_top=touches_top,
            touches_bottom=touches_bottom,
        )
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _find_valley_between(
        self,
        swing_lows: List[SwingPoint],
        start_idx: int,
        end_idx: int
    ) -> Optional[SwingPoint]:
        """Find the lowest swing low between two indices."""
        candidates = [l for l in swing_lows if start_idx < l.index < end_idx]
        if not candidates:
            return None
        return min(candidates, key=lambda l: l.price)
    
    def _find_peak_between(
        self,
        swing_highs: List[SwingPoint],
        start_idx: int,
        end_idx: int
    ) -> Optional[SwingPoint]:
        """Find the highest swing high between two indices."""
        candidates = [h for h in swing_highs if start_idx < h.index < end_idx]
        if not candidates:
            return None
        return max(candidates, key=lambda h: h.price)


# Singleton
_horizontal_detector = None

def get_horizontal_family_detector(config: Dict = None) -> HorizontalFamilyDetector:
    global _horizontal_detector
    if _horizontal_detector is None or config:
        _horizontal_detector = HorizontalFamilyDetector(config)
    return _horizontal_detector
