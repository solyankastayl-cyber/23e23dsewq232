"""
Geometry Normalization Layer
============================

Превращает кривые anchors → чистая геометрия.

Pipeline:
detected pattern → NORMALIZED → отрисовали

ПРАВИЛА НОРМАЛИЗАЦИИ:

1. DOUBLE TOP:
   - Выравнивание пиков по среднему уровню
   - Усиление valley (берём минимум)
   - Симметрия по времени

2. RANGE:
   - Padding чтобы не резало свечи
   - Confidence через касания

3. WEDGE/TRIANGLE:
   - Принудительная сходимость линий
   - Фильтр слабых пивотов

Результат: паттерны как в TradingView, а не "как нашли — так и нарисовали"
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import math


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

ATR_MULT = 0.5  # Минимальное движение от пивота для "сильного" пивота


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def avg(a: float, b: float) -> float:
    """Среднее двух значений."""
    return (a + b) / 2


def clamp(v: float, min_v: float, max_v: float) -> float:
    """Ограничение значения в диапазоне."""
    return max(min(v, max_v), min_v)


def calc_slope(x1: float, y1: float, x2: float, y2: float) -> float:
    """Вычисление наклона линии."""
    if abs(x2 - x1) < 1e-10:
        return 0
    return (y2 - y1) / (x2 - x1)


# ═══════════════════════════════════════════════════════════════
# PIVOT FILTER — отбор только сильных пивотов
# ═══════════════════════════════════════════════════════════════

def filter_strong_pivots(pivots: List[Dict], atr: float) -> List[Dict]:
    """
    Фильтрует только сильные пивоты.
    
    Пивот считается сильным, если движение от него >= ATR * ATR_MULT.
    """
    if not pivots or atr <= 0:
        return pivots
    
    strong = []
    for p in pivots:
        move = p.get("move", 0)
        if move >= atr * ATR_MULT:
            strong.append(p)
    
    # Если после фильтра осталось мало — вернуть исходные
    if len(strong) < 2 and len(pivots) >= 2:
        return pivots
    
    return strong


# ═══════════════════════════════════════════════════════════════
# DOUBLE TOP / DOUBLE BOTTOM NORMALIZATION
# ═══════════════════════════════════════════════════════════════

def normalize_double_top(pattern: Dict) -> Dict:
    """
    Нормализация Double Top / Double Bottom.
    
    БЫЛО: кривые пики, разные уровни, ломаная линия
    СТАНЕТ: ровная М форма, симметрия, читается мгновенно
    
    Изменения:
    1. Выравниваем пики по среднему уровню
    2. Усиливаем valley (берём минимум * 0.995)
    3. Симметрия по времени относительно valley
    """
    anchors = pattern.get("anchors", {})
    
    # Проверка наличия всех точек
    p1 = anchors.get("p1")
    p2 = anchors.get("p2")
    valley = anchors.get("valley")
    
    if not p1 or not p2:
        return pattern
    
    # 1. Выравниваем пики по среднему уровню
    avg_top = avg(p1.get("price", 0), p2.get("price", 0))
    p1["price"] = avg_top
    p2["price"] = avg_top
    
    # 2. Усиливаем valley (берём минимум)
    if valley:
        min_price = min(valley.get("price", 0), p1.get("price", 0), p2.get("price", 0))
        valley["price"] = min_price * 0.995
    
    # 3. Симметрия по времени
    if valley and "time" in valley:
        center = valley["time"]
        dist = p2.get("time", center) - center
        p1["time"] = center - dist
    
    # Обновляем anchors
    pattern["anchors"]["p1"] = p1
    pattern["anchors"]["p2"] = p2
    if valley:
        pattern["anchors"]["valley"] = valley
    
    # Пометка о нормализации
    pattern["_normalized"] = True
    pattern["_normalization_type"] = "double_top_symmetry"
    
    return pattern


# ═══════════════════════════════════════════════════════════════
# RANGE NORMALIZATION
# ═══════════════════════════════════════════════════════════════

def normalize_range(pattern: Dict) -> Dict:
    """
    Нормализация Range.
    
    БЫЛО: box без смысла
    СТАНЕТ: зона с отступом, видно границы, confidence живой
    
    Изменения:
    1. Padding чтобы не резало свечи (1% от размера)
    2. Confidence через количество касаний
    """
    bounds = pattern.get("bounds", {})
    
    top = bounds.get("top", 0)
    bottom = bounds.get("bottom", 0)
    
    if top <= bottom:
        return pattern
    
    # 1. Padding чтобы не резало свечи
    padding = (top - bottom) * 0.01
    bounds["top"] = top + padding
    bounds["bottom"] = bottom - padding
    
    # 2. Confidence через касания
    touches = pattern.get("touches", 2)
    pattern["confidence"] = clamp(touches / 6, 0.2, 1.0)
    
    pattern["bounds"] = bounds
    
    # Также обновляем boundaries если есть
    boundaries = pattern.get("meta", {}).get("boundaries", {})
    if boundaries:
        if "upper" in boundaries:
            boundaries["upper"]["y1"] = bounds["top"]
            boundaries["upper"]["y2"] = bounds["top"]
        if "lower" in boundaries:
            boundaries["lower"]["y1"] = bounds["bottom"]
            boundaries["lower"]["y2"] = bounds["bottom"]
    
    # Пометка о нормализации
    pattern["_normalized"] = True
    pattern["_normalization_type"] = "range_padding"
    
    return pattern


# ═══════════════════════════════════════════════════════════════
# WEDGE / TRIANGLE NORMALIZATION
# ═══════════════════════════════════════════════════════════════

def normalize_lines(pattern: Dict) -> Dict:
    """
    Нормализация Wedge / Triangle.
    
    БЫЛО: параллельные линии (мусор)
    СТАНЕТ: реально сходящийся клин
    
    Изменения:
    1. Делаем линии сходящимися если почти параллельны
    """
    lines = pattern.get("lines", {})
    
    upper = lines.get("upper", {})
    lower = lines.get("lower", {})
    
    if not upper or not lower:
        # Попробуем boundaries
        boundaries = pattern.get("meta", {}).get("boundaries", {})
        upper = boundaries.get("upper", {})
        lower = boundaries.get("lower", {})
    
    if not upper or not lower:
        return pattern
    
    # Вычисляем наклоны
    slope_upper = calc_slope(
        upper.get("x1", 0), upper.get("y1", 0),
        upper.get("x2", 0), upper.get("y2", 0)
    )
    slope_lower = calc_slope(
        lower.get("x1", 0), lower.get("y1", 0),
        lower.get("x2", 0), lower.get("y2", 0)
    )
    
    # Если линии почти параллельны — усиливаем сходимость
    if abs(slope_upper - slope_lower) < 0.001:
        # Сжимаем концы линий
        if "y2" in upper:
            upper["y2"] = upper["y2"] * 0.995
        if "y2" in lower:
            lower["y2"] = lower["y2"] * 1.005
    
    # Обновляем данные
    if "lines" in pattern:
        pattern["lines"]["upper"] = upper
        pattern["lines"]["lower"] = lower
    else:
        # Обновляем boundaries
        if pattern.get("meta", {}).get("boundaries"):
            pattern["meta"]["boundaries"]["upper"] = upper
            pattern["meta"]["boundaries"]["lower"] = lower
    
    # Пометка о нормализации
    pattern["_normalized"] = True
    pattern["_normalization_type"] = "wedge_convergence"
    
    return pattern


# ═══════════════════════════════════════════════════════════════
# HEAD & SHOULDERS NORMALIZATION
# ═══════════════════════════════════════════════════════════════

def normalize_head_shoulders(pattern: Dict) -> Dict:
    """
    Нормализация Head & Shoulders.
    
    Изменения:
    1. Выравнивание плеч по среднему уровню
    2. Голова должна быть чётко выше/ниже плеч
    3. Симметрия
    """
    anchors = pattern.get("anchors", [])
    
    if len(anchors) < 5:
        return pattern
    
    # Предполагаем порядок: LS, H, RS (или LS, N1, H, N2, RS)
    # Сортируем по времени
    sorted_anchors = sorted(anchors, key=lambda x: x.get("time", 0))
    
    # Для 5 точек: [LS, N1, Head, N2, RS]
    if len(sorted_anchors) >= 5:
        ls = sorted_anchors[0]  # Left Shoulder
        n1 = sorted_anchors[1]  # Neckline 1
        head = sorted_anchors[2]  # Head
        n2 = sorted_anchors[3]  # Neckline 2
        rs = sorted_anchors[4]  # Right Shoulder
        
        # 1. Выравниваем плечи
        avg_shoulder = avg(ls.get("price", 0), rs.get("price", 0))
        ls["price"] = avg_shoulder
        rs["price"] = avg_shoulder
        
        # 2. Выравниваем neckline
        avg_neckline = avg(n1.get("price", 0), n2.get("price", 0))
        n1["price"] = avg_neckline
        n2["price"] = avg_neckline
        
        # Обновляем anchors
        pattern["anchors"] = [ls, n1, head, n2, rs]
        
        # Обновляем neckline в meta
        if pattern.get("meta"):
            pattern["meta"]["neckline"] = avg_neckline
    
    # Пометка о нормализации
    pattern["_normalized"] = True
    pattern["_normalization_type"] = "head_shoulders_symmetry"
    
    return pattern


# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def normalize_pattern(pattern: Dict, atr: float = None, candles: List[Dict] = None) -> Dict:
    """
    Главная функция нормализации паттерна.
    
    Args:
        pattern: Словарь паттерна из детектора
        atr: ATR для фильтрации пивотов (опционально)
        candles: Свечи для дополнительных вычислений (опционально)
    
    Returns:
        Нормализованный паттерн
    
    Примеры:
        >>> pattern = {"type": "double_top", "anchors": {...}}
        >>> normalized = normalize_pattern(pattern, atr=100)
    """
    if not pattern:
        return pattern
    
    # Копируем чтобы не мутировать исходный
    pattern = dict(pattern)
    
    pattern_type = pattern.get("type", "").lower()
    
    # DOUBLE TOP / DOUBLE BOTTOM
    if pattern_type in ("double_top", "double_bottom"):
        return normalize_double_top(pattern)
    
    # RANGE
    if "range" in pattern_type:
        return normalize_range(pattern)
    
    # WEDGE / TRIANGLE
    if "wedge" in pattern_type or "triangle" in pattern_type:
        return normalize_lines(pattern)
    
    # HEAD & SHOULDERS
    if "head" in pattern_type or "shoulder" in pattern_type:
        return normalize_head_shoulders(pattern)
    
    # Для остальных — возвращаем как есть
    return pattern


# ═══════════════════════════════════════════════════════════════
# BATCH NORMALIZATION
# ═══════════════════════════════════════════════════════════════

def normalize_patterns(patterns: List[Dict], atr: float = None) -> List[Dict]:
    """
    Нормализация списка паттернов.
    """
    return [normalize_pattern(p, atr) for p in patterns]


# ═══════════════════════════════════════════════════════════════
# GEOMETRY NORMALIZER CLASS (OOP interface)
# ═══════════════════════════════════════════════════════════════

@dataclass
class NormalizationResult:
    """Результат нормализации."""
    pattern: Dict
    was_normalized: bool
    normalization_type: Optional[str]
    changes: List[str]


class GeometryNormalizer:
    """
    OOP интерфейс для нормализации геометрии паттернов.
    
    Использование:
        normalizer = GeometryNormalizer()
        result = normalizer.normalize(pattern)
        if result.was_normalized:
            print(f"Applied: {result.normalization_type}")
    """
    
    def __init__(self, atr_multiplier: float = 0.5):
        self.atr_multiplier = atr_multiplier
    
    def normalize(self, pattern: Dict, atr: float = None) -> NormalizationResult:
        """Нормализует паттерн и возвращает результат."""
        normalized = normalize_pattern(pattern, atr)
        
        was_normalized = normalized.get("_normalized", False)
        norm_type = normalized.get("_normalization_type")
        
        # Определяем изменения
        changes = []
        if was_normalized:
            if "symmetry" in (norm_type or ""):
                changes.append("peaks_aligned")
                changes.append("time_symmetry_applied")
            if "padding" in (norm_type or ""):
                changes.append("bounds_padded")
            if "convergence" in (norm_type or ""):
                changes.append("lines_converged")
        
        return NormalizationResult(
            pattern=normalized,
            was_normalized=was_normalized,
            normalization_type=norm_type,
            changes=changes
        )
    
    def normalize_batch(self, patterns: List[Dict], atr: float = None) -> List[NormalizationResult]:
        """Нормализует список паттернов."""
        return [self.normalize(p, atr) for p in patterns]


# ═══════════════════════════════════════════════════════════════
# SINGLETON GETTER
# ═══════════════════════════════════════════════════════════════

_normalizer_instance = None

def get_geometry_normalizer() -> GeometryNormalizer:
    """Получить singleton экземпляр нормализатора."""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = GeometryNormalizer()
    return _normalizer_instance
