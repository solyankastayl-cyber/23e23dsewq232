"""
Structure Detector
==================

Детектор BOS (Break of Structure) и CHOCH (Change of Character).
"""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from .structure_types import (
    TrendStructure,
    StructureEvent,
    StructureEventType
)


class StructureDetector:
    """
    Детектор структурных событий.
    
    BOS (Break of Structure):
    - Bullish: новый Higher High после Higher Low
    - Bearish: новый Lower Low после Lower High
    
    CHOCH (Change of Character):
    - Bullish CHOCH: первый Higher High после серии Lower Lows
    - Bearish CHOCH: первый Lower Low после серии Higher Highs
    """
    
    def __init__(
        self, 
        swing_lookback: int = 3,  # Reduced from 5 for higher sensitivity
        min_swing_pct: float = 0.2,  # Reduced from 0.5 for more sensitive detection
        bos_strength_threshold: float = 0.4  # Minimum strength for BOS detection
    ):
        self.swing_lookback = swing_lookback
        self.min_swing_pct = min_swing_pct  # Минимальный % движения для свинга
        self.bos_strength_threshold = bos_strength_threshold
    
    def detect(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        timestamps: Optional[List[datetime]] = None
    ) -> Dict[str, Any]:
        """
        Детектирование структурных событий.
        
        Returns:
            Dict с trend_structure, bos_events, choch_events, swing_points
        """
        if len(highs) < 20:
            return self._empty_result()
        
        # Generate timestamps if not provided
        if timestamps is None:
            timestamps = [datetime.utcnow() for _ in range(len(highs))]
        
        # Find swing points
        swing_highs, swing_lows = self._find_swing_points(highs, lows)
        
        # Analyze structure
        bos_events = []
        choch_events = []
        swing_points = []
        
        # Convert swing points to events
        for idx, price in swing_highs:
            swing_points.append(StructureEvent(
                event_type=StructureEventType.SWING_HIGH,
                price=price,
                timestamp=timestamps[idx] if idx < len(timestamps) else datetime.utcnow(),
                candle_index=idx,
                strength=self._calculate_swing_strength(highs, lows, idx, "high")
            ))
        
        for idx, price in swing_lows:
            swing_points.append(StructureEvent(
                event_type=StructureEventType.SWING_LOW,
                price=price,
                timestamp=timestamps[idx] if idx < len(timestamps) else datetime.utcnow(),
                candle_index=idx,
                strength=self._calculate_swing_strength(highs, lows, idx, "low")
            ))
        
        # Detect BOS and CHOCH
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            bos_events, choch_events = self._detect_structure_breaks(
                swing_highs, swing_lows, highs, lows, timestamps
            )
        
        # Determine trend structure
        trend_structure = self._determine_trend(bos_events, choch_events, swing_highs, swing_lows)
        
        # Calculate confidence
        confidence = self._calculate_confidence(bos_events, choch_events, trend_structure)
        
        return {
            "trend_structure": trend_structure,
            "structure_confidence": confidence,
            "bos_events": bos_events,
            "choch_events": choch_events,
            "swing_points": swing_points,
            "bos_count": len(bos_events),
            "choch_count": len(choch_events)
        }
    
    def _find_swing_points(
        self,
        highs: List[float],
        lows: List[float]
    ) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
        """Найти свинг-точки"""
        swing_highs = []
        swing_lows = []
        
        lookback = self.swing_lookback
        
        for i in range(lookback, len(highs) - lookback):
            # Swing High: highest point in window
            window_highs = highs[i-lookback:i+lookback+1]
            if highs[i] == max(window_highs):
                # Check minimum movement
                window_range = max(window_highs) - min(lows[i-lookback:i+lookback+1])
                if window_range / highs[i] * 100 >= self.min_swing_pct:
                    swing_highs.append((i, highs[i]))
            
            # Swing Low: lowest point in window
            window_lows = lows[i-lookback:i+lookback+1]
            if lows[i] == min(window_lows):
                window_range = max(highs[i-lookback:i+lookback+1]) - min(window_lows)
                if window_range / lows[i] * 100 >= self.min_swing_pct:
                    swing_lows.append((i, lows[i]))
        
        return swing_highs, swing_lows
    
    def _detect_structure_breaks(
        self,
        swing_highs: List[Tuple[int, float]],
        swing_lows: List[Tuple[int, float]],
        highs: List[float],
        lows: List[float],
        timestamps: List[datetime]
    ) -> Tuple[List[StructureEvent], List[StructureEvent]]:
        """Детектировать BOS и CHOCH"""
        bos_events = []
        choch_events = []
        
        # Track structure: HH, HL, LH, LL
        structure_sequence = []
        
        # Combine and sort swing points
        all_swings = []
        for idx, price in swing_highs:
            all_swings.append((idx, price, "HIGH"))
        for idx, price in swing_lows:
            all_swings.append((idx, price, "LOW"))
        
        all_swings.sort(key=lambda x: x[0])
        
        # Analyze sequence
        prev_high = None
        prev_low = None
        trend = "UNKNOWN"
        
        for i, (idx, price, swing_type) in enumerate(all_swings):
            ts = timestamps[idx] if idx < len(timestamps) else datetime.utcnow()
            
            if swing_type == "HIGH":
                if prev_high is not None:
                    if price > prev_high:
                        # Higher High
                        structure_sequence.append("HH")
                        
                        if trend == "BEARISH":
                            # CHOCH - trend change to bullish
                            strength = self._calculate_break_strength(price, prev_high, highs, idx)
                            choch_events.append(StructureEvent(
                                event_type=StructureEventType.CHOCH_BULLISH,
                                price=price,
                                timestamp=ts,
                                candle_index=idx,
                                strength=strength,
                                previous_swing=prev_high,
                                notes="Bullish CHOCH: Higher High after bearish structure"
                            ))
                            trend = "BULLISH"
                        elif trend == "BULLISH":
                            # BOS - continuation
                            strength = self._calculate_break_strength(price, prev_high, highs, idx)
                            bos_events.append(StructureEvent(
                                event_type=StructureEventType.BOS_BULLISH,
                                price=price,
                                timestamp=ts,
                                candle_index=idx,
                                strength=strength,
                                previous_swing=prev_high,
                                notes="Bullish BOS: Higher High continuation"
                            ))
                        else:
                            trend = "BULLISH"
                    else:
                        # Lower High
                        structure_sequence.append("LH")
                        if trend == "BULLISH":
                            trend = "TRANSITIONING"
                
                prev_high = price
                
            else:  # LOW
                if prev_low is not None:
                    if price < prev_low:
                        # Lower Low
                        structure_sequence.append("LL")
                        
                        if trend == "BULLISH":
                            # CHOCH - trend change to bearish
                            strength = self._calculate_break_strength(price, prev_low, lows, idx, bearish=True)
                            choch_events.append(StructureEvent(
                                event_type=StructureEventType.CHOCH_BEARISH,
                                price=price,
                                timestamp=ts,
                                candle_index=idx,
                                strength=strength,
                                previous_swing=prev_low,
                                notes="Bearish CHOCH: Lower Low after bullish structure"
                            ))
                            trend = "BEARISH"
                        elif trend == "BEARISH":
                            # BOS - continuation
                            strength = self._calculate_break_strength(price, prev_low, lows, idx, bearish=True)
                            bos_events.append(StructureEvent(
                                event_type=StructureEventType.BOS_BEARISH,
                                price=price,
                                timestamp=ts,
                                candle_index=idx,
                                strength=strength,
                                previous_swing=prev_low,
                                notes="Bearish BOS: Lower Low continuation"
                            ))
                        else:
                            trend = "BEARISH"
                    else:
                        # Higher Low
                        structure_sequence.append("HL")
                        if trend == "BEARISH":
                            trend = "TRANSITIONING"
                
                prev_low = price
        
        return bos_events, choch_events
    
    def _calculate_break_strength(
        self,
        current_price: float,
        previous_swing: float,
        prices: List[float],
        idx: int,
        bearish: bool = False
    ) -> float:
        """
        Рассчитать силу пробития структуры.
        
        Учитывает:
        - Величину пробития (% от предыдущего свинга)
        - Импульсивность движения
        - Позицию в контексте недавних цен
        """
        if previous_swing <= 0 or current_price <= 0:
            return 0.5
        
        # 1. Break magnitude (how much price broke through)
        if bearish:
            break_pct = (previous_swing - current_price) / previous_swing * 100
        else:
            break_pct = (current_price - previous_swing) / previous_swing * 100
        
        magnitude_score = min(1.0, break_pct / 2.0)  # 2% break = max score
        
        # 2. Momentum factor (how fast did price reach this level)
        lookback = min(5, idx)
        if lookback > 0:
            recent_prices = prices[idx-lookback:idx+1]
            if len(recent_prices) > 1:
                price_change = abs(recent_prices[-1] - recent_prices[0]) / recent_prices[0]
                momentum_score = min(1.0, price_change * 20)  # 5% move in 5 bars = 1.0
            else:
                momentum_score = 0.5
        else:
            momentum_score = 0.5
        
        # 3. Context score (is this a clean break or choppy)
        context_lookback = min(10, idx)
        if context_lookback > 2:
            context_prices = prices[idx-context_lookback:idx]
            avg_price = sum(context_prices) / len(context_prices)
            
            if bearish:
                context_score = 0.7 if current_price < avg_price else 0.4
            else:
                context_score = 0.7 if current_price > avg_price else 0.4
        else:
            context_score = 0.5
        
        # Combined strength
        strength = magnitude_score * 0.4 + momentum_score * 0.35 + context_score * 0.25
        
        return round(max(0.3, min(0.95, strength)), 4)
    
    def _calculate_swing_strength(
        self,
        highs: List[float],
        lows: List[float],
        idx: int,
        swing_type: str
    ) -> float:
        """Рассчитать силу свинг-точки"""
        lookback = min(10, idx)
        lookahead = min(10, len(highs) - idx - 1)
        
        if swing_type == "high":
            # How much higher than surrounding
            surrounding = highs[max(0, idx-lookback):idx+lookahead+1]
            if len(surrounding) > 1:
                prominence = (highs[idx] - min(surrounding)) / highs[idx]
                return min(1.0, prominence * 10)
        else:
            surrounding = lows[max(0, idx-lookback):idx+lookahead+1]
            if len(surrounding) > 1:
                prominence = (max(surrounding) - lows[idx]) / lows[idx]
                return min(1.0, prominence * 10)
        
        return 0.5
    
    def _determine_trend(
        self,
        bos_events: List[StructureEvent],
        choch_events: List[StructureEvent],
        swing_highs: List[Tuple[int, float]],
        swing_lows: List[Tuple[int, float]]
    ) -> TrendStructure:
        """Определить структуру тренда"""
        # Recent events have more weight
        recent_bos_bullish = sum(1 for e in bos_events[-3:] if e.event_type == StructureEventType.BOS_BULLISH)
        recent_bos_bearish = sum(1 for e in bos_events[-3:] if e.event_type == StructureEventType.BOS_BEARISH)
        
        recent_choch_bullish = sum(1 for e in choch_events[-2:] if e.event_type == StructureEventType.CHOCH_BULLISH)
        recent_choch_bearish = sum(1 for e in choch_events[-2:] if e.event_type == StructureEventType.CHOCH_BEARISH)
        
        # Check swing progression
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            last_two_highs = [h[1] for h in swing_highs[-2:]]
            last_two_lows = [l[1] for l in swing_lows[-2:]]
            
            hh = last_two_highs[-1] > last_two_highs[-2] if len(last_two_highs) == 2 else False
            hl = last_two_lows[-1] > last_two_lows[-2] if len(last_two_lows) == 2 else False
            lh = last_two_highs[-1] < last_two_highs[-2] if len(last_two_highs) == 2 else False
            ll = last_two_lows[-1] < last_two_lows[-2] if len(last_two_lows) == 2 else False
            
            if hh and hl:
                return TrendStructure.BULLISH
            elif lh and ll:
                return TrendStructure.BEARISH
        
        # Use events
        if recent_choch_bullish > 0:
            return TrendStructure.TRANSITIONING if recent_bos_bearish > 0 else TrendStructure.BULLISH
        elif recent_choch_bearish > 0:
            return TrendStructure.TRANSITIONING if recent_bos_bullish > 0 else TrendStructure.BEARISH
        elif recent_bos_bullish > recent_bos_bearish:
            return TrendStructure.BULLISH
        elif recent_bos_bearish > recent_bos_bullish:
            return TrendStructure.BEARISH
        
        return TrendStructure.NEUTRAL
    
    def _calculate_confidence(
        self,
        bos_events: List[StructureEvent],
        choch_events: List[StructureEvent],
        trend: TrendStructure
    ) -> float:
        """Рассчитать уверенность в структуре"""
        if trend == TrendStructure.NEUTRAL:
            return 0.3
        
        if trend == TrendStructure.TRANSITIONING:
            return 0.4
        
        # Base confidence from BOS count
        bos_same_direction = 0
        if trend == TrendStructure.BULLISH:
            bos_same_direction = sum(1 for e in bos_events if e.event_type == StructureEventType.BOS_BULLISH)
        else:
            bos_same_direction = sum(1 for e in bos_events if e.event_type == StructureEventType.BOS_BEARISH)
        
        confidence = min(0.9, 0.4 + bos_same_direction * 0.1)
        
        # Reduce if recent CHOCH against trend
        recent_against = sum(1 for e in choch_events[-2:] 
                           if (trend == TrendStructure.BULLISH and e.event_type == StructureEventType.CHOCH_BEARISH) or
                              (trend == TrendStructure.BEARISH and e.event_type == StructureEventType.CHOCH_BULLISH))
        
        if recent_against > 0:
            confidence *= 0.7
        
        return round(confidence, 4)
    
    def _empty_result(self) -> Dict[str, Any]:
        """Пустой результат"""
        return {
            "trend_structure": TrendStructure.NEUTRAL,
            "structure_confidence": 0.0,
            "bos_events": [],
            "choch_events": [],
            "swing_points": [],
            "bos_count": 0,
            "choch_count": 0
        }
