"""
Fibonacci Engine Package
========================
Auto swing detection and Fibonacci level calculation.

Usage:
    from modules.ta_engine.fibonacci import get_fibonacci_engine
    
    engine = get_fibonacci_engine()
    result = engine.build(
        candles=candles,
        pivot_highs=pivot_highs,
        pivot_lows=pivot_lows,
        structure_context=structure_context,
        timeframe="1D",
    )
"""

from .fibonacci_engine import FibonacciEngine, get_fibonacci_engine, FibonacciSet, FibLevel

__all__ = [
    'FibonacciEngine',
    'get_fibonacci_engine',
    'FibonacciSet',
    'FibLevel',
]
