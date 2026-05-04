"""
PHASE 3.5.3 — Market Structure Engine
=====================================

Институциональная модель рынка:
- BOS (Break of Structure) - подтверждение тренда
- CHOCH (Change of Character) - слом структуры
- Liquidity Zones - зоны ликвидности
- Liquidity Sweeps - sweep ликвидности
- Imbalance / FVG - зоны дисбаланса
- Support/Resistance Clusters - кластерные зоны

Интеграция с:
- Alpha Engine
- Signal Ensemble
- Strategy Selection
- Risk Engine
"""

from .structure_types import (
    TrendStructure,
    StructureEvent,
    StructureEventType,
    LiquidityZone,
    LiquidityZoneType,
    LiquiditySweep,
    Imbalance,
    ImbalanceType,
    SRCluster,
    SRType,
    MarketStructureResult,
    StructureSnapshot
)
from .structure_detector import StructureDetector
from .liquidity_detector import LiquidityDetector
from .imbalance_detector import ImbalanceDetector
from .support_resistance_engine import SupportResistanceEngine
from .structure_repository import StructureRepository

__all__ = [
    # Types
    "TrendStructure",
    "StructureEvent",
    "StructureEventType",
    "LiquidityZone",
    "LiquidityZoneType",
    "LiquiditySweep",
    "Imbalance",
    "ImbalanceType",
    "SRCluster",
    "SRType",
    "MarketStructureResult",
    "StructureSnapshot",
    # Components
    "StructureDetector",
    "LiquidityDetector",
    "ImbalanceDetector",
    "SupportResistanceEngine",
    "StructureRepository"
]
