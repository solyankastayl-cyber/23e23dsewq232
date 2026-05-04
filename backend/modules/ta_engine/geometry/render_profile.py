"""
Pattern Render Profile System
=============================

Контролирует что рисовать для каждого типа паттерна в зависимости от:
- mode: strict / loose
- stage: forming / maturing / confirmed / invalidated

ГЛАВНОЕ ПРАВИЛО:
- loose patterns → minimal render (только body, без projection)
- strict forming → compact render (body + bounds)
- strict confirmed → full render (body + bounds + projection)

Render Profiles:
- compact: только базовая фигура (M-shape, box, lines)
- box: только прямоугольник (для range)
- clean: границы без заливки (для triangle/wedge)
- full: всё включено (только для strict + confirmed)
"""

from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum


class RenderMode(Enum):
    """Режим рендеринга."""
    COMPACT = "compact"      # Только базовая фигура
    BOX = "box"              # Только прямоугольник
    CLEAN = "clean"          # Линии без заливки
    FULL = "full"            # Всё включено
    MINIMAL = "minimal"      # Минимум (для loose)
    NONE = "none"            # Не рисовать


@dataclass
class RenderProfile:
    """Профиль рендеринга паттерна."""
    
    # Что рисовать
    draw_structure: bool = True      # Базовая фигура (M, box, lines)
    draw_fill: bool = False          # Заливка
    draw_bounds: bool = True         # Границы (neckline, R/S)
    draw_completion: bool = False    # Линия завершения
    draw_projection: bool = False    # Стрелки target/invalidation
    draw_labels: bool = False        # Метки P1/P2/V
    draw_stage: bool = False         # Индикатор stage
    
    # Стиль
    stroke_width: float = 2.0
    fill_opacity: float = 0.1
    use_dashed: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "draw_structure": self.draw_structure,
            "draw_fill": self.draw_fill,
            "draw_bounds": self.draw_bounds,
            "draw_completion": self.draw_completion,
            "draw_projection": self.draw_projection,
            "draw_labels": self.draw_labels,
            "draw_stage": self.draw_stage,
            "stroke_width": self.stroke_width,
            "fill_opacity": self.fill_opacity,
            "use_dashed": self.use_dashed,
        }


# ═══════════════════════════════════════════════════════════════
# RENDER PROFILE MATRIX
# ═══════════════════════════════════════════════════════════════

# Profiles by mode/stage
PROFILES = {
    # STRICT + CONFIRMED → Full render
    "strict_confirmed": RenderProfile(
        draw_structure=True,
        draw_fill=True,
        draw_bounds=True,
        draw_completion=True,
        draw_projection=True,
        draw_labels=True,
        draw_stage=True,
        stroke_width=2.5,
        fill_opacity=0.15,
    ),
    
    # STRICT + FORMING/MATURING → Compact (no projection)
    "strict_forming": RenderProfile(
        draw_structure=True,
        draw_fill=True,
        draw_bounds=True,
        draw_completion=False,
        draw_projection=False,  # KEY: no projection
        draw_labels=False,
        draw_stage=False,
        stroke_width=2.0,
        fill_opacity=0.1,
    ),
    
    # LOOSE → Minimal (body only)
    "loose": RenderProfile(
        draw_structure=True,
        draw_fill=False,
        draw_bounds=True,
        draw_completion=False,
        draw_projection=False,  # KEY: no projection
        draw_labels=False,
        draw_stage=False,
        stroke_width=1.5,
        fill_opacity=0.05,
        use_dashed=True,
    ),
    
    # RANGE specific → Box only
    "range_box": RenderProfile(
        draw_structure=True,
        draw_fill=True,
        draw_bounds=True,
        draw_completion=False,
        draw_projection=False,
        draw_labels=False,
        draw_stage=False,
        stroke_width=1.5,
        fill_opacity=0.08,
    ),
    
    # INVALIDATED → Faded
    "invalidated": RenderProfile(
        draw_structure=True,
        draw_fill=False,
        draw_bounds=True,
        draw_completion=False,
        draw_projection=False,
        draw_labels=False,
        draw_stage=True,
        stroke_width=1.0,
        fill_opacity=0.03,
        use_dashed=True,
    ),
}


# ═══════════════════════════════════════════════════════════════
# PATTERN-SPECIFIC RENDER MODES
# ═══════════════════════════════════════════════════════════════

PATTERN_RENDER_MODES = {
    # Double patterns → compact by default
    "double_top": "compact",
    "double_bottom": "compact",
    
    # Range patterns → box mode
    "range": "box",
    "loose_range": "box",
    "accumulation_range": "box",
    "distribution_range": "box",
    
    # Triangle/Wedge → clean mode
    "triangle": "clean",
    "triangle_symmetrical": "clean",
    "triangle_ascending": "clean",
    "triangle_descending": "clean",
    "wedge": "clean",
    "wedge_falling": "clean",
    "wedge_rising": "clean",
    "loose_triangle": "clean",
    "loose_wedge": "clean",
    
    # Channel → only if valid geometry
    "channel": "clean",
}


def get_render_profile(
    pattern_type: str,
    mode: str = "strict",
    stage: str = "forming"
) -> RenderProfile:
    """
    Получить профиль рендеринга для паттерна.
    
    Args:
        pattern_type: Тип паттерна (double_top, range, etc.)
        mode: strict / loose
        stage: forming / maturing / confirmed / invalidated
    
    Returns:
        RenderProfile с настройками что рисовать
    """
    # Normalize inputs
    pattern_type = pattern_type.lower() if pattern_type else ""
    mode = mode.lower() if mode else "strict"
    stage = stage.lower() if stage else "forming"
    
    # RULE 1: Loose patterns → minimal render
    if mode == "loose" or "loose" in pattern_type:
        return PROFILES["loose"]
    
    # RULE 2: Invalidated → faded render
    if stage == "invalidated":
        return PROFILES["invalidated"]
    
    # RULE 3: Range patterns → box mode (even if strict)
    if "range" in pattern_type:
        profile = PROFILES["range_box"].to_dict()
        # Add projection only if confirmed
        if stage == "confirmed":
            profile["draw_projection"] = True
        return RenderProfile(**profile)
    
    # RULE 4: Strict + Confirmed → full render
    if mode == "strict" and stage == "confirmed":
        return PROFILES["strict_confirmed"]
    
    # RULE 5: Default → compact (no projection)
    return PROFILES["strict_forming"]


def apply_render_profile(pattern: Dict, profile: RenderProfile) -> Dict:
    """
    Применить профиль рендеринга к паттерну.
    
    Удаляет лишние данные согласно профилю.
    """
    result = dict(pattern)
    
    # Add profile to contract
    result["render_profile"] = profile.to_dict()
    
    # Remove projection if not allowed
    if not profile.draw_projection:
        result["projection_contract"] = None
        if "projection" in result:
            result["projection"] = None
    
    # Simplify projection contract if present
    if result.get("projection_contract") and not profile.draw_projection:
        pc = result["projection_contract"]
        if isinstance(pc, dict):
            pc["projection"] = {"primary": None, "secondary": None}
    
    return result


# ═══════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════

def configure_pattern_render(pattern: Dict) -> Dict:
    """
    Главная функция — конфигурирует рендер паттерна.
    
    Args:
        pattern: Паттерн с type, mode, stage
    
    Returns:
        Паттерн с render_profile и очищенными данными
    """
    pattern_type = pattern.get("type", "")
    mode = pattern.get("mode", "strict")
    stage = pattern.get("stage", "forming")
    
    # Get from projection_contract if available
    if pattern.get("projection_contract"):
        pc = pattern["projection_contract"]
        if isinstance(pc, dict):
            stage = pc.get("stage", stage)
    
    # Get profile
    profile = get_render_profile(pattern_type, mode, stage)
    
    # Apply profile
    result = apply_render_profile(pattern, profile)
    
    # Log
    print(f"[RenderProfile] {pattern_type}: mode={mode}, stage={stage}, "
          f"projection={profile.draw_projection}, fill={profile.draw_fill}")
    
    return result
