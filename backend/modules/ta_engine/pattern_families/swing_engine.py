"""
Swing Engine — Universal Swing Point Detection
===============================================

ONE engine that finds ALL significant highs/lows.
Used by ALL pattern families.

Provides:
- significant_highs
- significant_lows
- pivot_strength
- time_spacing
- reaction_strength
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SwingType(Enum):
    HIGH = "high"
    LOW = "low"


@dataclass
class SwingPoint:
    """A significant swing high or low."""
    type: SwingType
    index: int
    price: float
    timestamp: int
    strength: float  # 0-1, how significant
    touches: int     # how many times price tested this level
    reaction: float  # % move after this swing
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "index": self.index,
            "price": self.price,
            "timestamp": self.timestamp,
            "strength": round(self.strength, 3),
            "touches": self.touches,
            "reaction": round(self.reaction, 4),
        }


class SwingEngine:
    """
    Universal swing point detection.
    
    Config:
    - lookback: bars to check left/right for pivot
    - min_strength: minimum strength to qualify
    - min_spacing: minimum bars between swings
    - atr_filter: use ATR to filter noise
    """
    
    def __init__(self, config: Dict = None):
        config = config or {}
        self.lookback = config.get("lookback", 3)
        self.min_strength = config.get("min_strength", 0.3)
        self.min_spacing = config.get("min_spacing", 3)
        self.atr_multiplier = config.get("atr_multiplier", 0.5)
    
    def find_swings(
        self, 
        candles: List[Dict],
        lookback: int = None
    ) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        """
        Find all significant swing highs and lows.
        
        Returns:
            (swing_highs, swing_lows)
        """
        lookback = lookback or self.lookback
        
        if len(candles) < lookback * 2 + 1:
            return [], []
        
        # Calculate ATR for noise filtering
        atr = self._calculate_atr(candles)
        
        swing_highs = []
        swing_lows = []
        
        for i in range(lookback, len(candles) - lookback):
            candle = candles[i]
            high = candle.get("high", candle.get("close", 0))
            low = candle.get("low", candle.get("close", 0))
            
            # Check if swing high
            is_swing_high = self._is_swing_high(candles, i, lookback)
            if is_swing_high:
                strength = self._calculate_strength(candles, i, "high", atr)
                if strength >= self.min_strength:
                    reaction = self._calculate_reaction(candles, i, "high")
                    touches = self._count_touches(candles, high, atr, i)
                    
                    swing_highs.append(SwingPoint(
                        type=SwingType.HIGH,
                        index=i,
                        price=high,
                        timestamp=candle.get("time", candle.get("timestamp", i)),
                        strength=strength,
                        touches=touches,
                        reaction=reaction,
                    ))
            
            # Check if swing low
            is_swing_low = self._is_swing_low(candles, i, lookback)
            if is_swing_low:
                strength = self._calculate_strength(candles, i, "low", atr)
                if strength >= self.min_strength:
                    reaction = self._calculate_reaction(candles, i, "low")
                    touches = self._count_touches(candles, low, atr, i)
                    
                    swing_lows.append(SwingPoint(
                        type=SwingType.LOW,
                        index=i,
                        price=low,
                        timestamp=candle.get("time", candle.get("timestamp", i)),
                        strength=strength,
                        touches=touches,
                        reaction=reaction,
                    ))
        
        # Filter by minimum spacing
        swing_highs = self._filter_by_spacing(swing_highs)
        swing_lows = self._filter_by_spacing(swing_lows)
        
        return swing_highs, swing_lows
    
    def _is_swing_high(self, candles: List[Dict], idx: int, lookback: int) -> bool:
        """Check if index is a swing high."""
        high = candles[idx].get("high", candles[idx].get("close", 0))
        
        for j in range(idx - lookback, idx + lookback + 1):
            if j == idx or j < 0 or j >= len(candles):
                continue
            other_high = candles[j].get("high", candles[j].get("close", 0))
            if other_high > high:
                return False
        return True
    
    def _is_swing_low(self, candles: List[Dict], idx: int, lookback: int) -> bool:
        """Check if index is a swing low."""
        low = candles[idx].get("low", candles[idx].get("close", 0))
        
        for j in range(idx - lookback, idx + lookback + 1):
            if j == idx or j < 0 or j >= len(candles):
                continue
            other_low = candles[j].get("low", candles[j].get("close", 0))
            if other_low < low:
                return False
        return True
    
    def _calculate_atr(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(candles) < period + 1:
            return 0.01  # Default small value
        
        tr_sum = 0
        for i in range(1, min(period + 1, len(candles))):
            high = candles[i].get("high", candles[i].get("close", 0))
            low = candles[i].get("low", candles[i].get("close", 0))
            prev_close = candles[i-1].get("close", 0)
            
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_sum += tr
        
        return tr_sum / period if period > 0 else 0.01
    
    def _calculate_strength(
        self, 
        candles: List[Dict], 
        idx: int, 
        swing_type: str,
        atr: float
    ) -> float:
        """
        Calculate swing strength based on:
        - Depth from neighbors
        - Volume confirmation
        - Reaction after
        """
        if idx < 3 or idx >= len(candles) - 3:
            return 0.3
        
        candle = candles[idx]
        price = candle.get("high" if swing_type == "high" else "low", candle.get("close", 0))
        
        # Depth: how far above/below neighbors
        neighbors = []
        for j in range(max(0, idx - 3), min(len(candles), idx + 4)):
            if j != idx:
                n_price = candles[j].get("high" if swing_type == "high" else "low", 0)
                neighbors.append(n_price)
        
        if not neighbors:
            return 0.3
        
        avg_neighbor = sum(neighbors) / len(neighbors)
        depth = abs(price - avg_neighbor) / price if price > 0 else 0
        
        # Normalize depth (0.5% = 0.3 strength, 3% = 1.0 strength)
        depth_score = min(depth / 0.03, 1.0)
        
        # Volume confirmation
        volume = candle.get("volume", 0)
        avg_volume = sum(c.get("volume", 0) for c in candles[max(0, idx-10):idx]) / 10
        volume_score = min(volume / avg_volume, 2.0) / 2 if avg_volume > 0 else 0.5
        
        # Combined strength
        strength = (depth_score * 0.6 + volume_score * 0.4)
        return min(max(strength, 0.1), 1.0)
    
    def _calculate_reaction(self, candles: List[Dict], idx: int, swing_type: str) -> float:
        """Calculate % move after swing point."""
        if idx >= len(candles) - 5:
            return 0
        
        price = candles[idx].get("high" if swing_type == "high" else "low", candles[idx].get("close", 0))
        
        # Check next 5 candles
        if swing_type == "high":
            future_low = min(c.get("low", c.get("close", price)) for c in candles[idx+1:idx+6])
            return (price - future_low) / price if price > 0 else 0
        else:
            future_high = max(c.get("high", c.get("close", price)) for c in candles[idx+1:idx+6])
            return (future_high - price) / price if price > 0 else 0
    
    def _count_touches(
        self, 
        candles: List[Dict], 
        level: float, 
        atr: float,
        exclude_idx: int
    ) -> int:
        """Count how many times price touched this level."""
        tolerance = atr * self.atr_multiplier
        touches = 0
        
        for i, c in enumerate(candles):
            if i == exclude_idx:
                continue
            high = c.get("high", c.get("close", 0))
            low = c.get("low", c.get("close", 0))
            
            if low - tolerance <= level <= high + tolerance:
                touches += 1
        
        return min(touches, 10)  # Cap at 10
    
    def _filter_by_spacing(self, swings: List[SwingPoint]) -> List[SwingPoint]:
        """Filter swings that are too close together, keeping strongest."""
        if len(swings) <= 1:
            return swings
        
        # Sort by index
        swings = sorted(swings, key=lambda s: s.index)
        
        filtered = [swings[0]]
        for swing in swings[1:]:
            last = filtered[-1]
            if swing.index - last.index >= self.min_spacing:
                filtered.append(swing)
            elif swing.strength > last.strength:
                # Replace with stronger swing
                filtered[-1] = swing
        
        return filtered
    
    def get_recent_swings(
        self, 
        candles: List[Dict], 
        count: int = 5
    ) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        """Get most recent N swing highs and lows."""
        highs, lows = self.find_swings(candles)
        return highs[-count:], lows[-count:]
    
    def get_swing_sequence(
        self, 
        candles: List[Dict]
    ) -> List[SwingPoint]:
        """Get all swings in chronological order."""
        highs, lows = self.find_swings(candles)
        all_swings = highs + lows
        return sorted(all_swings, key=lambda s: s.index)


# Singleton instance
_swing_engine = None

def get_swing_engine(config: Dict = None) -> SwingEngine:
    global _swing_engine
    if _swing_engine is None or config:
        _swing_engine = SwingEngine(config)
    return _swing_engine
