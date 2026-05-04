"""
Trade Setup Module — Execution-Ready Trade Setups
=================================================

Converts analysis into actionable trade setups:
  - Entry zone
  - Stop loss
  - Targets
  - Risk/Reward
  - Validity
"""

from .trade_setup_generator import (
    TradeSetup,
    TradeSetupGenerator,
    get_trade_setup_generator,
    trade_setup_generator,
)

__all__ = [
    "TradeSetup",
    "TradeSetupGenerator",
    "get_trade_setup_generator",
    "trade_setup_generator",
]
