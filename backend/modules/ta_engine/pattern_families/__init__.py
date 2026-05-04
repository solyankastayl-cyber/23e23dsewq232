"""
Pattern Families Architecture
=============================

INSTEAD OF 100 SEPARATE DETECTORS:
- swing_engine.py          → finds all significant highs/lows
- geometry_engine.py       → unified geometric rules
- pattern_family_matrix.py → all patterns by family
- horizontal_family.py     → double/triple top/bottom, range, rectangle
- converging_family.py     → triangles, wedges
- parallel_family.py       → channels, flags
- swing_composite_family.py → H&S, complex patterns
- regime_family.py         → squeeze, compression
- family_classifier.py     → routes to correct family
- family_ranking.py        → selects dominant pattern

This closes 80% of patterns with 10-12 geometric primitives.
"""

from .swing_engine import SwingEngine, get_swing_engine
from .geometry_engine import GeometryEngine, get_geometry_engine
from .pattern_family_matrix import PATTERN_FAMILY_MATRIX, PatternFamily
from .family_classifier import FamilyClassifier, get_family_classifier
from .family_ranking import FamilyRanking, get_family_ranking

__all__ = [
    'SwingEngine', 'get_swing_engine',
    'GeometryEngine', 'get_geometry_engine', 
    'PATTERN_FAMILY_MATRIX', 'PatternFamily',
    'FamilyClassifier', 'get_family_classifier',
    'FamilyRanking', 'get_family_ranking',
]
