"""Partial Fill Engine - ORCH-6"""
import logging
logger = logging.getLogger(__name__)

class PartialFillEngine:
    def simulate(self, order: dict, fill_ratio: float = 0.25):
        status = order.get("status")
        if status not in ["PLACED", "OPEN", "PARTIALLY_FILLED"]:
            return None
        
        total_size = float(order.get("size", 0.0) or 0.0)
        already_filled = float(order.get("filled_qty", 0.0) or 0.0)
        remaining = max(0.0, total_size - already_filled)
        
        if remaining <= 0:
            return None
        
        fill_qty = round(min(remaining, total_size * fill_ratio), 8)
        if fill_qty <= 0:
            return None
        
        new_filled_total = round(already_filled + fill_qty, 8)
        status = "FILLED" if new_filled_total >= total_size else "PARTIALLY_FILLED"
        
        return {
            "filled_qty": fill_qty,
            "avg_price": order.get("entry"),
            "status": status,
            "new_filled_total": new_filled_total,
            "remaining_qty": round(max(0.0, total_size - new_filled_total), 8),
        }
