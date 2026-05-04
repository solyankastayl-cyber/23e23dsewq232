"""
Meta Layer - ORCH-7
===================

Multi-strategy orchestration and capital allocation.

Manages:
- Strategy registry
- Strategy scoring
- Capital allocation across strategies
- Strategy-level policy
"""

from .strategy_registry import StrategyRegistry, get_strategy_registry
from .strategy_score_engine import StrategyScoreEngine, get_strategy_score_engine
from .strategy_allocator import StrategyAllocator, get_strategy_allocator
from .strategy_policy_engine import StrategyPolicyEngine, get_strategy_policy_engine
from .meta_controller import MetaController, get_meta_controller

__all__ = [
    "StrategyRegistry",
    "get_strategy_registry",
    "StrategyScoreEngine",
    "get_strategy_score_engine",
    "StrategyAllocator",
    "get_strategy_allocator",
    "StrategyPolicyEngine",
    "get_strategy_policy_engine",
    "MetaController",
    "get_meta_controller",
]
