"""
Strong Pivot Filter
===================

Фильтрует pivot'ы по качеству - убирает "шумовые" точки.

КРИТЕРИИ СИЛЬНОГО PIVOT:
1. Реакция после касания (move > ATR * 0.5)
2. Визуальная значимость (выделяется на графике)
3. Не слишком близко к другим pivot'ам
"""

from typing import List, Dict, Tuple


class StrongPivotFilter:
    """Filter pivots by quality to remove noise."""
    
    def __init__(self, atr: float = 0.0, min_distance: int = 3):
        self.atr = atr
        self.min_distance = min_distance
        self.reaction_multiplier = 0.5  # move > ATR * 0.5 = strong
    
    def filter_strong_pivots(
        self, 
        pivots: List[Dict], 
        candles: List[Dict]
    ) -> List[Dict]:
        """
        Filter pivots to keep only strong ones.
        
        Strong pivot criteria:
        1. Has reaction after touch (price moves away)
        2. Not too close to another pivot
        3. Visually significant
        """
        if not pivots or not candles:
            return []
        
        # Calculate ATR if not provided
        if self.atr <= 0:
            self.atr = self._calc_atr(candles)
        
        strong = []
        reaction_threshold = self.atr * self.reaction_multiplier
        
        for p in pivots:
            idx = p.get("index", 0)
            price = p.get("price", p.get("value", 0))
            pivot_type = p.get("type", p.get("pivot_type", ""))
            
            # Check reaction after pivot
            reaction = self._check_reaction(candles, idx, price, pivot_type, reaction_threshold)
            
            if not reaction:
                continue
            
            # Check distance from existing strong pivots
            if self._is_too_close(strong, idx):
                continue
            
            # Add strength score
            p["strength"] = reaction
            p["is_strong"] = True
            strong.append(p)
        
        return strong
    
    def filter_strong_highs(self, highs: List[Dict], candles: List[Dict]) -> List[Dict]:
        """Filter only strong swing highs."""
        for h in highs:
            h["type"] = "H"
        return self.filter_strong_pivots(highs, candles)
    
    def filter_strong_lows(self, lows: List[Dict], candles: List[Dict]) -> List[Dict]:
        """Filter only strong swing lows."""
        for l in lows:
            l["type"] = "L"
        return self.filter_strong_pivots(lows, candles)
    
    def _check_reaction(
        self, 
        candles: List[Dict], 
        pivot_idx: int, 
        pivot_price: float,
        pivot_type: str,
        threshold: float
    ) -> float:
        """
        Check if there's a reaction after the pivot.
        Returns reaction strength (0 if no reaction).
        """
        if pivot_idx + 1 >= len(candles):
            return 0.0
        
        # Look at next 1-3 candles for reaction
        max_look = min(3, len(candles) - pivot_idx - 1)
        
        for i in range(1, max_look + 1):
            next_candle = candles[pivot_idx + i]
            
            if pivot_type in ["H", "high"]:
                # For swing high, expect price to move DOWN
                move = pivot_price - next_candle.get("close", pivot_price)
            else:
                # For swing low, expect price to move UP
                move = next_candle.get("close", pivot_price) - pivot_price
            
            if move > threshold:
                return move / threshold  # Normalize strength
        
        return 0.0
    
    def _is_too_close(self, existing: List[Dict], new_idx: int) -> bool:
        """Check if new pivot is too close to existing ones."""
        for p in existing:
            if abs(p.get("index", 0) - new_idx) < self.min_distance:
                return True
        return False
    
    def _calc_atr(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate ATR."""
        if len(candles) < period + 1:
            return 0.0
        
        tr_values = []
        for i in range(1, len(candles)):
            h = candles[i].get("high", 0)
            l = candles[i].get("low", 0)
            pc = candles[i-1].get("close", 0)
            tr = max(h - l, abs(h - pc), abs(l - pc))
            tr_values.append(tr)
        
        if len(tr_values) < period:
            return sum(tr_values) / len(tr_values) if tr_values else 0.0
        
        return sum(tr_values[-period:]) / period


def get_strong_pivot_filter(atr: float = 0.0, min_distance: int = 3) -> StrongPivotFilter:
    return StrongPivotFilter(atr=atr, min_distance=min_distance)
