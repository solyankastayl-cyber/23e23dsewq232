"""
Pattern Family Matrix — All Patterns by Family
===============================================

INSTEAD OF 100 separate pattern files, we have 6 families.
Each family uses the SAME primitives from:
- SwingEngine
- GeometryEngine

FAMILIES:
1. HORIZONTAL    → double/triple top/bottom, range, rectangle
2. CONVERGING    → triangles, wedges  
3. PARALLEL      → channels, flags
4. SWING_COMPOSITE → H&S, cup, complex patterns
5. REGIME        → squeeze, compression, volatility states
6. STRUCTURE     → HH/HL/LH/LL, BOS/CHOCH (foundation, not pattern)

Each pattern has:
- family: which family it belongs to
- core_rule: geometric primitive it uses
- bias: bullish/bearish/neutral
- min_swings: minimum required swings
- key_levels: what to render
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class PatternFamily(Enum):
    HORIZONTAL = "horizontal"
    CONVERGING = "converging"
    PARALLEL = "parallel"
    SWING_COMPOSITE = "swing_composite"
    REGIME = "regime"
    STRUCTURE = "structure"  # Not a pattern, but foundation


class PatternBias(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"  # Breakout either way


@dataclass
class PatternDefinition:
    """Definition of a pattern type."""
    name: str
    family: PatternFamily
    bias: PatternBias
    core_rule: str          # Geometric rule name
    min_swings: int         # Minimum swing points needed
    key_levels: List[str]   # What to extract for rendering
    description: str
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "family": self.family.value,
            "bias": self.bias.value,
            "core_rule": self.core_rule,
            "min_swings": self.min_swings,
            "key_levels": self.key_levels,
            "description": self.description,
        }


# =============================================================================
# PATTERN FAMILY MATRIX
# =============================================================================

PATTERN_FAMILY_MATRIX: Dict[str, PatternDefinition] = {
    
    # =========================================================================
    # HORIZONTAL FAMILY — Equal highs/lows
    # =========================================================================
    
    "double_top": PatternDefinition(
        name="Double Top",
        family=PatternFamily.HORIZONTAL,
        bias=PatternBias.BEARISH,
        core_rule="equal_highs_with_valley",
        min_swings=3,  # H-L-H
        key_levels=["p1", "p2", "neckline", "target"],
        description="Two peaks at similar level, bearish reversal"
    ),
    
    "double_bottom": PatternDefinition(
        name="Double Bottom",
        family=PatternFamily.HORIZONTAL,
        bias=PatternBias.BULLISH,
        core_rule="equal_lows_with_peak",
        min_swings=3,  # L-H-L
        key_levels=["p1", "p2", "neckline", "target"],
        description="Two troughs at similar level, bullish reversal"
    ),
    
    "triple_top": PatternDefinition(
        name="Triple Top",
        family=PatternFamily.HORIZONTAL,
        bias=PatternBias.BEARISH,
        core_rule="equal_highs_triple",
        min_swings=5,  # H-L-H-L-H
        key_levels=["p1", "p2", "p3", "neckline", "target"],
        description="Three peaks at similar level, strong bearish reversal"
    ),
    
    "triple_bottom": PatternDefinition(
        name="Triple Bottom",
        family=PatternFamily.HORIZONTAL,
        bias=PatternBias.BULLISH,
        core_rule="equal_lows_triple",
        min_swings=5,  # L-H-L-H-L
        key_levels=["p1", "p2", "p3", "neckline", "target"],
        description="Three troughs at similar level, strong bullish reversal"
    ),
    
    "range": PatternDefinition(
        name="Range",
        family=PatternFamily.HORIZONTAL,
        bias=PatternBias.NEUTRAL,
        core_rule="horizontal_bounds",
        min_swings=4,  # 2H + 2L minimum
        key_levels=["resistance", "support", "midpoint"],
        description="Horizontal consolidation between support/resistance"
    ),
    
    "rectangle": PatternDefinition(
        name="Rectangle",
        family=PatternFamily.HORIZONTAL,
        bias=PatternBias.NEUTRAL,
        core_rule="horizontal_bounds_strict",
        min_swings=6,  # 3H + 3L for clear rectangle
        key_levels=["resistance", "support", "breakout_up", "breakout_down"],
        description="Well-defined horizontal consolidation"
    ),
    
    # =========================================================================
    # CONVERGING FAMILY — Lines narrow
    # =========================================================================
    
    "symmetrical_triangle": PatternDefinition(
        name="Symmetrical Triangle",
        family=PatternFamily.CONVERGING,
        bias=PatternBias.NEUTRAL,
        core_rule="converging_both_slopes",
        min_swings=4,
        key_levels=["upper_line", "lower_line", "apex", "breakout_zone"],
        description="Lower highs + higher lows, breakout either direction"
    ),
    
    "ascending_triangle": PatternDefinition(
        name="Ascending Triangle",
        family=PatternFamily.CONVERGING,
        bias=PatternBias.BULLISH,
        core_rule="horizontal_top_rising_bottom",
        min_swings=4,
        key_levels=["resistance", "rising_support", "apex", "breakout"],
        description="Flat top + higher lows, bullish breakout expected"
    ),
    
    "descending_triangle": PatternDefinition(
        name="Descending Triangle",
        family=PatternFamily.CONVERGING,
        bias=PatternBias.BEARISH,
        core_rule="horizontal_bottom_falling_top",
        min_swings=4,
        key_levels=["support", "falling_resistance", "apex", "breakdown"],
        description="Flat bottom + lower highs, bearish breakdown expected"
    ),
    
    "rising_wedge": PatternDefinition(
        name="Rising Wedge",
        family=PatternFamily.CONVERGING,
        bias=PatternBias.BEARISH,
        core_rule="converging_both_rising",
        min_swings=4,
        key_levels=["upper_line", "lower_line", "apex", "breakdown"],
        description="Both lines rising but converging, bearish reversal"
    ),
    
    "falling_wedge": PatternDefinition(
        name="Falling Wedge",
        family=PatternFamily.CONVERGING,
        bias=PatternBias.BULLISH,
        core_rule="converging_both_falling",
        min_swings=4,
        key_levels=["upper_line", "lower_line", "apex", "breakout"],
        description="Both lines falling but converging, bullish reversal"
    ),
    
    # =========================================================================
    # PARALLEL FAMILY — Lines parallel
    # =========================================================================
    
    "ascending_channel": PatternDefinition(
        name="Ascending Channel",
        family=PatternFamily.PARALLEL,
        bias=PatternBias.BULLISH,
        core_rule="parallel_rising",
        min_swings=4,
        key_levels=["upper_line", "lower_line", "midline"],
        description="Parallel lines sloping upward, bullish trend"
    ),
    
    "descending_channel": PatternDefinition(
        name="Descending Channel",
        family=PatternFamily.PARALLEL,
        bias=PatternBias.BEARISH,
        core_rule="parallel_falling",
        min_swings=4,
        key_levels=["upper_line", "lower_line", "midline"],
        description="Parallel lines sloping downward, bearish trend"
    ),
    
    "horizontal_channel": PatternDefinition(
        name="Horizontal Channel",
        family=PatternFamily.PARALLEL,
        bias=PatternBias.NEUTRAL,
        core_rule="parallel_horizontal",
        min_swings=4,
        key_levels=["upper_line", "lower_line", "midline"],
        description="Flat parallel lines, consolidation"
    ),
    
    "bull_flag": PatternDefinition(
        name="Bull Flag",
        family=PatternFamily.PARALLEL,
        bias=PatternBias.BULLISH,
        core_rule="parallel_falling_after_impulse_up",
        min_swings=3,
        key_levels=["flagpole", "flag_top", "flag_bottom", "breakout"],
        description="Downward sloping consolidation after strong up move"
    ),
    
    "bear_flag": PatternDefinition(
        name="Bear Flag",
        family=PatternFamily.PARALLEL,
        bias=PatternBias.BEARISH,
        core_rule="parallel_rising_after_impulse_down",
        min_swings=3,
        key_levels=["flagpole", "flag_top", "flag_bottom", "breakdown"],
        description="Upward sloping consolidation after strong down move"
    ),
    
    # =========================================================================
    # SWING COMPOSITE FAMILY — Complex swing sequences
    # =========================================================================
    
    "head_shoulders": PatternDefinition(
        name="Head & Shoulders",
        family=PatternFamily.SWING_COMPOSITE,
        bias=PatternBias.BEARISH,
        core_rule="swing_sequence_HLH_higher_middle",
        min_swings=5,  # LS-Valley-Head-Valley-RS
        key_levels=["left_shoulder", "head", "right_shoulder", "neckline", "target"],
        description="Left shoulder, higher head, right shoulder — bearish reversal"
    ),
    
    "inverse_head_shoulders": PatternDefinition(
        name="Inverse Head & Shoulders",
        family=PatternFamily.SWING_COMPOSITE,
        bias=PatternBias.BULLISH,
        core_rule="swing_sequence_LHL_lower_middle",
        min_swings=5,  # LS-Peak-Head-Peak-RS
        key_levels=["left_shoulder", "head", "right_shoulder", "neckline", "target"],
        description="Inverse of H&S — bullish reversal"
    ),
    
    "cup_handle": PatternDefinition(
        name="Cup & Handle",
        family=PatternFamily.SWING_COMPOSITE,
        bias=PatternBias.BULLISH,
        core_rule="rounded_bottom_with_pullback",
        min_swings=5,
        key_levels=["cup_left", "cup_bottom", "cup_right", "handle", "breakout"],
        description="U-shaped bottom with small pullback, bullish continuation"
    ),
    
    # =========================================================================
    # REGIME FAMILY — Market states, not shapes
    # =========================================================================
    
    "squeeze": PatternDefinition(
        name="Squeeze",
        family=PatternFamily.REGIME,
        bias=PatternBias.NEUTRAL,
        core_rule="volatility_contraction",
        min_swings=2,
        key_levels=["squeeze_start", "expected_expansion"],
        description="Volatility contracting, big move expected"
    ),
    
    "compression": PatternDefinition(
        name="Compression",
        family=PatternFamily.REGIME,
        bias=PatternBias.NEUTRAL,
        core_rule="range_narrowing",
        min_swings=3,
        key_levels=["compression_zone"],
        description="Price range narrowing significantly"
    ),
    
    "expansion": PatternDefinition(
        name="Expansion",
        family=PatternFamily.REGIME,
        bias=PatternBias.NEUTRAL,
        core_rule="volatility_expansion",
        min_swings=2,
        key_levels=["expansion_start", "direction"],
        description="Volatility expanding after squeeze"
    ),
}


# =============================================================================
# FAMILY GROUPINGS (for quick lookup)
# =============================================================================

PATTERNS_BY_FAMILY: Dict[PatternFamily, List[str]] = {
    PatternFamily.HORIZONTAL: [
        "double_top", "double_bottom", 
        "triple_top", "triple_bottom",
        "range", "rectangle"
    ],
    PatternFamily.CONVERGING: [
        "symmetrical_triangle", "ascending_triangle", "descending_triangle",
        "rising_wedge", "falling_wedge"
    ],
    PatternFamily.PARALLEL: [
        "ascending_channel", "descending_channel", "horizontal_channel",
        "bull_flag", "bear_flag"
    ],
    PatternFamily.SWING_COMPOSITE: [
        "head_shoulders", "inverse_head_shoulders", "cup_handle"
    ],
    PatternFamily.REGIME: [
        "squeeze", "compression", "expansion"
    ],
}


def get_pattern_definition(pattern_type: str) -> Optional[PatternDefinition]:
    """Get pattern definition by type name."""
    return PATTERN_FAMILY_MATRIX.get(pattern_type.lower().replace(" ", "_"))


def get_patterns_in_family(family: PatternFamily) -> List[PatternDefinition]:
    """Get all patterns in a family."""
    pattern_names = PATTERNS_BY_FAMILY.get(family, [])
    return [PATTERN_FAMILY_MATRIX[name] for name in pattern_names if name in PATTERN_FAMILY_MATRIX]


def get_bullish_patterns() -> List[str]:
    """Get all bullish pattern names."""
    return [name for name, defn in PATTERN_FAMILY_MATRIX.items() 
            if defn.bias == PatternBias.BULLISH]


def get_bearish_patterns() -> List[str]:
    """Get all bearish pattern names."""
    return [name for name, defn in PATTERN_FAMILY_MATRIX.items() 
            if defn.bias == PatternBias.BEARISH]
