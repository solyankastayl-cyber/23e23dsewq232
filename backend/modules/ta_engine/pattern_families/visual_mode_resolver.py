"""
Visual Mode Resolver — RENDER ISOLATION DISCIPLINE
===================================================

PROBLEM:
Frontend draws everything at once:
- range box
- HH/HL/LL markers  
- trigger labels
- pattern polyline
- auxiliary levels

RESULT: Visual chaos. User sees "салат" instead of one clear idea.

SOLUTION:
This resolver determines ONE visual mode based on dominant pattern.
Frontend OBEYS this mode and draws ONLY what's allowed.

MODES:
1. range_only         → box + R/S + triggers (NO swings, NO polyline)
2. horizontal_pattern → polyline + neckline + labels (NO range, NO swings)
3. compression_pattern → upper/lower lines + apex (NO range, NO swings)
4. swing_pattern      → H&S polyline + shoulders (NO range)
5. structure_only     → HH/HL/LL + BOS/CHOCH (NO patterns, NO range)
6. none               → nothing (chart only)
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum


class VisualMode(Enum):
    """What the frontend is ALLOWED to render."""
    RANGE_ONLY = "range_only"
    HORIZONTAL_PATTERN = "horizontal_pattern"
    COMPRESSION_PATTERN = "compression_pattern"
    SWING_PATTERN = "swing_pattern"
    STRUCTURE_ONLY = "structure_only"
    NONE = "none"


@dataclass
class VisualModeConfig:
    """Configuration for what to render in each mode."""
    mode: VisualMode
    
    # What to SHOW
    show_box: bool = False           # Range/rectangle box
    show_polyline: bool = False      # Pattern polyline
    show_trendlines: bool = False    # Triangle/wedge/channel lines
    show_structure: bool = False     # HH/HL/LH/LL markers
    show_levels: bool = False        # R/S horizontal levels
    show_triggers: bool = False      # Breakout/breakdown labels
    show_neckline: bool = False      # Pattern neckline
    show_target: bool = False        # Target level
    
    # Specific elements
    max_levels: int = 2              # Max horizontal levels to show
    max_triggers: int = 2            # Max trigger labels
    max_markers: int = 5             # Max structure markers
    
    def to_dict(self) -> Dict:
        return {
            "mode": self.mode.value,
            "show_box": self.show_box,
            "show_polyline": self.show_polyline,
            "show_trendlines": self.show_trendlines,
            "show_structure": self.show_structure,
            "show_levels": self.show_levels,
            "show_triggers": self.show_triggers,
            "show_neckline": self.show_neckline,
            "show_target": self.show_target,
            "max_levels": self.max_levels,
            "max_triggers": self.max_triggers,
            "max_markers": self.max_markers,
        }


# ═══════════════════════════════════════════════════════════════
# PREDEFINED MODE CONFIGS
# ═══════════════════════════════════════════════════════════════

MODE_CONFIGS = {
    VisualMode.RANGE_ONLY: VisualModeConfig(
        mode=VisualMode.RANGE_ONLY,
        show_box=True,
        show_levels=True,
        show_triggers=True,
        max_levels=2,      # Just R and S
        max_triggers=2,    # breakout + breakdown
        # NO polyline, NO structure, NO trendlines
    ),
    
    VisualMode.HORIZONTAL_PATTERN: VisualModeConfig(
        mode=VisualMode.HORIZONTAL_PATTERN,
        show_polyline=True,
        show_neckline=True,
        show_levels=True,
        show_target=True,
        show_triggers=True,
        max_levels=2,      # neckline + resistance
        max_triggers=2,
        # NO box, NO structure, NO trendlines
    ),
    
    VisualMode.COMPRESSION_PATTERN: VisualModeConfig(
        mode=VisualMode.COMPRESSION_PATTERN,
        show_trendlines=True,
        show_triggers=True,
        max_triggers=2,    # breakout up/down
        # NO box, NO structure, NO polyline
    ),
    
    VisualMode.SWING_PATTERN: VisualModeConfig(
        mode=VisualMode.SWING_PATTERN,
        show_polyline=True,
        show_neckline=True,
        show_levels=True,
        show_target=True,
        show_triggers=True,
        max_levels=3,      # neckline + shoulders
        max_triggers=2,
        # NO box, NO extra structure
    ),
    
    VisualMode.STRUCTURE_ONLY: VisualModeConfig(
        mode=VisualMode.STRUCTURE_ONLY,
        show_structure=True,
        show_levels=True,
        max_markers=6,     # Recent swings only
        max_levels=2,      # Key support/resistance
        # NO patterns, NO box, NO polyline
    ),
    
    VisualMode.NONE: VisualModeConfig(
        mode=VisualMode.NONE,
        # Nothing rendered - clean chart
    ),
}


# ═══════════════════════════════════════════════════════════════
# PATTERN TYPE → VISUAL MODE MAPPING
# ═══════════════════════════════════════════════════════════════

PATTERN_TO_MODE = {
    # Range patterns → RANGE_ONLY
    "range": VisualMode.RANGE_ONLY,
    "rectangle": VisualMode.RANGE_ONLY,
    "active_range": VisualMode.RANGE_ONLY,
    "loose_range": VisualMode.RANGE_ONLY,
    "trading_range": VisualMode.RANGE_ONLY,
    
    # Horizontal patterns → HORIZONTAL_PATTERN
    "double_top": VisualMode.HORIZONTAL_PATTERN,
    "double_bottom": VisualMode.HORIZONTAL_PATTERN,
    "triple_top": VisualMode.HORIZONTAL_PATTERN,
    "triple_bottom": VisualMode.HORIZONTAL_PATTERN,
    
    # Compression patterns → COMPRESSION_PATTERN
    "symmetrical_triangle": VisualMode.COMPRESSION_PATTERN,
    "ascending_triangle": VisualMode.COMPRESSION_PATTERN,
    "descending_triangle": VisualMode.COMPRESSION_PATTERN,
    "rising_wedge": VisualMode.COMPRESSION_PATTERN,
    "falling_wedge": VisualMode.COMPRESSION_PATTERN,
    "ascending_channel": VisualMode.COMPRESSION_PATTERN,
    "descending_channel": VisualMode.COMPRESSION_PATTERN,
    "horizontal_channel": VisualMode.COMPRESSION_PATTERN,
    "bull_flag": VisualMode.COMPRESSION_PATTERN,
    "bear_flag": VisualMode.COMPRESSION_PATTERN,
    
    # Swing patterns → SWING_PATTERN
    "head_shoulders": VisualMode.SWING_PATTERN,
    "head_and_shoulders": VisualMode.SWING_PATTERN,
    "inverse_head_shoulders": VisualMode.SWING_PATTERN,
    "inverse_head_and_shoulders": VisualMode.SWING_PATTERN,
}


# ═══════════════════════════════════════════════════════════════
# RESOLVER CLASS
# ═══════════════════════════════════════════════════════════════

class VisualModeResolver:
    """
    Resolves what visual mode to use based on pattern detection result.
    
    CRITICAL RULE: ONE MODE, ONE VISUAL
    
    Never mix:
    - range box with pattern polyline
    - HH/HL with rectangle bounds
    - multiple pattern types at once
    """
    
    def __init__(self):
        self.pattern_map = PATTERN_TO_MODE
        self.mode_configs = MODE_CONFIGS
    
    def resolve(
        self,
        dominant_type: Optional[str],
        confidence_state: str,
        tradeable: bool = False,
    ) -> VisualModeConfig:
        """
        Determine visual mode from detection result.
        
        Args:
            dominant_type: Type of dominant pattern (or None)
            confidence_state: CLEAR/WEAK/CONFLICTED/COMPRESSION/NONE
            tradeable: Whether setup is tradeable
        
        Returns:
            VisualModeConfig with what to render
        """
        # No pattern → structure only or nothing
        if not dominant_type or confidence_state == "NONE":
            # Show structure for navigation, but minimal
            return self.mode_configs[VisualMode.STRUCTURE_ONLY]
        
        # Lookup pattern type
        pattern_lower = dominant_type.lower()
        
        if pattern_lower in self.pattern_map:
            mode = self.pattern_map[pattern_lower]
            return self.mode_configs[mode]
        
        # Unknown pattern type → structure only
        return self.mode_configs[VisualMode.STRUCTURE_ONLY]
    
    def get_allowed_elements(
        self,
        dominant_type: Optional[str],
        confidence_state: str,
    ) -> Dict:
        """
        Get explicit list of what frontend CAN and CANNOT render.
        
        Returns dict like:
        {
            "allowed": ["box", "levels", "triggers"],
            "forbidden": ["polyline", "structure", "trendlines"]
        }
        """
        config = self.resolve(dominant_type, confidence_state)
        
        allowed = []
        forbidden = []
        
        elements = [
            ("box", config.show_box),
            ("polyline", config.show_polyline),
            ("trendlines", config.show_trendlines),
            ("structure", config.show_structure),
            ("levels", config.show_levels),
            ("triggers", config.show_triggers),
            ("neckline", config.show_neckline),
            ("target", config.show_target),
        ]
        
        for name, show in elements:
            if show:
                allowed.append(name)
            else:
                forbidden.append(name)
        
        return {
            "mode": config.mode.value,
            "allowed": allowed,
            "forbidden": forbidden,
            "limits": {
                "max_levels": config.max_levels,
                "max_triggers": config.max_triggers,
                "max_markers": config.max_markers,
            }
        }
    
    def filter_render_contract(
        self,
        render_contract: Dict,
        dominant_type: Optional[str],
        confidence_state: str,
    ) -> Dict:
        """
        Filter a render contract to ONLY include allowed elements.
        
        This is the KEY function - it strips out everything forbidden.
        """
        if not render_contract:
            return None
        
        config = self.resolve(dominant_type, confidence_state)
        filtered = {
            "visual_mode": config.to_dict(),
        }
        
        # Copy only allowed elements
        if config.show_polyline and "polyline" in render_contract:
            filtered["polyline"] = render_contract["polyline"]
        
        if config.show_box and "box" in render_contract:
            filtered["box"] = render_contract["box"]
        
        if config.show_trendlines:
            if "upper_line" in render_contract:
                filtered["upper_line"] = render_contract["upper_line"]
            if "lower_line" in render_contract:
                filtered["lower_line"] = render_contract["lower_line"]
            if "trendlines" in render_contract:
                filtered["trendlines"] = render_contract["trendlines"]
        
        if config.show_levels and "levels" in render_contract:
            # Limit number of levels
            levels = render_contract["levels"]
            if isinstance(levels, list):
                filtered["levels"] = levels[:config.max_levels]
            else:
                filtered["levels"] = levels
        
        if config.show_neckline and "neckline" in render_contract:
            filtered["neckline"] = render_contract["neckline"]
        
        if config.show_target and "target" in render_contract:
            filtered["target"] = render_contract["target"]
        
        if config.show_triggers and "triggers" in render_contract:
            triggers = render_contract["triggers"]
            if isinstance(triggers, list):
                filtered["triggers"] = triggers[:config.max_triggers]
            else:
                filtered["triggers"] = triggers
        
        if config.show_structure and "structure" in render_contract:
            structure = render_contract["structure"]
            if isinstance(structure, list):
                filtered["structure"] = structure[:config.max_markers]
            else:
                filtered["structure"] = structure
        
        # Always copy metadata
        for key in ["pattern_type", "pattern_family", "render_type", "style"]:
            if key in render_contract:
                filtered[key] = render_contract[key]
        
        return filtered


# ═══════════════════════════════════════════════════════════════
# SINGLETON & HELPERS
# ═══════════════════════════════════════════════════════════════

_resolver = None

def get_visual_mode_resolver() -> VisualModeResolver:
    """Get resolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = VisualModeResolver()
    return _resolver


def resolve_visual_mode(
    dominant_type: Optional[str],
    confidence_state: str,
) -> Dict:
    """
    Convenience function to resolve visual mode.
    
    Returns dict with mode config.
    """
    resolver = get_visual_mode_resolver()
    config = resolver.resolve(dominant_type, confidence_state)
    return config.to_dict()


def filter_render_for_mode(
    render_contract: Dict,
    dominant_type: Optional[str],
    confidence_state: str,
) -> Dict:
    """
    Filter render contract to only allowed elements.
    
    This is what frontend should call to get clean render data.
    """
    resolver = get_visual_mode_resolver()
    return resolver.filter_render_contract(render_contract, dominant_type, confidence_state)
