"""
Fill Engine - ORCH-5

Simulates order fills for paper trading.
Logic:
- MARKET orders: instant fill
- LIMIT orders: remain open (not filled immediately)
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class FillEngine:
    """
    Fill simulation engine for paper trading.
    
    Real exchange integration would replace this with actual fill events.
    """
    
    def simulate_fill(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate fill for an order.
        
        Args:
            order: Order dict from order_manager
            
        Returns:
            Fill result with filled_qty, avg_price, status
        """
        # MARKET orders fill immediately
        if order.get("mode") != "PASSIVE_LIMIT":
            logger.info(f"[FillEngine] MARKET order filled: {order['order_id']}")
            return {
                "filled_qty": order["size"],
                "avg_price": order["entry"],
                "status": "FILLED",
            }
        
        # LIMIT orders remain open
        logger.debug(f"[FillEngine] LIMIT order remains open: {order['order_id']}")
        return {
            "filled_qty": 0.0,
            "avg_price": None,
            "status": "OPEN",
        }
