"""
PHASE 1.2 - Execution Styles Module
===================================

Фиксирует как именно стратегия исполняет вход и выход:
- CLEAN_ENTRY - один чистый вход
- SCALED_ENTRY - вход частями
- PARTIAL_EXIT - частичная фиксация
- TIME_EXIT - выход по времени
- DEFENSIVE_EXIT - защитный выход
"""

from .execution_style_types import (
    ExecutionStyleType,
    EntryBehavior,
    ExitBehavior,
    ExecutionStyleDefinition,
    StyleCompatibilityLevel
)
from .execution_style_registry import style_registry
from .style_compatibility import style_compatibility_matrix
from .style_policy import style_policy_engine
from .execution_style_service import execution_style_service

__all__ = [
    'ExecutionStyleType',
    'EntryBehavior',
    'ExitBehavior',
    'ExecutionStyleDefinition',
    'StyleCompatibilityLevel',
    'style_registry',
    'style_compatibility_matrix',
    'style_policy_engine',
    'execution_style_service'
]
