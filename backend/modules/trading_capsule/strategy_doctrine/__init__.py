"""
PHASE 1.1 - Strategy Doctrine Module
====================================

Фиксирует торговую доктрину системы:
- Какая стратегия primary/secondary
- Где каждая стратегия разрешена/запрещена
- Совместимость с режимами рынка
- Совместимость с профилями
- Иерархия приоритетов
"""

from .doctrine_types import (
    StrategyType,
    RegimeType,
    ProfileType,
    TimeframeType,
    AssetClass,
    CompatibilityLevel,
    StrategyDefinition,
    DoctrineRule
)
from .strategy_regime_matrix import strategy_regime_matrix
from .strategy_profile_matrix import strategy_profile_matrix
from .strategy_hierarchy import strategy_hierarchy
from .strategy_blocking_rules import blocking_rules_engine
from .doctrine_service import doctrine_service

__all__ = [
    'StrategyType',
    'RegimeType',
    'ProfileType',
    'TimeframeType',
    'AssetClass',
    'CompatibilityLevel',
    'StrategyDefinition',
    'DoctrineRule',
    'strategy_regime_matrix',
    'strategy_profile_matrix',
    'strategy_hierarchy',
    'blocking_rules_engine',
    'doctrine_service'
]
