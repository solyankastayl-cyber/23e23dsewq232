"""
PHASE 2.3 - Forward Simulation
==============================

Pseudo-live trading simulation:
- Candle-by-candle replay
- Real-time decision making
- Virtual broker execution
- Full Trading Doctrine integration
"""

from .forward_types import (
    SimulationConfig,
    SimulationRun,
    SimulatedTrade,
    EquityCurve,
    ForwardMetrics,
    SimulationStatus
)
from .market_replay_engine import market_replay_engine
from .forward_broker_simulator import broker_simulator
from .forward_position_manager import forward_position_manager
from .forward_metrics_engine import forward_metrics_engine
from .forward_engine import forward_engine
from .forward_repository import forward_repository

__all__ = [
    'SimulationConfig',
    'SimulationRun',
    'SimulatedTrade',
    'EquityCurve',
    'ForwardMetrics',
    'SimulationStatus',
    'market_replay_engine',
    'broker_simulator',
    'forward_position_manager',
    'forward_metrics_engine',
    'forward_engine',
    'forward_repository'
]
