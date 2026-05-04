"""
Displacement Module
===================
Impulse/Strength detection layer.
"""
from .displacement_engine import (
    DisplacementEngine,
    get_displacement_engine,
    displacement_engine,
)

__all__ = [
    "DisplacementEngine",
    "get_displacement_engine",
    "displacement_engine",
]
