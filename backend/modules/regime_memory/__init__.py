"""
Regime Memory Module

PHASE 34 — Market Regime Memory Layer

Stores and queries historical market states (regime, structure, hypothesis, outcome)
to inform current analysis using cosine similarity.

Components:
- memory_types.py: Pydantic models and constants
- memory_engine.py: Core similarity and scoring logic
- memory_registry.py: MongoDB CRUD operations
- memory_routes.py: FastAPI endpoints
- memory_tests.py: Unit tests (35+)

Key Formulas:
- cosine_similarity(query_vector, memory_vector)
- memory_score = 0.50 * similarity + 0.30 * success_rate + 0.20 * recency_weight
- recency_weight = 1 / log(days_since_event + 2)

Structure Vector (7 elements):
1. trend_slope
2. volatility
3. volume_delta
4. microstructure_bias
5. liquidity_state
6. regime_numeric
7. fractal_alignment

API Endpoints:
- GET  /api/v1/regime-memory/{symbol}
- GET  /api/v1/regime-memory/top/{symbol}
- GET  /api/v1/regime-memory/patterns/{symbol}
- POST /api/v1/regime-memory/recompute/{symbol}
- GET  /api/v1/regime-memory/summary/{symbol}
- GET  /api/v1/regime-memory/modifier/{symbol}
"""

from .memory_types import (
    # Constants
    VECTOR_SIZE,
    SIMILARITY_THRESHOLD,
    WEIGHT_SIMILARITY,
    WEIGHT_SUCCESS_RATE,
    WEIGHT_RECENCY,
    REGIME_MEMORY_WEIGHT,
    RECOMPUTE_INTERVAL_MINUTES,
    # Enums
    RegimeStateType,
    FractalStateType,
    HypothesisTypeEnum,
    MicrostructureStateType,
    # Models
    StructureVector,
    RegimeMemoryRecord,
    MemoryMatch,
    MemoryQuery,
    MemoryResponse,
    MemoryPattern,
    MemorySummary,
    MemoryModifier,
    PendingOutcomeRecord,
)

from .memory_engine import (
    RegimeMemoryEngine,
    get_memory_engine,
)

from .memory_registry import (
    MemoryRegistry,
    get_memory_registry,
    COLLECTION_NAME,
)

from .memory_routes import router as memory_router

from .memory_auto_writer import (
    MemoryAutoWriter,
    get_memory_auto_writer,
)


__all__ = [
    # Constants
    "VECTOR_SIZE",
    "SIMILARITY_THRESHOLD",
    "WEIGHT_SIMILARITY",
    "WEIGHT_SUCCESS_RATE",
    "WEIGHT_RECENCY",
    "REGIME_MEMORY_WEIGHT",
    "RECOMPUTE_INTERVAL_MINUTES",
    "COLLECTION_NAME",
    # Enums
    "RegimeStateType",
    "FractalStateType",
    "HypothesisTypeEnum",
    "MicrostructureStateType",
    # Models
    "StructureVector",
    "RegimeMemoryRecord",
    "MemoryMatch",
    "MemoryQuery",
    "MemoryResponse",
    "MemoryPattern",
    "MemorySummary",
    "MemoryModifier",
    "PendingOutcomeRecord",
    # Engine
    "RegimeMemoryEngine",
    "get_memory_engine",
    # Registry
    "MemoryRegistry",
    "get_memory_registry",
    # Auto-Writer (TASK 93)
    "MemoryAutoWriter",
    "get_memory_auto_writer",
    # Router
    "memory_router",
]
