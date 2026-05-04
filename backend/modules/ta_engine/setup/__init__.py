"""
Setup Engine Module
===================
Setup Graph Architecture for Technical Analysis.

This module provides:
- Setup types and data structures
- Pattern detection
- Indicator signal extraction
- Level detection (S/R, Fib, Liquidity)
- Structure analysis (HH/HL, BOS, CHOCH)
- Confluence computation
- Setup building and ranking
"""

from .setup_types import (
    Setup,
    SetupType,
    Direction,
    PatternType,
    StructureType,
    LevelType,
    DetectedPattern,
    IndicatorSignal,
    StructurePoint,
    PriceLevel,
    Confluence,
    ConflictSignal,
    SetupAnalysisResult,
)

from .setup_builder import get_setup_builder
from .pattern_detector import get_pattern_detector
from .indicator_engine import get_indicator_engine
from .level_engine import get_level_engine
from .structure_engine import get_structure_engine

# IMPORTANT: Import pattern_detectors_unified to register all pattern detectors
# This triggers @register_pattern decorators
from . import pattern_detectors_unified  # noqa: F401

__all__ = [
    # Types
    "Setup",
    "SetupType",
    "Direction",
    "PatternType",
    "StructureType",
    "LevelType",
    "DetectedPattern",
    "IndicatorSignal",
    "StructurePoint",
    "PriceLevel",
    "Confluence",
    "ConflictSignal",
    "SetupAnalysisResult",
    # Builders
    "get_setup_builder",
    "get_pattern_detector",
    "get_indicator_engine",
    "get_level_engine",
    "get_structure_engine",
]
