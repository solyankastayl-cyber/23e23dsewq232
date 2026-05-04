"""
Execution Sync - ORCH-5 + ORCH-6 UPGRADE

Synchronizes order state between local registry and exchange.
Now actively processes fills and creates positions.
ORCH-6: Added partial fill support for LIMIT orders.

Lifecycle:
1. Check open orders
2. Simulate fills (MARKET → instant, LIMIT → partial)
3. Update order status
4. Create/update positions
5. Return lifecycle updates
"""

from typing import Dict, Any, List
import logging

from .fill_engine import FillEngine
from .position_engine import PositionEngine
from .lifecycle_control.partial_fill_engine import PartialFillEngine

logger = logging.getLogger(__name__)


class ExecutionSync:
    """Execution synchronization layer - ORCH-5 + ORCH-6."""
    
    def __init__(self, order_manager):
        self.order_manager = order_manager
        self.fill_engine = FillEngine()
        self.partial_fill_engine = PartialFillEngine()
        self.position_engine = PositionEngine()
    
    def sync(self) -> Dict[str, Any]:
        """Sync order state and process fills."""
        updates: List[Dict[str, Any]] = []
        
        for order in self.order_manager.list_open():
            mode = order.get("mode")
            
            # PASSIVE_LIMIT → partial fills
            if mode == "PASSIVE_LIMIT":
                fill = self.partial_fill_engine.simulate(order, fill_ratio=0.25)
                if fill:
                    self.order_manager.update(
                        order["order_id"],
                        status=fill["status"],
                        filled_qty=fill["new_filled_total"],
                        remaining_qty=fill["remaining_qty"],
                    )
                    
                    if fill["filled_qty"] > 0:
                        position = self.position_engine.on_fill(order, fill)
                        updates.append({
                            "order_id": order["order_id"],
                            "status": fill["status"],
                            "position": position,
                        })
                continue
            
            # MARKET/AGGRESSIVE → instant fill
            fill = self.fill_engine.simulate_fill(order)
            if fill["status"] == "FILLED":
                self.order_manager.update(
                    order["order_id"],
                    status="FILLED",
                    filled_qty=fill["filled_qty"],
                    remaining_qty=0.0,
                )
                position = self.position_engine.on_fill(order, fill)
                updates.append({
                    "order_id": order["order_id"],
                    "status": "FILLED",
                    "position": position,
                })
        
        logger.debug(f"[ExecutionSync] Sync complete: {len(updates)} fills")
        
        return {
            "updates": updates,
            "positions": self.position_engine.list(),
        }

