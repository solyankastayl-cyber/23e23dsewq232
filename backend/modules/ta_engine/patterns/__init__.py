"""
Pattern Engine Package
======================
Production-level pattern detection with lifecycle management.

Supported patterns:
- Triangles (ascending, descending, symmetrical)
- Wedges (rising, falling)
- Channels (ascending, descending, horizontal)
- Double Top / Double Bottom
- Head & Shoulders / Inverse H&S

Usage:
    from modules.ta_engine.patterns import get_pattern_engine
    
    engine = get_pattern_engine()
    result = engine.build(
        candles=candles,
        pivot_highs=pivot_highs,
        pivot_lows=pivot_lows,
        structure_context=structure_context,
        liquidity=liquidity,
        displacement=displacement,
        poi=poi,
        timeframe="1D",
    )
"""

from .pattern_engine import PatternEngine, get_pattern_engine
from .pattern_candidate import PatternCandidate, PatternLine, PatternWindow, PatternScores
from .pattern_registry import PatternRegistry
from .pattern_ranker import PatternRanker
from .pattern_lifecycle import PatternLifecycleManager

__all__ = [
    'PatternEngine',
    'get_pattern_engine',
    'PatternCandidate',
    'PatternLine',
    'PatternWindow',
    'PatternScores',
    'PatternRegistry',
    'PatternRanker',
    'PatternLifecycleManager',
]
