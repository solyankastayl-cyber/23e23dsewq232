"""
Explanation Engine Module
========================

V1: Detailed explanation (legacy)
V2: Ultra-compact, 3 lines, trader-style
"""

from .explanation_engine_v1 import (
    ExplanationEngineV1,
    get_explanation_engine_v1,
    explanation_engine_v1,
)

from .explanation_engine_v2 import (
    ExplanationEngineV2,
    get_explanation_engine_v2,
    explanation_engine_v2,
)

__all__ = [
    # V1 (detailed)
    "ExplanationEngineV1",
    "get_explanation_engine_v1",
    "explanation_engine_v1",
    # V2 (compact)
    "ExplanationEngineV2",
    "get_explanation_engine_v2",
    "explanation_engine_v2",
]
