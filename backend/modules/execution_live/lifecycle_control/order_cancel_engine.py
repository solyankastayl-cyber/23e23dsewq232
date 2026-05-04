"""Order Cancel Engine - ORCH-6"""
import logging
logger = logging.getLogger(__name__)

class OrderCancelEngine:
    def cancel(self, order_manager, order_id: str, reason: str = "manual_cancel"):
        order = order_manager.get(order_id)
        if not order:
            return {"ok": False, "status": "NOT_FOUND", "reason": "order_not_found"}
        
        if order.get("status") in ["FILLED", "CANCELLED", "REJECTED", "FAILED"]:
            return {"ok": False, "status": "NOT_CANCELLABLE", "reason": "terminal_order_state"}
        
        updated = order_manager.update(order_id, status="CANCELLED", cancel_reason=reason)
        logger.info(f"[OrderCancelEngine] Cancelled {order_id}: {reason}")
        return {"ok": True, "status": "CANCELLED", "order": updated}
