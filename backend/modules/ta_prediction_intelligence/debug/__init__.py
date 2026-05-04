"""
Debug Layer — read-only interpretation of evaluated predictions.

Classifies each evaluated prediction into a single primary error type
(per the locked spec) and attributes the root cause to specific layers
(interaction / engines / conflict / temporal / risk / scenario).

HARD CONTRACT (read-only):
    DEBUG LAYER MAY:
        * read ta_prediction_history
        * read outcomes
        * read features / decision / temporal blocks within history records
        * write to its own collection ta_prediction_debug

    DEBUG LAYER MUST NOT:
        * mutate prediction records
        * mutate decision_intelligence formulas
        * mutate features / dataset / calibration / temporal layers
        * influence the live pipeline
"""
from .taxonomy import (
    ErrorType,
    SMALL_MOVE_THRESHOLD,
    HIGH_VOLATILITY_THRESHOLD,
    OVERCONFIDENT_THRESHOLD,
    UNDERCONFIDENT_THRESHOLD,
    classify_error,
)
from .root_cause import attribute_root_causes
from .service import analyze_record, build_debug_record
from .metrics import compute_metrics
from .repository import (
    DEBUG_COLLECTION,
    DebugRepository,
    get_debug_repository,
    init_debug_repository,
)

__all__ = [
    "ErrorType",
    "SMALL_MOVE_THRESHOLD",
    "HIGH_VOLATILITY_THRESHOLD",
    "OVERCONFIDENT_THRESHOLD",
    "UNDERCONFIDENT_THRESHOLD",
    "classify_error",
    "attribute_root_causes",
    "analyze_record",
    "build_debug_record",
    "compute_metrics",
    "DEBUG_COLLECTION",
    "DebugRepository",
    "get_debug_repository",
    "init_debug_repository",
]
