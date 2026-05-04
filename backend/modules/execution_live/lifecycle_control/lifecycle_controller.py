"""
Lifecycle Controller - ORCH-6

Action dispatcher for order and position lifecycle management.
"""

import logging
from .order_cancel_engine import OrderCancelEngine
from .order_replace_engine import OrderReplaceEngine
from .position_reduce_engine import PositionReduceEngine
from .position_close_engine import PositionCloseEngine
from .trailing_engine import TrailingEngine

logger = logging.getLogger(__name__)


class LifecycleController:
    """
    Lifecycle action dispatcher.
    
    Receives actions from LifecycleOrchestrator/Policy
    and routes them to appropriate engines.
    """
    
    def __init__(self, order_manager, position_engine):
        self.order_manager = order_manager
        self.position_engine = position_engine
        self.cancel_engine = OrderCancelEngine()
        self.replace_engine = OrderReplaceEngine()
        self.reduce_engine = PositionReduceEngine()
        self.close_engine = PositionCloseEngine()
        self.trailing_engine = TrailingEngine()
    
    def dispatch(self, action: dict):
        """Dispatch lifecycle action to appropriate engine."""
        action_type = action.get("action_type")
        target_id = action.get("target_id")
        reason = action.get("reason", "manual_action")
        payload = action.get("payload", {})
        
        if action_type == "CANCEL_ORDER":
            return self.cancel_engine.cancel(self.order_manager, target_id, reason)
        
        if action_type == "REPLACE_ORDER":
            return self.replace_engine.replace(
                self.order_manager,
                target_id,
                payload.get("new_entry"),
                payload.get("new_size"),
                reason,
            )
        
        if action_type == "REDUCE_POSITION":
            return self.reduce_engine.reduce(
                self.position_engine,
                target_id,
                payload.get("reduce_qty", 0.0),
                payload.get("exit_price"),
                reason,
            )
        
        if action_type == "CLOSE_POSITION":
            return self.close_engine.close(
                self.position_engine,
                target_id,
                payload.get("exit_price"),
                reason,
            )
        
        if action_type == "TRAIL_STOP":
            return self.trailing_engine.update_stop(
                self.position_engine,
                target_id,
                payload.get("new_stop"),
                reason,
            )
        
        logger.warning(f"[LifecycleController] Unknown action type: {action_type}")
        return {"ok": False, "status": "UNKNOWN_ACTION", "reason": "unsupported_action_type"}
