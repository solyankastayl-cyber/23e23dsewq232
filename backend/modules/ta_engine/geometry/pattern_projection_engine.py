"""
Pattern Projection Engine
=========================

Строит полный контракт отрисовки паттерна:
1. STRUCTURE - сама фигура (points, lines, fill)
2. BOUNDS - границы/уровни (resistance, support, neckline)
3. COMPLETION - где заканчивается форма (apex, confirm_level)
4. PROJECTION - что дальше (primary target, secondary invalidation)

Это превращает "распознанную форму" в "модель поведения цены".
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import math


# ═══════════════════════════════════════════════════════════════
# ENUMS & DATA CLASSES
# ═══════════════════════════════════════════════════════════════

class PatternStage(Enum):
    """Стадия паттерна."""
    FORMING = "forming"          # Ещё формируется
    MATURING = "maturing"        # Близок к подтверждению
    CONFIRMED = "confirmed"      # Подтверждён (пробит уровень)
    INVALIDATED = "invalidated"  # Сломан


class ProjectionDirection(Enum):
    """Направление проекции."""
    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


@dataclass
class Point:
    """Точка на графике."""
    time: int
    price: float
    
    def to_dict(self) -> Dict:
        return {"time": self.time, "price": self.price}


@dataclass
class Line:
    """Линия между двумя точками."""
    p1: Point
    p2: Point
    
    def to_dict(self) -> Dict:
        return {
            "x1": self.p1.time, "y1": self.p1.price,
            "x2": self.p2.time, "y2": self.p2.price
        }


@dataclass
class ProjectionTarget:
    """Цель проекции."""
    direction: str  # "up" or "down"
    target: float
    path: List[Point] = field(default_factory=list)
    confidence: float = 0.5
    
    def to_dict(self) -> Dict:
        return {
            "direction": self.direction,
            "target": self.target,
            "path": [p.to_dict() for p in self.path],
            "confidence": self.confidence
        }


@dataclass
class PatternProjectionContract:
    """
    Полный контракт для отрисовки паттерна.
    
    Содержит все 4 слоя:
    - structure: геометрия фигуры
    - bounds: уровни (resistance, support)
    - completion: завершение фигуры
    - projection: сценарии движения цены
    """
    pattern_type: str
    stage: str
    
    # LAYER 1: Structure
    structure_points: List[Point]
    structure_lines: List[Line]
    structure_fill: bool
    
    # LAYER 2: Bounds
    resistance: Optional[float] = None
    support: Optional[float] = None
    neckline: Optional[float] = None
    upper_line: Optional[Line] = None
    lower_line: Optional[Line] = None
    
    # LAYER 3: Completion
    end_time: Optional[int] = None
    apex: Optional[Point] = None
    confirm_level: Optional[float] = None
    invalidation_level: Optional[float] = None
    
    # LAYER 4: Projection
    primary_projection: Optional[ProjectionTarget] = None
    secondary_projection: Optional[ProjectionTarget] = None
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь для JSON."""
        return {
            "type": self.pattern_type,
            "stage": self.stage,
            
            "structure": {
                "points": [p.to_dict() for p in self.structure_points],
                "lines": [line.to_dict() for line in self.structure_lines],
                "fill": self.structure_fill
            },
            
            "bounds": {
                "resistance": self.resistance,
                "support": self.support,
                "neckline": self.neckline,
                "upper_line": self.upper_line.to_dict() if self.upper_line else None,
                "lower_line": self.lower_line.to_dict() if self.lower_line else None
            },
            
            "completion": {
                "end_time": self.end_time,
                "apex": self.apex.to_dict() if self.apex else None,
                "confirm_level": self.confirm_level,
                "invalidation_level": self.invalidation_level
            },
            
            "projection": {
                "primary": self.primary_projection.to_dict() if self.primary_projection else None,
                "secondary": self.secondary_projection.to_dict() if self.secondary_projection else None
            }
        }


# ═══════════════════════════════════════════════════════════════
# DOUBLE TOP / DOUBLE BOTTOM PROJECTOR
# ═══════════════════════════════════════════════════════════════

def build_double_top_projection(
    p1: Dict, 
    valley: Dict, 
    p2: Dict,
    current_price: float = None,
    neckline_broken: bool = False
) -> PatternProjectionContract:
    """
    Строит полную проекцию для Double Top.
    
    Визуал:
       P1      P2
        /\    /\
         \____/   ← fill зона
    ----------- neckline -----------
          ↓
          ↓
       target down
    """
    # Нормализация пиков
    avg_top = (p1["price"] + p2["price"]) / 2
    neckline = valley["price"]
    
    # Points для structure
    pt_p1 = Point(p1["time"], avg_top)
    pt_valley = Point(valley["time"], neckline)
    pt_p2 = Point(p2["time"], avg_top)
    
    # Height для measured move
    height = avg_top - neckline
    
    # Targets
    target_down = neckline - height
    target_up = avg_top + height * 0.5  # Invalidation target
    
    # Stage determination
    if neckline_broken:
        stage = PatternStage.CONFIRMED.value
    elif current_price and current_price < neckline * 1.01:
        stage = PatternStage.MATURING.value
    else:
        stage = PatternStage.FORMING.value
    
    # Primary projection (DOWN)
    primary = ProjectionTarget(
        direction="down",
        target=target_down,
        path=[
            Point(p2["time"], neckline),
            Point(p2["time"] + 10, target_down)
        ],
        confidence=0.68 if neckline_broken else 0.55
    )
    
    # Secondary projection (UP - invalidation)
    secondary = ProjectionTarget(
        direction="up",
        target=target_up,
        path=[
            pt_p2,
            Point(p2["time"] + 6, target_up)
        ],
        confidence=0.32
    )
    
    return PatternProjectionContract(
        pattern_type="double_top",
        stage=stage,
        
        # Structure
        structure_points=[pt_p1, pt_valley, pt_p2],
        structure_lines=[
            Line(pt_p1, pt_valley),
            Line(pt_valley, pt_p2)
        ],
        structure_fill=True,
        
        # Bounds
        resistance=avg_top,
        support=neckline,
        neckline=neckline,
        
        # Completion
        end_time=p2["time"] + 5,
        confirm_level=neckline,
        invalidation_level=avg_top * 1.01,
        
        # Projection
        primary_projection=primary,
        secondary_projection=secondary
    )


def build_double_bottom_projection(
    p1: Dict, 
    peak: Dict, 
    p2: Dict,
    current_price: float = None,
    neckline_broken: bool = False
) -> PatternProjectionContract:
    """
    Строит полную проекцию для Double Bottom.
    Зеркально от Double Top.
    """
    # Нормализация
    avg_bottom = (p1["price"] + p2["price"]) / 2
    neckline = peak["price"]
    
    pt_p1 = Point(p1["time"], avg_bottom)
    pt_peak = Point(peak["time"], neckline)
    pt_p2 = Point(p2["time"], avg_bottom)
    
    height = neckline - avg_bottom
    target_up = neckline + height
    target_down = avg_bottom - height * 0.5
    
    # Stage
    if neckline_broken:
        stage = PatternStage.CONFIRMED.value
    elif current_price and current_price > neckline * 0.99:
        stage = PatternStage.MATURING.value
    else:
        stage = PatternStage.FORMING.value
    
    primary = ProjectionTarget(
        direction="up",
        target=target_up,
        path=[
            Point(p2["time"], neckline),
            Point(p2["time"] + 10, target_up)
        ],
        confidence=0.68 if neckline_broken else 0.55
    )
    
    secondary = ProjectionTarget(
        direction="down",
        target=target_down,
        path=[pt_p2, Point(p2["time"] + 6, target_down)],
        confidence=0.32
    )
    
    return PatternProjectionContract(
        pattern_type="double_bottom",
        stage=stage,
        structure_points=[pt_p1, pt_peak, pt_p2],
        structure_lines=[Line(pt_p1, pt_peak), Line(pt_peak, pt_p2)],
        structure_fill=True,
        resistance=neckline,
        support=avg_bottom,
        neckline=neckline,
        end_time=p2["time"] + 5,
        confirm_level=neckline,
        invalidation_level=avg_bottom * 0.99,
        primary_projection=primary,
        secondary_projection=secondary
    )


# ═══════════════════════════════════════════════════════════════
# TRIANGLE PROJECTOR
# ═══════════════════════════════════════════════════════════════

def build_triangle_projection(
    upper_points: List[Dict],
    lower_points: List[Dict],
    triangle_type: str = "symmetrical",  # symmetrical, ascending, descending
    current_price: float = None
) -> PatternProjectionContract:
    """
    Строит полную проекцию для Triangle.
    
    Визуал:
    \        /
     \      /
      \    /
       \  /
        \/
         apex
        ↑ target
        ↓ target
    """
    if len(upper_points) < 2 or len(lower_points) < 2:
        return None
    
    # Upper/Lower lines
    up1 = Point(upper_points[0]["time"], upper_points[0]["price"])
    up2 = Point(upper_points[-1]["time"], upper_points[-1]["price"])
    lo1 = Point(lower_points[0]["time"], lower_points[0]["price"])
    lo2 = Point(lower_points[-1]["time"], lower_points[-1]["price"])
    
    upper_line = Line(up1, up2)
    lower_line = Line(lo1, lo2)
    
    # Calculate apex (intersection point)
    slope_upper = (up2.price - up1.price) / max(up2.time - up1.time, 1)
    slope_lower = (lo2.price - lo1.price) / max(lo2.time - lo1.time, 1)
    
    if abs(slope_upper - slope_lower) > 0.0001:
        apex_time = int((lo1.price - up1.price + slope_upper * up1.time - slope_lower * lo1.time) / (slope_upper - slope_lower))
        apex_price = up1.price + slope_upper * (apex_time - up1.time)
        apex = Point(apex_time, apex_price)
    else:
        apex_time = up2.time + 20
        apex = Point(apex_time, (up2.price + lo2.price) / 2)
    
    # Height at base
    base_height = abs(up1.price - lo1.price)
    
    # Targets
    breakout_price = (up2.price + lo2.price) / 2
    target_up = breakout_price + base_height
    target_down = breakout_price - base_height
    
    # Direction bias
    if triangle_type == "ascending":
        primary_dir = "up"
        primary_target = target_up
        secondary_target = target_down
    elif triangle_type == "descending":
        primary_dir = "down"
        primary_target = target_down
        secondary_target = target_up
    else:
        primary_dir = "up"  # Neutral bias
        primary_target = target_up
        secondary_target = target_down
    
    # Stage
    if current_price:
        if current_price > up2.price or current_price < lo2.price:
            stage = PatternStage.CONFIRMED.value
        elif abs(current_price - breakout_price) < base_height * 0.1:
            stage = PatternStage.MATURING.value
        else:
            stage = PatternStage.FORMING.value
    else:
        stage = PatternStage.FORMING.value
    
    primary = ProjectionTarget(
        direction=primary_dir,
        target=primary_target,
        path=[
            Point(apex.time, breakout_price),
            Point(apex.time + 10, primary_target)
        ],
        confidence=0.60
    )
    
    secondary = ProjectionTarget(
        direction="down" if primary_dir == "up" else "up",
        target=secondary_target,
        path=[
            Point(apex.time, breakout_price),
            Point(apex.time + 10, secondary_target)
        ],
        confidence=0.40
    )
    
    # Structure points (для fill)
    structure_points = [up1, up2, lo2, lo1]
    
    return PatternProjectionContract(
        pattern_type=f"triangle_{triangle_type}",
        stage=stage,
        structure_points=structure_points,
        structure_lines=[upper_line, lower_line],
        structure_fill=True,
        resistance=max(up1.price, up2.price),
        support=min(lo1.price, lo2.price),
        upper_line=upper_line,
        lower_line=lower_line,
        end_time=apex.time,
        apex=apex,
        confirm_level=up2.price if primary_dir == "up" else lo2.price,
        invalidation_level=lo2.price if primary_dir == "up" else up2.price,
        primary_projection=primary,
        secondary_projection=secondary
    )


# ═══════════════════════════════════════════════════════════════
# WEDGE PROJECTOR
# ═══════════════════════════════════════════════════════════════

def build_wedge_projection(
    upper_points: List[Dict],
    lower_points: List[Dict],
    wedge_type: str = "falling",  # falling or rising
    current_price: float = None
) -> PatternProjectionContract:
    """
    Строит полную проекцию для Wedge.
    
    FALLING WEDGE: primary → UP (bullish)
    RISING WEDGE: primary → DOWN (bearish)
    """
    if len(upper_points) < 2 or len(lower_points) < 2:
        return None
    
    up1 = Point(upper_points[0]["time"], upper_points[0]["price"])
    up2 = Point(upper_points[-1]["time"], upper_points[-1]["price"])
    lo1 = Point(lower_points[0]["time"], lower_points[0]["price"])
    lo2 = Point(lower_points[-1]["time"], lower_points[-1]["price"])
    
    upper_line = Line(up1, up2)
    lower_line = Line(lo1, lo2)
    
    # Apex
    slope_upper = (up2.price - up1.price) / max(up2.time - up1.time, 1)
    slope_lower = (lo2.price - lo1.price) / max(lo2.time - lo1.time, 1)
    
    if abs(slope_upper - slope_lower) > 0.0001:
        apex_time = int((lo1.price - up1.price + slope_upper * up1.time - slope_lower * lo1.time) / (slope_upper - slope_lower))
        apex_price = up1.price + slope_upper * (apex_time - up1.time)
        apex = Point(apex_time, apex_price)
    else:
        apex = Point(up2.time + 20, (up2.price + lo2.price) / 2)
    
    base_height = abs(up1.price - lo1.price)
    breakout_price = (up2.price + lo2.price) / 2
    
    # Direction based on wedge type
    if wedge_type == "falling":
        # Falling wedge = bullish
        primary_dir = "up"
        primary_target = breakout_price + base_height
        secondary_target = breakout_price - base_height * 0.5
    else:
        # Rising wedge = bearish
        primary_dir = "down"
        primary_target = breakout_price - base_height
        secondary_target = breakout_price + base_height * 0.5
    
    stage = PatternStage.FORMING.value
    if current_price:
        if wedge_type == "falling" and current_price > up2.price:
            stage = PatternStage.CONFIRMED.value
        elif wedge_type == "rising" and current_price < lo2.price:
            stage = PatternStage.CONFIRMED.value
    
    primary = ProjectionTarget(
        direction=primary_dir,
        target=primary_target,
        path=[
            Point(up2.time, breakout_price),
            Point(up2.time + 10, primary_target)
        ],
        confidence=0.65
    )
    
    secondary = ProjectionTarget(
        direction="down" if primary_dir == "up" else "up",
        target=secondary_target,
        path=[
            Point(up2.time, breakout_price),
            Point(up2.time + 10, secondary_target)
        ],
        confidence=0.35
    )
    
    return PatternProjectionContract(
        pattern_type=f"wedge_{wedge_type}",
        stage=stage,
        structure_points=[up1, up2, lo2, lo1],
        structure_lines=[upper_line, lower_line],
        structure_fill=True,
        resistance=max(up1.price, up2.price),
        support=min(lo1.price, lo2.price),
        upper_line=upper_line,
        lower_line=lower_line,
        end_time=apex.time,
        apex=apex,
        confirm_level=up2.price if wedge_type == "falling" else lo2.price,
        invalidation_level=lo2.price if wedge_type == "falling" else up2.price,
        primary_projection=primary,
        secondary_projection=secondary
    )


# ═══════════════════════════════════════════════════════════════
# RANGE PROJECTOR
# ═══════════════════════════════════════════════════════════════

def build_range_projection(
    resistance: float,
    support: float,
    start_time: int,
    end_time: int,
    touches: int = 2,
    current_price: float = None
) -> PatternProjectionContract:
    """
    Строит полную проекцию для Range.
    
    Визуал:
    ---------
    |       |
    |       |
    ---------
       ↑   ↓
    """
    range_height = resistance - support
    
    # Targets
    target_up = resistance + range_height
    target_down = support - range_height
    
    # Stage
    stage = PatternStage.FORMING.value
    if current_price:
        if current_price > resistance:
            stage = PatternStage.CONFIRMED.value
        elif current_price < support:
            stage = PatternStage.CONFIRMED.value
    
    # Confidence based on touches
    confidence = min(0.75, 0.4 + touches * 0.05)
    
    # Structure points (4 corners of box)
    pt_tl = Point(start_time, resistance)
    pt_tr = Point(end_time, resistance)
    pt_br = Point(end_time, support)
    pt_bl = Point(start_time, support)
    
    upper_line = Line(pt_tl, pt_tr)
    lower_line = Line(pt_bl, pt_br)
    
    primary = ProjectionTarget(
        direction="up",  # Default bias
        target=target_up,
        path=[
            Point(end_time, resistance),
            Point(end_time + 8, target_up)
        ],
        confidence=confidence
    )
    
    secondary = ProjectionTarget(
        direction="down",
        target=target_down,
        path=[
            Point(end_time, support),
            Point(end_time + 8, target_down)
        ],
        confidence=1 - confidence
    )
    
    return PatternProjectionContract(
        pattern_type="range",
        stage=stage,
        structure_points=[pt_tl, pt_tr, pt_br, pt_bl],
        structure_lines=[upper_line, lower_line],
        structure_fill=True,
        resistance=resistance,
        support=support,
        upper_line=upper_line,
        lower_line=lower_line,
        end_time=end_time,
        confirm_level=resistance,
        invalidation_level=support,
        primary_projection=primary,
        secondary_projection=secondary
    )


# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def build_pattern_projection(
    pattern: Dict,
    current_price: float = None
) -> Optional[PatternProjectionContract]:
    """
    Главная функция для построения проекции паттерна.
    
    Args:
        pattern: Распознанный паттерн от детектора
        current_price: Текущая цена (для определения stage)
    
    Returns:
        PatternProjectionContract или None
    """
    pattern_type = pattern.get("type", "").lower()
    anchors = pattern.get("anchors", {})
    
    try:
        # DOUBLE TOP
        if pattern_type == "double_top":
            p1 = anchors.get("p1") or (pattern.get("anchors", [{}])[0] if isinstance(pattern.get("anchors"), list) else None)
            p2 = anchors.get("p2") or (pattern.get("anchors", [{}])[-1] if isinstance(pattern.get("anchors"), list) else None)
            valley = anchors.get("valley") or pattern.get("meta", {}).get("valley")
            
            if not all([p1, p2, valley]):
                return None
            
            return build_double_top_projection(p1, valley, p2, current_price)
        
        # DOUBLE BOTTOM
        if pattern_type == "double_bottom":
            p1 = anchors.get("p1")
            p2 = anchors.get("p2")
            peak = anchors.get("peak") or pattern.get("meta", {}).get("peak")
            
            if not all([p1, p2, peak]):
                return None
            
            return build_double_bottom_projection(p1, peak, p2, current_price)
        
        # TRIANGLE
        if "triangle" in pattern_type:
            boundaries = pattern.get("meta", {}).get("boundaries", {})
            upper = boundaries.get("upper", {})
            lower = boundaries.get("lower", {})
            
            upper_points = [
                {"time": upper.get("x1", 0), "price": upper.get("y1", 0)},
                {"time": upper.get("x2", 0), "price": upper.get("y2", 0)}
            ]
            lower_points = [
                {"time": lower.get("x1", 0), "price": lower.get("y1", 0)},
                {"time": lower.get("x2", 0), "price": lower.get("y2", 0)}
            ]
            
            tri_type = "symmetrical"
            if "ascending" in pattern_type:
                tri_type = "ascending"
            elif "descending" in pattern_type:
                tri_type = "descending"
            
            return build_triangle_projection(upper_points, lower_points, tri_type, current_price)
        
        # WEDGE
        if "wedge" in pattern_type:
            boundaries = pattern.get("meta", {}).get("boundaries", {})
            upper = boundaries.get("upper", {})
            lower = boundaries.get("lower", {})
            
            upper_points = [
                {"time": upper.get("x1", 0), "price": upper.get("y1", 0)},
                {"time": upper.get("x2", 0), "price": upper.get("y2", 0)}
            ]
            lower_points = [
                {"time": lower.get("x1", 0), "price": lower.get("y1", 0)},
                {"time": lower.get("x2", 0), "price": lower.get("y2", 0)}
            ]
            
            wedge_type = "falling" if "falling" in pattern_type else "rising"
            
            return build_wedge_projection(upper_points, lower_points, wedge_type, current_price)
        
        # RANGE
        if "range" in pattern_type:
            bounds = pattern.get("bounds", {})
            meta = pattern.get("meta", {})
            boundaries = meta.get("boundaries", {})
            
            resistance = bounds.get("top") or meta.get("resistance")
            support = bounds.get("bottom") or meta.get("support")
            
            start_time = boundaries.get("upper", {}).get("x1", 0) or meta.get("start_time", 0)
            end_time = boundaries.get("upper", {}).get("x2", 0) or meta.get("end_time", 0)
            touches = pattern.get("touches", 2)
            
            if resistance and support:
                return build_range_projection(resistance, support, start_time, end_time, touches, current_price)
        
        return None
        
    except Exception as e:
        print(f"[PatternProjection] Error building projection: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# SINGLETON GETTER
# ═══════════════════════════════════════════════════════════════

class PatternProjectionEngine:
    """
    Engine для построения проекций паттернов.
    """
    
    def build(self, pattern: Dict, current_price: float = None) -> Optional[Dict]:
        """Построить проекцию и вернуть как dict."""
        contract = build_pattern_projection(pattern, current_price)
        if contract:
            return contract.to_dict()
        return None
    
    def build_batch(self, patterns: List[Dict], current_price: float = None) -> List[Dict]:
        """Построить проекции для списка паттернов."""
        results = []
        for p in patterns:
            result = self.build(p, current_price)
            if result:
                results.append(result)
        return results


_engine_instance = None

def get_pattern_projection_engine() -> PatternProjectionEngine:
    """Получить singleton экземпляр engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = PatternProjectionEngine()
    return _engine_instance
