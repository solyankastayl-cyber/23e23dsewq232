"""
PHASE 12 - System Intelligence Layer
======================================
Meta-level control layer for the entire system.

Combines all brains into unified intelligence:
- Market Brain
- Structure Brain  
- Liquidity Brain
- Microstructure Brain
- Strategy Brain
- Execution Brain
- Portfolio Brain
- Research Brain
- Learning Brain

This is the final layer that creates an Autonomous Trading Intelligence.
"""

from .system_types import (
    GlobalMarketState,
    SystemHealthState,
    RegimeProfile,
    SystemAction,
    SystemDecision,
    MarketStateSnapshot,
    SystemHealthSnapshot,
    RegimeSwitchRecommendation,
    ResearchLoopStatus,
    UnifiedSystemSnapshot
)

__all__ = [
    'GlobalMarketState',
    'SystemHealthState',
    'RegimeProfile',
    'SystemAction',
    'SystemDecision',
    'MarketStateSnapshot',
    'SystemHealthSnapshot',
    'RegimeSwitchRecommendation',
    'ResearchLoopStatus',
    'UnifiedSystemSnapshot'
]
