"""
Microstructure Intelligence v2

PHASE 28.1 — Microstructure Snapshot Engine
PHASE 28.2 — Liquidity Vacuum Detector
PHASE 28.3 — Orderbook Pressure Map
PHASE 28.4 — Liquidation Cascade Probability
PHASE 28.5 — Microstructure Context Integration

Provides unified microstructure context for execution decisions.
"""

from .microstructure_snapshot_engine import (
    MicrostructureSnapshotEngine,
    get_microstructure_snapshot_engine,
)
from .microstructure_registry import (
    MicrostructureRegistry,
    get_microstructure_registry,
)
from .microstructure_routes import router as microstructure_router
from .microstructure_types import (
    MicrostructureSnapshot,
    MicrostructureHistoryRecord,
    MicrostructureSummary,
    OrderbookData,
    ExchangeData,
)

# PHASE 28.2 — Liquidity Vacuum
from .liquidity_vacuum_engine import (
    LiquidityVacuumEngine,
    get_liquidity_vacuum_engine,
)
from .liquidity_vacuum_registry import (
    LiquidityVacuumRegistry,
    get_liquidity_vacuum_registry,
)
from .liquidity_vacuum_routes import router as liquidity_vacuum_router
from .liquidity_vacuum_types import (
    LiquidityVacuumState,
    LiquidityVacuumHistoryRecord,
    LiquidityVacuumSummary,
    OrderbookLevel,
    OrderbookLevels,
    MicrostructureContext as VacuumMicrostructureContext,
)

# PHASE 28.3 — Orderbook Pressure Map
from .orderbook_pressure_engine import (
    OrderbookPressureEngine,
    get_orderbook_pressure_engine,
)
from .orderbook_pressure_registry import (
    OrderbookPressureRegistry,
    get_orderbook_pressure_registry,
)
from .orderbook_pressure_routes import router as orderbook_pressure_router
from .orderbook_pressure_types import (
    OrderbookPressureMap,
    OrderbookPressureHistoryRecord,
    OrderbookPressureSummary,
    OrderbookPressureLevel,
    OrderbookPressureInput,
    MicrostructurePressureContext,
)

# PHASE 28.4 — Liquidation Cascade Probability
from .liquidation_cascade_engine import (
    LiquidationCascadeEngine,
    get_liquidation_cascade_engine,
)
from .liquidation_cascade_registry import (
    LiquidationCascadeRegistry,
    get_liquidation_cascade_registry,
)
from .liquidation_cascade_routes import router as liquidation_cascade_router
from .liquidation_cascade_types import (
    LiquidationCascadeState,
    LiquidationCascadeHistoryRecord,
    LiquidationCascadeSummary,
    CascadeInputContext,
)

# PHASE 28.5 — Microstructure Context Integration
from .microstructure_context_engine import (
    MicrostructureContextEngine,
    get_microstructure_context_engine,
)
from .microstructure_context_routes import router as microstructure_context_router
from .microstructure_context_types import (
    MicrostructureContext,
    MicrostructureInputLayers,
    MicrostructureDrivers,
    MicrostructureContextSummary,
)

__all__ = [
    # Phase 28.1
    "MicrostructureSnapshotEngine",
    "get_microstructure_snapshot_engine",
    "MicrostructureRegistry",
    "get_microstructure_registry",
    "microstructure_router",
    "MicrostructureSnapshot",
    "MicrostructureHistoryRecord",
    "MicrostructureSummary",
    "OrderbookData",
    "ExchangeData",
    # Phase 28.2
    "LiquidityVacuumEngine",
    "get_liquidity_vacuum_engine",
    "LiquidityVacuumRegistry",
    "get_liquidity_vacuum_registry",
    "liquidity_vacuum_router",
    "LiquidityVacuumState",
    "LiquidityVacuumHistoryRecord",
    "LiquidityVacuumSummary",
    "OrderbookLevel",
    "OrderbookLevels",
    # Phase 28.3
    "OrderbookPressureEngine",
    "get_orderbook_pressure_engine",
    "OrderbookPressureRegistry",
    "get_orderbook_pressure_registry",
    "orderbook_pressure_router",
    "OrderbookPressureMap",
    "OrderbookPressureHistoryRecord",
    "OrderbookPressureSummary",
    "OrderbookPressureLevel",
    "OrderbookPressureInput",
    "MicrostructurePressureContext",
    # Phase 28.4
    "LiquidationCascadeEngine",
    "get_liquidation_cascade_engine",
    "LiquidationCascadeRegistry",
    "get_liquidation_cascade_registry",
    "liquidation_cascade_router",
    "LiquidationCascadeState",
    "LiquidationCascadeHistoryRecord",
    "LiquidationCascadeSummary",
    "CascadeInputContext",
    # Phase 28.5
    "MicrostructureContextEngine",
    "get_microstructure_context_engine",
    "microstructure_context_router",
    "MicrostructureContext",
    "MicrostructureInputLayers",
    "MicrostructureDrivers",
    "MicrostructureContextSummary",
]
