"""
Routing Models for ORCH-2
========================

Data models for execution intent and routing results.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class ExecutionIntent:
    """Normalized execution intent after Final Gate enforcement."""
    symbol: str
    timeframe: str
    action: str  # ALLOW, ALLOW_REDUCED, ALLOW_MODIFIED, BLOCK
    side: str
    size: float
    mode: str
    entry: Optional[float]
    stop: Optional[float]
    target: Optional[float]
    blocked: bool
    block_reason: Optional[str]
    strategy_id: str = "default"  # ORCH-7 PHASE 3
    trace_id: Optional[str] = None  # P0.7.1: Audit trace ID for causal graph

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RoutingResult:
    """Result of order routing decision."""
    accepted: bool
    routed: bool
    route_type: str  # none, simulation, binance, coinbase, paper
    order_id: Optional[str]
    status: str  # BLOCKED, REJECTED, PLACED, PENDING
    reason: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
