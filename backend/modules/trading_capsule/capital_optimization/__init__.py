"""
PHASE 3.4 - Capital Optimization Engine
========================================

Modules:
- capital_optimizer.py - Core capital optimization
- strategy_allocator.py - Strategy allocation management
- capital_efficiency_engine.py - Capital efficiency calculations
- allocation_repository.py - Data persistence
- allocation_routes.py - API endpoints

Capital Flow:
Strategy Performance -> Efficiency Analysis -> Allocation Adjustment -> Portfolio Optimization
"""

from .capital_optimizer import CapitalOptimizer, capital_optimizer
from .strategy_allocator import StrategyAllocator, strategy_allocator
from .capital_efficiency_engine import CapitalEfficiencyEngine, capital_efficiency_engine
from .allocation_repository import allocation_repository

__all__ = [
    "CapitalOptimizer",
    "capital_optimizer",
    "StrategyAllocator",
    "strategy_allocator",
    "CapitalEfficiencyEngine",
    "capital_efficiency_engine",
    "allocation_repository"
]
