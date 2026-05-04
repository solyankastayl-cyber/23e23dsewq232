"""
PHASE 4.8 — Microstructure Entry Layer

Execution-level entry permission based on:
- Liquidity zones and cluster risk
- Orderbook depth and spread
- Buy/sell imbalance
- Absorption detection
- Sweep risk assessment

Decision types:
- ENTER_NOW: Safe to enter immediately
- ENTER_REDUCED: Enter with reduced size
- WAIT_LIQUIDITY_CLEAR: Wait for liquidity cluster to clear
- WAIT_SWEEP: Wait for sweep completion
- WAIT_MICRO_CONFIRMATION: Wait for microstructure confirmation
- SKIP_HOSTILE_SPREAD: Skip due to hostile spread
"""

from .liquidity_engine import LiquidityEngine
from .orderbook_engine import OrderbookEngine
from .imbalance_engine import ImbalanceEngine
from .absorption_engine import AbsorptionEngine
from .sweep_detector import SweepDetector
from .microstructure_decision_engine import MicrostructureDecisionEngine, get_microstructure_engine

MICROSTRUCTURE_DECISIONS = [
    "ENTER_NOW",
    "ENTER_REDUCED",
    "WAIT_LIQUIDITY_CLEAR",
    "WAIT_SWEEP",
    "WAIT_MICRO_CONFIRMATION",
    "SKIP_HOSTILE_SPREAD",
]

__all__ = [
    "LiquidityEngine",
    "OrderbookEngine",
    "ImbalanceEngine",
    "AbsorptionEngine",
    "SweepDetector",
    "MicrostructureDecisionEngine",
    "get_microstructure_engine",
    "MICROSTRUCTURE_DECISIONS",
]
