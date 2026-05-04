"""
Exchange Router

Routes execution intents to appropriate adapters (paper, binance, simulation).
Validates intents and wraps adapter responses in unified format.
"""

import uuid
from typing import Dict, Any
import logging

from .execution_config import EXECUTION_CONFIG
from .adapters.paper_adapter import PaperAdapter
from .adapters.binance_adapter import BinanceAdapter

logger = logging.getLogger(__name__)


class ExchangeRouter:
    """
    Exchange routing layer.
    
    Routes intents to:
    - paper: PaperAdapter (simulated fills)
    - binance: BinanceAdapter (live execution)
    - simulation: returns REJECTED (old behavior)
    """
    
    def __init__(self):
        # Initialize adapters
        self.paper = PaperAdapter(
            slippage_bps=EXECUTION_CONFIG["paper_slippage_bps"],
            fee_bps=EXECUTION_CONFIG["paper_fee_bps"],
        )
        
        self.binance = BinanceAdapter(
            allow_live=EXECUTION_CONFIG["allow_live"]
        )
    
    def route(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route an execution intent to appropriate adapter.
        
        Args:
            intent: Execution intent from ExecutionController
            
        Returns:
            Routing result with order details
        """
        # Check if intent is blocked
        if intent.get("blocked"):
            logger.info(f"[ExchangeRouter] Intent blocked: {intent.get('block_reason')}")
            return {
                "accepted": False,
                "routed": False,
                "route_type": "none",
                "order_id": None,
                "status": "BLOCKED",
                "reason": intent.get("block_reason"),
            }
        
        # Validate size
        size = float(intent.get("size", 0.0) or 0.0)
        if size <= 0:
            logger.info(f"[ExchangeRouter] Intent rejected: non-positive size ({size})")
            return {
                "accepted": False,
                "routed": False,
                "route_type": "none",
                "order_id": None,
                "status": "REJECTED",
                "reason": "non_positive_size",
            }
        
        # Determine route type
        route_type = intent.get("route_type") or EXECUTION_CONFIG["default_route"]
        
        # Map execution mode to order type
        order_type = "LIMIT" if intent.get("mode") == "PASSIVE_LIMIT" else "MARKET"
        
        logger.info(f"[ExchangeRouter] Routing {route_type}: {intent.get('side')} {size} {intent.get('symbol')} ({order_type})")
        
        # Route to paper
        if route_type == "paper":
            result = self.paper.place_order(
                symbol=intent["symbol"],
                side=intent["side"],
                size=size,
                price=intent.get("entry"),
                order_type=order_type,
            )
            return self._wrap(route_type, result)
        
        # Route to binance
        if route_type == "binance":
            result = self.binance.place_order(
                symbol=intent["symbol"],
                side=intent["side"],
                size=size,
                price=intent.get("entry"),
                order_type=order_type,
            )
            return self._wrap(route_type, result)
        
        # Simulation route (old behavior - reject)
        if route_type == "simulation":
            logger.info(f"[ExchangeRouter] Simulation route: not executing")
            return {
                "accepted": False,
                "routed": False,
                "route_type": "simulation",
                "order_id": None,
                "status": "REJECTED",
                "reason": "simulation_mode",
            }
        
        # Unknown route
        logger.error(f"[ExchangeRouter] Unsupported route type: {route_type}")
        return {
            "accepted": False,
            "routed": False,
            "route_type": route_type,
            "order_id": None,
            "status": "REJECTED",
            "reason": "unsupported_route",
        }
    
    def _wrap(self, route_type: str, adapter_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrap adapter result in unified routing response.
        
        Args:
            route_type: Route type (paper/binance)
            adapter_result: Result from adapter
            
        Returns:
            Unified routing result
        """
        # Adapter failed
        if not adapter_result["success"]:
            logger.warning(f"[ExchangeRouter] {route_type} adapter failed: {adapter_result['reason']}")
            return {
                "accepted": False,
                "routed": False,
                "route_type": route_type,
                "order_id": None,
                "status": adapter_result["status"],
                "reason": adapter_result["reason"],
            }
        
        # Adapter succeeded - generate local order ID
        local_order_id = f"{route_type}-{uuid.uuid4().hex[:12]}"
        
        logger.info(f"[ExchangeRouter] Order placed: {local_order_id} (exchange: {adapter_result['exchange_order_id']})")
        
        return {
            "accepted": True,
            "routed": True,
            "route_type": route_type,
            "order_id": local_order_id,
            "exchange_order_id": adapter_result["exchange_order_id"],
            "status": adapter_result["status"],
            "reason": adapter_result["reason"],
            "filled_qty": adapter_result["filled_qty"],
            "avg_price": adapter_result["avg_price"],
            "exchange": adapter_result["exchange"],
        }
