"""
Impulse Engine - Layer 2
========================

Детекция импульсів та контексту.
Визначає:
- Був чи імпульс?
- В якому напрямку?
- Яка сила?

Це КРИТИЧНИЙ шар - без нього range безглуздий.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime


class ImpulseEngine:
    """
    Impulse Engine V1 - визначення імпульсних рухів.
    
    Імпульс = сильний спрямований рух за короткий час.
    Після імпульсу зазвичай йде:
    - Корекція (pullback)
    - Баланс (range/consolidation)
    - Продовження (continuation)
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Пороги для визначення імпульсу
        self.impulse_threshold_pct = self.config.get("impulse_threshold_pct", 0.05)  # 5%
        self.strong_impulse_pct = self.config.get("strong_impulse_pct", 0.10)  # 10%
        self.impulse_bars = self.config.get("impulse_bars", 5)  # за скільки барів
        
        # ATR multiplier для динамічного порогу
        self.atr_multiplier = self.config.get("atr_multiplier", 2.0)
    
    def detect_impulse(self, candles: List[Dict]) -> Dict:
        """
        Основна функція детекції імпульсу.
        
        Returns:
            {
                "has_impulse": bool,
                "direction": "bullish" | "bearish" | "none",
                "strength": "weak" | "moderate" | "strong" | "extreme",
                "magnitude": float,  # % руху
                "bars_ago": int,  # скільки барів тому
                "start_price": float,
                "end_price": float,
                "context": str  # опис контексту
            }
        """
        if not candles or len(candles) < 10:
            return self._empty_result()
        
        # Аналізуємо останні N барів для пошуку імпульсу
        lookback = min(30, len(candles))
        recent = candles[-lookback:]
        
        # Знаходимо найсильніший рух в lookback
        impulse = self._find_strongest_impulse(recent)
        
        if not impulse["has_impulse"]:
            return impulse
        
        # Визначаємо контекст після імпульсу
        impulse["context"] = self._determine_context(candles, impulse)
        
        return impulse
    
    def _find_strongest_impulse(self, candles: List[Dict]) -> Dict:
        """Знаходить найсильніший імпульс в діапазоні."""
        
        best_impulse = None
        best_magnitude = 0
        
        # Скануємо вікна різного розміру
        for window_size in [3, 5, 7, 10]:
            if len(candles) < window_size:
                continue
                
            for i in range(len(candles) - window_size):
                window = candles[i:i + window_size]
                
                start_price = window[0]["open"]
                end_price = window[-1]["close"]
                high_in_window = max(c["high"] for c in window)
                low_in_window = min(c["low"] for c in window)
                
                # Bullish impulse
                bullish_move = (high_in_window - start_price) / start_price
                # Bearish impulse  
                bearish_move = (start_price - low_in_window) / start_price
                
                if bullish_move > best_magnitude and bullish_move > self.impulse_threshold_pct:
                    best_magnitude = bullish_move
                    best_impulse = {
                        "direction": "bullish",
                        "magnitude": bullish_move,
                        "start_price": start_price,
                        "end_price": high_in_window,
                        "start_idx": i,
                        "end_idx": i + window_size - 1,
                        "bars_ago": len(candles) - (i + window_size),
                    }
                
                if bearish_move > best_magnitude and bearish_move > self.impulse_threshold_pct:
                    best_magnitude = bearish_move
                    best_impulse = {
                        "direction": "bearish",
                        "magnitude": bearish_move,
                        "start_price": start_price,
                        "end_price": low_in_window,
                        "start_idx": i,
                        "end_idx": i + window_size - 1,
                        "bars_ago": len(candles) - (i + window_size),
                    }
        
        if not best_impulse:
            return self._empty_result()
        
        # Визначаємо силу
        strength = self._classify_strength(best_impulse["magnitude"])
        
        return {
            "has_impulse": True,
            "direction": best_impulse["direction"],
            "strength": strength,
            "magnitude": round(best_impulse["magnitude"] * 100, 2),  # у %
            "bars_ago": best_impulse["bars_ago"],
            "start_price": best_impulse["start_price"],
            "end_price": best_impulse["end_price"],
            "context": "",
        }
    
    def _classify_strength(self, magnitude: float) -> str:
        """Класифікує силу імпульсу."""
        if magnitude >= 0.15:
            return "extreme"
        elif magnitude >= 0.10:
            return "strong"
        elif magnitude >= 0.05:
            return "moderate"
        else:
            return "weak"
    
    def _determine_context(self, candles: List[Dict], impulse: Dict) -> str:
        """Визначає контекст після імпульсу."""
        
        bars_ago = impulse["bars_ago"]
        direction = impulse["direction"]
        
        if bars_ago <= 3:
            return f"fresh_{direction}_impulse"
        elif bars_ago <= 10:
            return f"recent_{direction}_impulse"
        elif bars_ago <= 20:
            return f"post_{direction}_consolidation"
        else:
            return f"old_{direction}_move"
    
    def _empty_result(self) -> Dict:
        return {
            "has_impulse": False,
            "direction": "none",
            "strength": "none",
            "magnitude": 0,
            "bars_ago": 0,
            "start_price": 0,
            "end_price": 0,
            "context": "no_impulse",
        }


# Singleton
_impulse_engine = None

def get_impulse_engine(config: Dict = None) -> ImpulseEngine:
    global _impulse_engine
    if _impulse_engine is None:
        _impulse_engine = ImpulseEngine(config)
    return _impulse_engine


def detect_impulse(candles: List[Dict], config: Dict = None) -> Dict:
    """Shortcut функція."""
    engine = get_impulse_engine(config)
    return engine.detect_impulse(candles)
