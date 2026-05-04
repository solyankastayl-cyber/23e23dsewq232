"""
Strategy Regime Engine
======================

Phase REG - Market regime classification for strategy optimization.

Regimes:
- TRENDING: Directional market with clear structure
- RANGE: Sideways market, mean reversion environment  
- HIGH_VOLATILITY: Large amplitude, breakout environment
- LOW_VOLATILITY: Compressed market, pre-breakout
- TRANSITION: Dirty/unclear phase, requires caution

Purpose:
- Classify current market regime
- Provide confidence/stability scores
- Detect regime transitions
- Guide STG2 Logic and STG5 Selection
"""

from .regime_types import (
    MarketRegimeType,
    RegimeState,
    RegimeFeatureSet,
    RegimeTransitionEvent,
    RegimeConfig
)
from .regime_service import regime_service

__all__ = [
    'MarketRegimeType',
    'RegimeState',
    'RegimeFeatureSet',
    'RegimeTransitionEvent',
    'RegimeConfig',
    'regime_service'
]
