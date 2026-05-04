"""
Pattern Detector
=================
Detects chart patterns from price data.

Supports:
- Triangles (ascending, descending, symmetrical)
- Channels
- Double top/bottom
- Head & Shoulders
- Flags, Pennants
- Compression/Squeeze
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
import math

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.ta_engine.setup.setup_types import (
    DetectedPattern,
    PatternType,
    Direction,
    StructureType,
)
from modules.ta_engine.setup.structure_engine import get_structure_engine


class PatternDetector:
    """Detects chart patterns from candle data with structure validation."""
    
    def __init__(self):
        self.min_pattern_candles = 10
        self.max_pattern_candles = 100
        self.structure_engine = get_structure_engine()
    
    def detect_all(self, candles: List[Dict]) -> List[DetectedPattern]:
        """
        Detect all patterns in candle data.
        Returns list sorted by confidence (highest first).
        Applies structure validation to adjust confidence.
        """
        if len(candles) < self.min_pattern_candles:
            return []
        
        # Get market structure for validation
        structure_points, structure_bias, structure_meta = self.structure_engine.analyze_all(candles)
        
        patterns = []
        
        # Detect various pattern types
        patterns.extend(self._detect_triangles(candles))
        patterns.extend(self._detect_channels(candles))
        patterns.extend(self._detect_double_patterns(candles))
        patterns.extend(self._detect_compression(candles))
        patterns.extend(self._detect_flags(candles))
        
        # Apply structure validation - adjust confidence based on structure consistency
        validated_patterns = self._validate_with_structure(patterns, structure_meta, structure_bias)
        
        # Sort by confidence
        validated_patterns.sort(key=lambda p: p.confidence, reverse=True)
        
        return validated_patterns
    
    def _validate_with_structure(
        self, 
        patterns: List[DetectedPattern], 
        structure_meta: Dict,
        structure_bias: Direction
    ) -> List[DetectedPattern]:
        """
        Validate patterns against market structure.
        
        Rules:
        - Ascending patterns require HH/HL structure (bullish)
        - Descending patterns require LH/LL structure (bearish)
        - If structure contradicts pattern, reduce confidence
        - If structure confirms pattern, boost confidence
        """
        validated = []
        
        hh = structure_meta.get("higher_highs", 0)
        hl = structure_meta.get("higher_lows", 0)
        lh = structure_meta.get("lower_highs", 0)
        ll = structure_meta.get("lower_lows", 0)
        
        bullish_structure = (hh >= 2 and hl >= 2)
        bearish_structure = (lh >= 2 and ll >= 2)
        
        for pattern in patterns:
            original_confidence = pattern.confidence
            adjusted_confidence = original_confidence
            validation_reason = None
            
            # Ascending triangle / ascending channel requires bullish structure
            if pattern.pattern_type in [PatternType.ASCENDING_TRIANGLE, PatternType.ASCENDING_CHANNEL]:
                if bullish_structure:
                    # Structure confirms - boost confidence
                    adjusted_confidence = min(1.0, original_confidence * 1.15)
                    validation_reason = f"Structure confirms (HH={hh}, HL={hl})"
                elif ll > 0:
                    # LL present contradicts ascending pattern - reduce confidence
                    adjusted_confidence = original_confidence * 0.6
                    validation_reason = f"Structure contradicts (LL={ll})"
            
            # Descending triangle / descending channel requires bearish structure
            elif pattern.pattern_type in [PatternType.DESCENDING_TRIANGLE, PatternType.DESCENDING_CHANNEL]:
                if bearish_structure:
                    # Structure confirms - boost confidence
                    adjusted_confidence = min(1.0, original_confidence * 1.15)
                    validation_reason = f"Structure confirms (LH={lh}, LL={ll})"
                elif hh > 0:
                    # HH present contradicts descending pattern - reduce confidence
                    adjusted_confidence = original_confidence * 0.6
                    validation_reason = f"Structure contradicts (HH={hh})"
            
            # Double top requires bearish reversal potential
            elif pattern.pattern_type == PatternType.DOUBLE_TOP:
                if structure_bias == Direction.BULLISH and hh >= 2:
                    # Strong uptrend - double top more significant
                    adjusted_confidence = min(1.0, original_confidence * 1.1)
                    validation_reason = "Strong uptrend reversal potential"
                elif bearish_structure:
                    # Already bearish - less significant
                    adjusted_confidence = original_confidence * 0.7
                    validation_reason = "Already bearish structure"
            
            # Double bottom requires bullish reversal potential
            elif pattern.pattern_type == PatternType.DOUBLE_BOTTOM:
                if structure_bias == Direction.BEARISH and ll >= 2:
                    # Strong downtrend - double bottom more significant
                    adjusted_confidence = min(1.0, original_confidence * 1.1)
                    validation_reason = "Strong downtrend reversal potential"
                elif bullish_structure:
                    # Already bullish - less significant
                    adjusted_confidence = original_confidence * 0.7
                    validation_reason = "Already bullish structure"
            
            # Head and shoulders - reversal pattern
            elif pattern.pattern_type == PatternType.HEAD_AND_SHOULDERS:
                if structure_bias == Direction.BULLISH:
                    adjusted_confidence = min(1.0, original_confidence * 1.1)
                    validation_reason = "Bullish trend reversal setup"
                elif structure_bias == Direction.BEARISH:
                    adjusted_confidence = original_confidence * 0.6
                    validation_reason = "Already bearish - less valid"
            
            # Inverse head and shoulders
            elif pattern.pattern_type == PatternType.INVERSE_HEAD_AND_SHOULDERS:
                if structure_bias == Direction.BEARISH:
                    adjusted_confidence = min(1.0, original_confidence * 1.1)
                    validation_reason = "Bearish trend reversal setup"
                elif structure_bias == Direction.BULLISH:
                    adjusted_confidence = original_confidence * 0.6
                    validation_reason = "Already bullish - less valid"
            
            # Update pattern with validated confidence
            pattern.confidence = round(adjusted_confidence, 2)
            if validation_reason:
                pattern.notes = validation_reason
            
            # Only include patterns with confidence > 0.3
            if pattern.confidence >= 0.3:
                validated.append(pattern)
        
        return validated
    
    def _detect_triangles(self, candles: List[Dict]) -> List[DetectedPattern]:
        """Detect triangle patterns."""
        patterns = []
        
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        times = [c.get("timestamp", c.get("time")) for c in candles]
        
        # Use last 30-50 candles for triangle detection
        lookback = min(50, len(candles))
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        recent_times = times[-lookback:]
        
        # Find swing highs and lows
        swing_highs = self._find_swing_points(recent_highs, is_high=True)
        swing_lows = self._find_swing_points(recent_lows, is_high=False)
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return patterns
        
        # Calculate trendlines
        high_slope = self._calculate_slope([recent_highs[i] for i in swing_highs])
        low_slope = self._calculate_slope([recent_lows[i] for i in swing_lows])
        
        # Determine triangle type
        pattern_type = None
        direction = Direction.NEUTRAL
        confidence = 0.0
        
        # Ascending Triangle: flat resistance, rising support
        if abs(high_slope) < 0.001 and low_slope > 0.001:
            pattern_type = PatternType.ASCENDING_TRIANGLE
            direction = Direction.BULLISH
            confidence = 0.65 + min(low_slope * 10, 0.2)
        
        # Descending Triangle: falling resistance, flat support
        elif high_slope < -0.001 and abs(low_slope) < 0.001:
            pattern_type = PatternType.DESCENDING_TRIANGLE
            direction = Direction.BEARISH
            confidence = 0.65 + min(abs(high_slope) * 10, 0.2)
        
        # Symmetrical Triangle: converging lines
        elif high_slope < -0.0005 and low_slope > 0.0005:
            pattern_type = PatternType.SYMMETRICAL_TRIANGLE
            direction = Direction.NEUTRAL
            convergence = abs(high_slope) + abs(low_slope)
            confidence = 0.55 + min(convergence * 5, 0.25)
        
        if pattern_type:
            # Calculate breakout level and targets
            current_high = recent_highs[-1]
            current_low = recent_lows[-1]
            pattern_height = max(recent_highs) - min(recent_lows)
            
            breakout_level = max(recent_highs[-5:]) if direction == Direction.BULLISH else min(recent_lows[-5:])
            
            if direction == Direction.BULLISH:
                target = breakout_level + pattern_height * 0.618
                invalidation = min(recent_lows[-10:])
            elif direction == Direction.BEARISH:
                target = breakout_level - pattern_height * 0.618
                invalidation = max(recent_highs[-10:])
            else:
                target = None
                invalidation = None
            
            # Build points for drawing
            points = []
            for i in swing_highs[-3:]:
                points.append({"time": self._parse_time(recent_times[i]), "price": recent_highs[i], "type": "high"})
            for i in swing_lows[-3:]:
                points.append({"time": self._parse_time(recent_times[i]), "price": recent_lows[i], "type": "low"})
            
            patterns.append(DetectedPattern(
                pattern_type=pattern_type,
                direction=direction,
                confidence=confidence,
                start_time=self._parse_datetime(recent_times[min(swing_highs[0], swing_lows[0])]),
                end_time=self._parse_datetime(recent_times[-1]),
                points=points,
                breakout_level=breakout_level,
                target_price=target,
                invalidation=invalidation,
            ))
        
        return patterns
    
    def _detect_channels(self, candles: List[Dict]) -> List[DetectedPattern]:
        """Detect channel patterns."""
        patterns = []
        
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        times = [c.get("timestamp", c.get("time")) for c in candles]
        
        lookback = min(40, len(candles))
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        recent_times = times[-lookback:]
        
        # Calculate parallel channel
        high_slope = self._linear_regression_slope(recent_highs)
        low_slope = self._linear_regression_slope(recent_lows)
        
        # Check if slopes are parallel (similar)
        slope_diff = abs(high_slope - low_slope)
        
        if slope_diff < 0.002:  # Parallel enough
            avg_slope = (high_slope + low_slope) / 2
            
            if avg_slope > 0.001:
                pattern_type = PatternType.ASCENDING_CHANNEL
                direction = Direction.BULLISH
            elif avg_slope < -0.001:
                pattern_type = PatternType.DESCENDING_CHANNEL
                direction = Direction.BEARISH
            else:
                pattern_type = PatternType.HORIZONTAL_CHANNEL
                direction = Direction.NEUTRAL
            
            confidence = 0.6 + (0.002 - slope_diff) * 100
            confidence = min(confidence, 0.85)
            
            channel_width = sum(h - l for h, l in zip(recent_highs, recent_lows)) / len(recent_highs)
            
            points = [
                {"time": self._parse_time(recent_times[0]), "price": recent_highs[0], "type": "high_start"},
                {"time": self._parse_time(recent_times[-1]), "price": recent_highs[-1], "type": "high_end"},
                {"time": self._parse_time(recent_times[0]), "price": recent_lows[0], "type": "low_start"},
                {"time": self._parse_time(recent_times[-1]), "price": recent_lows[-1], "type": "low_end"},
            ]
            
            patterns.append(DetectedPattern(
                pattern_type=pattern_type,
                direction=direction,
                confidence=confidence,
                start_time=self._parse_datetime(recent_times[0]),
                end_time=self._parse_datetime(recent_times[-1]),
                points=points,
                breakout_level=recent_highs[-1] if direction != Direction.BEARISH else recent_lows[-1],
                target_price=recent_highs[-1] + channel_width if direction == Direction.BULLISH else recent_lows[-1] - channel_width,
                invalidation=recent_lows[-1] if direction == Direction.BULLISH else recent_highs[-1],
            ))
        
        return patterns
    
    def _detect_double_patterns(self, candles: List[Dict]) -> List[DetectedPattern]:
        """Detect double top/bottom patterns."""
        patterns = []
        
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        times = [c.get("timestamp", c.get("time")) for c in candles]
        
        lookback = min(60, len(candles))
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        recent_times = times[-lookback:]
        
        # Find swing highs for double top
        swing_high_indices = self._find_swing_points(recent_highs, is_high=True, threshold=5)
        
        if len(swing_high_indices) >= 2:
            # Check last two swing highs
            idx1, idx2 = swing_high_indices[-2], swing_high_indices[-1]
            high1, high2 = recent_highs[idx1], recent_highs[idx2]
            
            # Double top: two highs at similar level
            tolerance = (max(recent_highs) - min(recent_lows)) * 0.03
            if abs(high1 - high2) < tolerance and idx2 - idx1 > 5:
                neckline = min(recent_lows[idx1:idx2+1])
                pattern_height = ((high1 + high2) / 2) - neckline
                
                patterns.append(DetectedPattern(
                    pattern_type=PatternType.DOUBLE_TOP,
                    direction=Direction.BEARISH,
                    confidence=0.7,
                    start_time=self._parse_datetime(recent_times[idx1]),
                    end_time=self._parse_datetime(recent_times[idx2]),
                    points=[
                        {"time": self._parse_time(recent_times[idx1]), "price": high1, "type": "top1"},
                        {"time": self._parse_time(recent_times[idx2]), "price": high2, "type": "top2"},
                        {"time": self._parse_time(recent_times[(idx1+idx2)//2]), "price": neckline, "type": "neckline"},
                    ],
                    breakout_level=neckline,
                    target_price=neckline - pattern_height,
                    invalidation=max(high1, high2) * 1.01,
                ))
        
        # Find swing lows for double bottom
        swing_low_indices = self._find_swing_points(recent_lows, is_high=False, threshold=5)
        
        if len(swing_low_indices) >= 2:
            idx1, idx2 = swing_low_indices[-2], swing_low_indices[-1]
            low1, low2 = recent_lows[idx1], recent_lows[idx2]
            
            tolerance = (max(recent_highs) - min(recent_lows)) * 0.03
            if abs(low1 - low2) < tolerance and idx2 - idx1 > 5:
                neckline = max(recent_highs[idx1:idx2+1])
                pattern_height = neckline - ((low1 + low2) / 2)
                
                patterns.append(DetectedPattern(
                    pattern_type=PatternType.DOUBLE_BOTTOM,
                    direction=Direction.BULLISH,
                    confidence=0.7,
                    start_time=self._parse_datetime(recent_times[idx1]),
                    end_time=self._parse_datetime(recent_times[idx2]),
                    points=[
                        {"time": self._parse_time(recent_times[idx1]), "price": low1, "type": "bottom1"},
                        {"time": self._parse_time(recent_times[idx2]), "price": low2, "type": "bottom2"},
                        {"time": self._parse_time(recent_times[(idx1+idx2)//2]), "price": neckline, "type": "neckline"},
                    ],
                    breakout_level=neckline,
                    target_price=neckline + pattern_height,
                    invalidation=min(low1, low2) * 0.99,
                ))
        
        return patterns
    
    def _detect_compression(self, candles: List[Dict]) -> List[DetectedPattern]:
        """Detect compression/squeeze patterns."""
        patterns = []
        
        if len(candles) < 20:
            return patterns
        
        # Calculate ATR-based volatility
        ranges = []
        for i in range(1, len(candles)):
            tr = max(
                candles[i]["high"] - candles[i]["low"],
                abs(candles[i]["high"] - candles[i-1]["close"]),
                abs(candles[i]["low"] - candles[i-1]["close"])
            )
            ranges.append(tr)
        
        # Compare recent volatility to historical
        recent_atr = sum(ranges[-10:]) / 10 if len(ranges) >= 10 else sum(ranges) / len(ranges)
        historical_atr = sum(ranges[-30:-10]) / 20 if len(ranges) >= 30 else sum(ranges) / len(ranges)
        
        compression_ratio = recent_atr / max(historical_atr, 1e-8)
        
        if compression_ratio < 0.6:  # Significant compression
            times = [c.get("timestamp", c.get("time")) for c in candles]
            
            patterns.append(DetectedPattern(
                pattern_type=PatternType.COMPRESSION,
                direction=Direction.NEUTRAL,
                confidence=0.65 + (0.6 - compression_ratio),
                start_time=self._parse_datetime(times[-20]),
                end_time=self._parse_datetime(times[-1]),
                points=[
                    {"time": self._parse_time(times[-20]), "price": candles[-20]["close"], "type": "start"},
                    {"time": self._parse_time(times[-1]), "price": candles[-1]["close"], "type": "end"},
                ],
                breakout_level=max(c["high"] for c in candles[-10:]),
                target_price=None,
                invalidation=min(c["low"] for c in candles[-10:]),
            ))
        
        return patterns
    
    def _detect_flags(self, candles: List[Dict]) -> List[DetectedPattern]:
        """Detect flag and pennant patterns."""
        patterns = []
        
        if len(candles) < 30:
            return patterns
        
        closes = [c["close"] for c in candles]
        times = [c.get("timestamp", c.get("time")) for c in candles]
        
        # Look for strong move (pole) followed by consolidation (flag)
        lookback = min(30, len(candles))
        
        # Calculate move in first part
        pole_end = lookback // 3
        pole_move = (closes[-lookback + pole_end] - closes[-lookback]) / closes[-lookback]
        
        # Calculate consolidation in second part
        flag_prices = closes[-lookback + pole_end:]
        flag_range = (max(flag_prices) - min(flag_prices)) / min(flag_prices)
        
        if abs(pole_move) > 0.05 and flag_range < 0.03:  # Strong move + tight flag
            direction = Direction.BULLISH if pole_move > 0 else Direction.BEARISH
            pattern_type = PatternType.BULL_FLAG if direction == Direction.BULLISH else PatternType.BEAR_FLAG
            
            patterns.append(DetectedPattern(
                pattern_type=pattern_type,
                direction=direction,
                confidence=0.65 + min(abs(pole_move) * 2, 0.2),
                start_time=self._parse_datetime(times[-lookback]),
                end_time=self._parse_datetime(times[-1]),
                points=[
                    {"time": self._parse_time(times[-lookback]), "price": closes[-lookback], "type": "pole_start"},
                    {"time": self._parse_time(times[-lookback + pole_end]), "price": closes[-lookback + pole_end], "type": "pole_end"},
                    {"time": self._parse_time(times[-1]), "price": closes[-1], "type": "flag_end"},
                ],
                breakout_level=max(flag_prices) if direction == Direction.BULLISH else min(flag_prices),
                target_price=closes[-1] + (closes[-lookback + pole_end] - closes[-lookback]) if direction == Direction.BULLISH else closes[-1] - (closes[-lookback] - closes[-lookback + pole_end]),
                invalidation=min(flag_prices) if direction == Direction.BULLISH else max(flag_prices),
            ))
        
        return patterns
    
    # Helper methods
    def _find_swing_points(self, prices: List[float], is_high: bool, threshold: int = 3) -> List[int]:
        """Find swing high/low indices."""
        swings = []
        for i in range(threshold, len(prices) - threshold):
            if is_high:
                if all(prices[i] >= prices[i-j] for j in range(1, threshold+1)) and \
                   all(prices[i] >= prices[i+j] for j in range(1, threshold+1)):
                    swings.append(i)
            else:
                if all(prices[i] <= prices[i-j] for j in range(1, threshold+1)) and \
                   all(prices[i] <= prices[i+j] for j in range(1, threshold+1)):
                    swings.append(i)
        return swings
    
    def _calculate_slope(self, values: List[float]) -> float:
        """Calculate simple slope between first and last value."""
        if len(values) < 2:
            return 0.0
        return (values[-1] - values[0]) / max(len(values), 1) / max(values[0], 1e-8)
    
    def _linear_regression_slope(self, values: List[float]) -> float:
        """Calculate linear regression slope."""
        n = len(values)
        if n < 2:
            return 0.0
        
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator / max(y_mean, 1e-8)
    
    def _parse_time(self, ts) -> float:
        """Convert timestamp to Unix seconds."""
        if isinstance(ts, (int, float)):
            return float(ts)
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                return dt.timestamp()
            except:
                return 0.0
        if isinstance(ts, datetime):
            return ts.timestamp()
        return 0.0
    
    def _parse_datetime(self, ts) -> datetime:
        """Convert any timestamp form into aware UTC datetime via unified normalizer."""
        from modules.ta_engine.utils.time_utils import normalize_timestamp
        return normalize_timestamp(ts) or datetime.now(timezone.utc)


# Singleton
_detector: Optional[PatternDetector] = None


def get_pattern_detector() -> PatternDetector:
    """Get singleton pattern detector."""
    global _detector
    if _detector is None:
        _detector = PatternDetector()
    return _detector
