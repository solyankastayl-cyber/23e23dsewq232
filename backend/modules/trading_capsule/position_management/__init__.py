"""
PHASE 1.3 - Position Management Policy Module
=============================================

Фиксирует правила управления позицией после входа:
- Stop Loss: HARD_STOP, STRUCTURE_STOP, VOLATILITY_STOP
- Take Profit: FIXED_RR, STRUCTURE_TP, TRAILING_TP
- Trailing: ATR_TRAILING, STRUCTURE_TRAILING, TIME_TRAILING
- Partial Close: фиксация части позиции на уровнях
- Time Stop: выход по времени
- Forced Exit: принудительный выход
"""

from .position_policy_types import (
    StopLossType,
    StopPlacement,
    TakeProfitType,
    TPPlacement,
    TrailingStopType,
    TrailingActivation,
    PartialCloseType,
    TimeStopType,
    ForcedExitTrigger,
    StopLossConfig,
    TakeProfitConfig,
    TrailingStopConfig,
    PartialCloseConfig,
    TimeStopConfig,
    ForcedExitConfig,
    PositionPolicy
)
from .position_policy_registry import position_policy_registry
from .stop_policy_engine import stop_policy_engine
from .take_profit_engine import take_profit_engine
from .trailing_stop_engine import trailing_stop_engine
from .partial_close_engine import partial_close_engine
from .time_stop_engine import time_stop_engine
from .forced_exit_engine import forced_exit_engine
from .position_policy_service import position_policy_service

__all__ = [
    # Types
    'StopLossType',
    'StopPlacement',
    'TakeProfitType',
    'TPPlacement',
    'TrailingStopType',
    'TrailingActivation',
    'PartialCloseType',
    'TimeStopType',
    'ForcedExitTrigger',
    # Configs
    'StopLossConfig',
    'TakeProfitConfig',
    'TrailingStopConfig',
    'PartialCloseConfig',
    'TimeStopConfig',
    'ForcedExitConfig',
    'PositionPolicy',
    # Singletons
    'position_policy_registry',
    'stop_policy_engine',
    'take_profit_engine',
    'trailing_stop_engine',
    'partial_close_engine',
    'time_stop_engine',
    'forced_exit_engine',
    'position_policy_service'
]
