"""
Exchange Adapters

Unified adapter interface for different execution venues.
"""

from .paper_adapter import PaperAdapter
from .binance_adapter import BinanceAdapter

__all__ = ["PaperAdapter", "BinanceAdapter"]
