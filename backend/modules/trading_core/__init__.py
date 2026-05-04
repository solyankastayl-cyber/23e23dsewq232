"""Trading Core Module — Week 2

Decision Engine + Portfolio Engine + Trading Runtime
"""

from .decision_engine import make_decision, calculate_position_size
from .portfolio_engine import (
    get_portfolio,
    open_position,
    close_position,
    update_position_pnl,
    calculate_portfolio_metrics,
)
from .trading_runtime import run_trading_cycle, start_trading_scheduler, stop_trading_scheduler

__all__ = [
    "make_decision",
    "calculate_position_size",
    "get_portfolio",
    "open_position",
    "close_position",
    "update_position_pnl",
    "calculate_portfolio_metrics",
    "run_trading_cycle",
    "start_trading_scheduler",
    "stop_trading_scheduler",
]
