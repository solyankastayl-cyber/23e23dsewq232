"""Order Replace Engine - ORCH-6"""
import logging
logger = logging.getLogger(__name__)

class OrderReplaceEngine:
    def replace(self, order_manager, order_id: str, new_entry: float = None, new_size: float = None, reason: str = "repriced"):
        order = order_manager.get(order_id)
        if not order:
            return {"ok": False, "status": "NOT_FOUND", "reason": "order_not_found"}
        
        if order.get("status") not in ["PLACED", "PARTIALLY_FILLED", "OPEN"]:
            return {"ok": False, "status": "NOT_REPLACEABLE", "reason": "order_not_open"}
        
        fields = {"replace_reason": reason}
        if new_entry is not None:
            fields["entry"] = new_entry
        if new_size is not None:
            if new_size <= 0:
                return {"ok": False, "status": "INVALID_SIZE", "reason": "non_positive_size"}
            fields["size"] = new_size
        
        updated = order_manager.update(order_id, **fields)
        logger.info(f"[OrderReplaceEngine] Replaced {order_id}: {reason}")
        return {"ok": True, "status": "REPLACED", "order": updated}
