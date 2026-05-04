"""
Execution Result — PHASE 2.4

Structured result of execution simulation.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionResult:
    filled: bool
    entry_price: Optional[float]
    slippage: float
    latency_price: float

    def to_dict(self) -> dict:
        return {
            "filled": self.filled,
            "entry_price": self.entry_price,
            "slippage": round(self.slippage, 6) if self.slippage else 0,
            "latency_price": round(self.latency_price, 2) if self.latency_price else 0,
        }
