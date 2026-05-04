"""
PHASE 1.4 - Recovery Engine Module
==================================

Контролируемое усреднение (bounded recovery) для Mean Reversion стратегии.

Ключевые принципы:
- Это НЕ мартингейл
- Это контекстное добавление к позиции
- Жёстко ограничено риском (max 2 adds, 1.5x exposure)
- Только для MEAN_REVERSION
- Только в RANGE/LOW_VOL режимах
"""

from .recovery_types import (
    RecoveryType,
    RecoveryDecision,
    RecoveryDenyReason,
    RegimeFilterResult,
    StructureFilterResult,
    PositionHealthResult,
    RiskLimitsResult,
    RecoveryConfig,
    RecoveryDecisionResult,
    RecoveryEvent
)
from .recovery_policy_engine import recovery_policy_engine
from .recovery_regime_filter import recovery_regime_filter
from .recovery_structure_filter import recovery_structure_filter
from .recovery_risk_limits import recovery_risk_limits
from .recovery_decision_engine import recovery_decision_engine
from .recovery_registry import recovery_registry
from .recovery_service import recovery_service

__all__ = [
    # Types
    'RecoveryType',
    'RecoveryDecision',
    'RecoveryDenyReason',
    'RegimeFilterResult',
    'StructureFilterResult',
    'PositionHealthResult',
    'RiskLimitsResult',
    'RecoveryConfig',
    'RecoveryDecisionResult',
    'RecoveryEvent',
    # Engines
    'recovery_policy_engine',
    'recovery_regime_filter',
    'recovery_structure_filter',
    'recovery_risk_limits',
    'recovery_decision_engine',
    'recovery_registry',
    'recovery_service'
]
