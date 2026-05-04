"""
Structure Engine
=================
Analyzes market structure.

Detects:
- Higher Highs / Higher Lows
- Lower Highs / Lower Lows
- Break of Structure (BOS)
- Change of Character (CHOCH)
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

from modules.ta_engine.setup.setup_types import (
    StructurePoint,
    StructureType,
    Direction,
)


class StructureEngine:
    """Analyzes market structure and swing points."""
    
    def __init__(self):
        self.swing_lookback = 5
    
    def analyze_all(self, candles: List[Dict]) -> Tuple[List[StructurePoint], Direction, Dict]:
        """
        Analyze market structure.
        
        Returns:
            - List of structure points
            - Overall structure bias
            - Structure metadata
        """
        if len(candles) < 20:
            return [], Direction.NEUTRAL, {}
        
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        times = [c.get("timestamp", c.get("time")) for c in candles]
        
        structure_points = []
        
        # Find swing highs and lows
        swing_high_indices = self._find_swing_points(highs, is_high=True)
        swing_low_indices = self._find_swing_points(lows, is_high=False)
        
        # Classify swing highs
        prev_high = None
        for idx in swing_high_indices:
            price = highs[idx]
            time = self._parse_datetime(times[idx])
            
            if prev_high is not None:
                if price > prev_high:
                    structure_points.append(StructurePoint(
                        structure_type=StructureType.HIGHER_HIGH,
                        price=price,
                        time=time,
                        confirmed=True,
                    ))
                elif price < prev_high:
                    structure_points.append(StructurePoint(
                        structure_type=StructureType.LOWER_HIGH,
                        price=price,
                        time=time,
                        confirmed=True,
                    ))
                else:
                    structure_points.append(StructurePoint(
                        structure_type=StructureType.EQUAL_HIGH,
                        price=price,
                        time=time,
                        confirmed=True,
                    ))
            prev_high = price
        
        # Classify swing lows
        prev_low = None
        for idx in swing_low_indices:
            price = lows[idx]
            time = self._parse_datetime(times[idx])
            
            if prev_low is not None:
                if price > prev_low:
                    structure_points.append(StructurePoint(
                        structure_type=StructureType.HIGHER_LOW,
                        price=price,
                        time=time,
                        confirmed=True,
                    ))
                elif price < prev_low:
                    structure_points.append(StructurePoint(
                        structure_type=StructureType.LOWER_LOW,
                        price=price,
                        time=time,
                        confirmed=True,
                    ))
                else:
                    structure_points.append(StructurePoint(
                        structure_type=StructureType.EQUAL_LOW,
                        price=price,
                        time=time,
                        confirmed=True,
                    ))
            prev_low = price
        
        # Detect BOS and CHOCH
        bos_choch = self._detect_bos_choch(highs, lows, times, swing_high_indices, swing_low_indices)
        structure_points.extend(bos_choch)
        
        # Sort by time
        structure_points.sort(key=lambda p: p.time)
        
        # Determine overall bias
        bias, metadata = self._calculate_structure_bias(structure_points, highs, lows)
        
        return structure_points, bias, metadata
    
    def _detect_bos_choch(
        self,
        highs: List[float],
        lows: List[float],
        times: List,
        swing_high_indices: List[int],
        swing_low_indices: List[int],
    ) -> List[StructurePoint]:
        """Detect Break of Structure and Change of Character."""
        points = []
        
        if len(swing_high_indices) < 2 or len(swing_low_indices) < 2:
            return points
        
        # Check for bullish BOS (price breaks above previous swing high)
        if len(swing_high_indices) >= 2:
            prev_swing_high = highs[swing_high_indices[-2]]
            last_swing_high = highs[swing_high_indices[-1]]
            current_high = highs[-1]
            
            if current_high > prev_swing_high and last_swing_high <= prev_swing_high:
                # This is a BOS in bullish direction
                points.append(StructurePoint(
                    structure_type=StructureType.BREAK_OF_STRUCTURE,
                    price=prev_swing_high,
                    time=self._parse_datetime(times[-1]),
                    confirmed=True,
                ))
        
        # Check for bearish BOS (price breaks below previous swing low)
        if len(swing_low_indices) >= 2:
            prev_swing_low = lows[swing_low_indices[-2]]
            last_swing_low = lows[swing_low_indices[-1]]
            current_low = lows[-1]
            
            if current_low < prev_swing_low and last_swing_low >= prev_swing_low:
                points.append(StructurePoint(
                    structure_type=StructureType.BREAK_OF_STRUCTURE,
                    price=prev_swing_low,
                    time=self._parse_datetime(times[-1]),
                    confirmed=True,
                ))
        
        # Detect CHOCH (Change of Character)
        # CHOCH occurs when structure changes from bullish to bearish or vice versa
        recent_highs = [highs[i] for i in swing_high_indices[-3:]] if len(swing_high_indices) >= 3 else []
        recent_lows = [lows[i] for i in swing_low_indices[-3:]] if len(swing_low_indices) >= 3 else []
        
        if len(recent_highs) >= 3 and len(recent_lows) >= 3:
            # Was bullish (HH, HL) but now making LH
            was_bullish = recent_highs[-3] < recent_highs[-2] and recent_lows[-3] < recent_lows[-2]
            now_bearish = recent_highs[-1] < recent_highs[-2]
            
            if was_bullish and now_bearish:
                points.append(StructurePoint(
                    structure_type=StructureType.CHANGE_OF_CHARACTER,
                    price=recent_highs[-1],
                    time=self._parse_datetime(times[swing_high_indices[-1]]),
                    confirmed=True,
                ))
            
            # Was bearish (LH, LL) but now making HL
            was_bearish = recent_highs[-3] > recent_highs[-2] and recent_lows[-3] > recent_lows[-2]
            now_bullish = recent_lows[-1] > recent_lows[-2]
            
            if was_bearish and now_bullish:
                points.append(StructurePoint(
                    structure_type=StructureType.CHANGE_OF_CHARACTER,
                    price=recent_lows[-1],
                    time=self._parse_datetime(times[swing_low_indices[-1]]),
                    confirmed=True,
                ))
        
        return points
    
    def _calculate_structure_bias(
        self,
        structure_points: List[StructurePoint],
        highs: List[float],
        lows: List[float],
    ) -> Tuple[Direction, Dict]:
        """Calculate overall structure bias from structure points."""
        if not structure_points:
            return Direction.NEUTRAL, {"reason": "Insufficient data"}
        
        # Count structure types
        hh_count = sum(1 for p in structure_points if p.structure_type == StructureType.HIGHER_HIGH)
        hl_count = sum(1 for p in structure_points if p.structure_type == StructureType.HIGHER_LOW)
        lh_count = sum(1 for p in structure_points if p.structure_type == StructureType.LOWER_HIGH)
        ll_count = sum(1 for p in structure_points if p.structure_type == StructureType.LOWER_LOW)
        bos_count = sum(1 for p in structure_points if p.structure_type == StructureType.BREAK_OF_STRUCTURE)
        choch_count = sum(1 for p in structure_points if p.structure_type == StructureType.CHANGE_OF_CHARACTER)
        
        bullish_score = (hh_count + hl_count) * 2
        bearish_score = (lh_count + ll_count) * 2
        
        # Recent structure matters more
        recent_points = structure_points[-5:] if len(structure_points) >= 5 else structure_points
        for p in recent_points:
            if p.structure_type in [StructureType.HIGHER_HIGH, StructureType.HIGHER_LOW]:
                bullish_score += 3
            elif p.structure_type in [StructureType.LOWER_HIGH, StructureType.LOWER_LOW]:
                bearish_score += 3
        
        metadata = {
            "higher_highs": hh_count,
            "higher_lows": hl_count,
            "lower_highs": lh_count,
            "lower_lows": ll_count,
            "bos_count": bos_count,
            "choch_count": choch_count,
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
        }
        
        if bullish_score > bearish_score * 1.3:
            return Direction.BULLISH, {**metadata, "reason": "Higher highs and higher lows dominant"}
        elif bearish_score > bullish_score * 1.3:
            return Direction.BEARISH, {**metadata, "reason": "Lower highs and lower lows dominant"}
        else:
            return Direction.NEUTRAL, {**metadata, "reason": "Mixed structure, range-bound"}
    
    def _find_swing_points(self, prices: List[float], is_high: bool) -> List[int]:
        """Find swing high/low indices."""
        swings = []
        lookback = self.swing_lookback
        
        for i in range(lookback, len(prices) - lookback):
            if is_high:
                if all(prices[i] >= prices[i-j] for j in range(1, lookback+1)) and \
                   all(prices[i] >= prices[i+j] for j in range(1, min(lookback+1, len(prices)-i))):
                    swings.append(i)
            else:
                if all(prices[i] <= prices[i-j] for j in range(1, lookback+1)) and \
                   all(prices[i] <= prices[i+j] for j in range(1, min(lookback+1, len(prices)-i))):
                    swings.append(i)
        return swings
    
    def _parse_datetime(self, ts) -> datetime:
        """Convert any timestamp form into aware UTC datetime via unified normalizer."""
        from modules.ta_engine.utils.time_utils import normalize_timestamp
        return normalize_timestamp(ts) or datetime.now(timezone.utc)


# Singleton
_engine: Optional[StructureEngine] = None


def get_structure_engine() -> StructureEngine:
    global _engine
    if _engine is None:
        _engine = StructureEngine()
    return _engine
