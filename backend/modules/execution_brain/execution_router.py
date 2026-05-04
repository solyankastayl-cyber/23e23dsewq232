"""
Execution Router

PHASE 37 — Execution Brain

Routes execution to appropriate order type based on liquidity.

Selection logic:
- high liquidity → MARKET
- medium liquidity → LIMIT
- low liquidity → TWAP
- very large orders → ICEBERG
"""

from typing import Optional
from datetime import datetime, timezone

from .execution_types import ExecutionType


class ExecutionRouter:
    """
    Routes execution to appropriate order type.
    """
    
    def __init__(self):
        pass
    
    def route_execution(
        self,
        liquidity_bucket: str,
        order_size_usd: float,
        impact_state: str,
        symbol: str,
    ) -> ExecutionType:
        """
        Determine optimal execution type.
        
        Selection logic:
        - DEEP liquidity + LOW_IMPACT → MARKET
        - NORMAL liquidity + MANAGEABLE → LIMIT
        - THIN liquidity or HIGH_IMPACT → TWAP
        - FRAGILE liquidity or UNTRADEABLE or very large → ICEBERG
        """
        # Check for very large orders (relative to typical volume)
        large_order_threshold = self._get_large_order_threshold(symbol)
        is_large_order = order_size_usd >= large_order_threshold
        
        # Route based on conditions
        if is_large_order or impact_state == "UNTRADEABLE" or liquidity_bucket == "FRAGILE":
            return "ICEBERG"
        
        if impact_state == "HIGH_IMPACT" or liquidity_bucket == "THIN":
            return "TWAP"
        
        if liquidity_bucket == "DEEP" and impact_state == "LOW_IMPACT":
            return "MARKET"
        
        # Default to LIMIT
        return "LIMIT"
    
    def _get_large_order_threshold(self, symbol: str) -> float:
        """Get large order threshold for symbol."""
        thresholds = {
            "BTC": 500000,  # $500K
            "ETH": 200000,  # $200K
            "SOL": 50000,   # $50K
        }
        return thresholds.get(symbol.upper(), 100000)
    
    def get_order_split_recommendation(
        self,
        execution_type: ExecutionType,
        order_size_usd: float,
    ) -> dict:
        """
        Get recommendation for order splitting.
        """
        if execution_type == "MARKET":
            return {
                "split_required": False,
                "num_slices": 1,
                "slice_size_usd": order_size_usd,
                "interval_seconds": 0,
            }
        
        elif execution_type == "LIMIT":
            return {
                "split_required": False,
                "num_slices": 1,
                "slice_size_usd": order_size_usd,
                "interval_seconds": 0,
            }
        
        elif execution_type == "TWAP":
            # Split into ~10 slices over 30 minutes
            num_slices = min(10, max(3, int(order_size_usd / 10000)))
            return {
                "split_required": True,
                "num_slices": num_slices,
                "slice_size_usd": round(order_size_usd / num_slices, 2),
                "interval_seconds": 180,  # 3 minutes between slices
            }
        
        elif execution_type == "ICEBERG":
            # Split into ~20 slices over 60 minutes
            num_slices = min(20, max(5, int(order_size_usd / 25000)))
            return {
                "split_required": True,
                "num_slices": num_slices,
                "slice_size_usd": round(order_size_usd / num_slices, 2),
                "interval_seconds": 180,
            }
        
        return {
            "split_required": False,
            "num_slices": 1,
            "slice_size_usd": order_size_usd,
            "interval_seconds": 0,
        }


# Singleton
_execution_router: Optional[ExecutionRouter] = None


def get_execution_router() -> ExecutionRouter:
    global _execution_router
    if _execution_router is None:
        _execution_router = ExecutionRouter()
    return _execution_router
