"""
Order Router
============

Routes execution intent to appropriate execution channel.
"""

import uuid
from typing import Dict, Any
from .routing_models import ExecutionIntent, RoutingResult


class OrderRouter:
    """Routes orders to execution channels."""
    
    def __init__(self, default_route: str = "simulation"):
        """
        Initialize router.
        
        Args:
            default_route: Default routing channel (simulation, binance, paper, etc.)
        """
        self.default_route = default_route
    
    def route(self, intent: ExecutionIntent) -> RoutingResult:
        """Route execution intent to appropriate channel."""
        
        # Blocked intents don't route
        if intent.blocked:
            return RoutingResult(
                accepted=False,
                routed=False,
                route_type="none",
                order_id=None,
                status="BLOCKED",
                reason=intent.block_reason,
            )
        
        # Reject non-positive sizes
        if intent.size <= 0:
            return RoutingResult(
                accepted=False,
                routed=False,
                route_type="none",
                order_id=None,
                status="REJECTED",
                reason="non_positive_size",
            )
        
        # Route to simulation (MVP)
        if self.default_route == "simulation":
            return RoutingResult(
                accepted=True,
                routed=True,
                route_type="simulation",
                order_id=f"sim-{uuid.uuid4().hex[:12]}",
                status="PLACED",
                reason=None,
            )
        
        # Unsupported route
        return RoutingResult(
            accepted=False,
            routed=False,
            route_type="none",
            order_id=None,
            status="REJECTED",
            reason="unsupported_route",
        )
