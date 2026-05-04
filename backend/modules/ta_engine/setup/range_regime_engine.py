"""
Range Regime Engine v1.0
========================

ПРАВИЛЬНАЯ СЕМАНТИКА RANGE (БОКОВИКА):

Range — это НЕ "локальная коробка между касаниями".
Range — это РЕЖИМ РЫНКА, который:

1. НАЧИНАЕТСЯ с момента, когда цена перестала делать импульсное продолжение
   (после падения/роста вошла в баланс)

2. ПРОДОЛЖАЕТСЯ до подтверждённого выхода (breakout/breakdown)

3. ВИЗУАЛЬНО тянется ВПРАВО вперёд, пока нет пробоя

4. Рисуется ПАРАЛЛЕЛЬНЫМИ линиями (не сходящийся канал)

КЛЮЧЕВЫЕ ОТЛИЧИЯ от старого подхода:
- Старый: detect range window -> draw box (локальный кусок)
- Новый: detect balance regime -> define boundaries -> extend forward -> draw active range

ПРАВИЛО ЗАВЕРШЕНИЯ:
Range заканчивается ТОЛЬКО если есть:
- Закрытие выше верхней границы с подтверждением
- Закрытие ниже нижней границы с подтверждением
- Серия свечей вне диапазона
- Retest после выхода
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class RangeStage(str, Enum):
    """Стадии жизни range."""
    FORMING = "forming"           # Начинает формироваться
    ACTIVE = "active"             # Активный range, цена внутри
    TESTING_UPPER = "testing_upper"  # Тестирует верхнюю границу
    TESTING_LOWER = "testing_lower"  # Тестирует нижнюю границу
    BREAKOUT_UP = "breakout_up"   # Пробой вверх (ждём подтверждения)
    BREAKOUT_DOWN = "breakout_down"  # Пробой вниз (ждём подтверждения)
    CONFIRMED_UP = "confirmed_up"    # Подтверждённый выход вверх
    CONFIRMED_DOWN = "confirmed_down"  # Подтверждённый выход вниз
    INVALIDATED = "invalidated"   # Отменён (не был range)


@dataclass
class ActiveRangeZone:
    """
    Активная зона баланса (range).
    
    Это НЕ паттерн в классическом смысле.
    Это РЕЖИМ РЫНКА с временными границами.
    """
    # Идентификация
    symbol: str = ""
    timeframe: str = "1D"
    
    # Состояние
    stage: RangeStage = RangeStage.FORMING
    is_active: bool = True
    
    # Границы по цене (параллельные линии)
    top: float = 0.0
    bottom: float = 0.0
    mid: float = 0.0  # Середина range
    
    # Границы по времени
    left_boundary_time: int = 0      # Timestamp начала баланса
    right_boundary_time: int = 0     # now + extension (для визуализации)
    
    # Начало баланса (важно!)
    balance_start_index: int = 0     # Индекс свечи где начался баланс
    impulse_end_index: int = 0       # Где закончился предыдущий импульс
    
    # Текущая позиция
    current_index: int = 0
    current_price: float = 0.0
    
    # Метрики качества
    touch_count_upper: int = 0
    touch_count_lower: int = 0
    total_touches: int = 0
    respect_score: float = 0.0       # Насколько цена уважает границы
    range_width_pct: float = 0.0     # Ширина в %
    
    # Breakout tracking
    breakout_state: str = "none"     # none / testing / confirmed
    breakout_direction: str = ""     # up / down
    breakout_bar_count: int = 0      # Сколько баров вне range
    last_breakout_test: int = 0      # Когда последний раз тестировали границу
    
    # Forward extension (для визуализации)
    forward_bars: int = 10           # Сколько баров вперёд рисуем
    
    # Confidence
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "active_range",
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "stage": self.stage.value,
            "is_active": self.is_active,
            "top": round(self.top, 2),
            "bottom": round(self.bottom, 2),
            "mid": round(self.mid, 2),
            "left_boundary_time": self.left_boundary_time,
            "right_boundary_time": self.right_boundary_time,
            "balance_start_index": self.balance_start_index,
            "current_price": round(self.current_price, 2),
            "touch_count_upper": self.touch_count_upper,
            "touch_count_lower": self.touch_count_lower,
            "total_touches": self.total_touches,
            "respect_score": round(self.respect_score, 2),
            "range_width_pct": round(self.range_width_pct, 4),
            "breakout_state": self.breakout_state,
            "breakout_direction": self.breakout_direction,
            "forward_bars": self.forward_bars,
            "confidence": round(self.confidence, 2),
        }
    
    def to_render_data(self) -> Dict[str, Any]:
        """
        Данные для отрисовки на графике.
        
        ВАЖНО: right_boundary_time тянется ВПЕРЁД от текущей свечи!
        """
        return {
            "type": "range_zone",
            "render_type": "parallel_box",  # Параллельные линии, не сходящиеся
            "is_active": self.is_active,
            "stage": self.stage.value,
            # Границы для рисования
            "lines": {
                "upper": {
                    "start_time": self.left_boundary_time,
                    "end_time": self.right_boundary_time,
                    "price": self.top,
                    "style": "solid" if self.is_active else "dashed",
                    "color": "resistance",
                },
                "lower": {
                    "start_time": self.left_boundary_time,
                    "end_time": self.right_boundary_time,
                    "price": self.bottom,
                    "style": "solid" if self.is_active else "dashed",
                    "color": "support",
                },
                "mid": {
                    "start_time": self.left_boundary_time,
                    "end_time": self.right_boundary_time,
                    "price": self.mid,
                    "style": "dotted",
                    "color": "neutral",
                },
            },
            # Box для заливки
            "box": {
                "left": self.left_boundary_time,
                "right": self.right_boundary_time,
                "top": self.top,
                "bottom": self.bottom,
                "fill_opacity": 0.08 if self.is_active else 0.03,
            },
            # Метки
            "labels": {
                "top_label": f"R {self.top:.0f}",
                "bottom_label": f"S {self.bottom:.0f}",
                "stage_label": self.stage.value.replace("_", " ").title(),
            },
            "confidence": self.confidence,
        }


class RangeRegimeEngine:
    """
    Движок определения режима баланса (range).
    
    ЛОГИКА:
    1. Найти фазу баланса после импульса
    2. Определить границы (top/bottom)
    3. Держать range активным
    4. Тянуть box вправо (forward extension)
    5. Завершать ТОЛЬКО по breakout
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Параметры определения
        self.min_touches = self.config.get("min_touches", 1)  # Minimum 1 touch per boundary
        self.min_range_width = self.config.get("min_range_width", 0.02)  # 2%
        self.max_range_width = self.config.get("max_range_width", 0.25)  # 25% (increased for crypto)
        self.breakout_confirm_bars = self.config.get("breakout_confirm_bars", 2)
        
        # КРИТИЧНО: Forward extension на неделю+ вперёд
        # Для 1D timeframe: 7-14 баров = 1-2 недели
        # Для 4H timeframe: 42 бара = ~1 неделя
        self.forward_extension_bars = self.config.get("forward_extension_bars", 30)
        
        self.impulse_threshold = self.config.get("impulse_threshold", 0.05)  # 5% move
        
        # Tolerance для касаний (более широкий для волатильных активов)
        self.touch_tolerance_pct = self.config.get("touch_tolerance_pct", 0.03)  # 3%
        
        # Lookback для поиска начала баланса (сколько свечей назад смотреть)
        self.balance_lookback = self.config.get("balance_lookback", 80)  # 80 candles
    
    def detect_range_regime(
        self,
        candles: List[Dict],
        symbol: str = "",
        timeframe: str = "1D",
    ) -> Optional[ActiveRangeZone]:
        """
        Определить активный range regime.
        
        АЛГОРИТМ:
        1. Найти конец последнего импульса
        2. От этой точки искать начало баланса
        3. Определить границы по многократным касаниям
        4. Проверить что цена до сих пор внутри
        5. Если да — range активен, тянем вправо
        """
        if len(candles) < 50:
            return None
        
        # 1. Найти конец импульса (начало баланса)
        impulse_end, impulse_direction = self._find_impulse_end(candles)
        
        if impulse_end is None:
            # Нет явного импульса — проверяем весь диапазон
            impulse_end = 0
            impulse_direction = "unknown"
        
        # 2. Анализируем свечи от конца импульса до сейчас
        balance_candles = candles[impulse_end:]
        if len(balance_candles) < 10:  # Minimum 10 candles for range
            return None
        
        # 3. Определяем границы range (используем перцентили чтобы исключить outliers)
        highs = [c["high"] for c in balance_candles]
        lows = [c["low"] for c in balance_candles]
        
        # Используем 95-й и 5-й перцентили вместо max/min
        sorted_highs = sorted(highs)
        sorted_lows = sorted(lows)
        
        high_idx = int(len(sorted_highs) * 0.95)
        low_idx = int(len(sorted_lows) * 0.05)
        
        range_high = sorted_highs[min(high_idx, len(sorted_highs) - 1)]
        range_low = sorted_lows[low_idx]
        
        range_width = (range_high - range_low) / range_low if range_low > 0 else 0
        
        # Проверка ширины
        if range_width < self.min_range_width or range_width > self.max_range_width:
            return None
        
        # 4. Считаем касания границ
        tolerance = range_width * self.touch_tolerance_pct * 10
        upper_touches = []
        lower_touches = []
        
        for i, c in enumerate(balance_candles):
            # Верхняя граница
            if c["high"] >= range_high * (1 - tolerance):
                upper_touches.append(i)
            # Нижняя граница
            if c["low"] <= range_low * (1 + tolerance):
                lower_touches.append(i)
        
        # Нужно минимум min_touches на каждой границе
        if len(upper_touches) < self.min_touches or len(lower_touches) < self.min_touches:
            return None
        
        # 5. Проверяем respect score (реакции от границ)
        respect_score = self._calculate_respect_score(balance_candles, range_high, range_low, tolerance)
        
        # 6. Проверяем текущую позицию цены
        current_price = candles[-1]["close"]
        current_high = candles[-1]["high"]
        current_low = candles[-1]["low"]
        
        # Определяем стадию
        stage, breakout_state, breakout_dir = self._determine_stage(
            current_price, current_high, current_low,
            range_high, range_low, tolerance, candles
        )
        
        # 7. Timestamps для границ
        left_time = self._get_timestamp(balance_candles[0])
        current_time = self._get_timestamp(candles[-1])
        
        # Forward extension: добавляем N баров вперёд
        # Рассчитываем интервал между свечами
        if len(candles) >= 2:
            interval = self._get_timestamp(candles[-1]) - self._get_timestamp(candles[-2])
        else:
            interval = 86400  # Default 1 day
        
        right_time = current_time + interval * self.forward_extension_bars
        
        # 8. Создаём ActiveRangeZone
        confidence = self._calculate_confidence(
            len(upper_touches), len(lower_touches), 
            respect_score, range_width, stage
        )
        
        range_zone = ActiveRangeZone(
            symbol=symbol,
            timeframe=timeframe,
            stage=stage,
            is_active=(stage not in [RangeStage.CONFIRMED_UP, RangeStage.CONFIRMED_DOWN, RangeStage.INVALIDATED]),
            top=range_high,
            bottom=range_low,
            mid=(range_high + range_low) / 2,
            left_boundary_time=left_time,
            right_boundary_time=right_time,
            balance_start_index=impulse_end,
            impulse_end_index=impulse_end,
            current_index=len(candles) - 1,
            current_price=current_price,
            touch_count_upper=len(upper_touches),
            touch_count_lower=len(lower_touches),
            total_touches=len(upper_touches) + len(lower_touches),
            respect_score=respect_score,
            range_width_pct=range_width,
            breakout_state=breakout_state,
            breakout_direction=breakout_dir,
            forward_bars=self.forward_extension_bars,
            confidence=confidence,
        )
        
        return range_zone
    
    def _find_impulse_end(self, candles: List[Dict]) -> Tuple[Optional[int], str]:
        """
        Найти где закончился последний импульс (начало баланса).
        
        УЛУЧШЕННЫЙ АЛГОРИТМ v4:
        Range должен начинаться не от "первой красивой локальной точки",
        а от момента когда рынок вошёл в баланс после импульса.
        
        Логика:
        1. Ищем значимый экстремум (минимум после падения / максимум после роста)
        2. Этот экстремум = конец импульса = начало баланса
        3. Range покрывает ВЕСЬ балансный участок от этой точки
        """
        if len(candles) < 30:
            return None, "unknown"
        
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        
        # Используем расширенный lookback для поиска начала баланса
        lookback = min(self.balance_lookback, len(candles))
        recent_lows = lows[-lookback:]
        recent_highs = highs[-lookback:]
        
        # Находим абсолютный минимум и максимум в lookback окне
        min_price = min(recent_lows)
        min_idx = recent_lows.index(min_price)
        global_min_idx = len(candles) - lookback + min_idx
        
        max_price = max(recent_highs)
        max_idx = recent_highs.index(max_price)
        global_max_idx = len(candles) - lookback + max_idx
        
        # Определяем какой экстремум был РАНЬШЕ (это конец импульса)
        # Если минимум раньше максимума — был downtrend, потом баланс/рост
        # Если максимум раньше минимума — был uptrend, потом баланс/падение
        
        if min_idx < max_idx:
            # Минимум раньше — downtrend закончился, начался баланс
            # Range начинается от минимума
            impulse_end = global_min_idx
            direction = "down"
        else:
            # Максимум раньше — uptrend закончился, начался баланс
            # Range начинается от максимума
            impulse_end = global_max_idx
            direction = "up"
        
        # Дополнительная проверка: если экстремум слишком далеко (>70% lookback),
        # значит мы в долгом боковике — берём меньший lookback
        lookback_position = (len(candles) - impulse_end) / lookback
        if lookback_position > 0.7:
            # Экстремум слишком далеко, попробуем найти ближе
            shorter_lookback = lookback // 2
            recent_lows_short = lows[-shorter_lookback:]
            recent_highs_short = highs[-shorter_lookback:]
            
            min_price_short = min(recent_lows_short)
            min_idx_short = recent_lows_short.index(min_price_short)
            global_min_idx_short = len(candles) - shorter_lookback + min_idx_short
            
            max_price_short = max(recent_highs_short)
            max_idx_short = recent_highs_short.index(max_price_short)
            global_max_idx_short = len(candles) - shorter_lookback + max_idx_short
            
            if min_idx_short < max_idx_short:
                impulse_end = global_min_idx_short
            else:
                impulse_end = global_max_idx_short
        
        return impulse_end, direction
    
    def _calculate_respect_score(
        self, 
        candles: List[Dict], 
        range_high: float, 
        range_low: float,
        tolerance: float
    ) -> float:
        """
        Рассчитать насколько цена "уважает" границы.
        
        Высокий score = после касания границы цена разворачивается.
        Низкий score = цена пробивает и идёт дальше.
        """
        reactions = 0
        touches = 0
        
        for i in range(1, len(candles) - 1):
            c = candles[i]
            next_c = candles[i + 1]
            
            # Касание верхней границы
            if c["high"] >= range_high * (1 - tolerance):
                touches += 1
                # Проверяем реакцию (цена пошла вниз)
                if next_c["close"] < c["close"]:
                    reactions += 1
            
            # Касание нижней границы
            if c["low"] <= range_low * (1 + tolerance):
                touches += 1
                # Проверяем реакцию (цена пошла вверх)
                if next_c["close"] > c["close"]:
                    reactions += 1
        
        return reactions / touches if touches > 0 else 0.0
    
    def _determine_stage(
        self,
        current_price: float,
        current_high: float,
        current_low: float,
        range_high: float,
        range_low: float,
        tolerance: float,
        candles: List[Dict]
    ) -> Tuple[RangeStage, str, str]:
        """
        Определить текущую стадию range.
        """
        # Tolerance для breakout (ATR-based идеально, но упростим)
        breakout_tolerance = (range_high - range_low) * 0.1
        
        # Проверяем положение цены
        if current_price > range_high + breakout_tolerance:
            # Выше верхней границы
            # Проверяем подтверждение (N баров выше)
            bars_above = 0
            for c in candles[-self.breakout_confirm_bars:]:
                if c["close"] > range_high:
                    bars_above += 1
            
            if bars_above >= self.breakout_confirm_bars:
                return RangeStage.CONFIRMED_UP, "confirmed", "up"
            else:
                return RangeStage.BREAKOUT_UP, "testing", "up"
        
        elif current_price < range_low - breakout_tolerance:
            # Ниже нижней границы
            bars_below = 0
            for c in candles[-self.breakout_confirm_bars:]:
                if c["close"] < range_low:
                    bars_below += 1
            
            if bars_below >= self.breakout_confirm_bars:
                return RangeStage.CONFIRMED_DOWN, "confirmed", "down"
            else:
                return RangeStage.BREAKOUT_DOWN, "testing", "down"
        
        elif current_high >= range_high * (1 - tolerance * 0.5):
            # Тестирует верхнюю границу
            return RangeStage.TESTING_UPPER, "none", ""
        
        elif current_low <= range_low * (1 + tolerance * 0.5):
            # Тестирует нижнюю границу
            return RangeStage.TESTING_LOWER, "none", ""
        
        else:
            # Внутри range
            return RangeStage.ACTIVE, "none", ""
    
    def _calculate_confidence(
        self,
        upper_touches: int,
        lower_touches: int,
        respect_score: float,
        range_width: float,
        stage: RangeStage
    ) -> float:
        """Рассчитать confidence для range."""
        # Base score from touches
        total_touches = upper_touches + lower_touches
        touch_score = min(1.0, total_touches / 10) * 0.3
        
        # Respect score
        respect_bonus = respect_score * 0.3
        
        # Balance bonus (равное кол-во касаний)
        if upper_touches > 0 and lower_touches > 0:
            balance = min(upper_touches, lower_touches) / max(upper_touches, lower_touches)
            balance_bonus = balance * 0.2
        else:
            balance_bonus = 0
        
        # Width penalty (слишком широкий = хуже)
        if range_width > 0.15:
            width_penalty = 0.1
        else:
            width_penalty = 0
        
        # Stage bonus
        stage_bonus = 0
        if stage == RangeStage.ACTIVE:
            stage_bonus = 0.1
        elif stage in [RangeStage.TESTING_UPPER, RangeStage.TESTING_LOWER]:
            stage_bonus = 0.15
        
        confidence = 0.4 + touch_score + respect_bonus + balance_bonus + stage_bonus - width_penalty
        return min(0.95, max(0.4, confidence))
    
    def _get_timestamp(self, candle: Dict) -> int:
        """Получить timestamp из свечи."""
        ts = candle.get("time", candle.get("timestamp", 0))
        if ts > 1e12:
            ts = ts // 1000
        return int(ts)


# Singleton
_range_regime_engine: Optional[RangeRegimeEngine] = None


def get_range_regime_engine(config: Dict = None) -> RangeRegimeEngine:
    """Получить singleton instance."""
    global _range_regime_engine
    if _range_regime_engine is None or config:
        _range_regime_engine = RangeRegimeEngine(config)
    return _range_regime_engine


def detect_active_range(
    candles: List[Dict],
    symbol: str = "",
    timeframe: str = "1D",
    config: Dict = None
) -> Optional[Dict[str, Any]]:
    """
    Convenience function для определения активного range.
    
    Возвращает dict для рендера или None.
    """
    engine = get_range_regime_engine(config)
    range_zone = engine.detect_range_regime(candles, symbol, timeframe)
    
    if range_zone and range_zone.confidence >= 0.5:
        return range_zone.to_dict()
    
    return None
